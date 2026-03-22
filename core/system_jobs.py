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
from database.music_database import get_database
from core.personalized_playlists import get_personalized_playlists_service

logger = get_logger("system_jobs")


def register_database_update_job(interval_seconds: int = 21600, enabled: bool = True):
    """
    Register a periodic database update job that syncs library data from the active media server.
    
    Args:
        interval_seconds: How often to run database updates (default 6 hours = 21600s)
        enabled: Whether the job should be enabled by default.
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
        enabled=enabled,
        tags=["system", "database"],
        max_retries=2
    )
    
    logger.info(
        f"Database update job registered "
        f"(interval: {interval_seconds}s = {interval_seconds/3600:.1f}h, enabled={enabled})"
    )


def register_media_server_scan_job(interval_seconds: int = 10800, enabled: bool = True):
    """Register periodic media server scan job.

    Runs more frequently than database_update so new files are recognized by the media server
    before incremental DB sync jobs run.
    """

    def run_media_server_scan():
        try:
            logger.info("Starting scheduled media server scan job")

            from core.provider import ProviderRegistry

            active_server = config_manager.get_active_media_server()
            if not active_server:
                logger.warning("No active media server configured, skipping media scan")
                return

            provider = ProviderRegistry.create_instance(active_server)
            if not provider:
                logger.error(f"Could not create provider instance for active server '{active_server}'")
                return

            if hasattr(provider, "ensure_connection") and not provider.ensure_connection():
                logger.error(f"Could not connect to active media server '{active_server}'")
                return

            triggered = False

            # Preferred path for MediaServerProvider implementations.
            if hasattr(provider, "trigger_library_scan"):
                try:
                    triggered = bool(provider.trigger_library_scan("Music"))
                except TypeError:
                    # Some providers accept no args.
                    triggered = bool(provider.trigger_library_scan())

            # Fallback for Plex client implementation.
            if not triggered and getattr(provider, "music_library", None) is not None:
                section = getattr(provider, "music_library", None)
                if section is not None and hasattr(section, "update"):
                    section.update()
                    triggered = True

            if triggered:
                logger.info(f"Media server scan triggered successfully for '{active_server}'")
            else:
                logger.warning(f"Media server scan trigger not supported or failed for '{active_server}'")
        except Exception as e:
            logger.error(f"Media server scan job failed: {e}", exc_info=True)

    job_queue.register_job(
        name="media_server_scan",
        func=run_media_server_scan,
        interval_seconds=interval_seconds,
        enabled=enabled,
        tags=["system", "media_scan"],
        max_retries=1,
    )

    logger.info(
        f"Media server scan job registered "
        f"(interval: {interval_seconds}s = {interval_seconds/3600:.1f}h, enabled={enabled})"
    )


def register_suggestion_engine_playlist_job(interval_seconds: int = 86400, enabled: bool = True):
    """Register daily suggestion playlist generation job (Phase 5)."""

    def run_suggestion_playlist_generation():
        try:
            logger.info("Starting daily suggestion playlist generation job")

            database = get_database()
            playlists_service = get_personalized_playlists_service(database, spotify_client=None)
            daily_mixes = playlists_service.get_all_daily_mixes(max_mixes=4)

            logger.info(
                "Suggestion playlist generation complete: "
                f"generated {len(daily_mixes)} daily mixes"
            )
        except Exception as e:
            logger.error(f"Suggestion playlist generation job failed: {e}", exc_info=True)

    job_queue.register_job(
        name="suggestion_engine_daily_playlists",
        func=run_suggestion_playlist_generation,
        interval_seconds=interval_seconds,
        enabled=enabled,
        tags=["system", "suggestion_engine", "playlists"],
        max_retries=1,
    )

    logger.info(
        f"Suggestion Engine daily playlist job registered "
        f"(interval: {interval_seconds}s = {interval_seconds/3600:.1f}h, enabled={enabled})"
    )


def register_all_system_jobs():
    """
    Register all system jobs with the global job_queue.
    Called during application startup.
    """
    try:
        # Database update should be enabled and run every 6 hours by default.
        register_database_update_job(interval_seconds=21600, enabled=True)

        # Media server scan should run every 3 hours (more frequently than DB update).
        register_media_server_scan_job(interval_seconds=10800, enabled=True)

        # Daily suggestion playlist generation (Phase 5).
        register_suggestion_engine_playlist_job(interval_seconds=86400, enabled=True)
        
        logger.info("All system jobs registered successfully")
    except Exception as e:
        logger.error(f"Failed to register system jobs: {e}", exc_info=True)
