"""Unit tests for soundtrack title sanitization (hyphen cues, colon normalization,
and album keyword independence) and baseline remix edition purging during AcoustID
canonical master resolution.
"""

from unittest.mock import MagicMock
from pathlib import Path
import pytest

import echosync_core
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.track_parser import sanitize_soundtrack_title
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest


def test_soundtrack_hyphen_sanitization_without_album_gate():
    """Verify sanitize_soundtrack_title("Sunflower - Spider-Man: Into the Spider-Verse")
    returns ("Sunflower", "Spider-Man - Into the Spider-Verse") even when album="Sunflower".
    """
    clean_title, film_provenance = sanitize_soundtrack_title(
        "Sunflower - Spider-Man: Into the Spider-Verse",
        album="Sunflower",
    )
    assert clean_title == "Sunflower"
    assert film_provenance == "Spider-Man - Into the Spider-Verse"


def test_baseline_remix_edition_cleared_to_film_edition_on_canonical_acoustid_match(monkeypatch, tmp_path):
    """Verify that a file tagged with edition="Remix" has its edition cleared to
    "Spider-Man - Into the Spider-Verse Edition" (not "Remix") when AcoustID matches the canonical track.
    """
    audio_file = tmp_path / "01 - Sunflower (Remix).mp3"
    audio_file.write_bytes(b"dummy mp3 data for testing")
    file_dur_ms = 158000

    # Dirty physical tags indicating a remix edition
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Sunflower (Remix)",
            "artist": "Post Malone & Swae Lee",
            "album": "Sunflower (Remix)",
            "edition": "Remix",
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
                "release_group": {
                    "id": "rg-sunflower-1",
                    "title": "Spider-Man: Into the Spider-Verse",
                    "primary_type": "Soundtrack",
                },
            }
        ],
        "release_group": {
            "id": "rg-sunflower-1",
            "title": "Spider-Man: Into the Spider-Verse",
            "primary_type": "Soundtrack",
        },
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
        media_id="media_sunflower_edition_test",
        file_path=audio_file,
        baseline_title="Sunflower (Remix)",
        baseline_artist="Post Malone & Swae Lee",
        baseline_album="Sunflower (Remix)",
        duration_ms=file_dur_ms,
    )

    resolved = engine.resolve_track(req)

    assert resolved is not None
    assert resolved.title == "Sunflower"
    # Contaminated baseline edition="Remix" purged, replaced with canonical film edition
    assert resolved.edition == "Spider-Man - Into the Spider-Verse Edition"
    assert resolved.edition != "Remix"

