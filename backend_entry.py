import asyncio
import logging
from typing import Any, Iterable
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

    # Initialize provider clients (each registers its own health check)
    spotify_client = SpotifyClient()
    plex_client = PlexClient()
    jellyfin_client = JellyfinClient()
    navidrome_client = NavidromeClient()
    soulseek_client = SlskdProvider()
    
    logger.info("Provider clients initialized - health checks registered with global system")

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
        await _graceful_close([soulseek_client, plex_client, jellyfin_client, navidrome_client])
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