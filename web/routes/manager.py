from flask import Blueprint, jsonify, request
from time_utils import utc_now
from core.tiered_logger import get_logger
from core.settings import config_manager
from services.library_hygiene import DuplicateHygieneService
from services.metadata_enhancer import get_metadata_enhancer
from database.music_database import get_database, Track, UserRating
from database.working_database import get_working_database, UserRating as WorkingUserRating, UserTrackState
from core.suggestion_engine.consensus import calculate_consensus
from pathlib import Path
from sqlalchemy import func, case
from datetime import datetime

logger = get_logger("web.routes.manager")
bp = Blueprint("manager", __name__, url_prefix="/api/manager")


def _normalize_sync_id(sync_id: str) -> str:
    return (sync_id or "").split("?")[0].strip()

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
    """Get items pending action (determined by consensus rules).
    
    NOTE: Phase 3 Suggestion Engine uses event-driven deletion instead of manual overrides.
    This endpoint is deprecated. Consensus is now evaluated asynchronously in the suggestion engine.
    """
    return jsonify({
        "success": True,
        "queue": [],
        "message": "Action queue deprecated. Use Phase 3 Suggestion Engine for consensus evaluation."
    }), 200

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
    db = get_database()
    try:
        with db.session_scope() as session:
            # Use SQL aggregation for efficiency
            distribution_query = (
                session.query(func.round(UserRating.rating), func.count(UserRating.id))
                .filter(UserRating.rating.isnot(None))
                .group_by(func.round(UserRating.rating))
                .all()
            )

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
