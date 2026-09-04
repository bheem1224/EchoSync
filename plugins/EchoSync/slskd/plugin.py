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
from pathlib import Path
from typing import Any, Dict, Optional

from core.event_bus import event_bus
from core.plugins.sdk import hookimpl, register_webhook_handler, sdk
from core.tiered_logger import get_logger

logger = get_logger("slskd_plugin")

PLUGIN_NAMESPACE = "EchoSync.slskd"
_RECONNECT_LOCK = asyncio.Lock()
_RECONNECT_ATTEMPTS = 0


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


def _resolve_task_id_from_payload(payload: Dict[str, Any]) -> Optional[int]:
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

    norm_filename = filename.replace("\\", "/").split("/")[-1].strip().lower()

    try:
        from database.working_database import get_working_database
        from core.database.models.working import DownloadQueue, DownloadStatus
        work_db = get_working_database()
        with work_db.session_scope() as session:
            # Look for active/downloading or verifying items
            active_items = (
                session.query(DownloadQueue)
                .filter(
                    DownloadQueue.status.in_([
                        DownloadStatus.DOWNLOADING.value,
                        DownloadStatus.VERIFYING.value,
                        DownloadStatus.QUEUED.value,
                        DownloadStatus.SEARCHING.value,
                        "downloading", "verifying", "queued", "searching"
                    ])
                )
                .order_by(DownloadQueue.id.desc())
                .all()
            )

            for item in active_items:
                # Check candidate_id or provider_id (format: username|filename)
                cand_id = item.active_candidate_id or item.plugin_id or ""
                if cand_id:
                    c_lower = cand_id.lower()
                    if norm_filename and norm_filename in c_lower:
                        return item.id
                    if username and username.lower() in c_lower:
                        return item.id

                # Check echo_sync_track filename
                track = item.echo_sync_track or {}
                t_file = track.get("file_path") or track.get("title") or ""
                if norm_filename and norm_filename in str(t_file).lower():
                    return item.id
    except Exception as e:
        logger.warning("Error resolving task_id from payload: %s", e)

    return None


def _find_completed_file_path(payload: Dict[str, Any]) -> Optional[str]:
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
async def on_webhook_received(slug: str, payload: Dict[str, Any]) -> None:
    """
    Handle inbound webhooks routed to EchoSync.slskd.
    Supports 'download_status' slug with DownloadFileComplete and DownloadFileFailed events.
    """
    logger.info("EchoSync.slskd received webhook for slug '%s': keys=%s", slug, list(payload.keys()))

    event_type = payload.get("event") or payload.get("type") or payload.get("status")
    # Case-insensitive event check
    event_str = str(event_type).strip() if event_type else ""

    if event_str.lower() in ["downloadfilecomplete", "complete", "completed", "finished", "succeeded"]:
        task_id = _resolve_task_id_from_payload(payload)
        file_path = _find_completed_file_path(payload)

        logger.info("DownloadFileComplete matched: task_id=%s, file_path=%s", task_id, file_path)

        # Transition DownloadQueue state to VERIFYING
        if task_id:
            try:
                from services.download_manager import get_download_manager
                dm = get_download_manager()
                dm.transition_to_verifying(task_id, file_path=file_path)
            except Exception as e:
                logger.error("Failed to transition DownloadQueue %s to VERIFYING: %s", task_id, e)

        # Emit DOWNLOAD_FILE_READY on EventBus
        event_bus.publish({
            "event": "DOWNLOAD_FILE_READY",
            "task_id": task_id,
            "download_id": task_id,
            "file_path": file_path,
            "provider": PLUGIN_NAMESPACE,
            "payload": payload,
        })

    elif event_str.lower() in ["downloadfilefailed", "failed", "error", "aborted", "cancelled"]:
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


async def _on_download_completed_or_failed(event_data: Dict[str, Any]) -> None:
    """Evict completed or failed transfers from daemon memory to prevent memory leaks."""
    event_name = event_data.get("event", "")
    task_id = event_data.get("download_id") or event_data.get("task_id")
    provider = _get_slskd_provider()

    username = event_data.get("username")
    transfer_id = event_data.get("transfer_id") or event_data.get("provider_id")

    if not username and task_id:
        try:
            from database.working_database import get_working_database
            from core.database.models.working import DownloadQueue
            work_db = get_working_database()
            with work_db.session_scope() as session:
                item = session.get(DownloadQueue, int(task_id))
                if item:
                    cand = item.active_candidate_id or item.plugin_id or ""
                    if "|" in cand:
                        parts = cand.split("|", 1)
                        username = parts[0]
                        transfer_id = parts[1]
        except Exception as e:
            logger.debug("Could not lookup transfer identity for task %s: %s", task_id, e)

    if username:
        logger.info("Evicting transfer from slskd memory on %s: username=%s", event_name, username)
        await provider.delete_transfer(username, transfer_id)


async def _on_service_degraded(event_data: Dict[str, Any]) -> None:
    """Auto-reconnect Soulseek daemon when degraded connection state is detected."""
    service = event_data.get("service", "")
    if service and service not in [PLUGIN_NAMESPACE, "slskd"]:
        return

    global _RECONNECT_ATTEMPTS
    async with _RECONNECT_LOCK:
        delay = min(60, (2 ** _RECONNECT_ATTEMPTS))
        _RECONNECT_ATTEMPTS = min(_RECONNECT_ATTEMPTS + 1, 6)
        logger.warning(
            "Service degraded detected for %s. Attempting reconnect after %ds (attempt %d)...",
            PLUGIN_NAMESPACE, delay, _RECONNECT_ATTEMPTS
        )
        await asyncio.sleep(delay)

        provider = _get_slskd_provider()
        success = await provider.reconnect_server()
        if success:
            logger.info("Successfully requested slskd server reconnect.")
            _RECONNECT_ATTEMPTS = 0
        else:
            logger.error("Failed to request slskd server reconnect.")


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
        logger.info("EchoSync.slskd webhook registered: %s (CRC32: %d)", reg.get("url"), crc32_id)

        # 2. Register functional webhook handler for this plugin's CRC32 ID
        register_webhook_handler(crc32_id, on_webhook_received)

        # 3. Bind EventBus subscribers
        def _handle_completed(data: dict):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_on_download_completed_or_failed(data))
            except RuntimeError:
                asyncio.run(_on_download_completed_or_failed(data))

        def _handle_failed(data: dict):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_on_download_completed_or_failed(data))
            except RuntimeError:
                asyncio.run(_on_download_completed_or_failed(data))

        def _handle_degraded(data: dict):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_on_service_degraded(data))
            except RuntimeError:
                asyncio.run(_on_service_degraded(data))

        event_bus.subscribe("DOWNLOAD_COMPLETED", _handle_completed)
        event_bus.subscribe("DOWNLOAD_FAILED", _handle_failed)
        event_bus.subscribe("SERVICE_DEGRADED", _handle_degraded)
        logger.info("EchoSync.slskd event listeners initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize EchoSync.slskd plugin module: %s", e, exc_info=True)


# Initialize on import
initialize_plugin()

