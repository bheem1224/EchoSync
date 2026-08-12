import os
import signal
import sys
import threading
import time
import uuid
from typing import Dict, List, Optional, Tuple
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

    def kill_with_cleanup(self, registration_id: str, wait_secs: float = 3.0) -> Tuple[bool, str]:
        """
        Safely terminate a specific registered process and release any DB sessions
        it may be holding, preventing database corruption.

        Steps:
          1. Send SIGTERM to the OS-level PID (if any).
          2. Wait up to `wait_secs` for the thread to exit naturally.
          3. Flush thread-local SQLAlchemy sessions via _release_worker_resources().
          4. Unregister the entry from the supervisor.

        Args:
            registration_id: The unique ID returned by register_process().
            wait_secs: How long to wait for the thread to finish after signalling.

        Returns:
            (success: bool, message: str)
        """
        with self._lock:
            owner = self._processes.get(registration_id)

        if not owner:
            return False, f"No process with registration_id '{registration_id}' found"

        task_label = f"'{owner.task_name}' (owner={owner.owner_id})"
        logger.info(f"[kill_with_cleanup] Initiating safe kill of {task_label}")

        # 1. Signal the OS-level process if we have a PID
        if owner.pid:
            self._kill_process(owner.pid, owner.task_name)

        # 2. Wait for the worker thread to exit so sessions are released naturally
        thread_exited = False
        if owner.thread_id:
            deadline = time.monotonic() + wait_secs
            while time.monotonic() < deadline:
                # Check if that thread ID is still alive
                alive_ids = {t.ident for t in threading.enumerate() if t.ident is not None}
                if owner.thread_id not in alive_ids:
                    thread_exited = True
                    break
                time.sleep(0.1)

            if thread_exited:
                logger.info(f"[kill_with_cleanup] Thread for {task_label} exited cleanly.")
            else:
                logger.warning(
                    f"[kill_with_cleanup] Thread for {task_label} did not exit within "
                    f"{wait_secs}s — forcing session cleanup anyway."
                )

        # 3. Release any DB sessions the thread may still be holding
        self._release_db_sessions_for_thread(owner.thread_id)

        # 4. Unregister
        self.unregister_process(registration_id)

        msg = (
            f"Process {task_label} terminated (thread_exited={thread_exited}, "
            f"pid={owner.pid}, thread={owner.thread_id})"
        )
        logger.info(f"[kill_with_cleanup] {msg}")
        return True, msg

    def _release_db_sessions_for_thread(self, thread_id: Optional[int]) -> None:
        """
        Flush thread-local SQLAlchemy sessions that a worker thread may have open.
        This is the same cleanup that _execute_wrapper runs on normal job completion.
        """
        try:
            from database.working_database import working_session_registry
            working_session_registry.remove()
        except Exception as e:
            logger.debug(f"[kill_with_cleanup] working_session_registry.remove(): {e}")

        try:
            from database.music_database import music_session_registry
            music_session_registry.remove()
        except Exception as e:
            logger.debug(f"[kill_with_cleanup] music_session_registry.remove(): {e}")

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

    def get_active_processes_with_ids(self, owner_id: Optional[str] = None) -> List[dict]:
        """
        Same as get_active_processes but includes the registration_id in each entry.
        Used by the REST API so the frontend can reference specific processes for kill.

        Returns:
            List of dicts with registration_id plus all ProcessOwner fields.
        """
        with self._lock:
            items = list(self._processes.items())

        result = []
        for reg_id, owner in items:
            if owner_id and owner.owner_id != owner_id:
                continue
            d = owner.model_dump()
            d["registration_id"] = reg_id
            # Convert datetime to ISO string for JSON serialisation
            if d.get("started_at") and hasattr(d["started_at"], "isoformat"):
                d["started_at"] = d["started_at"].isoformat()
            result.append(d)
        return result


# Global ProcessSupervisor singleton
supervisor = ProcessSupervisor()
