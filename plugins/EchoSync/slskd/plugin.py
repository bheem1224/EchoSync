"""
SLSKD Plugin Lifecycle & Webhook Ingestion Module.

Handles:
- Native webhook endpoint registration ('download_status')
- Inbound webhook processing (@hookimpl on_webhook_received)
- DownloadQueue state progression (DOWNLOADING -> VERIFYING on DownloadFileComplete)
- EventBus reactions (DOWNLOAD_COMPLETED / DOWNLOAD_FAILED -> transfer memory eviction)
- Connection self-healing (SERVICE_DEGRADED -> server/connect with exponential backoff)
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from core.event_bus import event_bus
from core.plugins.sdk import compute_plugin_crc32, hookimpl, register_webhook_handler, sdk
from core.task_manager.models import OwnerType
from core.task_manager.supervisor import supervisor
from core.task_manager.task_queue import db_write_lease
from core.tiered_logger import get_logger

PLUGIN_NAMESPACE = "EchoSync.slskd"
PLUGIN_CRC32 = compute_plugin_crc32(PLUGIN_NAMESPACE)
logger = get_logger("slskd_plugin", plugin_id=PLUGIN_CRC32)

_RECONNECT_LOCK = threading.Lock()
_RECONNECT_STATE_LOCK = threading.Lock()
_RECONNECT_ATTEMPTS = 0
_EVENT_SUBSCRIPTIONS: list[tuple[str, Callable[[dict[str, Any]], None]]] = []


def _get_slskd_provider():
    """Retrieve the active or registered SlskdProvider instance."""
    from plugins.EchoSync.slskd.client import SlskdProvider

    try:
        from core.nexus_framework.plugin_loader import PluginRegistry

        # Derive CRC32 ID
        from core.plugins.sdk import compute_plugin_crc32

        p_id = compute_plugin_crc32(PLUGIN_NAMESPACE)
        instance = PluginRegistry.get_instance(p_id)
        if instance and isinstance(instance, SlskdProvider):
            return instance
    except Exception:
        pass
    return SlskdProvider()


def _resolve_task_id_from_payload(payload: dict[str, Any]) -> int | None:
    """
    Extract task_id from payload, or lookup DownloadQueue record matching
    filename / username in the working database.
    """
    # 1. Direct task_id if provided in payload
    if payload.get("task_id"):
        try:
            return int(payload["task_id"])
        except (ValueError, TypeError):
            pass

    # 2. Extract transfer metadata from slskd webhook payload
    # slskd payload format example:
    # {"event": "DownloadFileComplete", "file": {"filename": "..."}, "username": "..."}
    # or {"filename": "...", "username": "...", ...}
    file_info = payload.get("file") if isinstance(payload.get("file"), dict) else {}
    filename = file_info.get("filename") or payload.get("filename") or ""
    username = payload.get("username") or file_info.get("username") or ""

    if not filename and not username:
        return None

    try:
        return sdk.working.resolve_active_download_task_id(filename=filename, username=username)
    except Exception as e:
        logger.warning("Error resolving task_id from payload: %s", e)

    return None


def _find_completed_file_path(payload: dict[str, Any]) -> str | None:
    """Find local absolute path of the downloaded file on disk."""
    provider = _get_slskd_provider()
    download_dir = getattr(provider, "download_path", Path("./downloads"))

    file_info = payload.get("file") if isinstance(payload.get("file"), dict) else {}
    filename = file_info.get("filename") or payload.get("filename") or ""
    local_path_raw = file_info.get("localPath") or payload.get("local_path")

    if local_path_raw and Path(local_path_raw).exists():
        return str(Path(local_path_raw).resolve())

    if filename:
        clean_name = filename.replace("\\", "/").split("/")[-1]
        candidate_path = Path(download_dir) / clean_name
        if candidate_path.exists():
            return str(candidate_path.resolve())

        # Check subdirectories
        try:
            for p in Path(download_dir).rglob(clean_name):
                if p.is_file():
                    return str(p.resolve())
        except Exception:
            pass

    return local_path_raw or (str(Path(download_dir) / filename) if filename else None)


@hookimpl
async def on_webhook_received(slug: str, payload: dict[str, Any]) -> None:
    """
    Handle inbound webhooks routed to EchoSync.slskd.
    Supports 'download_status' slug with DownloadFileComplete and DownloadFileFailed events.
    """
    logger.info(
        "EchoSync.slskd received webhook for slug '%s': keys=%s",
        slug,
        list(payload.keys()),
    )

    event_type = payload.get("event") or payload.get("type") or payload.get("status")
    # Case-insensitive event check
    event_str = str(event_type).strip() if event_type else ""

    if event_str.lower() in [
        "downloadfilecomplete",
        "complete",
        "completed",
        "finished",
        "succeeded",
    ]:
        task_id = _resolve_task_id_from_payload(payload)
        file_path = _find_completed_file_path(payload)

        logger.info("DownloadFileComplete matched: task_id=%s, file_path=%s", task_id, file_path)

        # Transition DownloadQueue state to VERIFYING
        if task_id:
            try:
                with db_write_lease(task_name=f"plugin_{PLUGIN_CRC32}"):
                    if sdk.working.transition_download_to_verifying(task_id, file_path=file_path):
                        logger.info("DownloadQueue %s transitioned to VERIFYING", task_id)
            except Exception as e:
                logger.error("Failed to transition DownloadQueue %s to VERIFYING: %s", task_id, e)

        # Emit DOWNLOAD_FILE_READY on EventBus
        event_bus.publish(
            {
                "event": "DOWNLOAD_FILE_READY",
                "task_id": task_id,
                "download_id": task_id,
                "file_path": file_path,
                "provider": PLUGIN_NAMESPACE,
                "payload": payload,
            }
        )

    elif event_str.lower() in [
        "downloadfilefailed",
        "failed",
        "error",
        "aborted",
        "cancelled",
    ]:
        task_id = _resolve_task_id_from_payload(payload)
        error_msg = payload.get("error") or payload.get("message") or "REMOTE_TRANSFER_FAILED"
        logger.warning("DownloadFileFailed matched: task_id=%s, error=%s", task_id, error_msg)

        if task_id:
            try:
                from services.download_manager import get_download_manager

                dm = get_download_manager()
                dm.handle_verification_failure(task_id, reason=str(error_msg))
            except Exception as e:
                logger.error("Failed to handle verification failure for %s: %s", task_id, e)

    elif event_str.lower() in [
        "soulseekclientconnected",
        "connected",
    ]:
        global _RECONNECT_ATTEMPTS
        with _RECONNECT_STATE_LOCK:
            _RECONNECT_ATTEMPTS = 0
        logger.info("SoulseekClientConnected matched: client connected.")
        event_bus.publish(
            {
                "event": "SERVICE_HEALTHY",
                "service": PLUGIN_NAMESPACE,
                "payload": payload,
            }
        )

    elif event_str.lower() in [
        "soulseekclientdisconnected",
        "disconnected",
    ]:
        logger.warning("SoulseekClientDisconnected matched: client disconnected.")
        event_bus.publish(
            {
                "event": "SERVICE_DEGRADED",
                "service": PLUGIN_NAMESPACE,
                "payload": payload,
            }
        )


async def _on_download_completed_or_failed(event_data: dict[str, Any]) -> None:
    """Evict completed or failed transfers from daemon memory to prevent memory leaks."""
    event_name = event_data.get("event", "")
    task_id = event_data.get("download_id") or event_data.get("task_id")
    provider = _get_slskd_provider()

    username = event_data.get("username")
    transfer_id = event_data.get("transfer_id") or event_data.get("provider_id")

    if not username and task_id:
        try:
            username, resolved_transfer_id = sdk.working.get_download_candidate_identity(task_id)
            if resolved_transfer_id:
                transfer_id = resolved_transfer_id
        except Exception as e:
            logger.debug("Could not lookup transfer identity for task %s: %s", task_id, e)

    if username:
        logger.info(
            "Evicting transfer from slskd memory on %s: username=%s",
            event_name,
            username,
        )
        await provider.delete_transfer(username, transfer_id)


async def _on_service_degraded(event_data: dict[str, Any]) -> None:
    """Auto-reconnect Soulseek daemon when degraded connection state is detected."""
    service = event_data.get("service", "")
    if service and service not in [PLUGIN_NAMESPACE, "slskd"]:
        return

    global _RECONNECT_ATTEMPTS
    if not _RECONNECT_LOCK.acquire(blocking=False):
        logger.debug("Reconnect already in progress for %s; skipping duplicate trigger.", PLUGIN_NAMESPACE)
        return

    try:
        with _RECONNECT_STATE_LOCK:
            delay = min(60, (2**_RECONNECT_ATTEMPTS))
            _RECONNECT_ATTEMPTS = min(_RECONNECT_ATTEMPTS + 1, 6)
            attempt_num = _RECONNECT_ATTEMPTS

        logger.warning(
            "Service degraded detected for %s. Attempting reconnect after %ds (attempt %d)...",
            PLUGIN_NAMESPACE,
            delay,
            attempt_num,
        )
        await asyncio.sleep(delay)

        provider = _get_slskd_provider()
        success = await provider.reconnect_server()
        if success:
            logger.info("Successfully requested slskd server reconnect.")
            with _RECONNECT_STATE_LOCK:
                _RECONNECT_ATTEMPTS = 0
        else:
            logger.error("Failed to request slskd server reconnect.")
    finally:
        _RECONNECT_LOCK.release()


def _dispatch_async_event_handler(
    coro_fn: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    event_data: dict[str, Any],
    task_name: str,
) -> None:
    """Synchronous thread-safe bridge executing an async slskd event coroutine cleanly."""
    payload = dict(event_data or {})

    def _log_task_exception(task: asyncio.Task[Any]) -> None:
        try:
            exc = task.exception()
            if exc is not None:
                logger.error("Unhandled error in %s: %s", task_name, exc, exc_info=exc)
        except asyncio.CancelledError:
            pass

    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(coro_fn(payload))
        task.add_done_callback(_log_task_exception)
    except RuntimeError:

        def _run_in_thread() -> None:
            try:
                asyncio.run(coro_fn(payload))
            except Exception as exc:
                logger.error("Error in supervised handler %s: %s", task_name, exc, exc_info=True)

        supervisor.spawn_supervised_thread(
            target=_run_in_thread,
            name=task_name,
            owner_id=str(PLUGIN_CRC32),
            owner_type=OwnerType.PLUGIN,
            bound_to_general_pool=True,
        )


def _handle_download_completed(data: dict[str, Any]) -> None:
    """Synchronous EventBus subscriber for DOWNLOAD_COMPLETED."""
    _dispatch_async_event_handler(
        _on_download_completed_or_failed, data, "slskd_download_completed"
    )


def _handle_download_failed(data: dict[str, Any]) -> None:
    """Synchronous EventBus subscriber for DOWNLOAD_FAILED."""
    _dispatch_async_event_handler(
        _on_download_completed_or_failed, data, "slskd_download_failed"
    )


def _handle_service_degraded(data: dict[str, Any]) -> None:
    """Synchronous EventBus subscriber for SERVICE_DEGRADED."""
    _dispatch_async_event_handler(
        _on_service_degraded, data, "slskd_service_degraded"
    )


def initialize_plugin() -> None:
    """Initialize plugin: register webhook endpoint, wire event listeners, and register hooks."""
    try:
        from core.plugins.sdk import compute_plugin_crc32

        crc32_id = compute_plugin_crc32(PLUGIN_NAMESPACE)

        # 1. Register default webhook endpoint
        reg = sdk.webhooks.register_endpoint(
            slug="download_status",
            allow_unauthenticated=False,
        )
        logger.info(
            "EchoSync.slskd webhook registered: %s (CRC32: %d)",
            reg.get("url"),
            crc32_id,
        )

        # 2. Register functional webhook handler for this plugin's CRC32 ID
        register_webhook_handler(crc32_id, on_webhook_received)

        # 3. Bind synchronous thread-safe EventBus subscribers idempotently
        for old_event, old_handler in list(_EVENT_SUBSCRIPTIONS):
            event_bus.unsubscribe(old_event, old_handler)
        _EVENT_SUBSCRIPTIONS.clear()

        subscriptions = [
            ("DOWNLOAD_COMPLETED", _handle_download_completed),
            ("DOWNLOAD_FAILED", _handle_download_failed),
            ("SERVICE_DEGRADED", _handle_service_degraded),
        ]
        for event_name, handler in subscriptions:
            event_bus.subscribe(event_name, handler)
            _EVENT_SUBSCRIPTIONS.append((event_name, handler))

        logger.info("EchoSync.slskd event listeners initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize EchoSync.slskd plugin module: %s", e, exc_info=True)


# Initialize on import
initialize_plugin()
