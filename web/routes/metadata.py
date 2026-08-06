"""Metadata API endpoints."""

import mimetypes
from flask import Blueprint, jsonify, request, send_file
from pathlib import Path
from services.metadata_enhancer import get_metadata_enhancer
from database.working_database import get_working_database, ReviewTask
from core.enums import Capability
from core.nexus_framework.plugin_loader import get_plugin_by_capability
from core.tiered_logger import get_logger

logger = get_logger("metadata_route")
bp = Blueprint("metadata", __name__, url_prefix="/api/metadata")

def _get_media_file_path(media_id: str) -> str:
    if not media_id:
        return ""
    from database.music_database import get_database, LocalMedia
    db = get_database()
    try:
        with db.session_scope() as session:
            media = session.query(LocalMedia).filter(LocalMedia.media_id == media_id).first()
            return media.file_path if media else ""
    except Exception as exc:
        logger.error(f"Failed to lookup media path for {media_id}: {exc}")
    return ""

def _get_plugin(capability: Capability):
    """Get the first available plugin with the given capability."""
    from core.nexus_framework.plugin_loader import get_plugin_by_capability
    return get_plugin_by_capability(capability)


def _extract_source_metadata(file_path: Path):
    """Extract best-effort source metadata from local file tags/audio headers using echosync_core."""
    import echosync_core
    try:
        meta = echosync_core.extract_metadata(str(file_path))
        dur_ms = meta.get("duration_ms")
        return {
            "title":          meta.get("title"),
            "artist":         meta.get("artist_name") or meta.get("artist"),
            "album":          meta.get("album_title") or meta.get("album"),
            "duration_seconds": (dur_ms // 1000) if dur_ms else None,
            "bitrate_kbps":   meta.get("bitrate"),
            "sample_rate":    meta.get("sample_rate"),
            "codec":          meta.get("codec"),
            "source":         "echosync_core",
        }
    except Exception as e:
        logger.warning(f"Failed to inspect file {file_path}: {e}")
        return {
            "title": None, "artist": None, "album": None,
            "duration_seconds": None, "bitrate_kbps": None,
            "sample_rate_hz": None, "channels": None,
            "file_format": file_path.suffix.lower().lstrip('.'),
        }

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
                media_path = _get_media_file_path(task.media_id)
                queue.append({
                    "id": task.id,
                    "file_path": media_path,
                    "filename": Path(media_path).name if media_path else "",
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

            media_path = _get_media_file_path(task.media_id)
            file_path = Path(media_path) if media_path else Path("")
            source_metadata = _extract_source_metadata(file_path) if file_path and file_path.exists() else None

            item = {
                "id": task.id,
                "file_path": media_path,
                "filename": file_path.name if media_path else "",
                "detected_metadata": task.detected_metadata,
                "confidence_score": task.confidence_score,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "source_metadata": source_metadata,
                "file_exists": file_path.exists() if media_path else False,
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
            media_path = _get_media_file_path(task.media_id)
            if not media_path:
                return jsonify({"error": "Media path not found"}), 404
            file_path = Path(media_path)

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
            media_path = _get_media_file_path(task.media_id)
            if not media_path:
                return jsonify({"error": "Media path not found"}), 404
            file_path = Path(media_path)

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

        provider = _get_plugin(Capability.FETCH_METADATA)
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


@bp.get("/isrc/<string:isrc>")
def lookup_isrc(isrc: str):
    """Resolve track metadata from an ISRC code using a capability-based plugin lookup."""
    from core.enums import Capability
    from core.nexus_framework.plugin_loader import get_plugin_by_capability

    provider = get_plugin_by_capability(Capability.FETCH_BY_ISRC)
    if not provider:
        return jsonify({"error": "No plugin available for ISRC lookups"}), 503

    try:
        from services.isrc_lookup_service import _normalise_isrc
        canonical = _normalise_isrc(isrc)
        if canonical is None:
            return jsonify({"error": f"Invalid ISRC format: {isrc}"}), 400

        track = provider.search_by_isrc(canonical)
        if not track:
            return jsonify({"isrc": canonical, "result": None, "tried": [getattr(provider, "name", repr(provider))]}), 404

        from services.isrc_lookup_service import _track_to_dict
        from core.db.echo_sync_track import EchosyncTrack
        if isinstance(track, EchosyncTrack):
            result = _track_to_dict(track, getattr(provider, "name", "plugin"))
        else:
            result = track

        return jsonify({
            "isrc": canonical,
            "result": result,
            "tried": [getattr(provider, "name", repr(provider))]
        }), 200
    except Exception as exc:
        logger.error("ISRC lookup error via plugin %s: %s", getattr(provider, "name", "plugin"), exc)
        return jsonify({"error": "ISRC lookup execution failed"}), 500


@bp.get("/cover-art")
def get_cover_art():
    """Extract embedded cover art from an audio file.

    Query params:
      - path: absolute path to audio file
    """
    import io
    from flask import make_response

    file_path_str = request.args.get("path")
    if not file_path_str:
        return jsonify({"error": "Missing path"}), 400

    file_path = Path(file_path_str)
    if not file_path.exists() or not file_path.is_file():
        return jsonify({"error": "File not found"}), 404

    try:
        for name in ["cover.jpg", "folder.jpg", "cover.png", "folder.png"]:
            fallback = file_path.parent / name
            if fallback.exists():
                return send_file(str(fallback))
        return jsonify({"error": "No cover art found"}), 404
    except Exception as e:
        logger.error(f"Error extracting cover art for {file_path}: {e}")
        return jsonify({"error": str(e)}), 500
        return jsonify({"error": str(e)}), 500
