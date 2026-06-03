"""Slskd (Soulseek daemon) provider routes.

All paths here are relative to the plugin blueprint prefix, which
plugin_loader sets to  /api/plugins/<plugin_name>  (e.g. /api/plugins/Slskd).

SlskdCard.svelte calls:
  GET  ${apiBase}/providers/download-clients/active   → proxied to plugins_api
  POST ${apiBase}/providers/download-clients/activate → proxied to plugins_api
  GET  ${apiBase}/providers/soulseek/settings
  POST ${apiBase}/providers/soulseek/settings
  POST ${apiBase}/providers/soulseek/connection/test
  GET  ${apiBase}/providers/soulseek/settings/key
"""

import logging
from flask import Blueprint, jsonify, request
from core.tiered_logger import get_logger
import asyncio
import aiohttp

logger = get_logger("slskd_routes")

# NOTE: url_prefix is overridden by plugin_loader to /api/plugins/<name>.
# The sub-paths below match what SlskdCard.svelte sends relative to apiBase.
bp = Blueprint("soulseek_routes", __name__, url_prefix="/api/plugins/Slskd")


# ---------------------------------------------------------------------------
# Download-client proxies — SlskdCard needs these under its own apiBase
# ---------------------------------------------------------------------------

@bp.get("/providers/download-clients/active")
def get_active_download_client():
    """Proxy: return the currently active download client."""
    def _safe_get(obj, attr, default):
        return obj.__getattribute__(attr) if hasattr(obj, attr) else default
        
    try:
        from core.nexus_framework.plugin_loader import PluginRegistry
        clients = PluginRegistry.get_download_clients()
        active = next((c for c in clients if _safe_get(c, 'is_active', False)), None)
        if active:
            name = _safe_get(active, 'name', 'slskd')
            return jsonify({"active": True, "name": name, "provider": name}), 200
        return jsonify({"active": False, "name": None}), 200
    except Exception as e:
        logger.error(f"Failed to get active download client: {e}")
        return jsonify({"active": False, "error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal error checking client"}), 200


@bp.post("/providers/download-clients/activate")
def activate_download_client():
    """Proxy: activate this plugin as the active download client."""
    try:
        data = request.get_json() or {}
        provider = data.get("provider", "slskd")
        # Forward to the core plugins_api activate endpoint
        from web.routes.plugins_api import bp as plugins_bp
        # Delegate by calling the function directly
        from web.routes.plugins_api import activate_download_client as core_activate
        return core_activate()
    except Exception as e:
        logger.error(f"Failed to activate download client: {e}")
        return jsonify({"success": False, "error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Soulseek / slskd settings
# ---------------------------------------------------------------------------

@bp.route("/providers/soulseek/settings", methods=["GET"])
def get_settings():
    """Get slskd configuration settings."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        slskd_url = sdk.config.get('slskd_url', '')
        server_name = sdk.config.get('server_name', '')
        api_key = sdk.secrets.get('api_key') or ''
        masked_api_key = '****' if api_key else ''

        return jsonify({
            "slskd_url": slskd_url,
            "server_name": server_name,
            "api_key": masked_api_key,
            "has_api_key": bool(api_key),
            "configured": bool(slskd_url and api_key),
        }), 200
    except Exception as e:
        logger.error(f"Failed to get slskd settings: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.route("/providers/soulseek/settings", methods=["POST"])
def save_settings():
    """Save slskd configuration settings."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        slskd_url = data.get("slskd_url", "").strip()
        api_key = data.get("api_key", "").strip()
        server_name = data.get("server_name", "").strip()

        if not slskd_url:
            return jsonify({"error": "Server URL is required"}), 400

        sdk.config.set('slskd_url', slskd_url)
        sdk.config.set('server_name', server_name)
        if api_key:
            sdk.secrets.set('api_key', api_key)

        logger.info(f"Saved slskd settings: url={slskd_url}")
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Failed to save slskd settings: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.route("/providers/soulseek/connection/test", methods=["POST"])
def test_connection():
    """Test connection to slskd server."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        payload = request.get_json(silent=True) or {}
        slskd_url = payload.get('slskd_url') or sdk.config.get('slskd_url', '')
        slskd_url = slskd_url.rstrip('/') if slskd_url else ''
        api_key = payload.get('api_key') or sdk.secrets.get('api_key') or ''

        if not slskd_url:
            return jsonify({"success": False, "error": "slskd URL not configured"}), 400
        if not api_key:
            return jsonify({"success": False, "error": "API key not configured"}), 400

        async def _test():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{slskd_url}/api/v0/application",
                        headers={"X-API-Key": api_key},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            d = await resp.json()
                            return {"success": True, "version": d.get("version", "unknown")}
                        if resp.status == 401:
                            return {"success": False, "error": "Invalid API key"}
                        return {"success": False, "error": f"Server returned {resp.status}"}
            except aiohttp.ClientConnectorError:
                return {"success": False, "error": "Could not connect. Check URL and ensure slskd is running."}
            except asyncio.TimeoutError:
                return {"success": False, "error": "Connection timed out."}
            except Exception as ex:
                return {"success": False, "error": str(ex)}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_test())
        finally:
            loop.close()

        return jsonify(result), 200 if result["success"] else 400
    except Exception as e:
        logger.error(f"Failed to test slskd connection: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.route("/providers/soulseek/settings/key", methods=["GET"])
def get_api_key():
    """Return the raw API key (only used by UI show/hide toggle)."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        api_key = sdk.secrets.get('api_key') or ''
        if not api_key:
            return jsonify({"error": "API key not configured"}), 404
        return jsonify({"api_key": api_key}), 200
    except Exception as e:
        logger.error(f"Failed to fetch API key: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500
