"""
PostProcessor Service - Audio tagging and file organization

This service handles:
1. Writing metadata tags (ID3 for MP3, Vorbis for FLAC/OGG, etc.)
2. Downloading and embedding cover art
3. Sanitizing filenames and paths
4. Handling duplicate files
5. Organizing files into folders using pattern substitution
6. Cross-partition file moves
7. Directory cleanup

Supports mutagen for tag writing across all formats.
"""

import re
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple, List
from urllib.request import urlopen
from urllib.error import URLError
from dataclasses import dataclass
from enum import Enum

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.flac import FLAC, Picture as FLACPicture
    from mutagen.oggvorbis import OggVorbis
    from mutagen.oggopus import OggOpus
    from mutagen.oggflac import OggFLAC
    from mutagen import File
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

from .matching_engine import SoulSyncTrack

logger = logging.getLogger(__name__)


class AudioFormat(Enum):
    """Supported audio formats"""
    MP3 = "mp3"
    FLAC = "flac"
    OGG_VORBIS = "ogg"
    OGG_OPUS = "opus"
    M4A = "m4a"
    WAV = "wav"
    WMA = "wma"
    UNKNOWN = "unknown"


@dataclass
class TagWriteResult:
    """Result of writing tags to a file"""
    success: bool
    file_path: Path
    format: AudioFormat
    tags_written: List[str]
    errors: List[str]


@dataclass
class FileOrganizeResult:
    """Result of organizing a file"""
    success: bool
    source_path: Path
    destination_path: Path
    moved: bool
    errors: List[str]


class PostProcessor:
    """
    Service for post-processing audio files with metadata and organization
    """

    # Illegal characters in filenames (platform-agnostic)
    ILLEGAL_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

    # Maximum filename length (varies by filesystem, 255 is safe)
    MAX_FILENAME_LENGTH = 255

    def __init__(self, check_mutagen: bool = True):
        """
        Initialize PostProcessor

        Args:
            check_mutagen: Raise error if mutagen not available
        """
        if check_mutagen and not MUTAGEN_AVAILABLE:
            logger.warning("mutagen not available - tagging will fail")

    def write_tags(
        self,
        file_path: Path,
        track: SoulSyncTrack,
        cover_art_url: Optional[str] = None,
        preserve_existing: bool = False,
    ) -> TagWriteResult:
        """
        Write metadata tags to audio file

        Args:
            file_path: Path to audio file
            track: SoulSyncTrack with metadata
            cover_art_url: URL to cover art image
            preserve_existing: Keep existing tags that aren't being overwritten

        Returns:
            TagWriteResult with success status and details
        """

        if not file_path.exists():
            return TagWriteResult(
                success=False,
                file_path=file_path,
                format=AudioFormat.UNKNOWN,
                tags_written=[],
                errors=[f"File not found: {file_path}"],
            )

        if not MUTAGEN_AVAILABLE:
            return TagWriteResult(
                success=False,
                file_path=file_path,
                format=AudioFormat.UNKNOWN,
                tags_written=[],
                errors=["mutagen library not available"],
            )

        # Detect format
        audio_format = self._detect_format(file_path)

        try:
            tags_written = []
            errors = []

            # Try to open and modify file
            if audio_format == AudioFormat.MP3:
                tags_written, errors = self._write_id3_tags(file_path, track)

            elif audio_format == AudioFormat.FLAC:
                tags_written, errors = self._write_flac_tags(file_path, track)

            elif audio_format in (AudioFormat.OGG_VORBIS, AudioFormat.OGG_OPUS):
                tags_written, errors = self._write_vorbis_tags(file_path, track)

            elif audio_format == AudioFormat.M4A:
                tags_written, errors = self._write_m4a_tags(file_path, track)

            # Add cover art if available
            if cover_art_url and tags_written:
                cover_success, cover_errors = self._embed_cover_art(
                    file_path, audio_format, cover_art_url
                )
                if cover_success:
                    tags_written.append("cover_art")
                errors.extend(cover_errors)

            return TagWriteResult(
                success=len(errors) == 0,
                file_path=file_path,
                format=audio_format,
                tags_written=tags_written,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"Error writing tags to {file_path}: {e}")
            return TagWriteResult(
                success=False,
                file_path=file_path,
                format=audio_format,
                tags_written=[],
                errors=[str(e)],
            )

    def organize_file(
        self,
        file_path: Path,
        track: SoulSyncTrack,
        pattern: str,
        destination_dir: Path,
        handle_duplicates: bool = True,
    ) -> FileOrganizeResult:
        """
        Organize file using pattern substitution

        Args:
            file_path: Source file path
            track: SoulSyncTrack with metadata
            pattern: Pattern like "{Artist}/{Year} - {Album}/{Title}{ext}"
            destination_dir: Base destination directory
            handle_duplicates: Handle duplicate filenames

        Returns:
            FileOrganizeResult with success status and new path
        """

        if not file_path.exists():
            return FileOrganizeResult(
                success=False,
                source_path=file_path,
                destination_path=file_path,
                moved=False,
                errors=[f"Source file not found: {file_path}"],
            )

        try:
            # Generate new path from pattern
            new_relative_path = self._generate_path_from_pattern(file_path, track, pattern)

            if not new_relative_path:
                return FileOrganizeResult(
                    success=False,
                    source_path=file_path,
                    destination_path=file_path,
                    moved=False,
                    errors=["Failed to generate destination path from pattern"],
                )

            # Full destination path
            destination_path = destination_dir / new_relative_path

            # Handle duplicates if destination already exists
            if destination_path.exists() and destination_path != file_path:
                if handle_duplicates:
                    destination_path = self._get_unique_filename(destination_path)
                    logger.info(f"Renamed to avoid duplicate: {destination_path}")
                else:
                    return FileOrganizeResult(
                        success=False,
                        source_path=file_path,
                        destination_path=destination_path,
                        moved=False,
                        errors=[f"Destination already exists: {destination_path}"],
                    )

            # Create parent directories
            destination_path.parent.mkdir(parents=True, exist_ok=True)

            # Move file (handles cross-partition moves)
            try:
                shutil.move(str(file_path), str(destination_path))
                logger.info(f"Moved {file_path} → {destination_path}")
            except Exception as e:
                logger.error(f"Failed to move file: {e}")
                return FileOrganizeResult(
                    success=False,
                    source_path=file_path,
                    destination_path=destination_path,
                    moved=False,
                    errors=[str(e)],
                )

            # Clean up empty directories in source hierarchy
            self._cleanup_empty_directories(file_path.parent)

            return FileOrganizeResult(
                success=True,
                source_path=file_path,
                destination_path=destination_path,
                moved=True,
                errors=[],
            )

        except Exception as e:
            logger.error(f"Error organizing file {file_path}: {e}")
            return FileOrganizeResult(
                success=False,
                source_path=file_path,
                destination_path=file_path,
                moved=False,
                errors=[str(e)],
            )

    def _detect_format(self, file_path: Path) -> AudioFormat:
        """Detect audio format from file extension"""
        ext = file_path.suffix.lower()

        format_map = {
            ".mp3": AudioFormat.MP3,
            ".flac": AudioFormat.FLAC,
            ".ogg": AudioFormat.OGG_VORBIS,
            ".opus": AudioFormat.OGG_OPUS,
            ".m4a": AudioFormat.M4A,
            ".aac": AudioFormat.M4A,
            ".wav": AudioFormat.WAV,
            ".wma": AudioFormat.WMA,
        }

        return format_map.get(ext, AudioFormat.UNKNOWN)

    def _write_id3_tags(self, file_path: Path, track: SoulSyncTrack) -> Tuple[List[str], List[str]]:
        """Write ID3v2 tags to MP3 file"""
        tags = []
        errors = []

        try:
            audio = EasyID3(str(file_path))
        except Exception:
            # File might not have ID3 tags yet
            try:
                audio = EasyID3()
            except Exception as e:
                return tags, [f"Failed to create ID3 tags: {e}"]

        try:
            # Basic tags
            if track.title:
                audio["title"] = track.title
                tags.append("title")

            if track.artist:
                audio["artist"] = track.artist
                tags.append("artist")

            if track.album:
                audio["album"] = track.album
                tags.append("album")

            if track.year:
                audio["date"] = str(track.year)
                tags.append("year")

            if track.track_number:
                audio["tracknumber"] = str(track.track_number)
                tags.append("track_number")

            if track.disc_number:
                audio["discnumber"] = str(track.disc_number)
                tags.append("disc_number")

            if track.version:
                audio["comment"] = track.version
                tags.append("version")

            # Save tags
            audio.save(str(file_path), v2_version=4)

        except Exception as e:
            errors.append(f"Error writing ID3 tags: {e}")

        return tags, errors

    def _write_flac_tags(self, file_path: Path, track: SoulSyncTrack) -> Tuple[List[str], List[str]]:
        """Write Vorbis tags to FLAC file"""
        tags = []
        errors = []

        try:
            audio = FLAC(str(file_path))
        except Exception as e:
            return tags, [f"Failed to open FLAC file: {e}"]

        try:
            if track.title:
                audio["title"] = [track.title]
                tags.append("title")

            if track.artist:
                audio["artist"] = [track.artist]
                tags.append("artist")

            if track.album:
                audio["album"] = [track.album]
                tags.append("album")

            if track.year:
                audio["date"] = [str(track.year)]
                tags.append("year")

            if track.track_number:
                audio["tracknumber"] = [str(track.track_number)]
                tags.append("track_number")

            if track.disc_number:
                audio["discnumber"] = [str(track.disc_number)]
                tags.append("disc_number")

            if track.version:
                audio["comment"] = [track.version]
                tags.append("version")

            audio.save()

        except Exception as e:
            errors.append(f"Error writing FLAC tags: {e}")

        return tags, errors

    def _write_vorbis_tags(self, file_path: Path, track: SoulSyncTrack) -> Tuple[List[str], List[str]]:
        """Write Vorbis comments to OGG file"""
        tags = []
        errors = []

        try:
            if file_path.suffix.lower() == ".opus":
                audio = OggOpus(str(file_path))
            else:
                audio = OggVorbis(str(file_path))
        except Exception as e:
            return tags, [f"Failed to open OGG file: {e}"]

        try:
            if track.title:
                audio["title"] = [track.title]
                tags.append("title")

            if track.artist:
                audio["artist"] = [track.artist]
                tags.append("artist")

            if track.album:
                audio["album"] = [track.album]
                tags.append("album")

            if track.year:
                audio["date"] = [str(track.year)]
                tags.append("year")

            if track.track_number:
                audio["tracknumber"] = [str(track.track_number)]
                tags.append("track_number")

            if track.disc_number:
                audio["discnumber"] = [str(track.disc_number)]
                tags.append("disc_number")

            if track.version:
                audio["comment"] = [track.version]
                tags.append("version")

            audio.save()

        except Exception as e:
            errors.append(f"Error writing Vorbis tags: {e}")

        return tags, errors

    def _write_m4a_tags(self, file_path: Path, track: SoulSyncTrack) -> Tuple[List[str], List[str]]:
        """Write tags to M4A/AAC file"""
        tags = []
        errors = []

        try:
            audio = File(str(file_path))
            if audio is None:
                return tags, ["Failed to open M4A file"]
        except Exception as e:
            return tags, [f"Error opening M4A file: {e}"]

        try:
            if track.title:
                audio["\xa9nam"] = [track.title]
                tags.append("title")

            if track.artist:
                audio["\xa9ART"] = [track.artist]
                tags.append("artist")

            if track.album:
                audio["\xa9alb"] = [track.album]
                tags.append("album")

            if track.year:
                audio["\xa9day"] = [str(track.year)]
                tags.append("year")

            if track.track_number:
                audio["trkn"] = [(track.track_number, 0)]
                tags.append("track_number")

            if track.disc_number:
                audio["disk"] = [(track.disc_number, 0)]
                tags.append("disc_number")

            if track.version:
                audio["\xa9cmt"] = [track.version]
                tags.append("version")

            audio.save()

        except Exception as e:
            errors.append(f"Error writing M4A tags: {e}")

        return tags, errors

    def _embed_cover_art(
        self,
        file_path: Path,
        audio_format: AudioFormat,
        cover_url: str,
    ) -> Tuple[bool, List[str]]:
        """Download and embed cover art"""
        errors = []

        try:
            # Download cover art
            logger.debug(f"Downloading cover art from {cover_url}")
            with urlopen(cover_url, timeout=10) as response:
                image_data = response.read()

            if audio_format == AudioFormat.FLAC:
                return self._embed_flac_cover(file_path, image_data)
            elif audio_format == AudioFormat.MP3:
                return self._embed_id3_cover(file_path, image_data)
            else:
                errors.append(f"Cover art embedding not supported for {audio_format.value}")
                return False, errors

        except URLError as e:
            errors.append(f"Failed to download cover art: {e}")
            return False, errors
        except Exception as e:
            errors.append(f"Error embedding cover art: {e}")
            return False, errors

    def _embed_flac_cover(self, file_path: Path, image_data: bytes) -> Tuple[bool, List[str]]:
        """Embed cover art in FLAC file"""
        try:
            audio = FLAC(str(file_path))
            picture = FLACPicture()
            picture.data = image_data
            picture.type = 3  # Front cover
            audio.add_picture(picture)
            audio.save()
            return True, []
        except Exception as e:
            return False, [f"Error embedding FLAC cover: {e}"]

    def _embed_id3_cover(self, file_path: Path, image_data: bytes) -> Tuple[bool, List[str]]:
        """Embed cover art in ID3 tags"""
        try:
            audio = EasyID3(str(file_path))
            # ID3 requires APIC frame - use mutagen's File API instead
            audio_file = File(str(file_path))
            if audio_file is not None:
                from mutagen.id3 import ID3, APIC
                id3 = ID3(str(file_path))
                id3.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=image_data))
                id3.save(v2_version=4)
            return True, []
        except Exception as e:
            return False, [f"Error embedding ID3 cover: {e}"]

    def _generate_path_from_pattern(
        self,
        file_path: Path,
        track: SoulSyncTrack,
        pattern: str,
    ) -> Optional[Path]:
        """
        Generate file path from pattern substitution

        Pattern example: "{Artist}/{Year} - {Album}/{TrackNumber}. {Title}{ext}"
        """

        try:
            # Prepare substitution values
            substitutions = {
                "{Artist}": self.sanitize_filename(track.artist or "Unknown Artist"),
                "{Album}": self.sanitize_filename(track.album or "Unknown Album"),
                "{Title}": self.sanitize_filename(track.title or "Unknown Track"),
                "{Year}": str(track.year) if track.year else "Unknown",
                "{TrackNumber}": str(track.track_number).zfill(2) if track.track_number else "00",
                "{DiscNumber}": str(track.disc_number) if track.disc_number else "1",
                "{Version}": self.sanitize_filename(track.version or ""),
                "{ext}": file_path.suffix.lower(),
            }

            # Perform substitutions
            result = pattern
            for placeholder, value in substitutions.items():
                result = result.replace(placeholder, value)

            # Clean up double slashes
            result = re.sub(r"/{2,}", "/", result)

            # Create Path and validate
            path = Path(result)

            # Check total path length
            if len(str(path)) > 260:  # Windows MAX_PATH limit
                logger.warning(f"Generated path exceeds 260 chars: {path}")
                # Truncate filename
                parts = path.parts[:-1]  # Everything except filename
                filename = path.parts[-1]
                max_filename_len = 260 - len(str(Path(*parts))) - 1
                filename = filename[: max(max_filename_len, 30)]
                path = Path(*parts, filename)

            return path

        except Exception as e:
            logger.error(f"Error generating path from pattern: {e}")
            return None

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing illegal characters

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """

        if not filename:
            return "Unknown"

        # Remove illegal characters
        sanitized = re.sub(self.ILLEGAL_CHARS, "", filename)

        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip(". ")

        # Collapse multiple spaces
        sanitized = re.sub(r"\s+", " ", sanitized)

        # Truncate to max length
        if len(sanitized) > self.MAX_FILENAME_LENGTH:
            sanitized = sanitized[: self.MAX_FILENAME_LENGTH - 4] + "...."

        return sanitized or "Unknown"

    def _get_unique_filename(self, file_path: Path) -> Path:
        """
        Generate unique filename if file exists

        Example: song.mp3 → song (1).mp3 → song (2).mp3
        """

        if not file_path.exists():
            return file_path

        stem = file_path.stem
        suffix = file_path.suffix
        parent = file_path.parent

        counter = 1
        while True:
            new_name = f"{stem} ({counter}){suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1

    def _cleanup_empty_directories(self, directory: Path, max_depth: int = 10) -> int:
        """
        Recursively clean up empty directories

        Args:
            directory: Starting directory
            max_depth: Maximum recursion depth (safety limit)

        Returns:
            Number of directories removed
        """

        if max_depth <= 0 or not directory.exists():
            return 0

        removed = 0

        try:
            # Don't go above workspace root
            if directory.parent == directory:
                return removed

            # Check if directory is empty
            if not any(directory.iterdir()):
                try:
                    directory.rmdir()
                    logger.debug(f"Removed empty directory: {directory}")
                    removed = 1

                    # Try to clean parent
                    removed += self._cleanup_empty_directories(directory.parent, max_depth - 1)
                except OSError as e:
                    logger.debug(f"Could not remove directory {directory}: {e}")

        except Exception as e:
            logger.debug(f"Error cleaning up directories: {e}")

        return removed


def get_post_processor() -> PostProcessor:
    """Get or create PostProcessor instance"""
    return PostProcessor()
