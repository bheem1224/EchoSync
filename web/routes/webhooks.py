"""
Routes for handling incoming webhooks from external media servers (e.g., Plex).
"""

import json
from flask import Blueprint, request, jsonify
from core.tiered_logger import get_logger
from services.user_ratings_service import UserRatingsService
from core.suggestion_engine.webhooks import PlexWebhookParser

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

    parser = PlexWebhookParser()
    parsed_data = parser.parse_payload(payload)

    if not parsed_data:
        return jsonify({"status": "ignored", "message": "Payload ignored or missing required track metadata"}), 200

    ratings_service = UserRatingsService()
    event_type = parsed_data.get("event_type")

    if event_type == "rate":
        ratings_service.update_rating(
            artist_name=parsed_data["artist_name"],
            track_title=parsed_data["track_title"],
            rating=parsed_data["rating"],
            source=parsed_data["source"],
            user_identifier=parsed_data["user_identifier"]
        )
        return jsonify({"status": "success", "message": "Rating updated"}), 200

    elif event_type == "scrobble":
        ratings_service.increment_play_count(
            artist_name=parsed_data["artist_name"],
            track_title=parsed_data["track_title"],
            source=parsed_data["source"],
            user_identifier=parsed_data["user_identifier"]
        )
        return jsonify({"status": "success", "message": "Scrobble recorded"}), 200

    return jsonify({"status": "ignored", "message": f"Unhandled event type: {event_type}"}), 200
