from .client import SlskdProvider
from .routes import bp

ProviderClass = SlskdProvider
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']

from core.nexus_framework.plugin_SDK import sdk

def check_slskd_health():
    server_url = sdk.config.get("slskd_url")
    if not server_url:
        return False, "Slskd URL not configured"
    
    import requests
    try:
        resp = requests.get(f"{server_url.rstrip('/')}/api/v0/application", timeout=5)
        # Even 401 means it's reachable.
        if resp.status_code in [200, 401]:
            return True, "Slskd reachable"
        return False, f"Slskd returned {resp.status_code}"
    except Exception as e:
        return False, str(e)

sdk.health.register(check_slskd_health, interval_seconds=300)
