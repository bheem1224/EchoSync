from core.health_check import health_check_registry
from core.settings import config_manager
from typing import Dict, Any

def get_system_health() -> Dict[str, Any]:
    """
    Calculate overall system health, total services, and operational services.

    Returns:
        Dict with keys: status, results, timestamp, summary
    """
    # Get all cached health check results
    results = health_check_registry.get_all_last_results()

    # Convert to JSON-serializable format
    results_dict = {}
    for service_name, result in results.items():
        results_dict[service_name] = {
            "status": result.status,
            "message": result.message,
            "details": result.details,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
            "response_time_ms": result.response_time_ms
        }

    # Calculate counts
    # We define "total services" as providers that are enabled and configured.
    # Since we modified backend_entry.py to only start enabled/configured services,
    # and those services register their health checks, the keys in 'results'
    # largely represent the enabled services.

    # However, to be more precise according to specs:
    # "total_services should calculate count(providers where enabled == True)"

    # Let's count enabled providers from config
    disabled_providers = config_manager.get_disabled_providers()

    # List of known providers we care about for stats
    # (In a real plugin system this might be dynamic, but for now we list core ones)
    known_providers = ['spotify', 'plex', 'jellyfin', 'navidrome', 'soulseek', 'slskd']

    # Also check if they are configured
    # We can use config_manager.is_configured() but that checks EVERYTHING.
    # We want per-provider check.

    enabled_count = 0

    # Check Spotify
    if 'spotify' not in disabled_providers:
        creds = config_manager.get_spotify_config()
        active = config_manager.get_active_spotify_account()
        if (creds.get('client_id') and creds.get('client_secret')) or active:
            enabled_count += 1

    # Check Plex
    if 'plex' not in disabled_providers:
        conf = config_manager.get_plex_config()
        if conf.get('base_url') and conf.get('token'):
            enabled_count += 1

    # Check Jellyfin
    if 'jellyfin' not in disabled_providers:
        conf = config_manager.get_jellyfin_config()
        if conf.get('base_url') and conf.get('api_key'):
            enabled_count += 1

    # Check Navidrome
    if 'navidrome' not in disabled_providers:
        conf = config_manager.get_navidrome_config()
        if conf.get('base_url') and conf.get('username'):
            enabled_count += 1

    # Check Soulseek
    if 'soulseek' not in disabled_providers and 'slskd' not in disabled_providers:
        conf = config_manager.get_soulseek_config()
        if conf.get('slskd_url') and conf.get('api_key'):
            enabled_count += 1

    # Operational = Status is 'healthy'
    operational_count = 0
    for res in results.values():
        if res.status == 'healthy':
            operational_count += 1

    # Overall status logic
    overall_status = "healthy"
    for result in results.values():
        if result.status == "unhealthy":
            overall_status = "degraded"
            break

    # If we have enabled services but 0 results (startup), status might be unknown
    if enabled_count > 0 and len(results) == 0:
        overall_status = "unknown"

    return {
        "status": overall_status,
        "results": results_dict,
        "timestamp": None,
        "summary": {
            "total": enabled_count,
            "operational": operational_count
        }
    }
