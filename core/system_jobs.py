"""
System Jobs Registration for SoulSync

This module registers periodic system maintenance jobs with the global job_queue.
System jobs run automatically at configured intervals and handle core operations like:
- Database updates (sync from media server)
- Health checks
- Cleanup tasks
"""

import base64
from collections import defaultdict

from core.tiered_logger import get_logger
from core.settings import config_manager
from core.job_queue import job_queue
from database.music_database import get_database
from database.config_database import get_config_database
from database.working_database import get_working_database, User, UserRating
from core.personalized_playlists import get_personalized_playlists_service
from services.library_hygiene import DuplicateHygieneService
from core.suggestion_engine.deletion import process_lifecycle_actions

logger = get_logger("system_jobs")


def _decode_artist_from_sync_id(sync_id: str) -> str:
    """Decode artist from base sync identity ss:track:meta:{base64(artist|title)}."""
    raw = str(sync_id or "").strip()
    if not raw.startswith("ss:track:meta:"):
        return ""

    encoded = raw.split("ss:track:meta:", 1)[1].split("?", 1)[0].strip()
    if not encoded:
        return ""

    try:
        padded = encoded + "=" * ((4 - len(encoded) % 4) % 4)
        decoded = base64.b64decode(padded.encode("ascii")).decode("utf-8", errors="ignore")
        artist, _title = decoded.split("|", 1)
        return artist.strip()
    except Exception:
        return ""


def _get_top_listened_artists(limit: int = 5):
    """Return top listened artist names across all active managed users."""
    config_db = get_config_database()
    working_db = get_working_database()

    plex_service_id = config_db.get_or_create_service_id("plex")
    active_accounts = config_db.get_accounts(service_id=plex_service_id, is_active=True)
    if not active_accounts:
        return []

    artist_play_counts = defaultdict(int)

    with working_db.session_scope() as session:
        active_user_ids = set()
        for account in active_accounts:
            plex_user_id = str(account.get("user_id") or "").strip()
            account_name = str(account.get("display_name") or account.get("account_name") or "").strip()

            user = None
            if plex_user_id:
                user = session.query(User).filter(User.provider_identifier == plex_user_id).first()
            if not user and account_name:
                user = session.query(User).filter(User.username == account_name).first()

            if user:
                active_user_ids.add(user.id)

        if not active_user_ids:
            return []

        rows = (
            session.query(UserRating.sync_id, UserRating.play_count)
            .filter(
                UserRating.user_id.in_(list(active_user_ids)),
                UserRating.play_count > 0,
            )
            .all()
        )

        for sync_id, play_count in rows:
            artist = _decode_artist_from_sync_id(sync_id)
            if not artist:
                continue
            artist_play_counts[artist] += int(play_count or 0)

    ranked = sorted(artist_play_counts.items(), key=lambda item: item[1], reverse=True)
    return [artist for artist, _count in ranked[:limit]]


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
            
            # Create and run worker — run() is a blocking synchronous call executed
            # directly on the JobQueue worker thread; no additional thread needed.
            try:
                worker = DatabaseUpdateWorker(
                    media_client=provider,
                    database_path=None,  # Use default path
                    full_refresh=False,  # Incremental by default for scheduled updates
                    server_type=active_server,
                    force_sequential=True
                )

                worker.run()

                logger.info(
                    f"Database update completed: {worker.processed_tracks} tracks, "
                    f"{worker.successful_operations} successful, {worker.failed_operations} failed"
                )

                # After syncing the library, kick off a metadata enhancement pass so
                # newly-imported tracks don't wait up to 24 h for the daily job.
                if worker.successful_operations > 0:
                    try:
                        from services.metadata_enhancer import get_metadata_enhancer
                        logger.info("Database update: triggering post-import metadata enhancement pass")
                        get_metadata_enhancer().enhance_library_metadata(batch_size=50)
                    except Exception as _enhance_err:
                        logger.warning(f"Post-import metadata enhancement failed: {_enhance_err}")

            except Exception as e:
                logger.error(f"Failed to run database update worker: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Database update job error: {e}", exc_info=True)
    
    # Register with job_queue
    job_queue.register_job(
        name="database_update",
        func=run_database_update,
        interval_seconds=interval_seconds,
        start_after=600,  # 10-minute startup delay so all plugins initialise before first sync
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
        start_after=600,  # 10-minute startup delay — avoids hammering Plex/Jellyfin during boot
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

            try:
                from core.suggestion_engine.discovery import discover_tracks

                top_artists = _get_top_listened_artists(limit=5)
                if top_artists:
                    logger.info(
                        "Running pre-playlist discovery for top artists: %s",
                        ", ".join(top_artists),
                    )
                    for artist_name in top_artists:
                        try:
                            discover_tracks(artist_name)
                        except Exception as discover_error:
                            logger.warning(
                                f"Discovery failed for artist '{artist_name}': {discover_error}",
                                exc_info=True,
                            )
                else:
                    logger.info("No active-user listening history available for discovery warm-up")
            except Exception as discovery_stage_error:
                logger.warning(
                    f"Pre-playlist discovery stage failed: {discovery_stage_error}",
                    exc_info=True,
                )

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


def register_duplicate_scan_job(interval_seconds: int = 86400, enabled: bool = True):
    """Register daily duplicate scan job for library hygiene."""

    def run_duplicate_scan():
        try:
            logger.info("Starting duplicate scan job")
            service = DuplicateHygieneService()
            result = service.find_duplicates()
            auto_count = len((result or {}).get("auto_resolve", []))
            manual_count = len((result or {}).get("manual_review", []))
            logger.info(
                f"Duplicate scan complete: auto_resolve_groups={auto_count}, manual_review_groups={manual_count}"
            )
        except Exception as e:
            logger.error(f"Duplicate scan job failed: {e}", exc_info=True)

    job_queue.register_job(
        name="duplicate_scan_job",
        func=run_duplicate_scan,
        interval_seconds=interval_seconds,
        enabled=enabled,
        tags=["system", "duplicates", "hygiene"],
        max_retries=1,
    )

    logger.info(
        f"Duplicate scan job registered "
        f"(interval: {interval_seconds}s = {interval_seconds/3600:.1f}h, enabled={enabled})"
    )


def register_stale_track_scan_job(interval_seconds: int = 604800, enabled: bool = True):
    """Register weekly stale track scan job for library hygiene."""

    def run_stale_track_scan():
        try:
            logger.info("Starting stale track scan job")
            service = DuplicateHygieneService()
            result = service.scan_for_stale_tracks(inactive_days=90)
            logger.info(f"Stale track scan complete: {result}")
        except Exception as e:
            logger.error(f"Stale track scan job failed: {e}", exc_info=True)

    job_queue.register_job(
        name="stale_track_scan_job",
        func=run_stale_track_scan,
        interval_seconds=interval_seconds,
        enabled=enabled,
        tags=["system", "stale_tracks", "hygiene"],
        max_retries=1,
    )

    logger.info(
        f"Stale track scan job registered "
        f"(interval: {interval_seconds}s = {interval_seconds/3600:.1f}h, enabled={enabled})"
    )


def register_process_lifecycle_actions_job(interval_seconds: int = 86400, enabled: bool = True):
    """Register daily lifecycle queue processing job."""

    def run_process_lifecycle_actions():
        try:
            logger.info("Starting lifecycle action processing job")
            summary = process_lifecycle_actions()
            logger.info(f"Lifecycle processing complete: {summary}")
        except Exception as e:
            logger.error(f"Lifecycle processing job failed: {e}", exc_info=True)

    job_queue.register_job(
        name="process_lifecycle_actions",
        func=run_process_lifecycle_actions,
        interval_seconds=interval_seconds,
        enabled=enabled,
        tags=["system", "lifecycle", "suggestion_engine"],
        max_retries=1,
    )

    logger.info(
        f"Lifecycle processing job registered "
        f"(interval: {interval_seconds}s = {interval_seconds/3600:.1f}h, enabled={enabled})"
    )


def register_download_manager_queue_job(interval_seconds: int = 21600, enabled: bool = True):
    """Register the download manager queue processing job (every 6 hours)."""
    try:
        from services.download_manager import register_download_manager_job
        register_download_manager_job(interval_seconds=interval_seconds)
        logger.info(
            f"Download manager queue job registered "
            f"(interval: {interval_seconds}s = {interval_seconds / 3600:.1f}h, enabled={enabled})"
        )
    except Exception as e:
        logger.error(f"Failed to register download_manager_queue job: {e}", exc_info=True)


def register_user_history_sync_job(interval_seconds: int = 43200, enabled: bool = True):
    """Register periodic user history sync job (every 12 hours)."""

    def run_user_history_sync():
        try:
            logger.info("Starting scheduled user history sync job")
            from services.user_history_service import UserHistoryService
            stats = UserHistoryService().sync_baseline_history()
            logger.info(f"User history sync complete: {stats}")
        except Exception as e:
            logger.error(f"User history sync job failed: {e}", exc_info=True)

    job_queue.register_job(
        name="user_history_sync",
        func=run_user_history_sync,
        interval_seconds=interval_seconds,
        start_after=600,  # 10-minute startup delay — avoids Plex API calls during boot
        enabled=enabled,
        tags=["system", "user_history", "suggestion_engine"],
        max_retries=1,
    )

    logger.info(
        f"User history sync job registered "
        f"(interval: {interval_seconds}s = {interval_seconds / 3600:.1f}h, enabled={enabled})"
    )


def register_retroactive_metadata_enhancement_job(interval_seconds: int = 86400, enabled: bool = True, batch_size: int = 100):
    """Register a daily job to fill in missing MusicBrainz IDs for library tracks."""

    def run_metadata_enhancement():
        try:
            logger.info("Starting scheduled retroactive metadata enhancement job")
            from services.metadata_enhancer import get_metadata_enhancer
            # full_refresh=True is required so that tracks with a NULL / NOT_FOUND
            # musicbrainz_id are sent through the full AcoustID + MusicBrainz
            # identification pipeline.  Without this flag the enhancer only runs
            # the plugin-stamp (CJK) pass and never actually identifies tracks.
            get_metadata_enhancer().enhance_library_metadata(batch_size=batch_size, full_refresh=True)
            logger.info("Retroactive metadata enhancement job complete")
        except Exception as e:
            logger.error(f"Retroactive metadata enhancement job failed: {e}", exc_info=True)

    job_queue.register_job(
        name="retroactive_metadata_enhancement",
        func=run_metadata_enhancement,
        interval_seconds=interval_seconds,
        enabled=enabled,
        tags=["system", "metadata", "library"],
        max_retries=1,
    )

    logger.info(
        f"Retroactive metadata enhancement job registered "
        f"(interval: {interval_seconds}s = {interval_seconds / 3600:.1f}h, enabled={enabled}, batch_size={batch_size})"
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

        # Daily duplicate scan for hygiene signals.
        register_duplicate_scan_job(interval_seconds=86400, enabled=True)

        # Weekly stale track scan for hygiene signals.
        register_stale_track_scan_job(interval_seconds=604800, enabled=True)

        # Daily lifecycle staging queue processing.
        register_process_lifecycle_actions_job(interval_seconds=86400, enabled=True)

        # Download manager queue processing (every 6 hours).
        register_download_manager_queue_job(interval_seconds=21600, enabled=True)

        # User history sync for Suggestion Engine baseline data (every 12 hours).
        register_user_history_sync_job(interval_seconds=43200, enabled=True)

        # Daily retroactive metadata enhancement for tracks missing MusicBrainz IDs.
        register_retroactive_metadata_enhancement_job(interval_seconds=86400, enabled=True)

        logger.info("All system jobs registered successfully")
    except Exception as e:
        logger.error(f"Failed to register system jobs: {e}", exc_info=True)
