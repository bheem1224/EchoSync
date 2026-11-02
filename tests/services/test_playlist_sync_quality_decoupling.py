"""
Tests for Playlist Sync Quality Decoupling and Diagnostic Parity.

Verifies:
1. Decoupling target_quality from matching: An existing library track encoded in MP3
   is successfully matched and marked 'Found' even when target_quality="raw/lossless".
   Also verifies highest quality edition selection among multiple LocalMedia files.
2. Batch analysis results include populated match_diagnostics payload with evaluated
   candidates and component scores.
3. Diagnostic lookup parity: POST /api/v1/core/playlists/match-diagnostics returns
   the exact trace cached from the batch analysis run.
"""

import uuid
import pytest
from database.music_database import Artist, Base, LocalMedia, Track, close_database, get_database
from services.playlist_sync import (
    PlaylistSyncService,
    analyze_playlist,
    analyze_playlists,
    clear_match_trace_cache,
    get_cached_match_trace,
    select_highest_quality_media,
)
from web.routes.playlists import MatchDiagnosticRequest, match_diagnostics


@pytest.fixture
def test_sync_db(tmp_path, monkeypatch):
    """Create isolated SQLite test database and patch MusicDatabase."""
    close_database()
    clear_match_trace_cache()

    db_path = tmp_path / f"sync_test_{uuid.uuid4().hex[:8]}.db"
    test_db = get_database(str(db_path))
    Base.metadata.create_all(test_db.engine)

    monkeypatch.setattr("database.music_database.MusicDatabase", lambda *a, **kw: test_db)
    monkeypatch.setattr("web.routes.playlists.MusicDatabase", lambda *a, **kw: test_db)
    monkeypatch.setattr("services.playlist_sync.db_mod.MusicDatabase", lambda *a, **kw: test_db)

    yield test_db

    clear_match_trace_cache()
    close_database()


def test_playlist_sync_mp3_matches_when_target_lossless(test_sync_db, tmp_path):
    """
    Test A: An existing library track encoded in MP3 is successfully marked 'Found'
    during playlist sync even when target_quality='raw/lossless'.
    Also tests that highest-quality edition is selected when multiple files exist.
    """
    sync_id_mp3 = f"sync_{uuid.uuid4().hex[:12]}"
    sync_id_multi = f"sync_{uuid.uuid4().hex[:12]}"

    with test_sync_db.session_scope() as session:
        art = Artist(name="James Arthur")
        session.add(art)
        session.flush()

        # Track 1: MP3 only
        t1 = Track(
            title="Rewrite The Stars",
            artist_id=art.id,
            duration=218000,
            sync_id=sync_id_mp3,
        )
        session.add(t1)
        session.flush()

        m1 = LocalMedia(
            track_id=t1.id,
            file_path=str(tmp_path / "RewriteTheStars.mp3"),
            file_format="mp3",
            bitrate=320000,
            sample_rate=44100,
            bit_depth=16,
        )
        session.add(m1)

        # Track 2: Has both MP3 (128k) and FLAC (lossless)
        art2 = Artist(name="American Head Charge")
        session.add(art2)
        session.flush()

        t2 = Track(
            title="Just So You Know",
            artist_id=art2.id,
            duration=275000,
            sync_id=sync_id_multi,
        )
        session.add(t2)
        session.flush()

        m2_mp3 = LocalMedia(
            track_id=t2.id,
            file_path=str(tmp_path / "JustSoYouKnow_low.mp3"),
            file_format="mp3",
            bitrate=128000,
            sample_rate=44100,
            bit_depth=16,
        )
        m2_flac = LocalMedia(
            track_id=t2.id,
            file_path=str(tmp_path / "JustSoYouKnow_hi.flac"),
            file_format="flac",
            bitrate=950000,
            sample_rate=96000,
            bit_depth=24,
        )
        session.add_all([m2_mp3, m2_flac])
        session.flush()

        # Verify select_highest_quality_media selects FLAC over MP3
        best_media = select_highest_quality_media([m2_mp3, m2_flac])
        assert best_media.file_format == "flac"
        assert best_media.bit_depth == 24

    # Run playlist analysis with strict target_quality="raw/lossless"
    playlist_payload = {
        "id": "pl_test_1",
        "name": "Sync Test Playlist",
        "tracks": [
            {
                "id": "item_1",
                "title": "Rewrite The Stars",
                "artist": "James Arthur",
                "duration_ms": 218000,
                "album": "The Greatest Showman: Reimagined",
            },
            {
                "id": "item_2",
                "title": "Just So You Know",
                "artist": "American Head Charge",
                "duration_ms": 275000,
                "album": "The War of Art",
            },
        ],
    }

    result = analyze_playlist(
        playlist_name="Sync Test Playlist",
        tracks=playlist_payload["tracks"],
        target_quality="raw/lossless",
        db=test_sync_db,
    )

    assert result["summary"]["total_tracks"] == 2
    assert result["summary"]["found_in_library"] == 2
    assert result["summary"]["missing_tracks"] == 0
    assert len(result["missing"]) == 0

    tracks = result["tracks"]
    assert len(tracks) == 2

    # Track 1 (MP3 only) MUST be marked found even though target_quality is raw/lossless
    t1_res = next(t for t in tracks if t["title"] == "Rewrite The Stars")
    assert t1_res["status"] == "found"
    assert t1_res["library_match"].startswith("Found")
    assert t1_res["matched_track_id"] is not None

    # Track 2 (MP3 + FLAC) must be found and select the FLAC media as primary
    t2_res = next(t for t in tracks if t["title"] == "Just So You Know")
    assert t2_res["status"] == "found"
    assert t2_res["library_match"].startswith("Found")
    assert t2_res["primary_media_path"].endswith(".flac")


def test_batch_analysis_persists_match_diagnostics(test_sync_db, tmp_path):
    """
    Test B: Batch analysis results include the populated match_diagnostics payload
    with evaluated candidates and component scores clamped to [0.0, 100.0].
    """
    with test_sync_db.session_scope() as session:
        art = Artist(name="Imagine Dragons")
        session.add(art)
        session.flush()

        tr = Track(
            title="Radioactive",
            artist_id=art.id,
            duration=186000,
            sync_id=f"sync_{uuid.uuid4().hex[:12]}",
        )
        session.add(tr)
        session.flush()

        media = LocalMedia(
            track_id=tr.id,
            file_path=str(tmp_path / "Radioactive.mp3"),
            file_format="mp3",
        )
        session.add(media)
        session.flush()

    batch_res = analyze_playlists(
        source="spotify",
        target_source="plex",
        playlists=[
            {
                "id": "pl_batch",
                "name": "Batch Playlist",
                "tracks": [
                    {
                        "id": "item_rad",
                        "title": "Radioactive",
                        "artist": "Imagine Dragons",
                        "duration_ms": 186000,
                        "album": "Night Visions",
                    }
                ],
            }
        ],
        target_quality="raw/lossless",
        db=test_sync_db,
    )

    track_out = batch_res["tracks"][0]
    assert "match_diagnostics" in track_out
    diag = track_out["match_diagnostics"]

    # Verify query block
    assert diag["query"]["title"] == "Radioactive"
    assert diag["query"]["artist"] == "Imagine Dragons"
    assert diag["query"]["duration_ms"] == 186000
    assert diag["candidates_located_count"] >= 1

    # Verify candidates list and score clamping
    candidates = diag["evaluated_candidates"]
    assert len(candidates) >= 1
    winner = candidates[0]

    assert winner["title"] == "Radioactive"
    assert winner["artist"] == "Imagine Dragons"
    assert 0.0 <= winner["composite_score"] <= 100.0
    assert 0.0 <= winner["title_score"] <= 1.0
    assert 0.0 <= winner["artist_score"] <= 1.0
    assert winner["accepted"] is True

    # Verify best_match object
    assert diag["best_match"] is not None
    assert diag["best_match"]["title"] == "Radioactive"


def test_match_diagnostics_endpoint_returns_exact_cached_trace(test_sync_db, tmp_path):
    """
    Test C: POST /api/v1/core/playlists/match-diagnostics returns the exact trace
    cached from the batch run without divergence.
    """
    with test_sync_db.session_scope() as session:
        art = Artist(name="Coldplay")
        session.add(art)
        session.flush()

        tr = Track(
            title="Yellow",
            artist_id=art.id,
            duration=269000,
            sync_id=f"sync_{uuid.uuid4().hex[:12]}",
        )
        session.add(tr)
        session.flush()

        media = LocalMedia(
            track_id=tr.id,
            file_path=str(tmp_path / "Yellow.mp3"),
            file_format="mp3",
        )
        session.add(media)
        session.flush()

    # Step 1: Run batch analysis
    batch_res = analyze_playlists(
        source="spotify",
        target_source="plex",
        playlists=[
            {
                "id": "pl_coldplay",
                "name": "Coldplay Sync",
                "tracks": [
                    {
                        "id": "tr_yellow",
                        "title": "Yellow",
                        "artist": "Coldplay",
                        "duration_ms": 269000,
                        "album": "Parachutes",
                    }
                ],
            }
        ],
        target_quality="raw/lossless",
        db=test_sync_db,
    )

    batch_track = batch_res["tracks"][0]
    batch_trace = batch_track["match_diagnostics"]

    # Step 2: Query match-diagnostics API endpoint
    req = MatchDiagnosticRequest(
        title="Yellow",
        artist="Coldplay",
        duration_ms=269000,
        album="Parachutes",
    )
    endpoint_trace = match_diagnostics(req)

    # Step 3: Verify 100% diagnostic parity
    assert endpoint_trace["query"] == batch_trace["query"]
    assert endpoint_trace["candidates_located_count"] == batch_trace["candidates_located_count"]
    assert endpoint_trace["best_match"] == batch_trace["best_match"]
    assert endpoint_trace["evaluated_candidates"] == batch_trace["evaluated_candidates"]

