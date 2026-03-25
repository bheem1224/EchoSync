from flask import Blueprint, jsonify, request
from time_utils import utc_now
from core.tiered_logger import get_logger
from core.settings import config_manager
from services.library_hygiene import DuplicateHygieneService
from services.metadata_enhancer import get_metadata_enhancer
from database.music_database import get_database, Track, Artist
from database.working_database import get_working_database, UserRating as WorkingUserRating, UserTrackState, User
from database.config_database import get_config_database
from core.suggestion_engine.consensus import calculate_consensus
from core.suggestion_engine.deletion import execute_delete_now, execute_upgrade_now
from core.matching_engine.text_utils import generate_deterministic_id
from pathlib import Path
from sqlalchemy import func, case
from datetime import datetime
import base64

logger = get_logger("web.routes.manager")
bp = Blueprint("manager", __name__, url_prefix="/api/manager")


def _normalize_sync_id(sync_id: str) -> str:
    return (sync_id or "").split("?")[0].strip()


def _sync_id_from_track_id(track_id: int) -> str | None:
    db = get_database()
    with db.session_scope() as session:
        row = (
            session.query(Track.title, Artist.name)
            .join(Artist, Track.artist_id == Artist.id)
            .filter(Track.id == track_id)
            .first()
        )
        if not row:
            return None
        encoded = generate_deterministic_id(row.name, row.title)
        return f"ss:track:meta:{encoded}"


def _resolve_track_preview(sync_id: str):
    base_sync_id = _normalize_sync_id(sync_id)
    if not base_sync_id.startswith("ss:track:meta:"):
        return None

    encoded = base_sync_id.split("ss:track:meta:", 1)[1]
    if not encoded:
        return None

    try:
        decoded = base64.b64decode(encoded.encode("ascii")).decode("utf-8")
        artist_name, title = decoded.split("|", 1)
    except Exception:
        return None

    db = get_database()
    with db.session_scope() as session:
        row = (
            session.query(Track.id, Track.title, Artist.name)
            .join(Artist, Track.artist_id == Artist.id)
            .filter(
                func.lower(Artist.name) == artist_name.lower(),
                func.lower(Track.title) == title.lower(),
            )
            .first()
        )
        if not row:
            return None

        return {
            "track_id": row.id,
            "title": row.title,
            "artist": row.name,
        }


def _resolve_working_user_for_trends():
    """Resolve the working DB user for trends filtering.

    Resolution order:
    1) Explicit query params: user_id, then account_id
    2) Active Plex managed account fallback (first active account)
    """
    config_db = get_config_database()
    working_db = get_working_database()

    requested_user_id = request.args.get("user_id", type=int)
    requested_account_id = request.args.get("account_id", type=int)

    resolved_user = None
    resolved_account_id = None

    with working_db.session_scope() as session:
        if requested_user_id:
            resolved_user = session.query(User).filter(User.id == requested_user_id).first()
            if resolved_user:
                session.expunge(resolved_user)
                return resolved_user, None, "user_id"

        if requested_account_id:
            plex_service_id = config_db.get_or_create_service_id("plex")
            account = next(
                (
                    acc for acc in config_db.get_accounts(service_id=plex_service_id)
                    if acc.get("id") == requested_account_id
                ),
                None,
            )
            if account:
                resolved_account_id = account.get("id")
                plex_user_id = str(account.get("user_id") or "").strip()
                if plex_user_id:
                    resolved_user = session.query(User).filter(User.plex_id == plex_user_id).first()
                if not resolved_user:
                    display_name = (account.get("display_name") or account.get("account_name") or "").strip()
                    if display_name:
                        resolved_user = session.query(User).filter(User.username == display_name).first()
                if resolved_user:
                    session.expunge(resolved_user)
                    return resolved_user, resolved_account_id, "account_id"

        plex_service_id = config_db.get_or_create_service_id("plex")
        active_accounts = config_db.get_accounts(service_id=plex_service_id, is_active=True)
        fallback_account = next((acc for acc in active_accounts if acc.get("user_id")), None)
        if fallback_account is None and active_accounts:
            fallback_account = active_accounts[0]

        if fallback_account:
            resolved_account_id = fallback_account.get("id")
            plex_user_id = str(fallback_account.get("user_id") or "").strip()
            if plex_user_id:
                resolved_user = session.query(User).filter(User.plex_id == plex_user_id).first()
            if not resolved_user:
                display_name = (fallback_account.get("display_name") or fallback_account.get("account_name") or "").strip()
                if display_name:
                    resolved_user = session.query(User).filter(User.username == display_name).first()

        # Expunge before the session closes so commit() does not expire the object's
        # attributes and callers can safely access .id / .username after this function returns.
        if resolved_user is not None:
            session.expunge(resolved_user)

    return resolved_user, resolved_account_id, "active_account"

@bp.route("/settings", methods=["GET", "POST"])
def manager_settings():
    """Get or update manager settings."""
    if request.method == "POST":
        payload = request.get_json() or {}
        # Validation could be added here
        try:
            manager_config = config_manager.get('manager', {})
            # Update known keys
            for key in [
                'enabled',
                'delete_threshold',
                'upgrade_threshold',
                'auto_delete',
                'auto_upgrade',
                'upgrade_quality_profile_id',
                'auto_delete_low_quality_duplicates',
                'auto_process_suggestion_engine_ratings',
            ]:
                if key in payload:
                    manager_config[key] = payload[key]

            config_manager.set('manager', manager_config)
            return jsonify({"success": True, "settings": manager_config}), 200
        except Exception as e:
            logger.error(f"Error updating manager settings: {e}")
            return jsonify({"error": str(e)}), 500
    else:
        # GET
        try:
            # Return defaults if not set
            settings = config_manager.get('manager', {
                'enabled': True,
                'delete_threshold': 1,
                'upgrade_threshold': 2,
                'auto_delete': False,
                'auto_upgrade': False,
                'upgrade_quality_profile_id': None,
                'auto_delete_low_quality_duplicates': False,
                'auto_process_suggestion_engine_ratings': True,
            })
            return jsonify({"success": True, "settings": settings}), 200
        except Exception as e:
            logger.error(f"Error getting manager settings: {e}")
            return jsonify({"error": str(e)}), 500


@bp.route("/suggestion-candidates", methods=["GET"])
def get_suggestion_candidates():
    """Get consensus-threshold candidates from working DB using the 10-point lifecycle model."""
    work_db = get_working_database()
    limit = request.args.get("limit", default=100, type=int) or 100
    limit = max(1, min(limit, 500))

    try:
        with work_db.session_scope() as session:
            score_expr = WorkingUserRating.rating * 2.0
            rows = (
                session.query(
                    WorkingUserRating.sync_id.label("sync_id"),
                    func.avg(score_expr).label("avg_score_10"),
                    func.count(WorkingUserRating.id).label("ratings_count"),
                    func.max(
                        case((UserTrackState.admin_exempt_deletion.is_(True), 1), else_=0)
                    ).label("admin_exempt_deletion"),
                    func.max(
                        case((UserTrackState.admin_force_upgrade.is_(True), 1), else_=0)
                    ).label("admin_force_upgrade"),
                    func.max(UserTrackState.updated_at).label("last_override_at"),
                )
                .outerjoin(UserTrackState, UserTrackState.sync_id == WorkingUserRating.sync_id)
                .group_by(WorkingUserRating.sync_id)
                .all()
            )

            delete_candidates = []
            upgrade_candidates = []

            for row in rows:
                if row.avg_score_10 is None:
                    continue

                avg_score = float(row.avg_score_10)
                candidate = {
                    "sync_id": row.sync_id,
                    "score_10": round(avg_score, 2),
                    "ratings_count": int(row.ratings_count or 0),
                    "admin_exempt_deletion": bool(row.admin_exempt_deletion),
                    "admin_force_upgrade": bool(row.admin_force_upgrade),
                    "last_override_at": row.last_override_at.isoformat() if row.last_override_at else None,
                }

                if avg_score <= 2.0:
                    delete_candidates.append(candidate)
                elif avg_score <= 4.0:
                    upgrade_candidates.append(candidate)

            delete_candidates.sort(key=lambda item: (item["score_10"], -item["ratings_count"]))
            upgrade_candidates.sort(key=lambda item: (item["score_10"], -item["ratings_count"]))

            return jsonify(
                {
                    "success": True,
                    "delete_candidates": delete_candidates[:limit],
                    "upgrade_candidates": upgrade_candidates[:limit],
                    "thresholds": {
                        "delete_month_end": "score 1-2",
                        "upgrade_week_end": "score 3-4",
                    },
                }
            ), 200
    except Exception as e:
        logger.error(f"Error getting suggestion candidates: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.route("/suggestion-candidates/override", methods=["POST"])
def toggle_suggestion_candidate_override():
    """Toggle admin exemption flags used by the suggestion engine lifecycle gate."""
    payload = request.get_json() or {}
    sync_id = _normalize_sync_id(payload.get("sync_id"))
    field = payload.get("field")
    value = bool(payload.get("value"))

    valid_fields = {"admin_exempt_deletion", "admin_force_upgrade"}
    if not sync_id:
        return jsonify({"error": "sync_id is required"}), 400
    if field not in valid_fields:
        return jsonify({"error": f"field must be one of: {sorted(valid_fields)}"}), 400

    work_db = get_working_database()
    try:
        with work_db.session_scope() as session:
            rating_user_ids = [
                user_id
                for (user_id,) in (
                    session.query(WorkingUserRating.user_id)
                    .filter(WorkingUserRating.sync_id == sync_id)
                    .distinct()
                    .all()
                )
            ]

            if not rating_user_ids:
                return jsonify({"error": "No ratings found for the provided sync_id"}), 404

            existing_states = (
                session.query(UserTrackState)
                .filter(
                    UserTrackState.sync_id == sync_id,
                    UserTrackState.user_id.in_(rating_user_ids),
                )
                .all()
            )
            state_by_user = {state.user_id: state for state in existing_states}

            for user_id in rating_user_ids:
                state = state_by_user.get(user_id)
                if state is None:
                    state = UserTrackState(user_id=user_id, sync_id=sync_id)
                    session.add(state)
                setattr(state, field, value)

            session.flush()

            all_states = session.query(UserTrackState).filter(UserTrackState.sync_id == sync_id).all()
            response_state = {
                "sync_id": sync_id,
                "admin_exempt_deletion": any(state.admin_exempt_deletion for state in all_states),
                "admin_force_upgrade": any(state.admin_force_upgrade for state in all_states),
            }

            return jsonify({"success": True, "state": response_state}), 200
    except Exception as e:
        logger.error(f"Error toggling suggestion candidate override for {sync_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route("/prune/run", methods=["POST"])
def run_prune_job():
    """Immediately triggers the background 'Prune/Delete' job."""
    try:
        service = DuplicateHygieneService()
        # Run synchronously for now as per "Immediately triggers"
        result = service.run_prune_job()
        return jsonify({"success": True, "result": result}), 200
    except Exception as e:
        logger.error(f"Error running prune job: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route("/duplicates", methods=["GET"])
def get_duplicates():
    """Get manual review duplicates."""
    try:
        service = DuplicateHygieneService()
        # find_duplicates returns {'auto_resolve': [...], 'manual_review': [...]}
        result = service.find_duplicates()
        return jsonify({"success": True, "duplicates": result.get('manual_review', [])}), 200
    except Exception as e:
        logger.error(f"Error getting duplicates: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route("/queue/actions", methods=["GET"])
def get_action_queue():
    """Get currently staged lifecycle actions and their queue age."""
    now = utc_now()
    work_db = get_working_database()

    try:
        with work_db.session_scope() as session:
            states = (
                session.query(UserTrackState)
                .filter(UserTrackState.lifecycle_action.in_(["DELETE_MONTH_END", "UPGRADE_WEEK_END"]))
                .all()
            )

        grouped = {}
        for state in states:
            row = grouped.setdefault(
                state.sync_id,
                {
                    "sync_id": state.sync_id,
                    "action_needed": state.lifecycle_action,
                    "queued_at": state.lifecycle_queued_at,
                    "admin_exempt_deletion": False,
                    "admin_force_upgrade": False,
                },
            )
            if state.lifecycle_queued_at and (row["queued_at"] is None or state.lifecycle_queued_at < row["queued_at"]):
                row["queued_at"] = state.lifecycle_queued_at
            row["admin_exempt_deletion"] = row["admin_exempt_deletion"] or bool(state.admin_exempt_deletion)
            row["admin_force_upgrade"] = row["admin_force_upgrade"] or bool(state.admin_force_upgrade)

        queue = []
        for item in grouped.values():
            queued_at = item["queued_at"]
            days_in_queue = 0
            if queued_at:
                days_in_queue = max(0, int((now - queued_at).total_seconds() // 86400))

            preview = _resolve_track_preview(item["sync_id"]) or {}

            queue.append(
                {
                    "sync_id": item["sync_id"],
                    "track_id": preview.get("track_id"),
                    "title": preview.get("title"),
                    "artist": preview.get("artist"),
                    "action_needed": item["action_needed"],
                    "queued_at": queued_at.isoformat() if queued_at else None,
                    "days_in_queue": days_in_queue,
                    "admin_exempt_deletion": item["admin_exempt_deletion"],
                    "admin_force_upgrade": item["admin_force_upgrade"],
                }
            )

        queue.sort(key=lambda row: (row["action_needed"], -(row["days_in_queue"] or 0)))

        return jsonify({"success": True, "queue": queue, "count": len(queue)}), 200
    except Exception as e:
        logger.error(f"Error getting staged lifecycle queue: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.route("/track/<int:track_id>/force_delete", methods=["POST"])
def force_delete_track(track_id: int):
    """Force immediate lifecycle delete execution for a track, bypassing timers."""
    sync_id = _sync_id_from_track_id(track_id)
    if not sync_id:
        return jsonify({"error": "Track not found"}), 404

    try:
        result = execute_delete_now(sync_id)
        status = 200 if result.get("success") else 400
        return jsonify(result), status
    except Exception as e:
        logger.error(f"Error forcing delete for track {track_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.route("/track/<int:track_id>/force_upgrade", methods=["POST"])
def force_upgrade_track(track_id: int):
    """Force immediate lifecycle upgrade execution for a track, bypassing timers."""
    sync_id = _sync_id_from_track_id(track_id)
    if not sync_id:
        return jsonify({"error": "Track not found"}), 404

    payload = request.get_json(silent=True) or {}
    quality_profile_id = payload.get("quality_profile_id")

    try:
        result = execute_upgrade_now(sync_id, quality_profile_id=quality_profile_id)
        status = 200 if result.get("success") else 400
        return jsonify(result), status
    except Exception as e:
        logger.error(f"Error forcing upgrade for track {track_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route("/track/<int:track_id>/fetch_metadata", methods=["POST"])
def fetch_metadata(track_id):
    """Manually triggers the MetadataEnhancer for a specific track ID."""
    db = get_database()
    try:
        path = db.get_track_path(track_id)
        if not path:
            return jsonify({"error": "Track not found or file missing"}), 404

        enhancer = get_metadata_enhancer()
        metadata, confidence = enhancer.identify_file(Path(path))

        return jsonify({
            "success": True,
            "metadata": metadata,
            "confidence": confidence
        }), 200
    except Exception as e:
        logger.error(f"Error fetching metadata for track {track_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route("/track/<int:track_id>/override", methods=["POST"])
def override_track(track_id):
    """DEPRECATED: Manual overrides removed in Phase 3.
    
    Phase 3 Suggestion Engine uses event-driven consensus, not system flags.
    Deletion decisions are now made by the Deletion Gate based on:
    - Global consensus (>= 2 ratings AND avg < 4.0)
    - Sponsor rating (from user_track_states)
    
    Manual track management should happen through the auto_importer or library hygiene service.
    """
    return jsonify({
        "success": False,
        "error": "Manual track overrides are deprecated. Use Phase 3 Suggestion Engine consensus rules."
    }), 410

@bp.route("/conflicts/resolve", methods=["POST"])
def resolve_conflict():
    """Manually resolve a conflict by keeping one track and deleting others."""
    payload = request.get_json() or {}
    keep_id = payload.get("keep_id")
    delete_ids = payload.get("delete_ids", [])

    if not keep_id or not delete_ids:
        return jsonify({"error": "keep_id and delete_ids are required"}), 400

    try:
        service = DuplicateHygieneService()
        success = service.resolve_conflict(keep_id, delete_ids)
        if success:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"error": "Failed to resolve some conflicts"}), 500
    except Exception as e:
        logger.error(f"Error resolving conflict: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route("/trends", methods=["GET"])
def get_trends():
    """Returns library stats (filtered)."""
    work_db = get_working_database()
    try:
        target_user, resolved_account_id, source = _resolve_working_user_for_trends()

        with work_db.session_scope() as session:
            # Use SQL aggregation for efficiency
            distribution_stmt = session.query(
                func.round(WorkingUserRating.rating),
                func.count(WorkingUserRating.id)
            ).filter(WorkingUserRating.rating.isnot(None))

            if target_user:
                distribution_stmt = distribution_stmt.filter(WorkingUserRating.user_id == target_user.id)

            distribution_query = distribution_stmt.group_by(func.round(WorkingUserRating.rating)).all()

            distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            total_filtered = 0
            sum_ratings = 0

            for rating_val, count in distribution_query:
                if rating_val is None: continue
                r = int(rating_val)
                if r in distribution:
                    distribution[r] = count
                total_filtered += count
                sum_ratings += r * count

            avg = sum_ratings / total_filtered if total_filtered > 0 else 0

            return jsonify({
                "total_ratings": total_filtered,
                "average_rating": avg,
                "distribution": distribution,
                "user_scope": {
                    "source": source,
                    "account_id": resolved_account_id,
                    "working_user_id": target_user.id if target_user else None,
                    "working_username": target_user.username if target_user else None,
                },
                "note": "Genre stats unavailable (schema limitation)"
            }), 200
    except Exception as e:
        logger.error(f"Error getting trends: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route("/search", methods=["GET"])
def search_library():
    """Unified search endpoint."""
    query = request.args.get("q")
    if not query:
        return jsonify({"artists": [], "albums": [], "tracks": []}), 200

    db = get_database()
    try:
        results = db.search_library(query)
        return jsonify(results), 200
    except Exception as e:
        logger.error(f"Error searching library: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
