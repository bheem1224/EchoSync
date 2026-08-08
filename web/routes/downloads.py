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
    if status.startswith("failed"):
        return "FAILED"
    return (raw_status or "UNKNOWN").upper()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/queue", response_model=QueueResponse)
def get_queue():
    """Return all downloads in the queue with their current status."""
    try:
        with get_working_database().session_scope() as session:
            downloads = session.query(DownloadQueue).all()
            
            queue_items = []
            for download in downloads:
                # Deserialize the EchosyncTrack from JSON
                track_data = download.echo_sync_track
                
                queue_items.append({
                    "id": download.id,
                    "title": track_data.get("title", "Unknown"),
                    "artist": track_data.get("artist", "Unknown"),
                    "album": track_data.get("album_title", ""),
                    "status": _to_ui_status(download.status),
                    "provider_id": download.provider_id,
                    "retry_count": download.retry_count,
                    "current_speed": track_data.get("current_speed", 0.0),
                    "progress_percent": track_data.get("progress_percent", 0.0),
                    "created_at": download.created_at.isoformat() if download.created_at else None,
                    "updated_at": download.updated_at.isoformat() if download.updated_at else None,
                })
            
            return {"total": len(queue_items), "items": queue_items}
    except Exception as e:
        logger.error(f"Error fetching download queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run")
def run_downloads():
    """Trigger the download manager to process queued downloads immediately."""
    try:
        # Check if download_manager job is already running
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


@router.delete("/{download_id}")
def delete_download(download_id: int):
    """Remove a specific download from the queue."""
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


@router.delete("/queue")
def clear_queue():
    """Clear all downloads from the queue."""
    try:
        with get_working_database().session_scope() as session:
            count = session.query(DownloadQueue).delete()
            session.commit()
            
            logger.info(f"Cleared {count} downloads from queue")
            return {"success": True, "message": f"Cleared {count} downloads", "count": count}
    except Exception as e:
        logger.error(f"Error clearing download queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{download_id}/search")
def search_download(download_id: int):
    """Trigger search and download for a specific queue item."""
    try:
        with get_working_database().session_scope() as session:
            download = session.query(DownloadQueue).filter(DownloadQueue.id == download_id).first()
            
            if not download:
                raise HTTPException(status_code=404, detail="DownloadQueue not found")
            
            # Mark as queued (in case it's in failed state) and trigger processing
            download.status = "queued"
            download.updated_at = utc_now()
            session.commit()
        
        # Trigger the download manager to process immediately
        dm = get_download_manager()
        dm.process_downloads_now()
        
        logger.info(f"Triggered search for download {download_id}")
        return {"success": True, "message": f"Search triggered for download {download_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering search for download {download_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/batch")
def delete_batch(payload: BatchDeleteRequest):
    """Delete multiple downloads by IDs."""
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
