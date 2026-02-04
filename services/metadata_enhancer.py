"""
Metadata Enhancer Service - Service for identifying and tagging audio.

This service focuses on:
1. Fingerprinting audio (AcoustID)
2. Fetching metadata (MusicBrainz)
3. Tagging files (Mutagen)
4. Managing the Review Queue (Database)

It does NOT move files or scan directories (see AutoImportService).
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import datetime

from core.enums import Capability
from core.settings import config_manager
from core.tiered_logger import get_logger
from core.matching_engine.fingerprinting import FingerprintGenerator
from database import get_database
from database.music_database import ReviewTask

# Optional Mutagen imports
try:
    import mutagen
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3, TXXX, APIC, TIT2, TPE1, TALB, TDRC, TRCK, TPOS
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
        pass

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MetadataEnhancerService()
        return cls._instance

    def _get_provider(self, capability: Capability):
        """Get the first available provider with the given capability."""
        from core.plugin_loader import get_provider
        return get_provider(capability)

    def identify_file(self, file_path: Path) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Identify a file using Fingerprinting and/or Metadata Search.
        Returns (metadata, confidence_score).
        """
        fingerprint_provider = self._get_provider(Capability.RESOLVE_FINGERPRINT)
        metadata_provider = self._get_provider(Capability.FETCH_METADATA)

        metadata = None
        confidence = 0.0

        try:
            # Step A: Fingerprint
            fingerprint = FingerprintGenerator.generate(str(file_path))
            duration = self._get_audio_duration(file_path)

            if fingerprint and duration and fingerprint_provider:
                logger.debug(f"Resolving fingerprint for {file_path.name}")
                mbids = fingerprint_provider.resolve_fingerprint(fingerprint, int(duration))

                if mbids and metadata_provider:
                    mbid = mbids[0]
                    logger.info(f"Identified MBID {mbid} for {file_path.name}")
                    metadata = metadata_provider.get_metadata(mbid)
                    if metadata:
                        confidence = 0.95

            # Fallback: Search by filename
            if not metadata and metadata_provider:
                logger.info(f"Fingerprint resolution failed/skipped. Falling back to filename search for {file_path.name}")
                query = file_path.stem.replace('_', ' ').replace('-', ' ')
                results = metadata_provider.search_metadata(query, limit=1)
                if results:
                    candidate = results[0]
                    mbid = candidate.get('mbid')
                    score = candidate.get('score', 0)
                    confidence = score / 100.0 if score else 0.5

                    if mbid:
                        metadata = metadata_provider.get_metadata(mbid)

        except Exception as e:
            logger.error(f"Error identifying {file_path}: {e}")

        return metadata, confidence

    def tag_file(self, file_path: Path, metadata: Dict[str, Any]):
        """
        Write tags using Mutagen. Public wrapper.
        """
        self._tag_file(file_path, metadata)

    def _tag_file(self, file_path: Path, metadata: Dict[str, Any]):
        """
        Internal: Write tags using Mutagen.
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

    def create_or_update_review_task(self, file_path: Path, metadata: Optional[Dict[str, Any]], confidence: float, status='pending'):
        """Create or update a task in the review queue."""
        try:
            db = get_database()
            with db.session_scope() as session:
                existing = session.query(ReviewTask).filter(ReviewTask.file_path == str(file_path)).first()
                if existing:
                    existing.detected_metadata = metadata
                    existing.confidence_score = confidence
                    existing.status = status
                    existing.created_at = datetime.datetime.utcnow()
                else:
                    task = ReviewTask(
                        file_path=str(file_path),
                        status=status,
                        detected_metadata=metadata,
                        confidence_score=confidence
                    )
                    session.add(task)
            logger.info(f"Review Task {status}: {file_path}")
        except Exception as e:
            logger.error(f"Failed to update review task: {e}")

    def approve_match(self, file_path: Path, metadata: Dict[str, Any]):
        """
        Approve a match manually.
        Delegates to AutoImportService to finalize (Tag & Move).
        """
        from services.auto_importer import get_auto_importer

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        auto_importer = get_auto_importer()
        auto_importer.finalize_import(file_path, metadata)

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

    def _tag_mp3(self, file_path: Path, metadata: Dict[str, Any]):
        """Tag MP3 with ID3v2.4"""
        try:
            try:
                audio = ID3(str(file_path))
            except Exception:
                audio = ID3()

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
            if metadata.get('isrc'):
                from mutagen.id3 import TSRC
                audio.add(TSRC(encoding=3, text=metadata['isrc']))
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
            if metadata.get('isrc'):
                audio['ISRC'] = metadata['isrc']
            if metadata.get('recording_id'):
                audio['MUSICBRAINZ_TRACKID'] = metadata['recording_id']
            if metadata.get('artist_id'):
                audio['MUSICBRAINZ_ARTISTID'] = metadata['artist_id']
            if metadata.get('release_id'):
                audio['MUSICBRAINZ_ALBUMID'] = metadata['release_id']

            audio.save()

        except Exception as e:
            logger.error(f"Error tagging FLAC: {e}")

    def _sanitize(self, filename: str) -> str:
        """Sanitize filename components (Helper for internal usage if needed)"""
        import re
        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename).strip()

def get_metadata_enhancer():
    return MetadataEnhancerService.get_instance()

def register_metadata_enhancer_service():
    """Kept for compatibility, though it no longer registers background jobs."""
    get_metadata_enhancer()
    logger.info("Metadata Enhancer Service initialized")
