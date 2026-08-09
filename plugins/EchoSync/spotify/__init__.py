from .client import SpotifyClient
from .routes import router

ProviderClass = SpotifyClient
RouteBlueprint = router

__all__ = ['ProviderClass', 'RouteBlueprint']

from core.nexus_framework.plugin_SDK import sdk

def check_spotify_health():
    import requests
    try:
        resp = requests.get("https://api.spotify.com/v1/", timeout=5)
        if resp.status_code in [401, 200, 404]:
            return True, "Spotify API reachable"
        return False, f"API returned {resp.status_code}"
    except Exception as e:
        return False, str(e)

sdk.health.register(check_spotify_health, interval_seconds=300)
