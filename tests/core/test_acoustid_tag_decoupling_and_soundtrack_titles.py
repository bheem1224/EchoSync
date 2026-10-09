"""Tests for AcoustID candidate arbitration untrusted tag decoupling,
deterministic multi-key tie-breaking, and soundtrack title sanitization.
"""

from unittest.mock import MagicMock
from pathlib import Path
import pytest

import echosync_core
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.track_parser import sanitize_soundtrack_title
from core.metadata.adapter import ResolutionAdapter
from core.metadata.engine import MetadataResolutionEngine, _create_resolved_track
from core.metadata.schemas import ResolutionRequest
from core.db.echo_sync_track import EchosyncTrack
from database.music_database import Album, Artist, Track


def test_test_a_acoustid_tag_decoupling_selects_canonical_original_over_unverified_cover(monkeypatch, tmp_path):
    """Test A: File tagged with Da Tweekaz and ISRC NLH2L1800070 with filename
    02 - Bring Me to Life.flac correctly selects Evanescence (2003) over
    Da Tweekaz (2018) when Stage 0 is unverified.
    """
    audio_file = tmp_path / "02 - Bring Me to Life.flac"
    audio_file.write_bytes(b"dummy flac data for testing")

    file_dur_ms = 237000

    # Physical tags have corrupted / unverified Da Tweekaz metadata and ISRC
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Bring Me to Life",
            "artist": "Da Tweekaz",
            "isrc": "NLH2L1800070",
            "musicbrainz_id": "mbid-da-tweekaz",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_chromaprint = "C" * 80
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    cand_da_tweekaz = {
        "id": "mbid-da-tweekaz",
        "title": "Bring Me to Life",
        "artist": "Da Tweekaz",
        "album": "Bring Me to Life (Single)",
        "year": 2018,
        "release_year": 2018,
        "date": "2018",
        "duration_ms": file_dur_ms,
        "isrc": "NLH2L1800070",
        "isrcs": ["NLH2L1800070"],
        "releases": [
            {"id": "rel-tweekaz-1", "date": "2018", "release_group": {"id": "rg-tweekaz-1", "primary_type": "Single"}}
        ],
        "release_group": {"id": "rg-tweekaz-1", "title": "Bring Me to Life", "primary_type": "Single"},
        "release_group_count": 1,
    }

    cand_evanescence = {
        "id": "mbid-evanescence",
        "title": "Bring Me to Life",
        "artist": "Evanescence",
        "album": "Fallen",
        "year": 2003,
        "release_year": 2003,
        "date": "2003-03-04",
        "duration_ms": file_dur_ms,
        "isrc": "USWU30300001",
        "isrcs": ["USWU30300001"],
        "releases": [
            {"id": f"rel-ev-{i}", "date": "2003", "release_group": {"id": f"rg-ev-{i % 3}", "primary_type": "Album"}}
            for i in range(25)
        ],
        "release_group": {"id": "rg-ev-0", "title": "Fallen", "primary_type": "Album"},
        "release_group_count": 25,
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.side_effect = lambda mbid: (
        cand_da_tweekaz if mbid == "mbid-da-tweekaz"
        else cand_evanescence if mbid == "mbid-evanescence"
        else None
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "aid-bmtl",
        "mbids": ["mbid-da-tweekaz", "mbid-evanescence"],
        "recordings": [
            {
                "id": "mbid-da-tweekaz",
                "title": "Bring Me to Life",
                "artist": "Da Tweekaz",
                "score": 96,
                "duration": file_dur_ms / 1000.0,
            },
            {
                "id": "mbid-evanescence",
                "title": "Bring Me to Life",
                "artist": "Evanescence",
                "score": 96,
                "duration": file_dur_ms / 1000.0,
            },
        ],
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_a",
        file_path=audio_file,
        baseline_title="Bring Me to Life",
        baseline_artist="Da Tweekaz",
        baseline_isrc="NLH2L1800070",
        duration_ms=file_dur_ms,
    )

    result = engine.resolve_track(req)

    # Invariant: Corrupted physical tags must not poison candidate arbitration.
    # Da Tweekaz (2018) must not receive exact-match ISRC bonus or tag artist advantage.
    # Evanescence (2003) must win decisively.
    assert result is not None
    assert result.artist_name == "Evanescence"
    assert result.musicbrainz_id == "mbid-evanescence"
    assert result.title == "Bring Me to Life"


def test_test_b_soundtrack_title_sanitization_and_album_routing():
    """Test B: Title Sunflower (Spider-Man: Into the Spider-Verse) with album Sunflower
    sanitizes to title Sunflower and album Spider-Man: Into the Spider-Verse (Soundtrack).
    """
    raw_title = "Sunflower (Spider-Man: Into the Spider-Verse)"
    raw_album = "Sunflower"

    clean_title, extracted_film = sanitize_soundtrack_title(raw_title, album=raw_album)
    assert clean_title == "Sunflower"
    assert extracted_film == "Spider-Man: Into the Spider-Verse"

    # Route through _create_resolved_track
    track = _create_resolved_track(
        title=raw_title,
        album=raw_album,
        artist="Post Malone & Swae Lee",
    )
    assert track.title == "Sunflower"
    assert track.album_title == "Spider-Man: Into the Spider-Verse (Soundtrack)"

    # Route through ResolutionAdapter.hydrate_track
    adapter = ResolutionAdapter()
    session = MagicMock()
    artist = Artist(name="Post Malone", normalized_name="post malone")
    album_orm = Album(title="Sunflower", artist=artist)
    track_orm = Track(title="Sunflower (Spider-Man: Into the Spider-Verse)", artist=artist, album=album_orm)

    res_model = EchosyncTrack(
        raw_title=raw_title,
        artist_name="Post Malone & Swae Lee",
        album_title=raw_album,
    )
    updated = adapter.hydrate_track(res_model, session, track_orm)
    assert updated.title == "Sunflower"


def test_test_c_version_titles_preserved_without_film_extraction():
    """Test C: Version titles like Song (Acoustic) or Track (Remix) remain
    untouched with extracted_film = None.
    """
    version_titles = [
        "Song (Acoustic)",
        "Track (Remix)",
        "Song (Live)",
        "Music (Instrumental)",
        "Audio (Deluxe)",
        "Title (Club Mix)",
        "Song (Radio Edit)",
        "Track (Original Mix)",
    ]

    for vt in version_titles:
        clean_t, extracted_film = sanitize_soundtrack_title(vt)
        assert clean_t == vt, f"Expected '{vt}' to remain untouched, got '{clean_t}'"
        assert extracted_film is None, f"Expected extracted_film to be None for '{vt}', got '{extracted_film}'"
