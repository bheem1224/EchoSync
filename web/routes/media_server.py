"""Media server selection API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("media_server")

router = APIRouter(prefix="/api/v1/system/media_server", tags=["Media Server"])


class ActiveServerResponse(BaseModel):
    active_server: str


class ActivateServerRequest(BaseModel):
    server: str


class ActivateServerResponse(BaseModel):
    success: bool
    active_server: str


@router.get("/active", response_model=ActiveServerResponse)
def get_active_server():
    """Get the currently active media server."""
    try:
        active_server = config_manager.get("active_media_server", "plex")
        return ActiveServerResponse(active_server=active_server)
    except Exception as e:
        logger.error(f"Error getting active media server: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate", response_model=ActivateServerResponse)
def set_active_server(payload: ActivateServerRequest):
    """Set the active media server."""
    try:
        server_name = payload.server

        if not server_name:
            raise HTTPException(status_code=400, detail="Server name is required")

        # Validate server name
        valid_servers = ["plex", "jellyfin", "navidrome"]
        if server_name not in valid_servers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid server. Must be one of: {', '.join(valid_servers)}",
            )

        config_manager.set("active_media_server", server_name)
        logger.info(f"Active media server set to: {server_name}")

        return ActivateServerResponse(success=True, active_server=server_name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting active media server: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
