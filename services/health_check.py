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
    disabled_plugins = config_manager.get_disabled_plugins()
    if disabled_plugins is None:
        disabled_plugins = []
    disabled_set = {d.lower() for d in disabled_plugins}
    enabled_providers_count = 0

    from database.config_database import get_config_database
    config_db = get_config_database()

    active_services = []
    try:
        with config_db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM services WHERE is_active = 1 AND name != 'system'")
            active_services = [row['name'] for row in c.fetchall()]
    except Exception as e:
        logger.error(f"Failed to fetch active services for health check: {e}")

    from core.nexus_framework.plugin_loader import PluginRegistry
    for svc_name in active_services:
        clean_name = svc_name.split('.')[-1].split('@')[0].lower()
        if clean_name in disabled_set or svc_name.lower() in disabled_set:
            continue

        try:
            instance = PluginRegistry.create_instance(svc_name)
            if instance:
                if instance.is_configured():
                    enabled_providers_count += 1
                elif clean_name == 'lrclib':
                    enabled_providers_count += 1
        except Exception as e:
            pass

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
