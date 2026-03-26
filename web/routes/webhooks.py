"""Webhooks API for receiving push events from media servers."""

from flask import Blueprint, request, jsonify
from core.tiered_logger import get_logger
from core.webhook_parsers import PlexWebhookParser
from database.working_database import get_working_database, PlaybackHistory
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from time_utils import utc_now

logger = get_logger("webhooks")

bp = Blueprint('webhooks', __name__, url_prefix='/api/webhooks')


@bp.post('/plex')
def handle_plex_webhook():
    """Handle incoming Plex webhooks."""
    try:
        parser = PlexWebhookParser()
        parsed_data = parser.parse(request)

        if parsed_data:
            user_id = parsed_data.get('user_id')
            provider_item_id = parsed_data.get('provider_item_id')

            if user_id and provider_item_id:
                listened_at = utc_now()
                working_db = get_working_database()
                with working_db.session_scope() as session:
                    # Use INSERT OR IGNORE so Plex delivery retries for the same
                    # scrobble at the same timestamp don't raise IntegrityError.
                    if working_db.engine.dialect.name == 'sqlite':
                        stmt = sqlite_insert(PlaybackHistory).values(
                            user_id=user_id,
                            provider_item_id=provider_item_id,
                            listened_at=listened_at,
                        ).on_conflict_do_nothing(
                            index_elements=['user_id', 'provider_item_id', 'listened_at']
                        )
                        session.execute(stmt)
                    else:
                        session.add(PlaybackHistory(
                            user_id=user_id,
                            provider_item_id=provider_item_id,
                            listened_at=listened_at,
                        ))
                    logger.info(f"Recorded Plex playback history: user {user_id}, track {provider_item_id}")

    except Exception as e:
        logger.error(f"Error handling Plex webhook: {e}", exc_info=True)

    # ALWAYS return 200 OK instantly so Plex doesn't flag our endpoint as dead
    return jsonify({"status": "ok"}), 200
