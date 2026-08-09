import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from core.nexus_framework.plugin_SDK import sdk
from core.tiered_logger import get_logger

logger = get_logger("acoustid_routes")

# Blueprint for the AcoustID settings-card config API
config_router = APIRouter()

@config_router.get("/config")
def get_config():
    """Return the current AcoustID settings-card configuration."""
    try:
        
        # The legacy key was stored under service 'acoustid' as 'api_key'
        api_key = sdk.config.get('api_key')
        auto_contribute = sdk.config.get('auto_contribute')
        return JSONResponse(content={
            "api_key_configured": bool(api_key),
            "auto_contribute": auto_contribute == "true" if isinstance(auto_contribute, str) else bool(auto_contribute),
        }), 200
    except Exception as e:
        logger.error(f"Error reading AcoustID config: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)

@config_router.post("/config")
async def save_config(request: Request):
    """Persist AcoustID settings-card values (API key + auto-contribute)."""
    try:
        payload = await request.json() or {}
        
        if "api_key" in payload and payload["api_key"].strip():
            from core.security import encrypt_string
            sdk.config.set('api_key', encrypt_string(payload["api_key"].strip()))

        if "auto_contribute" in payload:
            sdk.config.set('auto_contribute', str(bool(payload["auto_contribute"])).lower())

        api_key = sdk.config.get('api_key')
        auto_contribute = sdk.config.get('auto_contribute')
        return JSONResponse(content={
            "success": True, 
            "api_key_configured": bool(api_key),
            "auto_contribute": auto_contribute == "true" if isinstance(auto_contribute, str) else bool(auto_contribute)
        }), 200
    except Exception as e:
        logger.error(f"Error saving AcoustID config: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)
