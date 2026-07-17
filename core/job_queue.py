"""
Lightweight job queue / task scheduler for Echosync.
- Supports periodic and one-off jobs
- Enable/disable per job
- Retry with backoff
- Registration API for future plugins
- Minimal in-memory, thread-based runner (no external deps)
"""

import heapq
import multiprocessing
import threading
import time
import sys
import os
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
    params: Optional[Dict[str, Any]] = field(default=None, compare=False)

    def __post_init__(self):
        # sort_index ensures heapq stability even if next_run ties
        self.sort_index = id(self)


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
        self._is_running: Dict[str, bool] = {}  # Concurrency lock: job_name -> is_currently_running
        self._active_threads: Dict[str, threading.Thread] = {}  # Tracking thread handles for kill switch
        self._active_processes: Dict[str, Any] = {}  # Tracking multiprocessing.Process handles for kill switch

    def _release_worker_resources(self):
        """Clean up thread-local database sessions to prevent connection leaks."""
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

    def _finalize_job_after_run(self, job: ScheduledJob, finished_at: float) -> None:
        """Finalize job state after an execution attempt.

        One-time jobs (interval_seconds is None) are transient and must be removed from
        registry/heap once finished so they do not keep showing up in API/UI job lists.
        """
        job.last_finished = finished_at
        job.running = False
        job.params = None
        self._is_running[job.name] = False
        self._active_threads.pop(job.name, None)

        if job.interval_seconds is not None:
            if job.enabled:
                job.next_run = finished_at + job.interval_seconds
                heapq.heappush(self._heap, job)
            return

        # Purge transient one-time jobs from the heap so they do not run again,
        # but keep them in self._jobs if you want them to persist in the UI.
        # However, for memory hygiene and test compliance, we pop them if non-recurring.
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
        _MAX_RETRIES_CAP = 10
        max_retries = max(0, min(max_retries, _MAX_RETRIES_CAP))

        try:
            from core.hook_manager import hook_manager
            hook_kwargs = hook_manager.apply_filters('ON_JOB_ENQUEUED', {
                'name': name,
                'interval_seconds': interval_seconds,
                'start_after': start_after,
                'enabled': enabled,
                'max_retries': max_retries,
                'backoff_base': backoff_base,
                'backoff_factor': backoff_factor,
                'tags': tags,
                'plugin': plugin
            })
            if isinstance(hook_kwargs, dict):
                name = hook_kwargs.get('name', name)
                interval_seconds = hook_kwargs.get('interval_seconds', interval_seconds)
                start_after = hook_kwargs.get('start_after', start_after)
                enabled = hook_kwargs.get('enabled', enabled)
                max_retries = max(0, min(hook_kwargs.get('max_retries', max_retries), _MAX_RETRIES_CAP))
                backoff_base = hook_kwargs.get('backoff_base', backoff_base)
                backoff_factor = hook_kwargs.get('backoff_factor', backoff_factor)
                tags = hook_kwargs.get('tags', tags)
                plugin = hook_kwargs.get('plugin', plugin)
        except Exception as e:
            import logging
            logging.getLogger("job_queue").error(f"Error in ON_JOB_ENQUEUED hook: {e}")

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

    def execute_job_now(self, name: str, params: Optional[Dict[str, Any]] = None) -> bool:
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
            
            if params is not None:
                job.params = params

        is_heavy = getattr(job, 'plugin', None) is not None or "sync" in job.name or "scan" in job.name
        self._is_running[name] = True
        
        if is_heavy:
            p = multiprocessing.Process(
                target=_multiprocess_worker_target,
                args=(job.name, job.plugin, None, params),
                daemon=True
            )
            with self._lock:
                self._active_processes[name] = p
                self._is_running[name] = p
            p.start()
            
            def monitor():
                p.join()
                with self._lock:
                    self._finalize_job_after_run(job, time.time())
                    self._active_processes.pop(name, None)
                self._release_worker_resources()
            
            threading.Thread(target=monitor, daemon=True).start()
        else:
            def thread_worker():
                try:
                    _execute_job_logic(job, params=params)
                finally:
                    with self._lock:
                        self._finalize_job_after_run(job, time.time())
                    self._release_worker_resources()

            t = threading.Thread(target=thread_worker, daemon=True)
            with self._lock:
                self._active_threads[name] = t
            t.start()
        
        logger.info(f"Spawned {'multiprocess' if is_heavy else 'thread'} worker for manual execution of job '{name}'")
        return True

    def kill_job(self, name: str) -> bool:
        """Forcefully terminate a running job thread or multiprocess worker."""
        import ctypes
        with self._lock:
            # Check for OS-level escape hatch first
            process = self._active_processes.get(name)
            if process and process.is_alive():
                logger.warning(f"Forcefully terminating multiprocess worker for job '{name}'")
                process.terminate()
                process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()
                return True

            thread = self._active_threads.get(name)
            if not thread or not thread.is_alive():
                logger.warning(f"Job '{name}' is not currently running a tracked thread.")
                return False
                
            thread_id = thread.ident
            if not thread_id:
                return False
                
        try:
            # Raise SystemExit asynchronously in the target thread
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), ctypes.py_object(SystemExit))
            if res == 0:
                logger.error(f"Failed to kill job '{name}': invalid thread ID")
                return False
            elif res != 1:
                # Revert if it failed
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), None)
                logger.error(f"Failed to kill job '{name}': internal ctypes error")
                return False
                
            logger.info(f"Successfully sent kill signal to job '{name}'")
            return True
        except Exception as e:
            logger.error(f"Exception while trying to kill job '{name}': {e}")
            return False

    def kill_jobs_by_plugin(self, plugin_id: str):
        """Terminates all active jobs associated with a specific plugin."""
        with self._lock:
            jobs_to_kill = [name for name, job in self._jobs.items() if job.plugin == plugin_id]
        
        for name in jobs_to_kill:
            self.kill_job(name)
            self.unregister_job(name)
        
        logger.info(f"Terminated all jobs for plugin: {plugin_id}")

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
                    "params": job.params if hasattr(job, "params") else None,
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
                        "params": job.params if hasattr(job, "params") else None,
                    })
            return result

    # Internal runner
    def _is_job_running(self, name: str) -> bool:
        """Check if a job is currently executing."""
        with self._lock:
            val = self._is_running.get(name, False)
            return bool(val) or self._jobs.get(name, ScheduledJob(time.time(), "_dummy", lambda: None)).running

    def _run_loop(self):
        from core.state import system_state
        
        while self._running:
            # Task 2: Freeze execution if a restart is pending to avoid code mismatch
            if system_state.restart_pending or JobQueue.RESTART_PENDING:
                logger.warning("JobQueue: RESTART_PENDING is True. Freezing background job execution until reboot.")
                time.sleep(5)
                continue

            with self._lock:
                now = time.time()

                # Pre-fetch watchdog to recover Zombie Jobs
                for job_name, is_running in list(self._is_running.items()):
                    if is_running:
                        job_obj = self._jobs.get(job_name)
                        if job_obj and job_obj.running and job_obj.last_started:
                            if now - job_obj.last_started > 7200: # 2 hours
                                logger.warning(f"Watchdog: Job '{job_name}' has been running for >2 hours. Resetting state.")
                                job_obj.running = False
                                self._is_running[job_name] = False

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
        
        is_heavy = getattr(job, 'plugin', None) is not None or "sync" in job.name or "scan" in job.name
        worker_pool = self._general_workers if is_heavy else self._core_workers

        if not worker_pool.acquire(blocking=False):
            logger.warning(f"No available workers in {'general' if is_heavy else 'core'} pool for job: {job.name}")
            return

        self._is_running[job.name] = True

        if is_heavy:
            # Use multiprocessing for heavy jobs to bypass GIL and allow termination
            p = multiprocessing.Process(
                target=_multiprocess_worker_target,
                args=(job.name, job.plugin, None),
                daemon=True
            )
            with self._lock:
                self._active_processes[job.name] = p
                self._is_running[job.name] = p
            
            p.start()
            
            # Start a monitor thread in the parent process to wait for the worker
            # and clean up state, since the child process cannot update parent memory.
            def monitor():
                p.join()
                with self._lock:
                    self._finalize_job_after_run(job, time.time())
                    self._active_processes.pop(job.name, None)
                worker_pool.release()
                self._release_worker_resources()
            
            threading.Thread(target=monitor, daemon=True).start()
        else:
            def thread_worker():
                try:
                    # Run the job function directly in the thread
                    # Note: We reuse the same logic as the old worker here
                    _execute_job_logic(job)
                finally:
                    with self._lock:
                        self._finalize_job_after_run(job, time.time())
                    worker_pool.release()
                    self._release_worker_resources()

            t = threading.Thread(target=thread_worker, daemon=True)
            with self._lock:
                self._active_threads[job.name] = t
            t.start()


def _multiprocess_worker_target(job_name: str, plugin_id: Optional[str], owner_plugin_id: Optional[str], params: Optional[Dict[str, Any]] = None):
    """Top-level function for multiprocessing worker target (fix for pickling errors)."""
    try:
        from core.job_queue import job_queue
        with job_queue._lock:
            job = job_queue._jobs.get(job_name)
        
        if not job:
            return

        # Apply memory limits (Memory Jail)
        if sys.platform != 'win32':
            try:
                import resource
                effective_plugin_id = owner_plugin_id or plugin_id
                if effective_plugin_id and effective_plugin_id != "core":
                    # Check manifest for custom limit
                    from core.settings import config_manager
                    import json
                    limit_mb = 100
                    manifest_path = config_manager.get_plugins_dir() / effective_plugin_id.replace('plugin.', '') / "manifest.json"
                    if manifest_path.exists():
                        manifest = json.loads(manifest_path.read_text())
                        limit_mb = manifest.get('permissions', {}).get('memory_limit_mb', 100)
                    
                    limit_bytes = limit_mb * 1024 * 1024
                    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
            except Exception:
                pass

        _execute_job_logic(job, params=params)
    except Exception as e:
        import logging
        logging.getLogger("job_worker").error(f"Fatal error in multiprocess worker for {job_name}: {e}")

def _execute_job_logic(job: ScheduledJob, params: Optional[Dict[str, Any]] = None):
    """Core logic for executing a job, shared between threads and processes."""
    from core.tiered_logger import get_logger
    logger = get_logger("job_queue")
    
    attempt = 0
    while True:
        attempt += 1
        try:
            # Log health checks at DEBUG, other jobs at INFO
            log_level = logger.debug if 'health_check' in job.name else logger.info
            log_level(f"Starting job: {job.name} (attempt {attempt})")
            
            job.running = True
            job.last_started = time.time()
            if params is not None:
                job.params = params
            
            try:
                # Execute the actual function
                import inspect
                sig = inspect.signature(job.func)
                if len(sig.parameters) > 0:
                    job.func(params=params)
                else:
                    job.func()
            except Exception as e:
                # 1. Log the failure happens automatically in the outer except block, but we must force rollback
                logger.error(f"Job failed: {e}")
                raise
            finally:
                # Absolute cleanup guarantee
                # Explicitly remove the session from the registry to ensure no state
                # leaks into the next job that picks up this thread.
                try:
                    from database.music_database import music_session_registry
                    music_session_registry.remove()
                except Exception as e:
                    logger.error(f"Failed to remove music session registry: {e}")

                try:
                    from database.working_database import working_session_registry
                    working_session_registry.remove()
                except Exception as e:
                    logger.error(f"Failed to remove working session registry: {e}")
            
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
            logger.error(f"Job failed: {job.name}, attempt {attempt}, error: {e}", exc_info=True)

            if job.current_retries >= job.max_retries:
                logger.error(f"Job '{job.name}' exceeded max retries ({job.max_retries}); giving up.")
                try:
                    from core.hook_manager import hook_manager
                    hook_manager.apply_filters('ON_JOB_FAILED', None, job_name=job.name, error=error_msg, retries=job.current_retries)
                except Exception:
                    pass
                break

            backoff = job.backoff_base * (job.backoff_factor ** (job.current_retries - 1))
            logger.info(f"Retrying job '{job.name}' in {backoff:.1f}s")
            time.sleep(backoff)


# Global singleton
job_queue = JobQueue()


def register_scheduled_task(name: str, func: Callable[[], Any], frequency: float):
    """SDK Helper to expose internal scheduler to plugins easily."""
    job_queue.register_job(name=name, func=func, interval_seconds=frequency)

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
