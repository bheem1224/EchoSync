from core.health_check import health_check_registry
from core.settings import config_manager
from typing import Dict, Any
from core.tiered_logger import get_logger

logger = get_logger("health_check")

def get_system_health() -> Dict[str, Any]:
    """
    Calculate overall system health, total services, and operational services.

    Logic:
    - Core System (Database + Task Queue) is always the first service.
    - Total Services = 1 (Core) + Count(Enabled Providers).
    - Operational Services = (1 if Core is healthy) + Count(Healthy Enabled Providers).

    Returns:
        Dict with keys: status, results, timestamp, summary
    """
    # Get all cached health check results from the registry
    results = health_check_registry.get_all_last_results()

    # 1. Determine Core Health
    # We check if the database is accessible. If so, Core is healthy.
    core_healthy = False
    core_message = "Database connection failed"
    try:
        from database import get_database
        db = get_database()
        # Simple query to check connection
        # db.session_scope() handles session creation/closing
        with db.session_scope() as session:
            session.execute(text("SELECT 1"))
        core_healthy = True
        core_message = "Core services operational"
    except NameError:
        # Fallback if 'text' is not imported, though SQLAlchemy usually requires it for raw strings
        try:
             from sqlalchemy import text
             from database import get_database
             db = get_database()
             with db.session_scope() as session:
                session.execute(text("SELECT 1"))
             core_healthy = True
             core_message = "Core services operational"
        except Exception as e:
             logger.error(f"Core health check failed (fallback): {e}")
             core_message = str(e)
    except Exception as e:
        logger.error(f"Core health check failed: {e}")
        core_message = str(e)

    # 2. Count Enabled Providers
    disabled_providers = config_manager.get_disabled_providers()
    enabled_providers_count = 0

    # Check Spotify
    if 'spotify' not in disabled_providers:
        creds = config_manager.get_spotify_config()
        active = config_manager.get_active_spotify_account()
        if (creds.get('client_id') and creds.get('client_secret')) or active:
            enabled_providers_count += 1

    # Check Plex
    if 'plex' not in disabled_providers:
        from database.config_database import get_config_database
        config_db = get_config_database()
        plex_id = config_db.get_or_create_service_id('plex')
        plex_url = config_db.get_service_config(plex_id, 'base_url') or config_db.get_service_config(plex_id, 'server_url')
        plex_token = config_db.get_service_config(plex_id, 'token')

        if plex_url and plex_token:
            enabled_providers_count += 1

    # Check Jellyfin
    if 'jellyfin' not in disabled_providers:
        conf = config_manager.get_jellyfin_config()
        if conf.get('base_url') and conf.get('api_key'):
            enabled_providers_count += 1

    # Check Navidrome
    if 'navidrome' not in disabled_providers:
        conf = config_manager.get_navidrome_config()
        if conf.get('base_url') and conf.get('username'):
            enabled_providers_count += 1

    # Check Soulseek (slskd)
    if 'soulseek' not in disabled_providers and 'slskd' not in disabled_providers:
        from database.config_database import get_config_database
        config_db = get_config_database()
        slskd_id = config_db.get_or_create_service_id('soulseek')
        slskd_url = config_db.get_service_config(slskd_id, 'slskd_url') or config_db.get_service_config(slskd_id, 'server_url')
        api_key = config_db.get_service_config(slskd_id, 'api_key')

        if slskd_url and api_key:
            enabled_providers_count += 1

    # Check LRClib (bundled, usually enabled unless explicitly disabled)
    if 'lrclib' not in disabled_providers:
         # It's enabled by default in the backend startup logic if not disabled
         enabled_providers_count += 1

    # 3. Calculate Operational Services
    # Start with Core
    operational_count = 1 if core_healthy else 0

    # Add healthy providers from registry results
    # We only count them if they are in the enabled list logic above (implicitly, by being in results)
    # But strictly speaking, results only contains *running* providers.
    # So if a provider is enabled but failed to start, it might not be in results, or it might be there with 'unhealthy'.

    for res in results.values():
        if res.status == 'healthy':
            operational_count += 1

    # 4. Construct Results Dictionary
    results_dict = {
        "core": {
            "status": "healthy" if core_healthy else "unhealthy",
            "message": core_message,
            "details": {"component": "database"},
            "timestamp": None,
            "response_time_ms": 0
        }
    }

    # Merge provider results
    for service_name, result in results.items():
        results_dict[service_name] = {
            "status": result.status,
            "message": result.message,
            "details": result.details,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
            "response_time_ms": result.response_time_ms
        }

    # 5. Determine Overall Status
    overall_status = "healthy"
    if not core_healthy:
        overall_status = "unhealthy"
    else:
        # Check if any *enabled* provider is unhealthy
        # If a provider is missing from results but enabled, it's implicitly 'unknown' or 'starting',
        # but technically not 'unhealthy' yet unless we track start failures.
        # For now, we degrade if any reported result is unhealthy.
        for result in results.values():
            if result.status == "unhealthy":
                overall_status = "degraded"
                break

    # Total services = Core (1) + Enabled Providers
    total_services = 1 + enabled_providers_count

    return {
        "status": overall_status,
        "results": results_dict,
        "timestamp": None,
        "summary": {
            "total": total_services,
            "operational": operational_count
        }
    }
