"""Tests for Playlist Matching Diagnostics API endpoint.

Verifies:
1. Endpoint registration across canonical route prefixes (/api/v1/core/playlists, /api/v1/playlists, /api/playlists).
2. Diagnostic match trace schema for unmatched tracks (non-existing).
3. Detailed component score breakdown for candidates (title, artist, duration, album, penalties, composite).
4. Correct best_match determination and winning threshold comparison.
"""

import uuid
from unittest.mock import MagicMock
import pytest
from database.music_database import Artist, Base, LocalMedia, Track, close_database, get_database
from web.routes.playlists import (
    MatchDiagnosticRequest,
    api_v1_router,
    legacy_router,
    match_diagnostics,
    router,
)


def test_match_diagnostics_route_registration():
    """Verify endpoint is mounted across all canonical router prefixes."""
    router_paths = [r.path for r in router.routes]
    api_v1_paths = [r.path for r in api_v1_router.routes]
    legacy_paths = [r.path for r in legacy_router.routes]

    assert any("match-diagnostics" in p for p in router_paths), f"match-diagnostics missing in router: {router_paths}"
    assert any("match-diagnostics" in p for p in api_v1_paths), f"match-diagnostics missing in api_v1_router: {api_v1_paths}"
    assert any("match-diagnostics" in p for p in legacy_paths), f"match-diagnostics missing in legacy_router: {legacy_paths}"


def test_match_diagnostics_non_existing_track():
    """Verify diagnostics on a track with no candidate hits in database."""
    req = MatchDiagnosticRequest(
        title="Nonexistent Track 99999",
        artist="Unknown Ghost Artist",
        duration_ms=195000,
        album="Ghost Album",
    )

    trace = match_diagnostics(req)

    assert isinstance(trace, dict)
    assert trace["query"]["title"] == "Nonexistent Track 99999"
    assert trace["query"]["artist"] == "Unknown Ghost Artist"
    assert trace["query"]["duration_ms"] == 195000
    assert trace["candidates_retrieved_count"] == 0
    assert trace["candidates"] == []
    assert trace["best_match"] is None
    assert trace["winning_threshold"] == 85.0


def test_match_diagnostics_existing_candidate_breakdown(tmp_path, monkeypatch):
    """Verify full candidate component scoring breakdown for an existing track."""
    close_database()
    db_path = tmp_path / f"diagnostics_test_{uuid.uuid4().hex[:8]}.db"
    test_db = get_database(str(db_path))
    Base.metadata.create_all(test_db.engine)

    # Monkeypatch MusicDatabase to use test_db
    monkeypatch.setattr("database.music_database.MusicDatabase", lambda *a, **kw: test_db)
    monkeypatch.setattr("web.routes.playlists.MusicDatabase", lambda *a, **kw: test_db)

    test_sync_id = f"sync_{uuid.uuid4().hex[:12]}"

    # Seed an artist and track
    with test_db.session_scope() as session:
        art = Artist(name="Dua Lipa")
        session.add(art)
        session.flush()

        track = Track(
            title="Levitating",
            artist_id=art.id,
            duration=203000,
            sync_id=test_sync_id,
            edition=None,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            file_path=str(tmp_path / f"Levitating_{uuid.uuid4().hex[:6]}.flac"),
            file_format="flac",
        )
        session.add(media)
        session.flush()

    req = MatchDiagnosticRequest(
        title="Levitating",
        artist="Dua Lipa",
        duration_ms=203000,
        album="Future Nostalgia",
    )

    trace = match_diagnostics(req)

    assert trace["candidates_retrieved_count"] >= 1
    assert len(trace["candidates"]) >= 1

    cand = trace["candidates"][0]
    assert cand["title"] == "Levitating"
    assert cand["artist"] == "Dua Lipa"
    assert cand["track_sync_id"] == test_sync_id
    assert cand["duration_delta_sec"] == 0.0
    assert cand["title_score"] == 1.0
    assert cand["artist_score"] == 1.0
    assert cand["duration_score"] == 1.0
    assert cand["composite_score"] >= 90.0
    assert cand["accepted"] is True
    assert cand["rejection_reason"] is None

    assert trace["best_match"] is not None
    assert trace["best_match"]["track_sync_id"] == test_sync_id

    close_database()
