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
from typing import Optional, Dict, Any, Tuple, List
import datetime

from core.enums import Capability
from core.settings import config_manager
from core.tiered_logger import get_logger
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_EXACT_SYNC
from core.matching_engine.soul_sync_track import SoulSyncTrack
from database.working_database import get_working_database, ReviewTask

# Optional Mutagen imports
try:
    import mutagen
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3, TXXX, APIC, TIT2, TPE1, TALB, TDRC, TRCK, TPOS
    from mutagen.flac import FLAC, Picture
    from mutagen.oggvorbis import OggVorbis
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.wave import WAVE
    try:
        from mutagen._riff import RiffFile
    except Exception:
        RiffFile = None
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    RiffFile = None

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
        
        On failure: Returns (None, 0.0) - file will be marked for manual review.
        """
        fingerprint_provider = self._get_provider(Capability.RESOLVE_FINGERPRINT)
        metadata_provider = self._get_provider(Capability.FETCH_METADATA)

        metadata = None
        confidence = 0.0

        try:
            # Step A: Fingerprint via AcoustID
            try:
                fingerprint = FingerprintGenerator.generate(str(file_path))
                duration = self._get_audio_duration(file_path)

                if fingerprint and duration and fingerprint_provider:
                    # Clean debug output showing what's being sent to AcoustID
                    logger.debug(
                        f"→ AcoustID Lookup: {file_path.name}\n"
                        f"  Duration: {duration}s | Fingerprint: {len(fingerprint)} chars"
                    )
                    
                    try:
                        mbids = fingerprint_provider.resolve_fingerprint(fingerprint, int(duration))
                        
                        if mbids and metadata_provider:
                            mbid = mbids[0]
                            logger.info(f"✓ AcoustID identified: {file_path.name} → MBID: {mbid}")
                            try:
                                metadata = metadata_provider.get_metadata(mbid)
                                if metadata:
                                    confidence = 0.95
                                    logger.info(f"  ✓ Metadata fetched: {metadata.get('title')} by {metadata.get('artist')}")
                                    return metadata, confidence
                            except Exception as e:
                                logger.warning(f"Failed to fetch metadata for MBID {mbid}: {e}")
                                # Continue to fallback search
                        else:
                            logger.debug(f"✗ No MBID found from AcoustID for {file_path.name}")
                    except Exception as e:
                        logger.warning(f"AcoustID fingerprint resolution failed: {e}")
                        # Continue to fallback search
            except Exception as e:
                logger.warning(f"Fingerprint generation or provider error: {e}")
                # Continue to fallback search

            # Fallback: Search by filename with matching engine
            if metadata_provider:
                logger.debug(f"Attempting fallback filename search for {file_path.name}")
                try:
                    # Extract metadata from filename
                    query = file_path.stem.replace('_', ' ').replace('-', ' ')
                    
                    # Get duration for matching
                    duration = self._get_audio_duration(file_path)
                    
                    # Search MusicBrainz
                    results = metadata_provider.search_metadata(query, limit=10)
                    
                    if results:
                        # Convert file to SoulSyncTrack for matching
                        file_track = self._filename_to_track(file_path, duration)
                        
                        # Convert search results to SoulSyncTracks
                        candidate_tracks = []
                        for result in results:
                            candidate = self._search_result_to_track(result)
                            if candidate:
                                candidate_tracks.append((candidate, result.get('mbid')))
                        
                        if candidate_tracks:
                            # Use matching engine with EXACT_SYNC profile
                            matcher = WeightedMatchingEngine(PROFILE_EXACT_SYNC)
                            best_score = 0.0
                            best_mbid = None
                            
                            logger.debug(f"Comparing {len(candidate_tracks)} candidates for: {file_path.name}")
                            
                            for idx, (candidate, mbid) in enumerate(candidate_tracks, 1):
                                match_result = matcher.calculate_match(file_track, candidate)
                                score = match_result.confidence_score
                                
                                # Clean comparison log in debug mode
                                logger.debug(
                                    f"  [{idx}/{len(candidate_tracks)}] Score: {score:5.1f}% | "
                                    f"{candidate.title} - {candidate.artist_name} | "
                                    f"Duration: {candidate.duration}ms vs {file_track.duration}ms"
                                )
                                
                                if score > best_score:
                                    best_score = score
                                    best_mbid = mbid
                            
                            # Check if best match passes threshold (85%)
                            if best_score >= 85.0 and best_mbid:
                                logger.info(f"✓ Matched '{file_path.name}' (score: {best_score:.1f}%)")
                                try:
                                    metadata = metadata_provider.get_metadata(best_mbid)
                                    if metadata:
                                        confidence = best_score / 100.0
                                        logger.info(f"  → Result: {metadata.get('title')} by {metadata.get('artist')}")
                                        return metadata, confidence
                                except Exception as e:
                                    logger.warning(f"Failed to fetch metadata for matched MBID {best_mbid}: {e}")
                            else:
                                logger.debug(f"✗ Best match score {best_score:.1f}% below threshold (85%) for '{file_path.name}'")
                    else:
                        logger.debug(f"No search results for filename query: '{query}'")
                except Exception as e:
                    logger.warning(f"Fallback filename search failed: {e}", exc_info=True)

            # If we get here, all identification methods failed
            if metadata is None:
                logger.warning(f"All metadata identification methods failed for {file_path.name}. File will be queued for manual review.")
                return None, 0.0

        except Exception as e:
            logger.error(f"Unexpected error identifying {file_path}: {e}", exc_info=True)
            return None, 0.0

        return metadata, confidence

    def tag_file(self, file_path: Path, metadata: Dict[str, Any]):
        """
        Write tags to file (abstracted).
        """
        _TaggingHelper.write_tags(file_path, metadata)

    def read_tags(self, file_path: Path) -> Dict[str, Any]:
        """Read and normalize metadata tags from a local audio file."""
        return _TaggingHelper.read_tags(file_path)

    def create_or_update_review_task(self, file_path: Path, metadata: Optional[Dict[str, Any]], confidence: float, status='pending'):
        """Create or update a task in the review queue."""
        try:
            db = get_working_database()
            with db.session_scope() as session:
                existing = session.query(ReviewTask).filter(ReviewTask.file_path == str(file_path)).first()
                if existing:
                    existing.detected_metadata = metadata
                    existing.confidence_score = confidence
                    existing.status = status
                    existing.created_at = datetime.datetime.now(datetime.UTC)
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

    def _filename_to_track(self, file_path: Path, duration: Optional[int]) -> SoulSyncTrack:
        """Convert filename to SoulSyncTrack for matching using provider_base helper."""
        from core.track_parser import TrackParser
        from core.provider_base import ProviderBase
        
        # Use TrackParser to extract artist/title from filename
        parser = TrackParser()
        parsed = parser.parse_filename(file_path.stem)
        
        # Use the standard factory method from ProviderBase
        return ProviderBase.create_soul_sync_track(
            title=parsed.title or file_path.stem,
            artist=parsed.artist_name or 'Unknown Artist',
            album=parsed.album_title or '',
            duration_ms=duration * 1000 if duration else None,
            provider_id=str(file_path),
            source='local_file'
        )
    
    def _search_result_to_track(self, result: Dict[str, Any]) -> Optional[SoulSyncTrack]:
        """Convert MusicBrainz search result to SoulSyncTrack using provider_base helper."""
        from core.provider_base import ProviderBase
        
        try:
            return ProviderBase.create_soul_sync_track(
                title=result.get('title', ''),
                artist=result.get('artist', ''),
                album=result.get('album', ''),
                duration_ms=result.get('duration'),  # MusicBrainz returns ms
                isrc=result.get('isrc'),
                musicbrainz_id=result.get('mbid', ''),
                provider_id=result.get('mbid', ''),
                source='musicbrainz'
            )
        except Exception as e:
            logger.warning(f"Failed to convert search result to track: {e}")
            return None


class _TaggingHelper:
    """
    Internal helper class to abstract raw mutagen logic.
    Supports Tier 1 Auto-Write.
    """
    @staticmethod
    def write_tags(file_path: Path, metadata: Dict[str, Any]):
        if not MUTAGEN_AVAILABLE:
            logger.warning("Mutagen not available, skipping tagging")
            return

        try:
            ext = file_path.suffix.lower()
            if ext == '.mp3':
                _TaggingHelper._tag_mp3(file_path, metadata)
            elif ext == '.flac':
                _TaggingHelper._tag_flac(file_path, metadata)

            logger.info(f"Tagged {file_path.name}")
        except Exception as e:
            logger.error(f"Failed to tag {file_path}: {e}")

    @staticmethod
    def read_tags(file_path: Path) -> Dict[str, Any]:
        if not MUTAGEN_AVAILABLE:
            return {}

        metadata: Dict[str, Any] = {
            'file_format': file_path.suffix.lower().lstrip('.'),
        }

        try:
            easy_audio = mutagen.File(str(file_path), easy=True)
            metadata = _TaggingHelper._merge_metadata(metadata, _TaggingHelper._extract_easy_tags(easy_audio))
            metadata = _TaggingHelper._merge_metadata(metadata, _TaggingHelper._extract_audio_info(easy_audio))
        except Exception as e:
            logger.debug(f"Failed easy tag read for {file_path}: {e}")

        try:
            detailed_audio = mutagen.File(str(file_path))
            metadata = _TaggingHelper._merge_metadata(metadata, _TaggingHelper._extract_detailed_tags(detailed_audio))
            metadata = _TaggingHelper._merge_metadata(metadata, _TaggingHelper._extract_audio_info(detailed_audio))
        except Exception as e:
            logger.debug(f"Failed detailed tag read for {file_path}: {e}")

        if file_path.suffix.lower() == '.wav':
            metadata = _TaggingHelper._merge_metadata(metadata, _TaggingHelper._read_wav_tags(file_path))

        if not metadata.get('year') and metadata.get('date'):
            date_value = str(metadata['date']).strip()
            if len(date_value) >= 4 and date_value[:4].isdigit():
                metadata['year'] = date_value[:4]

        return {key: value for key, value in metadata.items() if value not in (None, '', [], {})}

    @staticmethod
    def _merge_metadata(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(base)
        for key, value in (update or {}).items():
            if value not in (None, '', [], {}):
                merged[str(key)] = value
        return merged

    @staticmethod
    def _extract_audio_info(audio: Any) -> Dict[str, Any]:
        info = getattr(audio, 'info', None)
        if not info:
            return {}

        metadata: Dict[str, Any] = {}
        length = getattr(info, 'length', None)
        bitrate = getattr(info, 'bitrate', None)
        sample_rate = getattr(info, 'sample_rate', None)
        channels = getattr(info, 'channels', None)

        if length is not None:
            metadata['duration_seconds'] = int(length)
        if bitrate is not None:
            metadata['bitrate_kbps'] = int(bitrate / 1000)
        if sample_rate is not None:
            metadata['sample_rate_hz'] = int(sample_rate)
        if channels is not None:
            metadata['channels'] = int(channels)
        return metadata

    @staticmethod
    def _extract_easy_tags(audio: Any) -> Dict[str, Any]:
        tags = getattr(audio, 'tags', None) or {}
        return _TaggingHelper._map_simple_tags(tags)

    @staticmethod
    def _extract_detailed_tags(audio: Any) -> Dict[str, Any]:
        tags = getattr(audio, 'tags', None)
        if not tags:
            return {}

        if hasattr(tags, 'getall'):
            metadata = {
                'title': _TaggingHelper._id3_text(tags, 'TIT2'),
                'artist': _TaggingHelper._id3_text(tags, 'TPE1'),
                'album': _TaggingHelper._id3_text(tags, 'TALB'),
                'date': _TaggingHelper._id3_text(tags, 'TDRC'),
                'track_number': _TaggingHelper._id3_text(tags, 'TRCK'),
                'disc_number': _TaggingHelper._id3_text(tags, 'TPOS'),
                'isrc': _TaggingHelper._id3_text(tags, 'TSRC'),
                'comments': _TaggingHelper._id3_text(tags, 'COMM'),
            }

            for frame in tags.getall('TXXX'):
                desc = str(getattr(frame, 'desc', '') or '').strip().lower()
                text = _TaggingHelper._frame_text(frame)
                if desc == 'musicbrainz track id':
                    metadata['recording_id'] = text
                    metadata['musicbrainz_id'] = text
                elif desc == 'musicbrainz artist id':
                    metadata['artist_id'] = text
                elif desc == 'musicbrainz release id':
                    metadata['release_id'] = text
                elif desc == 'acoustid id':
                    metadata['acoustid_id'] = text

            if not metadata.get('musicbrainz_id') and metadata.get('recording_id'):
                metadata['musicbrainz_id'] = metadata['recording_id']

            return {key: value for key, value in metadata.items() if value not in (None, '', [], {})}

        return _TaggingHelper._map_simple_tags(tags)

    @staticmethod
    def _map_simple_tags(tags: Any) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        if not hasattr(tags, 'items'):
            return normalized

        lowered = {str(key).lower(): value for key, value in tags.items()}
        normalized['title'] = _TaggingHelper._first_value(lowered, 'title', 'inam')
        normalized['artist'] = _TaggingHelper._first_value(lowered, 'artist', 'iart')
        normalized['album'] = _TaggingHelper._first_value(lowered, 'album', 'iprd')
        normalized['date'] = _TaggingHelper._first_value(lowered, 'date', 'year', 'icrd')
        normalized['track_number'] = _TaggingHelper._first_value(lowered, 'tracknumber', 'track_number', 'trck', 'itrk')
        normalized['disc_number'] = _TaggingHelper._first_value(lowered, 'discnumber', 'disc_number', 'tpos')
        normalized['isrc'] = _TaggingHelper._first_value(lowered, 'isrc', 'tsrc')
        normalized['comments'] = _TaggingHelper._first_value(lowered, 'comment', 'comments', 'comm', 'icmt')
        normalized['recording_id'] = _TaggingHelper._first_value(
            lowered,
            'musicbrainz_trackid',
            'musicbrainz track id',
            'recording_id',
            'musicbrainz_id',
        )
        normalized['musicbrainz_id'] = normalized['recording_id']
        normalized['artist_id'] = _TaggingHelper._first_value(lowered, 'musicbrainz_artistid', 'musicbrainz artist id', 'artist_id')
        normalized['release_id'] = _TaggingHelper._first_value(lowered, 'musicbrainz_albumid', 'musicbrainz release id', 'release_id')
        normalized['acoustid_id'] = _TaggingHelper._first_value(lowered, 'acoustid id', 'acoustid_id')

        return {key: value for key, value in normalized.items() if value not in (None, '', [], {})}

    @staticmethod
    def _first_value(mapping: Dict[str, Any], *keys: str) -> Optional[str]:
        for key in keys:
            if key not in mapping:
                continue
            value = _TaggingHelper._coerce_value(mapping[key])
            if value not in (None, ''):
                return value
        return None

    @staticmethod
    def _coerce_value(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            for item in value:
                coerced = _TaggingHelper._coerce_value(item)
                if coerced not in (None, ''):
                    return coerced
            return None
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace').replace('\x00', '').strip() or None
        text = getattr(value, 'text', None)
        if text is not None:
            return _TaggingHelper._coerce_value(text)
        return str(value).replace('\x00', '').strip() or None

    @staticmethod
    def _frame_text(frame: Any) -> Optional[str]:
        return _TaggingHelper._coerce_value(frame)

    @staticmethod
    def _id3_text(tags: Any, frame_id: str) -> Optional[str]:
        frames = tags.getall(frame_id)
        if not frames:
            return None
        return _TaggingHelper._frame_text(frames[0])

    @staticmethod
    def _read_wav_tags(file_path: Path) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}

        try:
            audio = WAVE(str(file_path))
            metadata = _TaggingHelper._merge_metadata(metadata, _TaggingHelper._extract_audio_info(audio))
            metadata = _TaggingHelper._merge_metadata(metadata, _TaggingHelper._extract_detailed_tags(audio))
            metadata = _TaggingHelper._merge_metadata(metadata, _TaggingHelper._map_simple_tags(getattr(audio, 'tags', None) or {}))
        except Exception as e:
            logger.debug(f"Failed WAVE parser tag read for {file_path}: {e}")

        if RiffFile is None:
            return metadata

        try:
            with file_path.open('rb') as handle:
                riff = RiffFile(handle)
                info_chunk = None
                for chunk in riff.root.subchunks():
                    if getattr(chunk, 'id', None) == 'LIST' and getattr(chunk, 'name', None) == 'INFO':
                        info_chunk = chunk
                        break

                if info_chunk is None:
                    return metadata

                riff_tags: Dict[str, Any] = {}
                for chunk in info_chunk.subchunks():
                    chunk_id = str(getattr(chunk, 'id', '') or '').lower()
                    if not chunk_id:
                        continue
                    riff_tags[chunk_id] = chunk.read()

                metadata = _TaggingHelper._merge_metadata(metadata, _TaggingHelper._map_simple_tags(riff_tags))
        except Exception as e:
            logger.debug(f"Failed RIFF INFO tag read for {file_path}: {e}")

        return metadata

    @staticmethod
    def _tag_mp3(file_path: Path, metadata: Dict[str, Any]):
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

    @staticmethod
    def _tag_flac(file_path: Path, metadata: Dict[str, Any]):
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
