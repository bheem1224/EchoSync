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
from core.tiered_logger import get_logger

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

    def _remove_from_heap(self, name: str):
        self._heap = [job for job in self._heap if job.name != name]
        heapq.heapify(self._heap)

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
        """
        with self._lock:
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
            self._jobs[name] = job
            heapq.heappush(self._heap, job)
            logger.info(f"Registered job: {name}")

    def enable_job(self, name: str):
        with self._lock:
            job = self._jobs.get(name)
            if job:
                job.enabled = True
                job.current_retries = 0
                job.last_error = None
                self._remove_from_heap(name)
                job.next_run = time.time()
                heapq.heappush(self._heap, job)
                logger.info(f"Enabled job '{name}'")

    def disable_job(self, name: str):
        with self._lock:
            job = self._jobs.get(name)
            if job:
                job.enabled = False
                logger.info(f"Disabled job '{name}'")

    def run_now(self, name: str):
        with self._lock:
            job = self._jobs.get(name)
            if job and job.enabled:
                self._remove_from_heap(name)
                job.next_run = time.time()
                heapq.heappush(self._heap, job)
                logger.info(f"Scheduled immediate run for '{name}'")

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
        if not self._workers.acquire(blocking=False):
            logger.warning(f"No available workers for job: {job.name}")
            return

        def worker():
            attempt = 0
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
                    job.current_retries = 0
                    log_level(f"Completed job: {job.name}")
                    break
                except Exception as e:
                    job.last_error = str(e)
                    job.current_retries += 1
                    attempt += 1
                    logger.error(f"Job failed: {job.name}, attempt {attempt}, error: {e}")

                    if job.current_retries >= job.max_retries:
                        logger.error(
                            f"Job '{job.name}' exceeded max retries ({job.max_retries}); giving up"
                        )
                        break

                    backoff = job.backoff_base * (job.backoff_factor ** (job.current_retries - 1))
                    logger.info(f"Retrying job '{job.name}' in {backoff:.1f}s")
                    time.sleep(backoff)
                    continue
                finally:
                    job.last_finished = time.time()
                    job.running = False

            self._workers.release()

            if job.interval_seconds:
                job.next_run = time.time() + job.interval_seconds
                heapq.heappush(self._heap, job)

        threading.Thread(target=worker, daemon=True).start()


# Global singleton
job_queue = JobQueue()


def register_job(**kwargs):
    job_queue.register_job(**kwargs)


def enable_job(name: str):
    job_queue.enable_job(name)


def disable_job(name: str):
    job_queue.disable_job(name)


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
