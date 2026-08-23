"""
System Jobs Registration for Echosync

This module registers periodic system maintenance jobs with the global job_queue.
System jobs run automatically at configured intervals and handle core operations like:
- Database updates (sync from media server)
- Health checks
- Cleanup tasks
"""

from typing import Optional, List, Dict, Any

import base64
from collections import defaultdict

from core.tiered_logger import get_logger
from core.settings import config_manager
from core.task_manager.task_queue import job_queue
from database.music_database import get_database
from database.working_database import get_working_database, Account, UserRating
from core.personalized_playlists import get_personalized_playlists_service
from services.library_hygiene import DuplicateHygieneService
from core.suggestion_engine.deletion import process_lifecycle_actions
from core.suggestion_engine.consensus import calculate_consensus
from core.jobs.reorganize_library_job import register_reorganize_library_job
from core.jobs.decouple_media_job import register_decouple_media_job

logger = get_logger("system_jobs")


def _decode_artist_from_sync_id(sync_id: str) -> str:
    """Decode artist from base sync identity (database lookup via sync_id)."""
    if not sync_id:
        return ""
    try:
        from database.music_database import Track
        db = get_database()
        with db.session_scope() as session:
            track = session.query(Track).filter_by(sync_id=sync_id).first()
            if track and track.artist:
                return track.artist.name.strip()
    except Exception:
        pass
    return ""


def _get_top_listened_artists(limit: int = 5):
    """Return top listened artist names across all active managed users."""
    config_db = get_config_database()
    working_db = get_working_database()

    # Get all active media servers
    from core.nexus_framework.plugin_loader import PluginRegistry
    active_servers = PluginRegistry.get_active_services_by_type('media_server')
    if not active_servers:
        return []

    active_user_ids = set()
    artist_play_counts = defaultdict(int)

    with working_db.session_scope() as session:
        for p_id in active_servers:
            plugin_cls = PluginRegistry.get_plugin_class(p_id)
            plugin_name = getattr(plugin_cls, 'name', str(p_id)) if plugin_cls else str(p_id)
            service_id = config_db.get_or_create_service_id(plugin_name)
            active_accounts = config_db.get_accounts(service_id=service_id, is_active=True)
            
            for account in active_accounts:
                provider_user_id = str(account.get("user_id") or "").strip()
                account_name = str(account.get("display_name") or account.get("account_name") or "").strip()

                user = None
                if provider_user_id:
                    user = session.query(User).filter(Account.provider_identifier == provider_user_id).first()
                if not user and account_name:
                    user = session.query(User).filter(Account.username == account_name).first()

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
    def run_database_update(full_refresh: bool = False, identifiers_only: bool = False, **kwargs):
        """Execute a database update, prioritizing Local Server first."""
        try:
            logger.info("Starting scheduled database update job")
            from core.nexus_framework.plugin_loader import PluginRegistry
            from services.library_sync_service import LibrarySyncService
            
            total_successful_operations = 0
            
            # Step 1: Run Local Server first if available
            from core.nexus_framework.plugin_loader import generate_plugin_id
            local_server_id = generate_plugin_id('echosync.local server')
            local_success = False
            
            if PluginRegistry.get_plugin_class(local_server_id) and not PluginRegistry.is_plugin_disabled(local_server_id):
                try:
                    local_provider = PluginRegistry.create_instance(local_server_id)
                    if local_provider:
                        can_connect = True
                        if hasattr(local_provider, 'authenticate'):
                            can_connect = local_provider.authenticate()
                            
                        if can_connect:
                            scan_mode = kwargs.get("scan_mode") or ("full_rebuild" if full_refresh else "incremental")
                            logger.info(f"Step 1: Running primary database update for local_server via LibrarySyncService (mode={scan_mode})")
                            worker = LibrarySyncService()
                            worker.sync_library(scan_mode=scan_mode)
                            total_successful_operations += 1
                            local_success = True
                except Exception as e:
                    logger.error(f"Failed to run primary local media server update: {e}", exc_info=True)
            else:
                logger.debug(f"Local server provider '{local_server_id}' not registered or disabled; skipping Step 1.")
            
            # Step 2: Run active media servers
            try:
                active_servers = []
                from database.config_database import get_config_database
                config_db = get_config_database()
                for p_id in PluginRegistry.get_plugins_by_type('mediaserver', exclude_disabled=True):
                    plugin_cls = PluginRegistry.get_plugin_class(p_id)
                    if not plugin_cls:
                        continue
                    caps = getattr(plugin_cls, 'capabilities', None)
                    if not caps or not getattr(caps, 'supports_library_scan', False):
                        continue

                    p_name = getattr(plugin_cls, 'name', '') or str(p_id)
                    svc_id = config_db.get_or_create_service_id(p_name)
                    has_acc = bool(config_db.get_accounts(service_id=svc_id))
                    has_url = bool(config_db.get_service_config(svc_id, 'server_url') or config_db.get_service_config(svc_id, 'url') or config_db.get_service_config(svc_id, 'host'))

                    if has_acc or has_url:
                        active_servers.append(p_id)
            except Exception as e:
                logger.error(f"Failed to get active media servers: {e}")
                active_servers = []
                
            for active_server in active_servers:
                if active_server == local_server_id:
                    continue
                    
                # Get provider instance
                provider = None
                try:
                    provider = PluginRegistry.create_instance(active_server)
                except Exception as e:
                    logger.error(f"Failed to create provider instance for {active_server}: {e}", exc_info=True)
                    continue
                
                if not provider:
                    logger.error(f"Media server '{active_server}' not available")
                    continue
                
                # Check if configured
                if hasattr(provider, 'is_configured') and not provider.is_configured():
                    logger.debug(f"Media server '{active_server}' is not configured; skipping.")
                    continue

                # Ensure connection
                try:
                    can_connect = True
                    if hasattr(provider, 'authenticate'):
                        can_connect = provider.authenticate()
                        
                    if not can_connect:
                        error_msg = f"Could not connect to {active_server}. Check your server status and credentials."
                        logger.error(error_msg)
                        from core.event_bus import event_bus
                        event_bus.publish("NOTIFICATION", {
                            "type": "error",
                            "title": "Media Server Connection Failed",
                            "message": error_msg
                        })
                        continue
                except Exception as e:
                    error_msg = f"Connection failed for {active_server}: {e}"
                    logger.error(error_msg)
                    from core.event_bus import event_bus
                    event_bus.publish("NOTIFICATION", {
                        "type": "error",
                        "title": "Media Server Connection Failed",
                        "message": error_msg
                    })
                    continue
                
                # Phase 2: Remote Syncs. If Phase 1 (Local Scan) succeeded, we only sync identifiers.
                # Otherwise, we run a full sync.
                identifiers_only = local_success
                
                logger.info(f"Step 2: Remote sync for {active_server} bypassed for delta transition")
                total_successful_operations += 1

        except Exception as e:
            logger.error(f"Error in scheduled database update job: {e}", exc_info=True)
    
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


def register_external_identifier_sync_job(interval_seconds: int = 21600, enabled: bool = True):
    """
    Register a standalone job that only fetches external identifiers from media servers.
    This runs as a follow-up to the main database update.
    """
    def run_external_identifier_sync(plugin_source: Optional[str] = None, **kwargs):
        try:
            logger.info("Starting external identifier sync job")
            from core.nexus_framework.plugin_loader import PluginRegistry, generate_plugin_id
            from database import get_database, _canonicalize_path
            from database.music_database import LocalMedia, ExternalIdentifier, Track, Artist
            from sqlalchemy import func
            from datetime import datetime, timezone
            from pathlib import Path
            from core.utils import PathMapper

            local_server_id = generate_plugin_id('echosync.local server')

            active_servers = []
            try:
                from database.config_database import get_config_database
                config_db = get_config_database()
                for p_id in PluginRegistry.get_plugins_by_type('mediaserver', exclude_disabled=True):
                    plugin_cls = PluginRegistry.get_plugin_class(p_id)
                    if not plugin_cls:
                        continue
                    caps = getattr(plugin_cls, 'capabilities', None)
                    if not caps or not getattr(caps, 'supports_library_scan', False):
                        continue

                    p_name = getattr(plugin_cls, 'name', '') or str(p_id)
                    svc_id = config_db.get_or_create_service_id(p_name)
                    has_acc = bool(config_db.get_accounts(service_id=svc_id))
                    has_url = bool(config_db.get_service_config(svc_id, 'server_url') or config_db.get_service_config(svc_id, 'url') or config_db.get_service_config(svc_id, 'host'))

                    if has_acc or has_url:
                        active_servers.append(p_id)
                    else:
                        logger.debug(f"Skipping unconfigured media server provider '{p_name}' for external identifier sync")
            except Exception as e:
                logger.error(f"Failed to get active media servers for external sync: {e}")

            db = get_database()

            for active_server in active_servers:
                if active_server == local_server_id:
                    continue

                provider = None
                try:
                    provider = PluginRegistry.create_instance(active_server)
                except Exception as e:
                    logger.error(f"Failed to create provider instance for {active_server}: {e}", exc_info=True)
                    continue

                if not provider:
                    continue

                # Ensure connection
                try:
                    can_connect = True
                    if hasattr(provider, 'authenticate'):
                        can_connect = provider.authenticate()

                    if not can_connect:
                        error_msg = f"Could not connect to {active_server} during external identifier sync."
                        logger.error(error_msg)
                        from core.event_bus import event_bus
                        event_bus.publish("NOTIFICATION", {
                            "type": "error",
                            "title": "Media Server Connection Failed",
                            "message": error_msg
                        })
                        continue
                except Exception as e:
                    error_msg = f"Connection failed for {active_server}: {e}"
                    logger.error(error_msg)
                    continue

                p_name = getattr(provider, 'name', '') or getattr(provider, 'plugin_id', '') or str(active_server)
                p_lower = p_name.lower()
                source_name = 'plex' if 'plex' in p_lower else ('jellyfin' if 'jellyfin' in p_lower else ('navidrome' if 'navidrome' in p_lower else p_lower))

                logger.info(f"Running external identifier sync for {source_name} ({active_server})")

                try:
                    mappings = []
                    if hasattr(provider, 'get_identifier_mappings'):
                        mappings = provider.get_identifier_mappings()
                    elif hasattr(provider, 'get_all_tracks'):
                        raw_tracks = provider.get_all_tracks() or []
                        mappings = []
                        for t in raw_tracks:
                            if isinstance(t, dict):
                                mappings.append(t)
                            elif hasattr(t, 'to_dict'):
                                mappings.append(t.to_dict())
                            elif hasattr(t, 'id') or hasattr(t, 'ratingKey'):
                                item_id = getattr(t, 'ratingKey', None) or getattr(t, 'id', None)
                                mappings.append({
                                    'file_path': getattr(t, 'file_path', None) or getattr(t, 'path', None),
                                    'plugin_source': source_name,
                                    'plugin_item_id': str(item_id) if item_id else None,
                                    'title': getattr(t, 'title', None) or getattr(t, 'name', None),
                                    'artist_name': getattr(t, 'artist', None) or getattr(t, 'artist_name', None),
                                })

                    with db.session_scope() as session:
                        local_media_rows = session.query(LocalMedia.media_id, LocalMedia.file_path).all()
                        path_to_media_id = {}
                        name_to_media_ids = {}

                        for mid, fp in local_media_rows:
                            if fp:
                                path_to_media_id[fp] = mid
                                canon = _canonicalize_path(fp)
                                path_to_media_id[canon] = mid
                                path_to_media_id[canon.lower()] = mid
                                fname = Path(fp).name.lower()
                                name_to_media_ids.setdefault(fname, []).append(mid)

                        existing_plugin_item_ids = set(
                            r[0] for r in session.query(ExternalIdentifier.plugin_item_id)
                            .filter(ExternalIdentifier.plugin_source == source_name).all()
                        )
                        existing_media_ids = set(
                            r[0] for r in session.query(ExternalIdentifier.media_id)
                            .filter(ExternalIdentifier.plugin_source == source_name).all()
                        )

                        synced_count = 0
                        for item in mappings:
                            if not isinstance(item, dict):
                                continue
                            item_id = str(item.get('plugin_item_id') or item.get('id') or '')
                            if not item_id or item_id in existing_plugin_item_ids:
                                continue

                            file_path = item.get('file_path')
                            media_id = None
                            if file_path:
                                local_fp = PathMapper.to_local(file_path)
                                canon_local = _canonicalize_path(local_fp)
                                media_id = (
                                    path_to_media_id.get(file_path)
                                    or path_to_media_id.get(_canonicalize_path(file_path))
                                    or path_to_media_id.get(local_fp)
                                    or path_to_media_id.get(canon_local)
                                    or path_to_media_id.get(canon_local.lower())
                                )
                                if not media_id:
                                    fname = Path(file_path).name.lower()
                                    matching_mids = name_to_media_ids.get(fname, [])
                                    if len(matching_mids) == 1:
                                        media_id = matching_mids[0]

                            if not media_id and item.get('title') and item.get('artist_name'):
                                title_clean = str(item['title']).strip().lower()
                                artist_clean = str(item['artist_name']).strip().lower()
                                matched_track = (
                                    session.query(Track)
                                    .join(Artist, Track.artist_id == Artist.id)
                                    .filter(
                                        func.lower(Track.title) == title_clean,
                                        func.lower(Artist.name) == artist_clean,
                                    )
                                    .first()
                                )
                                if matched_track and matched_track.media_files:
                                    media_id = matched_track.media_files[0].media_id

                            if media_id and media_id not in existing_media_ids:
                                new_ext = ExternalIdentifier(
                                    media_id=media_id,
                                    plugin_source=source_name,
                                    plugin_item_id=item_id,
                                    raw_data={"synced_at": datetime.now(timezone.utc).isoformat()}
                                )
                                session.add(new_ext)
                                existing_plugin_item_ids.add(item_id)
                                existing_media_ids.add(media_id)
                                synced_count += 1

                        logger.info(f"External identifier sync for {source_name}: successfully synced {synced_count} identifiers.")

                except Exception as e:
                    logger.error(f"External identifier sync worker failed for {active_server}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in external identifier sync job: {e}", exc_info=True)

    job_queue.register_job(
        name="external_identifier_sync",
        func=run_external_identifier_sync,
        # This job is normally triggered manually or sequentially, but we can give it an interval fallback
        interval_seconds=interval_seconds,
        start_after=900, 
        enabled=enabled,
        tags=["system", "database", "identifiers"],
        max_retries=2
    )
    
    logger.info(f"External identifier sync job registered (enabled={enabled})")


def register_media_server_scan_job(interval_seconds: int = 10800, enabled: bool = True):
    """Register periodic media server scan job.

    Runs more frequently than database_update so new files are recognized by the media server
    before incremental DB sync jobs run.
    """

    def run_media_server_scan(section: Optional[str] = None, **kwargs):
        try:
            logger.info("Starting scheduled media server scan job")

            from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry

            active_servers = PluginRegistry.get_active_services_by_type('media_server')
            if not active_servers:
                logger.warning("No active media server configured, skipping media scan")
                return

            for active_server in active_servers:
                provider = PluginRegistry.create_instance(active_server)
                if not provider:
                    logger.error(f"Could not create provider instance for active server '{active_server}'")
                    continue

                if hasattr(provider, "ensure_connection") and not provider.ensure_connection():
                    logger.error(f"Could not connect to active media server '{active_server}'")
                    continue

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
                    logger.info(f"Successfully triggered library scan on {active_server}")
                else:
                    logger.warning(f"Could not trigger library scan on {active_server} (no supported method found)")
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

    def run_suggestion_playlist_generation(max_mixes: int = 4, **kwargs):
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

    def run_duplicate_scan(auto_resolve: bool = False, **kwargs):
        try:
            logger.info("Starting duplicate scan job")
            service = DuplicateHygieneService()
            result = service.find_duplicates()
            auto_count = len((result or {}).get("auto_resolve", []))
            manual_count = len((result or {}).get("manual_review", []))
            total = auto_count + manual_count
            if total:
                logger.info(
                    "Duplicate scan complete: %d group(s) queued for manual review "
                    "(%d quality-ranked, %d metadata-conflict). "
                    "Review at Library > Manager > Duplicate Resolution.",
                    total, auto_count, manual_count,
                )
            else:
                logger.info("Duplicate scan complete: no duplicates found.")
            # Additionally, re-evaluate rated tracks to stage lifecycle actions
            try:
                work_db = get_working_database()
                staged_deletes = 0
                staged_upgrades = 0
                with work_db.session_scope() as session:
                    rated_sync_ids = [row[0] for row in session.query(UserRating.sync_id).distinct().all()]

                consensus_map = {}
                for sync_id in rated_sync_ids:
                    consensus = calculate_consensus(sync_id)
                    action = consensus.get("action", "KEEP")
                    if action in ("DELETE_MONTH_END", "UPGRADE_WEEK_END"):
                        consensus_map[sync_id] = consensus

                if consensus_map:
                    from core.suggestion_engine.deletion import apply_lifecycle_actions_batch
                    results = apply_lifecycle_actions_batch(consensus_map)

                    for raw_sync_id, res in results.items():
                        res_action = res.get("action")
                        if res_action == "DELETE_MONTH_END":
                            staged_deletes += 1
                        elif res_action == "UPGRADE_WEEK_END":
                            staged_upgrades += 1

                if staged_deletes or staged_upgrades:
                    logger.info(f"Duplicate scan staging: {staged_deletes} staged deletes, {staged_upgrades} staged upgrades")
            except Exception as e:
                logger.warning(f"Failed to stage lifecycle actions during duplicate scan: {e}")
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

    def run_stale_track_scan(inactive_days: int = 90, **kwargs):
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

    def run_process_lifecycle_actions(dry_run: bool = False, **kwargs):
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


def register_auto_import_scan_job(interval_seconds: int = 10800, enabled: bool = True):
    """Register the auto-importer directory scan & processing job (every 3 hours fallback, plus realtime watchdog)."""
    try:
        from services.auto_importer import get_auto_importer
        auto_importer = get_auto_importer()
        job_queue.register_job(
            name="auto_import_scan",
            func=auto_importer.scan_and_process,
            interval_seconds=interval_seconds,
            start_after=600,
            enabled=enabled,
            tags=["echosync", "import", "auto_import"],
            max_retries=3,
        )
        logger.info(
            f"Auto import scan job registered "
            f"(interval: {interval_seconds}s = {interval_seconds / 3600:.1f}h, enabled={enabled})"
        )
    except Exception as e:
        logger.error(f"Failed to register auto_import_scan job: {e}", exc_info=True)


def register_user_history_sync_job(interval_seconds: int = 43200, enabled: bool = True):
    """Register periodic user history sync job (every 12 hours)."""

    def run_user_history_sync(force_full: bool = False, **kwargs):
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


def register_retroactive_metadata_enhancement_job(interval_seconds: int = 86400, enabled: bool = True, batch_size: int = 100, check_all_files: bool = False):
    """Register a daily job to fill in missing MusicBrainz IDs for library tracks."""

    def run_metadata_enhancement(batch_size: int = 100, check_all_files: bool = False, **kwargs):
        def _worker(batch_size, check_all_files):
            try:
                from core.tiered_logger import get_logger
                from services.metadata_enhancer import RetroactiveEnhancer
                logger = get_logger("retroactive_metadata_worker")
                logger.info("Starting scheduled retroactive metadata enhancement job (child process)")
                RetroactiveEnhancer().enhance_library_metadata(batch_size=batch_size, check_all_files=check_all_files)
                logger.info("Retroactive metadata enhancement job complete")
            except Exception as e:
                from core.tiered_logger import get_logger
                get_logger("retroactive_metadata_worker").error(f"Job failed: {e}", exc_info=True)

        try:
            import multiprocessing
            from core.task_manager.supervisor import supervisor
            from core.task_manager.models import ProcessOwner, OwnerType
            
            p = multiprocessing.Process(target=_worker, args=(batch_size, check_all_files), daemon=True)
            p.start()
            
            reg_id = None
            if p.pid:
                owner = ProcessOwner(
                    owner_id="core.system_job",
                    owner_type=OwnerType.SYSTEM_JOB,
                    pid=p.pid,
                    task_name="retroactive_metadata_enhancement"
                )
                reg_id = supervisor.register_process(owner)
                
            p.join()
            
            if reg_id:
                supervisor.unregister_process(reg_id)
                
            if p.exitcode and p.exitcode != 0:
                if p.exitcode == -15:  # SIGTERM
                    logger.info("Retroactive metadata enhancement job was terminated by supervisor")
                else:
                    raise RuntimeError(f"Child process exited with code {p.exitcode}")
        except Exception as e:
            logger.error(f"Retroactive metadata enhancement job failed: {e}", exc_info=True)

    job_queue.register_job(
        name="retroactive_metadata_enhancement",
        func=run_metadata_enhancement,
        interval_seconds=interval_seconds,
        enabled=enabled,
        tags=["system", "metadata", "library"],
        max_retries=1,
        params={"batch_size": batch_size, "check_all_files": check_all_files},
    )

    logger.info(
        f"Retroactive metadata enhancement job registered "
        f"(interval: {interval_seconds}s = {interval_seconds / 3600:.1f}h, enabled={enabled}, batch_size={batch_size})"
    )



def register_plugin_update_check_job(interval_seconds: int = 43200, enabled: bool = True):
    """Register a 12-hour job to check for plugin updates and emit UI notifications."""
    def run_plugin_update_check(force: bool = False, **kwargs):
        try:
            logger.info("Starting scheduled plugin update check")
            from core.nexus_framework.plugin_store import plugin_store
            from core.event_bus import event_bus

            plugins = plugin_store.get_all_store_plugins()
            updates_found = []

            from database.config_database import get_config_database
            db = get_config_database()
            conn = db._open_connection()
            try:
                c = conn.cursor()
                for p in plugins:
                    if p.get("_installed") and p.get("update_available"):
                        updates_found.append(p.get("name", "Unknown Plugin"))
                        # Ensure background job is strictly read-only on the filesystem.
                        # Do NOT call download_plugin() here. Just update the DB for the UI.
                        
                        plugin_id = p.get("id", p.get("name"))
                        target_version = p.get("version", "Unknown")
                        if p.get("installed_channel") == "beta" and p.get("beta_version"):
                            target_version = p.get("beta_version")

                        # We just update available_version in DB
                        c.execute("SELECT id FROM services WHERE plugin_id=? OR name=?", (plugin_id, plugin_id))
                        row = c.fetchone()
                        if row:
                            c.execute("UPDATE services SET available_version = ? WHERE id = ?", (target_version, row[0]))
                conn.commit()
            finally:
                conn.close()

            if updates_found:
                event_bus.publish("NOTIFICATION", {
                    "type": "info",
                    "title": "Plugin Updates Available",
                    "message": f"Updates are available for: {', '.join(updates_found)}"
                })
                logger.info(f"Plugin updates found for: {', '.join(updates_found)}")
            else:
                logger.info("No plugin updates available.")

        except Exception as e:
            logger.error(f"Plugin update check job failed: {e}", exc_info=True)
            from core.event_bus import event_bus
            event_bus.publish("NOTIFICATION", {
                "type": "error",
                "title": "Plugin Update Check Failed",
                "message": str(e)
            })

    job_queue.register_job(
        name="plugin_update_check",
        func=run_plugin_update_check,
        interval_seconds=interval_seconds,
        enabled=enabled,
        tags=["system", "plugins", "updates"],
        max_retries=1,
    )
    logger.info(
        f"Plugin update check job registered (interval: {interval_seconds}s = {interval_seconds / 3600:.1f}h, enabled={enabled})"
    )

def cleanup_orphaned_plugin_databases():
    """
    Scans /data/plugins/data/ for any .db files and aggressively deletes them
    if their filename (plugin_id) does not match an active plugin in the services registry.
    It also checks the actual plugin folders and removes registry records if the plugin was physically deleted.
    """
    import os
    from pathlib import Path
    from core.tiered_logger import get_logger
    from database.config_database import get_config_database

    logger = get_logger("plugin_sweeper")
    plugin_data_dir = Path("/data/plugins/data/")

    db = get_config_database()
    active_ids = set()

    # 1. Clean Registry of missing folders (Ghost entries)
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, plugin_id, absolute_install_path FROM services WHERE is_active = 1 AND absolute_install_path IS NOT NULL")
        records = c.fetchall()
        for row in records:
            service_id, plugin_id, absolute_path = row[0], row[1], row[2]
            
            is_in_plugins_dir = False
            if absolute_path:
                try:
                    resolved_path = Path(absolute_path).resolve()
                    resolved_plugins_dir = Path(config_manager.get_plugins_dir()).resolve()
                    is_in_plugins_dir = str(resolved_path).lower().startswith(str(resolved_plugins_dir).lower())
                except Exception:
                    is_in_plugins_dir = False
            
            if absolute_path:
                exists = False
                if is_in_plugins_dir:
                    try:
                        from core.nexus_framework.plugin_loader import find_case_insensitive_path
                        exists = find_case_insensitive_path(Path(absolute_path)) is not None
                    except Exception:
                        exists = False
                else:
                    try:
                        exists = Path(absolute_path).exists()
                    except Exception:
                        exists = False

                if not exists and not is_in_plugins_dir:
                    logger.warning(f"Sweeper detected missing plugin folder outside plugins dir for plugin_id {plugin_id}: {absolute_path}. Removing ghost registry entry.")
                    c.execute("DELETE FROM services WHERE id=?", (service_id,))
                elif plugin_id:
                    active_ids.add(str(plugin_id))
            elif plugin_id:
                active_ids.add(str(plugin_id))
        conn.commit()

    # 2. Clean orphaned databases
    if not plugin_data_dir.exists():
        return

    for db_file in plugin_data_dir.glob("*.db"):
        file_id = db_file.stem.split('@')[0] # handle @beta files too
        if file_id not in active_ids:
            try:
                logger.warning(f"Sweeper detected orphaned database {db_file.name}. Removing it.")
                os.remove(db_file)
            except OSError as e:
                logger.error(f"Sweeper failed to remove orphaned database {db_file.name}: {e}")



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

        # Standalone job for fetching external identifiers
        register_external_identifier_sync_job(interval_seconds=21600, enabled=True)

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

        # Auto-importer scan job (every 3 hours fallback & watchdog initialization).
        register_auto_import_scan_job(interval_seconds=10800, enabled=True)

        # User history sync for Suggestion Engine baseline data (every 12 hours).
        register_user_history_sync_job(interval_seconds=43200, enabled=True)

        # Daily retroactive metadata enhancement for tracks missing MusicBrainz IDs.
        register_retroactive_metadata_enhancement_job(interval_seconds=86400, enabled=True)

        # 12-hour plugin update check
        cleanup_orphaned_plugin_databases()
        register_plugin_update_check_job(interval_seconds=43200, enabled=True)

        # Ad-hoc / manual system job for physical library reorganization
        register_reorganize_library_job(enabled=True)

        # Ad-hoc / manual maintenance job to decouple collapsed multi-edition media records
        register_decouple_media_job(enabled=True)

        logger.info("All system jobs registered successfully")
    except Exception as e:
        logger.error(f"Failed to register system jobs: {e}", exc_info=True)
