"""
Metadata Enhancer Service - Post-processing pipeline for identifying and tagging audio.

This service orchestrates the identification, tagging, and organization of downloaded files.
It uses Capability-based discovery to find:
- Fingerprinting providers (e.g., AcoustID)
- Metadata providers (e.g., MusicBrainz)

Workflow:
1. Fingerprint audio
2. Resolve fingerprint to MusicBrainz ID (MBID)
3. Fetch detailed metadata from MusicBrainz
4. Tag file with standard tags + MusicBrainz IDs (TXXX)
5. Rename and move to library
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from core.enums import Capability
from core.provider import ProviderRegistry
from core.job_queue import register_job
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine import text_utils
from core.settings import config_manager
from core.tiered_logger import get_logger

# Optional Mutagen imports
try:
    import mutagen
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3, TXXX, APIC
    from mutagen.flac import FLAC, Picture
    from mutagen.oggvorbis import OggVorbis
    from mutagen.mp4 import MP4, MP4Cover
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

logger = get_logger("services.metadata_enhancer")

class MetadataEnhancerService:
    _instance = None

    def __init__(self):
        self.library_root = config_manager.get_library_dir()
        self._register_jobs()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MetadataEnhancerService()
        return cls._instance

    def _register_jobs(self):
        """Register background jobs"""
        register_job(
            name="metadata_enhancer_scan",
            func=self.scan_and_process,
            interval_seconds=300,  # 5 minutes
            enabled=True,
            tags=["soulsync", "metadata"],
            max_retries=3
        )

    def scan_and_process(self):
        """Scan download directory for audio files and process them."""
        download_dir = config_manager.get_download_dir()
        if not download_dir.exists():
            return

        supported_exts = {'.mp3', '.flac', '.ogg', '.m4a', '.wav'}
        files_to_process = []

        for root, dirs, files in os.walk(download_dir):
            for file in files:
                path = Path(root) / file
                if path.suffix.lower() in supported_exts:
                    files_to_process.append(path)

        if files_to_process:
            logger.info(f"Found {len(files_to_process)} files to process")
            self.process_batch(files_to_process)

    def _get_provider(self, capability: Capability):
        """Get the first available provider with the given capability."""
        # Use plugin_loader as requested by architectural standards
        from core.plugin_loader import get_provider
        return get_provider(capability)

    def process_batch(self, files: List[Path]):
        """
        Process a batch of files: Identify -> Tag -> Move.
        """
        fingerprint_provider = self._get_provider(Capability.RESOLVE_FINGERPRINT)
        metadata_provider = self._get_provider(Capability.FETCH_METADATA)

        if not fingerprint_provider:
            logger.warning("No fingerprint provider available (Capability.RESOLVE_FINGERPRINT)")
        if not metadata_provider:
            logger.warning("No metadata provider available (Capability.FETCH_METADATA)")

        for file_path in files:
            if not file_path.exists():
                continue

            logger.info(f"Processing file: {file_path}")

            try:
                # Step A: Fingerprint
                fingerprint = FingerprintGenerator.generate(str(file_path))
                duration = self._get_audio_duration(file_path)

                metadata = None

                # Step B: Resolve Fingerprint
                if fingerprint and duration and fingerprint_provider:
                    logger.debug(f"Resolving fingerprint for {file_path.name}")
                    mbids = fingerprint_provider.resolve_fingerprint(fingerprint, int(duration))

                    if mbids and metadata_provider:
                        # Step C: Fetch Metadata from MBID
                        # Use first MBID
                        mbid = mbids[0]
                        logger.info(f"Identified MBID {mbid} for {file_path.name}")
                        metadata = metadata_provider.get_metadata(mbid)

                # Fallback: Search by filename
                if not metadata and metadata_provider:
                    logger.info(f"Fingerprint resolution failed/skipped. Falling back to filename search for {file_path.name}")
                    # Simple filename cleanup
                    query = file_path.stem.replace('_', ' ').replace('-', ' ')
                    results = metadata_provider.search_metadata(query, limit=1)
                    if results:
                        candidate = results[0]
                        mbid = candidate.get('mbid')
                        if mbid:
                            metadata = metadata_provider.get_metadata(mbid)

                if metadata:
                    # Step D: Tag
                    self._tag_file(file_path, metadata)

                    # Step E: Rename and Move
                    self._move_file(file_path, metadata)
                else:
                    logger.warning(f"Could not identify metadata for {file_path.name}")

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}", exc_info=True)

        # Cleanup source directories (if they are empty)
        # Assuming files came from the same source root, we can try to clean up their parents
        processed_parents = set(f.parent for f in files if f.exists() or not f.exists()) # f.exists() check is tricky if moved
        # Better: Since we moved files, we should check their original parent folders.
        # But we only have the original path in 'files' list.
        for f in files:
            # Check if parent still exists and is empty
            self._cleanup_empty_directories(f.parent)

    def _get_audio_duration(self, file_path: Path) -> Optional[int]:
        """Get audio duration in seconds using Mutagen."""
        if not MUTAGEN_AVAILABLE:
            return None
        try:
            audio = mutagen.File(str(file_path))
            if audio and audio.info:
                return int(audio.info.length)
        except Exception:
            return None
        return None

    def _tag_file(self, file_path: Path, metadata: Dict[str, Any]):
        """
        Write tags using Mutagen.
        Writes standard tags + TXXX MusicBrainz IDs.
        """
        if not MUTAGEN_AVAILABLE:
            logger.warning("Mutagen not available, skipping tagging")
            return

        try:
            ext = file_path.suffix.lower()

            if ext == '.mp3':
                self._tag_mp3(file_path, metadata)
            elif ext == '.flac':
                self._tag_flac(file_path, metadata)
            # Add other formats as needed

            logger.info(f"Tagged {file_path.name}")

        except Exception as e:
            logger.error(f"Failed to tag {file_path}: {e}")

    def _tag_mp3(self, file_path: Path, metadata: Dict[str, Any]):
        """Tag MP3 with ID3v2.4"""
        try:
            # Ensure ID3 tags exist
            try:
                audio = ID3(str(file_path))
            except Exception:
                audio = ID3()

            # Helper to set text frame
            from mutagen.id3 import TIT2, TPE1, TALB, TDRC, TXXX, TRCK, TPOS

            if metadata.get('title'):
                audio.add(TIT2(encoding=3, text=metadata['title']))
            if metadata.get('artist'):
                audio.add(TPE1(encoding=3, text=metadata['artist']))
            if metadata.get('album'):
                audio.add(TALB(encoding=3, text=metadata['album']))
            if metadata.get('date'):
                audio.add(TDRC(encoding=3, text=metadata['date']))
            if metadata.get('track_number'):
                audio.add(TRCK(encoding=3, text=str(metadata['track_number'])))
            if metadata.get('disc_number'):
                audio.add(TPOS(encoding=3, text=str(metadata['disc_number'])))

            # Critical MusicBrainz IDs (TXXX)
            if metadata.get('recording_id'):
                audio.add(TXXX(encoding=3, desc='MusicBrainz Track Id', text=metadata['recording_id']))
            if metadata.get('artist_id'):
                audio.add(TXXX(encoding=3, desc='MusicBrainz Artist Id', text=metadata['artist_id']))
            if metadata.get('release_id'):
                audio.add(TXXX(encoding=3, desc='MusicBrainz Release Id', text=metadata['release_id']))

            audio.save(str(file_path), v2_version=4)

        except Exception as e:
            logger.error(f"Error tagging MP3: {e}")

    def _tag_flac(self, file_path: Path, metadata: Dict[str, Any]):
        """Tag FLAC with Vorbis Comments"""
        try:
            audio = FLAC(str(file_path))

            if metadata.get('title'):
                audio['TITLE'] = metadata['title']
            if metadata.get('artist'):
                audio['ARTIST'] = metadata['artist']
            if metadata.get('album'):
                audio['ALBUM'] = metadata['album']
            if metadata.get('date'):
                audio['DATE'] = metadata['date']
            if metadata.get('track_number'):
                audio['TRACKNUMBER'] = str(metadata['track_number'])
            if metadata.get('disc_number'):
                audio['DISCNUMBER'] = str(metadata['disc_number'])

            # MusicBrainz IDs (Vorbis style)
            # Mapping TXXX to Vorbis comments often uses MUSICBRAINZ_... keys
            if metadata.get('recording_id'):
                audio['MUSICBRAINZ_TRACKID'] = metadata['recording_id']
            if metadata.get('artist_id'):
                audio['MUSICBRAINZ_ARTISTID'] = metadata['artist_id']
            if metadata.get('release_id'):
                audio['MUSICBRAINZ_ALBUMID'] = metadata['release_id']

            audio.save()

        except Exception as e:
            logger.error(f"Error tagging FLAC: {e}")

    def _move_file(self, file_path: Path, metadata: Dict[str, Any]):
        """
        Rename and move file to library.
        Format: /{Artist}/{Album}/{Track} - {Title}.ext
        """
        try:
            artist = self._sanitize(metadata.get('artist') or "Unknown Artist")
            album = self._sanitize(metadata.get('album') or "Unknown Album")
            title = self._sanitize(metadata.get('title') or file_path.stem)

            # Track Number padding
            track_num = metadata.get('track_number')
            if track_num:
                try:
                    track_padded = f"{int(track_num):02d}"
                except ValueError:
                    track_padded = self._sanitize(str(track_num))
            else:
                track_padded = "00"

            # Extension
            ext = file_path.suffix.lower()

            # Destination Path: {Artist}/{Album}/{Track} - {Title}.ext
            rel_path = Path(artist) / album / f"{track_padded} - {title}{ext}"
            dest_path = self.library_root / rel_path

            if dest_path.exists() and dest_path != file_path:
                # Handle duplicate
                stem = dest_path.stem
                dest_path = dest_path.with_name(f"{stem}_{file_path.stat().st_size}{ext}")

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(file_path), str(dest_path))
            logger.info(f"Moved to {dest_path}")

        except Exception as e:
            logger.error(f"Failed to move file {file_path}: {e}")

    def _sanitize(self, filename: str) -> str:
        """Sanitize filename components"""
        import re
        # Remove illegal characters
        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename).strip()

    def _cleanup_empty_directories(self, directory: Path):
        """Recursively remove empty directories."""
        try:
            if not directory.exists():
                return

            # Stop if we hit download dir root or something (simple check)
            # Assuming directory is inside downloads or similar.

            if not any(directory.iterdir()):
                directory.rmdir()
                logger.debug(f"Removed empty directory: {directory}")
                self._cleanup_empty_directories(directory.parent)
        except Exception:
            pass

# Global Accessor
def get_metadata_enhancer():
    return MetadataEnhancerService.get_instance()

def register_metadata_enhancer_service():
    """
    Initialize the metadata enhancer service and register its background jobs.
    This should be called during application startup to ensure the service
    and its scheduled jobs are available.
    """
    service = MetadataEnhancerService.get_instance()
    logger.info("Metadata Enhancer Service initialized and jobs registered")
