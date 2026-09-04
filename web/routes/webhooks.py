import hmac
import ipaddress
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from core.tiered_logger import get_logger
from core.plugins.sdk import compute_plugin_crc32, dispatch_webhook, lookup_registered_endpoint
from core.webhook_parsers import parse_media_server_webhook
from database.working_database import get_working_database, PlaybackHistory
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from time_utils import utc_now

logger = get_logger("webhooks")

router = APIRouter(tags=["Webhooks"])


def is_ip_allowed(client_ip: str, allowed_subnets: list) -> bool:
    """Check if client IP matches any allowed CIDR subnets. If list empty, all allowed."""
    if not allowed_subnets:
        return True
    try:
        ip_obj = ipaddress.ip_address(client_ip)
        for subnet in allowed_subnets:
            if "/" in subnet:
                net = ipaddress.ip_network(subnet, strict=False)
                if ip_obj in net:
                    return True
            else:
                if str(ip_obj) == subnet.strip():
                    return True
        return False
    except Exception as e:
        logger.warning(f"Error checking CIDR whitelist for {client_ip}: {e}")
        return False


@router.post("/api/v1/webhooks/{plugin_identifier}/{endpoint_slug}")
async def handle_plugin_ingress_webhook(
    plugin_identifier: str,
    endpoint_slug: str,
    request: Request,
):
    """
    Centralized Ingress Gateway for Plugin Webhooks.
    Enforces strict identifier scoping (CRC32 integer or fully qualified dot-namespaced string).
    Unqualified bare names (e.g. 'slskd') are strictly rejected with 404.
    """
    # 1. Identifier Validation & Resolution
    clean_identifier = plugin_identifier.strip()
    plugin_id: int

    if clean_identifier.isdigit():
        plugin_id = int(clean_identifier)
    elif "." in clean_identifier:
        plugin_id = compute_plugin_crc32(clean_identifier)
    else:
        # Bare unqualified aliases are strictly forbidden
        logger.warning(
            f"Rejected webhook request with unqualified plugin alias: '{clean_identifier}'. "
            f"Must use fully qualified namespace (e.g. 'EchoSync.slskd') or CRC32 integer."
        )
        raise HTTPException(
            status_code=404,
            detail="Invalid plugin identifier: bare unqualified names are not permitted. Use fully qualified namespace (e.g. 'EchoSync.slskd') or CRC32 ID."
        )

    # 2. Lookup Endpoint Registration
    endpoint_meta = lookup_registered_endpoint(plugin_id, endpoint_slug)
    if not endpoint_meta:
        logger.warning(
            f"Webhook endpoint '{endpoint_slug}' not found for plugin_id {plugin_id} (identifier: '{clean_identifier}')."
        )
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    # 3. CIDR Subnet Filtering
    client_ip = request.client.host if request.client else "127.0.0.1"
    # Consider X-Forwarded-For if behind proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    allowed_subnets = endpoint_meta.get("allowed_subnets", [])
    if not is_ip_allowed(client_ip, allowed_subnets):
        logger.warning(f"Forbidden webhook access from IP {client_ip} to {endpoint_slug} (CIDR mismatch)")
        raise HTTPException(status_code=403, detail="Forbidden: IP address not allowed")

    # 4. Secret / Authentication Check
    allow_unauth = endpoint_meta.get("allow_unauthenticated", False)
    if not allow_unauth:
        expected_secret = endpoint_meta.get("secret")
        if expected_secret:
            # Check X-EchoSync-Webhook-Secret header or ?secret= query parameter
            provided_secret = request.headers.get("X-EchoSync-Webhook-Secret") or request.query_params.get("secret")
            if not provided_secret or not hmac.compare_digest(str(provided_secret), str(expected_secret)):
                logger.warning(f"Unauthorized webhook attempt for {endpoint_slug} on plugin {plugin_id}")
                raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing webhook secret")

    # 5. Extract Payload
    payload = {}
    content_type = request.headers.get("content-type", "")
    try:
        if "application/json" in content_type:
            payload = await request.json()
        elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            payload = dict(form)
        else:
            raw_body = await request.body()
            if raw_body:
                import json
                try:
                    payload = json.loads(raw_body.decode("utf-8", errors="replace"))
                except Exception:
                    payload = {"raw": raw_body.decode("utf-8", errors="replace")}
    except Exception as e:
        logger.warning(f"Failed to parse webhook body: {e}")
        payload = {}

    # 6. Dispatch Payload
    try:
        await dispatch_webhook(plugin_id, endpoint_slug, payload)
    except Exception as e:
        logger.error(f"Error dispatching webhook to plugin {plugin_id}: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

    return {"status": "ok", "plugin_id": plugin_id, "endpoint": endpoint_slug}


@router.post("/api/v1/system/webhooks/{plugin}")
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
