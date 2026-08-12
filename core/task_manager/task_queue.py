"""
Refactored Job Queue / Task Manager Scaffold with Collision Avoidance and FFI Cancellation.
Supports TaskCategory enums (GENERAL, CRITICAL, DATABASE_WRITE_HEAVY) and TaskState tracking.
Prevents concurrent execution of multiple DATABASE_WRITE_HEAVY tasks to avoid DB lock amplification.
"""
from enum import Enum
import heapq
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, List
from core.tiered_logger import get_logger
from core.settings import config_manager

logger = get_logger("job_queue")


class TaskCategory(str, Enum):
    GENERAL = "general"
    CRITICAL = "critical"
    DATABASE_WRITE_HEAVY = "database_write_heavy"


class TaskState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PENDING = "pending"
    PENDING_BLOCKED = "pending_blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class ScheduledJob:
    next_run: float
    sort_index: int = field(init=False, repr=False)
    name: str = field(compare=False)
    func: Callable[[], Any] = field(compare=False)
    interval_seconds: Optional[float] = field(default=None, compare=False)
    enabled: bool = field(default=True, compare=False)
    category: TaskCategory = field(default=TaskCategory.GENERAL, compare=False)
    state: TaskState = field(default=TaskState.IDLE, compare=False)
    cancel_token: Optional[Any] = field(default=None, compare=False)
    max_retries: int = field(default=0, compare=False)
    backoff_base: float = field(default=5.0, compare=False)
    backoff_factor: float = field(default=2.0, compare=False)
    current_retries: int = field(default=0, compare=False)
    last_error: Optional[str] = field(default=None, compare=False)
    last_error_time: Optional[float] = field(default=None, compare=False)
    total_failures: int = field(default=0, compare=False)
    total_successes: int = field(default=0, compare=False)
    last_started: Optional[float] = field(default=None, compare=False)
    last_finished: Optional[float] = field(default=None, compare=False)
    last_success: Optional[float] = field(default=None, compare=False)
    running: bool = field(default=False, compare=False)
    tags: List[str] = field(default_factory=list, compare=False)
    plugin: Optional[str] = field(default=None, compare=False)
    manual_next_run: Optional[float] = field(default=None, compare=False)
    params: Optional[Dict[str, Any]] = field(default=None, compare=False)

    def __post_init__(self):
        self.sort_index = id(self)

    def to_dict(self) -> Dict[str, Any]:
        import time as _time
        now = _time.time()
        duration_s = None
        if self.running and self.last_started:
            duration_s = round(now - self.last_started, 1)
        return {
            "name": self.name,
            "category": self.category.value if isinstance(self.category, TaskCategory) else str(self.category),
            "state": self.state.value if isinstance(self.state, TaskState) else str(self.state),
            "enabled": self.enabled,
            "running": self.running,
            "next_run": self.next_run,
            "interval_seconds": self.interval_seconds,
            "tags": self.tags,
            "plugin": self.plugin,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time,
            "last_started": self.last_started,
            "last_finished": self.last_finished,
            "duration_seconds": duration_s,
        }



class JobQueue:
    RESTART_PENDING = False

    def __init__(self, worker_count: int = 2, poll_interval: float = 0.5):
        self._lock = threading.RLock()
        self._jobs: Dict[str, ScheduledJob] = {}
        self._heap: List[ScheduledJob] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._core_workers = threading.BoundedSemaphore(2)
        self._general_workers = threading.BoundedSemaphore(worker_count)
        self._poll_interval = poll_interval
        self._is_running: Dict[str, bool] = {}
        self._active_threads: Dict[str, threading.Thread] = {}
        self._active_processes: Dict[str, Any] = {}

    def _release_worker_resources(self):
        try:
            from database.working_database import working_session_registry
            working_session_registry.remove()
        except Exception as e:
            logger.error(f"Failed to remove working session registry: {e}")

        try:
            from database.music_database import music_session_registry
            music_session_registry.remove()
        except Exception as e:
            logger.error(f"Failed to remove music session registry: {e}")

    def _remove_from_heap(self, name: str):
        self._heap = [job for job in self._heap if job.name != name]
        heapq.heapify(self._heap)

    def is_db_write_heavy_running(self) -> bool:
        """Check if any DATABASE_WRITE_HEAVY task is currently running."""
        with self._lock:
            return any(
                job.running and job.category == TaskCategory.DATABASE_WRITE_HEAVY
                for job in self._jobs.values()
            )

    def can_execute(self, job: ScheduledJob) -> bool:
        """
        Evaluate job against currently running jobs for collision avoidance and capability gating.
        Rule: If job.plugin is set, evaluate plugin_state_manager.can_accept_work(job.plugin).
        Rule: If a DATABASE_WRITE_HEAVY task is running, new DATABASE_WRITE_HEAVY tasks are blocked.
        """
        with self._lock:
            if job.plugin:
                from core.task_manager.plugin_state import plugin_state_manager
                if not plugin_state_manager.can_accept_work(job.plugin):
                    if job.state != TaskState.PENDING_BLOCKED:
                        status = plugin_state_manager.get_state(job.plugin)
                        logger.warning(
                            f"Job '{job.name}' blocked from execution: plugin '{job.plugin}' cannot accept work "
                            f"(state: {status.state.value})"
                        )
                    job.state = TaskState.PENDING_BLOCKED
                    job.next_run = time.time() + 10.0
                    return False

            if job.category == TaskCategory.DATABASE_WRITE_HEAVY:
                if self.is_db_write_heavy_running():
                    job.state = TaskState.PENDING_BLOCKED
                    return False
            return True

    def cancel_job(self, name: str) -> bool:
        """
        Cancel a running or scheduled job cleanly.
        If the job carries a CancellationToken, call .cancel() to trigger FFI bailout.
        Transition state to CANCELLED.
        """
        with self._lock:
            job = self._jobs.get(name)
            if not job:
                return False

            if job.cancel_token and hasattr(job.cancel_token, "cancel"):
                try:
                    job.cancel_token.cancel()
                    logger.info(f"Triggered cross-FFI cancellation token for job: {name}")
                except Exception as e:
                    logger.error(f"Error signaling cancel_token for {name}: {e}")

            job.running = False
            job.state = TaskState.CANCELLED
            job.last_error = "Cancelled by user"
            self._is_running[job.name] = False
            return True

    def unregister_job(self, name: str) -> bool:
        """
        Cancel and completely remove a job from the queue.
        """
        with self._lock:
            if name not in self._jobs:
                return False
            
            self.cancel_job(name)
            self._remove_from_heap(name)
            self._jobs.pop(name, None)
            return True

    def _finalize_job_after_run(self, job: ScheduledJob, finished_at: float) -> None:
        job.last_finished = finished_at
        job.running = False
        if job.state != TaskState.CANCELLED:
            job.state = TaskState.COMPLETED if not job.last_error else TaskState.FAILED
        job.params = None
        self._is_running[job.name] = False
        self._active_threads.pop(job.name, None)

        if job.interval_seconds is not None:
            if job.enabled and job.state != TaskState.CANCELLED:
                job.next_run = finished_at + job.interval_seconds
                job.state = TaskState.IDLE
                heapq.heappush(self._heap, job)
            return

        self._remove_from_heap(job.name)
        self._jobs.pop(job.name, None)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("JobQueue started")

    def stop(self, timeout: float = 5.0):
        self._running = False
        if self._thread:
            self._thread.join(timeout=timeout)
        logger.info("JobQueue stopped")

    def register_job(
        self,
        name: str,
        func: Callable[[], Any],
        interval_seconds: Optional[float] = None,
        start_after: float = 0.0,
        enabled: bool = True,
        category: TaskCategory = TaskCategory.GENERAL,
        cancel_token: Optional[Any] = None,
        max_retries: int = 0,
        backoff_base: float = 5.0,
        backoff_factor: float = 2.0,
        tags: Optional[List[str]] = None,
        plugin: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        _MAX_RETRIES_CAP = 10
        max_retries = max(0, min(max_retries, _MAX_RETRIES_CAP))

        with self._lock:
            if start_after == 0.0 and interval_seconds is not None:
                next_run = time.time() + interval_seconds
            else:
                next_run = time.time() + max(start_after, 0.0)

            job = ScheduledJob(
                next_run=next_run,
                name=name,
                func=func,
                interval_seconds=interval_seconds,
                enabled=enabled,
                category=category,
                state=TaskState.PENDING if enabled else TaskState.IDLE,
                cancel_token=cancel_token,
                max_retries=max_retries,
                backoff_base=backoff_base,
                backoff_factor=backoff_factor,
                tags=tags or [],
                plugin=plugin,
                params=params,
            )

            if name in self._jobs:
                self._remove_from_heap(name)

            self._jobs[name] = job
            heapq.heappush(self._heap, job)
            logger.info(f"Registered job: {name} [Category: {category}]")

    def execute_job_now(self, name: str, params: Optional[Dict[str, Any]] = None) -> bool:
        with self._lock:
            job = self._jobs.get(name)
            if not job:
                return False

            if job.running or self._is_running.get(name, False):
                logger.warning(f"Job {name} is already running")
                return False

            if not self.can_execute(job):
                logger.warning(f"Job {name} blocked due to collision avoidance (DATABASE_WRITE_HEAVY task running)")
                return False

            job.manual_next_run = time.time()
            if params:
                job.params = params

            self._remove_from_heap(name)
            job.next_run = job.manual_next_run
            heapq.heappush(self._heap, job)
            return True

    def get_queue_state(self) -> Dict[str, Any]:
        """
        Return serializable representation of full queue state for SSE telemetry.
        """
        with self._lock:
            running = []
            pending = []
            blocked = []

            for job in self._jobs.values():
                d = job.to_dict()
                if job.running or job.state == TaskState.RUNNING:
                    running.append(d)
                elif job.state == TaskState.PENDING_BLOCKED:
                    blocked.append(d)
                else:
                    pending.append(d)

            return {
                "running_jobs": running,
                "pending_jobs": pending,
                "blocked_jobs": blocked,
                "stats": {
                    "total": len(self._jobs),
                    "running": len(running),
                    "pending": len(pending),
                    "blocked": len(blocked)
                }
            }

    def _run_loop(self):
        while self._running:
            time.sleep(self._poll_interval)
            now = time.time()
            to_run = []

            with self._lock:
                while self._heap and self._heap[0].next_run <= now:
                    job = heapq.heappop(self._heap)
                    if job.enabled and not job.running:
                        if self.can_execute(job):
                            job.running = True
                            job.state = TaskState.RUNNING
                            self._is_running[job.name] = True
                            to_run.append(job)
                        else:
                            job.next_run = now + self._poll_interval
                            heapq.heappush(self._heap, job)

            for job in to_run:
                thread = threading.Thread(target=self._execute_wrapper, args=(job,), daemon=True)
                with self._lock:
                    self._active_threads[job.name] = thread
                thread.start()

    def _execute_wrapper(self, job: ScheduledJob):
        started_at = time.time()
        job.last_started = started_at
        reg_id = None
        try:
            import os
            from core.task_manager.supervisor import supervisor
            from core.task_manager.models import ProcessOwner, OwnerType
            owner_id = job.plugin if job.plugin else "core.system_job"
            owner_type = OwnerType.PLUGIN if job.plugin else OwnerType.SYSTEM_JOB
            owner = ProcessOwner(
                owner_id=owner_id,
                owner_type=owner_type,
                pid=None,
                thread_id=threading.get_ident(),
                task_name=job.name
            )
            reg_id = supervisor.register_process(owner)
        except Exception:
            pass

        try:
            if job.params:
                job.func(**job.params)
            else:
                job.func()
            job.total_successes += 1
            job.last_error = None
        except Exception as e:
            job.total_failures += 1
            job.last_error = str(e)
            job.last_error_time = time.time()
            logger.error(f"Job {job.name} failed: {e}", exc_info=True)
        finally:
            if reg_id:
                try:
                    from core.task_manager.supervisor import supervisor
                    supervisor.unregister_process(reg_id)
                except Exception:
                    pass
            self._release_worker_resources()
            with self._lock:
                self._finalize_job_after_run(job, time.time())

    def _execute_job(self, job: ScheduledJob):
        """Alias for _execute_wrapper for test suite compatibility."""
        self._execute_wrapper(job)

    def kill_job(self, name: str) -> bool:
        """Alias for cancel_job for backward compatibility."""
        return self.cancel_job(name)

    def kill_jobs_by_plugin(self, plugin_id: str) -> int:
        """Cancel all jobs associated with a specific plugin."""
        count = 0
        with self._lock:
            names_to_cancel = [name for name, job in self._jobs.items() if job.plugin == plugin_id]
            for name in names_to_cancel:
                if self.cancel_job(name):
                    count += 1
        return count

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Return a list of all registered jobs as dictionaries."""
        with self._lock:
            return [job.to_dict() for job in self._jobs.values()]


job_queue = JobQueue()


def list_jobs() -> List[Dict[str, Any]]:
    """Top-level helper function to return all registered jobs as dictionaries."""
    return job_queue.list_jobs()


def update_job_interval(name: str, interval_seconds: float) -> bool:
    """Top-level helper function to update job interval."""
    with job_queue._lock:
        job = job_queue._jobs.get(name)
        if not job:
            return False
        job.interval_seconds = interval_seconds
        return True


def start_job_queue() -> None:
    """Top-level helper function to start global job_queue."""
    job_queue.start()


def stop_job_queue(timeout: float = 5.0) -> None:
    """Top-level helper function to stop global job_queue."""
    job_queue.stop(timeout=timeout)


def register_job(
    name: str,
    func: Callable[[], Any],
    interval_seconds: Optional[float] = None,
    start_after: float = 0.0,
    enabled: bool = True,
    category: TaskCategory = TaskCategory.GENERAL,
    cancel_token: Optional[Any] = None,
    max_retries: int = 0,
    backoff_base: float = 5.0,
    backoff_factor: float = 2.0,
    tags: Optional[List[str]] = None,
    plugin: Optional[str] = None,
) -> None:
    """Top-level helper function to register a job on the global job_queue."""
    job_queue.register_job(
        name=name,
        func=func,
        interval_seconds=interval_seconds,
        start_after=start_after,
        enabled=enabled,
        category=category,
        cancel_token=cancel_token,
        max_retries=max_retries,
        backoff_base=backoff_base,
        backoff_factor=backoff_factor,
        tags=tags,
        plugin=plugin,
    )


def unregister_job(name: str) -> bool:
    """Top-level helper function to unregister/cancel a job on global job_queue."""
    return job_queue.cancel_job(name)
