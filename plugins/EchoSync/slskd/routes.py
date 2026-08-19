"""Slskd (Soulseek daemon) provider routes.

All paths here are relative to the plugin router prefix, which
plugin_loader mounts to /api/v1/plugins/<plugin_id>.

SlskdCard.svelte calls:
  GET  ${apiBase}/download-clients/active
  POST ${apiBase}/download-clients/activate
  GET  ${apiBase}/settings
  POST ${apiBase}/settings
  POST ${apiBase}/connection/test
  GET  ${apiBase}/settings/key
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from core.tiered_logger import get_logger
import asyncio
import aiohttp

logger = get_logger("slskd_routes")

# The router will be mounted automatically by the plugin loader
router = APIRouter()


# ---------------------------------------------------------------------------
# Download-client proxies — SlskdCard needs these under its own apiBase
# ---------------------------------------------------------------------------

@router.get("/download-clients/active")
def get_active_download_client():
    """Proxy: return the currently active download client."""
    try:
        from core.settings import config_manager
        active_name = config_manager.get_active_download_client() or "slskd"
        is_active = (active_name.lower() == "slskd")
        return {
            "active": is_active,
            "active_client": active_name,
            "name": active_name,
            "provider": active_name
        }
    except Exception as e:
        logger.error(f"Failed to get active download client: {e}")
        return {"active": False, "active_client": None, "error": "Failed to get active download client"}


class ActivateClientRequest(BaseModel):
    provider: Optional[str] = None
    client: Optional[str] = None

@router.post("/download-clients/activate")
def activate_download_client(data: Optional[ActivateClientRequest] = None):
    """Proxy: activate this plugin as the active download client."""
    try:
        from core.settings import config_manager
        target = (data.provider or data.client or "slskd") if data else "slskd"
        config_manager.set_active_download_client(target)
        config_manager.save_settings(config_manager.get_settings())
        return {"success": True, "active_client": target}
    except Exception as e:
        logger.error(f"Failed to activate download client: {e}")
        raise HTTPException(status_code=500, detail="Failed to activate download client")


# ---------------------------------------------------------------------------
# Soulseek / slskd settings
# ---------------------------------------------------------------------------

@router.get("/settings")
def get_settings():
    """Get slskd configuration settings."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        slskd_url = sdk.config.get('slskd_url', '')
        server_name = sdk.config.get('server_name', '')
        api_key = sdk.secrets.get('api_key') or ''
        masked_api_key = '****' if api_key else ''

        return {
            "slskd_url": slskd_url,
            "server_name": server_name,
            "api_key": masked_api_key,
            "has_api_key": bool(api_key),
            "configured": bool(slskd_url and api_key),
        }
    except Exception as e:
        logger.error(f"Failed to get slskd settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get slskd settings")


class SettingsRequest(BaseModel):
    slskd_url: Optional[str] = ""
    api_key: Optional[str] = ""
    server_name: Optional[str] = ""

@router.post("/settings")
def save_settings(data: SettingsRequest):
    """Save slskd configuration settings."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        if not data.slskd_url:
            raise HTTPException(status_code=400, detail="Server URL is required")

        slskd_url = data.slskd_url.strip()
        api_key = data.api_key.strip() if data.api_key else ""
        server_name = data.server_name.strip() if data.server_name else ""

        sdk.config.set('slskd_url', slskd_url)
        sdk.config.set('server_name', server_name)
        if api_key:
            sdk.secrets.set('api_key', api_key)

        logger.info(f"Saved slskd settings: url={slskd_url}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save slskd settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save slskd settings")


class TestConnectionRequest(BaseModel):
    slskd_url: Optional[str] = None
    api_key: Optional[str] = None

@router.post("/connection/test")
def test_connection(data: Optional[TestConnectionRequest] = None):
    """Test connection to slskd server."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        slskd_url = (data.slskd_url if data and data.slskd_url else None) or sdk.config.get('slskd_url', '')
        slskd_url = slskd_url.rstrip('/') if slskd_url else ''
        api_key = (data.api_key if data and data.api_key else None) or sdk.secrets.get('api_key') or ''

        if not slskd_url:
            raise HTTPException(status_code=400, detail="slskd URL not configured")
        if not api_key:
            raise HTTPException(status_code=400, detail="API key not configured")

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
            except Exception:
                return {"success": False, "error": "Connection failed."}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_test())
        finally:
            loop.close()

        if not result["success"]:
            return JSONResponse(status_code=400, content=result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test slskd connection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Connection test failed")


@router.get("/settings/key")
def get_api_key():
    """Return the raw API key (only used by UI show/hide toggle)."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        api_key = sdk.secrets.get('api_key') or ''
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not configured")
        return {"api_key": api_key}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch API key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch API key")
