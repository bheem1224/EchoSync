from core.health_check import health_check_registry
from core.settings import config_manager
from typing import Dict, Any
import logging

# Ensure logger is set up
logger = logging.getLogger("health_check")

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
    disabled_providers = config_manager.get('disabled_providers', [])
    enabled_providers_count = 0

    from database.config_database import get_config_database
    config_db = get_config_database()

    # Check Spotify
    if 'spotify' not in disabled_providers:
        spotify_id = config_db.get_or_create_service_id('spotify')
        spotify_creds = config_db.get_all_service_config(spotify_id) or {}
        spotify_accounts = config_db.get_accounts(service_id=spotify_id, is_active=True)
        if (spotify_creds.get('client_id') and spotify_creds.get('client_secret')) or spotify_accounts:
            enabled_providers_count += 1

    # Check Plex
    if 'plex' not in disabled_providers:
        plex_id = config_db.get_or_create_service_id('plex')
        plex_url = config_db.get_service_config(plex_id, 'base_url') or config_db.get_service_config(plex_id, 'server_url')
        plex_token = config_db.get_service_config(plex_id, 'token')

        if plex_url and plex_token:
            enabled_providers_count += 1

    # Check Jellyfin
    if 'jellyfin' not in disabled_providers:
        jellyfin_id = config_db.get_or_create_service_id('jellyfin')
        jellyfin_creds = config_db.get_all_service_config(jellyfin_id) or {}
        if jellyfin_creds.get('base_url') and jellyfin_creds.get('api_key'):
            enabled_providers_count += 1

    # Check Navidrome
    if 'navidrome' not in disabled_providers:
        navidrome_id = config_db.get_or_create_service_id('navidrome')
        navidrome_creds = config_db.get_all_service_config(navidrome_id) or {}
        if navidrome_creds.get('base_url') and navidrome_creds.get('username'):
            enabled_providers_count += 1

    # Check Soulseek (slskd)
    if 'soulseek' not in disabled_providers and 'slskd' not in disabled_providers:
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

    # 6. Library Statistics
    library_data = {}
    try:
        from database.music_database import get_database
        db = get_database()
        tracks = db.count_tracks()
        albums = db.count_albums()
        storage_bytes = db.get_total_storage_used()
        
        # Format storage
        if storage_bytes <= 0:
            storage_str = "0 B"
        else:
            import math
            units = ("B", "KB", "MB", "GB", "TB")
            i = int(math.floor(math.log(storage_bytes, 1024)))
            p = math.pow(1024, i)
            s = round(storage_bytes / p, 1)
            storage_str = f"{s} {units[i]}"

        library_data = {
            "total_tracks": tracks,
            "total_albums": albums,
            "storage_used": storage_str
        }
    except Exception as e:
        logger.error(f"Failed to get library stats for health check: {e}")

    return {
        "status": overall_status,
        "results": results_dict,
        "timestamp": None,
        "summary": {
            "total": total_services,
            "operational": operational_count
        },
        "library": library_data
    }
