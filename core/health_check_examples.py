"""
Health Check Integration Examples

This file demonstrates how to use the integrated health check system with job_queue.

Key Points:
1. Health checks are registered globally and executed by job_queue
2. Each check has a default 60-second interval that can be overridden
3. Use register_health_check() for manual/one-off checks
4. Use register_health_check_job() for periodic checks via job_queue
5. job_queue must be started for periodic checks to run
6. All results are cached and available via the /api/health endpoint
"""

from core.health_check import (
    HealthCheckResult,
    register_health_check,
    register_health_check_job,
    run_health_check,
    run_all_health_checks,
)
from core.job_queue import start_job_queue, stop_job_queue


# Example 1: Simple Plex health check
def check_plex_connection() -> HealthCheckResult:
    """Check if Plex server is reachable."""
    try:
        from providers.plex.client import PlexClient
        
        client = PlexClient()
        # Verify connection to Plex server
        connected = client.ensure_connection()
        
        if connected:
            return HealthCheckResult(
                service_name="plex",
                status="healthy",
                message="Plex server is reachable",
                details={"server": "connected"}
            )
        else:
            return HealthCheckResult(
                service_name="plex",
                status="unhealthy",
                message="Plex server connection failed",
                details={"error": "connection_failed"}
            )
    except Exception as e:
        return HealthCheckResult(
            service_name="plex",
            status="unhealthy",
            message=f"Plex connection error: {str(e)}",
            details={"error": str(e)}
        )


# Example 2: Database health check
def check_database_connection() -> HealthCheckResult:
    """Check if database is accessible."""
    try:
        from database.music_database import get_database
        
        # Get database instance for this thread
        db = get_database()
        
        # Try a query to verify database is working
        stats = db.get_statistics()
        
        return HealthCheckResult(
            service_name="database",
            status="healthy",
            message=f"Database is accessible",
            details={"artist_count": stats.get('artists', 0), "track_count": stats.get('tracks', 0)}
        )
    except Exception as e:
        return HealthCheckResult(
            service_name="database",
            status="unhealthy",
            message=f"Database connection failed: {str(e)}",
            details={"error": str(e)}
        )


# Example 3: Soulseek health check (more frequent for debug mode)
def check_soulseek_connection() -> HealthCheckResult:
    """Check if Soulseek client is available and can be instantiated."""
    try:
        from providers.soulseek.client import SoulseekClient
        
        # Attempt to instantiate Soulseek client
        # If it fails, credentials are missing or invalid
        client = SoulseekClient()
        
        return HealthCheckResult(
            service_name="soulseek",
            status="healthy",
            message="Soulseek client is available and configured",
            details={"available": True}
        )
    except Exception as e:
        # Check if it's a configuration error or connection error
        error_msg = str(e).lower()
        if 'config' in error_msg or 'credential' in error_msg or 'not found' in error_msg:
            return HealthCheckResult(
                service_name="soulseek",
                status="degraded",
                message="Soulseek is not configured",
                details={"error": "not_configured"}
            )
        else:
            return HealthCheckResult(
                service_name="soulseek",
                status="unhealthy",
                message=f"Soulseek check failed: {str(e)}",
                details={"error": str(e)}
            )


def setup_health_checks(debug_mode: bool = False):
    """
    Setup all health checks.
    
    Called during application startup to register health checks.
    
    Args:
        debug_mode: If True, health checks run more frequently
    """
    # Standard checks (60 second interval)
    register_health_check_job("plex", check_plex_connection, interval_seconds=60)
    register_health_check_job("database", check_database_connection, interval_seconds=60)
    
    # Soulseek check (more frequent in debug mode)
    soulseek_interval = 30 if debug_mode else 120
    register_health_check_job(
        "soulseek",
        check_soulseek_connection,
        interval_seconds=soulseek_interval,
        max_retries=2  # Retry twice before marking unhealthy
    )


def initialize_health_system(debug_mode: bool = False):
    """
    Initialize the health check system and start job_queue.
    
    Call this once during application startup.
    
    Args:
        debug_mode: If True, health checks run more frequently
    """
    # Register all health checks
    setup_health_checks(debug_mode=debug_mode)
    
    # Start job_queue to execute periodic health checks
    start_job_queue()
    
    print("[HEALTH] Health check system initialized")


def shutdown_health_system():
    """
    Shutdown the health check system.
    
    Call this during application shutdown.
    """
    stop_job_queue()
    print("[HEALTH] Health check system shutdown")


# Usage Example in Flask app initialization:
# ============================================
# def create_app():
#     app = Flask(__name__)
#     
#     # Initialize health checks
#     initialize_health_system(debug_mode=os.getenv('DEBUG') == 'true')
#     
#     # Health endpoint will automatically serve cached results
#     # GET /api/health returns the last cached results for all checks
#     
#     return app
#
#
# if __name__ == '__main__':
#     app = create_app()
#     try:
#         app.run()
#     finally:
#         shutdown_health_system()


# Manual Check Example:
# ====================
# To run a single health check manually without scheduling:
#
# result = run_health_check("plex")
# if result:
#     print(f"Plex status: {result.status}")
#     print(f"Message: {result.message}")
#     print(f"Response time: {result.response_time_ms}ms")
#
#
# To run all registered checks at once:
#
# results = run_all_health_checks()
# for service_name, result in results.items():
#     print(f"{service_name}: {result.status} - {result.message}")
