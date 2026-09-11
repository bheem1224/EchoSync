"""Tests for MetadataResolutionEngine (core/metadata/engine.py)."""

from unittest.mock import MagicMock

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


def test_resolve_track_rejects_corrupted_embedded_mbid_via_trust_gate(monkeypatch, tmp_path):
    """Verifies that a corrupted embedded MBID (pointing to a different song) is rejected

    by the Trust Gate, allowing execution to fall through to AcoustID resolution.
    """
    audio_file = tmp_path / "01 - There's Nothing Holdin' Me Back.flac"
    audio_file.write_bytes(b"dummy flac content")

    file_dur_ms = 199000

    # Physical tags have corrupted MBID pointing to "Where Were You in the Morning?"
    corrupted_mbid = "2aeeb920-2e46-4b09-bfe9-ee1c56f0294d"
    canonical_mbid = "correct-mbid-holdin-back"

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "There's Nothing Holdin' Me Back",
            "artist": "Shawn Mendes",
            "duration_ms": file_dur_ms,
            "channels": 2,
            "musicbrainz_trackid": corrupted_mbid,
        },
    )

    dummy_cp = "E" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_cp, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-holdin-back",
        "mbids": [canonical_mbid],
    }

    mock_mb = MagicMock()

    def mock_get_metadata(mbid):
        if mbid == corrupted_mbid:
            # Stale / wrong song metadata
            return {
                "title": "Where Were You in the Morning?",
                "artist": "Shawn Mendes",
                "album": "Shawn Mendes",
                "recording_id": corrupted_mbid,
                "release_id": "rel-shawn-mendes-stale",
            }
        elif mbid == canonical_mbid:
            # Genuine canonical release from AcoustID
            return {
                "title": "There's Nothing Holdin' Me Back",
                "artist": "Shawn Mendes",
                "album": "Illuminate",
                "recording_id": canonical_mbid,
                "release_id": "rel-illuminate-canonical",
                "year": 2017,
                "track_number": 1,
                "disc_number": 1,
                "duration_ms": file_dur_ms,
                "release_group": {"primary_type": "Album"},
            }
        return None

    mock_mb.get_metadata.side_effect = mock_get_metadata

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_shawn_mendes",
        file_path=audio_file,
        baseline_title="There's Nothing Holdin' Me Back",
        baseline_artist="Shawn Mendes",
    )

    result = engine.resolve_track(req)

    # Trust Gate must have rejected corrupted_mbid and fallen through to AcoustID
    assert result.musicbrainz_track_id == canonical_mbid
    assert result.title == "There's Nothing Holdin' Me Back"
    assert result.artist == "Shawn Mendes"
    assert result.album == "Illuminate"
    assert result.resolution_method == "acoustid"
    assert result.acoustid_id == "acoustid-holdin-back"
    assert result.year == 2017
    assert result.track_number == 1
    assert result.disc_number == 1
    assert result.musicbrainz_release_id == "rel-illuminate-canonical"
    assert mock_acoustid.resolve_fingerprint_details.called


def test_resolve_track_honors_ignore_embedded_mbid_flag(monkeypatch, tmp_path):
    """Verifies that ignore_embedded_mbid=True bypasses embedded MBID lookup completely."""
    audio_file = tmp_path / "song_with_tag.flac"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 210000
    embedded_mbid = "mbid-embedded-tag"
    acoustid_mbid = "mbid-acoustid-resolved"

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Song Title",
            "artist": "Artist Name",
            "duration_ms": file_dur_ms,
            "channels": 2,
            "musicbrainz_id": embedded_mbid,
        },
    )

    dummy_cp = "F" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_cp, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-98765",
        "mbids": [acoustid_mbid],
    }

    mock_mb = MagicMock()

    def mock_get_metadata(mbid):
        if mbid == embedded_mbid:
            return {
                "title": "Song Title",
                "artist": "Artist Name",
                "album": "Embedded Tag Album",
                "recording_id": embedded_mbid,
            }
        elif mbid == acoustid_mbid:
            return {
                "title": "Song Title",
                "artist": "Artist Name",
                "album": "Acoustic Verified Album",
                "recording_id": acoustid_mbid,
                "year": 2021,
                "track_number": 3,
                "disc_number": 1,
                "duration_ms": file_dur_ms,
                "release_group": {"primary_type": "Album"},
            }
        return None

    mock_mb.get_metadata.side_effect = mock_get_metadata

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_ignore_flag",
        file_path=audio_file,
        baseline_title="Song Title",
        baseline_artist="Artist Name",
        ignore_embedded_mbid=True,
    )

    result = engine.resolve_track(req)

    # Embedded MBID must have been ignored; resolved via AcoustID
    assert result.musicbrainz_track_id == acoustid_mbid
    assert result.album == "Acoustic Verified Album"
    assert result.resolution_method == "acoustid"
    assert result.acoustid_id == "acoustid-98765"
    assert result.year == 2021
    assert result.track_number == 3
    assert result.disc_number == 1
    assert mock_acoustid.resolve_fingerprint_details.called


def test_resolve_track_bypasses_cache_when_ignore_cache_true(monkeypatch, tmp_path):
    """Verifies that Stage 2 local cache is bypassed when ignore_cache=True."""
    audio_file = tmp_path / "song_cached.flac"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 200000
    cached_mbid = "mbid-cached-1234"
    acoustid_mbid = "mbid-fresh-acoustid"

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Song Title",
            "artist": "Song Artist",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_cp = "C" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_cp, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-fresh-5678",
        "mbids": [acoustid_mbid],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = {
        "title": "Song Title",
        "artist": "Song Artist",
        "album": "Fresh AcoustID Album",
        "recording_id": acoustid_mbid,
        "duration_ms": file_dur_ms,
        "release_group": {"primary_type": "Album"},
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    # Pre-populate engine's in-memory chromaprint cache with stale/cached metadata
    engine._chromaprint_cache[dummy_cp] = {
        "title": "Song Title",
        "artist": "Song Artist",
        "album": "Old Cached Album",
        "musicbrainz_id": cached_mbid,
        "duration_ms": file_dur_ms,
    }

    # 1. Without ignore_cache, Stage 2 returns cached entry
    req_cached = ResolutionRequest(
        media_id="test_cache_hit",
        file_path=audio_file,
        baseline_title="Song Title",
        baseline_artist="Song Artist",
        ignore_cache=False,
    )
    result_cached = engine.resolve_track(req_cached)
    assert result_cached.resolution_method == "local_cache"
    assert result_cached.musicbrainz_track_id == cached_mbid
    assert not mock_acoustid.resolve_fingerprint_details.called

    # 2. With ignore_cache=True, Stage 2 is skipped and external AcoustID is queried
    req_bypass = ResolutionRequest(
        media_id="test_cache_bypass",
        file_path=audio_file,
        baseline_title="Song Title",
        baseline_artist="Song Artist",
        ignore_cache=True,
    )
    result_bypass = engine.resolve_track(req_bypass)
    assert result_bypass.resolution_method == "acoustid"
    assert result_bypass.musicbrainz_track_id == acoustid_mbid
    assert result_bypass.album == "Fresh AcoustID Album"
    assert mock_acoustid.resolve_fingerprint_details.called


def test_trust_gate_rejects_candidate_matching_dirty_baseline_but_contradicting_filename(monkeypatch, tmp_path):
    """Simulates file '01 - There's Nothing Holdin' Me Back.flac' with dirty DB baseline

    'Where Were You in the Morning?' and asserts that candidate 'Where Were You in the Morning?'
    is rejected and invalidated from cache, falling through to AcoustID.
    """
    from core.matching_engine.trust_gate import verify_title_trust_gate

    # 1. Direct Trust Gate unit test
    dirty_db_baseline = "Where Were You in the Morning?"
    physical_filename = "01 - There's Nothing Holdin' Me Back.flac"
    candidate_bad = "Where Were You in the Morning?"
    candidate_good = "There's Nothing Holdin' Me Back"

    # Candidate matching dirty DB baseline but contradicting filename MUST be rejected
    assert not verify_title_trust_gate(
        candidate_title=candidate_bad,
        baseline_title=dirty_db_baseline,
        filename=physical_filename,
    )

    # Candidate matching clean filename stem MUST be accepted
    assert verify_title_trust_gate(
        candidate_title=candidate_good,
        baseline_title=dirty_db_baseline,
        filename=physical_filename,
    )

    # 2. Engine integration test with cache poisoning invalidation
    audio_file = tmp_path / physical_filename
    audio_file.write_bytes(b"dummy audio flac")

    file_dur_ms = 199000
    dummy_cp = "E" * 60

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": dirty_db_baseline,
            "artist": "Shawn Mendes",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_cp, file_dur_ms / 1000.0),
    )

    correct_mbid = "mbid-correct-holdin-me-back"
    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-shawn-1234",
        "mbids": [correct_mbid],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = {
        "title": "There's Nothing Holdin' Me Back",
        "artist": "Shawn Mendes",
        "album": "Illuminate",
        "recording_id": correct_mbid,
        "duration_ms": file_dur_ms,
        "release_group": {"primary_type": "Album"},
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    # Poison the in-memory cache with the dirty title
    engine._chromaprint_cache[dummy_cp] = {
        "title": candidate_bad,
        "artist": "Shawn Mendes",
        "album": "Shawn Mendes",
        "musicbrainz_id": "mbid-poisoned",
        "duration_ms": file_dur_ms,
    }

    req = ResolutionRequest(
        media_id="track_123",
        file_path=audio_file,
        baseline_title=dirty_db_baseline,
        baseline_artist="Shawn Mendes",
    )

    result = engine.resolve_track(req)

    # Verify poisoned cache entry was rejected and removed from cache
    assert dummy_cp not in engine._chromaprint_cache or engine._chromaprint_cache[dummy_cp]["title"] != candidate_bad
    # Verify result resolved via AcoustID with correct title
    assert result.resolution_method == "acoustid"
    assert result.title == "There's Nothing Holdin' Me Back"
    assert result.musicbrainz_track_id == correct_mbid
    assert mock_acoustid.resolve_fingerprint_details.called


def test_acoustid_prefilters_unrelated_artists_without_musicbrainz_fetches(monkeypatch, tmp_path):
    """Mocks AcoustID returning MBIDs for Metro Station, Jonas Blue, and Shawn Mendes.
    Asserts MusicBrainz client is only called for the Shawn Mendes MBID.
    """
    audio_file = tmp_path / "01 - There's Nothing Holdin' Me Back.flac"
    audio_file.write_bytes(b"dummy audio flac")

    file_dur_ms = 199000
    dummy_cp = "F" * 60

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "There's Nothing Holdin' Me Back",
            "artist": "Shawn Mendes",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_cp, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-cluster-123",
        "mbids": [
            "mbid-metro-station",
            "mbid-jonas-blue",
            "mbid-shawn-mendes",
        ],
        "recordings": [
            {
                "id": "mbid-metro-station",
                "title": "Shake It",
                "artist": "Metro Station",
                "duration": 199,
            },
            {
                "id": "mbid-jonas-blue",
                "title": "Fast Car",
                "artist": "Jonas Blue",
                "duration": 199,
            },
            {
                "id": "mbid-shawn-mendes",
                "title": "There's Nothing Holdin' Me Back",
                "artist": "Shawn Mendes",
                "duration": 199,
            },
        ],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = {
        "title": "There's Nothing Holdin' Me Back",
        "artist": "Shawn Mendes",
        "album": "Illuminate",
        "recording_id": "mbid-shawn-mendes",
        "duration_ms": file_dur_ms,
        "release_group": {"primary_type": "Album"},
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="test_prefilter",
        file_path=audio_file,
        baseline_title="There's Nothing Holdin' Me Back",
        baseline_artist="Shawn Mendes",
        ignore_cache=True,
    )

    result = engine.resolve_track(req)

    # MusicBrainz client must ONLY have been called for the Shawn Mendes MBID
    assert mock_mb.get_metadata.call_count == 1
    mock_mb.get_metadata.assert_called_once_with("mbid-shawn-mendes")
    assert result.musicbrainz_track_id == "mbid-shawn-mendes"
    assert result.resolution_method == "acoustid"


def test_acoustid_matching_engine_selects_correct_title_over_same_album_track(monkeypatch, tmp_path):
    """Simulates candidates for 'Where Were You in the Morning?' and 'There's Nothing Holdin' Me Back'.
    Verifies 'There's Nothing Holdin' Me Back' is selected when the filename is
    '01 - There's Nothing Holdin' Me Back.flac'.
    """
    audio_file = tmp_path / "01 - There's Nothing Holdin' Me Back.flac"
    audio_file.write_bytes(b"dummy audio flac")

    file_dur_ms = 199000
    dummy_cp = "G" * 60

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": None,
            "artist": "Shawn Mendes",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_cp, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-shawn-cluster",
        "mbids": [
            "mbid-morning",
            "mbid-holdin-me-back",
        ],
        "recordings": [
            {
                "id": "mbid-morning",
                "title": "Where Were You in the Morning?",
                "artist": "Shawn Mendes",
                "duration": 199,
            },
            {
                "id": "mbid-holdin-me-back",
                "title": "There's Nothing Holdin' Me Back",
                "artist": "Shawn Mendes",
                "duration": 199,
            },
        ],
    }

    mock_mb = MagicMock()

    def mb_meta(mbid):
        if mbid == "mbid-morning":
            return {
                "title": "Where Were You in the Morning?",
                "artist": "Shawn Mendes",
                "album": "Shawn Mendes",
                "recording_id": "mbid-morning",
                "duration_ms": file_dur_ms,
                "release_group": {"primary_type": "Album"},
            }
        elif mbid == "mbid-holdin-me-back":
            return {
                "title": "There's Nothing Holdin' Me Back",
                "artist": "Shawn Mendes",
                "album": "Illuminate",
                "recording_id": "mbid-holdin-me-back",
                "duration_ms": file_dur_ms,
                "release_group": {"primary_type": "Album"},
            }
        return None

    mock_mb.get_metadata.side_effect = mb_meta

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="test_same_artist_disambiguation",
        file_path=audio_file,
        baseline_title=None,
        baseline_artist="Shawn Mendes",
        ignore_cache=True,
    )

    result = engine.resolve_track(req)

    # Candidate 'Where Were You in the Morning?' must have been rejected
    # Candidate 'There's Nothing Holdin' Me Back' must have been chosen
    assert result.musicbrainz_track_id == "mbid-holdin-me-back"
    assert result.title == "There's Nothing Holdin' Me Back"
    assert result.resolution_method == "acoustid"
    assert result.confidence_score >= 0.70


def test_acoustid_zero_trust_corrupted_tags_selects_true_recording(monkeypatch, tmp_path):
    """Verifies that a track with corrupted embedded tags and a 201s duration matches
    an AcoustID candidate of 200.6s ('There's Nothing Holdin' Me Back') over an AcoustID
    candidate of 205s ('Where Were You in the Morning?') outside the 2.0s duration window.
    """
    audio_file = tmp_path / "corrupted_track.mp3"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 201000  # 201.0s
    dummy_cp = "H" * 60

    # Corrupted embedded tags: title is tagged as "Where Were You in the Morning?"
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Where Were You in the Morning?",
            "artist": "Shawn Mendes",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_cp, file_dur_ms / 1000.0),
    )

    # Candidate 1: matches corrupted tag title, but duration is 205.0s (delta = 4.0s > 2.0s)
    # Candidate 2: true physical acoustic match, duration is 200.6s (delta = 0.4s <= 1.0s)
    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-cluster-shawn",
        "mbids": [
            "mbid-corrupt-title",
            "mbid-true-acoustic",
        ],
        "recordings": [
            {
                "id": "mbid-corrupt-title",
                "title": "Where Were You in the Morning?",
                "artist": "Shawn Mendes",
                "duration": 205,
            },
            {
                "id": "mbid-true-acoustic",
                "title": "There's Nothing Holdin' Me Back",
                "artist": "Shawn Mendes",
                "duration": 200.6,
            },
        ],
    }

    mock_mb = MagicMock()

    def mb_meta(mbid):
        if mbid == "mbid-corrupt-title":
            return {
                "title": "Where Were You in the Morning?",
                "artist": "Shawn Mendes",
                "album": "Shawn Mendes",
                "recording_id": "mbid-corrupt-title",
                "duration_ms": 205000,
                "release_group": {"primary_type": "Album"},
            }
        elif mbid == "mbid-true-acoustic":
            return {
                "title": "There's Nothing Holdin' Me Back",
                "artist": "Shawn Mendes",
                "album": "Illuminate",
                "recording_id": "mbid-true-acoustic",
                "duration_ms": 200600,
                "release_group": {"primary_type": "Album"},
            }
        return None

    mock_mb.get_metadata.side_effect = mb_meta

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="test_corrupted_tag_override",
        file_path=audio_file,
        baseline_title="Where Were You in the Morning?",  # Dirty baseline title
        baseline_artist="Shawn Mendes",
        ignore_cache=True,
    )

    result = engine.resolve_track(req)

    # Candidate 'There's Nothing Holdin' Me Back' (200.6s) must be chosen via AcoustID
    # Candidate 'Where Were You in the Morning?' (205s) must be rejected (>2.0s duration window)
    assert result.musicbrainz_track_id == "mbid-true-acoustic"
    assert result.title == "There's Nothing Holdin' Me Back"
    assert result.resolution_method == "acoustid"


def test_acoustid_duration_gate_and_weight_curve():
    """Verifies calculate_acoustid_duration_weight parabolic curve and hard 2.0s gate."""
    from core.metadata.engine import calculate_acoustid_duration_weight

    # Delta = 0s -> 1.0
    assert calculate_acoustid_duration_weight(200.0, 200.0) == 1.0

    # Delta = 1s -> 1.0 - (1.0/2.0)^2 = 0.75
    assert calculate_acoustid_duration_weight(200.0, 201.0) == 0.75

    # Delta = 2s -> 1.0 - (2.0/2.0)^2 = 0.0
    assert calculate_acoustid_duration_weight(200.0, 202.0) == 0.0

    # Delta > 2.0s -> 0.0 (Hard gate)
    assert calculate_acoustid_duration_weight(200.0, 202.1) == 0.0
    assert calculate_acoustid_duration_weight(200.0, 205.0) == 0.0
    assert calculate_acoustid_duration_weight(200.0, 190.0) == 0.0

    # Engine score_candidate rejects delta > 2.0s
    engine = MetadataResolutionEngine()
    cand_rejected = {
        "title": "Song",
        "artist": "Artist",
        "duration_ms": 202500,  # delta = 2.5s > 2.0s
    }
    score = engine.score_candidate(
        candidate=cand_rejected,
        baseline_title="Song",
        file_duration_ms=200000,
    )
    assert score == 0.0


def test_text_waterfall_duration_decay_and_cutoff():
    """Verifies calculate_text_duration_weight linear decay curve and 8.0s failure cutoff."""
    from core.metadata.engine import calculate_text_duration_weight

    # Delta = 0s -> 1.0
    assert calculate_text_duration_weight(200.0, 200.0) == 1.0

    # Delta = 4s -> 1.0 - 4.0/8.0 = 0.5
    assert calculate_text_duration_weight(200.0, 204.0) == 0.5

    # Delta = 8s -> 1.0 - 8.0/8.0 = 0.0
    assert calculate_text_duration_weight(200.0, 208.0) == 0.0

    # Delta > 8.0s -> 0.0 (Failure threshold)
    assert calculate_text_duration_weight(200.0, 208.1) == 0.0
    assert calculate_text_duration_weight(200.0, 215.0) == 0.0
    assert calculate_text_duration_weight(200.0, 180.0) == 0.0
