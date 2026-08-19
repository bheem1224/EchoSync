"""
Metadata Enhancer Service - Service for identifying and tagging audio.

This service focuses on:
1. Fingerprinting audio (AcoustID)
2. Fetching metadata (MusicBrainz)
3. Tagging files (echosync_core)
4. Managing the Review Queue (Database)

It does NOT move files or scan directories (see AutoImportService).
"""

from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import datetime

from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import OperationalError
from core.enums import Capability
from core.hook_manager import hook_manager
from core.tiered_logger import get_logger
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
from core.matching_engine.scoring_profile import PROFILE_EXACT_SYNC
from core.db.echo_sync_track import EchosyncTrack
from database.working_database import get_working_database, ReviewTask
import echosync_core

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
        tags = echosync_core.extract_metadata(str(file_path))
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


def _tagging_write(file_path: Any, tags: Dict[str, Any]) -> None:
    """
    Write physical audio tags to a file via echosync_core.
    If PyO3 bindings for physical tag writing are not exposed for a specific format,
    fails gracefully.
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning("_tagging_write: file does not exist at %s", path)
        return

    tags_dict = {str(k): str(v) for k, v in tags.items() if v not in (None, '')}
    if not tags_dict:
        return

    try:
        if hasattr(echosync_core, "write_metadata"):
            echosync_core.write_metadata(str(path), tags_dict)
            logger.debug("_tagging_write: wrote tags to %s via echosync_core", path.name)
        elif hasattr(echosync_core, "write_tags"):
            echosync_core.write_tags(str(path), tags_dict)
            logger.debug("_tagging_write: wrote tags to %s via echosync_core", path.name)
        else:
            logger.debug("_tagging_write: physical tag writing not yet exposed in echosync_core for %s", path.name)
    except Exception as e:
        logger.warning("_tagging_write: failed writing tags to %s via echosync_core: %s", path.name, e)


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
            # Priority 1: Native file tags (parsed via echosync_core)
            track_obj = None
            raw_tags = {}
            try:
                import echosync_core
                raw_tags = echosync_core.extract_metadata(str(file_path)) or {}

                # Support both echosync_core native keys and legacy fallback keys
                raw_dur_ms = raw_tags.get("duration_ms")
                if raw_dur_ms is not None:
                    duration_ms = int(raw_dur_ms)
                    duration_sec = duration_ms / 1000.0
                elif raw_tags.get("duration") is not None:
                    duration_sec = float(raw_tags["duration"])
                    duration_ms = int(duration_sec * 1000)
                else:
                    duration_ms = None
                    duration_sec = None

                mbid = raw_tags.get("mbid") or raw_tags.get("musicbrainz_id") or raw_tags.get("musicbrainz_trackid")

                track_obj = EchosyncTrack(
                    raw_title=raw_tags.get("title") or "",
                    artist_name=raw_tags.get("artist") or raw_tags.get("artist_name") or "",
                    album_title=raw_tags.get("album") or raw_tags.get("album_title") or ""
                )
                if duration_ms:
                    track_obj.duration = int(duration_ms)
                if raw_tags.get("track_number") or raw_tags.get("track_no"):
                    try:
                        track_obj.track_number = int(str(raw_tags.get("track_number") or raw_tags.get("track_no")).split("/")[0])
                    except: pass
                if raw_tags.get("disc_number") or raw_tags.get("disc_no"):
                    try:
                        track_obj.disc_number = int(str(raw_tags.get("disc_number") or raw_tags.get("disc_no")).split("/")[0])
                    except: pass
                if raw_tags.get("year") or raw_tags.get("date"):
                    try:
                        val = str(raw_tags.get("year") or raw_tags.get("date"))
                        track_obj.release_year = int(val[:4])
                    except: pass
                if mbid:
                    track_obj.musicbrainz_id = mbid
                if raw_tags.get("isrc"):
                    track_obj.isrc = raw_tags["isrc"]
            except Exception as e:
                logger.warning(f"Failed to read native tags via echosync_core for {file_path.name}: {e}")

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
                            if isinstance(results, EchosyncTrack):
                                results_list = [results]
                            elif isinstance(results, (list, tuple)):
                                results_list = list(results)
                            else:
                                results_list = [results]

                            candidate_tracks = []
                            for result in results_list:
                                if isinstance(result, EchosyncTrack):
                                    candidate = result
                                    mbid = result.musicbrainz_id
                                    if not mbid and isinstance(result.identifiers, dict):
                                        mbid = result.identifiers.get('musicbrainz_recording_id') or result.identifiers.get('mbid')
                                elif isinstance(result, dict):
                                    candidate = self._search_result_to_track(result)
                                    mbid = result.get('mbid') or result.get('recording_id')
                                else:
                                    candidate = None
                                    mbid = None

                                if candidate:
                                    candidate_tracks.append((candidate, mbid))

                            if candidate_tracks:
                                from core.matching_engine.scoring_profile import PROFILE_EXACT_SYNC
                                from core.matching_engine.matching_engine import WeightedMatchingEngine
                                engine_cls = ServiceRegistry.resolve('matching_engine') or WeightedMatchingEngine
                                matcher = engine_cls(PROFILE_EXACT_SYNC)
                                best_score = 0.0
                                best_mbid = None
                                best_candidate = None

                                for candidate, mbid in candidate_tracks:
                                    match_result = matcher.calculate_match(track_obj, candidate)
                                    score = match_result.confidence_score if match_result else 0.0
                                    if score > best_score:
                                        best_score = score
                                        best_mbid = mbid
                                        best_candidate = candidate

                                if best_score >= 85.0:
                                    logger.info(f"✓ Matched '{file_path.name}' via local_metadata text search (score: {best_score:.1f}%)")
                                    if best_mbid:
                                        metadata = metadata_provider.get_metadata(best_mbid)
                                        if metadata:
                                            return metadata, best_score / 100.0
                                    if best_candidate:
                                        return best_candidate, best_score / 100.0
                        else:
                            logger.debug(f"No search results for fallback query using local_metadata")
                    except Exception as e:
                        logger.warning(f"Fallback search using local_metadata failed: {e}", exc_info=True)

            # Priority 1.5: ISRC Waterfall Resolution (if file tags contain an ISRC)
            if not metadata:
                isrc_val = (raw_tags.get("isrc") if isinstance(raw_tags, dict) else None) or (track_obj.isrc if track_obj else None)
                if isrc_val:
                    try:
                        from services.isrc_lookup_service import dispatch_isrc_lookup
                        isrc_track = dispatch_isrc_lookup(str(isrc_val).strip())
                        if isrc_track:
                            src_name = (
                                (isrc_track.identifiers.get("source") if isinstance(isrc_track.identifiers, dict) else None)
                                or "ISRC"
                            )
                            logger.info(f"Identified file via ISRC waterfall from provider: {src_name}")
                            return isrc_track, 0.92
                    except Exception as isrc_err:
                        logger.warning(f"ISRC waterfall lookup error for {file_path.name}: {isrc_err}")

            # Priority 2: AcoustID fingerprinting matches (if native tags are missing or search failed)
            if not metadata:
                try:
                    fingerprint = FingerprintGenerator.generate(str(file_path))
                    duration_sec = None
                    if track_obj and track_obj.duration:
                        duration_sec = track_obj.duration / 1000.0
                    elif raw_tags:
                        raw_dur_ms = raw_tags.get("duration_ms")
                        if raw_dur_ms is not None:
                            duration_sec = int(raw_dur_ms) / 1000.0
                        elif raw_tags.get("duration") is not None:
                            duration_sec = float(raw_tags["duration"])
                        else:
                            duration_sec = None
                    else:
                        try:
                            import echosync_core
                            raw_tags = echosync_core.extract_metadata(str(file_path)) or {}
                            raw_dur_ms = raw_tags.get("duration_ms")
                            if raw_dur_ms is not None:
                                duration_sec = int(raw_dur_ms) / 1000.0
                            elif raw_tags.get("duration") is not None:
                                duration_sec = float(raw_tags["duration"])
                            else:
                                duration_sec = None
                        except Exception:
                            duration_sec = None

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

            # Step D: If no tags are found or search failed, halt execution. Do not guess.
            logger.warning(f"All metadata identification methods failed for {file_path.name}. File will be queued for manual review.")
            return None, 0.0

        except Exception as e:
            logger.error(f"Unexpected error identifying {file_path}: {e}", exc_info=True)
            return None, 0.0

        return metadata, confidence

    def identify_batch(self, file_paths: list[str]) -> dict:
        results = {}
        for path_str in file_paths:
            metadata = None
            confidence = 0.0
            try:
                metadata, confidence = self.identify_file(Path(path_str))
            except Exception as e:
                logger.error(f"Error identifying {path_str}: {e}")
            results[path_str] = (metadata, confidence)

        return results

    def read_tags(self, file_path: Path) -> Dict[str, Any]:
        """Read tags from a file using the internal tagging helper."""
        return echosync_core.extract_metadata(str(file_path))

    def tag_file(self, file_path: Path, metadata: Dict[str, Any]) -> None:
        """Write *metadata* to the physical audio file at *file_path*.

        Translates the flat metadata dict produced by ``identify_file`` /
        ``auto_importer`` into the tag keys understood by ``_tagging_write``,
        then writes them via echosync_core.  Called by ``auto_importer.finalize_import``
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
                from core.db.echo_sync_track import EchosyncTrack
                from core.nexus_framework.plugin_loader import PluginRegistry
                from core.matching_engine.fingerprinting import FingerprintGenerator
                
                track = None
                try:
                    import echosync_core
                    raw_tags = echosync_core.extract_metadata(file_path_str) or {}
                    # Support both echosync_core native keys and legacy fallback keys
                    raw_dur_ms = raw_tags.get("duration_ms")
                    if raw_dur_ms is not None:
                        duration_ms = int(raw_dur_ms)
                        duration_sec = duration_ms / 1000.0
                    elif raw_tags.get("duration") is not None:
                        duration_sec = float(raw_tags["duration"])
                        duration_ms = int(duration_sec * 1000)
                    else:
                        duration_ms = None
                        duration_sec = None

                    mbid = raw_tags.get("mbid") or raw_tags.get("musicbrainz_id") or raw_tags.get("musicbrainz_trackid")
                    track = EchosyncTrack(
                        raw_title=raw_tags.get("title") or "",
                        artist_name=raw_tags.get("artist") or raw_tags.get("artist_name") or "",
                        album_title=raw_tags.get("album") or raw_tags.get("album_title") or ""
                    )
                    if duration_ms:
                        track.duration = int(duration_ms)
                    if raw_tags.get("track_number") or raw_tags.get("track_no"):
                        try:
                            track.track_number = int(str(raw_tags.get("track_number") or raw_tags.get("track_no")).split("/")[0])
                        except: pass
                    if raw_tags.get("disc_number") or raw_tags.get("disc_no"):
                        try:
                            track.disc_number = int(str(raw_tags.get("disc_number") or raw_tags.get("disc_no")).split("/")[0])
                        except: pass
                    if raw_tags.get("year") or raw_tags.get("date"):
                        try:
                            val = str(raw_tags.get("year") or raw_tags.get("date"))
                            track.release_year = int(val[:4])
                        except: pass
                    if mbid:
                        track.musicbrainz_id = mbid
                    if raw_tags.get("isrc"):
                        track.isrc = raw_tags["isrc"]
                except Exception as parse_err:
                    logger.warning(f"Failed to get track from file via echosync_core: {parse_err}")
                
                if not track:
                    track = EchosyncTrack(
                        raw_title="",
                        artist_name="",
                        album_title=""
                    )

                # Local heuristic fallback when tags are absent/empty
                if not track.artist_name or not (track.title or track.raw_title):
                    try:
                        from core.matching_engine.track_parser import TrackParser
                        parsed_meta = TrackParser.parse_filename(file_path_str)
                        if parsed_meta:
                            parsed_artist = getattr(parsed_meta, 'artist', None) or getattr(parsed_meta, 'artist_name', None)
                            parsed_title = getattr(parsed_meta, 'title', None) or getattr(parsed_meta, 'raw_title', None)
                            if parsed_artist and not track.artist_name:
                                track.artist_name = parsed_artist
                            if parsed_title and not (track.title or track.raw_title):
                                track.title = parsed_title
                                track.raw_title = parsed_title
                            if getattr(parsed_meta, 'display_title', None) and not track.display_title:
                                track.display_title = parsed_meta.display_title
                            if getattr(parsed_meta, 'album_title', None) and not track.album_title:
                                track.album_title = parsed_meta.album_title
                    except Exception as tp_err:
                        logger.debug(f"TrackParser filename fallback error for {file_path_str}: {tp_err}")

                from core.io_gatekeeper import Gatekeeper
                file_exists = False
                try:
                    Gatekeeper.authorize_and_execute({"operation": "validate_only", "target": file_path_str})
                    file_exists = Path(file_path_str).is_file()
                except Exception:
                    pass
                if file_exists and not track.fingerprint:
                    try:
                        fingerprint = FingerprintGenerator.generate(file_path_str)
                        if fingerprint:
                            track.fingerprint = fingerprint
                            track.fingerprint_confidence = 1.0
                    except Exception as fp_err:
                        logger.warning(f"Failed to generate fingerprint for review task: {fp_err}")
                
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

                # Ensure track_data dictionary contains structured artist_name, title, display_title, album_title
                # using TrackParser fallback if still missing
                if not track_dict.get('artist_name') and not track_dict.get('artist') or not track_dict.get('title'):
                    try:
                        from core.matching_engine.track_parser import TrackParser
                        parsed_meta = TrackParser.parse_filename(file_path_str)
                        if parsed_meta:
                            parsed_artist = getattr(parsed_meta, 'artist', None) or getattr(parsed_meta, 'artist_name', None)
                            parsed_title = getattr(parsed_meta, 'title', None) or getattr(parsed_meta, 'raw_title', None)
                            if parsed_artist:
                                track_dict['artist_name'] = parsed_artist
                                track_dict['artist'] = parsed_artist
                            if parsed_title:
                                track_dict['title'] = parsed_title
                                track_dict['raw_title'] = parsed_title
                            if getattr(parsed_meta, 'display_title', None):
                                track_dict['display_title'] = parsed_meta.display_title
                            if getattr(parsed_meta, 'album_title', None):
                                track_dict['album_title'] = parsed_meta.album_title
                    except Exception as tp_err:
                        logger.debug(f"TrackParser fallback dictionary error for {file_path_str}: {tp_err}")
                else:
                    if track_dict.get('artist') and not track_dict.get('artist_name'):
                        track_dict['artist_name'] = track_dict['artist']
                    elif track_dict.get('artist_name') and not track_dict.get('artist'):
                        track_dict['artist'] = track_dict['artist_name']
                
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

    def enhance_library_metadata(self, batch_size=50, check_all_files: bool = False) -> None:
        """Retroactive metadata enhancer following a Local-First, highly efficient 5-Step Pipeline.

        Loops through batches until no more tracks require enhancement.  Each batch is
        committed in its own session so memory stays flat even on large libraries.
        """
        from sqlalchemy import or_, and_, func, Integer
        from sqlalchemy.exc import OperationalError
        from database.music_database import get_database, Track, Artist, AudioFingerprint
        from core.utils import PathMapper
        from core.matching_engine.scoring_profile import ExactSyncProfile
        from core.matching_engine.fingerprinting import FingerprintGenerator
        from core.db.echo_sync_track import EchosyncTrack
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
                try:
                    from core.database.repositories.track_repo import TrackRepository
                    tracks_to_process = TrackRepository.get_tracks_for_enhancement(session, batch_size, check_all_files)
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
                    
                    if not local_path_str or local_path_str == ".":
                        logger.warning(f"Skipping track ID {t_data['id']}: No valid local media path resolved.")
                        continue
                        
                    local_path = Path(local_path_str)
                    
                    if not local_path.exists():
                        logger.warning("Enhancer skipping missing file: %s", local_path)
                        t_data['musicbrainz_id'] = "NOT_FOUND"
                        t_data['metadata_status']['enhancement_attempts'] = t_data['metadata_status'].get('enhancement_attempts', 0) + 1
                        results_to_commit.append(t_data)
                        continue

                    # Step 1: Read Local Tags
                    try:
                        file_tags = echosync_core.extract_metadata(str(local_path))
                    except Exception as e:
                        logger.warning("Failed to read tags from %s: %s", local_path.name, e)
                        file_tags = {}

                    tag_mbid = file_tags.get("mbid") or file_tags.get("musicbrainz_id") or file_tags.get("recording_id")
                    
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

                    if track.media_files:
                        media_ids = [m.media_id for m in track.media_files if m.media_id]
                        existing_fps = {
                            fp.media_id: fp 
                            for fp in session.query(AudioFingerprint).filter(AudioFingerprint.media_id.in_(media_ids)).all()
                        } if media_ids else {}

                        if res.get('new_chromaprint_generated', False) and res.get('chromaprint'):
                            for media in track.media_files:
                                if media.media_id not in existing_fps:
                                    track_fp = AudioFingerprint(
                                        media_id=media.media_id,
                                        chromaprint=res['chromaprint'],
                                        acoustid_id=res.get('acoustid_id'),
                                    )
                                    session.add(track_fp)
                                    existing_fps[media.media_id] = track_fp
                                elif res.get('acoustid_id') and not existing_fps[media.media_id].acoustid_id:
                                    existing_fps[media.media_id].acoustid_id = res['acoustid_id']
                        elif res.get('has_fp_record') and res.get('acoustid_id'):
                            for media in track.media_files:
                                if media.media_id in existing_fps and not existing_fps[media.media_id].acoustid_id:
                                    existing_fps[media.media_id].acoustid_id = res['acoustid_id']

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
