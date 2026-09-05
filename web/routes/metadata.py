"""Metadata API endpoints."""

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from core.db.schemas import (
    ApproveMatchRequest,
    IgnoreTaskRequest,
    ManualSearchRequest,
    QueueDetailResponse,
    QueueItemDetailSchema,
    QueueItemSchema,
    QueueListResponse,
    SuccessResponse,
)
from core.enums import Capability
from core.nexus_framework.plugin_loader import get_plugin_by_capability
from core.tiered_logger import get_logger
from database.working_database import ReviewTask, get_working_database
from services.metadata_enhancer import get_metadata_enhancer

logger = get_logger("metadata_route")
router = APIRouter(prefix="/api/v1/core/metadata", tags=["Metadata"])


def _get_media_file_path(media_id: str) -> str:
    if not media_id:
        return ""
    from database.music_database import LocalMedia, get_database

    db = get_database()
    try:
        with db.session_scope() as session:
            media = (
                session.query(LocalMedia)
                .filter(LocalMedia.media_id == media_id)
                .first()
            )
            return media.file_path if media else ""
    except Exception as exc:
        logger.error(f"Failed to lookup media path for {media_id}: {exc}")
    return ""


def _get_plugin(capability: Capability):
    """Get the first available plugin with the given capability."""
    return get_plugin_by_capability(capability)


def _extract_source_metadata(file_path: Path):
    """Extract best-effort source metadata from local file tags/audio headers using echosync_core."""
    import echosync_core

    try:
        meta = echosync_core.extract_metadata(str(file_path))
        dur_ms = meta.get("duration_ms")
        return {
            "title": meta.get("title"),
            "artist": meta.get("artist_name") or meta.get("artist"),
            "album": meta.get("album_title") or meta.get("album"),
            "duration_seconds": (dur_ms // 1000) if dur_ms else None,
            "bitrate_kbps": meta.get("bitrate"),
            "sample_rate": meta.get("sample_rate"),
            "codec": meta.get("codec"),
            "source": "echosync_core",
        }
    except Exception as e:
        logger.warning(f"Failed to inspect file {file_path}: {e}")
        return {
            "title": None,
            "artist": None,
            "album": None,
            "duration_seconds": None,
            "bitrate_kbps": None,
            "sample_rate_hz": None,
            "channels": None,
            "file_format": file_path.suffix.lower().lstrip("."),
        }


@router.get("/queue", response_model=QueueListResponse)
def get_queue():
    """Get items in the review queue."""
    try:
        db = get_working_database()
        queue = []
        with db.session_scope() as session:
            try:
                tasks = (
                    session.query(ReviewTask)
                    .filter(ReviewTask.status == "pending")
                    .all()
                )
            except Exception as e:
                if "no such table" in str(e).lower():
                    logger.info("Review tasks table not found, returning empty queue.")
                    return QueueListResponse(queue=[])
                raise e

            for task in tasks:
                media_path = _get_media_file_path(task.media_id)
                queue.append(
                    QueueItemSchema(
                        id=task.id,
                        file_path=media_path,
                        filename=Path(media_path).name if media_path else "",
                        detected_metadata=task.detected_metadata,
                        confidence_score=task.confidence_score,
                        created_at=task.created_at.isoformat()
                        if task.created_at
                        else None,
                    )
                )
        return QueueListResponse(queue=queue)
    except Exception as e:
        logger.error(f"Error getting queue: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue: {e!s}")


@router.get("/queue/{task_id}", response_model=QueueDetailResponse)
def get_queue_item(task_id: int):
    """Get full details for one review queue item, including source metadata."""
    try:
        db = get_working_database()
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task or task.status != "pending":
                raise HTTPException(status_code=404, detail="Task not found")

            media_path = _get_media_file_path(task.media_id)
            file_path = Path(media_path) if media_path else Path("")
            source_metadata = (
                _extract_source_metadata(file_path)
                if file_path and file_path.exists()
                else None
            )

            item = QueueItemDetailSchema(
                id=task.id,
                file_path=media_path,
                filename=file_path.name if media_path else "",
                detected_metadata=task.detected_metadata,
                confidence_score=task.confidence_score,
                created_at=task.created_at.isoformat() if task.created_at else None,
                source_metadata=source_metadata,
                file_exists=file_path.exists() if media_path else False,
            )
            return QueueDetailResponse(item=item)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting queue item {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue item: {e!s}")


@router.get("/queue/{task_id}/audio")
def stream_queue_audio(task_id: int):
    """Stream audio file for a review queue item."""
    try:
        db = get_working_database()
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task or task.status != "pending":
                raise HTTPException(status_code=404, detail="Task not found")
            media_path = _get_media_file_path(task.media_id)
            if not media_path:
                raise HTTPException(status_code=404, detail="Media path not found")
            file_path = Path(media_path)

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File no longer exists")

        guessed_type, _ = mimetypes.guess_type(str(file_path))
        return FileResponse(
            path=str(file_path), media_type=guessed_type or "application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming queue audio for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to stream audio")


@router.post("/queue/approve", response_model=SuccessResponse)
def approve_match(payload: ApproveMatchRequest):
    """Approve a match and process the file."""
    try:
        db = get_working_database()
        enhancer = get_metadata_enhancer()

        file_path = None

        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == payload.id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            media_path = _get_media_file_path(task.media_id)
            if not media_path:
                raise HTTPException(status_code=404, detail="Media path not found")
            file_path = Path(media_path)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File no longer exists")

        try:
            enhancer.approve_match(file_path, payload.metadata)
        except Exception as e:
            logger.error(f"Approve failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        return SuccessResponse(success=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving match: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/queue/manual-search")
def manual_search(payload: ManualSearchRequest):
    """Search for metadata manually."""
    try:
        provider = _get_plugin(Capability.FETCH_METADATA)
        if not provider:
            raise HTTPException(
                status_code=503, detail="No metadata provider available"
            )

        results = provider.search_metadata(payload.query)
        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching metadata: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.delete("/queue/ignore", response_model=SuccessResponse)
def ignore_task(payload: IgnoreTaskRequest):
    """Ignore/Remove item from queue."""
    try:
        db = get_working_database()
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == payload.id).first()
            if task:
                task.status = "ignored"
            else:
                raise HTTPException(status_code=404, detail="Task not found")

        return SuccessResponse(success=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ignoring task: {e}")
        raise HTTPException(status_code=500, detail="Failed to ignore task")


@router.get("/isrc/{isrc}")
def lookup_isrc(isrc: str):
    """Resolve track metadata from an ISRC code using a capability-based plugin lookup."""
    from core.enums import Capability
    from core.nexus_framework.plugin_loader import get_plugin_by_capability

    provider = get_plugin_by_capability(Capability.FETCH_BY_ISRC)
    if not provider:
        raise HTTPException(
            status_code=503, detail="No plugin available for ISRC lookups"
        )

    try:
        from services.isrc_lookup_service import _normalise_isrc

        canonical = _normalise_isrc(isrc)
        if canonical is None:
            raise HTTPException(status_code=400, detail=f"Invalid ISRC format: {isrc}")

        track = provider.search_by_isrc(canonical)
        if not track:
            raise HTTPException(status_code=404, detail="Not found")

        from core.db.echo_sync_track import EchosyncTrack
        from services.isrc_lookup_service import _track_to_dict

        if isinstance(track, EchosyncTrack):
            result = _track_to_dict(track, getattr(provider, "name", "plugin"))
        else:
            result = track

        return {
            "isrc": canonical,
            "result": result,
            "tried": [getattr(provider, "name", repr(provider))],
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "ISRC lookup error via plugin %s: %s",
            getattr(provider, "name", "plugin"),
            exc,
        )
        raise HTTPException(status_code=500, detail="ISRC lookup execution failed")


@router.get("/cover-art")
def get_cover_art(path: str = Query(..., description="absolute path to audio file")):
    """Extract embedded cover art from an audio file."""
    try:
        from core.path_security import PathTraversalError, resolve_safe_path
        from core.settings import config_manager

        candidate_roots = [
            config_manager.get("storage.library_dir"),
            config_manager.get("library_dir"),
            config_manager.get("download_dir"),
            config_manager.get("storage.download_dir"),
            config_manager.get("data_dir"),
            ".",
        ]
        allowed_roots = [Path(r).resolve() for r in candidate_roots if r]

        try:
            file_path = resolve_safe_path(allowed_roots, path)
        except (PathTraversalError, ValueError):
            raise HTTPException(
                status_code=403, detail="Security violation: Access denied"
            )

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        for name in ["cover.jpg", "folder.jpg", "cover.png", "folder.png"]:
            try:
                fallback = resolve_safe_path(allowed_roots, file_path.parent / name)
                if fallback.exists() and fallback.is_file():
                    return FileResponse(path=str(fallback))
            except (PathTraversalError, ValueError):
                continue

        raise HTTPException(status_code=404, detail="No cover art found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting cover art for {path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to extract cover art")
