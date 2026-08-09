from .client import TidalClient
from .routes import router
from . import oauth_routes

ProviderClass = TidalClient
RouteBlueprint = router
RouteBlueprint2 = oauth_routes.router

__all__ = ['ProviderClass', 'RouteBlueprint', 'RouteBlueprint2']

from core.nexus_framework.plugin_SDK import sdk

def check_tidal_health():
    import requests
    try:
        resp = requests.get("https://api.tidal.com/v1/", timeout=5)
        if resp.status_code in [401, 200, 404]:
            return True, "Tidal API reachable"
        return False, f"API returned {resp.status_code}"
    except Exception as e:
        return False, str(e)

sdk.health.register(check_tidal_health, interval_seconds=300)
