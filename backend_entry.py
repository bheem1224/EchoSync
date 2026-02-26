import asyncio
import logging
from typing import Any, Iterable, List
from dotenv import load_dotenv

# Load environment variables from .env file before importing config_manager
load_dotenv()

from core.settings import config_manager
from core.tiered_logger import setup_logging, get_logger
from services.download_manager import get_download_manager
from providers.spotify.client import SpotifyClient
from providers.plex.client import PlexClient
from providers.jellyfin.client import JellyfinClient
from providers.navidrome.client import NavidromeClient
from providers.slskd.client import SlskdProvider

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
    """Start the backend services without configuring logging (assumes external logging setup).
    
    Note: Provider health checks are registered automatically by each client's __init__ method
    and managed by the global health check system (see core/health_check.py).
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
        conf = config_manager.get_plex_config()
        if conf.get("base_url") and conf.get("token"):
            try:
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
        conf = config_manager.get_soulseek_config()
        if conf.get("slskd_url") and conf.get("api_key"):
            try:
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

    # Keep services alive indefinitely
    try:
        # Create an event that will never be set - keeps the service running
        shutdown_event = asyncio.Event()
        await shutdown_event.wait()
    except asyncio.CancelledError:
        logger.info("Backend shutdown signal received")
    finally:
        await download_manager.stop_background_task()
        # Filter out None clients
        active_clients = [c for c in [soulseek_client, plex_client, jellyfin_client, navidrome_client] if c is not None]
        await _graceful_close(active_clients)
        logger.info("Backend services stopped")


async def backend_main() -> None:
    logging_config = config_manager.get_logging_config()
    log_file = logging_config.get("path", "logs/backend.log")
    setup_logging(level=logging_config.get("level", "INFO"), log_file=log_file)

    await start_services()


if __name__ == "__main__":
    try:
        asyncio.run(backend_main())
    except KeyboardInterrupt:
        logger.info("Backend interrupted by user")
