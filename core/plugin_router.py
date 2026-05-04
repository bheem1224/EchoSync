from flask import Blueprint, abort, request, current_app
from typing import List, Dict
from web.auth import require_auth
from core.tiered_logger import get_logger

logger = get_logger("plugin_router")

class PluginProxyRouter:
    """
    Dynamic Proxy Router for Zero-Downtime Hot Reloading.
    
    Sitting at /api/plugins/{plugin_id}/*, it dynamically routes traffic 
    to whatever blueprint is currently registered in memory for that ID.
    """
    _routers: Dict[str, Blueprint] = {}

    @classmethod
    def mount_router(cls, plugin_id: str, router: Blueprint):
        """Register (or overwrite) a plugin's router in the proxy registry."""
        prefix = f"/api/plugins/{plugin_id}"
        router.url_prefix = prefix
        
        # Enforce internal authentication on all routes within the blueprint
        @router.before_request
        @require_auth
        def enforce_internal_auth():
            pass

        cls._routers[plugin_id] = router
        logger.debug(f"Mounted/Updated dynamic router for {plugin_id} at {prefix}")

    @classmethod
    def get_all_routers(cls) -> List[Blueprint]:
        return list(cls._routers.values())

# Legacy alias for backward compatibility
PluginRouterRegistry = PluginProxyRouter
