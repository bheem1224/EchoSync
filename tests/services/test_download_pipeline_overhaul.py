"""Regression & feature tests for the Download Pipeline Overhaul."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.db.echo_sync_track import EchosyncMedia, EchosyncTrack
from core.matching_engine.matching_engine import (
    WeightedMatchingEngine,
    evaluate_version_compatibility,
)
from core.matching_engine.scoring_profile import PROFILE_DOWNLOAD_SEARCH
from core.matching_engine.track_parser import TrackParser
from database.config_database import ConfigDatabase
from plugins.EchoSync.slskd.client import _is_raw_file_eligible
from services.download_manager import DownloadManager


def test_remaster_year_exact_vs_generic_vs_contradicting():
    # Exact year match -> 0 penalty
    ok_exact, pen_exact, _ = evaluate_version_compatibility(
        "2011 Remaster", "2011 Remaster", context="download", duration_delta_ms=500
    )
    assert ok_exact is True and pen_exact == 0.0

    # Contradicting year -> hard reject
    ok_wrong, _, _ = evaluate_version_compatibility(
        "2011 Remaster", "2009 Remaster", context="download", duration_delta_ms=500
    )
    assert ok_wrong is False

    # Generic remaster when year requested -> allowed with ordering penalty so exact year ranks #1
    ok_gen, pen_gen, _ = evaluate_version_compatibility(
        "2011 Remaster", "Remastered", context="download", duration_delta_ms=500
    )
    assert ok_gen is True and pen_gen > 0.0

    # Unlabeled candidate when year requested -> allowed in download with ordering penalty
    ok_unlab, pen_unlab, _ = evaluate_version_compatibility(
        "2011 Remaster", None, context="download", duration_delta_ms=500
    )
    assert ok_unlab is True and pen_unlab > pen_gen

    # Original requested vs Remaster -> rejected in download, allowed ONLY in download_remaster_fallback
    ok_orig_dl, _, _ = evaluate_version_compatibility(
        None, "2011 Remaster", context="download", duration_delta_ms=500
    )
    assert ok_orig_dl is False
    ok_orig_fb, _, _ = evaluate_version_compatibility(
        None, "2011 Remaster", context="download_remaster_fallback", duration_delta_ms=500
    )
    assert ok_orig_fb is True


def test_multidisc_folder_parsing_preserves_artist_and_album():
    parser = TrackParser()
    parsed = parser.parse_filename("Music/Pink Floyd/The Wall/CD 1/01 - In the Flesh.flac")
    assert parsed is not None
    assert parsed.artist_name.lower() == "pink floyd"
    assert parsed.album_title.lower() == "the wall"
    assert "in the flesh" in parsed.title.lower()


def test_enrich_candidate_metadata_preserves_remix_and_folder_remaster():
    dm = object.__new__(DownloadManager)
    cand_remix = EchosyncTrack(
        raw_title="Coldplay - Hymn for the Weekend (Seeb Remix).flac",
        title="Coldplay - Hymn for the Weekend (Seeb Remix).flac",
        artist_name="Unknown Artist",
        media=[EchosyncMedia(file_path="Music/Coldplay/Single/Coldplay - Hymn for the Weekend (Seeb Remix).flac")],
    )
    enriched = dm._enrich_candidate_metadata(cand_remix)
    assert enriched.edition and "seeb" in enriched.edition.lower()

    cand_folder_remaster = EchosyncTrack(
        raw_title="01 - Comfortably Numb.flac",
        title="01 - Comfortably Numb.flac",
        artist_name="Unknown Artist",
        media=[EchosyncMedia(file_path="Music/Pink Floyd/The Wall [2011 Remaster]/CD 2/01 - Comfortably Numb.flac")],
    )
    enriched_rem = dm._enrich_candidate_metadata(cand_folder_remaster)
    assert enriched_rem.artist_name.lower() == "pink floyd"
    assert (enriched_rem.edition and "2011" in enriched_rem.edition) or (
        enriched_rem.version and "2011" in enriched_rem.version
    )


def test_prefilter_normalized_tokens_and_lossless_floors():
    # Normalized token matching: apostrophes, underscores, diacritics
    raw_underscore = {
        "filename": "Music\\Queen\\01_Dont_Stop_Me_Now.flac",
        "size": 25_000_000,
        "length": 210,
    }
    assert _is_raw_file_eligible(
        raw_underscore,
        basic_filters={"allowed_extensions": ["flac"], "filter_expression": "don't stop me now"},
    )

    raw_accent = {
        "filename": "Music\\Beyoncé\\01 - Déjà Vu.flac",
        "size": 25_000_000,
        "length": 240,
    }
    assert _is_raw_file_eligible(
        raw_accent,
        basic_filters={"allowed_extensions": ["flac"], "filter_expression": "deja vu"},
        includes=["beyonce"],
    )

    # Quiet acoustic FLAC (~320 kbps = 40,000 B/s) passes new 250 kbps floor
    quiet_flac = {"filename": "Piano.flac", "size": 40_000 * 180, "length": 180}
    profile = {"formats": [{"type": "flac", "priority": 1}, {"type": "wav", "priority": 2}]}
    assert _is_raw_file_eligible(quiet_flac, quality_profile=profile) is True

    # Fake tiny FLAC (~128 kbps = 16,000 B/s) rejected
    fake_flac = {"filename": "Fake.flac", "size": 16_000 * 180, "length": 180}
    assert _is_raw_file_eligible(fake_flac, quality_profile=profile) is False

    # Fake truncated WAV (~320 kbps = 40,000 B/s < 85,000 B/s PCM floor) rejected
    fake_wav = {"filename": "Fake.wav", "size": 40_000 * 180, "length": 180}
    assert _is_raw_file_eligible(fake_wav, quality_profile=profile) is False


def test_quality_profile_fallback_dag_validation():
    # Valid 1-hop fallback
    ok, err = ConfigDatabase.validate_quality_profiles_fallback_dag(
        [
            {"id": "lossless", "name": "Lossless", "fallback_profile_id": "mp3"},
            {"id": "mp3", "name": "MP3 320", "fallback_profile_id": None},
        ]
    )
    assert ok is True and err is None

    # Invalid 2-hop chain (mp3 is already fallback for lossless, so mp3 cannot name another fallback)
    ok_chain, err_chain = ConfigDatabase.validate_quality_profiles_fallback_dag(
        [
            {"id": "lossless", "name": "Lossless", "fallback_profile_id": "mp3"},
            {"id": "mp3", "name": "MP3 320", "fallback_profile_id": "ogg"},
            {"id": "ogg", "name": "OGG", "fallback_profile_id": None},
        ]
    )
    assert ok_chain is False and "already used as a fallback" in (err_chain or "")

    # Invalid self-reference
    ok_self, _ = ConfigDatabase.validate_quality_profiles_fallback_dag(
        [{"id": "lossless", "name": "Lossless", "fallback_profile_id": "lossless"}]
    )
    assert ok_self is False


@pytest.mark.asyncio
async def test_dual_profile_single_pass_fallback_promotion():
    dm = object.__new__(DownloadManager)
    dm._deduplicate_candidates = lambda cands: cands
    dm._enrich_candidate_metadata = lambda c: c
    dm._remaster_fallback_ids = set()
    dm._transfer_progress_tracker = {}

    target = EchosyncTrack(
        raw_title="Rare Song",
        title="Rare Song",
        artist_name="Indie Artist",
        album_title="Indie Album",
        duration_ms=200000,
    )
    queued_download = SimpleNamespace(echo_sync_track=target.to_dict())

    class FakeSession:
        def query(self, _model):
            return SimpleNamespace(get=lambda _id: queued_download)

    class FakeScope:
        def __enter__(self):
            return FakeSession()

        def __exit__(self, *args):
            return False

    dm.work_db = SimpleNamespace(session_scope=lambda: FakeScope())
    dm._track_exists_in_library = lambda *a, **kw: False

    preferred_prof = {"id": "flac_only", "name": "FLAC", "formats": [{"type": "flac", "priority": 1}], "fallback_profile_id": "mp3_fb"}
    fallback_prof = {"id": "mp3_fb", "name": "MP3", "formats": [{"type": "mp3", "priority": 1}]}
    dm._get_quality_profile = lambda _pid: preferred_prof
    dm._get_fallback_quality_profile = lambda _p: fallback_prof
    dm._generate_search_strategies = lambda track, tol: [
        {"query": "Indie Artist Rare Song", "duration_tolerance_ms": tol, "name": "artist+title"},
        {"query": "Indie Album Rare Song", "duration_tolerance_ms": tol, "name": "album+title"},
    ]

    mp3_cand = EchosyncTrack(
        raw_title="Rare Song",
        title="Rare Song",
        artist_name="Indie Artist",
        album_title="Indie Album",
        duration_ms=200000,
        media=[EchosyncMedia(file_format="mp3", bitrate=320, file_size_bytes=8_000_000)],
        identifiers={
            "username": "peer_mp3",
            "plugin_item_id": "Indie Artist - Rare Song.mp3",
            "provider_item_id": "Indie Artist - Rare Song.mp3",
            "size": 8_000_000,
            "bitrate": 320,
            "free_upload_slots": 1,
        },
    )

    search_calls = []

    async def fake_search(provider, query, strategy_filters, quality_profile, **kwargs):
        search_calls.append(query)
        # Strategy 1 returns MP3 only; must NOT short-circuit before Strategy 2 hunts for FLAC
        return ([mp3_cand], False) if len(search_calls) == 1 else ([], False)

    dm._invoke_provider_search = fake_search
    dm._update_status = lambda *a, **kw: None
    dm.transition_to_searching = lambda _id: True

    started = []

    class Provider:
        name = "slskd"
        plugin_id = 12345

        async def _async_download(self, username, filename, size):
            started.append((username, filename, size))
            return f"{username}|{filename}"

    await dm._execute_waterfall_search_and_download(99, [Provider()])
    # Both strategies ran (didn't short-circuit on MP3), then promoted MP3 from memory with 0 extra searches
    assert len(search_calls) == 2
    assert started == [("peer_mp3", "Indie Artist - Rare Song.mp3", 8_000_000)]
    # Compact diagnostics persisted with strategy funnel + top_candidates
    diag = queued_download.echo_sync_track.get("_diagnostics")
    assert diag is not None
    assert len(diag["strategy_funnel"]) == 2
    assert diag["top_candidates"][0]["pool"] == "fallback_profile"


@pytest.mark.asyncio
async def test_slskd_list_transfer_api_status_and_cancel():
    """Verify real slskd REST API v0 list payload is parsed for Completed, Errored & Completed, Succeeded."""
    from unittest.mock import patch
    from plugins.EchoSync.slskd.client import SlskdProvider

    provider = SlskdProvider()
    provider.base_url = "http://localhost:5030"

    real_slskd_list_payload = [
        {
            "username": "Vaelin",
            "directories": [
                {
                    "directory": "@@ihwjx\\Music Library\\Skillet\\2009 - Awake (Deluxe Edition)",
                    "files": [
                        {
                            "id": "uuid-err-1",
                            "filename": "@@ihwjx\\Music Library\\Skillet\\2009 - Awake (Deluxe Edition)\\04. Awake And Alive.flac",
                            "state": "Completed, Errored",
                            "percentComplete": 0,
                            "size": 28730982,
                            "averageSpeed": 0,
                        }
                    ],
                }
            ],
        },
        {
            "username": "beeer",
            "directories": [
                {
                    "directory": "music\\Kate Bush\\Kate Bush - Hounds of Love (1985)",
                    "files": [
                        {
                            "id": "uuid-ok-2",
                            "filename": "music\\Kate Bush\\Kate Bush - Hounds of Love (1985)\\01 - Running Up That Hill (A Deal with God).flac",
                            "state": "Completed, Succeeded",
                            "percentComplete": 100,
                            "size": 37539020,
                            "averageSpeed": 1200000,
                        }
                    ],
                }
            ],
        },
    ]

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = real_slskd_list_payload

        st_err = await provider._async_get_download_status(
            "Vaelin|@@ihwjx\\Music Library\\Skillet\\2009 - Awake (Deluxe Edition)\\04. Awake And Alive.flac"
        )
        assert st_err is not None
        assert st_err["status"] == "failed"

        st_ok = await provider._async_get_download_status(
            "beeer|music\\Kate Bush\\Kate Bush - Hounds of Love (1985)\\01 - Running Up That Hill (A Deal with God).flac"
        )
        assert st_ok is not None
        assert st_ok["status"] == "complete"
        assert st_ok["speed"] == 1200000

        cancelled = await provider._async_cancel_download(
            "Vaelin|@@ihwjx\\Music Library\\Skillet\\2009 - Awake (Deluxe Edition)\\04. Awake And Alive.flac"
        )
        assert cancelled is True
        mock_req.assert_any_call("DELETE", "transfers/downloads/Vaelin/uuid-err-1")


def test_exact_sync_remaster_fallback_prefers_original_and_falls_back_when_absent(monkeypatch):
    """ExactSync matches a local Remaster via tier3_fallback when Original is absent,
    always prefers Original when present, and rejects wrong remaster years."""
    from unittest.mock import MagicMock
    from services import playlist_sync as ps

    # Stub DB engine so _fetch_candidates_tier1 returns our controlled rows
    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, *args, **kwargs):
            m = MagicMock()
            m.fetchall.return_value = []
            return m

    class _FakeEngine:
        def connect(self):
            return _FakeConn()

    fake_db = MagicMock()
    fake_db.engine = _FakeEngine()

    # Row tuple: (id, title, duration_ms, edition, artist, artist_id, sort_title, album, media_path, sync_id)
    remaster_row = (
        101,
        "Bohemian Rhapsody (2011 Remaster)",
        355000,
        "2011 Remaster",
        "Queen",
        1,
        "bohemian rhapsody",
        "A Night at the Opera",
        "/library/Queen/Bohemian Rhapsody (2011 Remaster).flac",
        "sync-101",
    )
    original_row = (
        102,
        "Bohemian Rhapsody",
        355000,
        None,
        "Queen",
        1,
        "bohemian rhapsody",
        "A Night at the Opera",
        "/library/Queen/Bohemian Rhapsody.flac",
        "sync-102",
    )
    wrong_year_row = (
        103,
        "Bohemian Rhapsody (2009 Remaster)",
        355000,
        "2009 Remaster",
        "Queen",
        1,
        "bohemian rhapsody",
        "A Night at the Opera",
        "/library/Queen/Bohemian Rhapsody (2009 Remaster).flac",
        "sync-103",
    )

    # Case 1: Only Remaster exists in library, Original requested -> matches via tier3_fallback
    monkeypatch.setattr(ps, "_fetch_candidates_tier1", lambda *a, **k: [remaster_row])
    monkeypatch.setattr(ps, "_fetch_candidates_tier2", lambda *a, **k: [])
    trace1 = ps.evaluate_single_track_diagnostics(
        title="Bohemian Rhapsody",
        artist="Queen",
        duration_ms=355000,
        album="A Night at the Opera",
        db=fake_db,
    )
    assert trace1["best_match"] is not None
    assert trace1["best_match"]["track_id"] == 101
    assert trace1["best_match"]["accepted"] is True
    assert trace1["best_match"]["fallback_tier"] == "tier3_fallback"
    assert trace1["best_match"]["matched_via_remaster_fallback"] is True

    # Case 2: Both Original and Remaster exist -> Original wins in primary pass (no tier3 fallback)
    monkeypatch.setattr(ps, "_fetch_candidates_tier1", lambda *a, **k: [remaster_row, original_row])
    trace2 = ps.evaluate_single_track_diagnostics(
        title="Bohemian Rhapsody",
        artist="Queen",
        duration_ms=355000,
        album="A Night at the Opera",
        db=fake_db,
    )
    assert trace2["best_match"] is not None
    assert trace2["best_match"]["track_id"] == 102
    assert trace2["best_match"].get("fallback_tier") is None

    # Case 3: 2011 Remaster requested, only 2009 Remaster in library -> strictly rejected
    monkeypatch.setattr(ps, "_fetch_candidates_tier1", lambda *a, **k: [wrong_year_row])
    trace3 = ps.evaluate_single_track_diagnostics(
        title="Bohemian Rhapsody (2011 Remaster)",
        artist="Queen",
        duration_ms=355000,
        album="A Night at the Opera",
        db=fake_db,
    )
    assert trace3["best_match"] is None


@pytest.mark.asyncio
async def test_reclaim_orphaned_searching_and_safe_failure_dispatch(tmp_path):
    """Orphaned SEARCHING rows are reclaimed to QUEUED without touching DOWNLOADING or live searches,
    and _handle_active_download_failure awaits backup dispatch instead of fire-and-forget create_task."""
    from unittest.mock import AsyncMock, MagicMock
    from database.working_database import WorkingDatabase, WorkingBase
    from core.database.models.working import DownloadQueue, DownloadStatus
    from services.download_manager import DownloadManager

    wdb = WorkingDatabase(str(tmp_path / "working.db"))
    WorkingBase.metadata.create_all(wdb.engine)
    dm = object.__new__(DownloadManager)
    dm.work_db = wdb
    dm._active_search_ids = set()
    dm._transfer_progress_tracker = {}
    dm._repo_instance = None

    with wdb.session_scope() as s:
        orphan = DownloadQueue(
            status=DownloadStatus.SEARCHING.value,
            echo_sync_track={"title": "Orphan", "artist_name": "A"},
        )
        live_search = DownloadQueue(
            status=DownloadStatus.SEARCHING.value,
            echo_sync_track={"title": "Live", "artist_name": "B"},
        )
        downloading = DownloadQueue(
            status=DownloadStatus.DOWNLOADING.value,
            provider_id="peer|file.flac",
            echo_sync_track={"title": "ActiveDL", "artist_name": "C"},
        )
        s.add_all([orphan, live_search, downloading])
        s.flush()
        orphan_id, live_id, dl_id = orphan.id, live_search.id, downloading.id

    dm._active_search_ids.add(live_id)
    reclaimed = dm._reclaim_orphaned_searching_items()
    assert reclaimed == 1

    with wdb.session_scope() as s:
        assert s.get(DownloadQueue, orphan_id).status == DownloadStatus.QUEUED.value
        assert s.get(DownloadQueue, live_id).status == DownloadStatus.SEARCHING.value
        assert s.get(DownloadQueue, dl_id).status == DownloadStatus.DOWNLOADING.value

    # Verify _handle_active_download_failure awaits _dispatch_candidate when a backup exists
    with wdb.session_scope() as s:
        rot = DownloadQueue(
            status=DownloadStatus.DOWNLOADING.value,
            active_candidate_id="peer1|a.flac",
            provider_id="peer1|a.flac",
            candidate_stack=[{"id": "peer2|b.flac", "size": 25000000}],
            echo_sync_track={"title": "RotateMe", "artist_name": "D"},
        )
        s.add(rot)
        s.flush()
        rot_id = rot.id

    dm._cancel_transfer_async = AsyncMock()
    dm._dispatch_candidate = AsyncMock()
    dm.process_single_download = MagicMock()

    await dm._handle_active_download_failure(
        rot_id, "peer1|a.flac", [], [], reason="TRANSFER_FAILED"
    )
    dm._dispatch_candidate.assert_awaited_once()
    dm.process_single_download.assert_not_called()


def test_webhook_secret_persists_universally_across_reregistrations(tmp_path, monkeypatch):
    """Webhook secrets must persist in config.db and never re-roll on restart/update."""
    from database.config_database import ConfigDatabase
    from core.nexus_framework.sdk import facades

    cdb = ConfigDatabase(str(tmp_path / "config.db"))
    monkeypatch.setattr("database.config_database.get_config_database", lambda: cdb)
    facades._REGISTERED_WEBHOOKS.clear()

    wh = facades._WebhooksSDKFacade(caller_namespace="EchoSync.slskd")
    reg1 = wh.register_endpoint("download_status", allow_unauthenticated=False)
    secret1 = reg1["secret"]
    assert secret1.startswith("sk_live_")

    # Simulate restart / hot-swap by wiping in-memory registry
    facades._REGISTERED_WEBHOOKS.clear()
    reg2 = wh.register_endpoint("download_status", allow_unauthenticated=False)
    assert reg2["secret"] == secret1

    # Second plugin endpoint shares the same universal system.webhook_secret
    wh2 = facades._WebhooksSDKFacade(caller_namespace="EchoSync.other")
    reg3 = wh2.register_endpoint("events", allow_unauthenticated=False)
    assert reg3["secret"] == secret1


def test_track_imported_reconciles_failed_download_to_completed(tmp_path):
    """A FAILED DownloadQueue row transitions to COMPLETED when AutoImportService imports the track."""
    from database.working_database import WorkingDatabase, WorkingBase
    from core.database.models.working import DownloadQueue, DownloadStatus
    from services.download_manager import DownloadManager

    wdb = WorkingDatabase(str(tmp_path / "working.db"))
    WorkingBase.metadata.create_all(wdb.engine)
    dm = object.__new__(DownloadManager)
    dm.work_db = wdb
    dm._repo_instance = None

    with wdb.session_scope() as s:
        failed_item = DownloadQueue(
            status=DownloadStatus.FAILED.value,
            error_reason="NO_MATCHING_CANDIDATES",
            echo_sync_track={
                "title": "Gone, Gone, Gone",
                "artist_name": "Phillip Phillips",
                "duration_ms": 209000,
            },
        )
        s.add(failed_item)
        s.flush()
        fid = failed_item.id

    dm._on_track_imported(
        {
            "track": {
                "title": "Gone, Gone, Gone",
                "artist_name": "Phillip Phillips",
                "duration_ms": 210000,
            },
            "file_path": "/data/library/Phillip Phillips/03 - Gone, Gone, Gone.flac",
        }
    )

    with wdb.session_scope() as s:
        refreshed = s.get(DownloadQueue, fid)
        assert refreshed is not None
        assert refreshed.status == DownloadStatus.COMPLETED.value
        assert refreshed.error_reason is None
        tl = refreshed.echo_sync_track["_diagnostics"]["timeline"]
        assert any(ev["event"] == "IMPORTED_RECONCILED" for ev in tl)


def test_reconcile_verifying_items_completes_owned_and_fails_orphaned(tmp_path):
    """VERIFYING rows already in library flip to COMPLETED (100%, 0 KB/s), while
    orphaned >5m VERIFYING rows with missing files fail cleanly as VERIFICATION_ORPHANED."""
    from datetime import timedelta
    from database.working_database import WorkingDatabase, WorkingBase
    from core.database.models.working import DownloadQueue, DownloadStatus
    from services.download_manager import DownloadManager
    from time_utils import utc_now

    wdb = WorkingDatabase(str(tmp_path / "working.db"))
    WorkingBase.metadata.create_all(wdb.engine)
    dm = object.__new__(DownloadManager)
    dm.work_db = wdb
    dm._repo_instance = None
    dm._loop_task = None
    dm._active_search_ids = set()

    # Stub _track_exists_in_library: "Running Up That Hill" is in library, "Ghost Track" is not
    dm._track_exists_in_library = lambda artist, title, **kw: "running up that hill" in (title or "").lower()

    with wdb.session_scope() as s:
        owned = DownloadQueue(
            status=DownloadStatus.VERIFYING.value,
            echo_sync_track={
                "title": "Running Up That Hill (A Deal With God)",
                "artist_name": "Kate Bush",
                "current_speed": 803500.0,
                "progress_percent": 85.0,
            },
            updated_at=utc_now() - timedelta(minutes=2),
        )
        orphaned = DownloadQueue(
            status=DownloadStatus.VERIFYING.value,
            echo_sync_track={
                "title": "Ghost Track",
                "artist_name": "Nobody",
                "downloaded_file_path": str(tmp_path / "nonexistent.flac"),
                "current_speed": 500000.0,
                "progress_percent": 90.0,
            },
            updated_at=utc_now() - timedelta(minutes=6),
        )
        s.add_all([owned, orphaned])
        s.flush()
        owned_id, orphaned_id = owned.id, orphaned.id

    dm._reconcile_verifying_items()

    with wdb.session_scope() as s:
        r_owned = s.get(DownloadQueue, owned_id)
        assert r_owned.status == DownloadStatus.COMPLETED.value
        assert r_owned.echo_sync_track["progress_percent"] == 100.0
        assert r_owned.echo_sync_track["current_speed"] == 0.0

        r_orph = s.get(DownloadQueue, orphaned_id)
        assert r_orph.status == DownloadStatus.FAILED.value
        assert r_orph.error_reason == "VERIFICATION_ORPHANED"
        assert r_orph.echo_sync_track["current_speed"] == 0.0





