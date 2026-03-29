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
from core.hook_manager import hook_manager
from core.tiered_logger import get_logger
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.provider import ServiceRegistry
from core.matching_engine.scoring_profile import PROFILE_EXACT_SYNC
from core.matching_engine.soul_sync_track import SoulSyncTrack
from database.working_database import get_working_database, ReviewTask

logger = get_logger("services.metadata_enhancer")


def _title_similarity(a: str, b: str) -> float:
    """Jaccard word-set similarity for comparing track titles (case-insensitive)."""
    if a == b:
        return 1.0
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _track_entry_to_metadata(track: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an album_cache track entry to the standard identify_file return format."""
    return {
        "title": track.get("title"),
        "recording_id": track.get("recording_id"),
        "artist": track.get("artist"),
        "artist_id": "",
        "album": track.get("album"),
        "release_id": track.get("release_id"),
        "date": track.get("date"),
        "track_number": track.get("track_number"),
        "disc_number": track.get("disc_number"),
        "cover_art_url": track.get("cover_art_url"),
        "isrc": track.get("isrc"),
    }


def _match_from_album_cache(
    file_path: Path,
    album_cache: Dict[str, Any],
) -> "Optional[Tuple[Optional[Dict[str, Any]], float]]":
    """Try to match *file_path* against any release stored in *album_cache*.

    Matching priority:
    1. ID3 ``track_number`` (+ disc_number) exact match → confidence 0.90
    2. Title Jaccard word-set similarity ≥ 0.85     → confidence 0.88

    Returns a ``(metadata, confidence)`` tuple on a hit, or ``None``.
    """
    try:
        tags = _tagging_read(file_path)
    except Exception:
        return None

    tag_title = str(tags.get("title") or "").strip().lower()
    raw_track_num = tags.get("track_number") or tags.get("tracknumber")
    raw_disc_num = tags.get("disc_number") or tags.get("discnumber") or "1"
    try:
        tag_track_num: Optional[int] = int(str(raw_track_num).split("/")[0].strip())
    except (TypeError, ValueError):
        tag_track_num = None
    try:
        tag_disc_num = int(str(raw_disc_num).split("/")[0].strip())
    except (TypeError, ValueError):
        tag_disc_num = 1

    for _release_id, release_data in album_cache.items():
        tracks = release_data.get("tracks") or []

        # Priority 1: exact track number + disc number
        if tag_track_num is not None:
            for t in tracks:
                if (
                    t.get("track_number") == tag_track_num
                    and (t.get("disc_number") or 1) == tag_disc_num
                ):
                    logger.info(
                        "Album cache HIT (disc %d, track %d): %s → %s",
                        tag_disc_num, tag_track_num, file_path.name, t.get("title"),
                    )
                    return _track_entry_to_metadata(t), 0.90

        # Priority 2: title word-set similarity
        if tag_title:
            for t in tracks:
                cache_title = str(t.get("title") or "").strip().lower()
                if cache_title and _title_similarity(tag_title, cache_title) >= 0.85:
                    logger.info(
                        "Album cache HIT (title match): %s → %s",
                        file_path.name, t.get("title"),
                    )
                    return _track_entry_to_metadata(t), 0.88

    return None


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
        required_keys = hook_manager.apply_filters('register_metadata_requirements', [])
        from database.music_database import get_database, Track
        from core.file_handling.path_mapper import PathMapper
        from core.matching_engine.scoring_profile import ExactSyncProfile
        from core.matching_engine.fingerprinting import FingerprintGenerator
        from core.matching_engine.soul_sync_track import SoulSyncTrack
        from core.matching_engine.matching_engine import WeightedMatchingEngine
        from core.provider import ServiceRegistry
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

                # Load any existing fingerprint record for this track (avoids re-fingerprinting).
                from database.music_database import AudioFingerprint
                track_fp = session.query(AudioFingerprint).filter_by(track_id=track.id).first()

                # Step 3 (DB AcoustID Fast-Path): fingerprint already stored — skip re-generation.
                if track_fp and track_fp.acoustid_id and fingerprint_provider and duration:
                    logger.debug(f"Step 3 (DB AcoustID Fast-Path): Resolving existing AcoustID for {local_path.name}")
                    try:
                        mbids = fingerprint_provider.resolve_fingerprint(track_fp.acoustid_id, int(duration / 1000) if duration > 10000 else duration)
                        if mbids:
                            new_musicbrainz_id = mbids[0]
                    except Exception as e:
                        logger.warning(f"AcoustID fast-path resolution failed: {e}")

                # Step 4 (Generate AcoustID): no fingerprint on record yet — compute one now.
                if not new_musicbrainz_id and not (track_fp and track_fp.acoustid_id) and fingerprint_provider and duration:
                    logger.debug(f"Step 4 (Generate AcoustID): Fingerprinting {local_path.name}")
                    try:
                        fingerprint = FingerprintGenerator.generate(str(local_path))
                        if fingerprint:
                            found_new_data = True

                            # Step 4a (Fingerprint Cache): before hitting the AcoustID network,
                            # check audio_fingerprints for another track with this same chromaprint.
                            # If a resolved entry exists, reuse its MBID without any network call.
                            cached_fp = session.query(AudioFingerprint).filter_by(
                                fingerprint_hash=fingerprint
                            ).first()

                            if cached_fp and cached_fp.acoustid_id:
                                # Another track shares this fingerprint — look for a resolved MBID.
                                linked_fp = (
                                    session.query(AudioFingerprint)
                                    .join(Track, AudioFingerprint.track_id == Track.id)
                                    .filter(
                                        AudioFingerprint.acoustid_id == cached_fp.acoustid_id,
                                        AudioFingerprint.track_id != track.id,
                                        Track.musicbrainz_id.isnot(None),
                                        Track.musicbrainz_id != "NOT_FOUND",
                                    )
                                    .first()
                                )
                                if linked_fp:
                                    linked = session.get(Track, linked_fp.track_id)
                                    new_musicbrainz_id = linked.musicbrainz_id
                                    track_fp = cached_fp  # reference for tag writing
                                    logger.info(
                                        "Step 4a (Cache Hit): MBID %s from fingerprint cache for %s",
                                        new_musicbrainz_id, local_path.name,
                                    )
                                else:
                                    # Have cached acoustid_id but no resolved MBID — still need network
                                    duration_secs = int(duration / 1000) if duration > 10000 else duration
                                    mbids = fingerprint_provider.resolve_fingerprint(
                                        cached_fp.acoustid_id, duration_secs
                                    )
                                    if mbids:
                                        new_musicbrainz_id = mbids[0]
                                    track_fp = cached_fp
                            else:
                                # No cached entry — hit network and persist fingerprint for future fast-path.
                                duration_secs = int(duration / 1000) if duration > 10000 else duration
                                mbids = fingerprint_provider.resolve_fingerprint(fingerprint, duration_secs)
                                if mbids:
                                    new_musicbrainz_id = mbids[0]
                                track_fp = AudioFingerprint(
                                    track_id=track.id,
                                    fingerprint_hash=fingerprint,
                                    acoustid_id=fingerprint,
                                )
                                session.add(track_fp)
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
                            engine_cls = ServiceRegistry.resolve('matching_engine') or WeightedMatchingEngine
                            matcher = engine_cls(ExactSyncProfile())
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
                    elif not track.isrc and metadata_provider:
                        # Optionally fetch detailed metadata to grab ISRC if missing
                        try:
                            meta = metadata_provider.get_metadata(new_musicbrainz_id)
                            if meta and meta.get('isrc'):
                                track.isrc = meta.get('isrc')
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
                    if track_fp and track_fp.acoustid_id:
                        update_tags['acoustid_id'] = track_fp.acoustid_id

                    if update_tags:
                        _tagging_write(local_path, update_tags)

                # Apply post-enrichment hooks before SQLAlchemy auto-commits at the end of the session context
                track = hook_manager.apply_filters('post_metadata_enrichment', track)

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
            # Step 0: Read file tags first — cheapest check, no CPU fingerprinting, no network.
            try:
                tags = _tagging_read(file_path)
                tag_mbid = tags.get('musicbrainz_id') or tags.get('recording_id')
                if tag_mbid and metadata_provider:
                    logger.info(f"Step 0 (File Tags): Found MBID {tag_mbid} in tags for {file_path.name}")
                    try:
                        metadata = metadata_provider.get_metadata(tag_mbid)
                        if metadata:
                            return metadata, 0.99
                    except Exception as e:
                        logger.warning(f"Failed to fetch metadata for tag MBID {tag_mbid}: {e}")
                        # fall through to fingerprint
            except Exception as e:
                logger.warning(f"Failed to read tags for {file_path.name}: {e}")

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
                    raw_query = file_path.stem.replace('_', ' ').replace('-', ' ')
                    query = hook_manager.apply_filters('pre_normalize_text', raw_query)
                    
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
                            engine_cls = ServiceRegistry.resolve('matching_engine') or WeightedMatchingEngine
                            matcher = engine_cls(PROFILE_EXACT_SYNC)
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

    def identify_batch(
        self, files: List[Path]
    ) -> List[Tuple[Optional[Dict[str, Any]], float]]:
        """Identify a batch of files sharing a parent directory (typically one album).

        Uses an in-process ``album_cache`` to avoid N+1 AcoustID / MusicBrainz
        round-trips.  After the first successful identification yields a
        ``release_id``, the full MusicBrainz release is fetched *once* via
        ``MusicBrainzClient.get_release`` (itself cached for 30 days) and
        indexed by track number and title.  Subsequent files in the same batch
        look up their metadata in O(1) — no network call needed.

        Returns:
            List of ``(metadata, confidence)`` tuples in the same order as
            *files*.
        """
        results: List[Tuple[Optional[Dict[str, Any]], float]] = []
        # release_id -> {"album": str, "cover_art_url": str|None, "tracks": [...]}
        album_cache: Dict[str, Any] = {}
        metadata_provider = self._get_provider(Capability.FETCH_METADATA)

        for file_path in files:
            # ── Try album cache first ─────────────────────────────────────────
            if album_cache:
                cached = _match_from_album_cache(file_path, album_cache)
                if cached is not None:
                    results.append(cached)
                    continue

            # ── Full identification pipeline ──────────────────────────────────
            metadata, confidence = self.identify_file(file_path)
            results.append((metadata, confidence))

            # ── Populate album cache on first successful release_id ───────────
            if metadata and metadata.get("release_id") and metadata_provider:
                release_id = metadata["release_id"]
                if release_id not in album_cache:
                    get_release = getattr(metadata_provider, "get_release", None)
                    if get_release is not None:
                        release_data = get_release(release_id)
                        if release_data and release_data.get("tracks"):
                            album_cache[release_id] = release_data
                            logger.info(
                                "Album memory cache populated: release=%s, tracks=%d",
                                release_id,
                                len(release_data["tracks"]),
                            )

        return results

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
        
        # Use the standard factory method from ProviderBase
        return ProviderBase.create_soul_sync_track(
            title=(parsed.title if parsed else None) or file_path.stem,
            artist=(parsed.artist_name if parsed else None) or 'Unknown Artist',
            album=(parsed.album_title if parsed else None) or '',
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
