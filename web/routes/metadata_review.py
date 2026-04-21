"""Metadata review queue endpoints."""
from web.auth import require_auth


from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, cast

from flask import Blueprint, jsonify, request, send_file

from core.matching_engine.echo_sync_track import EchosyncTrack
from core.enums import Capability
from core.plugin_loader import get_provider
from core.track_parser import TrackParser
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.settings import config_manager
from core.tiered_logger import get_logger
from database import LibraryManager, get_database
from database.working_database import ReviewTask, get_working_database
from services.metadata_enhancer import get_metadata_enhancer

logger = get_logger("metadata_review_route")
bp = Blueprint("metadata_review", __name__, url_prefix="/api")

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
        resolved = Path(task.file_path).expanduser().resolve(strict=True)
    except Exception:
        return None

    if not resolved.exists() or not resolved.is_file():
        return None

    # Jail / LFI protection
    allowed_dirs = [
        config_manager.get_library_dir().resolve(),
        config_manager.get_download_dir().resolve()
    ]

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
        enhancer = get_metadata_enhancer()
        metadata = enhancer.read_tags(resolved_file)
        return {str(key): value for key, value in metadata.items()}
    except Exception as exc:
        logger.debug(f"Failed to read current metadata for {task.file_path}: {exc}")
    return {}


def _serialize_task(
    task: ReviewTask,
    detected_metadata: Optional[Dict[str, Any]] = None,
    current_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized = detected_metadata if detected_metadata is not None else _normalize_detected_metadata(getattr(task, "detected_metadata", None))
    return {
        "id": task.id,
        "file_path": task.file_path,
        "detected_metadata": normalized,
        "current_metadata": current_metadata if current_metadata is not None else _read_current_metadata(task),
        "confidence_score": task.confidence_score,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


def _best_effort_path_parse(file_path: Path) -> Optional[Dict[str, Any]]:
    parser = TrackParser()

    # Prefer concrete filename parse, then progressively richer fallbacks.
    candidates = [
        file_path.name,
        file_path.stem,
        f"{file_path.parent.name} - {file_path.stem}",
    ]

    for candidate in candidates:
        track = parser.parse_filename(candidate)
        if not track:
            continue

        parsed: Dict[str, Any] = {
            "title": track.title,
            "artist": track.artist_name,
            "album": track.album_title or file_path.parent.name,
            "track_number": track.track_number,
            "disc_number": track.disc_number,
            "year": track.release_year,
            "source": "path_parser",
        }
        return {k: v for k, v in parsed.items() if v not in (None, "")}

    return None


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


def _musicbrainz_text_search(metadata_provider, artist: str, title: str) -> Optional[Dict[str, Any]]:
    query = f'artist:"{artist}" AND recording:"{title}"'

    # Preferred provider-native search method if available.
    if hasattr(metadata_provider, "search_metadata"):
        try:
            results = metadata_provider.search_metadata(query, limit=5) or []
        except Exception:
            results = []

        if results:
            top = results[0]
            mbid = top.get("mbid")
            if mbid and hasattr(metadata_provider, "get_metadata"):
                try:
                    metadata = metadata_provider.get_metadata(mbid)
                    if isinstance(metadata, dict):
                        return metadata
                except Exception:
                    pass
            return top if isinstance(top, dict) else None

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
        fingerprint_provider = get_provider(Capability.RESOLVE_FINGERPRINT)
        if not fingerprint_provider or not hasattr(fingerprint_provider, "submit_fingerprint"):
            logger.debug("Skipping AcoustID contribution: no submit-capable fingerprint provider")
            return

        fingerprint_provider.submit_fingerprint(fingerprint=fingerprint, duration=duration, mbid=mbid)
    except Exception as exc:
        logger.debug(f"AcoustID background contribution failed: {exc}")


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
                current_metadata = _read_current_metadata(task)
                resolved_file = _resolve_task_file(task)

                if _is_missing_or_low_confidence(detected_metadata, float(task.confidence_score or 0.0)):
                    parsed_guess = _best_effort_path_parse(resolved_file) if resolved_file else None
                    if parsed_guess:
                        detected_metadata = _merge_metadata(detected_metadata, parsed_guess)
                        task.detected_metadata = detected_metadata
                        if float(task.confidence_score or 0.0) < _PARSER_FALLBACK_CONFIDENCE:
                            task.confidence_score = _PARSER_FALLBACK_CONFIDENCE

                serialized_tasks.append(
                    _serialize_task(task, detected_metadata=detected_metadata, current_metadata=current_metadata)
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
@require_auth
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


def _process_approval_background(task_id: int, final_metadata: Dict[str, Any]):
    """Background processor for approval tasks to prevent thread blocking."""
    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                return

            file_path = Path(task.file_path)
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

@bp.post("/review-queue/<int:task_id>/approve")
@require_auth
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

            from core.job_queue import job_queue
            def _background_approval_task():
                try:
                    # 1. Tag the physical file
                    enhancer = get_metadata_enhancer()
                    enhancer.tag_file(file_path, final_metadata)

                    # 2. Community Contribution (AcoustID)
                    # Safety gate: keep auto-submission OFF unless explicitly enabled.
                    # This remains disabled by default while contribution flow is tested.
                    # Preferences are stored under the 'metadata_enhancement' config key
                    # (set by /api/settings/preferences in system.py).
                    contribute_metadata_pref = bool(config_manager.get("metadata_enhancement.contribute_metadata", True))
                    auto_submit_enabled = bool(
                        config_manager.get("metadata_enhancement.enable_acoustid_auto_submission", False)
                    )
                    contribute_metadata = contribute_metadata_pref and auto_submit_enabled
                    acoustid_fingerprint = str(final_metadata.get("acoustid_fingerprint") or "").strip()
                    musicbrainz_id = str(final_metadata.get("musicbrainz_id") or "").strip()

                    if contribute_metadata and acoustid_fingerprint and musicbrainz_id:
                        duration_seconds = _normalize_duration_seconds(final_metadata, file_path)
                        if duration_seconds and duration_seconds > 0:
                            # We are ALREADY safely inside a background task! 
                            # We can just call this directly without a rogue threading.Thread.
                            _submit_acoustid_contribution_async(
                                fingerprint=acoustid_fingerprint,
                                duration=duration_seconds,
                                mbid=musicbrainz_id
                            )
                        else:
                            logger.debug("Skipping AcoustID contribution: duration unavailable")

                    # 3. Import the file into the database
                    imported_count = _import_single_file(file_path, final_metadata)
                except Exception as e:
                    logger.error(f"Background approval failed: {e}")
                    
            # Register and run the task as a one-off background job
            job_name = f"approve_metadata_{task_id}"
            job_queue.register_job(job_name, _background_approval_task, interval_seconds=None)
            job_queue.execute_job_now(job_name)

            return jsonify(
                {
                    "success": True,
                    "id": task.id,
                    "status": "approved_queued"
                }
            ), 202
    except Exception as e:
        logger.error(f"Failed to approve review task {task_id}: {e}", exc_info=True)


@bp.get("/review-queue/<int:task_id>/stream")
def stream_review_queue_item(task_id: int):
    """Stream raw audio file for a review task with Range support."""
    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                return jsonify({"error": "Task not found"}), 404

            file_path = _resolve_task_file(task)
            if not file_path:
                return jsonify({"error": "File does not exist"}), 404
    except Exception as e:
        logger.error(f"Failed to stream review task {task_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to stream review file"}), 500

    # Use Flask's native send_file with conditional=True to automatically
    # handle 'Accept-Ranges: bytes' and safe streaming without holding locks.
    # Called outside the session_scope so the DB connection is released before
    # the (potentially long-running) streaming response begins.
    from flask import send_file

    return send_file(
        file_path,
        mimetype="audio/mpeg" if file_path.suffix.lower() == ".mp3" else "audio/flac",
        as_attachment=False,
        conditional=True,
        download_name=file_path.name
    )


@bp.post("/review-queue/<int:task_id>/lookup/acoustid")
@require_auth
def lookup_review_queue_item_acoustid(task_id: int):
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
                return jsonify({"error": "Task not found"}), 404

            file_path = _resolve_task_file(task)
            if not file_path:
                return jsonify({"error": "File does not exist"}), 404

            fingerprint_provider = get_provider(Capability.RESOLVE_FINGERPRINT)
            metadata_provider = get_provider(Capability.FETCH_METADATA)
            if not fingerprint_provider:
                return jsonify({"error": "No fingerprint provider configured"}), 503

            # ── Step 1: generate fingerprint + duration in one fpcalc call ──────
            fingerprint, duration = FingerprintGenerator.generate_with_duration(str(file_path))

            if not fingerprint:
                return jsonify({"error": "Fingerprint generation failed"}), 422

            if isinstance(fingerprint, bytes):
                fingerprint = fingerprint.decode("utf-8", errors="ignore")

            # Fall back to mutagen if fpcalc didn't report duration (very rare)
            if not duration or duration <= 0:
                enhancer = get_metadata_enhancer()
                if hasattr(enhancer, "_get_audio_duration"):
                    try:
                        duration = enhancer._get_audio_duration(file_path)
                    except Exception:
                        duration = None

            if not duration or int(duration) <= 0:
                return jsonify({"error": "Audio duration unavailable for lookup"}), 422

            duration_int = int(duration)

            # ── Step 2: persist the raw fingerprint NOW, before any API call ────
            # This ensures it is always available for submission even if the
            # AcoustID lookup returns no match (track not yet in their DB).
            merged = _normalize_detected_metadata(task.detected_metadata) or {}
            merged["acoustid_fingerprint"] = fingerprint
            merged["acoustid_fingerprint_duration"] = duration_int
            task.detected_metadata = merged

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
                merged["source"] = "acoustid_no_match"
                task.detected_metadata = merged
                return jsonify({
                    "success": True,
                    "acoustid_match": False,
                    "acoustid_fingerprint": fingerprint,
                    "acoustid_fingerprint_duration": duration_int,
                    "task": _serialize_task(task, detected_metadata=merged),
                }), 200

            # ── Step 5: match found → enrich metadata ────────────────────────────
            if acoustid_id:
                merged["acoustid_id"] = acoustid_id
            merged["source"] = "acoustid_lookup"

            if mbids:
                merged["musicbrainz_id"] = mbids[0]
                merged["recording_id"] = mbids[0]

            if mbids and metadata_provider and hasattr(metadata_provider, "get_metadata"):
                try:
                    fetched = metadata_provider.get_metadata(mbids[0])
                    if isinstance(fetched, dict):
                        merged = _merge_metadata(merged, fetched)
                except Exception as lookup_error:
                    logger.warning(f"AcoustID metadata enrichment failed for task {task_id}: {lookup_error}")

            task.detected_metadata = merged
            confidence_floor = 0.9 if mbids else 0.6
            task.confidence_score = max(float(task.confidence_score or 0.0), confidence_floor)

            return jsonify({
                "success": True,
                "acoustid_match": True,
                "task": _serialize_task(task, detected_metadata=merged),
            }), 200
    except Exception as e:
        logger.error(f"Failed acoustid lookup for review task {task_id}: {e}", exc_info=True)
        return jsonify({"error": "AcoustID lookup failed"}), 500


@bp.post("/review-queue/<int:task_id>/lookup/musicbrainz")
@require_auth
def lookup_review_queue_item_musicbrainz(task_id: int):
    """Run text-based MusicBrainz lookup and update detected metadata."""
    from flask import request

    payload = request.get_json(silent=True) or {}

    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                return jsonify({"error": "Task not found"}), 404

            current = _normalize_detected_metadata(task.detected_metadata) or {}
            artist = str(payload.get("artist") or current.get("artist") or "").strip()
            title = str(payload.get("title") or current.get("title") or "").strip()
            task_file_path = task.file_path

        if (not artist or not title) and task_file_path:
            guessed = _best_effort_path_parse(Path(task_file_path))
            artist = artist or str((guessed or {}).get("artist") or "").strip()
            title = title or str((guessed or {}).get("title") or "").strip()

        if not artist or not title:
            return jsonify({"error": "artist and title are required"}), 400

        metadata_provider = get_provider(Capability.FETCH_METADATA)
        if not metadata_provider:
            return jsonify({"error": "No metadata provider configured"}), 503

        found = _musicbrainz_text_search(metadata_provider, artist=artist, title=title)
        if not found:
            return jsonify({"error": "No MusicBrainz match found"}), 404

        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                return jsonify({"error": "Task not found"}), 404

            current = _normalize_detected_metadata(task.detected_metadata) or {}
            merged = _merge_metadata(current, found)
            merged["source"] = "musicbrainz_text_lookup"
            task.detected_metadata = merged
            task.confidence_score = max(float(task.confidence_score or 0.0), 0.85)

            return jsonify({
                "success": True,
                "task": _serialize_task(task, detected_metadata=merged),
            }), 200
    except Exception as e:
        logger.error(f"Failed musicbrainz lookup for review task {task_id}: {e}", exc_info=True)
        return jsonify({"error": "MusicBrainz lookup failed"}), 500
