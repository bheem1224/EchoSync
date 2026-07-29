import os
import signal
import sys
import threading
import uuid
from typing import Dict, List, Optional
from core.tiered_logger import get_logger
from core.task_manager.models import ProcessOwner

logger = get_logger("process_supervisor")


class ProcessSupervisor:
    """
    Tracks process ownership and manages active thread or sub-process PID registrations.
    Enables safe termination of tasks registered under a specific owner_id.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._processes: Dict[str, ProcessOwner] = {}

    def register_process(self, owner: ProcessOwner) -> str:
        """
        Registers an active thread or sub-process PID.

        Args:
            owner: ProcessOwner instance describing ownership and metadata.

        Returns:
            str: Unique registration ID.
        """
        registration_id = f"{owner.owner_id}_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._processes[registration_id] = owner
        logger.debug(
            f"Registered process '{registration_id}' for owner '{owner.owner_id}' "
            f"(PID: {owner.pid}, Thread: {owner.thread_id}, Task: {owner.task_name})"
        )
        return registration_id

    def unregister_process(self, registration_id: str) -> None:
        """
        Removes completed or stopped tasks from the process registry.

        Args:
            registration_id: Unique registration ID returned during register_process.
        """
        with self._lock:
            removed = self._processes.pop(registration_id, None)
        if removed:
            logger.debug(f"Unregistered process '{registration_id}' for owner '{removed.owner_id}'")

    def terminate_owner_processes(self, owner_id: str) -> None:
        """
        Kills all sub-processes/threads registered under owner_id.
        Used when a plugin is disabled, reloaded, or encounters a fatal error.

        Args:
            owner_id: The owner identifier (e.g. 'plugin.plex').
        """
        with self._lock:
            target_ids = [
                reg_id for reg_id, owner in self._processes.items()
                if owner.owner_id == owner_id
            ]

        if not target_ids:
            logger.debug(f"No active processes found for owner '{owner_id}' to terminate.")
            return

        logger.info(f"Terminating {len(target_ids)} process(es) registered under owner '{owner_id}'")

        for reg_id in target_ids:
            with self._lock:
                owner = self._processes.pop(reg_id, None)

            if not owner:
                continue

            if owner.pid:
                self._kill_process(owner.pid, owner.task_name)

    def _kill_process(self, pid: int, task_name: str) -> None:
        """Helper to terminate a OS process safely across platforms."""
        try:
            if sys.platform == "win32":
                # Windows process termination
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    # Fallback to force kill if SIGTERM fails
                    os.kill(pid, signal.SIGABRT)
            else:
                # POSIX process termination
                os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent termination signal to process PID {pid} (Task: {task_name})")
        except (ProcessLookupError, OSError) as exc:
            logger.debug(f"Process PID {pid} (Task: {task_name}) was already terminated or not found: {exc}")

    def get_active_processes(self, owner_id: Optional[str] = None) -> List[ProcessOwner]:
        """
        Lists active process registrations across the platform.

        Args:
            owner_id: Optional owner_id to filter results.

        Returns:
            List[ProcessOwner]: Matching active process registrations.
        """
        with self._lock:
            if owner_id:
                return [p for p in self._processes.values() if p.owner_id == owner_id]
            return list(self._processes.values())


# Global ProcessSupervisor singleton
supervisor = ProcessSupervisor()
