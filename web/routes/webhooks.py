"""Webhooks API for receiving push events from media servers."""

from flask import Blueprint, request, jsonify
from core.tiered_logger import get_logger
from core.webhook_parsers import parse_media_server_webhook
from database.working_database import get_working_database, PlaybackHistory
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from time_utils import utc_now

logger = get_logger("webhooks")

bp = Blueprint('webhooks', __name__, url_prefix='/api/webhooks')


@bp.post('/<provider>')
def handle_provider_webhook(provider: str):
    """Handle incoming webhooks from any supported media server (plex, navidrome, …)."""
    try:
        parsed_data = parse_media_server_webhook(request, provider=provider)

        if parsed_data:
            user_id = parsed_data.get('user_id')
            provider_item_id = parsed_data.get('provider_item_id')

            if user_id and provider_item_id:
                listened_at = utc_now()
                working_db = get_working_database()
                with working_db.session_scope() as session:
                    # INSERT OR IGNORE: delivery retries for the same scrobble at
                    # the same timestamp must not raise IntegrityError.
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
                    logger.info(
                        f"Recorded {provider} playback: user={user_id}, "
                        f"provider_item_id={provider_item_id}"
                    )

    except Exception as e:
        logger.error(f"Error handling {provider} webhook: {e}", exc_info=True)

    # ALWAYS return 200 OK so the media server never marks our endpoint as dead.
    return jsonify({"status": "ok"}), 200
