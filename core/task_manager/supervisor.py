import os
import signal
import sys
import threading
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any
from core.tiered_logger import get_logger
from core.task_manager.models import ProcessOwner, ProcessCategory

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = get_logger("process_supervisor")


class ProcessSupervisor:
    """
    Tracks process ownership and manages active thread or sub-process PID registrations.
    Enables safe termination of tasks registered under a specific owner_id.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._processes: Dict[str, ProcessOwner] = {}
        self._wasm_wrappers: Dict[str, Any] = {}
        self._cancellation_events: Dict[str, threading.Event] = {}

    def register_process(self, owner: ProcessOwner, wasm_wrapper: Optional[Any] = None, cancellation_event: Optional[threading.Event] = None) -> str:
        """
        Registers an active thread, WASM instance, or sub-process PID.

        Args:
            owner: ProcessOwner instance describing ownership and metadata.
            wasm_wrapper: Optional reference to the WasmPluginWrapper for epoch interrupts.
            cancellation_event: Optional threading.Event for cooperative worker thread cancellation.

        Returns:
            str: Unique registration ID.
        """
        registration_id = f"{owner.owner_id}_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._processes[registration_id] = owner
            if wasm_wrapper:
                self._wasm_wrappers[registration_id] = wasm_wrapper
            if cancellation_event:
                self._cancellation_events[registration_id] = cancellation_event
                
        logger.debug(
            f"Registered {owner.category.value} '{registration_id}' for owner '{owner.owner_id}' "
            f"(PID: {owner.pid}, Thread: {owner.thread_id}, Task: {owner.task_name})"
        )
        return registration_id

    def unregister_process(self, registration_id: str) -> None:
        """
        Removes completed or stopped tasks from the process registry.
        """
        with self._lock:
            removed = self._processes.pop(registration_id, None)
            self._wasm_wrappers.pop(registration_id, None)
            self._cancellation_events.pop(registration_id, None)
            
        if removed:
            logger.debug(f"Unregistered process '{registration_id}' for owner '{removed.owner_id}'")

    def terminate_owner_processes(self, owner_id: str) -> None:
        """
        Kills all sub-processes/threads registered under owner_id.
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
            self.kill_with_cleanup(reg_id)

    def kill_with_cleanup(self, registration_id: str, wait_secs: float = 3.0) -> Tuple[bool, str]:
        """
        Safely terminate a specific registered process based on its category.
        Releases DB sessions it may be holding to prevent corruption.
        """
        with self._lock:
            owner = self._processes.get(registration_id)
            wasm_wrapper = self._wasm_wrappers.get(registration_id)
            cancel_event = self._cancellation_events.get(registration_id)

        if not owner:
            return False, f"No process with registration_id '{registration_id}' found"

        if not owner.is_killable:
            return False, f"Process '{owner.task_name}' is a Core System task and cannot be terminated."

        task_label = f"'{owner.task_name}' (owner={owner.owner_id})"
        logger.info(f"[kill_with_cleanup] Initiating safe kill of {task_label} ({owner.category.value})")

        thread_exited = False

        if owner.category == ProcessCategory.WASM_SANDBOX:
            if wasm_wrapper and hasattr(wasm_wrapper, "engine"):
                try:
                    wasm_wrapper.engine.increment_epoch()
                    logger.info(f"[kill_with_cleanup] Triggered epoch interrupt for WASM Sandbox: {task_label}")
                except Exception as e:
                    logger.error(f"[kill_with_cleanup] Failed to trigger epoch interrupt: {e}")
            else:
                logger.warning(f"[kill_with_cleanup] No WASM engine found to interrupt for {task_label}")
                
        elif owner.category == ProcessCategory.WORKER_THREAD:
            if cancel_event:
                cancel_event.set()
                logger.info(f"[kill_with_cleanup] Set cooperative cancellation flag for {task_label}")
            else:
                logger.warning(f"[kill_with_cleanup] No cancellation event provided for worker thread {task_label}. Relying solely on DB session release.")
                
        elif owner.category == ProcessCategory.OS_SUBPROCESS:
            if owner.pid:
                self._kill_process(owner.pid, owner.task_name)
                
        # For any thread-based task, wait for clean exit
        if owner.thread_id:
            deadline = time.monotonic() + wait_secs
            while time.monotonic() < deadline:
                alive_ids = {t.ident for t in threading.enumerate() if t.ident is not None}
                if owner.thread_id not in alive_ids:
                    thread_exited = True
                    break
                time.sleep(0.1)

            if thread_exited:
                logger.info(f"[kill_with_cleanup] Thread for {task_label} exited cleanly.")
            else:
                logger.warning(f"[kill_with_cleanup] Thread for {task_label} did not exit within {wait_secs}s — forcing session cleanup anyway.")

        # Release any DB sessions the thread may still be holding
        if owner.thread_id:
            self._release_db_sessions_for_thread(owner.thread_id)

        # Unregister
        self.unregister_process(registration_id)

        msg = f"Process {task_label} terminated (category={owner.category.value})"
        logger.info(f"[kill_with_cleanup] {msg}")
        return True, msg

    def _release_db_sessions_for_thread(self, thread_id: Optional[int]) -> None:
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
        try:
            if sys.platform == "win32":
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    os.kill(pid, signal.SIGABRT)
            else:
                os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent termination signal to process PID {pid} (Task: {task_name})")
        except (ProcessLookupError, OSError) as exc:
            logger.debug(f"Process PID {pid} (Task: {task_name}) was already terminated or not found: {exc}")

    def get_active_processes(self, owner_id: Optional[str] = None) -> List[ProcessOwner]:
        with self._lock:
            if owner_id:
                return [p for p in self._processes.values() if p.owner_id == owner_id]
            return list(self._processes.values())

    def get_active_processes_with_ids(self, owner_id: Optional[str] = None) -> List[dict]:
        with self._lock:
            items = list(self._processes.items())
            
        result = []
        for reg_id, owner in items:
            if owner_id and owner.owner_id != owner_id:
                continue
                
            # Aggregate system metrics dynamically
            if HAS_PSUTIL and owner.pid and owner.category == ProcessCategory.OS_SUBPROCESS:
                try:
                    p = psutil.Process(owner.pid)
                    owner.cpu_percent = p.cpu_percent(interval=None)
                    owner.memory_bytes = p.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
            
            # Aggregate WASM metrics
            if owner.category == ProcessCategory.WASM_SANDBOX:
                wasm_wrapper = self._wasm_wrappers.get(reg_id)
                if wasm_wrapper and hasattr(wasm_wrapper, "store"):
                    try:
                        owner.memory_bytes = 0 # Cannot easily query linear memory without exports, leave as 0 or mock
                        # if hasattr(wasm_wrapper.store, "fuel_consumed"):
                        #     owner.cpu_percent = float(wasm_wrapper.store.fuel_consumed())
                    except Exception:
                        pass
                
            d = owner.model_dump()
            d["registration_id"] = reg_id
            if d.get("started_at") and hasattr(d["started_at"], "isoformat"):
                d["started_at"] = d["started_at"].isoformat()
            result.append(d)
            
        return result


    # Global ProcessSupervisor singleton
supervisor = ProcessSupervisor()

# Register core system workers
try:
    from core.task_manager.models import ProcessOwner, OwnerType, ProcessCategory
    import threading

    supervisor.register_process(
        ProcessOwner(
            owner_id="core.scheduler",
            owner_type=OwnerType.CORE,
            task_name="Task Scheduler Daemon",
            category=ProcessCategory.CORE_SYSTEM,
            is_killable=False,
            thread_id=threading.main_thread().ident
        )
    )
except Exception:
    pass
