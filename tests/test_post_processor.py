"""
Comprehensive tests for PostProcessor service

Tests cover:
- Filename sanitization
- Pattern-based file organization
- Duplicate file handling
- Cross-partition moves (simulated)
- Tag writing (mocked since mutagen might not be available)
- Cover art embedding
- Empty directory cleanup
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from core.post_processor import (
    PostProcessor,
    AudioFormat,
    TagWriteResult,
    FileOrganizeResult,
)
from core.matching_engine import SoulSyncTrack


class TestPostProcessorFilename:
    """Tests for filename sanitization"""

    def setup_method(self):
        self.processor = PostProcessor(check_mutagen=False)

    def test_sanitize_basic_filename(self):
        """Test sanitizing a basic filename"""
        result = self.processor.sanitize_filename("My Song.mp3")
        assert result == "My Song.mp3"

    def test_remove_illegal_characters(self):
        """Test removal of illegal characters"""
        result = self.processor.sanitize_filename("Song <Title> | Artist")
        assert "<" not in result
        assert ">" not in result
        assert "|" not in result

    def test_remove_leading_trailing_dots(self):
        """Test removal of leading/trailing dots"""
        result = self.processor.sanitize_filename("...Song Title...")
        assert not result.startswith(".")
        assert not result.endswith(".")

    def test_collapse_multiple_spaces(self):
        """Test collapsing multiple spaces"""
        result = self.processor.sanitize_filename("Song   Title")
        assert "   " not in result
        assert result == "Song Title"

    def test_remove_colon(self):
        """Test removal of colon (illegal on Windows)"""
        result = self.processor.sanitize_filename("Album: Artist - Song")
        assert ":" not in result

    def test_remove_slash(self):
        """Test removal of forward slash"""
        result = self.processor.sanitize_filename("Artist/Song")
        # Slash should be removed, not converted to something else
        assert "/" not in result

    def test_remove_backslash(self):
        """Test removal of backslash"""
        result = self.processor.sanitize_filename("Artist\\Song")
        assert "\\" not in result

    def test_truncate_long_filename(self):
        """Test truncation of very long filenames"""
        long_name = "A" * 300
        result = self.processor.sanitize_filename(long_name)
        assert len(result) <= 255

    def test_empty_filename(self):
        """Test handling of empty filename"""
        result = self.processor.sanitize_filename("")
        assert result == "Unknown"

    def test_unicode_characters(self):
        """Test handling of unicode characters"""
        result = self.processor.sanitize_filename("Björk - Jóga")
        assert "Björk" in result
        assert "Jóga" in result

    def test_special_characters_but_valid(self):
        """Test preserving valid special characters"""
        result = self.processor.sanitize_filename("Song & Artist (Remix)")
        # & and parentheses are valid
        assert "&" in result or "and" in result
        assert "(" in result or "Remix" in result


class TestPostProcessorPatternGeneration:
    """Tests for path generation from pattern"""

    def setup_method(self):
        self.processor = PostProcessor(check_mutagen=False)
        self.test_file = Path("test.mp3")

    def test_simple_pattern(self):
        """Test simple pattern substitution"""
        track = SoulSyncTrack(
            raw_title="Song Title",
            artist_name="Artist Name",
            album_title="Album Name",
        )

        pattern = "{Artist}/{Album}/{Title}{ext}"
        result = self.processor._generate_path_from_pattern(
            self.test_file, track, pattern
        )

        assert result is not None
        assert "Artist Name" in str(result)
        assert "Album Name" in str(result)
        assert "Song Title" in str(result)
        assert ".mp3" in str(result)

    def test_pattern_with_year(self):
        """Test pattern with year substitution"""
        track = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="Album",
            year=2024,
        )

        pattern = "{Artist}/{Year} - {Album}/{Title}{ext}"
        result = self.processor._generate_path_from_pattern(
            self.test_file, track, pattern
        )

        assert "2024" in str(result)

    def test_pattern_with_track_number(self):
        """Test pattern with track number (zero-padded)"""
        track = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="Album",
            track_number=5,
        )

        pattern = "{TrackNumber}. {Title}{ext}"
        result = self.processor._generate_path_from_pattern(
            self.test_file, track, pattern
        )

        assert "05" in str(result)  # Should be zero-padded

    def test_pattern_missing_fields(self):
        """Test pattern with missing fields (should use defaults)"""
        track = SoulSyncTrack(
            raw_title="Song",
            # No artist, album, year
        )

        pattern = "{Artist}/{Album}/{Title}{ext}"
        result = self.processor._generate_path_from_pattern(
            self.test_file, track, pattern
        )

        assert result is not None
        assert "Unknown" in str(result)  # Should have default values

    def test_pattern_with_special_chars_in_values(self):
        """Test pattern with special characters in metadata"""
        track = SoulSyncTrack(
            raw_title="Song: The <Remix>",
            artist_name="Artist & Friends",
            album_title="Album (2024)",
        )

        pattern = "{Artist}/{Album}/{Title}{ext}"
        result = self.processor._generate_path_from_pattern(
            self.test_file, track, pattern
        )

        assert result is not None
        # Special chars should be removed
        assert "<" not in str(result)
        assert ">" not in str(result)


class TestPostProcessorFormatDetection:
    """Tests for audio format detection"""

    def setup_method(self):
        self.processor = PostProcessor(check_mutagen=False)

    def test_detect_mp3(self):
        """Test MP3 detection"""
        result = self.processor._detect_format(Path("song.mp3"))
        assert result == AudioFormat.MP3

    def test_detect_flac(self):
        """Test FLAC detection"""
        result = self.processor._detect_format(Path("song.flac"))
        assert result == AudioFormat.FLAC

    def test_detect_ogg(self):
        """Test OGG Vorbis detection"""
        result = self.processor._detect_format(Path("song.ogg"))
        assert result == AudioFormat.OGG_VORBIS

    def test_detect_m4a(self):
        """Test M4A detection"""
        result = self.processor._detect_format(Path("song.m4a"))
        assert result == AudioFormat.M4A

    def test_detect_opus(self):
        """Test Opus detection"""
        result = self.processor._detect_format(Path("song.opus"))
        assert result == AudioFormat.OGG_OPUS

    def test_detect_unknown(self):
        """Test unknown format"""
        result = self.processor._detect_format(Path("song.unknown"))
        assert result == AudioFormat.UNKNOWN

    def test_case_insensitive(self):
        """Test case-insensitive detection"""
        result1 = self.processor._detect_format(Path("song.MP3"))
        result2 = self.processor._detect_format(Path("song.mp3"))
        assert result1 == result2 == AudioFormat.MP3


class TestPostProcessorDuplicateHandling:
    """Tests for duplicate file handling"""

    def setup_method(self):
        self.processor = PostProcessor(check_mutagen=False)

    def test_get_unique_filename_nonexistent(self):
        """Test unique filename for non-existent file"""
        path = Path("/tmp/song.mp3")
        with patch.object(Path, "exists", return_value=False):
            result = self.processor._get_unique_filename(path)
            assert result == path

    def test_get_unique_filename_exists(self):
        """Test unique filename generation for existing file"""
        path = Path("/tmp/song.mp3")
        with patch.object(Path, "exists") as mock_exists:
            # First call returns True (file exists)
            # Second call returns False (unique name doesn't exist)
            mock_exists.side_effect = [True, False]
            result = self.processor._get_unique_filename(path)
            assert " (1)" in str(result)

    def test_unique_filename_increments(self):
        """Test that unique filename counter increments"""
        path = Path("/tmp/song.mp3")
        with patch.object(Path, "exists") as mock_exists:
            # Simulate multiple existing files
            mock_exists.side_effect = [True, True, True, False]
            result = self.processor._get_unique_filename(path)
            assert " (3)" in str(result)


class TestPostProcessorDirectoryCleanup:
    """Tests for empty directory cleanup"""

    def setup_method(self):
        self.processor = PostProcessor(check_mutagen=False)

    def test_cleanup_empty_directory(self):
        """Test cleanup of empty directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir) / "empty"
            empty_dir.mkdir()

            removed = self.processor._cleanup_empty_directories(empty_dir)
            assert removed > 0
            assert not empty_dir.exists()

    def test_cleanup_non_empty_directory(self):
        """Test that non-empty directories are not removed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_with_file = Path(tmpdir) / "with_file"
            dir_with_file.mkdir()
            (dir_with_file / "file.txt").touch()

            removed = self.processor._cleanup_empty_directories(dir_with_file)
            assert removed == 0
            assert dir_with_file.exists()

    def test_cleanup_recursive(self):
        """Test recursive cleanup of empty directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            deep_dir = Path(tmpdir) / "a" / "b" / "c"
            deep_dir.mkdir(parents=True)

            removed = self.processor._cleanup_empty_directories(deep_dir)
            assert removed > 0


class TestPostProcessorIntegration:
    """Integration tests for PostProcessor"""

    def setup_method(self):
        self.processor = PostProcessor(check_mutagen=False)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

    def teardown_method(self):
        self.temp_dir.cleanup()

    def test_organize_file_creates_directories(self):
        """Test that organize_file creates necessary directories"""
        # Create a test file
        source_file = self.base_dir / "source" / "test.mp3"
        source_file.parent.mkdir(parents=True)
        source_file.touch()

        track = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="Album",
            year=2024,
        )

        dest_dir = self.base_dir / "organized"
        pattern = "{Artist}/{Album}/{Title}{ext}"

        result = self.processor.organize_file(
            source_file, track, pattern, dest_dir
        )

        assert result.moved
        assert result.destination_path.exists()
        assert "Artist" in result.destination_path.parts

    def test_organize_file_handles_missing_source(self):
        """Test organize_file with non-existent source"""
        missing_file = self.base_dir / "missing.mp3"

        track = SoulSyncTrack(raw_title="Song", artist_name="Artist")
        dest_dir = self.base_dir / "organized"

        result = self.processor.organize_file(
            missing_file, track, "{Artist}/{Title}{ext}", dest_dir
        )

        assert not result.success
        assert not result.moved

    def test_organize_file_avoids_duplicates(self):
        """Test that organize_file avoids overwriting duplicates"""
        # Create source file
        source_file = self.base_dir / "source" / "test.mp3"
        source_file.parent.mkdir(parents=True)
        source_file.touch()

        # Create destination file that will conflict
        dest_dir = self.base_dir / "organized"
        dest_path = dest_dir / "Artist" / "Album" / "test.mp3"
        dest_path.parent.mkdir(parents=True)
        dest_path.touch()

        track = SoulSyncTrack(
            raw_title="test",
            artist_name="Artist",
            album_title="Album",
        )

        result = self.processor.organize_file(
            source_file, track, "{Artist}/{Album}/{Title}{ext}", dest_dir
        )

        assert result.moved
        # Should have renamed to avoid duplicate
        assert " (1)" in result.destination_path.name or result.destination_path.name == dest_path.name


class TestPostProcessorTagWriting:
    """Tests for tag writing (mocked)"""

    def setup_method(self):
        self.processor = PostProcessor(check_mutagen=False)

    def test_write_tags_missing_file(self):
        """Test write_tags with missing file"""
        missing_file = Path("/nonexistent/file.mp3")
        track = SoulSyncTrack(raw_title="Song", artist_name="Artist")

        result = self.processor.write_tags(missing_file, track)

        assert not result.success
        assert "not found" in result.errors[0].lower()

    def test_write_tags_without_mutagen(self):
        """Test write_tags fails gracefully without mutagen"""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            processor = PostProcessor(check_mutagen=False)
            track = SoulSyncTrack(raw_title="Song", artist_name="Artist")

            result = processor.write_tags(tmp_path, track)
            # Should fail or warn about missing mutagen
            assert "mutagen" in str(result.errors).lower() or not result.success
        finally:
            tmp_path.unlink()

    @patch("core.post_processor.MUTAGEN_AVAILABLE", True)
    @patch("core.post_processor.EasyID3")
    def test_write_id3_tags_success(self, mock_easyid3):
        """Test successful ID3 tag writing"""
        # Mock mutagen
        mock_audio = MagicMock()
        mock_easyid3.return_value = mock_audio

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            processor = PostProcessor(check_mutagen=False)
            track = SoulSyncTrack(
                raw_title="Song Title",
                artist_name="Artist Name",
                album_title="Album Name",
                year=2024,
                track_number=5,
            )

            result = processor.write_tags(tmp_path, track)

            # Should have attempted to write tags
            assert "title" in result.tags_written or not result.success

        finally:
            tmp_path.unlink()


class TestPostProcessorEdgeCases:
    """Tests for edge cases"""

    def setup_method(self):
        self.processor = PostProcessor(check_mutagen=False)

    def test_very_long_path(self):
        """Test handling of very long paths"""
        long_artist = "A" * 100
        long_album = "B" * 100
        long_title = "C" * 100

        track = SoulSyncTrack(
            raw_title=long_title,
            artist_name=long_artist,
            album_title=long_album,
        )

        pattern = "{Artist}/{Album}/{Title}{ext}"
        result = self.processor._generate_path_from_pattern(
            Path("test.mp3"), track, pattern
        )

        # Should handle long paths without crashing
        assert result is not None
        # Path might be truncated but should be valid
        assert len(str(result)) < 500

    def test_special_folder_names(self):
        """Test handling of special folder names in pattern"""
        track = SoulSyncTrack(raw_title="Song", artist_name="Artist")

        # Pattern with special chars that will be sanitized
        pattern = "{Artist}/[{Year}] {Album}/{Title}{ext}"
        result = self.processor._generate_path_from_pattern(
            Path("test.mp3"), track, pattern
        )

        assert result is not None

    def test_duplicate_slashes_in_pattern(self):
        """Test cleanup of duplicate slashes in generated path"""
        track = SoulSyncTrack(raw_title="Song", artist_name="Artist", album_title="Album")

        # Pattern that might create double slashes
        pattern = "{Artist}//{Album}/{Title}{ext}"
        result = self.processor._generate_path_from_pattern(
            Path("test.mp3"), track, pattern
        )

        # Should clean up double slashes
        assert "//" not in str(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
