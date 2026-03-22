"""Metadata API endpoints."""

import mimetypes
from flask import Blueprint, jsonify, request, send_file
from pathlib import Path
from services.metadata_enhancer import get_metadata_enhancer
from database.working_database import get_working_database, ReviewTask
from core.enums import Capability
from core.plugin_loader import get_provider
from core.tiered_logger import get_logger

logger = get_logger("metadata_route")
bp = Blueprint("metadata", __name__, url_prefix="/api/metadata")

def _get_provider(capability: Capability):
    """Get the first available provider with the given capability."""
    from core.plugin_loader import get_provider
    return get_provider(capability)


def _extract_source_metadata(file_path: Path):
    """Extract best-effort source metadata from local file tags/audio headers."""
    metadata = {
        "title": None,
        "artist": None,
        "album": None,
        "duration_seconds": None,
        "bitrate_kbps": None,
        "sample_rate_hz": None,
        "channels": None,
        "file_format": file_path.suffix.lower().lstrip('.'),
    }

    try:
        import mutagen
    except Exception:
        return metadata

    try:
        audio = mutagen.File(str(file_path), easy=True)
        if not audio:
            return metadata

        tags = getattr(audio, "tags", None) or {}
        metadata["title"] = (tags.get("title") or [None])[0]
        metadata["artist"] = (tags.get("artist") or [None])[0]
        metadata["album"] = (tags.get("album") or [None])[0]

        info = getattr(audio, "info", None)
        if info:
            length = getattr(info, "length", None)
            bitrate = getattr(info, "bitrate", None)
            sample_rate = getattr(info, "sample_rate", None)
            channels = getattr(info, "channels", None)
            if length is not None:
                metadata["duration_seconds"] = int(length)
            if bitrate is not None:
                metadata["bitrate_kbps"] = int(bitrate / 1000)
            if sample_rate is not None:
                metadata["sample_rate_hz"] = int(sample_rate)
            if channels is not None:
                metadata["channels"] = int(channels)
    except Exception as e:
        logger.debug(f"Failed to extract source metadata for {file_path}: {e}")

    return metadata

@bp.get("/queue")
def get_queue():
    """Get items in the review queue."""
    try:
        db = get_working_database()
        queue = []
        with db.session_scope() as session:
            # Query pending tasks
            try:
                tasks = session.query(ReviewTask).filter(ReviewTask.status == 'pending').all()
            except Exception as e:
                # If table doesn't exist yet, return empty list instead of 500
                if "no such table" in str(e).lower():
                    logger.info("Review tasks table not found, returning empty queue.")
                    return jsonify({"queue": []}), 200
                raise e

            for task in tasks:
                queue.append({
                    "id": task.id,
                    "file_path": task.file_path,
                    "filename": Path(task.file_path).name,
                    "detected_metadata": task.detected_metadata,
                    "confidence_score": task.confidence_score,
                    "created_at": task.created_at.isoformat() if task.created_at else None
                })
        return jsonify({"queue": queue}), 200
    except Exception as e:
        logger.error(f"Error getting queue: {e}")
        return jsonify({"error": f"Failed to get queue: {str(e)}"}), 500


@bp.get("/queue/<int:task_id>")
def get_queue_item(task_id: int):
    """Get full details for one review queue item, including source metadata."""
    try:
        db = get_working_database()
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task or task.status != 'pending':
                return jsonify({"error": "Task not found"}), 404

            file_path = Path(task.file_path)
            source_metadata = _extract_source_metadata(file_path) if file_path.exists() else None

            item = {
                "id": task.id,
                "file_path": task.file_path,
                "filename": file_path.name,
                "detected_metadata": task.detected_metadata,
                "confidence_score": task.confidence_score,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "source_metadata": source_metadata,
                "file_exists": file_path.exists(),
            }
            return jsonify({"item": item}), 200
    except Exception as e:
        logger.error(f"Error getting queue item {task_id}: {e}")
        return jsonify({"error": f"Failed to get queue item: {str(e)}"}), 500


@bp.get("/queue/<int:task_id>/audio")
def stream_queue_audio(task_id: int):
    """Stream audio file for a review queue item."""
    try:
        db = get_working_database()
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task or task.status != 'pending':
                return jsonify({"error": "Task not found"}), 404
            file_path = Path(task.file_path)

        if not file_path.exists() or not file_path.is_file():
            return jsonify({"error": "File no longer exists"}), 404

        guessed_type, _ = mimetypes.guess_type(str(file_path))
        return send_file(str(file_path), mimetype=guessed_type or "application/octet-stream", as_attachment=False)
    except Exception as e:
        logger.error(f"Error streaming queue audio for task {task_id}: {e}")
        return jsonify({"error": "Failed to stream audio"}), 500

@bp.post("/queue/approve")
def approve_match():
    """Approve a match and process the file."""
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Missing payload"}), 400

        task_id = payload.get("id")
        metadata = payload.get("metadata")

        if not task_id or not metadata:
             return jsonify({"error": "Missing task ID or metadata"}), 400

        db = get_working_database()
        enhancer = get_metadata_enhancer()

        file_path = None

        # Open session just to get task details
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                return jsonify({"error": "Task not found"}), 404
            file_path = Path(task.file_path)

        # Close session before calling enhancer to avoid nested session issues with SQLite

        if not file_path.exists():
            return jsonify({"error": "File no longer exists"}), 404

        # Tag and Move (this will open its own session to finalize)
        try:
            enhancer.approve_match(file_path, metadata)
            # If successful, task is removed by approve_match calling _finalize_review_task internally via _move_file
        except Exception as e:
            logger.error(f"Approve failed: {e}")
            return jsonify({"error": str(e)}), 500

        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Error approving match: {e}")
        return jsonify({"error": str(e)}), 500

@bp.post("/queue/manual-search")
def manual_search():
    """Search for metadata manually."""
    try:
        payload = request.get_json()
        if not payload:
             return jsonify({"error": "Missing payload"}), 400

        query = payload.get("query")

        if not query:
            return jsonify({"error": "Missing query"}), 400

        provider = _get_provider(Capability.FETCH_METADATA)
        if not provider:
            return jsonify({"error": "No metadata provider available"}), 503

        results = provider.search_metadata(query)
        return jsonify({"results": results}), 200
    except Exception as e:
        logger.error(f"Error searching metadata: {e}")
        return jsonify({"error": "Search failed"}), 500

@bp.delete("/queue/ignore")
def ignore_task():
    """Ignore/Remove item from queue."""
    try:
        payload = request.get_json()
        if not payload:
             return jsonify({"error": "Missing payload"}), 400

        task_id = payload.get("id")

        if not task_id:
             return jsonify({"error": "Missing task ID"}), 400

        db = get_working_database()
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if task:
                task.status = 'ignored'
                # Don't delete, just mark ignored so it doesn't show up again
            else:
                 return jsonify({"error": "Task not found"}), 404

        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Error ignoring task: {e}")
        return jsonify({"error": "Failed to ignore task"}), 500
