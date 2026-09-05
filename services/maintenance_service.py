"""
Maintenance Service for EchoSync background remediation tasks.
"""

import os
import threading
from collections.abc import Callable
from typing import Any

from core.database.repositories.track_repo import TrackRepository
from core.task_manager.models import OwnerType, ProcessCategory, ProcessOwner
from core.task_manager.supervisor import supervisor
from core.tiered_logger import get_logger
from database.music_database import get_database

logger = get_logger("services.maintenance_service")


def run_media_decoupling_job(
    progress_callback: Callable[[int, int, str], None] | None = None,
    duration_threshold_ms: int = 5000,
) -> dict[str, Any]:
    """
    Standard background maintenance routine to decouple multi-edition media records.
    Wraps TrackRepository.decouple_collapsed_media within session_scope and registers
    with the ProcessSupervisor.
    """
    thread_id = threading.get_ident()
    reg_id = supervisor.register_process(
        ProcessOwner(
            owner_id="system.decouple_collapsed_media",
            owner_type=OwnerType.SYSTEM_JOB,
            task_name="Decouple Collapsed Media Versions",
            category=ProcessCategory.WORKER_THREAD,
            is_killable=True,
            thread_id=thread_id,
            pid=os.getpid(),
            metadata={"duration_threshold_ms": duration_threshold_ms},
        )
    )
    logger.info(
        f"Starting media decoupling job [{reg_id}] with threshold {duration_threshold_ms}ms"
    )
    if progress_callback:
        try:
            progress_callback(0, 100, "Starting media decoupling scan...")
        except Exception:
            pass

    try:
        db = get_database()
        with db.session_scope() as session:
            decoupled_count = TrackRepository.decouple_collapsed_media(
                session, duration_threshold_ms=duration_threshold_ms
            )

        logger.info(
            f"Media decoupling completed [{reg_id}]: {decoupled_count} track(s) decoupled"
        )
        if progress_callback:
            try:
                progress_callback(
                    100, 100, f"Completed: {decoupled_count} track(s) decoupled"
                )
            except Exception:
                pass

        return {
            "job_id": reg_id,
            "status": "completed",
            "decoupled_count": decoupled_count,
        }
    except Exception as e:
        logger.error(
            f"Error during media decoupling job [{reg_id}]: {e}", exc_info=True
        )
        if progress_callback:
            try:
                progress_callback(0, 100, f"Failed: {e!s}")
            except Exception:
                pass
        raise
    finally:
        supervisor.unregister_process(reg_id)
