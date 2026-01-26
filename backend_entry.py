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


class ServiceStatusMonitor:
    """Background service monitor that periodically checks provider connectivity."""

    def __init__(self, spotify: SpotifyClient, plex: PlexClient, jellyfin: JellyfinClient,
                 navidrome: NavidromeClient, soulseek: SlskdProvider):
        self.spotify = spotify
        self.plex = plex
        self.jellyfin = jellyfin
        self.navidrome = navidrome
        self.soulseek = soulseek
        self._stop_event = asyncio.Event()

    async def check_once(self) -> None:
        try:
            spotify_status = self.spotify.sp is not None
            logger.debug("Spotify status: %s", spotify_status)

            active_server = config_manager.get_active_media_server()
            if active_server == "plex":
                server_status = self.plex.is_connected()
                logger.debug("Plex status: %s", server_status)
            elif active_server == "jellyfin":
                server_status = self.jellyfin.is_connected()
                logger.debug("Jellyfin status: %s", server_status)
            elif active_server == "navidrome":
                server_status = self.navidrome.is_connected()
                logger.debug("Navidrome status: %s", server_status)
            else:
                server_status = False

            soulseek_status = self.soulseek.is_configured()
            logger.debug("Soulseek status: %s", soulseek_status)

        except Exception as exc:  # noqa: BLE001
            logger.error("Service status check failed: %s", exc)

    async def run(self, interval_seconds: int = 10) -> None:
        logger.info("ServiceStatusMonitor started (interval=%ss)", interval_seconds)
        try:
            while not self._stop_event.is_set():
                await self.check_once()
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=interval_seconds)
                except asyncio.TimeoutError:
                    continue
        finally:
            logger.info("ServiceStatusMonitor stopped")

    def stop(self) -> None:
        self._stop_event.set()

    async def shutdown(self) -> None:
        self.stop()


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
    """Start the backend services without configuring logging (assumes external logging setup)."""
    logger.info("Starting backend services...")

    spotify_client = SpotifyClient()
    plex_client = PlexClient()
    jellyfin_client = JellyfinClient()
    navidrome_client = NavidromeClient()
    soulseek_client = SlskdProvider()

    monitor = ServiceStatusMonitor(
        spotify=spotify_client,
        plex=plex_client,
        jellyfin=jellyfin_client,
        navidrome=navidrome_client,
        soulseek=soulseek_client,
    )

    monitor_task = asyncio.create_task(monitor.run())

    # Start Download Manager background task
    download_manager = get_download_manager()
    await download_manager.start_background_task()

    try:
        await monitor_task
    except asyncio.CancelledError:
        logger.info("Backend shutdown signal received")
    finally:
        await monitor.shutdown()
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