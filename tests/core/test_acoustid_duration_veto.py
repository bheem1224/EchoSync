"""Unit and integration tests for dynamic similarity-weighted AcoustID duration veto (Step D).

Verifies:
1. compute_dynamic_duration_threshold unit rules and normalization.
2. Candidate with delta=3.8s and acoustic similarity >= 0.95 passes Step D.
3. Candidate with delta=3.8s and acoustic similarity <= 0.80 is dropped by Step D.
4. Candidate with delta=2.07s (e.g. silence padding) passes when similarity is sufficient.
5. Standard resolution and [acoustid-isolated] paths both honor dynamic duration threshold.
"""

from unittest.mock import MagicMock
import pytest

import echosync_core
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.metadata.engine import (
    MetadataResolutionEngine,
    compute_dynamic_duration_threshold,
)
from core.metadata.schemas import ResolutionRequest


def test_compute_dynamic_duration_threshold_unit():
    """Verify dynamic duration threshold boundary and lerp calculations."""
    # Low similarity (<= 0.80) -> 2.0s
    assert compute_dynamic_duration_threshold(0.0) == 2.0
    assert compute_dynamic_duration_threshold(0.50) == 2.0
    assert compute_dynamic_duration_threshold(0.80) == 2.0
    assert compute_dynamic_duration_threshold(80.0) == 2.0  # 0-100 scale

    # High similarity (>= 0.95) -> 5.0s
    assert compute_dynamic_duration_threshold(0.95) == 5.0
    assert compute_dynamic_duration_threshold(0.99) == 5.0
    assert compute_dynamic_duration_threshold(1.0) == 5.0
    assert compute_dynamic_duration_threshold(95.0) == 5.0
    assert compute_dynamic_duration_threshold(100.0) == 5.0

    # Lerp region between 0.80 and 0.95: progress = (sim - 0.80) / 0.15, threshold = 2.0 + (progress * 3.0)
    # Midpoint at 0.875 -> progress 0.5 -> 2.0 + 1.5 = 3.5s
    assert pytest.approx(compute_dynamic_duration_threshold(0.875), 0.001) == 3.5
    # At 0.85 -> progress 1/3 -> 2.0 + 1.0 = 3.0s
    assert pytest.approx(compute_dynamic_duration_threshold(0.85), 0.001) == 3.0
    # At 0.90 -> progress 2/3 -> 2.0 + 2.0 = 4.0s
    assert pytest.approx(compute_dynamic_duration_threshold(0.90), 0.001) == 4.0


def test_acoustid_candidate_with_3_8s_delta_passes_when_high_similarity(monkeypatch, tmp_path):
    """Candidate with delta=3.8s passes Step D when acoustic similarity is >= 0.95."""
    audio_file = tmp_path / "Dancing Queen.mp3"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 230000  # 230.0s (3m 50s)
    cand_dur_ms = 233800  # 233.8s (3.8s delta)

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Dancing Queen",
            "artist": "ABBA",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_fp = "C" * 80
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_fp, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-abba-1",
        "score": 0.96,  # 96% similarity -> dynamic threshold = 5.0s
        "recordings": [
            {
                "id": "mbid-abba-dancing-queen",
                "title": "Dancing Queen",
                "artist": "ABBA",
                "duration": cand_dur_ms / 1000.0,
                "score": 0.96,
            }
        ],
        "mbids": ["mbid-abba-dancing-queen"],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = {
        "id": "mbid-abba-dancing-queen",
        "title": "Dancing Queen",
        "artist": "ABBA",
        "album": "Arrival",
        "length": cand_dur_ms,  # 3.8s delta from 230000
        "release_id": "rel-abba-arrival",
        "release_group": {"primary_type": "Album"},
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_abba",
        file_path=audio_file,
        baseline_title="Dancing Queen",
        baseline_artist="ABBA",
        chromaprint=dummy_fp,
        duration_ms=file_dur_ms,
        ignore_cache=True,
    )

    res = engine.resolve_track(req)

    assert res.musicbrainz_id == "mbid-abba-dancing-queen"
    assert res.title == "Dancing Queen"
    assert res.artist_name == "ABBA"
    assert res.confidence_score >= 0.90


def test_acoustid_candidate_with_3_8s_delta_rejected_when_low_similarity(monkeypatch, tmp_path):
    """Candidate with delta=3.8s is rejected by Step D when acoustic similarity is <= 0.80."""
    audio_file = tmp_path / "Dancing Queen.mp3"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 230000  # 230.0s
    cand_dur_ms = 233800  # 233.8s (3.8s delta)

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Dancing Queen",
            "artist": "ABBA",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_fp = "C" * 80
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_fp, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-abba-low",
        "score": 0.75,  # 75% similarity -> dynamic threshold = 2.0s
        "recordings": [
            {
                "id": "mbid-abba-low-score",
                "title": "Dancing Queen",
                "artist": "ABBA",
                "duration": cand_dur_ms / 1000.0,
                "score": 0.75,
            }
        ],
        "mbids": ["mbid-abba-low-score"],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = {
        "id": "mbid-abba-low-score",
        "title": "Dancing Queen",
        "artist": "ABBA",
        "album": "Arrival",
        "length": cand_dur_ms,  # 3.8s delta > 2.0s threshold
        "release_id": "rel-abba-arrival",
        "release_group": {"primary_type": "Album"},
    }
    # No text search fallback result
    mock_mb.search_metadata.return_value = []

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_abba_low",
        file_path=audio_file,
        baseline_title="Dancing Queen",
        baseline_artist="ABBA",
        chromaprint=dummy_fp,
        duration_ms=file_dur_ms,
        ignore_cache=True,
    )

    res = engine.resolve_track(req)

    # Candidate was dropped by duration veto and text fallback returned nothing
    assert res.musicbrainz_id is None
    assert res.confidence_score == 0.0


def test_acoustid_isolated_path_honors_dynamic_duration_veto(monkeypatch, tmp_path):
    """Verify [acoustid-isolated] scan path respects the dynamic duration threshold."""
    audio_file = tmp_path / "Waterloo.mp3"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 168000  # 168.0s
    cand_dur_ms = 170100  # 170.1s (2.1s delta)

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Waterloo",
            "artist": "ABBA",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_fp = "C" * 80
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_fp, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-waterloo",
        "score": 0.92,  # 92% similarity -> dynamic threshold = 2.0 + (0.12/0.15)*3 = 4.4s
        "recordings": [
            {
                "id": "mbid-abba-waterloo",
                "title": "Waterloo",
                "artist": "ABBA",
                "duration": cand_dur_ms / 1000.0,
                "score": 0.92,
            }
        ],
        "mbids": ["mbid-abba-waterloo"],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = {
        "id": "mbid-abba-waterloo",
        "title": "Waterloo",
        "artist": "ABBA",
        "album": "Waterloo",
        "length": cand_dur_ms,
        "release_id": "rel-waterloo",
        "release_group": {"primary_type": "Album"},
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_waterloo",
        file_path=audio_file,
        baseline_title="Waterloo",
        baseline_artist="ABBA",
        chromaprint=dummy_fp,
        duration_ms=file_dur_ms,
        ignore_cache=True,
    )

    res = engine.resolve_track(req, enabled_stages=["acoustid"])

    # Delta of 2.1s < 4.4s threshold -> Passes Stage 3 in isolated mode
    assert res.musicbrainz_id == "mbid-abba-waterloo"
    assert res.title == "Waterloo"
    assert res.resolution_method == "acoustid"
    assert res.confidence_score == 0.95
