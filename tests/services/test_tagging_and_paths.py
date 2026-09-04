"""
Test suite for deterministic audio tagging, lofty Rust FFI extension,
dynamic path formatting, and roundtrip verification gates.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import echosync_core
from core.path_formatter import (
    sanitize_path_segment,
    build_destination_path,
    get_library_preferences,
)
from services.metadata_enhancer import (
    RetroactiveEnhancer,
    MetadataWriteVerificationError,
    build_native_tag_payload,
)
from services.auto_importer import AutoImportService
from tests.core.test_metadata_writer import (
    _create_minimal_wav_file,
    _create_minimal_flac_file,
    _create_minimal_mp3_file,
    _create_minimal_m4a_file,
)


def test_user_defined_path_formatting(tmp_path):
    """Verifies user-defined renaming patterns, token substitution, and clean omission."""
    lib_root = tmp_path / "music_library"
    pattern = "{Artist}/{Album}/{Track} - {Title}.{ext}"

    # 1. Standard full metadata
    meta1 = {
        "artist": "Daft Punk",
        "album": "Random Access Memories",
        "track_number": 1,
        "title": "Give Life Back to Music",
        "year": "2013",
    }
    p1 = build_destination_path(str(lib_root), pattern, meta1, "flac")
    expected_p1 = lib_root / "Daft Punk" / "Random Access Memories" / "01 - Give Life Back to Music.flac"
    assert p1 == expected_p1

    # 2. Clean omission of Track (no dangling hyphens like '- Title.ext')
    meta2 = {
        "artist": "Rob Dougan",
        "album": "Furious Angels",
        "title": "Clubbed to Death",
        "track_number": None,
    }
    p2 = build_destination_path(str(lib_root), pattern, meta2, "mp3")
    expected_p2 = lib_root / "Rob Dougan" / "Furious Angels" / "Clubbed to Death.mp3"
    assert p2 == expected_p2
    assert " - " not in p2.name
    assert not p2.name.startswith("-")

    # 3. Missing album defaults cleanly to 'Singles'
    meta3 = {
        "artist": "Avicii",
        "title": "Levels",
        "version": "Radio Edit",
    }
    p3 = build_destination_path(str(lib_root), "{Artist}/{Album}/{Title}.{ext}", meta3, "m4a")
    expected_p3 = lib_root / "Avicii" / "Singles" / "Levels (Radio Edit).m4a"
    assert p3 == expected_p3

    # 4. OS filesystem safety & sanitization (illegal chars: \ / * ? : " < > |)
    meta4 = {
        "artist": 'AC/DC *Special* "Rock"',
        "album": "Who Made Who?",
        "title": "D.T. <Live: 1986>",
        "track_number": "2/10",
    }
    p4 = build_destination_path(str(lib_root), pattern, meta4, "flac")
    for illegal in ['/', '\\', '*', '?', ':', '"', '<', '>', '|']:
        assert illegal not in p4.parent.parent.name  # Artist
        assert illegal not in p4.parent.name         # Album
        assert illegal not in p4.name                # Filename


def test_version_tag_injection(tmp_path):
    """Verifies versions (e.g. 'Radio Edit') are injected into title and container version tags."""
    enhancer = RetroactiveEnhancer()

    for ext, creator in [
        ("flac", _create_minimal_flac_file),
        ("mp3", _create_minimal_mp3_file),
        ("wav", _create_minimal_wav_file),
        ("m4a", _create_minimal_m4a_file),
    ]:
        audio_file = creator(tmp_path / f"version_test.{ext}")
        tags = {
            "title": "Titanium",
            "version": "David Guetta & Sia Radio Edit",
            "artist": "David Guetta feat. Sia",
            "album": "Nothing but the Beat",
        }

        # Write through enhancer
        enhancer.tag_file(audio_file, tags, verify=True)

        # Read back directly through echosync_core
        read_back = echosync_core.read_metadata(str(audio_file))
        assert read_back is not None

        # Title must have version injected
        assert "Titanium (David Guetta & Sia Radio Edit)" in read_back["title"]

        # Version tag must be preserved
        assert read_back.get("version") == "David Guetta & Sia Radio Edit"


def test_deterministic_ids_persistence(tmp_path):
    """Verifies ISRC and MBIDs survive write/read roundtrip across FLAC, MP3, WAV, and M4A."""
    enhancer = RetroactiveEnhancer()

    expected_isrc = "GBAYE0601498"
    expected_mbid = "863a3d5e-60f3-4217-bf41-69234aeef48d"
    expected_album_mbid = "4591ae2f-934c-473d-82d6-44485eb1743f"

    for ext, creator in [
        ("flac", _create_minimal_flac_file),
        ("mp3", _create_minimal_mp3_file),
        ("wav", _create_minimal_wav_file),
        ("m4a", _create_minimal_m4a_file),
    ]:
        audio_file = creator(tmp_path / f"persistence_test.{ext}")
        meta = {
            "title": "Harder, Better, Faster, Stronger",
            "artist": "Daft Punk",
            "album": "Discovery",
            "isrc": expected_isrc,
            "musicbrainz_track_id": expected_mbid,
            "musicbrainz_album_id": expected_album_mbid,
        }

        # 1. Verified tag write
        verified_tags = enhancer.tag_file_verified(audio_file, meta)
        assert verified_tags is not None

        # 2. Native readback check
        readback = echosync_core.read_metadata(str(audio_file))
        assert readback.get("isrc") == expected_isrc
        assert readback.get("musicbrainz_track_id") == expected_mbid


def test_verification_failure_blocks_move(tmp_path):
    """Confirms file movement to library is strictly denied if tag readback fails."""
    source_dir = tmp_path / "downloads"
    source_dir.mkdir()
    library_dir = tmp_path / "library"
    library_dir.mkdir()

    source_file = _create_minimal_flac_file(source_dir / "incoming.flac")
    enhancer = RetroactiveEnhancer()

    # Simulate readback mismatch (e.g. readback returns different ISRC or Title)
    with patch("echosync_core.read_metadata") as mock_read:
        mock_read.return_value = {
            "title": "Corrupted Title",
            "artist": "Unknown Artist",
            "isrc": "CORRUPTED_ISRC",
        }

        meta = {
            "title": "Expected Title",
            "artist": "Expected Artist",
            "isrc": "USRC17607839",
        }

        # 1. Direct tag_file with verify=True must raise MetadataWriteVerificationError
        with pytest.raises(MetadataWriteVerificationError):
            enhancer.tag_file(source_file, meta, verify=True)

        # 2. AutoImporter finalize_import must abort before moving file
        auto_importer = AutoImportService(library_root=library_dir)
        auto_importer.enhancer = enhancer

        with pytest.raises(MetadataWriteVerificationError):
            auto_importer.finalize_import(source_file, meta)

        # Source file must STILL exist in source directory
        assert source_file.exists(), "Source file should not have been moved or deleted upon failure!"

        # No destination files should have been created in library
        dest_files = list(library_dir.rglob("*.flac"))
        assert len(dest_files) == 0, f"No files should have been moved into library, but found: {dest_files}"


def test_preferences_priority_lookup(tmp_path):
    """Verifies that config.db system_settings takes precedence over default settings."""
    from database.config_database import get_config_database
    db = get_config_database()

    test_root = (tmp_path / "custom_lib").as_posix()
    test_pattern = "{Artist} - {Title}.{ext}"

    # Insert into system_settings
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('storage_locations.library', ?)", (test_root,))
        c.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('library_import.renaming_pattern', ?)", (test_pattern,))
        conn.commit()

    try:
        resolved_root, resolved_pattern = get_library_preferences()
        assert resolved_root == test_root
        assert resolved_pattern == test_pattern
    finally:
        # Cleanup test settings from config.db
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM system_settings WHERE key IN ('storage_locations.library', 'library_import.renaming_pattern')")
            conn.commit()
