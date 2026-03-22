"""
Lightweight job queue / task scheduler for SoulSync.
- Supports periodic and one-off jobs
- Enable/disable per job
- Retry with backoff
- Registration API for future plugins
- Minimal in-memory, thread-based runner (no external deps)
"""

import heapq
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, List
from database.working_database import get_working_database
from core.tiered_logger import get_logger
from core.settings import config_manager

logger = get_logger("job_queue")


@dataclass(order=True)
class ScheduledJob:
    next_run: float
    sort_index: int = field(init=False, repr=False)
    name: str = field(compare=False)
    func: Callable[[], Any] = field(compare=False)
    interval_seconds: Optional[float] = field(default=None, compare=False)
    enabled: bool = field(default=True, compare=False)
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

    def __post_init__(self):
        # sort_index ensures heapq stability even if next_run ties
        self.sort_index = id(self)


class JobQueue:
    def __init__(self, worker_count: int = 2, poll_interval: float = 0.5):
        self._lock = threading.Lock()
        self._jobs: Dict[str, ScheduledJob] = {}
        self._heap: List[ScheduledJob] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._workers = threading.BoundedSemaphore(worker_count)
        self._poll_interval = poll_interval
        self._is_running: Dict[str, bool] = {}  # Concurrency lock: job_name -> is_currently_running

    def _release_worker_resources(self):
        """Return any working DB connections opened by background jobs to the engine."""
        try:
            get_working_database().dispose()
        except Exception as e:
            logger.debug(f"Failed to dispose working database after job execution: {e}")

    def _remove_from_heap(self, name: str):
        self._heap = [job for job in self._heap if job.name != name]
        heapq.heapify(self._heap)

    def _finalize_job_after_run(self, job: ScheduledJob, finished_at: float) -> None:
        """Finalize job state after an execution attempt.

        One-time jobs (interval_seconds is None) are transient and must be removed from
        registry/heap once finished so they do not keep showing up in API/UI job lists.
        """
        job.last_finished = finished_at
        job.running = False
        self._is_running[job.name] = False

        if job.interval_seconds is not None:
            if job.enabled:
                job.next_run = finished_at + job.interval_seconds
                heapq.heappush(self._heap, job)
            return

        # Purge transient one-time jobs to prevent "ghost" stale entries in UI.
        self._remove_from_heap(job.name)
        self._jobs.pop(job.name, None)

    # Public API
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
        max_retries: int = 0,
        backoff_base: float = 5.0,
        backoff_factor: float = 2.0,
        tags: Optional[List[str]] = None,
        plugin: Optional[str] = None,
    ) -> None:
        """
        Register a job. If interval_seconds is provided, job is periodic; otherwise one-off.

        Checks config for any saved interval overrides for this job.
        """
        with self._lock:
            # Check for saved overrides in config
            saved_config = config_manager.get(f"jobs.{name}")
            if saved_config and isinstance(saved_config, dict):
                saved_interval = saved_config.get("interval_seconds")
                if saved_interval is not None:
                    interval_seconds = float(saved_interval)
                    logger.debug(f"Applied saved interval override for {name}: {interval_seconds}s")

            # When start_after is 0 for a periodic job, schedule the first run one full
            # interval from now rather than immediately.  Running at "now" risks the job
            # being popped from the heap before the queue's worker loop is running, which
            # can leave it stuck in a permanent «Pending» state with no future next_run.
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
                max_retries=max_retries,
                backoff_base=backoff_base,
                backoff_factor=backoff_factor,
                tags=tags or [],
                plugin=plugin,
            )

            # If job already exists, remove it from heap first (idempotency)
            if name in self._jobs:
                self._remove_from_heap(name)

            self._jobs[name] = job
            heapq.heappush(self._heap, job)
            logger.info(f"Registered job: {name}")

    def update_job_interval(self, name: str, interval_seconds: float) -> bool:
        """
        Update a job's interval and persist to config.
        """
        with self._lock:
            job = self._jobs.get(name)
            if not job:
                return False

            job.interval_seconds = interval_seconds

            # Persist to config
            try:
                # We need to ensure the parent 'jobs' key exists if we are going deep
                current_jobs_config = config_manager.get("jobs", {})
                if not isinstance(current_jobs_config, dict):
                    current_jobs_config = {}

                job_config = current_jobs_config.get(name, {})
                job_config["interval_seconds"] = interval_seconds
                current_jobs_config[name] = job_config

                config_manager.set("jobs", current_jobs_config)
                logger.info(f"Updated and persisted interval for job '{name}': {interval_seconds}s")
            except Exception as e:
                logger.error(f"Failed to persist job interval for '{name}': {e}")

            return True

    def enable_job(self, name: str):
        with self._lock:
            job = self._jobs.get(name)
            if job:
                job.enabled = True
                job.current_retries = 0
                job.last_error = None
                job.last_error_time = None
                self._remove_from_heap(name)
                job.next_run = time.time()
                heapq.heappush(self._heap, job)
                logger.info(f"Enabled job '{name}' (cleared error state)")

    def disable_job(self, name: str):
        with self._lock:
            job = self._jobs.get(name)
            if job:
                job.enabled = False
                logger.info(f"Disabled job '{name}'")

    def unregister_job(self, name: str):
        with self._lock:
            if name in self._jobs:
                self._remove_from_heap(name)
                del self._jobs[name]
                logger.info(f"Unregistered job '{name}'")

    def run_now(self, name: str):
        with self._lock:
            job = self._jobs.get(name)
            if job and job.enabled:
                self._remove_from_heap(name)
                job.next_run = time.time()
                heapq.heappush(self._heap, job)
                logger.info(f"Scheduled immediate run for '{name}'")

    def execute_job_now(self, name: str) -> bool:
        """Execute a job immediately in a background thread without affecting its scheduled interval.
        
        This is useful for manual UI triggers that should not reset the APScheduler interval.
        Returns True if job was executed, False if job not found or already running.
        """
        with self._lock:
            job = self._jobs.get(name)
            if not job or not job.enabled:
                logger.warning(f"Cannot execute job '{name}': not found or disabled")
                return False
            
            # Check if already running
            if self._is_running.get(name, False):
                logger.warning(f"Job '{name}' is already running, skipping duplicate execution")
                return False
            
            # Mark as running — will be cleared by _run_job_thread's finally block
            self._is_running[name] = True
        
        # Execute in a background thread outside the lock
        def _run_job_thread():
            try:
                logger.info(f"Starting manual execution of job '{name}'")
                job.running = True
                job.last_started = time.time()
                job.func()
                job.last_finished = time.time()
                job.last_success = job.last_finished
                job.total_successes += 1
                job.current_retries = 0
                job.last_error = None
                logger.info(f"Manual execution of job '{name}' completed successfully")
            except Exception as e:
                job.last_finished = time.time()
                job.last_error = str(e)
                job.last_error_time = job.last_finished
                job.total_failures += 1
                logger.error(f"Error during manual execution of job '{name}': {e}")
            finally:
                with self._lock:
                    self._finalize_job_after_run(job, time.time())
                self._release_worker_resources()
        
        try:
            thread = threading.Thread(target=_run_job_thread, daemon=True)
            thread.start()
        except Exception:
            # Thread failed to start — release the lock so the job is not permanently stuck
            with self._lock:
                self._is_running[name] = False
            raise
        logger.info(f"Spawned background thread for manual execution of job '{name}'")
        return True

    def schedule_in(self, name: str, delay_seconds: float):
        with self._lock:
            job = self._jobs.get(name)
            if job and job.enabled:
                # Clear any existing heap entry so we do not accumulate duplicates
                self._remove_from_heap(name)
                job.manual_next_run = time.time() + max(delay_seconds, 0.0)
                job.next_run = job.manual_next_run
                heapq.heappush(self._heap, job)
                logger.info(f"Rescheduled job '{name}' to run in {delay_seconds} seconds")

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self._lock:
            result = []
            for job in self._jobs.values():
                result.append({
                    "name": job.name,
                    "enabled": job.enabled,
                    "next_run": job.next_run,
                    "interval_seconds": job.interval_seconds,
                    "running": job.running,
                    "current_retries": job.current_retries,
                    "last_error": job.last_error,
                    "last_error_time": job.last_error_time,
                    "total_failures": job.total_failures,
                    "total_successes": job.total_successes,
                    "last_started": job.last_started,
                    "last_finished": job.last_finished,
                    "last_success": job.last_success,
                    "tags": job.tags,
                    "plugin": job.plugin,
                })
            return result

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get list of currently running jobs."""
        with self._lock:
            result = []
            for job in self._jobs.values():
                if job.running:
                    result.append({
                        "name": job.name,
                        "enabled": job.enabled,
                        "next_run": job.next_run,
                        "interval_seconds": job.interval_seconds,
                        "running": job.running,
                        "current_retries": job.current_retries,
                        "last_error": job.last_error,
                        "last_started": job.last_started,
                        "last_finished": job.last_finished,
                        "last_success": job.last_success,
                        "tags": job.tags,
                        "plugin": job.plugin,
                    })
            return result

    # Internal runner
    def _is_job_running(self, name: str) -> bool:
        """Check if a job is currently executing."""
        with self._lock:
            return self._is_running.get(name, False) or self._jobs.get(name, ScheduledJob(time.time(), "_dummy", lambda: None)).running

    def _run_loop(self):
        while self._running:
            with self._lock:
                now = time.time()
                while self._heap and self._heap[0].next_run <= now:
                    job = heapq.heappop(self._heap)
                    if job.enabled:
                        self._execute_job(job)
                    elif job.manual_next_run:
                        job.next_run = job.manual_next_run
                        heapq.heappush(self._heap, job)

            time.sleep(self._poll_interval)

    def _execute_job(self, job: ScheduledJob):
        # Check for duplicate jobs (prevent same job from running twice simultaneously)
        # Exception: sync jobs can have multiple instances (individually registered) and run concurrently
        if 'sync_job' not in job.name:
            for other_job in self._jobs.values():
                if other_job.name == job.name and other_job.running:
                    logger.warning(
                        f"Job '{job.name}' is already running. Skipping duplicate execution. "
                        f"If this happens frequently, check for long-running processes or scheduling conflicts."
                    )
                    return
        
        if not self._workers.acquire(blocking=False):
            logger.warning(f"No available workers for job: {job.name}")
            return

        # _is_running is set here; the worker's finally block clears it via _finalize_job_after_run.
        # The try/except below ensures it is also cleared if Thread.start() itself fails.
        self._is_running[job.name] = True

        def worker():
            attempt = 0
            try:
                while True:
                    try:
                        # Log health checks at DEBUG, other jobs at INFO
                        log_level = logger.debug if 'health_check' in job.name else logger.info
                        log_level(f"Starting job: {job.name} (attempt {attempt + 1})")
                        job.running = True
                        job.last_started = time.time()
                        job.func()
                        job.last_success = time.time()
                        job.last_error = None
                        job.last_error_time = None
                        job.current_retries = 0
                        job.total_successes += 1
                        log_level(f"Completed job: {job.name}")
                        break
                    except Exception as e:
                        error_msg = str(e)
                        job.last_error = error_msg
                        job.last_error_time = time.time()
                        job.current_retries += 1
                        job.total_failures += 1
                        attempt += 1
                        logger.error(f"Job failed: {job.name}, attempt {attempt}, error: {e}", exc_info=True)

                        if job.current_retries >= job.max_retries:
                            logger.error(
                                f"Job '{job.name}' exceeded max retries ({job.max_retries}); giving up. "
                                f"Total failures: {job.total_failures}"
                            )
                            break

                        backoff = job.backoff_base * (job.backoff_factor ** (job.current_retries - 1))
                        logger.info(f"Retrying job '{job.name}' in {backoff:.1f}s")
                        time.sleep(backoff)
                        continue
            finally:
                with self._lock:
                    self._finalize_job_after_run(job, time.time())
                self._workers.release()
                self._release_worker_resources()

        try:
            threading.Thread(target=worker, daemon=True).start()
        except Exception:
            # Thread failed to start — release semaphore and lock so resources are not leaked
            with self._lock:
                self._is_running[job.name] = False
            self._workers.release()
            raise


# Global singleton
job_queue = JobQueue()


def register_job(**kwargs):
    job_queue.register_job(**kwargs)


def enable_job(name: str):
    job_queue.enable_job(name)


def disable_job(name: str):
    job_queue.disable_job(name)


def unregister_job(name: str):
    job_queue.unregister_job(name)


def run_job_now(name: str):
    job_queue.run_now(name)


def schedule_job_in(name: str, delay_seconds: float):
    job_queue.schedule_in(name, delay_seconds)


def list_jobs():
    return job_queue.list_jobs()


def start_job_queue():
    job_queue.start()


def stop_job_queue():
    job_queue.stop()

def update_job_interval(name: str, interval_seconds: float) -> bool:
    return job_queue.update_job_interval(name, interval_seconds)
