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
from core.file_handling.local_io import LocalFileHandler
from core.file_handling.tagging_io import read_tags as _tagging_read, write_tags as _tagging_write
from core.settings import config_manager
from core.tiered_logger import get_logger
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_EXACT_SYNC
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.plugins.hook_manager import hook_manager
from database.working_database import get_working_database, ReviewTask

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

    def enhance_library_metadata(self, batch_size=100):
        """
        Retroactive metadata enhancer following a Local-First, highly efficient 5-Step Pipeline.
        """
        from database.music_database import get_database, Track
        from core.file_handling.path_mapper import PathMapper
        from core.matching_engine.scoring_profile import ExactSyncProfile
        from core.matching_engine.fingerprinting import FingerprintGenerator
        from core.matching_engine.soul_sync_track import SoulSyncTrack
        from core.matching_engine.matching_engine import WeightedMatchingEngine
        from pathlib import Path

        db = get_database()

        fingerprint_provider = self._get_provider(Capability.RESOLVE_FINGERPRINT)
        metadata_provider = self._get_provider(Capability.FETCH_METADATA)

        with db.session_scope() as session:
            # Step 1 (Path Mapping): Query DB for tracks where musicbrainz_id IS NULL
            tracks_to_process = session.query(Track).filter(Track.musicbrainz_id.is_(None)).limit(batch_size).all()

            if not tracks_to_process:
                logger.info("No tracks missing MusicBrainz ID. Enhancement complete.")
                return

            logger.info(f"Processing batch of {len(tracks_to_process)} tracks for metadata enhancement.")

            for track in tracks_to_process:
                local_path_str = PathMapper.to_local(track.file_path)
                local_path = Path(local_path_str)

                if not local_path.exists():
                    logger.warning(f"File not found for track {track.id}: {local_path}")
                    track.musicbrainz_id = "NOT_FOUND"
                    continue

                found_new_data = False
                new_musicbrainz_id = None
                new_isrc = None

                # Step 2 (Local File Parsing): Read physical file tags first
                tags = _tagging_read(local_path)
                if tags:
                    tag_mbid = tags.get('musicbrainz_id') or tags.get('recording_id')
                    tag_isrc = tags.get('isrc')

                    if tag_mbid and tag_isrc:
                        logger.info(f"Step 2 (Local Tags): Found MBID {tag_mbid} and ISRC {tag_isrc} for {local_path.name}")
                        track.musicbrainz_id = tag_mbid
                        if not track.isrc:
                            track.isrc = tag_isrc
                        continue  # Move to next track, DB updated

                # Prepare for identification
                duration = track.duration or _tagging_read(local_path).get("duration")

                # Step 3 (DB AcoustID Fast-Path):
                if track.acoustid_id and fingerprint_provider and duration:
                    logger.debug(f"Step 3 (DB AcoustID Fast-Path): Resolving existing AcoustID for {local_path.name}")
                    try:
                        mbids = fingerprint_provider.resolve_fingerprint(track.acoustid_id, int(duration / 1000) if duration > 10000 else duration)
                        if mbids:
                            new_musicbrainz_id = mbids[0]
                    except Exception as e:
                        logger.warning(f"AcoustID fast-path resolution failed: {e}")

                # Step 4 (Generate AcoustID):
                if not new_musicbrainz_id and not track.acoustid_id and fingerprint_provider and duration:
                    logger.debug(f"Step 4 (Generate AcoustID): Fingerprinting {local_path.name}")
                    try:
                        fingerprint = FingerprintGenerator.generate(str(local_path))
                        if fingerprint:
                            track.acoustid_id = fingerprint
                            found_new_data = True
                            mbids = fingerprint_provider.resolve_fingerprint(fingerprint, int(duration / 1000) if duration > 10000 else duration)
                            if mbids:
                                new_musicbrainz_id = mbids[0]
                    except Exception as e:
                        logger.warning(f"Fingerprint generation/resolution failed: {e}")

                # Step 5 (Text Fallback & Write):
                # Resolve artist name from the ORM relationship — Track has no
                # artist_name column; artist_name lives on the related Artist row.
                artist_name_str = track.artist.name if track.artist else None
                if not new_musicbrainz_id and metadata_provider and artist_name_str and track.title:
                    logger.debug(f"Step 5 (Text Fallback): Searching MusicBrainz for {artist_name_str} - {track.title}")
                    try:
                        query = f"{artist_name_str} {track.title}"
                        # Ensure we use standard search which returns List[SoulSyncTrack]
                        results = metadata_provider.search(query, type="track", limit=5)
                        if results:
                            # Strict match evaluation
                            file_track = SoulSyncTrack(
                                raw_title=track.title,
                                artist_name=artist_name_str,
                                album_title=track.album.title if track.album else "",
                                duration=duration
                            )
                            matcher = WeightedMatchingEngine(ExactSyncProfile())
                            best_score = 0.0

                            for candidate in results:
                                if candidate:
                                    match_result = matcher.calculate_match(file_track, candidate)
                                    if match_result.confidence_score > best_score:
                                        best_score = match_result.confidence_score
                                        if best_score >= 85.0:
                                            new_musicbrainz_id = candidate.musicbrainz_id
                                            new_isrc = candidate.isrc
                    except Exception as e:
                        logger.warning(f"Text fallback search failed: {e}", exc_info=True)

                # Handle found data
                if new_musicbrainz_id:
                    track.musicbrainz_id = new_musicbrainz_id
                    found_new_data = True
                    logger.info(f"Identified MBID {new_musicbrainz_id} for {local_path.name}")

                    if not track.isrc and new_isrc:
                        track.isrc = new_isrc
                    if metadata_provider:
                        # Fetch full metadata record for ISRC fill and plugin hooks
                        try:
                            meta = metadata_provider.get_metadata(new_musicbrainz_id)
                            if meta:
                                if not track.isrc and meta.get('isrc'):
                                    track.isrc = meta.get('isrc')
                                hook_manager.apply_filters(
                                    'post_musicbrainz_fetch', track, mb_data=meta
                                )
                        except Exception:
                            pass
                else:
                    logger.warning(f"Failed to identify track {track.id}: {local_path.name}")
                    track.musicbrainz_id = "NOT_FOUND"

                # Tag physical file if new data was found
                if found_new_data:
                    update_tags = {}
                    if track.musicbrainz_id and track.musicbrainz_id != "NOT_FOUND":
                        update_tags['musicbrainz_id'] = track.musicbrainz_id
                        update_tags['recording_id'] = track.musicbrainz_id
                    if track.isrc:
                        update_tags['isrc'] = track.isrc
                    if track.acoustid_id:
                        update_tags['acoustid_id'] = track.acoustid_id

                    if update_tags:
                        _tagging_write(local_path, update_tags)

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
                # read_tags returns duration in ms
                duration_ms = _tagging_read(file_path).get("duration")
                duration_sec = int(duration_ms / 1000) if duration_ms else None

                if fingerprint and duration_sec and fingerprint_provider:
                    # Clean debug output showing what's being sent to AcoustID
                    logger.debug(
                        f"→ AcoustID Lookup: {file_path.name}\n"
                        f"  Duration: {duration_sec}s | Fingerprint: {len(fingerprint)} chars"
                    )
                    
                    try:
                        mbids = fingerprint_provider.resolve_fingerprint(fingerprint, int(duration_sec))
                        
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
                    duration_ms = _tagging_read(file_path).get("duration")
                    
                    # Search MusicBrainz
                    results = metadata_provider.search_metadata(query, limit=10)
                    
                    if results:
                        # Convert file to SoulSyncTrack for matching
                        file_track = self._filename_to_track(file_path, duration_ms)
                        
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

    def _filename_to_track(self, file_path: Path, duration_ms: Optional[int]) -> SoulSyncTrack:
        """Convert filename to SoulSyncTrack for matching using provider_base helper."""
        from core.track_parser import TrackParser
        from core.provider_base import ProviderBase
        
        # Use TrackParser to extract artist/title from filename
        parser = TrackParser()
        parsed = parser.parse_filename(file_path.stem)

        title = file_path.stem
        artist = None
        album = ''
        if parsed is not None:
            title = parsed.title or file_path.stem
            artist = parsed.artist_name
            album = parsed.album_title or ''
        
        # Use the standard factory method from ProviderBase
        return ProviderBase.create_soul_sync_track(
            title=title,
            artist=artist,
            album=album,
            duration_ms=duration_ms,
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


    def _sanitize(self, filename: str) -> str:
        """Sanitize filename components."""
        import re
        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename).strip()

def get_metadata_enhancer():
    return MetadataEnhancerService.get_instance()

def register_metadata_enhancer_service():
    """Kept for compatibility, though it no longer registers background jobs."""
    get_metadata_enhancer()
    logger.info("Metadata Enhancer Service initialized")
