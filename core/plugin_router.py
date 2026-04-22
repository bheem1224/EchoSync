from flask import Blueprint, abort, request
from typing import List
from web.auth import require_auth

class PluginRouterRegistry:
    _blueprints: List[Blueprint] = []

    @classmethod
    def mount_router(cls, plugin_id: str, router: Blueprint):
        """
        Mounts a plugin's internal micro-API.
        Strictly enforces the /api/plugins/{plugin_id} namespace.
        Applies require_auth to all routes to lock them down to internal Svelte frontend.
        """
        # Enforce strict namespace
        prefix = f"/api/plugins/{plugin_id}"
        router.url_prefix = prefix

        # Enforce internal authentication on all routes within the blueprint
        @router.before_request
        @require_auth
        def enforce_internal_auth():
            pass

        cls._blueprints.append(router)

    @classmethod
    def get_all_routers(cls) -> List[Blueprint]:
        return cls._blueprints
