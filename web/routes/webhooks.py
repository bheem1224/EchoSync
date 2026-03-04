"""
Routes for handling incoming webhooks from external media servers (e.g., Plex).
"""

import json
from flask import Blueprint, request, jsonify
from core.tiered_logger import get_logger
from services.user_ratings_service import UserRatingsService

logger = get_logger("webhooks_route")
bp = Blueprint("webhooks", __name__, url_prefix="/api/webhooks")

@bp.route("/plex", methods=["POST"])
def plex_webhook():
    """
    Handle incoming Plex webhooks.
    Expected format: multipart/form-data with a 'payload' field containing JSON.
    """
    if "payload" not in request.form:
        logger.warning("Plex webhook received without 'payload' field")
        return jsonify({"status": "error", "message": "Missing payload"}), 400

    try:
        payload_str = request.form["payload"]
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        logger.error("Failed to decode Plex webhook JSON payload")
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    event = payload.get("event")
    metadata = payload.get("Metadata", {})
    account = payload.get("Account", {})

    media_type = metadata.get("type")
    if media_type != "track":
        # We only care about track events
        return jsonify({"status": "ignored", "message": f"Ignoring media type: {media_type}"}), 200

    user_identifier = account.get("title")
    if not user_identifier:
        logger.warning("Plex webhook missing Account.title (user identifier)")
        return jsonify({"status": "error", "message": "Missing user identifier"}), 400

    track_title = metadata.get("title")
    artist_name = metadata.get("grandparentTitle")

    if not track_title or not artist_name:
        logger.warning("Plex webhook missing track title or artist name")
        return jsonify({"status": "error", "message": "Missing track/artist metadata"}), 400

    ratings_service = UserRatingsService()

    if event == "media.rate":
        rating = metadata.get("userRating")
        if rating is None:
            logger.warning("Plex media.rate event missing userRating")
            return jsonify({"status": "error", "message": "Missing rating"}), 400

        # Plex sends rating on a 0-10 scale
        ratings_service.update_rating(
            artist_name=artist_name,
            track_title=track_title,
            rating=float(rating),
            source="plex",
            user_identifier=user_identifier
        )
        return jsonify({"status": "success", "message": "Rating updated"}), 200

    elif event == "media.scrobble":
        ratings_service.increment_play_count(
            artist_name=artist_name,
            track_title=track_title,
            source="plex",
            user_identifier=user_identifier
        )
        return jsonify({"status": "success", "message": "Scrobble recorded"}), 200

    return jsonify({"status": "ignored", "message": f"Ignoring event: {event}"}), 200
