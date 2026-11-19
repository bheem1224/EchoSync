"""Wave 4 unit tests for unified PlaylistSyncService, route/matcher deduplication, and hygiene decoupling."""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch
import uuid

from fastapi.testclient import TestClient
import pytest

from core.db.echo_sync_track import EchosyncTrack
from core.sync_history import sync_history
from database.music_database import (
    Artist,
    Base,
    ExternalIdentifier,
    LocalMedia,
    Track,
    close_database,
    get_database,
)
from database.working_database import (
    ReviewTask,
    WorkingBase,
    close_working_database,
    get_working_database,
)
from services.deduplicator import get_deduplicator
from services.library_hygiene import DuplicateHygieneService, LibraryHygieneService
from services.playlist_sync import (
    ANALYSIS_JOBS,
    MATCH_TRACE_CACHE,
    BoundedTTLCache,
    PlaylistSyncService,
    SourcePlaylist,
    SyncProgress,
    SyncResult,
    clear_match_trace_cache,
    get_cached_match_trace,
)
from web.api_app import create_app
import web.routes.playlists as playlists_route

REPO_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_VENDOR_NAMES = ("plex", "jellyfin", "spotify", "slskd", "acoustid")


@pytest.fixture
def isolated_wave4_dbs(tmp_path, monkeypatch):
    """Create isolated music and working SQLite databases in tmp_path."""
    close_database()
    close_working_database()
    clear_match_trace_cache()
    ANALYSIS_JOBS.clear()

    music_db_path = tmp_path / f"wave4_music_{uuid.uuid4().hex[:8]}.db"
    work_db_path = tmp_path / f"wave4_work_{uuid.uuid4().hex[:8]}.db"

    music_db = get_database(str(music_db_path))
    Base.metadata.create_all(music_db.engine)

    work_db = get_working_database(str(work_db_path))
    WorkingBase.metadata.create_all(work_db.engine)

    monkeypatch.setattr("database.music_database.MusicDatabase", lambda *a, **kw: music_db)
    monkeypatch.setattr("database.music_database.get_database", lambda *a, **kw: music_db)
    monkeypatch.setattr("services.playlist_sync.db_mod.MusicDatabase", lambda *a, **kw: music_db)
    monkeypatch.setattr("web.routes.playlists.MusicDatabase", lambda *a, **kw: music_db)
    monkeypatch.setattr("database.working_database.get_working_database", lambda *a, **kw: work_db)
    monkeypatch.setattr("web.routes.metadata_review.get_working_database", lambda *a, **kw: work_db)
    monkeypatch.setattr("web.routes.metadata_review.get_database", lambda *a, **kw: music_db)
    monkeypatch.setattr(sync_history, "_history_file", tmp_path / "sync_history.jsonl")

    yield music_db, work_db

    clear_match_trace_cache()
    ANALYSIS_JOBS.clear()
    close_working_database()
    close_database()


def test_obsolete_duplicate_files_deleted():
    """Verify legacy duplicate service and route files have been deleted."""
    deleted_paths = [
        REPO_ROOT / "services" / "sync_service.py",
        REPO_ROOT / "web" / "services" / "sync_service.py",
        REPO_ROOT / "services" / "match_service.py",
        REPO_ROOT / "web" / "routes" / "metadata.py",
    ]
    for path in deleted_paths:
        assert not path.exists(), f"Expected obsolete file to be deleted: {path}"


def test_playlists_route_has_no_duplicate_inline_matcher_helpers():
    """Verify inline matcher helpers (_cmp_titles, _cmp_artists, _fetch_tier1_candidates, _fetch_tier2_candidates) were stripped from web/routes/playlists.py."""
    source = (REPO_ROOT / "web" / "routes" / "playlists.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    defined_funcs = {
        node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    for forbidden_helper in (
        "_cmp_titles",
        "_cmp_artists",
        "_fetch_tier1_candidates",
        "_fetch_tier2_candidates",
    ):
        assert forbidden_helper not in defined_funcs
        assert not hasattr(playlists_route, forbidden_helper)


def test_services_are_vendor_agnostic():
    """Verify services/playlist_sync.py, services/deduplicator.py, and services/library_hygiene.py contain zero vendor-specific names."""
    target_files = [
        REPO_ROOT / "services" / "playlist_sync.py",
        REPO_ROOT / "services" / "deduplicator.py",
        REPO_ROOT / "services" / "library_hygiene.py",
    ]
    for file_path in target_files:
        content_lower = file_path.read_text(encoding="utf-8").lower()
        for vendor in FORBIDDEN_VENDOR_NAMES:
            assert vendor not in content_lower, f"Vendor name '{vendor}' found in {file_path.name}"


def test_deduplicator_and_library_hygiene_have_no_circular_imports():
    """Verify services/deduplicator.py does not import services.library_hygiene."""
    source = (REPO_ROOT / "services" / "deduplicator.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert not any("library_hygiene" in mod for mod in imported_modules)
    assert LibraryHygieneService is DuplicateHygieneService


def test_unified_playlist_sync_execution_deluxe_fallback_and_history(isolated_wave4_dbs, tmp_path):
    """Verify PlaylistSyncService matches Deluxe fallback, selects highest quality media, decouples target_quality, and records sync history."""
    music_db, _ = isolated_wave4_dbs
    sync_history.clear()

    with music_db.session_scope() as session:
        artist = Artist(name="David Bowie")
        session.add(artist)
        session.flush()

        # Deluxe edition track in library with both MP3 and FLAC files
        track = Track(
            title="Heroes",
            artist_id=artist.id,
            duration=367000,
            edition="Deluxe Edition",
            sync_id="sync_bowie_heroes",
        )
        session.add(track)
        session.flush()

        m_mp3 = LocalMedia(
            track_id=track.id,
            file_path=str(tmp_path / "Heroes_low.mp3"),
            media_id="media_heroes_mp3",
            file_format="mp3",
            bitrate=192000,
            sample_rate=44100,
            bit_depth=16,
        )
        m_flac = LocalMedia(
            track_id=track.id,
            file_path=str(tmp_path / "Heroes_hi.flac"),
            media_id="media_heroes_flac",
            file_format="flac",
            bitrate=1411000,
            sample_rate=96000,
            bit_depth=24,
        )
        session.add_all([m_mp3, m_flac])
        session.flush()

        ext = ExternalIdentifier(
            media_id="media_heroes_flac",
            plugin_source="media_srv",
            plugin_item_id="srv_item_77",
        )
        session.add(ext)
        session.commit()

    fake_media_server = MagicMock()
    fake_media_server.name = "media_srv"
    fake_media_server.is_connected.return_value = True
    fake_media_server.get_track.return_value = {"id": "srv_item_77"}
    fake_media_server.add_tracks_to_playlist.return_value = True

    service = PlaylistSyncService(db=music_db, media_client=fake_media_server)
    assert isinstance(MATCH_TRACE_CACHE, BoundedTTLCache)
    assert isinstance(ANALYSIS_JOBS, BoundedTTLCache)

    # 1. Analyze with target_quality="raw/lossless": Deluxe fallback + highest quality media selection
    analysis = service.analyze_playlist(
        playlist_name="Bowie Classics",
        tracks=[
            {
                "id": "src_1",
                "title": "Heroes",
                "artist": "David Bowie",
                "album": "Heroes",
                "duration_ms": 367500,
            },
            {
                "id": "src_2",
                "title": "Unmatched Missing Track",
                "artist": "David Bowie",
                "album": "Low",
                "duration_ms": 210000,
                "isrc": "USRC17700001",
            },
        ],
        target_source="media_srv",
        target_quality="raw/lossless",
    )

    assert analysis["summary"]["total_tracks"] == 2
    assert analysis["summary"]["found_in_library"] == 1
    assert analysis["summary"]["missing_tracks"] == 1

    found_item = next(t for t in analysis["tracks"] if t["title"] == "Heroes")
    assert found_item["status"] == "found"
    assert found_item["primary_media_path"].endswith("Heroes_hi.flac")
    assert found_item["target_identifier"] == "srv_item_77"
    assert get_cached_match_trace("Heroes", "David Bowie", 367500) is not None

    # 2. Queue missing downloads applies target_quality strictly to download queue
    queued_calls = []

    class FakeDM:
        def queue_download(self, track, quality_profile_id=None):
            queued_calls.append((track, quality_profile_id))
            return 555

        def process_downloads_now(self):
            pass

    service.download_manager = FakeDM()
    dl_res = service.queue_missing_downloads(analysis["missing"], target_quality="raw/lossless")
    assert dl_res["accepted"] is True
    assert dl_res["queued"] == 1
    assert queued_calls[0][0].title == "Unmatched Missing Track"
    assert queued_calls[0][1] == "raw/lossless"

    # 3. Execute sync_playlist and verify media server dispatch & sync_history recording
    source_pl = SourcePlaylist(
        id="pl_bowie",
        name="Bowie Classics",
        tracks=[
            EchosyncTrack(
                raw_title="Heroes",
                title="Heroes",
                artist_name="David Bowie",
                album_title="Heroes",
                duration_ms=367500,
            )
        ],
    )
    progress_updates: list[SyncProgress] = []
    service.set_progress_callback(progress_updates.append, playlist_name="Bowie Classics")
    sync_result: SyncResult = asyncio.run(service.sync_playlist(source_pl, download_missing=False))

    assert sync_result.total_tracks == 1
    assert sync_result.matched_tracks == 1
    assert sync_result.synced_tracks == 1
    assert sync_result.success_rate == 100.0
    assert len(progress_updates) >= 2
    fake_media_server.add_tracks_to_playlist.assert_called_once_with("Bowie Classics", ["srv_item_77"])

    recent_history = sync_history.get_recent(limit=5)
    assert any(r.playlist == "Bowie Classics" and r.synced == 1 for r in recent_history)


def test_consolidated_metadata_routes_on_core_and_v1_prefixes(isolated_wave4_dbs, tmp_path):
    """Verify consolidated metadata endpoints in metadata_review.py respond on both /api/v1/core/metadata/* and /api/v1/metadata/*."""
    _, work_db = isolated_wave4_dbs
    audio_file = tmp_path / "review_sample.flac"
    audio_file.write_bytes(b"dummy audio bytes")

    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(audio_file),
            status="pending",
            confidence_score=0.55,
            track_data={
                "title": "Pending Song",
                "artist": "Pending Artist",
                "album": "Pending Album",
            },
        )
        session.add(task)
        session.flush()
        task_id = task.id

    app = create_app(testing=True)
    with TestClient(app) as client:
        # 1. GET /queue on both prefixes
        for prefix in ("/api/v1/core/metadata", "/api/v1/metadata"):
            resp = client.get(f"{prefix}/queue")
            assert resp.status_code == 200
            queue_items = resp.json()["queue"]
            assert any(item["id"] == task_id for item in queue_items)

            detail_resp = client.get(f"{prefix}/queue/{task_id}")
            assert detail_resp.status_code == 200
            assert detail_resp.json()["item"]["id"] == task_id

        # 2. POST /queue/manual-search
        fake_provider = MagicMock()
        fake_provider.search_metadata.return_value = [{"title": "Found Song", "artist": "Found Artist"}]
        with patch("web.routes.metadata_review._get_plugin", return_value=fake_provider):
            search_resp = client.post("/api/v1/core/metadata/queue/manual-search", json={"query": "Found Song"})
            assert search_resp.status_code == 200
            assert search_resp.json()["results"][0]["title"] == "Found Song"

        # 3. GET /isrc/{isrc}
        fake_isrc_provider = MagicMock()
        fake_isrc_provider.name = "test_isrc_provider"
        fake_isrc_provider.search_by_isrc.return_value = EchosyncTrack(
            raw_title="ISRC Track",
            title="ISRC Track",
            artist_name="ISRC Artist",
            isrc="USRC17607839",
        )
        with patch("web.routes.metadata_review.get_plugin_by_capability", return_value=fake_isrc_provider):
            isrc_resp = client.get("/api/v1/metadata/isrc/USRC17607839")
            assert isrc_resp.status_code == 200
            assert isrc_resp.json()["isrc"] == "USRC17607839"

        # 4. DELETE /queue/ignore
        ignore_resp = client.request("DELETE", "/api/v1/core/metadata/queue/ignore", json={"id": task_id})
        assert ignore_resp.status_code == 200
        assert ignore_resp.json()["success"] is True


def test_decoupled_deduplicator_and_hygiene_scan(isolated_wave4_dbs, tmp_path):
    """Verify DeduplicationService and DuplicateHygieneService scan relational and acoustic duplicates without circular import errors."""
    music_db, _ = isolated_wave4_dbs

    with music_db.session_scope() as session:
        artist = Artist(name="Hygiene Test Artist")
        session.add(artist)
        session.flush()

        t1 = Track(title="Relational Dup", artist_id=artist.id, sync_id="sync_rel_1", duration=200000)
        session.add(t1)
        session.flush()

        m1 = LocalMedia(
            track_id=t1.id,
            file_path=str(tmp_path / "rel_1.flac"),
            media_id="med_rel_flac",
            file_format="flac",
            bitrate=1411,
            bit_depth=24,
            sample_rate=48000,
        )
        m2 = LocalMedia(
            track_id=t1.id,
            file_path=str(tmp_path / "rel_2.mp3"),
            media_id="med_rel_mp3",
            file_format="mp3",
            bitrate=320,
            bit_depth=16,
            sample_rate=44100,
        )
        session.add_all([m1, m2])
        session.commit()

    dedup = get_deduplicator(music_db)
    scan_res = dedup.scan_library_duplicates(backfill=False)
    assert len(scan_res["relational_duplicates"]) == 1
    assert scan_res["relational_duplicates"][0]["keep_media_id"] == "med_rel_flac"

    hygiene = DuplicateHygieneService(music_db)
    hygiene_res = hygiene.find_duplicates(backfill=False)
    assert len(hygiene_res["auto_resolve"]) == 1
    assert hygiene_res["auto_resolve"][0]["keep_media_id"] == "med_rel_flac"
