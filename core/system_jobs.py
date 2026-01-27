"""
System Jobs Registration for SoulSync

This module registers periodic system maintenance jobs with the global job_queue.
System jobs run automatically at configured intervals and handle core operations like:
- Database updates (sync from media server)
- Health checks
- Cleanup tasks
"""

from core.tiered_logger import get_logger
from core.settings import config_manager
from core.job_queue import job_queue

logger = get_logger("system_jobs")


def register_database_update_job(interval_seconds: int = 86400):
    """
    Register a periodic database update job that syncs library data from the active media server.
    
    Args:
        interval_seconds: How often to run database updates (default 24 hours = 86400s)
    """
    def run_database_update():
        """Execute a database update from the active media server"""
        try:
            logger.info("Starting scheduled database update job")
            
            # Get active media server
            try:
                active_server = config_manager.get_active_media_server()
            except Exception as e:
                logger.error(f"Failed to get active media server: {e}")
                return
            
            if not active_server:
                logger.warning("No active media server configured, skipping database update")
                return
            
            # Get provider instance
            provider = None
            try:
                from core.provider import ProviderRegistry
                provider = ProviderRegistry.create_instance(active_server)
            except Exception as e:
                logger.error(f"Failed to create provider instance for {active_server}: {e}", exc_info=True)
                return
            
            if not provider:
                logger.error(f"Media server '{active_server}' not available")
                return
            
            # Ensure connection
            try:
                if not provider.ensure_connection():
                    logger.error(f"Could not connect to {active_server}")
                    return
            except Exception as e:
                logger.error(f"Connection failed for {active_server}: {e}")
                return
            
            # Import DatabaseUpdateWorker
            try:
                from core.database_update_worker import DatabaseUpdateWorker
            except ImportError as e:
                logger.error(f"Failed to import DatabaseUpdateWorker: {e}")
                return
            
            # Create and run worker
            try:
                worker = DatabaseUpdateWorker(
                    media_client=provider,
                    database_path=None,  # Use default path
                    full_refresh=False,  # Incremental by default for scheduled updates
                    server_type=active_server,
                    force_sequential=True
                )
                
                # Start worker thread
                worker.start()
                worker.join(timeout=3600)  # 1 hour timeout
                
                if worker.is_alive():
                    logger.warning("Database update worker still running after 1 hour, may be stuck")
                else:
                    logger.info(
                        f"Database update completed: {worker.processed_tracks} tracks, "
                        f"{worker.successful_operations} successful, {worker.failed_operations} failed"
                    )
                    
            except Exception as e:
                logger.error(f"Failed to run database update worker: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Database update job error: {e}", exc_info=True)
    
    # Register with job_queue
    job_queue.register_job(
        name="database_update",
        func=run_database_update,
        interval_seconds=interval_seconds,
        enabled=False,  # Disabled by default, users can enable via UI
        tags=["system", "database"],
        max_retries=2
    )
    
    logger.info(f"Database update job registered (interval: {interval_seconds}s = {interval_seconds/3600:.1f}h, disabled by default)")


def register_all_system_jobs():
    """
    Register all system jobs with the global job_queue.
    Called during application startup.
    """
    try:
        # Database update job (24h interval, disabled by default)
        register_database_update_job(interval_seconds=86400)
        
        # Media scan update job (5min interval, disabled by default)
        # Note: Actual scanning requires MediaScanManager instance
        def media_scan_placeholder():
            """Placeholder - actual scanning requires MediaScanManager instance"""
            logger.info("Media scan job triggered (requires MediaScanManager instance for active scanning)")
        
        job_queue.register_job(
            name="media_scan_update",
            func=media_scan_placeholder,
            interval_seconds=300,  # 5 minutes
            enabled=False,  # Disabled by default
            tags=["system", "media_scan"]
        )
        logger.info("Media scan update job registered (interval: 5m, disabled by default)")
        
        logger.info("All system jobs registered successfully")
    except Exception as e:
        logger.error(f"Failed to register system jobs: {e}", exc_info=True)
