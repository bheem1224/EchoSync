from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.nexus_framework.plugin_SDK import sdk
from core.tiered_logger import get_logger

logger = get_logger("acoustid_routes")

# Blueprint for the AcoustID settings-card config API
config_router = APIRouter()


def _get_acoustid_config(key: str) -> str | None:
    val = sdk.config.get(key) or sdk.secrets.get(key)
    if val:
        return val
    for svc_key in (1910609384, 2136125342, "EchoSync.Acoustid", "EchoSync.acoustid", "acoustid"):
        val = sdk.config.get_for_service(svc_key, key)
        if val:
            return val
    from core.settings import config_manager

    return config_manager.get(f"acoustid.{key}")


def _set_acoustid_config(key: str, value: str) -> None:
    sdk.config.set(key, value)
    for svc_key in (1910609384, 2136125342, "EchoSync.Acoustid", "EchoSync.acoustid", "acoustid"):
        if sdk.config.set_for_service(svc_key, key, value, is_sensitive=True):
            break


@config_router.get("/config")
def get_config():
    """Return the current AcoustID settings-card configuration."""
    try:
        api_key = _get_acoustid_config("api_key")
        user_api_key = _get_acoustid_config("user_api_key")

        auto_contribute = sdk.config.get("auto_contribute")
        return JSONResponse(
            content={
                "api_key_configured": bool(api_key),
                "user_key_configured": bool(user_api_key),
                "auto_contribute": auto_contribute == "true"
                if isinstance(auto_contribute, str)
                else bool(auto_contribute),
            }
        )
    except Exception as e:
        logger.error(f"Error reading AcoustID config: {e}", exc_info=True)
        return JSONResponse(
            content={"error": "Failed to read AcoustID config"}, status_code=500
        )


@config_router.post("/config")
async def save_config(request: Request):
    """Persist AcoustID settings-card values (API key + user API key + auto-contribute)."""
    try:
        payload = await request.json() or {}

        if "api_key" in payload and payload["api_key"].strip():
            from core.security import encrypt_string

            enc_key = encrypt_string(payload["api_key"].strip())
            _set_acoustid_config("api_key", enc_key)

        if "user_api_key" in payload and payload["user_api_key"].strip():
            from core.security import encrypt_string

            enc_user_key = encrypt_string(payload["user_api_key"].strip())
            _set_acoustid_config("user_api_key", enc_user_key)

        if "auto_contribute" in payload:
            sdk.config.set(
                "auto_contribute", str(bool(payload["auto_contribute"])).lower()
            )

        api_key = _get_acoustid_config("api_key")
        user_api_key = _get_acoustid_config("user_api_key")

        auto_contribute = sdk.config.get("auto_contribute")
        return JSONResponse(
            content={
                "success": True,
                "api_key_configured": bool(api_key),
                "user_key_configured": bool(user_api_key),
                "auto_contribute": auto_contribute == "true"
                if isinstance(auto_contribute, str)
                else bool(auto_contribute),
            }
        )
    except Exception as e:
        logger.error(f"Error saving AcoustID config: {e}", exc_info=True)
        return JSONResponse(
            content={"error": "Failed to save AcoustID config"}, status_code=500
        )
