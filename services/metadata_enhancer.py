"""
Metadata Enhancer Service - Service for identifying and tagging audio.

This service focuses on:
1. Fingerprinting audio (AcoustID)
2. Fetching metadata (MusicBrainz)
3. Tagging files (Mutagen)
4. Managing the Review Queue (Database)

It does NOT move files or scan directories (see AutoImportService).
"""

from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import datetime

from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import OperationalError
from core.enums import Capability
from core.file_handling.tagging_io import read_tags as _tagging_read, write_tags as _tagging_write
from core.hook_manager import hook_manager
from core.tiered_logger import get_logger
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
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



class RetroactiveEnhancer:
    """Background service for library-wide batch metadata enhancement."""

    def _get_plugin(self, capability: Capability, required_algorithm: str = None):
        from core.nexus_framework.plugin_loader import PluginRegistry
        
        plugins = PluginRegistry.get_plugins_with_capability(capability)
        for p in plugins:
            if not required_algorithm:
                return p
            
            # Check algorithm support if required
            caps = getattr(p, 'capabilities', None)
            if caps and capability == Capability.RESOLVE_FINGERPRINT:
                algorithms = getattr(caps, 'fingerprint_algorithms', []) or []
                if not algorithms and getattr(caps, 'supports_fingerprinting', False):
                    algorithms = ['chromaprint']  # Default legacy
                if required_algorithm in algorithms:
                    return p
                    
        return None

    def identify_file(self, file_path: Path) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Identify a file using Fingerprinting and/or Metadata Search.
        Returns (metadata, confidence_score).

        On failure: Returns (None, 0.0) - file will be marked for manual review.
        """
        fingerprint_provider = self._get_plugin(Capability.RESOLVE_FINGERPRINT, required_algorithm='chromaprint')
        metadata_provider = self._get_plugin(Capability.FETCH_METADATA)

        metadata = None
        confidence = 0.0

        try:
            # Step A: Try AcoustID fingerprint lookup first
            try:
                fingerprint = FingerprintGenerator.generate(str(file_path))
                # Invoke local_metadata to get duration safely via authorized wrapper
                from core.nexus_framework.plugin_loader import plugin_loader
                local_metadata_plugin = plugin_loader.get_plugin("EchoSync.local_metadata")
                duration_sec = None
                track_obj = None
                if local_metadata_plugin:
                    track_obj = local_metadata_plugin.get_track_from_file(str(file_path))
                    if track_obj and track_obj.duration:
                        duration_sec = int(track_obj.duration / 1000)

                if fingerprint and duration_sec and fingerprint_provider:
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
                        else:
                            logger.debug(f"✗ No MBID found from AcoustID for {file_path.name}")
                    except Exception as e:
                        logger.warning(f"AcoustID fingerprint resolution failed: {e}")
            except Exception as e:
                logger.warning(f"AcoustID check failed: {e}")

            # Step B: If AcoustID fails, invoke the EchoSync.local_metadata plugin (already read tags above if track_obj is present)
            from core.nexus_framework.plugin_loader import plugin_loader
            local_metadata_plugin = plugin_loader.get_plugin("EchoSync.local_metadata")
            if not track_obj and local_metadata_plugin:
                track_obj = local_metadata_plugin.get_track_from_file(str(file_path))

            # Step C: If tags are found, construct the EchoSyncTrack object and pass to lookup
            if track_obj:
                # Fast path: Check if tags contain an embedded MBID
                if track_obj.musicbrainz_id and metadata_provider:
                    logger.info(f"Found MBID {track_obj.musicbrainz_id} in local_metadata tags for {file_path.name}")
                    try:
                        metadata = metadata_provider.get_metadata(track_obj.musicbrainz_id)
                        if metadata:
                            return metadata, 0.99
                    except Exception as e:
                        logger.warning(f"Failed to fetch metadata for tag MBID {track_obj.musicbrainz_id}: {e}")

                if track_obj.title and track_obj.artist_name and metadata_provider:
                    logger.debug(f"Attempting search fallback using local_metadata tags for {file_path.name}")
                    try:
                        results = metadata_provider.search_metadata(track_obj, limit=10)
                        if results:
                            candidate_tracks = []
                            for result in results:
                                candidate = self._search_result_to_track(result)
                                if candidate:
                                    candidate_tracks.append((candidate, result.get('mbid') or result.get('recording_id')))

                            if candidate_tracks:
                                engine_cls = ServiceRegistry.resolve('matching_engine') or WeightedMatchingEngine
                                matcher = engine_cls(PROFILE_EXACT_SYNC)
                                best_score = 0.0
                                best_mbid = None

                                for candidate, mbid in candidate_tracks:
                                    match_result = matcher.calculate_match(track_obj, candidate)
                                    score = match_result.confidence_score if match_result else 0.0
                                    if score > best_score:
                                        best_score = score
                                        best_mbid = mbid

                                if best_score >= 85.0 and best_mbid:
                                    logger.info(f"✓ Matched '{file_path.name}' via local_metadata text search (score: {best_score:.1f}%)")
                                    metadata = metadata_provider.get_metadata(best_mbid)
                                    if metadata:
                                        return metadata, best_score / 100.0
                        else:
                            logger.debug(f"No search results for fallback query using local_metadata")
                    except Exception as e:
                        logger.warning(f"Fallback search using local_metadata failed: {e}", exc_info=True)

            # Step D: If no tags are found or search failed, halt execution. Do not guess.
            logger.warning(f"All metadata identification methods failed for {file_path.name}. File will be queued for manual review.")
            return None, 0.0

        except Exception as e:
            logger.error(f"Unexpected error identifying {file_path}: {e}", exc_info=True)
            return None, 0.0

        return metadata, confidence

    def identify_batch(self, file_paths: list[str]) -> dict:
        results = {}
        fingerprint_provider = self._get_plugin(Capability.RESOLVE_FINGERPRINT, required_algorithm='chromaprint')
        metadata_provider = self._get_plugin(Capability.FETCH_METADATA)

        for path_str in file_paths:
            metadata = None
            try:
                fingerprint = FingerprintGenerator.generate(path_str)
                if fingerprint and fingerprint_provider:
                    duration_ms = _tagging_read(Path(path_str)).get("duration", 0)
                    duration_sec = int(duration_ms / 1000) if duration_ms else 0
                    mbids = fingerprint_provider.resolve_fingerprint(fingerprint, duration_sec)
                    if mbids and metadata_provider:
                        mbid = mbids[0]
                        metadata = metadata_provider.get_metadata(mbid)
            except Exception as e:
                logger.error(f"Error identifying {path_str}: {e}")
            results[path_str] = metadata

        return results

    def read_tags(self, file_path: Path) -> Dict[str, Any]:
        """Read tags from a file using the internal tagging helper."""
        return _tagging_read(file_path)

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

    def create_or_update_review_task(self, file_path: Any, decision: Any = None, match_data: Any = None, confidence_score: float = 0.0, status: str = 'pending') -> None:
        try:
            file_path_str = str(file_path)
            
            # Positional argument compatibility normalization
            if isinstance(decision, dict) and (isinstance(match_data, (float, int)) or match_data is None):
                confidence_score = float(match_data) if match_data is not None else 1.0
                match_data = decision
                decision = "Approved match"
                
            if not confidence_score and isinstance(match_data, (float, int)):
                confidence_score = float(match_data)
                match_data = None

            # 1. Check if the task already exists by file_path
            db = get_working_database()
            with db.session_scope() as session:
                existing = session.query(ReviewTask).filter(ReviewTask.file_path == file_path_str).first()
                
                # 2. Get/Create EchosyncTrack
                from core.matching_engine.track_parser import parse_file
                from core.matching_engine.echo_sync_track import EchosyncTrack
                
                track = None
                from core.file_handling import check_file_exists
                if check_file_exists(file_path_str):
                    try:
                        track = parse_file(file_path_str, generate_fingerprint=True)
                    except Exception as parse_err:
                        logger.warning(f"Failed to parse file {file_path_str} for review task: {parse_err}")
                
                if not track:
                    track = EchosyncTrack(
                        raw_title=Path(file_path_str).name,
                        artist_name="Unknown Artist",
                        album_title="Unknown Album"
                    )
                
                # 3. Merge incoming match_data (metadata suggestion) if present
                if isinstance(match_data, dict):
                    if match_data.get("title"):
                        track.raw_title = match_data["title"]
                        track.title = match_data["title"]
                        track.display_title = match_data["title"]
                    if match_data.get("artist"):
                        track.artist_name = match_data["artist"]
                    if match_data.get("album"):
                        track.album_title = match_data["album"]
                    if match_data.get("year"):
                        try:
                            track.release_year = int(match_data["year"])
                        except Exception:
                            pass
                    if match_data.get("track_number"):
                        try:
                            track.track_number = int(match_data["track_number"])
                        except Exception:
                            pass
                    if match_data.get("disc_number"):
                        try:
                            track.disc_number = int(match_data["disc_number"])
                        except Exception:
                            pass
                    if match_data.get("musicbrainz_id"):
                        track.musicbrainz_id = match_data["musicbrainz_id"]
                    if match_data.get("isrc"):
                        track.isrc = match_data["isrc"]
                    if match_data.get("duration"):
                        try:
                            track.duration = int(match_data["duration"])
                        except Exception:
                            pass

                track_dict = track.to_dict()
                
                if existing:
                    existing.track_data = track_dict
                    existing.status = status
                    existing.confidence_score = confidence_score
                    existing.created_at = datetime.datetime.now(datetime.UTC)
                else:
                    task = ReviewTask(
                        file_path=file_path_str,
                        status=status,
                        track_data=track_dict,
                        confidence_score=confidence_score
                    )
                    session.add(task)
            logger.info(f"Review Task pending/updated: {file_path_str} (status={status})")
        except Exception as e:
            logger.error(f"Failed to update review task: {e}", exc_info=True)

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
        from core.matching_engine.track_parser import TrackParser
        from core.nexus_framework.plugin_SDK import PluginBase

        # Use TrackParser to extract artist/title from filename
        parser = TrackParser()
        parsed = parser.parse_filename(file_path.stem)

        # Use the standard factory method from PluginBase
        return PluginBase.create_echo_sync_track(
            title=(parsed.title if parsed else None) or file_path.stem,
            artist=(parsed.artist_name if parsed else None) or 'Unknown Artist',
            album=(parsed.album_title if parsed else None) or '',
            duration_ms=duration_ms,
            provider_id=str(file_path),
            source='local_file'
        )

    def _search_result_to_track(self, result: Dict[str, Any]) -> Optional[EchosyncTrack]:
        """Convert MusicBrainz search result to EchosyncTrack using provider_base helper."""
        from core.nexus_framework.plugin_SDK import PluginBase

        try:
            return PluginBase.create_echo_sync_track(
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

    def enhance_library_metadata(self, batch_size=50) -> None:
        """Retroactive metadata enhancer following a Local-First, highly efficient 5-Step Pipeline.

        Loops through batches until no more tracks require enhancement.  Each batch is
        committed in its own session so memory stays flat even on large libraries.
        """
        from sqlalchemy import or_, and_, func, Integer
        from database.music_database import get_database, Track, Artist, AudioFingerprint
        from core.file_handling.path_mapper import PathMapper
        from core.matching_engine.scoring_profile import ExactSyncProfile
        from core.matching_engine.fingerprinting import FingerprintGenerator
        from core.matching_engine.echo_sync_track import EchosyncTrack
        from core.matching_engine.matching_engine import WeightedMatchingEngine
        from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
        from pathlib import Path

        MAX_REATTEMPTS = 5

        db = get_database()

        fingerprint_provider = self._get_plugin(Capability.RESOLVE_FINGERPRINT, required_algorithm='chromaprint')
        metadata_provider = self._get_plugin(Capability.FETCH_METADATA)

        total_processed = 0
        MAX_ITERATIONS = 500  # safety cap — prevents infinite loops on persistent failures

        required_keys = hook_manager.apply_filters('register_metadata_requirements', [])
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
                    from database.music_database import LocalMedia
                    track_fp = session.query(AudioFingerprint).join(LocalMedia, AudioFingerprint.media_id == LocalMedia.media_id).filter(LocalMedia.track_id == track.id).first()
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


            # ── Chunked Processing with Absolute Trust Waterfall ──
            import asyncio
            from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry

            mb_client = PluginRegistry.get_plugin("musicbrainz")
            CHUNK_SIZE = 50

            for chunk_start in range(0, len(track_data_list), CHUNK_SIZE):
                chunk = track_data_list[chunk_start:chunk_start + CHUNK_SIZE]

                # Buckets
                bucket_trust = []   # MBID found locally, all required tags present
                bucket_target = []  # MBID found locally, missing some tags
                bucket_heavy = []   # No MBID found locally

                for t_data in chunk:
                    local_path_str = PathMapper.to_local(t_data['file_path'])
                    local_path = Path(local_path_str)
                    
                    if not local_path.exists():
                        logger.warning("Enhancer skipping missing file: %s", local_path)
                        t_data['musicbrainz_id'] = "NOT_FOUND"
                        t_data['metadata_status']['enhancement_attempts'] = t_data['metadata_status'].get('enhancement_attempts', 0) + 1
                        results_to_commit.append(t_data)
                        continue

                    # Step 1: Read Local Tags
                    try:
                        file_tags = _tagging_read(local_path)
                    except Exception as e:
                        logger.warning("Failed to read tags from %s: %s", local_path.name, e)
                        file_tags = {}

                    tag_mbid = file_tags.get("musicbrainz_id") or file_tags.get("recording_id")
                    
                    # Also fix VA artist from tags if needed
                    if not t_data['metadata_status'].get('artist_fixed_from_tags'):
                        tag_artist = file_tags.get("artist")
                        if tag_artist and t_data['artist_name'] and t_data['artist_name'].lower().startswith("various artist"):
                            t_data['artist_name'] = tag_artist
                            t_data['metadata_status']['artist_fixed_from_tags'] = True
                            t_data['metadata_changed'] = True

                    # Determine missing fields
                    missing_fields = []
                    for key in required_keys:
                        if not t_data['metadata_status'].get(key):
                            missing_fields.append(key)

                    if tag_mbid:
                        t_data['musicbrainz_id'] = tag_mbid
                        if not missing_fields:
                            bucket_trust.append((t_data, local_path, file_tags))
                        else:
                            bucket_target.append((t_data, local_path, file_tags))
                    else:
                        bucket_heavy.append((t_data, local_path, file_tags))

                # Step 2: Absolute Trust Gate
                for t_data, local_path, file_tags in bucket_trust:
                    logger.info("Absolute Trust Gate Passed: %s", local_path.name)
                    t_data['metadata_status']['enhanced'] = True
                    results_to_commit.append(t_data)

                # Step 3: Targeted Fetch
                if bucket_target:
                    if mb_client:
                        mbids_to_fetch = [t[0]['musicbrainz_id'] for t in bucket_target]
                        logger.info("Targeted Fetch for %d tracks", len(bucket_target))
                        batch_metadata = mb_client.get_metadata_batch(mbids_to_fetch) if getattr(mb_client.capabilities, 'supports_batching', False) else {}
                        
                        for t_data, local_path, file_tags in bucket_target:
                            mbid = t_data['musicbrainz_id']
                            # Fallback to 1-by-1 if batching not supported or failed
                            meta = batch_metadata.get(mbid)
                            if not meta and not batch_metadata:
                                try:
                                    meta = mb_client.get_metadata(mbid)
                                except Exception:
                                    pass

                            if meta:
                                if not t_data['isrc'] and meta.get('isrc'):
                                    t_data['isrc'] = meta.get('isrc')
                                
                                update_tags = {'musicbrainz_id': mbid, 'recording_id': mbid}
                                if t_data['isrc']:
                                    update_tags['isrc'] = t_data['isrc']
                                try:
                                    _tagging_write(local_path, update_tags)
                                except Exception:
                                    pass
                                    
                                t_data['metadata_status']['enhanced'] = True
                                for key in required_keys:
                                    t_data['metadata_status'][key] = True
                                t_data['metadata_changed'] = True
                            else:
                                t_data['metadata_status']['enhancement_attempts'] = t_data['metadata_status'].get('enhancement_attempts', 0) + 1
                            results_to_commit.append(t_data)
                    else:
                        for t_data, local_path, file_tags in bucket_target:
                            t_data['metadata_status']['enhancement_attempts'] = t_data['metadata_status'].get('enhancement_attempts', 0) + 1
                            results_to_commit.append(t_data)

                # Step 4: Heavyweight Fingerprint Discovery
                for t_data, local_path, file_tags in bucket_heavy:
                    new_musicbrainz_id = None
                    duration = t_data['duration'] or file_tags.get("duration")
                    t_data['new_chromaprint_generated'] = False

                    if fingerprint_provider and duration:
                        if not t_data['chromaprint']:
                            try:
                                chromaprint = FingerprintGenerator.generate(str(local_path))
                                if chromaprint:
                                    t_data['chromaprint'] = chromaprint
                                    t_data['new_chromaprint_generated'] = True
                            except Exception:
                                pass

                        if t_data['chromaprint']:
                            try:
                                duration_secs = int(duration / 1000) if duration > 10000 else duration
                                details = fingerprint_provider.resolve_fingerprint_details(t_data['chromaprint'], duration_secs)
                                if details.get('mbids'):
                                    new_musicbrainz_id = details['mbids'][0]
                                if details.get('acoustid_id'):
                                    t_data['acoustid_id'] = details['acoustid_id']
                            except Exception:
                                pass

                    if new_musicbrainz_id:
                        t_data['musicbrainz_id'] = new_musicbrainz_id
                        logger.info("Heavyweight Fingerprint Success: %s -> %s", local_path.name, new_musicbrainz_id)
                        if mb_client:
                            try:
                                meta = mb_client.get_metadata(new_musicbrainz_id)
                                if meta and not t_data['isrc'] and meta.get('isrc'):
                                    t_data['isrc'] = meta.get('isrc')
                            except Exception:
                                pass
                                
                        update_tags = {'musicbrainz_id': new_musicbrainz_id, 'recording_id': new_musicbrainz_id}
                        if t_data['isrc']:
                            update_tags['isrc'] = t_data['isrc']
                        try:
                            _tagging_write(local_path, update_tags)
                        except Exception:
                            pass
                            
                        t_data['metadata_status']['enhanced'] = True
                        for key in required_keys:
                            t_data['metadata_status'][key] = True
                        t_data['metadata_changed'] = True
                    else:
                        logger.info("Heavyweight Fingerprint returned no matches for: %s", local_path.name)
                        t_data['musicbrainz_id'] = "NOT_FOUND"
                        t_data['metadata_status']['enhancement_attempts'] = t_data['metadata_status'].get('enhancement_attempts', 0) + 1

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

                    if res.get('new_chromaprint_generated', False):
                        # Avoid IntegrityError by checking if it exists
                        existing_fp = session.query(AudioFingerprint).filter_by(chromaprint=res['chromaprint']).first()
                        if not existing_fp:
                            track_fp = AudioFingerprint(
                                track_id=track.id,
                                chromaprint=res['chromaprint'],
                                acoustid_id=res['acoustid_id'],
                            )
                            session.add(track_fp)
                        else:
                            logger.debug(f"Skipping audio fingerprint insert for {track.id}: duplicate chromaprint.")
                    elif res['has_fp_record'] and res['acoustid_id']:
                        # Update existing FP record
                        track_fp = session.query(AudioFingerprint).filter_by(track_id=track.id).first()
                        if track_fp and not track_fp.acoustid_id:
                            track_fp.acoustid_id = res['acoustid_id']

                    # Always apply post-metadata enrichment hooks so that the cjk_restored stamp is set and aliases are persisted
                    track = hook_manager.apply_filters('post_metadata_enrichment', track)
                    flag_modified(track, "metadata_status")
                    total_processed += 1




class MetadataEnhancerService(RetroactiveEnhancer):
    _instance = None

    def __init__(self):
        super().__init__()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MetadataEnhancerService()
        return cls._instance

def get_metadata_enhancer():
    return MetadataEnhancerService.get_instance()

def register_metadata_enhancer_service():
    """Kept for compatibility, though it no longer registers background jobs."""
    get_metadata_enhancer()
    logger.info("Metadata Enhancer Service initialized")
