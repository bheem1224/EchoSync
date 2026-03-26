"""Contains helper routines for starting the background services.

This replaces the now-removed ``backend_entry.py`` script.  The Flask
application imports :func:`start_services` to spin up the download manager
and provider clients in a dedicated thread; the former script also exposed a
standalone ``backend_main`` entry point which may be used for debugging or
CLI workflows.

The code is intentionally kept minimal: logging configuration is performed by
``run_api.py`` prior to invoking these helpers, and environment variables are
expected to have been loaded already.  No code outside the core package should
need to import this module, but the tests may reference it.
"""

import asyncio
import logging
from typing import Any, Iterable

from core.settings import config_manager
from core.tiered_logger import setup_logging, get_logger
from services.download_manager import get_download_manager
from services.library_watcher import get_library_watcher

logger = get_logger("backend")


async def _graceful_close(clients: Iterable[Any]) -> None:
    for client in clients:
        if client is None:
            continue
        close_fn = getattr(client, "close", None)
        if callable(close_fn):
            try:
                maybe_coro = close_fn()
                if asyncio.iscoroutine(maybe_coro):
                    await asyncio.wait_for(maybe_coro, timeout=3)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error closing %s: %s", client.__class__.__name__, exc)


async def start_services() -> None:
    """Start backend services.

    This logic mirrors the original ``backend_entry.start_services``.  It
    initializes provider clients (Spotify, Plex, etc.) and optionally starts
    the download manager if ``downloads.auto_start`` is enabled in the
    configuration.
    """
    logger.info("Starting backend services...")

    disabled_providers = config_manager.get_disabled_providers()

    # Initialize provider clients (each registers its own health check)
    spotify_client = None
    plex_client = None
    jellyfin_client = None
    navidrome_client = None
    soulseek_client = None

    # Spotify
    if "spotify" not in disabled_providers:
        creds = config_manager.get_spotify_config()
        # Also check active account or global creds
        active_acc = config_manager.get_active_spotify_account()
        if (creds.get("client_id") and creds.get("client_secret")) or active_acc:
            try:
                from providers.spotify.client import SpotifyClient
                spotify_client = SpotifyClient()
                logger.info("Spotify client started")
            except Exception as e:
                logger.error(f"Failed to start Spotify client: {e}")
        else:
            logger.debug("Spotify not configured, skipping")
    else:
        logger.info("Spotify is disabled")

    # Plex
    if "plex" not in disabled_providers:
        from database.config_database import get_config_database
        config_db = get_config_database()
        plex_id = config_db.get_or_create_service_id('plex')
        plex_url = config_db.get_service_config(plex_id, 'base_url') or config_db.get_service_config(plex_id, 'server_url')
        plex_token = config_db.get_service_config(plex_id, 'token')

        if plex_url and plex_token:
            try:
                from providers.plex.client import PlexClient
                plex_client = PlexClient()
                logger.info("Plex client started")
            except Exception as e:
                logger.error(f"Failed to start Plex client: {e}")
        else:
            logger.debug("Plex not configured, skipping")
    else:
        logger.info("Plex is disabled")

    # Jellyfin
    if "jellyfin" not in disabled_providers:
        conf = config_manager.get_jellyfin_config()
        if conf.get("base_url") and conf.get("api_key"):
            try:
                from providers.jellyfin.client import JellyfinClient
                jellyfin_client = JellyfinClient()
                logger.info("Jellyfin client started")
            except Exception as e:
                logger.error(f"Failed to start Jellyfin client: {e}")
        else:
            logger.debug("Jellyfin not configured, skipping")
    else:
        logger.info("Jellyfin is disabled")

    # Navidrome
    if "navidrome" not in disabled_providers:
        conf = config_manager.get_navidrome_config()
        if conf.get("base_url") and conf.get("username"):
            try:
                from providers.navidrome.client import NavidromeClient
                navidrome_client = NavidromeClient()
                logger.info("Navidrome client started")
            except Exception as e:
                logger.error(f"Failed to start Navidrome client: {e}")
        else:
            logger.debug("Navidrome not configured, skipping")
    else:
        logger.info("Navidrome is disabled")

    # Slskd (Soulseek)
    if "soulseek" not in disabled_providers and "slskd" not in disabled_providers:
        from database.config_database import get_config_database
        config_db = get_config_database()
        slskd_id = config_db.get_or_create_service_id('soulseek')
        slskd_url = config_db.get_service_config(slskd_id, 'slskd_url') or config_db.get_service_config(slskd_id, 'server_url')
        api_key = config_db.get_service_config(slskd_id, 'api_key')

        if slskd_url and api_key:
            try:
                from providers.slskd.client import SlskdProvider
                soulseek_client = SlskdProvider()
                logger.info("Slskd client started")
            except Exception as e:
                logger.error(f"Failed to start Slskd client: {e}")
        else:
            logger.debug("Slskd not configured, skipping")
    else:
        logger.info("Soulseek/Slskd is disabled")
    
    logger.info("Provider clients initialization complete")

    # Start Download Manager only if explicitly enabled (default: off)
    downloads_cfg = config_manager.get_all().get("downloads", {}) if hasattr(config_manager, "get_all") else {}
    auto_start_downloads = downloads_cfg.get("auto_start", False)

    download_manager = get_download_manager()
    if auto_start_downloads:
        await download_manager.start_background_task()
        logger.info("Download Manager auto-start enabled")
    else:
        logger.info("Download Manager auto-start is disabled (downloads will not run on startup)")

    # Start real-time library file watcher
    library_watcher = get_library_watcher()
    library_watcher.start()

    # Keep services alive indefinitely
    try:
        shutdown_event = asyncio.Event()
        await shutdown_event.wait()
    except asyncio.CancelledError:
        logger.info("Backend shutdown signal received")
    finally:
        library_watcher.stop()
        await download_manager.stop_background_task()
        active_clients = [c for c in [soulseek_client, plex_client, jellyfin_client, navidrome_client] if c is not None]
        await _graceful_close(active_clients)
        logger.info("Backend services stopped")


async def backend_main() -> None:
    """Standalone entry point if someone wants to run services outside of Flask."""
    logging_config = config_manager.get_logging_config()
    log_file = logging_config.get("path", "logs/backend.log")
    setup_logging(level=logging_config.get("level", "INFO"), log_file=log_file)

    await start_services()
