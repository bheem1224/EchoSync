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
        api_key = sdk.config.get('api_key') or sdk.secrets.get('api_key')
        if not api_key:
            from database.config_database import get_config_database
            db = get_config_database()
            svc_id = db.get_service_id(2136125342) or db.get_service_id('EchoSync.Acoustid') or db.get_service_id('EchoSync.acoustid') or db.get_service_id('acoustid')
            if svc_id:
                api_key = db.get_service_config(svc_id, 'api_key')
        if not api_key:
            from core.settings import config_manager
            api_key = config_manager.get('acoustid.api_key')

        user_api_key = sdk.config.get('user_api_key') or sdk.secrets.get('user_api_key')
        if not user_api_key:
            from database.config_database import get_config_database
            db = get_config_database()
            svc_id = db.get_service_id(2136125342) or db.get_service_id('EchoSync.Acoustid') or db.get_service_id('EchoSync.acoustid') or db.get_service_id('acoustid')
            if svc_id:
                user_api_key = db.get_service_config(svc_id, 'user_api_key')
        if not user_api_key:
            from core.settings import config_manager
            user_api_key = config_manager.get('acoustid.user_api_key')

        auto_contribute = sdk.config.get('auto_contribute')
        return JSONResponse(content={
            "api_key_configured": bool(api_key),
            "user_key_configured": bool(user_api_key),
            "auto_contribute": auto_contribute == "true" if isinstance(auto_contribute, str) else bool(auto_contribute),
        })
    except Exception as e:
        logger.error(f"Error reading AcoustID config: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to read AcoustID config"}, status_code=500)

@config_router.post("/config")
async def save_config(request: Request):
    """Persist AcoustID settings-card values (API key + user API key + auto-contribute)."""
    try:
        payload = await request.json() or {}
        
        if "api_key" in payload and payload["api_key"].strip():
            from core.security import encrypt_string
            enc_key = encrypt_string(payload["api_key"].strip())
            sdk.config.set('api_key', enc_key)
            from database.config_database import get_config_database
            db = get_config_database()
            svc_id = db.get_service_id(2136125342) or db.get_service_id('EchoSync.Acoustid') or db.get_service_id('EchoSync.acoustid') or db.get_service_id('acoustid')
            if svc_id:
                db.set_service_config(svc_id, 'api_key', enc_key, is_sensitive=True)

        if "user_api_key" in payload and payload["user_api_key"].strip():
            from core.security import encrypt_string
            enc_user_key = encrypt_string(payload["user_api_key"].strip())
            sdk.config.set('user_api_key', enc_user_key)
            from database.config_database import get_config_database
            db = get_config_database()
            svc_id = db.get_service_id(2136125342) or db.get_service_id('EchoSync.Acoustid') or db.get_service_id('EchoSync.acoustid') or db.get_service_id('acoustid')
            if svc_id:
                db.set_service_config(svc_id, 'user_api_key', enc_user_key, is_sensitive=True)

        if "auto_contribute" in payload:
            sdk.config.set('auto_contribute', str(bool(payload["auto_contribute"])).lower())

        api_key = sdk.config.get('api_key') or sdk.secrets.get('api_key')
        if not api_key:
            from database.config_database import get_config_database
            db = get_config_database()
            svc_id = db.get_service_id(2136125342) or db.get_service_id('EchoSync.Acoustid') or db.get_service_id('EchoSync.acoustid') or db.get_service_id('acoustid')
            if svc_id:
                api_key = db.get_service_config(svc_id, 'api_key')

        user_api_key = sdk.config.get('user_api_key') or sdk.secrets.get('user_api_key')
        if not user_api_key:
            from database.config_database import get_config_database
            db = get_config_database()
            svc_id = db.get_service_id(2136125342) or db.get_service_id('EchoSync.Acoustid') or db.get_service_id('EchoSync.acoustid') or db.get_service_id('acoustid')
            if svc_id:
                user_api_key = db.get_service_config(svc_id, 'user_api_key')

        auto_contribute = sdk.config.get('auto_contribute')
        return JSONResponse(content={
            "success": True, 
            "api_key_configured": bool(api_key),
            "user_key_configured": bool(user_api_key),
            "auto_contribute": auto_contribute == "true" if isinstance(auto_contribute, str) else bool(auto_contribute)
        })
    except Exception as e:
        logger.error(f"Error saving AcoustID config: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to save AcoustID config"}, status_code=500)
