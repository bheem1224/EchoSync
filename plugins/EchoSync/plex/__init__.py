from .client import PlexClient
from .routes import bp

ProviderClass = PlexClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']

from core.nexus_framework.plugin_SDK import sdk

def check_plex_health():
    server_url = sdk.config.get("server_url")
    if not server_url:
        return False, "Plex server_url not configured"
    
    import requests
    try:
        resp = requests.get(f"{server_url.rstrip('/')}/identity", timeout=5)
        if resp.status_code == 200:
            return True, "Plex server reachable"
        return False, f"Plex returned {resp.status_code}"
    except Exception as e:
        return False, str(e)

sdk.health.register(check_plex_health, interval_seconds=300)
