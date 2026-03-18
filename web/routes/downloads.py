from flask import Blueprint, Response, request

from time_utils import utc_now
import json
from core.tiered_logger import get_logger
from services.download_manager import get_download_manager
from database.music_database import get_database, Download
from core.job_queue import list_jobs as jq_list_jobs

logger = get_logger("downloads_route")
bp = Blueprint("downloads", __name__, url_prefix="/api/downloads")


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


@bp.get("/queue")
def get_queue():
    """Return all downloads in the queue with their current status."""
    try:
        with get_database().session_scope() as session:
            downloads = session.query(Download).all()
            
            queue_items = []
            for download in downloads:
                # Deserialize the SoulSyncTrack from JSON
                track_data = download.soul_sync_track
                
                queue_items.append({
                    "id": download.id,
                    "title": track_data.get("title", "Unknown"),
                    "artist": track_data.get("artist_name", "Unknown"),
                    "album": track_data.get("album_name", ""),
                    "status": _to_ui_status(download.status),
                    "provider_id": download.provider_id,
                    "retry_count": download.retry_count,
                    "created_at": download.created_at.isoformat() if download.created_at else None,
                    "updated_at": download.updated_at.isoformat() if download.updated_at else None,
                })
            
            return Response(
                json.dumps({"total": len(queue_items), "items": queue_items}),
                status=200,
                mimetype="application/json"
            )
    except Exception as e:
        logger.error(f"Error fetching download queue: {e}")
        return Response(
            json.dumps({"error": str(e), "total": 0, "items": []}),
            status=500,
            mimetype="application/json"
        )


@bp.post("/run")
def run_downloads():
    """Trigger the download manager to process queued downloads immediately."""
    try:
        # Check if download_manager job is already running
        jobs = jq_list_jobs()
        download_job = next((j for j in jobs if j.get("name") == "download_manager"), None)
        
        if download_job and download_job.get("running"):
            return Response(
                json.dumps({
                    "error": "Download manager is already running",
                    "reason": "A download operation is in progress. Please wait for it to complete.",
                    "job": "download_manager",
                    "started_at": download_job.get("last_started")
                }),
                status=409,
                mimetype="application/json"
            )
        
        dm = get_download_manager()
        dm.ensure_background_task()
        dm.process_downloads_now()
        
        return Response(
            json.dumps({"success": True, "message": "Download processing triggered"}),
            status=200,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error running download manager: {e}")
        return Response(
            json.dumps({"success": False, "error": str(e)}),
            status=500,
            mimetype="application/json"
        )


@bp.delete("/<int:download_id>")
def delete_download(download_id: int):
    """Remove a specific download from the queue."""
    try:
        with get_database().session_scope() as session:
            download = session.query(Download).filter(Download.id == download_id).first()
            
            if not download:
                return Response(
                    json.dumps({"success": False, "error": "Download not found"}),
                    status=404,
                    mimetype="application/json"
                )
            
            session.delete(download)
            session.commit()
            
            logger.info(f"Deleted download {download_id} from queue")
            return Response(
                json.dumps({"success": True, "message": f"Download {download_id} removed"}),
                status=200,
                mimetype="application/json"
            )
    except Exception as e:
        logger.error(f"Error deleting download {download_id}: {e}")
        return Response(
            json.dumps({"success": False, "error": str(e)}),
            status=500,
            mimetype="application/json"
        )


@bp.delete("/queue")
def clear_queue():
    """Clear all downloads from the queue."""
    try:
        with get_database().session_scope() as session:
            count = session.query(Download).delete()
            session.commit()
            
            logger.info(f"Cleared {count} downloads from queue")
            return Response(
                json.dumps({"success": True, "message": f"Cleared {count} downloads", "count": count}),
                status=200,
                mimetype="application/json"
            )
    except Exception as e:
        logger.error(f"Error clearing download queue: {e}")
        return Response(
            json.dumps({"success": False, "error": str(e)}),
            status=500,
            mimetype="application/json"
        )


@bp.post("/<int:download_id>/search")
def search_download(download_id: int):
    """Trigger search and download for a specific queue item."""
    try:
        with get_database().session_scope() as session:
            download = session.query(Download).filter(Download.id == download_id).first()
            
            if not download:
                return Response(
                    json.dumps({"success": False, "error": "Download not found"}),
                    status=404,
                    mimetype="application/json"
                )
            
            # Mark as queued (in case it's in failed state) and trigger processing
            download.status = "queued"
            download.updated_at = utc_now()
            session.commit()
        
        # Trigger the download manager to process immediately
        dm = get_download_manager()
        dm.ensure_background_task()
        dm.process_downloads_now()
        
        logger.info(f"Triggered search for download {download_id}")
        return Response(
            json.dumps({"success": True, "message": f"Search triggered for download {download_id}"}),
            status=200,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error triggering search for download {download_id}: {e}")
        return Response(
            json.dumps({"success": False, "error": str(e)}),
            status=500,
            mimetype="application/json"
        )


@bp.delete("/batch")
def delete_batch():
    """Delete multiple downloads by IDs."""
    try:
        payload = request.get_json(silent=True) or {}
        ids = payload.get("ids", [])
        
        if not ids:
            return Response(
                json.dumps({"success": False, "error": "No IDs provided"}),
                status=400,
                mimetype="application/json"
            )
        
        with get_database().session_scope() as session:
            count = session.query(Download).filter(Download.id.in_(ids)).delete(synchronize_session=False)
            session.commit()
            
            logger.info(f"Deleted {count} downloads from queue (batch)")
            return Response(
                json.dumps({"success": True, "message": f"Deleted {count} downloads", "count": count}),
                status=200,
                mimetype="application/json"
            )
    except Exception as e:
        logger.error(f"Error batch deleting downloads: {e}")
        return Response(
            json.dumps({"success": False, "error": str(e)}),
            status=500,
            mimetype="application/json"
        )
