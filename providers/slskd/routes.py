from flask import Blueprint, jsonify, request
from core.settings import config_manager
from core.tiered_logger import get_logger
import asyncio
import aiohttp

logger = get_logger("slskd_routes")
bp = Blueprint("soulseek_routes", __name__, url_prefix="/api/providers/soulseek")


@bp.route("/settings", methods=["GET"])
def get_settings():
    """Get slskd configuration settings."""
    try:
        slskd_url = config_manager.get('soulseek.slskd_url', '')
        server_name = config_manager.get('soulseek.server_name', '')
        # api_key is sensitive; prefer the storage helper which persists to DB
        from core.file_handling.storage import get_storage_service
        storage = get_storage_service()
        api_key = storage.get_service_config('soulseek', 'api_key') or ''
        
        # also update in-memory config in case UI reads it
        # (key is filtered out on save but may still exist transiently)
        if api_key:
            config_manager.set('soulseek.api_key', api_key)
        
        # Return masked API key if it exists
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
        return jsonify({"error": str(e)}), 500


@bp.route("/settings", methods=["POST"])
def save_settings():
    """Save slskd configuration settings."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        slskd_url = data.get("slskd_url", "").strip()
        api_key = data.get("api_key", "").strip()
        server_name = data.get("server_name", "").strip()
        
        if not slskd_url:
            return jsonify({"error": "Server URL is required"}), 400
        
        # Save settings using config_manager
        config_manager.set('soulseek.slskd_url', slskd_url)
        config_manager.set('soulseek.server_name', server_name)
        
        # Only update API key if provided (don't overwrite with empty string)
        if api_key:
            # write secret via storage service to ensure DB persistence
            from core.file_handling.storage import get_storage_service
            storage = get_storage_service()
            storage.set_service_config('soulseek', 'api_key', api_key, is_sensitive=True)
            # mirror to config_manager so GET requests can see it immediately
            config_manager.set('soulseek.api_key', api_key)
        
        logger.info(f"Saved slskd settings: {slskd_url}")
        
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Failed to save slskd settings: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.route("/connection/test", methods=["POST"])
def test_connection():
    """Test connection to slskd server."""
    try:
        slskd_url = config_manager.get('soulseek.slskd_url', '')
        api_key = config_manager.get('soulseek.api_key', '')
        server_name = config_manager.get('soulseek.server_name', '')
        
        if not slskd_url:
            return jsonify({
                "success": False,
                "error": "slskd URL not configured"
            }), 400
        
        if not api_key:
            return jsonify({
                "success": False,
                "error": "API key not configured"
            }), 400
        
        # Test connection using slskd API
        async def test_slskd():
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"X-API-Key": api_key}
                    
                    # Try to get server state
                    async with session.get(
                        f"{slskd_url}/api/v0/application",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return {
                                "success": True,
                                "version": data.get("version", "unknown"),
                                "server_name": server_name or "slskd"
                            }
                        elif response.status == 401:
                            return {
                                "success": False,
                                "error": "Invalid API key"
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"Server returned status {response.status}"
                            }
            except aiohttp.ClientConnectorError:
                return {
                    "success": False,
                    "error": "Could not connect to server. Check URL and ensure slskd is running."
                }
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "error": "Connection timeout. Server is not responding."
                }
            except Exception as e:
                logger.error(f"Connection test error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_slskd())
        finally:
            loop.close()
        
        status_code = 200 if result["success"] else 400
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Failed to test slskd connection: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route("/settings/key", methods=["GET"])
def get_api_key():
    """Return the raw API key for slskd. This is only used by the web UI when
    the user explicitly requests to reveal the key via the show/hide toggle.
    """
    try:
        api_key = config_manager.get('soulseek.api_key', '')
        if not api_key:
            return jsonify({"error": "API key not configured"}), 404

        return jsonify({"api_key": api_key}), 200
    except Exception as e:
        logger.error(f"Failed to fetch API key: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
