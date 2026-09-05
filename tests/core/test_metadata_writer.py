import struct
from pathlib import Path

import echosync_core

from services.metadata_enhancer import (
    RetroactiveEnhancer,
)


def _create_minimal_wav_file(path: Path) -> Path:
    """Create a minimal, valid PCM RIFF/WAV audio file."""
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


def _create_minimal_flac_file(path: Path) -> Path:
    """Create a minimal, valid FLAC audio file with STREAMINFO and VorbisComment block."""
    frame = b"\xff\xf8\x19\x18\x00\x93\x00\x00\x00\x00\x00\x00\x96\xb3"
    vc_payload = b"\x08\x00\x00\x00lofty-rs\x00\x00\x00\x00"
    flac_bytes = (
        b"fLaC"
        + b"\x00\x00\x00\x22"  # STREAMINFO block header (is_last = 0, len = 34)
        + b"\x00\xc0\x00\xc0"  # min/max block size = 192
        + b"\x00\x00\x0e\x00\x00\x0e"  # min/max frame size = 14
        + b"\x0a\xc4\x42\xf0\x00\x00\x00\xc0"  # 44100Hz, 2ch, 16bit, 192 samples
        + b"\x00" * 16  # MD5 signature
        + b"\x84\x00\x00"  # VORBIS_COMMENT header (is_last = 1)
        + bytes([len(vc_payload)])
        + vc_payload
        + frame * 5  # Audio frames
    )
    path.write_bytes(flac_bytes)
    return path


def _create_minimal_mp3_file(path: Path) -> Path:
    """Create a minimal, valid MP3 audio file with ID3v2 header and MPEG Layer 3 frames."""
    id3_header = b"ID3\x04\x00\x00\x00\x00\x00\x00"
    mp3_frame = b"\xff\xfb\x90\x00" + b"\x00" * 413
    path.write_bytes(id3_header + mp3_frame * 4)
    return path


def _create_minimal_m4a_file(path: Path) -> Path:
    """Create a minimal, valid ISO BMFF MP4/M4A audio file."""

    def box(box_type: bytes, payload: bytes) -> bytes:
        return struct.pack(">I4s", len(payload) + 8, box_type) + payload

    ftyp = box(b"ftyp", b"M4A \x00\x00\x00\x00M4A mp42isom")
    mvhd = box(
        b"mvhd",
        b"\x00" * 4
        + b"\x00" * 4
        + b"\x00" * 4
        + struct.pack(">II", 1000, 1000)
        + struct.pack(">IH", 0x00010000, 0x0100)
        + b"\x00" * 10
        + b"\x00\x01\x00\x00"
        + b"\x00" * 12
        + b"\x00\x01\x00\x00"
        + b"\x00" * 12
        + b"\x40\x00\x00\x00"
        + b"\x00" * 24
        + struct.pack(">I", 2),
    )
    tkhd = box(
        b"tkhd",
        b"\x00\x00\x00\x01"
        + b"\x00" * 8
        + struct.pack(">I", 1)
        + b"\x00" * 4
        + struct.pack(">I", 1000)
        + b"\x00" * 8
        + b"\x00\x00\x00\x00\x01\x00\x00\x00"
        + b"\x00\x01\x00\x00"
        + b"\x00" * 12
        + b"\x00\x01\x00\x00"
        + b"\x00" * 12
        + b"\x40\x00\x00\x00"
        + b"\x00" * 8,
    )
    mdhd = box(
        b"mdhd",
        b"\x00" * 12 + struct.pack(">II", 44100, 44100) + struct.pack(">HH", 0x55C4, 0),
    )
    hdlr = box(
        b"hdlr",
        b"\x00" * 4 + b"\x00" * 4 + b"soun" + b"\x00" * 12 + b"SoundHandler\x00",
    )
    smhd = box(b"smhd", b"\x00" * 8)
    url_box = box(b"url ", b"\x00\x00\x00\x01")
    dref = box(b"dref", b"\x00" * 4 + struct.pack(">I", 1) + url_box)
    dinf = box(b"dinf", dref)
    mp4a = box(
        b"mp4a",
        b"\x00" * 6
        + struct.pack(">H", 1)
        + b"\x00" * 8
        + struct.pack(">HH", 2, 16)
        + b"\x00" * 4
        + struct.pack(">I", 44100 << 16),
    )
    stsd = box(b"stsd", b"\x00" * 4 + struct.pack(">I", 1) + mp4a)
    stts = box(
        b"stts", b"\x00" * 4 + struct.pack(">I", 1) + struct.pack(">II", 1, 44100)
    )
    stsc = box(
        b"stsc", b"\x00" * 4 + struct.pack(">I", 1) + struct.pack(">III", 1, 1, 1)
    )
    stsz = box(b"stsz", b"\x00" * 4 + struct.pack(">I", 16) + struct.pack(">I", 1))
    stco = box(b"stco", b"\x00" * 4 + struct.pack(">I", 1) + struct.pack(">I", 0))

    stbl = box(b"stbl", stsd + stts + stsc + stsz + stco)
    minf = box(b"minf", smhd + dinf + stbl)
    mdia = box(b"mdia", mdhd + hdlr + minf)
    trak = box(b"trak", tkhd + mdia)
    moov = box(b"moov", mvhd + trak)
    mdat = box(b"mdat", b"\x00" * 16)

    path.write_bytes(ftyp + moov + mdat)
    return path


def test_rust_tag_writer_roundtrip_wav(tmp_path):
    """Verify that echosync_core writes and reads tags on RIFF/WAV files."""
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


def test_wav_riff_info_tag_write_read_roundtrip(tmp_path):
    """Verify RIFF INFO / ID3v2 tag writing and readback on WAV files."""
    wav_path = _create_minimal_wav_file(tmp_path / "riff_test.wav")
    enhancer = RetroactiveEnhancer()

    metadata = {
        "title": "Clubbed to Death",
        "artist": "Rob Dougan",
        "album": "Furious Angels",
        "album_artist": "Rob Dougan",
        "year": "2002",
        "track_number": "1",
    }

    verified = enhancer.tag_file_verified(wav_path, metadata)
    assert verified.get("title") == "Clubbed to Death"
    assert verified.get("artist") == "Rob Dougan"
    assert verified.get("album") == "Furious Angels"


def test_flac_vorbis_comments_roundtrip(tmp_path):
    """Verify Vorbis Comments tag writing and readback on FLAC files."""
    flac_path = _create_minimal_flac_file(tmp_path / "vorbis_test.flac")
    enhancer = RetroactiveEnhancer()

    metadata = {
        "title": "Furious Angels (Instrumental)",
        "artist": "Rob Dougan",
        "album": "Furious Angels",
        "year": "2002",
        "track_number": "2",
        "musicbrainz_id": "98765432-1111-2222-3333-abcdefabcdef",
    }

    verified = enhancer.tag_file_verified(flac_path, metadata)
    assert verified.get("title") == "Furious Angels (Instrumental)"
    assert verified.get("artist") == "Rob Dougan"
    assert verified.get("album") == "Furious Angels"
    assert verified.get("mbid") == "98765432-1111-2222-3333-abcdefabcdef"


def test_mp3_id3v2_roundtrip(tmp_path):
    """Verify ID3v2 tag writing and readback on MP3 files."""
    mp3_path = _create_minimal_mp3_file(tmp_path / "id3_test.mp3")
    enhancer = RetroactiveEnhancer()

    metadata = {
        "title": "Chateau",
        "artist": "Rob Dougan",
        "album": "Furious Angels",
        "year": "2002",
        "track_number": "3",
    }

    verified = enhancer.tag_file_verified(mp3_path, metadata)
    assert verified.get("title") == "Chateau"
    assert verified.get("artist") == "Rob Dougan"
    assert verified.get("album") == "Furious Angels"


def test_alac_mp4_ilst_roundtrip(tmp_path):
    """Verify MP4 ilst atom tag writing and readback on M4A/ALAC files."""
    m4a_path = _create_minimal_m4a_file(tmp_path / "alac_test.m4a")
    enhancer = RetroactiveEnhancer()

    metadata = {
        "title": "There's Only Me",
        "artist": "Rob Dougan",
        "album": "Furious Angels",
        "year": "2002",
        "track_number": "4",
    }

    verified = enhancer.tag_file_verified(m4a_path, metadata)
    assert verified.get("title") == "There's Only Me"
    assert verified.get("artist") == "Rob Dougan"
    assert verified.get("album") == "Furious Angels"


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


def test_wav_dual_tag_write_read_roundtrip(tmp_path):
    """Verify that echosync_core writes and reads dual RIFF INFO + ID3v2 tags on WAV files."""
    wav_path = _create_minimal_wav_file(tmp_path / "dual_tag_test.wav")

    tags_to_write = {
        "title": "I'm Not Driving Anymore",
        "artist": "Rob Dougan",
        "album": "Furious Angels",
        "album_artist": "Rob Dougan",
        "track_number": "5",
        "disc_number": "1",
        "year": "2002",
        "genre": "Trip Hop",
        "musicbrainz_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
    }

    # 1. Native write
    success = echosync_core.write_metadata(str(wav_path), tags_to_write)
    assert success is True

    # 2. Native extract via read_metadata
    read_back = echosync_core.read_metadata(str(wav_path))
    assert isinstance(read_back, dict)
    assert read_back.get("title") == "I'm Not Driving Anymore"
    assert read_back.get("artist") == "Rob Dougan"
    assert read_back.get("album") == "Furious Angels"
    assert read_back.get("album_artist") == "Rob Dougan"
    assert read_back.get("track_number") == 5
    assert read_back.get("disc_number") == 1
    assert read_back.get("year") == 2002
    assert read_back.get("genre") == "Trip Hop"
    assert read_back.get("mbid") == "a1b2c3d4-5678-90ab-cdef-1234567890ab"


def test_misnamed_container_magic_bytes_detection(tmp_path):
    """Verify that an MP3 file with a .wav extension is detected by magic bytes and tagged successfully."""
    fake_wav_path = _create_minimal_mp3_file(tmp_path / "misnamed.wav")
    enhancer = RetroactiveEnhancer()

    metadata = {
        "title": "New Religion",
        "artist": "OnCue",
        "album": "Leftovers 2",
        "year": "2013",
    }

    verified = enhancer.tag_file_verified(fake_wav_path, metadata)
    assert verified.get("title") == "New Religion"
    assert verified.get("artist") == "OnCue"
    assert verified.get("codec") == "MPEG"


def test_wav_corrupt_legacy_riff_info_recovery(tmp_path):
    """Verify that a WAV file with corrupt legacy RIFF INFO item keys recovers and is tagged successfully."""
    num_channels = 2
    sample_rate = 44100
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    fmt_chunk = struct.pack(
        "<4sIHHIIHH",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
    )

    # Invalid non-ASCII RIFF INFO chunk
    invalid_subchunk = b"\x00\x01\x02\x03" + struct.pack("<I", 4) + b"test"
    list_info_chunk = (
        b"LIST"
        + struct.pack("<I", 4 + len(invalid_subchunk))
        + b"INFO"
        + invalid_subchunk
    )

    data = b"\x00" * 1000
    data_chunk = b"data" + struct.pack("<I", len(data)) + data

    riff_payload = b"WAVE" + fmt_chunk + list_info_chunk + data_chunk
    wav_bytes = b"RIFF" + struct.pack("<I", len(riff_payload)) + riff_payload

    corrupt_wav_path = tmp_path / "corrupt_riff.wav"
    corrupt_wav_path.write_bytes(wav_bytes)

    enhancer = RetroactiveEnhancer()
    metadata = {
        "title": "Open Sore",
        "artist": "Skinny Puppy",
        "album": "Bites",
        "year": "1985",
    }

    verified = enhancer.tag_file_verified(corrupt_wav_path, metadata)
    assert verified.get("title") == "Open Sore"
    assert verified.get("artist") == "Skinny Puppy"
