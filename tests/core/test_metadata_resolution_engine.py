"""Tests for MetadataResolutionEngine (core/metadata/engine.py)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import echosync_core
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest


def test_resolve_track_acoustid_penalizes_remix(monkeypatch, tmp_path):
    """Verifies AcoustID candidate scoring penalizes remix/country mix variant

    in favor of the canonical studio recording.
    """
    audio_file = tmp_path / "train_hey_soul_sister.mp3"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 217000  # 3:37

    # Mock extract_metadata
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Hey, Soul Sister",
            "artist": "Train",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    # Mock FingerprintGenerator
    dummy_chromaprint = "A" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    # Candidate 1: Country Mix (exact duration match, but remix disambiguation)
    cand_country = {
        "title": "Hey, Soul Sister (Country Mix)",
        "disambiguation": "Country Mix",
        "artist": "Train",
        "album": "Hey, Soul Sister",
        "duration_ms": file_dur_ms,  # 0ms delta
        "release_id": "rel-country-1",
        "release_group": {"primary_type": "Single"},
    }

    # Candidate 2: Canonical Studio Album (500ms duration delta, official Album)
    cand_canonical = {
        "title": "Hey, Soul Sister",
        "disambiguation": "",
        "artist": "Train",
        "album": "Save Me, San Francisco",
        "duration_ms": file_dur_ms + 500,  # 500ms delta
        "release_id": "rel-album-canonical",
        "release_group": {"primary_type": "Album"},
    }

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-12345",
        "mbids": ["mbid-country-mix", "mbid-canonical-studio"],
    }

    mock_mb = MagicMock()

    def mock_get_meta(mbid):
        if mbid == "mbid-country-mix":
            return cand_country
        elif mbid == "mbid-canonical-studio":
            return cand_canonical
        return None

    mock_mb.get_metadata.side_effect = mock_get_meta

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_1",
        file_path=audio_file,
        baseline_title="Hey, Soul Sister",
        baseline_artist="Train",
    )

    result = engine.resolve_track(req)

    # Assert that Candidate 2 (canonical studio album) won despite the 500ms delta
    assert result.musicbrainz_track_id == "mbid-canonical-studio"
    assert result.title == "Hey, Soul Sister"
    assert result.album == "Save Me, San Francisco"
    assert result.acoustid_id == "acoustid-12345"
    assert result.resolution_method == "acoustid"
    assert result.confidence_score == 0.95


def test_resolve_track_respects_duration_delta(monkeypatch, tmp_path):
    """Ensures AcoustID candidate with >2000ms duration delta is rejected."""
    audio_file = tmp_path / "song.mp3"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 200000  # 200s

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Radioactive",
            "artist": "Imagine Dragons",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_chromaprint = "B" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    # Candidate with duration 204000ms -> delta 4000ms (> 2000ms window)
    cand_extended = {
        "title": "Radioactive (Extended Version)",
        "disambiguation": "extended",
        "artist": "Imagine Dragons",
        "album": "Night Visions",
        "duration_ms": 204000,
        "release_id": "rel-ext",
    }

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-99999",
        "mbids": ["mbid-extended"],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = cand_extended
    mock_mb.search_metadata.return_value = []  # No text search fallback hit

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_2",
        file_path=audio_file,
        baseline_title="Radioactive",
        baseline_artist="Imagine Dragons",
    )

    result = engine.resolve_track(req)

    # Candidate should have been rejected by duration window delta > 2000ms
    assert result.musicbrainz_track_id is None
    assert result.confidence_score == 0.0


def test_resolve_track_preserves_native_script(monkeypatch, tmp_path):
    """Verifies original native script is strictly retained in title and artist fields without romanization."""
    audio_file = tmp_path / "yoasobi_idol.flac"
    audio_file.write_bytes(b"dummy japanese audio")

    file_dur_ms = 213000

    # Japanese native script
    native_title = "アイドル"
    native_artist = "YOASOBI"
    native_album = "THE BOOK 3"

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": native_title,
            "artist": native_artist,
            "album": native_album,
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_chromaprint = "C" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    cand_native = {
        "title": native_title,
        "disambiguation": "",
        "artist": native_artist,
        "album": native_album,
        "duration_ms": file_dur_ms,
        "release_id": "rel-yoasobi-book3",
        "release_group": {"primary_type": "Album"},
    }

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-yoasobi",
        "mbids": ["mbid-idol-native"],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = cand_native

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_yoasobi",
        file_path=audio_file,
        baseline_title=native_title,
        baseline_artist=native_artist,
    )

    result = engine.resolve_track(req)

    assert result.title == native_title
    assert result.artist == native_artist
    assert result.album == native_album
    assert result.musicbrainz_track_id == "mbid-idol-native"
    assert result.resolution_method == "acoustid"


def test_resolve_track_skips_fingerprinting_for_multichannel(monkeypatch, tmp_path):
    """Verifies that multi-channel audio (>2 channels, e.g. 5.1/7.1) skips Chromaprint extraction."""
    audio_file = tmp_path / "surround_5_1.flac"
    audio_file.write_bytes(b"dummy surround flac")

    # 6 channels (5.1 surround sound)
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Surround Symphonic",
            "artist": "London Philharmonic Orchestra",
            "duration_ms": 300000,
            "channels": 6,
        },
    )

    fp_called = False

    def fake_generate_with_duration(p):
        nonlocal fp_called
        fp_called = True
        return "some_chromaprint", 300.0

    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        fake_generate_with_duration,
    )

    mock_mb = MagicMock()
    mock_mb.search_metadata.return_value = []

    engine = MetadataResolutionEngine(
        acoustid_provider=MagicMock(),
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_surround",
        file_path=audio_file,
        baseline_title="Surround Symphonic",
        baseline_artist="London Philharmonic Orchestra",
    )

    result = engine.resolve_track(req)

    # Chromaprint generation must have been skipped
    assert not fp_called
    assert result.chromaprint is None


def test_resolve_track_local_cache_hit(monkeypatch, tmp_path):
    """Verifies local chromaprint cache hit resolves canonical metadata without outbound AcoustID call."""
    audio_file = tmp_path / "cached_song.mp3"
    audio_file.write_bytes(b"dummy cached song")

    dummy_cp = "D" * 60
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Get Lucky",
            "artist": "Daft Punk",
            "duration_ms": 248000,
            "channels": 2,
        },
    )
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_cp, 248.0),
    )

    engine = MetadataResolutionEngine(
        acoustid_provider=MagicMock(),
        metadata_provider=MagicMock(),
    )

    # Pre-populate engine's local cache
    engine._chromaprint_cache[dummy_cp] = {
        "title": "Get Lucky",
        "artist": "Daft Punk feat. Pharrell Williams",
        "album": "Random Access Memories",
        "year": 2013,
        "musicbrainz_id": "mbid-daft-punk-get-lucky",
        "release_mbid": "rel-ram-2013",
        "track_number": 8,
        "disc_number": 1,
        "duration_ms": 248000,
        "isrc": "US1234567890",
        "acoustid_id": "acoustid-cached-ram",
    }

    req = ResolutionRequest(
        media_id="media_cached",
        file_path=audio_file,
        baseline_title="Get Lucky",
        baseline_artist="Daft Punk",
    )

    result = engine.resolve_track(req)

    assert result.resolution_method == "local_cache"
    assert result.confidence_score == 0.95
    assert result.musicbrainz_track_id == "mbid-daft-punk-get-lucky"
    assert result.acoustid_id == "acoustid-cached-ram"
    assert result.album == "Random Access Memories"
    # Verify acoustid provider was not called
    assert not engine._acoustid_provider.resolve_fingerprint_details.called
