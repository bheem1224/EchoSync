from flask import Blueprint, jsonify, request
from time_utils import utc_now
from core.tiered_logger import get_logger
from core.settings import config_manager
from services.library_hygiene import DuplicateHygieneService
from services.metadata_enhancer import get_metadata_enhancer
from database.music_database import get_database, Track, UserRating
from core.suggestion_engine.consensus import calculate_consensus
from pathlib import Path
from sqlalchemy import func
from datetime import datetime

logger = get_logger("web.routes.manager")
bp = Blueprint("manager", __name__, url_prefix="/api/manager")

@bp.route("/settings", methods=["GET", "POST"])
def manager_settings():
    """Get or update manager settings."""
    if request.method == "POST":
        payload = request.get_json() or {}
        # Validation could be added here
        try:
            manager_config = config_manager.get('manager', {})
            # Update known keys
            for key in ['enabled', 'delete_threshold', 'upgrade_threshold']:
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
                'upgrade_threshold': 2
            })
            return jsonify({"success": True, "settings": settings}), 200
        except Exception as e:
            logger.error(f"Error getting manager settings: {e}")
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
