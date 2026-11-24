import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.task_manager.task_queue import list_jobs as jq_list_jobs
from core.tiered_logger import get_logger
from database.working_database import DownloadQueue, DownloadStatus, get_working_database
from services.download_manager import get_download_manager
from time_utils import utc_now

logger = get_logger("downloads_route")
router = APIRouter(prefix="/api/v1/system/downloads", tags=["Downloads"])
core_router = APIRouter(prefix="/api/v1/core/downloads", tags=["Downloads"])

_ACTIVE_QUEUE_STATUSES = [
    DownloadStatus.QUEUED.value,
    DownloadStatus.SEARCHING.value,
    DownloadStatus.DOWNLOADING.value,
    DownloadStatus.VERIFYING.value,
    DownloadStatus.RETRYING.value,
    DownloadStatus.PENDING_BLOCKED.value,
    "PAUSED",
    "IN_PROGRESS",
]

_HISTORY_QUEUE_STATUSES = [
    DownloadStatus.COMPLETED.value,
    DownloadStatus.FAILED.value,
    DownloadStatus.CANCELLED.value,
    "FAILED_NO_RESULTS",
    "FAILED_NO_MATCH",
    "FAILED_START_DOWNLOAD",
    "FAILED_ERROR",
    "FAILED_NO_USERNAME",
    "FAILED_NO_FILENAME",
    "FAILED_TERMINAL",
    "FAILED_MAX_RETRIES",
    "NOT_FOUND",
]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class QueueItem(BaseModel):
    id: int
    title: str
    artist: str
    album: str
    status: str
    provider_id: str | None = None
    retry_count: int
    current_speed: float
    progress_percent: float
    cancellation_reason: str | None = None
    error_reason: str | None = None
    diagnostics: dict | None = None
    created_at: str | None = None
    updated_at: str | None = None


class QueueResponse(BaseModel):
    total: int
    items: list[QueueItem]


class BatchDeleteRequest(BaseModel):
    ids: list[int]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_ui_status(raw_status: str) -> str:
    status = (raw_status or "").lower()
    if status == "queued":
        return "QUEUED"
    if status == "searching":
        return "SEARCHING"
    if status in {"downloading", "in_progress"}:
        return "DOWNLOADING"
    if status == "verifying":
        return "VERIFYING"
    if status == "retrying":
        return "RETRYING"
    if status in {"completed", "complete", "verified"}:
        return "COMPLETED"
    if status in {"failed_no_results", "not_found"}:
        return "NOT_FOUND"
    if status == "paused":
        return "PAUSED"
    if status == "pending_blocked":
        return "PENDING_BLOCKED"
    if status in {"cancelled", "canceled"}:
        return "CANCELLED"
    if status.startswith("failed"):
        return "FAILED"
    return (raw_status or "UNKNOWN").upper()


def _cancel_remote_transfers(items: list[DownloadQueue]) -> None:
    """Best-effort cancellation of active remote provider transfers for deleted/cancelled items."""
    targets = []
    for item in items:
        provider_ref = getattr(item, "provider_id", None)
        active_cand = getattr(item, "active_candidate_id", None)
        cancel_id = (
            provider_ref
            if (provider_ref and "|" in str(provider_ref))
            else (active_cand or provider_ref)
        )
        if cancel_id:
            targets.append(cancel_id)

    if not targets:
        return

    dm = get_download_manager()
    providers = dm._get_active_download_providers()
    for cancel_id in targets:
        for p in providers:
            try:
                if hasattr(p, "cancel_download"):
                    p.cancel_download(cancel_id)
                elif hasattr(p, "_async_cancel_download"):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(p._async_cancel_download(cancel_id))
                    except RuntimeError:
                        asyncio.run(p._async_cancel_download(cancel_id))
            except Exception as ce:
                logger.debug(f"Failed to cancel remote transfer {cancel_id}: {ce}")


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
        "error_reason": getattr(download, "error_reason", None),
        "diagnostics": track_data.get("_diagnostics"),
        "created_at": download.created_at.isoformat() if download.created_at else None,
        "updated_at": download.updated_at.isoformat() if download.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _get_queue_impl(status: str | None = None):
    try:
        with get_working_database().session_scope() as session:
            query = session.query(DownloadQueue)
            if status:
                clean_status = status.strip().lower()
                if clean_status == "active":
                    query = query.filter(DownloadQueue.status.in_(_ACTIVE_QUEUE_STATUSES))
                elif clean_status == "history":
                    query = query.filter(DownloadQueue.status.in_(_HISTORY_QUEUE_STATUSES))
                else:
                    query = query.filter(DownloadQueue.status == clean_status.upper())
            downloads = query.order_by(DownloadQueue.created_at.desc()).all()
            queue_items = [_format_item(d) for d in downloads]
            return {"total": len(queue_items), "items": queue_items}
    except Exception as e:
        logger.error(f"Error fetching download queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_active_impl():
    try:
        with get_working_database().session_scope() as session:
            downloads = (
                session.query(DownloadQueue)
                .filter(DownloadQueue.status.in_(_ACTIVE_QUEUE_STATUSES))
                .order_by(DownloadQueue.created_at.asc())
                .all()
            )
            queue_items = [_format_item(d) for d in downloads]
            return {"total": len(queue_items), "items": queue_items}
    except Exception as e:
        logger.error(f"Error fetching active downloads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_history_impl():
    try:
        with get_working_database().session_scope() as session:
            downloads = (
                session.query(DownloadQueue)
                .filter(DownloadQueue.status.in_(_HISTORY_QUEUE_STATUSES))
                .order_by(DownloadQueue.updated_at.desc())
                .limit(100)
                .all()
            )
            queue_items = [_format_item(d) for d in downloads]
            return {"total": len(queue_items), "items": queue_items}
    except Exception as e:
        logger.error(f"Error fetching download history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _run_downloads_impl():
    try:
        jobs = jq_list_jobs()
        download_job = next(
            (j for j in jobs if j.get("name") == "download_manager"), None
        )

        if download_job and download_job.get("running"):
            raise HTTPException(
                status_code=409,
                detail="A download operation is in progress. Please wait for it to complete.",
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
            download = (
                session.query(DownloadQueue)
                .filter(DownloadQueue.id == download_id)
                .first()
            )
            if not download:
                raise HTTPException(status_code=404, detail="DownloadQueue not found")

            if download.status == DownloadStatus.DOWNLOADING.value:
                _cancel_remote_transfers([download])

            session.delete(download)
            logger.info(f"Deleted download {download_id} from queue")
            return {"success": True, "message": f"DownloadQueue {download_id} removed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting download {download_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _clear_queue_impl(
    scope: str | None = None, status: str | None = None, clear_all: bool | None = True
):
    try:
        with get_working_database().session_scope() as session:
            query = session.query(DownloadQueue)
            if status:
                clean_status = status.strip().lower()
                if clean_status == "active":
                    query = query.filter(DownloadQueue.status.in_(_ACTIVE_QUEUE_STATUSES))
                elif clean_status == "history":
                    query = query.filter(DownloadQueue.status.in_(_HISTORY_QUEUE_STATUSES))
                else:
                    query = query.filter(DownloadQueue.status == clean_status.upper())
            elif scope == "failed":
                query = query.filter(DownloadQueue.status.ilike("failed%"))
            elif scope == "active":
                query = query.filter(DownloadQueue.status.in_(_ACTIVE_QUEUE_STATUSES))

            active_downloads = query.filter(
                DownloadQueue.status == DownloadStatus.DOWNLOADING.value
            ).all()
            if active_downloads:
                _cancel_remote_transfers(active_downloads)

            count = query.delete(synchronize_session=False)
            logger.info(
                f"Cleared {count} downloads from queue (scope={scope}, status={status})"
            )
            return {
                "success": True,
                "message": f"Cleared {count} downloads",
                "count": count,
            }
    except Exception as e:
        logger.error(f"Error clearing download queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _requeue_download_impl(download_id: int):
    try:
        with get_working_database().session_scope() as session:
            download = (
                session.query(DownloadQueue)
                .filter(DownloadQueue.id == download_id)
                .first()
            )
            if not download:
                raise HTTPException(status_code=404, detail="Download not found")

            download.status = DownloadStatus.QUEUED.value
            download.error_reason = None
            download.updated_at = utc_now()

        # Passive return: Do NOT call process_downloads_now or process_single_download
        logger.info(f"Passively re-queued download {download_id}")
        return {"success": True, "message": f"Download {download_id} re-queued"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-queueing download {download_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _pause_download_impl(download_id: int):
    try:
        with get_working_database().session_scope() as session:
            download = (
                session.query(DownloadQueue)
                .filter(DownloadQueue.id == download_id)
                .first()
            )
            if not download:
                raise HTTPException(status_code=404, detail="DownloadQueue not found")

            download.status = "PAUSED"
            download.updated_at = utc_now()
            return {"success": True, "message": f"Download {download_id} paused"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing download {download_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _cancel_download_impl(download_id: int):
    try:
        with get_working_database().session_scope() as session:
            download = (
                session.query(DownloadQueue)
                .filter(DownloadQueue.id == download_id)
                .first()
            )
            if not download:
                raise HTTPException(status_code=404, detail="DownloadQueue not found")

            if download.status == DownloadStatus.DOWNLOADING.value:
                _cancel_remote_transfers([download])

            download.status = DownloadStatus.CANCELLED.value
            download.updated_at = utc_now()
            return {"success": True, "message": f"Download {download_id} cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling download {download_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _requeue_all_failed_impl():
    try:
        with get_working_database().session_scope() as session:
            failed_items = (
                session.query(DownloadQueue)
                .filter(DownloadQueue.status.ilike("failed%"))
                .all()
            )
            count = len(failed_items)
            for item in failed_items:
                item.status = DownloadStatus.QUEUED.value
                item.retry_count = (item.retry_count or 0) + 1
                item.error_reason = None
                item.updated_at = utc_now()
            logger.info(f"Re-queued {count} failed downloads")
            return {
                "success": True,
                "message": f"Re-queued {count} failed downloads",
                "count": count,
            }
    except Exception as e:
        logger.error(f"Error re-queueing failed downloads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _delete_all_failed_impl():
    try:
        with get_working_database().session_scope() as session:
            count = (
                session.query(DownloadQueue)
                .filter(DownloadQueue.status.ilike("failed%"))
                .delete(synchronize_session=False)
            )
            session.commit()
            logger.info(f"Cleared {count} failed downloads from queue")
            return {
                "success": True,
                "message": f"Cleared {count} failed downloads",
                "count": count,
            }
    except Exception as e:
        logger.error(f"Error clearing failed downloads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _start_download_now_impl(download_id: int):
    try:
        with get_working_database().session_scope() as session:
            download = (
                session.query(DownloadQueue)
                .filter(DownloadQueue.id == download_id)
                .first()
            )
            if not download:
                raise HTTPException(status_code=404, detail="DownloadQueue not found")

            download.status = DownloadStatus.QUEUED.value
            download.retry_count = (download.retry_count or 0) + 1
            download.updated_at = utc_now()
            session.commit()

        dm = get_download_manager()
        dm.process_single_download(download_id)

        logger.info(f"Immediately triggered download {download_id}")
        return {"success": True, "message": f"Download {download_id} started"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting download {download_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _delete_batch_impl(payload: BatchDeleteRequest):
    try:
        ids = payload.ids
        if not ids:
            raise HTTPException(status_code=400, detail="No IDs provided")
        with get_working_database().session_scope() as session:
            active_downloads = (
                session.query(DownloadQueue)
                .filter(
                    DownloadQueue.id.in_(ids),
                    DownloadQueue.status == DownloadStatus.DOWNLOADING.value,
                )
                .all()
            )
            if active_downloads:
                _cancel_remote_transfers(active_downloads)

            count = (
                session.query(DownloadQueue)
                .filter(DownloadQueue.id.in_(ids))
                .delete(synchronize_session=False)
            )
            session.commit()
            logger.info(f"Deleted {count} downloads from queue (batch)")
            return {
                "success": True,
                "message": f"Deleted {count} downloads",
                "count": count,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch deleting downloads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Route Bindings
# ---------------------------------------------------------------------------

for r in (router, core_router):
    r.add_api_route(
        "/queue", _get_queue_impl, methods=["GET"], response_model=QueueResponse
    )
    r.add_api_route(
        "/active", _get_active_impl, methods=["GET"], response_model=QueueResponse
    )
    r.add_api_route(
        "/history", _get_history_impl, methods=["GET"], response_model=QueueResponse
    )
    r.add_api_route("/run", _run_downloads_impl, methods=["POST"])
    r.add_api_route("/requeue-all-failed", _requeue_all_failed_impl, methods=["POST"])
    r.add_api_route("/failed", _delete_all_failed_impl, methods=["DELETE"])
    r.add_api_route("/queue", _clear_queue_impl, methods=["DELETE"])
    r.add_api_route("/batch", _delete_batch_impl, methods=["DELETE"])
    r.add_api_route(
        "/{download_id}/start-now", _start_download_now_impl, methods=["POST"]
    )
    r.add_api_route("/{download_id}/requeue", _requeue_download_impl, methods=["POST"])
    r.add_api_route("/{download_id}/retry", _requeue_download_impl, methods=["POST"])
    r.add_api_route("/{download_id}/search", _start_download_now_impl, methods=["POST"])
    r.add_api_route("/{download_id}/pause", _pause_download_impl, methods=["POST"])
    r.add_api_route("/{download_id}/cancel", _cancel_download_impl, methods=["POST"])
    r.add_api_route("/{download_id}", _delete_download_impl, methods=["DELETE"])
