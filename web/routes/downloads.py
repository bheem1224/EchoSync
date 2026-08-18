from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import json

from time_utils import utc_now
from core.tiered_logger import get_logger
from services.download_manager import get_download_manager
from database.working_database import get_working_database, DownloadQueue
from core.job_queue import list_jobs as jq_list_jobs

logger = get_logger("downloads_route")
router = APIRouter(prefix="/api/v1/system/downloads", tags=["Downloads"])
core_router = APIRouter(prefix="/api/v1/core/downloads", tags=["Downloads"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class QueueItem(BaseModel):
    id: int
    title: str
    artist: str
    album: str
    status: str
    provider_id: Optional[str] = None
    retry_count: int
    current_speed: float
    progress_percent: float
    cancellation_reason: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class QueueResponse(BaseModel):
    total: int
    items: List[QueueItem]

class BatchDeleteRequest(BaseModel):
    ids: List[int]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_ui_status(raw_status: str) -> str:
    status = (raw_status or "").lower()
    if status == "queued":
        return "QUEUED"
    if status == "searching":
        return "SEARCHING"
    if status == "downloading":
        return "DOWNLOADING"
    if status == "completed":
        return "COMPLETED"
    if status in {"failed_no_results", "not_found"}:
        return "NOT_FOUND"
    if status == "paused":
        return "PAUSED"
    if status == "cancelled":
        return "CANCELLED"
    if status.startswith("failed"):
        return "FAILED"
    return (raw_status or "UNKNOWN").upper()


def _format_item(download) -> dict:
    track_data = download.echo_sync_track or {}
    return {
        "id": download.id,
        "title": track_data.get("title", "Unknown"),
        "artist": track_data.get("artist", track_data.get("artist_name", "Unknown")),
        "album": track_data.get("album_title", track_data.get("album", "")),
        "status": _to_ui_status(download.status),
        "provider_id": download.provider_id,
        "retry_count": download.retry_count,
        "current_speed": track_data.get("current_speed", 0.0),
        "progress_percent": track_data.get("progress_percent", 0.0),
        "cancellation_reason": track_data.get("cancellation_reason"),
        "created_at": download.created_at.isoformat() if download.created_at else None,
        "updated_at": download.updated_at.isoformat() if download.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _get_queue_impl():
    try:
        with get_working_database().session_scope() as session:
            downloads = session.query(DownloadQueue).order_by(DownloadQueue.created_at.desc()).all()
            queue_items = [_format_item(d) for d in downloads]
            return {"total": len(queue_items), "items": queue_items}
    except Exception as e:
        logger.error(f"Error fetching download queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_active_impl():
    try:
        with get_working_database().session_scope() as session:
            active_statuses = ["queued", "searching", "downloading", "in_progress", "paused"]
            downloads = session.query(DownloadQueue).filter(DownloadQueue.status.in_(active_statuses)).order_by(DownloadQueue.created_at.asc()).all()
            queue_items = [_format_item(d) for d in downloads]
            return {"total": len(queue_items), "items": queue_items}
    except Exception as e:
        logger.error(f"Error fetching active downloads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_history_impl():
    try:
        with get_working_database().session_scope() as session:
            history_statuses = ["completed", "failed", "failed_no_results", "not_found", "cancelled"]
            downloads = session.query(DownloadQueue).filter(DownloadQueue.status.in_(history_statuses)).order_by(DownloadQueue.updated_at.desc()).limit(100).all()
            queue_items = [_format_item(d) for d in downloads]
            return {"total": len(queue_items), "items": queue_items}
    except Exception as e:
        logger.error(f"Error fetching download history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _run_downloads_impl():
    try:
        jobs = jq_list_jobs()
        download_job = next((j for j in jobs if j.get("name") == "download_manager"), None)
        
        if download_job and download_job.get("running"):
            raise HTTPException(
                status_code=409,
                detail="A download operation is in progress. Please wait for it to complete."
            )
        
        dm = get_download_manager()
        dm.process_downloads_now()
        
        return {"success": True, "message": "DownloadQueue processing triggered"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running download manager: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _delete_download_impl(download_id: int):
    try:
        with get_working_database().session_scope() as session:
            download = session.query(DownloadQueue).filter(DownloadQueue.id == download_id).first()
            if not download:
                raise HTTPException(status_code=404, detail="DownloadQueue not found")
            session.delete(download)
            session.commit()
            logger.info(f"Deleted download {download_id} from queue")
            return {"success": True, "message": f"DownloadQueue {download_id} removed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting download {download_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _clear_queue_impl():
    try:
        with get_working_database().session_scope() as session:
            count = session.query(DownloadQueue).delete()
            session.commit()
            logger.info(f"Cleared {count} downloads from queue")
            return {"success": True, "message": f"Cleared {count} downloads", "count": count}
    except Exception as e:
        logger.error(f"Error clearing download queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _search_or_retry_download_impl(download_id: int):
    try:
        with get_working_database().session_scope() as session:
            download = session.query(DownloadQueue).filter(DownloadQueue.id == download_id).first()
            if not download:
                raise HTTPException(status_code=404, detail="DownloadQueue not found")
            
            download.status = "queued"
            download.retry_count = (download.retry_count or 0) + 1
            download.updated_at = utc_now()
            session.commit()
        
        dm = get_download_manager()
        dm.process_single_download(download_id)
        
        logger.info(f"Triggered search/retry for download {download_id}")
        return {"success": True, "message": f"Search triggered for download {download_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering search for download {download_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _pause_download_impl(download_id: int):
    try:
        with get_working_database().session_scope() as session:
            download = session.query(DownloadQueue).filter(DownloadQueue.id == download_id).first()
            if not download:
                raise HTTPException(status_code=404, detail="DownloadQueue not found")
            
            download.status = "paused"
            download.updated_at = utc_now()
            session.commit()
            return {"success": True, "message": f"Download {download_id} paused"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing download {download_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _cancel_download_impl(download_id: int):
    try:
        with get_working_database().session_scope() as session:
            download = session.query(DownloadQueue).filter(DownloadQueue.id == download_id).first()
            if not download:
                raise HTTPException(status_code=404, detail="DownloadQueue not found")
            
            download.status = "cancelled"
            download.updated_at = utc_now()
            session.commit()
            return {"success": True, "message": f"Download {download_id} cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling download {download_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _delete_batch_impl(payload: BatchDeleteRequest):
    try:
        ids = payload.ids
        if not ids:
            raise HTTPException(status_code=400, detail="No IDs provided")
        with get_working_database().session_scope() as session:
            count = session.query(DownloadQueue).filter(DownloadQueue.id.in_(ids)).delete(synchronize_session=False)
            session.commit()
            logger.info(f"Deleted {count} downloads from queue (batch)")
            return {"success": True, "message": f"Deleted {count} downloads", "count": count}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch deleting downloads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Route Bindings
# ---------------------------------------------------------------------------

for r in (router, core_router):
    r.add_api_route("/queue", _get_queue_impl, methods=["GET"], response_model=QueueResponse)
    r.add_api_route("/active", _get_active_impl, methods=["GET"], response_model=QueueResponse)
    r.add_api_route("/history", _get_history_impl, methods=["GET"], response_model=QueueResponse)
    r.add_api_route("/run", _run_downloads_impl, methods=["POST"])
    r.add_api_route("/{download_id}/retry", _search_or_retry_download_impl, methods=["POST"])
    r.add_api_route("/{download_id}/search", _search_or_retry_download_impl, methods=["POST"])
    r.add_api_route("/{download_id}/pause", _pause_download_impl, methods=["POST"])
    r.add_api_route("/{download_id}/cancel", _cancel_download_impl, methods=["POST"])
    r.add_api_route("/{download_id}", _delete_download_impl, methods=["DELETE"])
    r.add_api_route("/queue", _clear_queue_impl, methods=["DELETE"])
    r.add_api_route("/batch", _delete_batch_impl, methods=["DELETE"])

