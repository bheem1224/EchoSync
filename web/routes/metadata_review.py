"""Metadata review queue endpoints."""

from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from flask import Blueprint, jsonify, request

from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.tiered_logger import get_logger
from database import LibraryManager, get_database
from database.working_database import ReviewTask, get_working_database
from services.metadata_enhancer import get_metadata_enhancer

logger = get_logger("metadata_review_route")
bp = Blueprint("metadata_review", __name__, url_prefix="/api")


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


def _build_track_from_metadata(file_path: Path, metadata: Dict[str, Any]):
    title = metadata.get("title") or file_path.stem
    artist = metadata.get("artist") or "Unknown Artist"
    album = metadata.get("album") or ""

    source = metadata.get("source") or "manual_review"
    provider_id = metadata.get("provider_item_id") or metadata.get("rating_key") or metadata.get("plex_rating_key")

    release_year = _coerce_int(metadata.get("year"))
    if release_year is None and metadata.get("date"):
        date_value = str(metadata.get("date"))
        if len(date_value) >= 4 and date_value[:4].isdigit():
            release_year = int(date_value[:4])

    track = SoulSyncTrack(
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
        bitrate=_coerce_int(metadata.get("bitrate") or metadata.get("bitrate_kbps")),
        file_format=file_path.suffix.lower().lstrip("."),
        file_path=str(file_path),
        identifiers={source: str(provider_id)} if provider_id else {},
    )
    return track


def _import_single_file(file_path: Path, metadata: Dict[str, Any]) -> int:
    db = get_database()
    manager = LibraryManager(db.session_factory)
    track = _build_track_from_metadata(file_path, metadata)
    return manager.bulk_import([track], total_count=1)


@bp.get("/review-queue")
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
                serialized_tasks.append(
                    {
                        "id": task.id,
                        "file_path": task.file_path,
                        "detected_metadata": detected_metadata,
                        "confidence_score": task.confidence_score,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                    }
                )
            return jsonify(
                {
                    "tasks": serialized_tasks
                }
            ), 200
    except Exception as e:
        logger.error(f"Failed to fetch review queue: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch review queue"}), 500


@bp.put("/review-queue/<int:task_id>")
def update_review_queue_item(task_id: int):
    """Update detected metadata JSON for a review task."""
    payload = request.get_json(silent=True)
    metadata = _extract_payload_metadata(payload)

    if not isinstance(metadata, dict):
        return jsonify({"error": "Invalid metadata payload"}), 400

    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                return jsonify({"error": "Task not found"}), 404

            task.detected_metadata = metadata
            return jsonify({"success": True, "id": task.id}), 200
    except Exception as e:
        logger.error(f"Failed to update review task {task_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to update review task"}), 500


@bp.post("/review-queue/<int:task_id>/approve")
def approve_review_queue_item(task_id: int):
    """Approve a review task: write tags, import file, mark approved."""
    payload = request.get_json(silent=True)
    final_metadata = _extract_payload_metadata(payload)

    if not isinstance(final_metadata, dict):
        return jsonify({"error": "Invalid metadata payload"}), 400

    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                return jsonify({"error": "Task not found"}), 404

            file_path = Path(task.file_path)
            if not file_path.exists() or not file_path.is_file():
                return jsonify({"error": "File does not exist"}), 404

            enhancer = get_metadata_enhancer()
            enhancer.tag_file(file_path, final_metadata)

            imported_count = _import_single_file(file_path, final_metadata)

            task.detected_metadata = final_metadata
            task.status = "approved"

            return jsonify(
                {
                    "success": True,
                    "id": task.id,
                    "status": task.status,
                    "imported_count": imported_count,
                }
            ), 200
    except Exception as e:
        logger.error(f"Failed to approve review task {task_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to approve review task"}), 500
