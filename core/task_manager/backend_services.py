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

    from core.nexus_framework.plugin_loader import PluginRegistry

    active_clients = []

    # Initialize Sync Services
    sync_services = PluginRegistry.get_active_services_by_type('sync')
    for service_ns in sync_services:
        try:
            client = PluginRegistry.create_instance(service_ns)
            active_clients.append(client)
            logger.info(f"Started sync plugin: {service_ns}")
        except Exception as e:
            logger.error(f"Failed to start sync plugin {service_ns}: {e}")

    # Initialize Media Server Services
    media_services = PluginRegistry.get_active_services_by_type('media_server')
    for service_ns in media_services:
        try:
            client = PluginRegistry.create_instance(service_ns)
            active_clients.append(client)
            logger.info(f"Started media server plugin: {service_ns}")
        except Exception as e:
            logger.error(f"Failed to start media server plugin {service_ns}: {e}")

    # Initialize Downloader Services
    download_services = PluginRegistry.get_active_services_by_type('download')
    for service_ns in download_services:
        try:
            client = PluginRegistry.create_instance(service_ns)
            active_clients.append(client)
            logger.info(f"Started download plugin: {service_ns}")
        except Exception as e:
            logger.error(f"Failed to start download plugin {service_ns}: {e}")

    # Initialize other active services
    metadata_services = PluginRegistry.get_active_services_by_type('metadata')
    for service_ns in metadata_services:
        try:
            client = PluginRegistry.create_instance(service_ns)
            active_clients.append(client)
            logger.info(f"Started metadata plugin: {service_ns}")
        except Exception as e:
            logger.error(f"Failed to start metadata plugin {service_ns}: {e}")

    logger.info("Provider clients initialization complete")

    # Start Download Manager only if explicitly enabled (default: off)
    from services.storage_service import get_storage_service
    storage = get_storage_service()
    downloads_cfg = storage.get_service_config('system', 'downloads') or {}
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
        pass
        await _graceful_close(active_clients)
        logger.info("Backend services stopped")


async def backend_main() -> None:
    """Standalone entry point if someone wants to run services outside of Flask."""
    from services.storage_service import get_storage_service
    storage = get_storage_service()
    logging_config = storage.get_service_config('system', 'logging') or {}
    log_file = logging_config.get("path", "logs/backend.log")
    setup_logging(level=logging_config.get("level", "INFO"), log_file=log_file)

    await start_services()
