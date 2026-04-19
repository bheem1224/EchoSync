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

from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import OperationalError
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
from core.matching_engine.echo_sync_track import EchosyncTrack
from database.working_database import get_working_database, ReviewTask

logger = get_logger("services.metadata_enhancer")

# ── DIAGNOSTIC FLAG ────────────────────────────────────────────────────────────
# Set True to bypass ALL network calls (Steps 2.5 / 3 / 4 / 5).
# Only MBIDs already embedded in file tags are saved.  Tracks with no embedded
# MBID have their plugin-required keys stamped and are left with musicbrainz_id
# = NULL so real processing can run later.  Flips back to False for production.
_NETWORK_DISABLED = False
# ───────────────────────────────────────────────────────────────────────────────


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

    def enhance_library_metadata(self, batch_size=50) -> None:
        """Retroactive metadata enhancer following a Local-First, highly efficient 5-Step Pipeline.

        Loops through batches until no more tracks require enhancement.  Each batch is
        committed in its own session so memory stays flat even on large libraries.
        """
        from sqlalchemy import or_, and_, func, Integer
        from sqlalchemy.orm.attributes import flag_modified
        from sqlalchemy.exc import OperationalError
        required_keys = hook_manager.apply_filters('register_metadata_requirements', [])
        from database.music_database import get_database, Track, Artist, AudioFingerprint
        from core.file_handling.path_mapper import PathMapper
        from core.matching_engine.scoring_profile import ExactSyncProfile
        from core.matching_engine.fingerprinting import FingerprintGenerator
        from core.matching_engine.echo_sync_track import EchosyncTrack
        from core.matching_engine.matching_engine import WeightedMatchingEngine
        from core.provider import ServiceRegistry
        from pathlib import Path

        MAX_REATTEMPTS = 5

        db = get_database()

        fingerprint_provider = self._get_provider(Capability.RESOLVE_FINGERPRINT)
        metadata_provider = self._get_provider(Capability.FETCH_METADATA)

        total_processed = 0
        MAX_ITERATIONS = 500  # safety cap — prevents infinite loops on persistent failures

        for _iteration in range(MAX_ITERATIONS):
            # Step 1: Select tracks that still need work in a short session
            track_data_list = []

            with db.session_scope() as session:
                needs_identification = or_(
                    Track.musicbrainz_id.is_(None),
                    and_(
                        Track.musicbrainz_id == "NOT_FOUND",
                        func.coalesce(
                            func.json_extract(Track.metadata_status, '$.enhancement_attempts'),
                            0,
                        ).cast(Integer) < MAX_REATTEMPTS,
                    ),
                )
                conditions = [needs_identification]
                for key in required_keys:
                    conditions.append(
                        and_(
                            Track.musicbrainz_id.isnot(None),
                            Track.musicbrainz_id != "NOT_FOUND",
                            func.json_extract(Track.metadata_status, f'$.{key}').is_(None),
                        )
                    )
                _va_artist_ids_subq = (
                    session.query(Artist.id)
                    .filter(Artist.name.ilike('various artist%'))
                )
                conditions.append(
                    and_(
                        Track.artist_id.in_(_va_artist_ids_subq),
                        func.json_extract(
                            Track.metadata_status, '$.artist_fixed_from_tags'
                        ).is_(None),
                    )
                )
                try:
                    tracks_to_process = (
                        session.query(Track).filter(or_(*conditions)).limit(batch_size).all()
                    )
                except OperationalError as _oe:
                    if "database is locked" in str(_oe).lower():
                        logger.critical(
                            "EMERGENCY ABORT: Database is locked by an external process. "
                            "Halting job to prevent corruption."
                        )
                    raise

                if not tracks_to_process:
                    if total_processed > 0:
                        logger.info("Enhancement complete. Total tracks processed: %d", total_processed)
                    else:
                        logger.info("No tracks require metadata enhancement.")
                    return

                logger.info(
                    "Enhancement pass %d: processing %d tracks (total so far: %d).",
                    _iteration + 1, len(tracks_to_process), total_processed,
                )

                # Extract necessary data into memory to perform network calls outside session
                for track in tracks_to_process:
                    track_fp = session.query(AudioFingerprint).filter_by(track_id=track.id).first()
                    track_data_list.append({
                        'id': track.id,
                        'file_path': track.file_path,
                        'musicbrainz_id': track.musicbrainz_id,
                        'isrc': track.isrc,
                        'title': track.title,
                        'duration': track.duration,
                        'album_title': track.album.title if track.album else "",
                        'artist_name': track.artist.name if track.artist else None,
                        'metadata_status': dict(track.metadata_status or {}),
                        'chromaprint': track_fp.chromaprint if track_fp else None,
                        'acoustid_id': track_fp.acoustid_id if track_fp else None,
                        'has_fp_record': track_fp is not None
                    })

            # Process tracks outside DB session
            results_to_commit = []

            for t_data in track_data_list:
                local_path_str = PathMapper.to_local(t_data['file_path'])
                local_path = Path(local_path_str)

                if not local_path.exists():
                    logger.warning("Enhancer skipping missing file: %s", local_path)
                    # We should probably update the status in DB, but old logic skipped it inside session.
                    # We will append an update dict to mark it missing or just ignore. Old logic just continued.
                    continue

                new_musicbrainz_id = t_data['musicbrainz_id'] if t_data['musicbrainz_id'] != "NOT_FOUND" else None
                found_new_data = False

                tag_mbid = None
                tag_isrc = None

                # Step 2: Read physical file tags locally
                try:
                    file_tags = _tagging_read(local_path)
                    tag_mbid = file_tags.get("musicbrainz_id") or file_tags.get("recording_id")
                    tag_isrc = file_tags.get("isrc")

                    if not t_data['metadata_status'].get('artist_fixed_from_tags'):
                        tag_artist = file_tags.get("artist")
                        if tag_artist and t_data['artist_name'] and t_data['artist_name'].lower().startswith("various artist"):
                            logger.info("Fixing VA per-track artist from tags: %s", local_path.name)
                            # We mark it to be updated
                            t_data['artist_name'] = tag_artist
                            t_data['metadata_status']['artist_fixed_from_tags'] = True
                            found_new_data = True

                except Exception as e:
                    logger.warning("Failed to read tags from %s: %s", local_path.name, e)

                if tag_mbid:
                    logger.info("Step 2 (Local Tags): Found MBID %s for %s", tag_mbid, local_path.name)
                    new_musicbrainz_id = tag_mbid
                    if tag_isrc and not t_data['isrc']:
                        t_data['isrc'] = tag_isrc

                if tag_isrc and not t_data['isrc']:
                    logger.info("Step 2 (Local Tags): Found ISRC %s for %s, will attempt ISRC lookup", tag_isrc, local_path.name)
                    t_data['isrc'] = tag_isrc

                # DIAGNOSTIC SHORT-CIRCUIT
                if _NETWORK_DISABLED:
                    if new_musicbrainz_id:
                        t_data['musicbrainz_id'] = new_musicbrainz_id
                        found_new_data = True
                        logger.info("DIAGNOSTIC: tag-only MBID %s saved for %s", new_musicbrainz_id, local_path.name)
                    else:
                        logger.debug("DIAGNOSTIC: no MBID in file tags for %s — left unidentified.", local_path.name)

                    t_data['metadata_status']['enhanced'] = True
                    for _diag_key in required_keys:
                        if _diag_key not in t_data['metadata_status']:
                            t_data['metadata_status'][_diag_key] = True

                    if found_new_data:
                        _tagging_write(local_path, {
                            'musicbrainz_id': t_data['musicbrainz_id'],
                            'recording_id':   t_data['musicbrainz_id'],
                        })

                    results_to_commit.append(t_data)
                    total_processed += 1
                    continue

                # Step 2.5 (ISRC Fast-Path)
                if not new_musicbrainz_id and t_data['isrc'] and metadata_provider and getattr(metadata_provider, 'supports_isrc_lookup', False):
                    logger.debug("Step 2.5 (ISRC Lookup): Resolving MBID for ISRC %s → %s", t_data['isrc'], local_path.name)
                    try:
                        isrc_result = metadata_provider.search_by_isrc(t_data['isrc'])
                        if isrc_result and isrc_result.musicbrainz_id:
                            new_musicbrainz_id = isrc_result.musicbrainz_id
                            logger.info("Step 2.5 (ISRC Lookup): MBID %s from ISRC %s", new_musicbrainz_id, t_data['isrc'])
                    except Exception as e:
                        logger.warning("ISRC lookup failed for %s: %s", t_data['isrc'], e)

                duration = t_data['duration'] or _tagging_read(local_path).get("duration")

                # Step 3 (Stored Chromaprint Fast-Path)
                if not new_musicbrainz_id and t_data['has_fp_record'] and t_data['chromaprint'] and fingerprint_provider and duration:
                    logger.debug("Step 3 (Stored Chromaprint): Re-resolving via AcoustID for %s", local_path.name)
                    try:
                        duration_secs = int(duration / 1000) if duration > 10000 else duration
                        details = fingerprint_provider.resolve_fingerprint_details(t_data['chromaprint'], duration_secs)
                        if details.get('mbids'):
                            new_musicbrainz_id = details['mbids'][0]
                            logger.debug("Step 3: resolved MBID %s for %s", new_musicbrainz_id, local_path.name)
                        if details.get('acoustid_id') and not t_data['acoustid_id']:
                            t_data['acoustid_id'] = details['acoustid_id']
                    except Exception as e:
                        logger.warning("AcoustID fast-path resolution failed: %s", e)

                # Step 4 (Generate Chromaprint)
                new_chromaprint_generated = False
                if not new_musicbrainz_id and not t_data['chromaprint'] and fingerprint_provider and duration:
                    logger.debug("Step 4 (Generate Chromaprint): Fingerprinting %s", local_path.name)
                    try:
                        chromaprint = FingerprintGenerator.generate(str(local_path))
                        if chromaprint:
                            found_new_data = True
                            t_data['chromaprint'] = chromaprint
                            new_chromaprint_generated = True
                            duration_secs = int(duration / 1000) if duration > 10000 else duration

                            # Step 4a (Chromaprint Cache) - We do this in the later session commit phase if we can,
                            # but we need to check if there's a cached one now to avoid network call.
                            # Since we don't have session here, we will just make the network call if we can't do the cache check.
                            # For absolute safety and to fix deadlock, we accept doing the network call, OR we open a tiny session just to check cache.
                            with db.session_scope() as cache_session:
                                cached_fp = cache_session.query(AudioFingerprint).filter_by(chromaprint=chromaprint).first()
                                linked_mbid = None
                                if cached_fp:
                                    linked_fp = (
                                        cache_session.query(AudioFingerprint)
                                        .join(Track, AudioFingerprint.track_id == Track.id)
                                        .filter(
                                            AudioFingerprint.chromaprint == chromaprint,
                                            AudioFingerprint.track_id != t_data['id'],
                                            Track.musicbrainz_id.isnot(None),
                                            Track.musicbrainz_id != "NOT_FOUND",
                                        )
                                        .first()
                                    )
                                    if linked_fp:
                                        linked = cache_session.get(Track, linked_fp.track_id)
                                        linked_mbid = linked.musicbrainz_id

                            if linked_mbid:
                                new_musicbrainz_id = linked_mbid
                                logger.info("Step 4a (Chromaprint Cache Hit): MBID %s reused for %s", new_musicbrainz_id, local_path.name)
                                t_data['acoustid_id'] = cached_fp.acoustid_id if cached_fp else None
                            else:
                                details = fingerprint_provider.resolve_fingerprint_details(chromaprint, duration_secs)
                                if details.get('mbids'):
                                    new_musicbrainz_id = details['mbids'][0]
                                if details.get('acoustid_id') and not t_data['acoustid_id']:
                                    t_data['acoustid_id'] = details['acoustid_id']

                    except Exception as e:
                        logger.warning("Fingerprint generation/resolution failed: %s", e)

                t_data['new_chromaprint_generated'] = new_chromaprint_generated

                # Step 5 (Text Fallback)
                if not new_musicbrainz_id and metadata_provider and t_data['artist_name'] and t_data['title']:
                    logger.debug("Step 5 (Text Fallback): Searching MusicBrainz for %s - %s", t_data['artist_name'], t_data['title'])
                    try:
                        query = f"{t_data['artist_name']} {t_data['title']}"
                        results = metadata_provider.search(query, type="track", limit=5)
                        if results:
                            file_track = EchosyncTrack(
                                raw_title=t_data['title'],
                                artist_name=t_data['artist_name'],
                                album_title=t_data['album_title'],
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
                                            t_data['isrc'] = candidate.isrc
                    except Exception as e:
                        logger.warning("Text fallback search failed: %s", e, exc_info=True)

                if new_musicbrainz_id:
                    t_data['musicbrainz_id'] = new_musicbrainz_id
                    found_new_data = True
                    logger.info("Identified MBID %s for %s", new_musicbrainz_id, local_path.name)
                    t_data['metadata_status']['enhanced'] = True

                    if metadata_provider:
                        try:
                            meta = metadata_provider.get_metadata(new_musicbrainz_id)
                            if meta and not t_data['isrc'] and meta.get('isrc'):
                                t_data['isrc'] = meta.get('isrc')
                        except Exception:
                            pass
                else:
                    attempts = t_data['metadata_status'].get('enhancement_attempts', 0) + 1
                    t_data['metadata_status']['enhancement_attempts'] = attempts
                    t_data['musicbrainz_id'] = "NOT_FOUND"
                    logger.warning(
                        "Failed to identify track %d: %s (attempt %d/%d)",
                        t_data['id'], local_path.name, attempts, MAX_REATTEMPTS,
                    )

                if found_new_data:
                    update_tags = {}
                    if t_data['musicbrainz_id'] and t_data['musicbrainz_id'] != "NOT_FOUND":
                        update_tags['musicbrainz_id'] = t_data['musicbrainz_id']
                        update_tags['recording_id'] = t_data['musicbrainz_id']
                    if t_data['isrc']:
                        update_tags['isrc'] = t_data['isrc']

                    if update_tags:
                        try:
                            _tagging_write(local_path, update_tags)
                        except Exception as e:
                            logger.warning("Failed to write tags to %s: %s", local_path.name, e)

                results_to_commit.append(t_data)

            # Step 6: Commit the batch updates in a new short session
            with db.session_scope() as session:
                for res in results_to_commit:
                    track = session.get(Track, res['id'])
                    if not track:
                        continue

                    if res['musicbrainz_id'] != "NOT_FOUND":
                        track.musicbrainz_id = res['musicbrainz_id']
                    else:
                        track.musicbrainz_id = "NOT_FOUND"

                    if res['isrc']:
                        track.isrc = res['isrc']

                    track.metadata_status = res['metadata_status']
                    flag_modified(track, "metadata_status")

                    if res['metadata_status'].get('artist_fixed_from_tags') and track.artist:
                        track.artist.name = res['artist_name']

                    if res['new_chromaprint_generated']:
                        track_fp = AudioFingerprint(
                            track_id=track.id,
                            chromaprint=res['chromaprint'],
                            acoustid_id=res['acoustid_id'],
                        )
                        session.add(track_fp)
                    elif res['has_fp_record'] and res['acoustid_id']:
                        # Update existing FP record
                        track_fp = session.query(AudioFingerprint).filter_by(track_id=track.id).first()
                        if track_fp and not track_fp.acoustid_id:
                            track_fp.acoustid_id = res['acoustid_id']

                    track = hook_manager.apply_filters('post_metadata_enrichment', track)
                    total_processed += 1


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
                        # Convert file to EchosyncTrack for matching
                        file_track = self._filename_to_track(file_path, duration_ms)
                        
                        # Convert search results to EchosyncTracks
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

    def tag_file(self, file_path: Path, metadata: Dict[str, Any]) -> None:
        """Write *metadata* to the physical audio file at *file_path*.

        Translates the flat metadata dict produced by ``identify_file`` /
        ``auto_importer`` into the tag keys understood by ``_tagging_write``,
        then writes them via Mutagen.  Called by ``auto_importer.finalize_import``
        before the file is moved into the library.
        """
        tags_to_write: Dict[str, Any] = {}

        field_map = {
            'title':        'title',
            'artist':       'artist',
            'album':        'album',
            'date':         'date',
            'track_number': 'track_number',
            'disc_number':  'disc_number',
            'isrc':         'isrc',
            'recording_id': 'recording_id',
            'musicbrainz_id': 'musicbrainz_id',
            'acoustid_id':  'acoustid_id',
            'cover_art_url': 'cover_art_url',
        }

        for src_key, dst_key in field_map.items():
            value = metadata.get(src_key)
            if value is not None and value != '':
                tags_to_write[dst_key] = value

        # Ensure both MBID keys stay in sync (some tag readers check one, others the other).
        if tags_to_write.get('musicbrainz_id') and not tags_to_write.get('recording_id'):
            tags_to_write['recording_id'] = tags_to_write['musicbrainz_id']
        elif tags_to_write.get('recording_id') and not tags_to_write.get('musicbrainz_id'):
            tags_to_write['musicbrainz_id'] = tags_to_write['recording_id']

        if not tags_to_write:
            logger.debug("tag_file: no writable tags for %s — skipping write.", file_path.name)
            return

        try:
            _tagging_write(file_path, tags_to_write)
            logger.info("tag_file: wrote %d tag(s) to %s", len(tags_to_write), file_path.name)
        except Exception as exc:
            logger.warning("tag_file: failed to write tags for %s: %s", file_path.name, exc)
            raise

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

    def _filename_to_track(self, file_path: Path, duration_ms: Optional[int]) -> EchosyncTrack:
        """Convert filename to EchosyncTrack for matching using provider_base helper."""
        from core.track_parser import TrackParser
        from core.provider_base import ProviderBase
        
        # Use TrackParser to extract artist/title from filename
        parser = TrackParser()
        parsed = parser.parse_filename(file_path.stem)
        
        # Use the standard factory method from ProviderBase
        return ProviderBase.create_echo_sync_track(
            title=(parsed.title if parsed else None) or file_path.stem,
            artist=(parsed.artist_name if parsed else None) or 'Unknown Artist',
            album=(parsed.album_title if parsed else None) or '',
            duration_ms=duration_ms,
            provider_id=str(file_path),
            source='local_file'
        )
    
    def _search_result_to_track(self, result: Dict[str, Any]) -> Optional[EchosyncTrack]:
        """Convert MusicBrainz search result to EchosyncTrack using provider_base helper."""
        from core.provider_base import ProviderBase
        
        try:
            return ProviderBase.create_echo_sync_track(
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
