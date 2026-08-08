from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from core.db.echo_sync_track import EchosyncTrack
from core.enums import Capability
from core.nexus_framework.plugin_loader import get_plugin_by_capability
from core.nexus_framework import plugin_loader
from core.matching_engine.track_parser import TrackParser
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.settings import config_manager
from core.tiered_logger import get_logger
from database import get_database
from database.working_database import ReviewTask, get_working_database
from services.metadata_enhancer import get_metadata_enhancer, MetadataEnhancerService
from web.auth import require_auth
from core.db.schemas import QueueListResponse, SuccessResponse

logger = get_logger("metadata_review_route")
router = APIRouter(prefix="/api/v1/core/metadata_review", tags=["Metadata Review"])

class UpdateReviewQueueRequest(BaseModel):
    metadata: Optional[Dict[str, Any]] = None
    track_data: Optional[Dict[str, Any]] = None

class ApproveReviewQueueRequest(BaseModel):
    metadata: Optional[Dict[str, Any]] = None
    detected_metadata: Optional[Dict[str, Any]] = None

class MusicBrainzLookupRequest(BaseModel):
    metadata: Optional[Dict[str, Any]] = None

def _get_media_file_path(media_id: str) -> Optional[str]:
    if not media_id:
        return None
    if "/" in media_id or "\\" in media_id or media_id.startswith("virtual://"):
        return media_id
    from database.music_database import LocalMedia
    db = get_database()
    try:
        with db.session_scope() as session:
            media = session.query(LocalMedia).filter(LocalMedia.media_id == media_id).first()
            return media.file_path if media else None
    except Exception as exc:
        logger.error(f"Failed to lookup media path for {media_id}: {exc}")
    return None

_PARSER_FALLBACK_CONFIDENCE = 0.35
_LOW_CONFIDENCE_THRESHOLD = 0.6


def _coerce_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except Exception:
        return None


def _extract_payload_metadata(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, dict):
        payload_dict = cast(Dict[str, Any], payload)
        metadata = payload_dict.get("metadata")
        detected_metadata = payload_dict.get("detected_metadata")
        if isinstance(metadata, dict):
            return cast(Dict[str, Any], metadata)
        if isinstance(detected_metadata, dict):
            return cast(Dict[str, Any], detected_metadata)
        return payload_dict
    return None


def _normalize_detected_metadata(value: object) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    value_dict = cast(Dict[Any, Any], value)
    return {str(k): v for k, v in value_dict.items()}


def _resolve_task_file(task: ReviewTask) -> Optional[Path]:
    from core.settings import config_manager
    try:
        media_path = task.file_path
        if not media_path:
            return None
        resolved = Path(media_path).expanduser().resolve(strict=True)
    except Exception:
        return None

    if not resolved.exists() or not resolved.is_file():
        return None

    # Jail / LFI protection
    allowed_dirs = []
    _lib = config_manager.get('storage.library_dir') or config_manager.get('library_dir')
    _dl = config_manager.get('storage.download_dir') or config_manager.get('download_dir')
    if _lib:
        allowed_dirs.append(Path(_lib).resolve())
    if _dl:
        allowed_dirs.append(Path(_dl).resolve())

    is_safe = False
    for allowed in allowed_dirs:
        try:
            if resolved.is_relative_to(allowed):
                is_safe = True
                break
        except Exception:
            pass

    if not is_safe:
        return None

    return resolved


def _read_current_metadata(task: ReviewTask) -> Dict[str, Any]:
    resolved_file = _resolve_task_file(task)
    if not resolved_file:
        return {}

    try:
        import echosync_core
        metadata = echosync_core.extract_metadata(str(resolved_file))
             
        # Remove raw cover data from the general metadata dict to keep JSON response light
        clean_metadata = {str(key): value for key, value in metadata.items() if not str(key).startswith("_cover_")}
        # Add a flag if cover is present
        if "_cover_data" in metadata:
            clean_metadata["_has_embedded_cover"] = True
            
        return clean_metadata
    except Exception as exc:
        media_path = task.file_path
        logger.debug(f"Failed to read current metadata for {media_path}: {exc}")
    return {}


def _serialize_task(
    task: ReviewTask,
    detected_metadata: Optional[Dict[str, Any]] = None,
    current_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    track_data = task.track_data or {}
    detected = detected_metadata if detected_metadata is not None else {
        "title": track_data.get("title") or track_data.get("raw_title"),
        "artist": track_data.get("artist"),
        "album": track_data.get("album_title") or track_data.get("album"),
        "year": track_data.get("release_year") or track_data.get("year"),
        "track_number": track_data.get("track_number"),
        "disc_number": track_data.get("disc_number"),
        "musicbrainz_id": track_data.get("mbid") or track_data.get("musicbrainz_id"),
        "isrc": track_data.get("isrc"),
        "acoustid_id": track_data.get("acoustid") or track_data.get("acoustid_id"),
        "mb_release_id": track_data.get("mb_release_id"),
        "fingerprint": track_data.get("fingerprint"),
    }
    return {
        "id": task.id,
        "file_path": task.file_path,
        "media_id": task.file_path,
        "detected_metadata": detected,
        "current_metadata": current_metadata if current_metadata is not None else _read_current_metadata(task),
        "confidence_score": task.confidence_score,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }



def _is_missing_or_low_confidence(metadata: Optional[Dict[str, Any]], confidence_score: float) -> bool:
    if not metadata:
        return True
    if confidence_score < _LOW_CONFIDENCE_THRESHOLD:
        return True
    if not str(metadata.get("artist") or "").strip():
        return True
    if not str(metadata.get("title") or "").strip():
        return True
    return False


def _merge_metadata(base: Optional[Dict[str, Any]], update: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base or {})
    for key, value in (update or {}).items():
        if value is not None and value != "":
            merged[str(key)] = value
    return merged


def _musicbrainz_text_search(metadata_provider, track: Any) -> Optional[EchosyncTrack]:
    # Ensure artist and title are available, otherwise return None
    if isinstance(track, dict) or hasattr(track, 'get'):
        artist = track.get('artist_name') or track.get('artist')
        title = track.get('title') or track.get('raw_title')
    else:
        artist = getattr(track, 'artist_name', getattr(track, 'artist', None))
        title = getattr(track, 'title', getattr(track, 'raw_title', None))

    logger.debug(f"[MusicBrainz Search] Starting text search: artist='{artist}', title='{title}'")
    if not artist or not title:
        logger.debug("[MusicBrainz Search] Missing artist or title, search aborted")
        return None

    if hasattr(metadata_provider, "search_metadata"):
        try:
            logger.debug(f"[MusicBrainz Search] Calling search_metadata on provider '{getattr(metadata_provider, 'name', type(metadata_provider).__name__)}' with track={track}")
            # Assume search_metadata can now take EchosyncTrack (per architecture directives)
            enriched_track = metadata_provider.search_metadata(track=track)
            logger.debug(f"[MusicBrainz Search] search_metadata returned: {enriched_track}")
            if isinstance(enriched_track, EchosyncTrack):
                if enriched_track.musicbrainz_id:
                    logger.debug(f"[MusicBrainz Search] Found valid EchosyncTrack with musicbrainz_id: '{enriched_track.musicbrainz_id}'")
                    return enriched_track
                else:
                    logger.debug("[MusicBrainz Search] enriched_track has empty musicbrainz_id")
            else:
                logger.debug(f"[MusicBrainz Search] enriched_track is not EchosyncTrack instance (type: {type(enriched_track).__name__})")
        except Exception as e:
            logger.error("Error calling search_metadata directly with track", exc_info=True)

    logger.debug("[MusicBrainz Search] Returning None (search failed or not implemented)")
    return None

    # Fallback to direct MusicBrainz WS/2 query using provider HTTP client.
    try:
        response = metadata_provider.http.get(
            "https://musicbrainz.org/ws/2/recording",
            params={"fmt": "json", "query": query, "limit": 5},
        )
        if response.status_code != 200:
            return None

        payload = response.json() or {}
        recordings = payload.get("recordings") or []
        if not recordings:
            return None

        recording = recordings[0]
        mbid = recording.get("id")
        if mbid and hasattr(metadata_provider, "get_metadata"):
            metadata = metadata_provider.get_metadata(mbid)
            if isinstance(metadata, dict):
                return metadata

        artist_name = ""
        for credit in recording.get("artist-credit") or []:
            if isinstance(credit, dict):
                artist_name += str(credit.get("name") or "")
                artist_name += str(credit.get("joinphrase") or "")

        return {
            "title": recording.get("title"),
            "artist": artist_name.strip(),
            "recording_id": recording.get("id"),
            "source": "musicbrainz_text_lookup",
        }
    except Exception:
        return None


def _build_track_from_metadata(file_path: Path, metadata: Dict[str, Any]):
    title = metadata.get("title") or file_path.stem
    artist = metadata.get("artist") or "Unknown Artist"
    album = metadata.get("album") or ""

    source = metadata.get("source") or "manual_review"
    provider_id = metadata.get("provider_item_id") or metadata.get("rating_key")

    release_year = _coerce_int(metadata.get("year"))
    if release_year is None and metadata.get("date"):
        date_value = str(metadata.get("date"))
        if len(date_value) >= 4 and date_value[:4].isdigit():
            release_year = int(date_value[:4])

    from core.db.echo_sync_track import EchosyncMedia
    media_item = EchosyncMedia(
        file_path=str(file_path),
        file_format=file_path.suffix.lower().lstrip("."),
        bitrate=_coerce_int(metadata.get("bitrate") or metadata.get("bitrate_kbps")),
    )
    track = EchosyncTrack(
        raw_title=title,
        artist_name=artist,
        album_title=album,
        duration=_coerce_int(metadata.get("duration_ms") or metadata.get("duration")),
        isrc=cast(Optional[str], metadata.get("isrc")),
        musicbrainz_id=cast(Optional[str], metadata.get("recording_id") or metadata.get("musicbrainz_id")),
        mb_release_id=cast(Optional[str], metadata.get("release_id") or metadata.get("musicbrainz_album_id")),
        release_year=release_year,
        track_number=_coerce_int(metadata.get("track_number")),
        disc_number=_coerce_int(metadata.get("disc_number")),
        media=[media_item],
        identifiers={source: str(provider_id)} if provider_id else {},
    )
    return track


def _import_single_file(file_path: Path, metadata: Dict[str, Any]) -> int:
    db = get_database()
    track = _build_track_from_metadata(file_path, metadata)
    from core.database.repositories.track_repo import bulk_upsert_tracks
    with db.session_scope() as session:
        return bulk_upsert_tracks(session, [track])
      
def _normalize_duration_seconds(metadata: Dict[str, Any], file_path: Path) -> Optional[int]:
    duration = _coerce_int(metadata.get("duration"))
    if duration and duration > 0:
        return duration

    duration_ms = _coerce_int(metadata.get("duration_ms"))
    if duration_ms and duration_ms > 0:
        return max(1, int(duration_ms / 1000))

    enhancer = get_metadata_enhancer()
    if hasattr(enhancer, "_get_audio_duration"):
        try:
            detected = enhancer._get_audio_duration(file_path)
            duration_detected = _coerce_int(detected)
            if duration_detected and duration_detected > 0:
                return duration_detected
        except Exception:
            pass

    return None


def _submit_acoustid_contribution_async(fingerprint: str, duration: int, mbid: str) -> None:
    try:
        fingerprint_provider = get_plugin_by_capability(Capability.RESOLVE_FINGERPRINT)
        if not fingerprint_provider or not hasattr(fingerprint_provider, "submit_fingerprint"):
            logger.debug("Skipping AcoustID contribution: no submit-capable fingerprint provider")
            return

        fingerprint_provider.submit_fingerprint(fingerprint=fingerprint, duration=duration, mbid=mbid)
    except Exception as exc:
        logger.debug(f"AcoustID background contribution failed: {exc}")


@router.get("")
def get_review_queue():
    """Return pending metadata review tasks sorted newest-first."""
    db = get_working_database()
    try:
        with db.session_scope() as session:
            tasks = (
                session.query(ReviewTask)
                .filter(ReviewTask.status == "pending")
                .order_by(ReviewTask.created_at.desc())
                .all()
            )
            serialized_tasks: List[Dict[str, Any]] = []
            for task in tasks:
                detected_metadata = _normalize_detected_metadata(getattr(task, "detected_metadata", None))
                current_metadata = _read_current_metadata(task)
                resolved_file = _resolve_task_file(task)

                serialized_tasks.append(
                    _serialize_task(task, detected_metadata=detected_metadata, current_metadata=current_metadata)
                )
            return {"tasks": serialized_tasks}
    except Exception as e:
        logger.error(f"Failed to fetch review queue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch review queue")


@router.patch("/{task_id}/save")
@router.put("/{task_id}")
def update_review_queue_item(task_id: int, payload: UpdateReviewQueueRequest, _=Depends(require_auth)):
    """Update track_data JSON blob or save progress incrementally for a review task."""
    metadata = payload.metadata or payload.track_data or payload.model_dump(exclude_unset=True)
    if not metadata:
        raise HTTPException(status_code=400, detail="Missing JSON payload")
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="Invalid metadata payload")

    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            # Update/Merge into track_data blob incrementally
            if not task.track_data:
                task.track_data = {}
            for k, v in metadata.items():
                task.track_data[k] = v

            # Standardize properties through detected_metadata setter (backward compatibility)
            if any(k in metadata for k in ["title", "artist", "album", "year", "musicbrainz_id"]):
                task.detected_metadata = metadata

            return {"success": True, "id": task.id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update review task")


def _process_approval_background(task_id: int, final_metadata: Dict[str, Any]):
    """Background processor for approval tasks to prevent thread blocking."""
    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                return

            media_path = task.file_path
            if not media_path:
                return
            file_path = Path(media_path)
            if not file_path.exists() or not file_path.is_file():
                return

            enhancer = get_metadata_enhancer()

            # Identify the file first to check AcoustID fingerprint asynchronously if needed
            # even though we are approving, triggering the metadata enhancer tag_file handles the core logic
            enhancer.tag_file(file_path, final_metadata)

            _import_single_file(file_path, final_metadata)

            task.detected_metadata = final_metadata
            task.status = "approved"
    except Exception as e:
        logger.error(f"Background approval task {task_id} failed: {e}", exc_info=True)

@router.post("/{task_id}/approve")
def approve_review_queue_item(task_id: int, payload: ApproveReviewQueueRequest, _=Depends(require_auth)):
    """Approve a review task: write tags, relocate file, import file, mark approved."""
    final_metadata = payload.metadata or payload.detected_metadata or payload.model_dump(exclude_unset=True)

    if not isinstance(final_metadata, dict):
        raise HTTPException(status_code=400, detail="Invalid metadata payload")

    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            if not task.file_path:
                raise HTTPException(status_code=404, detail="File path not found")

            file_path = Path(task.file_path)
            if not file_path.exists() or not file_path.is_file():
                raise HTTPException(status_code=404, detail="File does not exist")

            from core.job_queue import job_queue
            def _background_approval_task():
                try:
                    import shutil
                    from database import _canonicalize_path
                    from database.music_database import LocalMedia
                    from core.db.echo_sync_track import EchosyncTrack

                    # 1. Resolve task details in fresh working DB session
                    working_db = get_working_database()
                    file_path_str = None
                    track_dict = None
                    with working_db.session_scope() as w_session:
                        task_row = w_session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
                        if not task_row:
                            logger.error(f"Task {task_id} not found in working DB")
                            return
                        file_path_str = task_row.file_path
                        track_dict = task_row.track_data or {}
                        if not track_dict and task_row.detected_metadata:
                            track_dict = task_row.detected_metadata

                    if not file_path_str:
                        logger.error(f"Task {task_id} has no file_path")
                        return

                    file_path_obj = Path(file_path_str)
                    if not file_path_obj.exists() or not file_path_obj.is_file():
                        logger.error(f"Physical file does not exist: {file_path_str}")
                        return

                    # Construct EchosyncTrack object from staging track_data
                    staged_track = EchosyncTrack.from_dict(track_dict)

                    # Update staged_track properties with any modifications from final_metadata
                    if final_metadata:
                        if final_metadata.get("title"):
                            staged_track.raw_title = final_metadata["title"]
                            staged_track.title = final_metadata["title"]
                            staged_track.display_title = final_metadata["title"]
                        if final_metadata.get("artist"):
                            staged_track.artist_name = final_metadata["artist"]
                        if final_metadata.get("album"):
                            staged_track.album_title = final_metadata["album"]
                        if final_metadata.get("year"):
                            try:
                                staged_track.release_year = int(final_metadata["year"])
                            except Exception:
                                pass
                        if final_metadata.get("track_number"):
                            try:
                                staged_track.track_number = int(final_metadata["track_number"])
                            except Exception:
                                pass
                        if final_metadata.get("disc_number"):
                            try:
                                staged_track.disc_number = int(final_metadata["disc_number"])
                            except Exception:
                                pass
                        if final_metadata.get("musicbrainz_id"):
                            staged_track.musicbrainz_id = final_metadata["musicbrainz_id"]
                        if final_metadata.get("isrc"):
                            staged_track.isrc = final_metadata["isrc"]
                        if final_metadata.get("duration"):
                            try:
                                staged_track.duration = int(final_metadata["duration"])
                            except Exception:
                                pass

                    # Merge the finalized metadata back to dict for tagging
                    metadata_to_tag = {
                        "title": staged_track.title,
                        "artist": staged_track.artist_name,
                        "album": staged_track.album_title,
                        "year": str(staged_track.release_year) if staged_track.release_year else None,
                        "track_number": str(staged_track.track_number) if staged_track.track_number else None,
                        "disc_number": str(staged_track.disc_number) if staged_track.disc_number else None,
                        "musicbrainz_id": staged_track.musicbrainz_id,
                        "isrc": staged_track.isrc,
                        "acoustid_id": staged_track.acoustid_id,
                        "mb_release_id": staged_track.mb_release_id,
                        "fingerprint": staged_track.fingerprint,
                    }

                    # 2. Tag the physical file
                    enhancer = get_metadata_enhancer()
                    enhancer.tag_file(file_path_obj, metadata_to_tag)

                    # 3. Calculate target relocation path using naming pattern
                    library_dir = config_manager.get('storage.library_dir') or config_manager.get('library_dir') or "./library"
                    pattern = config_manager.get("auto_import.file_organization_pattern") or "{Artist}/{Album}/{Title}{ext}"
                    if "{ext}" not in pattern:
                        pattern += "{ext}"

                    artist_name = staged_track.artist_name or "Unknown Artist"
                    album_title = staged_track.album_title or "Unknown Album"
                    title = staged_track.title or "Unknown Title"
                    ext = file_path_obj.suffix or ".mp3"
                    new_rel = Path(artist_name) / album_title / f"{title}{ext}"
                    destination_path = Path(library_dir).resolve() / new_rel

                    if destination_path.exists() and destination_path != file_path_obj:
                        counter = 1
                        while destination_path.exists():
                            destination_path = destination_path.with_name(f"{title}_{counter}{ext}")
                            counter += 1

                    canonical_target_path = _canonicalize_path(str(destination_path))

                    # 4. Relocate file physically if path changes
                    if destination_path != file_path_obj:
                        destination_path.parent.mkdir(parents=True, exist_ok=True)
                        from core.io_gatekeeper import Gatekeeper
                        Gatekeeper.authorize_and_execute({"operation": "safe_move", "src": str(file_path_obj), "dst": str(destination_path)})
                        logger.info(f"Relocated file: {file_path_obj} -> {destination_path}")

                    # 5. Community Contribution (AcoustID)
                    contribute_metadata_pref = bool(config_manager.get("metadata_enhancement.contribute_metadata", True))
                    auto_submit_enabled = bool(
                        config_manager.get("metadata_enhancement.enable_acoustid_auto_submission", False)
                    )
                    contribute_metadata = contribute_metadata_pref and auto_submit_enabled
                    acoustid_fingerprint = str(staged_track.fingerprint or "").strip()
                    musicbrainz_id = str(staged_track.musicbrainz_id or "").strip()

                    if contribute_metadata and acoustid_fingerprint and musicbrainz_id:
                        duration_seconds = _normalize_duration_seconds(metadata_to_tag, destination_path)
                        if duration_seconds and duration_seconds > 0:
                            _submit_acoustid_contribution_async(
                                fingerprint=acoustid_fingerprint,
                                duration=duration_seconds,
                                mbid=musicbrainz_id
                            )

                    # 6. Create the final LocalMedia and Track rows in music_library.db (atomic import)
                    _import_single_file(destination_path, metadata_to_tag)

                    # 7. Deletion of the ReviewTask from working.db
                    with working_db.session_scope() as w_session:
                        task_row = w_session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
                        if task_row:
                            w_session.delete(task_row)
                            w_session.commit()
                            logger.info(f"Successfully deleted review task {task_id}")

                except Exception as e:
                    logger.error(f"Background approval failed: {e}", exc_info=True)

            # Register and run the task as a one-off background job
            job_name = f"approve_metadata_{task_id}"
            job_queue.register_job(job_name, _background_approval_task, interval_seconds=None)
            job_queue.execute_job_now(job_name)

            return {
                "success": True,
                "id": task.id,
                "status": "approved_queued"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to approve review task")


@router.get("/{task_id}/stream")
def stream_review_queue_item(task_id: int):
    """Stream raw audio file for a review task with Range support."""
    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            file_path = _resolve_task_file(task)
            if not file_path:
                raise HTTPException(status_code=404, detail="File does not exist")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stream review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to stream review file")

    return FileResponse(
        path=str(file_path),
        media_type="audio/mpeg" if file_path.suffix.lower() == ".mp3" else "audio/flac",
        filename=file_path.name
    )


@router.get("/{task_id}/cover")
def get_review_queue_item_cover(task_id: int):
    """Stream embedded cover art for a review task."""
    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            file_path = _resolve_task_file(task)
            if not file_path:
                raise HTTPException(status_code=404, detail="File does not exist")

            from core.file_handling.tagging_io import read_tags
            metadata = read_tags(file_path)
            
            cover_data = metadata.get("_cover_data")
            cover_mime = metadata.get("_cover_mime") or "image/jpeg"
            
            if not cover_data:
                raise HTTPException(status_code=404, detail="No embedded cover found")

            from fastapi.responses import Response
            return Response(content=cover_data, media_type=cover_mime)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch cover for review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch cover")


@router.post("/{task_id}/lookup/acoustid")
def lookup_review_queue_item_acoustid(task_id: int, _=Depends(require_auth)):
    """Run AcoustID fingerprint lookup and update detected metadata.

    Flow
    ----
    1. Generate fingerprint + duration from fpcalc in a single pass.
    2. Persist the raw fingerprint in the task immediately so it is always
       available for later AcoustID / MusicBrainz submission even if the
       lookup API returns no match.
    3. Call AcoustID API.  If a match is found, populate acoustid_id and MBID
       and enrich from MusicBrainz.
    4. If no match exists yet (track not in the AcoustID library), return 200
       with the stored fingerprint + duration so the UI can present the user
       with a "submit to AcoustID" option rather than a hard error.
    """
    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            file_path = _resolve_task_file(task)
            if not file_path:
                raise HTTPException(status_code=404, detail="File does not exist")

            fingerprint_provider = get_plugin_by_capability(Capability.RESOLVE_FINGERPRINT)
            metadata_provider = get_plugin_by_capability(Capability.FETCH_METADATA)
            if not fingerprint_provider:
                raise HTTPException(status_code=503, detail="No fingerprint provider configured")

            # ── Step 1: generate fingerprint + duration in one fpcalc call ──────
            fingerprint, duration = FingerprintGenerator.generate_with_duration(str(file_path))

            if not fingerprint:
                raise HTTPException(status_code=422, detail="Fingerprint generation failed")

            if isinstance(fingerprint, bytes):
                fingerprint = fingerprint.decode("utf-8", errors="ignore")

            # Fall back to audio duration helper if fpcalc didn't report duration (very rare)
            if not duration or duration <= 0:
                enhancer = get_metadata_enhancer()
                if hasattr(enhancer, "_get_audio_duration"):
                    try:
                        duration = enhancer._get_audio_duration(file_path)
                    except Exception:
                        duration = None

            if not duration or int(duration) <= 0:
                raise HTTPException(status_code=422, detail="Audio duration unavailable for lookup")

            duration_int = int(duration)

            from sqlalchemy.orm.attributes import flag_modified
            # ── Step 2: Hydrate track and persist raw fingerprint NOW, before API call ────
            track_obj = EchosyncTrack.from_dict(task.track_data or {})
            track_obj.fingerprint = fingerprint

            task.track_data = track_obj.to_dict()
            flag_modified(task, "track_data")

            # ── Step 3: query AcoustID API ───────────────────────────────────────
            acoustid_id: Optional[str] = None
            mbids: List[str] = []

            if hasattr(fingerprint_provider, "resolve_fingerprint_details"):
                try:
                    details = fingerprint_provider.resolve_fingerprint_details(fingerprint, duration_int)
                    if isinstance(details, dict):
                        acoustid_id = str(details.get("acoustid_id") or "").strip() or None
                        raw_mbids = details.get("mbids") or []
                        if isinstance(raw_mbids, list):
                            mbids = [str(mbid).strip() for mbid in raw_mbids if str(mbid).strip()]
                except Exception as lookup_error:
                    logger.warning(f"AcoustID detail lookup failed for task {task_id}: {lookup_error}")
            else:
                try:
                    mbids = fingerprint_provider.resolve_fingerprint(fingerprint, duration_int) or []
                except Exception as lookup_error:
                    logger.warning(f"AcoustID resolve_fingerprint failed for task {task_id}: {lookup_error}")

            # ── Step 4: no match → return 200 with fingerprint for submission ───
            if not acoustid_id and not mbids:
                logger.info(
                    f"AcoustID scan for task {task_id}: no match in database. "
                    "Fingerprint stored for submission."
                )

                track_obj.identifiers["source"] = "acoustid_no_match"
                task.track_data = track_obj.to_dict()
                flag_modified(task, "track_data")
                return {
                    "success": True,
                    "acoustid_match": False,
                    "acoustid_fingerprint": fingerprint,
                    "acoustid_fingerprint_duration": duration_int,
                    "task": _serialize_task(task),
                }

            # ── Step 5: match found → enrich metadata ────────────────────────────
            if acoustid_id:
                track_obj.acoustid_id = acoustid_id

            track_obj.identifiers["source"] = "acoustid_lookup"

            if mbids:
                track_obj.musicbrainz_id = mbids[0]

            if mbids and metadata_provider and hasattr(metadata_provider, "get_metadata"):
                try:
                    fetched = metadata_provider.get_metadata(mbids[0])
                    if isinstance(fetched, dict):
                        # merge primitive dictionary into the hydrated object manually
                        track_obj.title = fetched.get("title") or track_obj.title
                        track_obj.artist_name = fetched.get("artist") or track_obj.artist_name
                        track_obj.album_title = fetched.get("album") or track_obj.album_title
                        track_obj.isrc = fetched.get("isrc") or track_obj.isrc
                except Exception as lookup_error:
                    logger.warning(f"AcoustID metadata enrichment failed for task {task_id}: {lookup_error}")

            task.track_data = track_obj.to_dict()
            flag_modified(task, "track_data")
            confidence_floor = 0.9 if mbids else 0.6
            task.confidence_score = max(float(task.confidence_score or 0.0), confidence_floor)

            return {
                "success": True,
                "acoustid_match": True,
                "task": _serialize_task(task),
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed acoustid lookup for review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AcoustID lookup failed")


@router.post("/{task_id}/lookup/musicbrainz")
def lookup_review_queue_item_musicbrainz(task_id: int, payload: MusicBrainzLookupRequest, _=Depends(require_auth)):
    """Run text-based MusicBrainz lookup and update detected metadata."""
    payload_data = payload.metadata or payload.model_dump(exclude_unset=True)
    logger.debug(f"[MusicBrainz Route] POST request received for task_id={task_id}, payload={payload_data}")

    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                logger.debug(f"[MusicBrainz Route] Task {task_id} not found in database")
                raise HTTPException(status_code=404, detail="Task not found")

            current = _normalize_detected_metadata(task.detected_metadata) or {}
            artist = str(payload_data.get("artist") or current.get("artist") or "").strip()
            title = str(payload_data.get("title") or current.get("title") or "").strip()
            task_file_path = task.file_path

        logger.debug(f"[MusicBrainz Route] Extracted initial search info: artist='{artist}', title='{title}', file_path='{task_file_path}'")

        if (not artist or not title) and task_file_path:
            mbid = None
            
            # Step A: Try AcoustID
            try:
                fingerprint, duration = FingerprintGenerator.generate_with_duration(str(task_file_path))
                if fingerprint and duration:
                    fingerprint_provider = get_plugin_by_capability(Capability.RESOLVE_FINGERPRINT)
                    if fingerprint_provider:
                        mbids = fingerprint_provider.resolve_fingerprint(fingerprint, int(duration)) or []
                        if mbids:
                            mbid = mbids[0]
            except Exception as e:
                logger.debug(f"[MusicBrainz Route] AcoustID pre-lookup check failed: {e}")
                
            # Step B: If AcoustID fails, invoke the EchoSync.local_metadata plugin
            track_obj = None
            if not mbid:
                local_metadata_plugin = plugin_loader.get_plugin("EchoSync.local_metadata")
                if local_metadata_plugin:
                    track_obj = local_metadata_plugin.get_track_from_file(str(task_file_path))
            
            # Step C: If tags/AcoustID are found, construct/search
            if mbid:
                logger.info(f"[MusicBrainz Route] AcoustID pre-lookup succeeded. MBID: {mbid}")
                metadata_provider = plugin_loader.get_plugin("EchoSync.musicbrainz")
                if metadata_provider:
                    found_track = metadata_provider.get_track(mbid)
                    if found_track:
                        found_track.identifiers["source"] = "acoustid_pre_lookup"
                        from sqlalchemy.orm.attributes import flag_modified
                        with db.session_scope() as session:
                            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
                            task.track_data = found_track.to_dict()
                            flag_modified(task, "track_data")
                            task.confidence_score = max(float(task.confidence_score or 0.0), 0.95)
                            return {
                                "success": True,
                                "task": _serialize_task(task),
                            }
            elif track_obj and track_obj.title and track_obj.artist_name:
                artist = track_obj.artist_name
                title = track_obj.title
                logger.debug(f"[MusicBrainz Route] EchoSync.local_metadata read tags: artist='{artist}', title='{title}'")
            else:
                # Step D: If no tags are found, halt execution
                logger.debug("[MusicBrainz Route] No tags found, halting execution. Returning minimal EchoSyncTrack payload.")
                empty_track = EchosyncTrack(
                    raw_title="Unknown Title",
                    artist_name="Unknown Artist",
                    album_title=""
                )
                from sqlalchemy.orm.attributes import flag_modified
                with db.session_scope() as session:
                    task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
                    task.track_data = empty_track.to_dict()
                    flag_modified(task, "track_data")
                    return {
                        "success": False,
                        "error": "No physical tags found and AcoustID match failed",
                        "task": _serialize_task(task, detected_metadata=empty_track.to_dict()),
                    }

        if not artist or not title:
            raise HTTPException(status_code=400, detail="artist and title are required")

        metadata_provider = plugin_loader.get_plugin("EchoSync.musicbrainz")
        logger.debug(f"[MusicBrainz Route] Resolved metadata provider: {getattr(metadata_provider, 'name', type(metadata_provider).__name__) if metadata_provider else None}")
        if not metadata_provider:
            logger.error("[MusicBrainz Route] No metadata provider configured")
            raise HTTPException(status_code=503, detail="No metadata provider configured")

        from sqlalchemy.orm.attributes import flag_modified
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                logger.debug(f"[MusicBrainz Route] Task {task_id} not found in database in second session check")
                raise HTTPException(status_code=404, detail="Task not found")

            track_obj = EchosyncTrack.from_dict(task.track_data or {})

            # fallback if artist/title wasn't already in track_data but is passed in payload
            if not track_obj.artist_name or track_obj.artist_name == "Unknown Artist":
                track_obj.artist_name = artist
            if not track_obj.title or track_obj.title == "Unknown Title":
                track_obj.title = title
            track_obj.raw_title = track_obj.title

            logger.debug(f"[MusicBrainz Route] Prepared EchosyncTrack for text search: {track_obj.to_dict()}")

            found_track = _musicbrainz_text_search(metadata_provider, track_obj)
            if not found_track:
                logger.debug("[MusicBrainz Route] No MusicBrainz match found")
                raise HTTPException(status_code=404, detail="No MusicBrainz match found")

            logger.debug(f"[MusicBrainz Route] MusicBrainz match found: {found_track.to_dict()}")
            found_track.identifiers["source"] = "musicbrainz_text_lookup"
            task.track_data = found_track.to_dict()
            flag_modified(task, "track_data")
            task.confidence_score = max(float(task.confidence_score or 0.0), 0.85)

            logger.debug(f"[MusicBrainz Route] Successfully updated task {task_id} with MusicBrainz data")
            return {
                "success": True,
                "task": _serialize_task(task),
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed musicbrainz lookup for review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="MusicBrainz lookup failed")
