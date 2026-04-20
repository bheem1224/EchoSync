from flask import Blueprint
from typing import List

class PluginRouterRegistry:
    _blueprints: List[Blueprint] = []

    @classmethod
    def mount_router(cls, prefix: str, router: Blueprint):
        if prefix and not prefix.startswith("/"):
            prefix = "/" + prefix
        router.url_prefix = prefix
        cls._blueprints.append(router)

    @classmethod
    def get_all_routers(cls) -> List[Blueprint]:
        return cls._blueprints
