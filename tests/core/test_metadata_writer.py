import struct
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

import echosync_core
from services.metadata_enhancer import RetroactiveEnhancer, MetadataWriteVerificationError


def _create_minimal_wav_file(path: Path) -> Path:
    """Create a minimal, valid 44-byte PCM RIFF/WAV audio file."""
    num_channels = 2
    sample_rate = 44100
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data = b"\x00" * 44100  # 0.25s silence
    data_len = len(data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_len,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM format
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_len,
    )
    path.write_bytes(header + data)
    return path


def test_rust_tag_writer_roundtrip_wav(tmp_path):
    """Verify that echosync_core writes and reads ID3v2 tags on RIFF/WAV files."""
    wav_path = _create_minimal_wav_file(tmp_path / "test_roundtrip.wav")

    tags_to_write = {
        "title": "Valedico (Orchestral Session)",
        "artist": "Rob Dougan",
        "album": "A Drawing-Down of Blinds",
        "album_artist": "Rob Dougan",
        "track_number": "4",
        "disc_number": "1",
        "year": "2026",
        "genre": "Soundtrack",
        "musicbrainz_id": "1970bda6-446f-40fd-8872-24b31a302ca3",
    }

    # 1. Native write
    success = echosync_core.write_metadata(str(wav_path), tags_to_write)
    assert success is True

    # 2. Native extract
    read_back = echosync_core.extract_metadata(str(wav_path))
    assert isinstance(read_back, dict)
    assert read_back.get("title") == "Valedico (Orchestral Session)"
    assert read_back.get("artist") == "Rob Dougan"
    assert read_back.get("album") == "A Drawing-Down of Blinds"
    assert read_back.get("album_artist") == "Rob Dougan"
    assert read_back.get("track_number") == 4
    assert read_back.get("disc_number") == 1
    assert read_back.get("year") == 2026
    assert read_back.get("genre") == "Soundtrack"
    assert read_back.get("mbid") == "1970bda6-446f-40fd-8872-24b31a302ca3"


def test_tag_file_verified_success(tmp_path):
    """Verify that tag_file_verified succeeds and returns verified metadata on valid file."""
    wav_path = _create_minimal_wav_file(tmp_path / "verified_test.wav")
    enhancer = RetroactiveEnhancer()

    metadata = {
        "title": "Clubbed to Death",
        "artist": "Rob Dougan",
        "album": "Furious Angels",
        "year": "2002",
        "track_number": "1",
    }

    verified = enhancer.tag_file_verified(wav_path, metadata)
    assert verified.get("title") == "Clubbed to Death"
    assert verified.get("artist") == "Rob Dougan"


def test_tag_verification_blocks_relocation_on_mismatch(tmp_path):
    """Verify that a mismatch in readback raises MetadataWriteVerificationError."""
    wav_path = _create_minimal_wav_file(tmp_path / "mismatch_test.wav")
    enhancer = RetroactiveEnhancer()

    metadata = {
        "title": "Original Title",
        "artist": "Original Artist",
    }

    # Mock extract_metadata to return corrupt or mismatched metadata
    with patch("echosync_core.extract_metadata", return_value={"title": "Mismatched Title", "artist": "Original Artist"}):
        with pytest.raises(MetadataWriteVerificationError) as excinfo:
            enhancer.tag_file_verified(wav_path, metadata)
        assert "title mismatch" in str(excinfo.value)
