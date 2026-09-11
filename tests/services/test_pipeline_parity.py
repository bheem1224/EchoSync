from pathlib import Path
from unittest.mock import MagicMock

from core.db.echo_sync_track import EchosyncTrack
from core.enums import Capability
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest
from database.music_database import (
    Album,
    Artist,
    AudioFingerprint,
    Base,
    LocalMedia,
    MusicDatabase,
    Track,
)
from services.metadata_enhancer import RetroactiveEnhancer


def test_automated_enhance_track_shawn_mendes_parity(tmp_path, monkeypatch):
    """Verify that automated enhance_track() on '01 - There's Nothing Holdin' Me Back.flac'
    yields the exact ground truth MBID 'd2555d82-571d-406c-8e96-21562753cebc' with confidence >= 0.75,
    matching the hardened manual review workflow.
    """
    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    file_dir = tmp_path / "data" / "library" / "Shawn Mendes" / "Illuminate"
    file_dir.mkdir(parents=True, exist_ok=True)
    audio_file = file_dir / "01 - There's Nothing Holdin' Me Back.flac"
    audio_file.write_bytes(b"dummy flac content")

    target_mbid = "d2555d82-571d-406c-8e96-21562753cebc"
    mock_chromaprint = "AQABz0mSRIqYJEoUB9_xH_shawn_mendes" * 50

    with music_db.session_scope() as session:
        art = Artist(name="Shawn Mendes", normalized_name="shawn mendes")
        alb = Album(title="Illuminate", normalized_title="illuminate", artist=art)
        session.add_all([art, alb])
        session.flush()

        track = Track(
            id=1001,
            title="Where Were You in the Morning?",  # Dirty/divergent embedded title
            normalized_title="where were you in the morning",
            sync_id="sync_shawn_1001",
            duration=199400,
            musicbrainz_id=None,
            isrc=None,
            artist=art,
            album=alb,
            metadata_status={},
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=1001,
            file_path=str(audio_file),
            file_format="flac",
            media_id="media_shawn_001",
        )
        session.add(media)
        session.flush()

        fp = AudioFingerprint(
            media_id="media_shawn_001",
            chromaprint=mock_chromaprint,
            acoustid_id=None,
        )
        session.add(fp)

    monkeypatch.setattr("database.music_database.get_database", lambda: music_db)
    monkeypatch.setattr("database.get_database", lambda: music_db)
    monkeypatch.setattr("services.metadata_enhancer._tagging_write", lambda p, tags: None)
    monkeypatch.setattr(
        "services.metadata_enhancer.RetroactiveEnhancer.tag_file_verified",
        lambda self, p, tags: None,
    )

    import echosync_core

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Where Were You in the Morning?",
            "artist": "Shawn Mendes",
            "duration": 199.4,
            "duration_ms": 199400,
        },
    )

    dsp_called = []

    def fake_generate_with_dur(p):
        dsp_called.append(p)
        return (mock_chromaprint, 199.4)

    monkeypatch.setattr(FingerprintGenerator, "generate_with_duration", fake_generate_with_dur)

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid_shawn_uuid",
        "recordings": [
            {
                "id": target_mbid,
                "title": "There's Nothing Holdin' Me Back",
                "artist": "Shawn Mendes",
                "duration": 199.4,
                "score": 0.98,
            },
            {
                "id": "2aeeb920-571d-406c-8e96-21562753cebc",
                "title": "Where Were You in the Morning?",
                "artist": "Shawn Mendes",
                "duration": 199.4,
                "score": 0.94,
            },
        ],
        "mbids": [target_mbid, "2aeeb920-571d-406c-8e96-21562753cebc"],
        "score": 0.98,
    }

    mb_calls = []
    mock_mb = MagicMock()

    def fake_mb_get_metadata(mbid):
        mb_calls.append(mbid)
        if mbid == target_mbid:
            return {
                "title": "There's Nothing Holdin' Me Back",
                "artist": "Shawn Mendes",
                "artist_name": "Shawn Mendes",
                "album": "Illuminate",
                "album_title": "Illuminate",
                "recording_id": target_mbid,
                "length": 199400,
                "duration_ms": 199400,
                "release_group": {"primary_type": "Album"},
            }
        return {
            "title": "Where Were You in the Morning?",
            "artist": "Shawn Mendes",
            "album": "Illuminate",
            "recording_id": mbid,
            "length": 199400,
        }

    mock_mb.get_metadata.side_effect = fake_mb_get_metadata

    enhancer = RetroactiveEnhancer()

    def fake_get_plugin(cap, required_algorithm=None):
        if cap == Capability.RESOLVE_FINGERPRINT:
            return mock_acoustid
        if cap == Capability.FETCH_METADATA:
            return mock_mb
        return None

    monkeypatch.setattr(enhancer, "_get_plugin", fake_get_plugin)
    monkeypatch.setattr(enhancer, "_get_mb_plugin", lambda: mock_mb)
    monkeypatch.setattr(enhancer, "_get_spotify_plugin", lambda: None)

    # Execute automated enhance_track
    with music_db.session_scope() as session:
        result = enhancer.enhance_track(1001, session=session)

    # 1. Parity Assertions
    assert result is not None, "enhance_track must return a ResolutionResult"
    assert result.musicbrainz_track_id == target_mbid, f"Expected {target_mbid}, got {result.musicbrainz_track_id}"
    assert result.title == "There's Nothing Holdin' Me Back"
    assert result.confidence_score >= 0.75, f"Confidence score {result.confidence_score} must be >= 0.75"

    # 2. Rust DSP / Audio Re-decoding Assertions (pre-existing chromaprint reused)
    assert len(dsp_called) == 0, "DSP / Audio re-decoding must be 0 when chromaprint is pre-populated in database"

    # 3. Network Egress Assertions: Clear filename match short-circuits secondary MB queries
    assert len(mb_calls) == 1, f"Expected exactly 1 MusicBrainz call on clear match, got {len(mb_calls)}: {mb_calls}"
    assert mb_calls[0] == target_mbid

    # 4. Database Atomicity Assertions
    with music_db.session_scope() as session:
        db_track = session.get(Track, 1001)
        assert db_track.musicbrainz_id == target_mbid
        assert db_track.title == "There's Nothing Holdin' Me Back"
        assert db_track.metadata_status.get("enhanced") is True

        db_fp = session.query(AudioFingerprint).filter_by(media_id="media_shawn_001").first()
        assert db_fp is not None
        assert db_fp.chromaprint == mock_chromaprint
        assert db_fp.acoustid_id == "acoustid_shawn_uuid"


def test_chromaprint_reuse_bypasses_dsp_and_audio_decoding(tmp_path, monkeypatch):
    """Verify that when ResolutionRequest provides a chromaprint, neither _execute_waterfall
    nor _resolve_acoustid invokes FingerprintGenerator.generate_with_duration.
    """
    audio_file = tmp_path / "test_track.flac"
    audio_file.write_bytes(b"dummy flac content")

    mock_cp = "PRE_COMPUTED_CHROMAPRINT_STRING_12345"
    dsp_called = []

    def mock_dsp(p):
        dsp_called.append(p)
        return ("GENERATED_FINGERPRINT", 180)

    monkeypatch.setattr(FingerprintGenerator, "generate_with_duration", mock_dsp)

    mock_acoustid = MagicMock()
    acoustid_payloads = []

    def mock_resolve_details(fingerprint, duration):
        acoustid_payloads.append((fingerprint, duration))
        return {
            "acoustid_id": "acoustid_test_id",
            "recordings": [
                {
                    "id": "mbid_test_001",
                    "title": "Test Title",
                    "artist": "Test Artist",
                    "duration": 180.0,
                    "score": 0.95,
                }
            ],
            "mbids": ["mbid_test_001"],
            "score": 0.95,
        }

    mock_acoustid.resolve_fingerprint_details.side_effect = mock_resolve_details

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = {
        "title": "Test Title",
        "artist": "Test Artist",
        "album": "Test Album",
        "recording_id": "mbid_test_001",
        "length": 180000,
        "release_group": {"primary_type": "Album"},
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_1",
        file_path=audio_file,
        chromaprint=mock_cp,
        duration=180.0,
        duration_ms=180000,
        baseline_title="Test Title",
        baseline_artist="Test Artist",
    )

    result = engine.resolve_track(req)

    assert result is not None
    assert result.musicbrainz_track_id == "mbid_test_001"
    assert result.chromaprint == mock_cp
    # Verify DSP was never invoked
    assert len(dsp_called) == 0, f"FingerprintGenerator was called {len(dsp_called)} times; expected 0."
    # Verify AcoustID received the pre-computed chromaprint
    assert len(acoustid_payloads) == 1
    assert acoustid_payloads[0][0] == mock_cp


def test_musicbrainz_http_call_count_capped_on_clear_match(tmp_path, monkeypatch):
    """Verify that when AcoustID returns multiple candidates, but candidate 1 is a clear
    filename match, MusicBrainz get_metadata is called at most 1 time.
    """
    audio_file = tmp_path / "01 - Radioactive.flac"
    audio_file.write_bytes(b"dummy audio")

    mock_cp = "RADIOACTIVE_CHROMAPRINT"
    monkeypatch.setattr(FingerprintGenerator, "generate_with_duration", lambda p: (mock_cp, 186.0))

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid_radioactive",
        "recordings": [
            {
                "id": "mbid_radioactive_canon",
                "title": "Radioactive",
                "artist": "Imagine Dragons",
                "duration": 186.0,
                "score": 0.99,
            },
            {
                "id": "mbid_radioactive_alt",
                "title": "Radioactive (Acoustic)",
                "artist": "Imagine Dragons",
                "duration": 186.0,
                "score": 0.95,
            },
            {
                "id": "mbid_radioactive_remix",
                "title": "Radioactive (dMix)",
                "artist": "Imagine Dragons",
                "duration": 186.0,
                "score": 0.90,
            },
        ],
        "mbids": ["mbid_radioactive_canon", "mbid_radioactive_alt", "mbid_radioactive_remix"],
        "score": 0.99,
    }

    mb_calls = []
    mock_mb = MagicMock()

    def track_mb_calls(mbid):
        mb_calls.append(mbid)
        if mbid == "mbid_radioactive_canon":
            return {
                "title": "Radioactive",
                "artist": "Imagine Dragons",
                "album": "Night Visions",
                "recording_id": "mbid_radioactive_canon",
                "length": 186000,
                "release_group": {"primary_type": "Album"},
            }
        return {
            "title": "Radioactive (Acoustic)",
            "artist": "Imagine Dragons",
            "album": "Night Visions (Deluxe)",
            "recording_id": mbid,
            "length": 186000,
        }

    mock_mb.get_metadata.side_effect = track_mb_calls

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_radioactive_1",
        file_path=audio_file,
        chromaprint=mock_cp,
        duration=186.0,
        duration_ms=186000,
        baseline_title="Radioactive",
        baseline_artist="Imagine Dragons",
    )

    result = engine.resolve_track(req)

    assert result is not None
    assert result.musicbrainz_track_id == "mbid_radioactive_canon"
    # Crucial assertion: HTTP call count <= 1 when clear filename match exists
    assert len(mb_calls) == 1, f"Expected <= 1 MusicBrainz call, but got {len(mb_calls)}: {mb_calls}"
