"""Tests for hyphen-delimited soundtrack subtitle sanitization,
duration score preservation on version mismatch veto, and dirty baseline
edition invalidation during AcoustID canonical resolution.
"""

from unittest.mock import MagicMock
from pathlib import Path
import pytest

import echosync_core
from core.db.echo_sync_track import EchosyncTrack
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import ExactSyncProfile
from core.matching_engine.track_parser import sanitize_soundtrack_title
from core.metadata.adapter import ResolutionAdapter
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest
from database.music_database import Album, Artist, Track


def test_test_a_soundtrack_hyphen_delimiter_and_colon_normalization():
    """Test A: Verify sanitize_soundtrack_title("Sunflower - Spider-Man: Into the Spider-Verse")
    returns ("Sunflower", "Spider-Man - Into the Spider-Verse").
    """
    input_title = "Sunflower - Spider-Man: Into the Spider-Verse"
    clean_title, film_provenance = sanitize_soundtrack_title(input_title)

    assert clean_title == "Sunflower"
    assert film_provenance == "Spider-Man - Into the Spider-Verse"


def test_test_b_duration_match_score_preserved_on_version_mismatch_veto():
    """Test B: Verify candidate evaluation returning version_match=False
    still retains duration_match_score == 1.0 when delta_t = 0s.
    """
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="Lovely",
        artist_name="Billie Eilish & Khalid",
        duration=200000,
    )
    candidate_remix = EchosyncTrack(
        raw_title="Lovely",
        artist_name="Billie Eilish & Khalid",
        edition="Remix",
        duration=200000,
    )

    result = engine.calculate_match(source, candidate_remix, context="sync")

    assert result.passed_version_check is False
    assert result.confidence_score == 0.0
    assert result.duration_match_score == 1.0


def test_test_c_baseline_remix_edition_invalidated_on_canonical_acoustid_match(monkeypatch, tmp_path):
    """Test C: Verify that an audio file named with (Remix) does not persist
    edition="Remix" when AcoustID matches the canonical soundtrack master.
    """
    audio_file = tmp_path / "01 - Sunflower (Remix).mp3"
    audio_file.write_bytes(b"dummy mp3 data for testing")
    file_dur_ms = 158000

    # Dirty physical tags and filename indicating a remix
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Sunflower (Remix)",
            "artist": "Post Malone & Swae Lee",
            "album": "Sunflower (Remix)",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_chromaprint = "A" * 80
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    canonical_recording = {
        "id": "mbid-sunflower-canonical",
        "title": "Sunflower",
        "artist": "Post Malone & Swae Lee",
        "album": "Spider-Man: Into the Spider-Verse",
        "year": 2018,
        "duration_ms": file_dur_ms,
        "isrc": "USUM71816090",
        "releases": [
            {
                "id": "rel-sunflower-1",
                "date": "2018-10-19",
                "release_group": {"id": "rg-sunflower-1", "title": "Spider-Man: Into the Spider-Verse", "primary_type": "Soundtrack"},
            }
        ],
        "release_group": {"id": "rg-sunflower-1", "title": "Spider-Man: Into the Spider-Verse", "primary_type": "Soundtrack"},
        "release_group_count": 10,
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = canonical_recording

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "aid-sunflower",
        "mbids": ["mbid-sunflower-canonical"],
        "recordings": [
            {
                "id": "mbid-sunflower-canonical",
                "title": "Sunflower",
                "artist": "Post Malone & Swae Lee",
                "score": 95,
                "duration": file_dur_ms / 1000.0,
            }
        ],
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_sunflower_test",
        file_path=audio_file,
        baseline_title="Sunflower (Remix)",
        baseline_artist="Post Malone & Swae Lee",
        duration_ms=file_dur_ms,
    )

    resolved = engine.resolve_track(req)

    assert resolved is not None
    assert resolved.title == "Sunflower"
    # Canonical master must invalidate the dirty "Remix" baseline tag
    assert resolved.edition != "Remix"

    # Verify adapter hydration into ORM Track entity also does not resurrect "Remix"
    adapter = ResolutionAdapter()
    session = MagicMock()
    artist_orm = Artist(name="Post Malone & Swae Lee", normalized_name="post malone & swae lee")
    album_orm = Album(title="Sunflower (Remix)", artist=artist_orm)
    track_orm = Track(title="Sunflower (Remix)", artist=artist_orm, album=album_orm, edition="Remix")

    updated_track = adapter.hydrate_track(resolved, session, track_orm)
    assert updated_track.title == "Sunflower"
    assert updated_track.edition != "Remix"

