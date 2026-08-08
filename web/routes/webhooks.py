"""Webhooks API for receiving push events from media servers."""

from fastapi import APIRouter, Request
from core.tiered_logger import get_logger
from core.webhook_parsers import parse_media_server_webhook
from database.working_database import get_working_database, PlaybackHistory
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from time_utils import utc_now

logger = get_logger("webhooks")

router = APIRouter(prefix="/api/v1/system/webhooks", tags=["Webhooks"])


@router.post("/{plugin}")
async def handle_plugin_webhook(plugin: str, request: Request):
    """Handle incoming webhooks from any supported media server (plex, navidrome, …)."""
    try:
        try:
            from core.hook_manager import hook_manager

            content_type = request.headers.get("content-type", "")
            raw_payload = None
            form_data = {}

            if "application/json" in content_type:
                raw_payload = await request.json()
            elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                form = await request.form()
                form_data = dict(form)
                raw_payload = form_data
            else:
                body = await request.body()
                raw_payload = body.decode('utf-8', errors='replace')

            plugin_action = hook_manager.apply_filters(
                'ON_INBOUND_WEBHOOK', None, provider=plugin, payload=raw_payload, headers=dict(request.headers)
            )
            if plugin_action == "SKIP":
                logger.info(f"Plugin intercepted and handled webhook for plugin: {plugin}")
                return {"status": "ok"}
        except Exception as e:
            logger.error(f"Error in ON_INBOUND_WEBHOOK hook: {e}")
            form_data = {} # fallback
            raw_payload = {}

        # Pass the parsed dictionary to the webhook parser
        payload_to_parse = raw_payload if isinstance(raw_payload, dict) else form_data
        parsed_data = parse_media_server_webhook(payload_to_parse, plugin=plugin)

        if parsed_data:
            user_id = parsed_data.get('user_id')
            plugin_item_id = parsed_data.get('plugin_item_id')

            if user_id and plugin_item_id:
                listened_at = utc_now()
                working_db = get_working_database()
                with working_db.session_scope() as session:
                    # INSERT OR IGNORE: delivery retries for the same scrobble at
                    # the same timestamp must not raise IntegrityError.
                    if working_db.engine.dialect.name == 'sqlite':
                        stmt = sqlite_insert(PlaybackHistory).values(
                            user_id=user_id,
                            plugin_item_id=plugin_item_id,
                            listened_at=listened_at,
                        ).on_conflict_do_nothing(
                            index_elements=['user_id', 'plugin_item_id', 'listened_at']
                        )
                        session.execute(stmt)
                    else:
                        session.add(PlaybackHistory(
                            user_id=user_id,
                            plugin_item_id=plugin_item_id,
                            listened_at=listened_at,
                        ))
                    logger.info(
                        f"Recorded {plugin} playback: user={user_id}, "
                        f"plugin_item_id={plugin_item_id}"
                    )

    except Exception as e:
        logger.error(f"Error handling {plugin} webhook: {e}", exc_info=True)

    # ALWAYS return 200 OK so the media server never marks our endpoint as dead.
    return {"status": "ok"}
