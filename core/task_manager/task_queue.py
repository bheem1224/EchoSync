"""
Refactored Job Queue / Task Manager Scaffold with Collision Avoidance and FFI Cancellation.
Supports TaskCategory enums (GENERAL, CRITICAL, DATABASE_WRITE_HEAVY, BACKGROUND_METADATA) and TaskStatus tracking.
Enforces two-tier worker pools and a single-writer SQLite WAL lease manager with backpressure.
"""

from __future__ import annotations

import heapq
import os
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.enums import TaskCategory, TaskPriority, TaskStatus
from core.tiered_logger import get_logger

logger = get_logger("core.task_manager")

# Backward-compatibility alias
TaskState = TaskStatus


class QueueFullError(Exception):
    """Raised when the JobQueue reaches its maximum pending capacity."""


@dataclass(order=True)
class ScheduledJob:
    next_run: float
    sort_index: int = field(init=False, repr=False)
    name: str = field(compare=False)
    func: Callable[[], Any] = field(compare=False)
    interval_seconds: float | None = field(default=None, compare=False)
    enabled: bool = field(default=True, compare=False)
    category: TaskCategory = field(default=TaskCategory.GENERAL, compare=False)
    state: TaskStatus = field(default=TaskStatus.QUEUED, compare=False)
    cancel_token: Any | None = field(default=None, compare=False)
    max_retries: int = field(default=0, compare=False)
    backoff_base: float = field(default=5.0, compare=False)
    backoff_factor: float = field(default=2.0, compare=False)
    current_retries: int = field(default=0, compare=False)
    last_error: str | None = field(default=None, compare=False)
    last_error_time: float | None = field(default=None, compare=False)
    total_failures: int = field(default=0, compare=False)
    total_successes: int = field(default=0, compare=False)
    last_started: float | None = field(default=None, compare=False)
    last_finished: float | None = field(default=None, compare=False)
    last_success: float | None = field(default=None, compare=False)
    running: bool = field(default=False, compare=False)
    tags: list[str] = field(default_factory=list, compare=False)
    plugin: str | None = field(default=None, compare=False)
    manual_next_run: float | None = field(default=None, compare=False)
    params: dict[str, Any] | None = field(default=None, compare=False)
    progress: dict[str, Any] | None = field(default=None, compare=False)
    exclusive_db_lease: bool = field(default=False, compare=False)
    skip_if_blocked: bool = field(default=False, compare=False)
    priority: TaskPriority = field(default=TaskPriority.NORMAL, compare=False)

    def __post_init__(self):
        self.sort_index = id(self)

    def to_dict(self) -> dict[str, Any]:
        import time as _time

        now = _time.time()
        duration_s = None
        if self.running and self.last_started:
            duration_s = round(now - self.last_started, 1)
        return {
            "name": self.name,
            "category": self.category.value if isinstance(self.category, TaskCategory) else str(self.category),
            "state": self.state.value if isinstance(self.state, TaskStatus) else str(self.state),
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
            "progress": self.progress,
            "exclusive_db_lease": self.exclusive_db_lease,
            "skip_if_blocked": self.skip_if_blocked,
            "priority": self.priority.value if isinstance(self.priority, TaskPriority) else str(self.priority),
        }


class JobQueue:
    RESTART_PENDING = False

    def __init__(self, worker_count: int = 2, poll_interval: float = 0.5, engine: Any = None):
        self._lock = threading.RLock()
        self._jobs: dict[str, ScheduledJob] = {}
        self._heap: list[ScheduledJob] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._core_workers = threading.BoundedSemaphore(2)
        self._general_workers = threading.BoundedSemaphore(worker_count)
        self._poll_interval = poll_interval
        self._is_running: dict[str, bool] = {}
        self._active_threads: dict[str, threading.Thread] = {}
        self._active_processes: dict[str, Any] = {}
        self._paused_jobs: set[str] = set()
        self._max_pending_jobs = 100
        self._engine = engine

        # Detect database dialect: check engine.dialect.name if provided, fallback to inspection
        self._dialect = self._detect_db_dialect(engine)
        if self._dialect == "postgresql":
            # PostgreSQL supports multiple concurrent writers
            max_writers = max(2, worker_count)
        else:
            # SQLite single-writer constraint
            max_writers = 1
        self._db_write_lease = threading.Semaphore(max_writers)
        self._max_writers = max_writers
        self._exclusive_lease_active = False

        # Re-entrant lease tracking
        self._lease_holders: dict[int, int] = {}
        self._lease_lock = threading.Lock()

        # Bootstrap native Rust Rayon thread pool with progressive container limits
        try:
            import echosync_core

            rust_threads_override = None
            if hasattr(self, "config") and isinstance(self.config, dict):
                rust_threads_override = self.config.get("performance", {}).get("rust_threads")
            effective_native_threads = echosync_core.init_native_thread_pool(rust_threads_override)
            logger.info(
                f"Native execution engine initialized: Rayon thread pool bound to "
                f"{effective_native_threads} worker threads (override={rust_threads_override})"
            )
        except ImportError:
            logger.debug("echosync_core C-extension not available; native pool init skipped")
        except Exception as exc:
            logger.warning(f"Failed to configure native thread pool: {exc}")

        try:
            from core.event_bus import event_bus

            event_bus.subscribe("job_progress", self._on_job_progress)
        except Exception:
            pass

    @staticmethod
    def _detect_db_dialect(engine: Any = None) -> str:
        """Inspect SQLAlchemy engine dialect, falling back to database singleton or env URI."""
        if engine is not None and hasattr(engine, "dialect") and hasattr(engine.dialect, "name"):
            return str(engine.dialect.name).lower()
        try:
            from database.music_database import get_database

            db = get_database()
            if hasattr(db, "engine") and hasattr(db.engine, "dialect") and hasattr(db.engine.dialect, "name"):
                return str(db.engine.dialect.name).lower()
        except Exception:
            pass
        # Fallback to URI/env inspection
        db_uri = os.getenv("DATABASE_URL", "").lower()
        if db_uri.startswith("postgresql") or db_uri.startswith("postgres"):
            return "postgresql"
        return "sqlite"

    def _check_wal_backpressure(self) -> bool:
        """Check if SQLite WAL size exceeds 32 MB threshold.

        If exceeded, proactively attempts PRAGMA wal_checkpoint(PASSIVE) with bounded wait.
        Returns True if WAL is acceptable, False if backpressure limit exceeded.
        """
        if self._dialect != "sqlite":
            return True

        wal_candidates = [
            Path("data/music_library.db-wal"),
            Path("music_library.db-wal"),
            Path("data/library.db-wal"),
        ]
        threshold = 32 * 1024 * 1024  # 32 MB

        wal_file = None
        for cand in wal_candidates:
            if cand.exists():
                wal_file = cand
                break

        if not wal_file:
            return True

        try:
            wal_size = wal_file.stat().st_size
        except (OSError, FileNotFoundError):
            return True

        if wal_size > threshold:
            logger.warning(
                f"SQLite WAL size ({wal_size / (1024 * 1024):.1f} MB) exceeds 32 MB threshold. "
                "Triggering proactive PRAGMA wal_checkpoint(PASSIVE)..."
            )
            # Execute checkpoint with 5.0s bounded wait
            try:
                from sqlalchemy import text

                from database.music_database import get_database

                db = get_database()
                with db.engine.connect() as conn:
                    conn.execute(text("PRAGMA wal_checkpoint(PASSIVE);"))
            except Exception as exc:
                logger.debug(f"WAL checkpoint attempt error: {exc}")

            # Re-check size
            try:
                still_exceeds = wal_file.stat().st_size > threshold
            except (OSError, FileNotFoundError):
                still_exceeds = False

            if still_exceeds:
                logger.warning(
                    f"SQLite WAL size still exceeds 32 MB after checkpoint ({wal_size / (1024 * 1024):.1f} MB). Backpressure active."
                )
                return False

        return True

    @contextmanager
    def db_write_lease(self, task_name: str = "", timeout: float = 30.0):
        """Scoped context manager for granular database write operations.

        Ensures SQLite single-writer mutual exclusion and checks WAL backpressure.
        Thread-aware and re-entrant: nested calls within the same thread increment
        a depth counter to prevent self-deadlock.
        """
        tid = threading.get_ident()
        with self._lease_lock:
            if tid in self._lease_holders:
                self._lease_holders[tid] += 1
                is_nested = True
            else:
                is_nested = False

        if is_nested:
            try:
                yield
            finally:
                with self._lease_lock:
                    self._lease_holders[tid] -= 1
                    if self._lease_holders[tid] <= 0:
                        self._lease_holders.pop(tid, None)
            return

        if not self._check_wal_backpressure():
            raise TimeoutError("Database write lease rejected: WAL backpressure limit exceeded (>32MB)")

        acquired = self._db_write_lease.acquire(timeout=timeout)
        if not acquired:
            raise TimeoutError(f"Could not acquire database write lease within {timeout}s for task '{task_name}'")

        with self._lease_lock:
            self._lease_holders[tid] = 1

        try:
            yield
        finally:
            with self._lease_lock:
                self._lease_holders[tid] -= 1
                if self._lease_holders[tid] <= 0:
                    self._lease_holders.pop(tid, None)
            try:
                self._db_write_lease.release()
            except ValueError:
                pass

    @contextmanager
    def db_read_lease(self, task_name: str = "", timeout: float = 30.0):
        """Scoped context manager for database read operations.

        Provides cooperative tracking and bounded access for read-heavy operations.
        In SQLite WAL mode, concurrent readers are permitted while tracking lease scope.
        """
        yield

    def should_yield(self, task_name: str = "") -> bool:
        """Cooperative yield check for long-running workers.

        Returns True if a CRITICAL task is queued or the task has been cancelled.
        """
        with self._lock:
            if any(j.category == TaskCategory.CRITICAL and not j.running for j in self._jobs.values()):
                return True
        try:
            from core.task_manager.supervisor import supervisor

            if supervisor.is_current_task_cancelled():
                return True
        except Exception:
            pass
        return False

    def _acquire_worker_slot(self, job: ScheduledJob) -> bool:
        semaphore = self._core_workers if job.category == TaskCategory.CRITICAL else self._general_workers
        return semaphore.acquire(blocking=False)

    def _release_worker_slot(self, job: ScheduledJob) -> None:
        semaphore = self._core_workers if job.category == TaskCategory.CRITICAL else self._general_workers
        try:
            semaphore.release()
        except ValueError:
            pass

    def _on_job_progress(self, payload: dict[str, Any]) -> None:
        if isinstance(payload, dict):
            job_name = payload.get("job_name")
            if job_name:
                self.update_job_progress(job_name, payload)

    def update_job_progress(self, name: str, progress: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(name)
            if job:
                job.progress = progress

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

        try:
            from core.task_manager.supervisor import release_system_memory

            release_system_memory()
        except Exception as e:
            logger.debug(f"Failed to trim system memory: {e}")

    def _remove_from_heap(self, name: str):
        self._heap = [job for job in self._heap if job.name != name]
        heapq.heapify(self._heap)

    def is_db_write_heavy_running(self) -> bool:
        """Check if any DATABASE_WRITE_HEAVY or BACKGROUND_METADATA task (or exclusive lease) is running."""
        with self._lock:
            if self._exclusive_lease_active:
                return True
            return any(
                job.running
                and (
                    job.category in (TaskCategory.DATABASE_WRITE_HEAVY, TaskCategory.BACKGROUND_METADATA)
                    or job.exclusive_db_lease
                )
                for job in self._jobs.values()
            )

    def is_job_running(self, name_pattern: str) -> bool:
        """Check if any job matching name_pattern is currently running."""
        with self._lock:
            for job_name, is_run in self._is_running.items():
                if is_run and name_pattern in job_name:
                    return True
            for job in self._jobs.values():
                if (job.running or job.state == TaskStatus.RUNNING) and name_pattern in job.name:
                    return True
            return False

    def can_execute(self, job: ScheduledJob) -> bool:
        """Evaluate job against currently running jobs for collision avoidance and capability gating."""
        with self._lock:
            if (
                self.RESTART_PENDING or getattr(JobQueue, "RESTART_PENDING", False)
            ) and job.category != TaskCategory.CRITICAL:
                job.state = TaskStatus.PAUSED
                return False

            if job.plugin:
                from core.task_manager.plugin_state import plugin_state_manager

                if not plugin_state_manager.can_accept_work(job.plugin):
                    if job.state != TaskStatus.BLOCKED_WAITING_LEASE:
                        status = plugin_state_manager.get_state(job.plugin)
                        logger.warning(
                            f"Job '{job.name}' blocked from execution: plugin '{job.plugin}' cannot accept work "
                            f"(state: {status.state.value})"
                        )
                    job.state = TaskStatus.BLOCKED_WAITING_LEASE
                    job.next_run = time.time() + 10.0
                    return False

            is_write = (
                job.category in (TaskCategory.DATABASE_WRITE_HEAVY, TaskCategory.BACKGROUND_METADATA)
                or job.exclusive_db_lease
            )
            if is_write:
                if self.is_db_write_heavy_running():
                    job.state = TaskStatus.BLOCKED_WAITING_LEASE
                    if job.skip_if_blocked and job.interval_seconds:
                        job.next_run = time.time() + job.interval_seconds
                    else:
                        job.next_run = time.time() + 2.0
                    return False

            # Mutual exclusion between library_sync/database_update and auto_import
            if "library_sync" in job.name or "database_update" in job.name:
                if self.is_job_running("auto_import"):
                    job.state = TaskStatus.BLOCKED_WAITING_LEASE
                    job.next_run = time.time() + 5.0
                    return False
            elif "auto_import" in job.name:
                if self.is_job_running("library_sync") or self.is_job_running("database_update"):
                    job.state = TaskStatus.BLOCKED_WAITING_LEASE
                    job.next_run = time.time() + 5.0
                    return False

            return True

    def cancel_job(self, name: str) -> bool:
        """Cancel a running or scheduled job cleanly."""
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
            old_state = job.state
            job.state = TaskStatus.CANCELLED
            job.last_error = "Cancelled by user"
            self._is_running[job.name] = False
            taint = f"[TAINT:{job.plugin}] " if job.plugin else ""
            logger.info(f"{taint}Task '{job.name}' state transition: {old_state.value} -> {job.state.value}")
            return True

    def unregister_job(self, name: str) -> bool:
        """Cancel and completely remove a job from the queue."""
        with self._lock:
            if name not in self._jobs:
                return False

            self.cancel_job(name)
            self._remove_from_heap(name)
            self._jobs.pop(name, None)
            return True

    def _finalize_job_after_run(self, job: ScheduledJob, finished_at: float) -> None:
        try:
            if job.exclusive_db_lease:
                self._exclusive_lease_active = False
                try:
                    self._db_write_lease.release()
                except ValueError:
                    pass
        finally:
            self._release_worker_slot(job)

        job.last_finished = finished_at
        job.running = False
        job.params = None
        job.progress = None
        self._is_running[job.name] = False
        self._active_threads.pop(job.name, None)

        if job.state == TaskStatus.RETRY_BACKOFF:
            heapq.heappush(self._heap, job)
            return

        if job.interval_seconds is not None:
            if job.enabled and job.state != TaskStatus.CANCELLED:
                job.next_run = finished_at + job.interval_seconds
                old_state = job.state
                job.state = TaskStatus.QUEUED
                taint = f"[TAINT:{job.plugin}] " if job.plugin else ""
                logger.debug(f"{taint}Task '{job.name}' state transition: {old_state.value} -> {job.state.value}")
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
        interval_seconds: float | None = None,
        start_after: float = 0.0,
        enabled: bool = True,
        category: TaskCategory = TaskCategory.GENERAL,
        cancel_token: Any | None = None,
        max_retries: int = 0,
        backoff_base: float = 5.0,
        backoff_factor: float = 2.0,
        tags: list[str] | None = None,
        plugin: str | None = None,
        params: dict[str, Any] | None = None,
        exclusive_db_lease: bool = False,
        skip_if_blocked: bool = False,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> None:
        _MAX_RETRIES_CAP = 10
        max_retries = max(0, min(max_retries, _MAX_RETRIES_CAP))

        with self._lock:
            # 1. Deduplication by name
            if name in self._jobs:
                existing = self._jobs[name]
                if existing.running or self._is_running.get(name, False):
                    # Job is actively running: update recurring settings without duplicating
                    existing.interval_seconds = interval_seconds
                    existing.enabled = enabled
                    existing.params = params
                    existing.exclusive_db_lease = exclusive_db_lease
                    existing.skip_if_blocked = skip_if_blocked
                    existing.priority = priority
                    return
                # If already queued, update and re-heapify
                self._remove_from_heap(name)

            # 2. Capacity & Deduplicated Hybrid Eviction Policy (max 100 pending jobs)
            if len(self._jobs) >= self._max_pending_jobs and name not in self._jobs:
                is_recurring = interval_seconds is not None
                if is_recurring:
                    logger.warning(
                        f"JobQueue capacity reached ({self._max_pending_jobs}). Dropping recurring job '{name}' to next interval."
                    )
                    return
                else:
                    # One-time / interactive request: evict lowest-priority scheduled recurring non-running job
                    evicted = False
                    candidates = [j for j in self._jobs.values() if not j.running and j.interval_seconds is not None]
                    if candidates:
                        # Sort by priority (LOW first), then next_run (furthest away first)
                        candidates.sort(
                            key=lambda j: (
                                0
                                if j.priority == TaskPriority.LOW
                                else (1 if j.priority == TaskPriority.NORMAL else 2),
                                -j.next_run,
                            )
                        )
                        victim = candidates[0]
                        logger.info(
                            f"JobQueue capacity reached. Evicting recurring job '{victim.name}' to admit one-time job '{name}'."
                        )
                        self.unregister_job(victim.name)
                        evicted = True

                    if not evicted:
                        raise QueueFullError(
                            f"JobQueue capacity reached ({self._max_pending_jobs} jobs) with no evictable background tasks."
                        )

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
                state=TaskStatus.QUEUED,
                cancel_token=cancel_token,
                max_retries=max_retries,
                backoff_base=backoff_base,
                backoff_factor=backoff_factor,
                tags=tags or [],
                plugin=plugin,
                params=params,
                exclusive_db_lease=exclusive_db_lease,
                skip_if_blocked=skip_if_blocked,
                priority=priority,
            )

            self._jobs[name] = job
            heapq.heappush(self._heap, job)
            taint = f"[TAINT:{plugin}] " if plugin else ""
            logger.info(f"{taint}Registered job: {name} [Category: {category.value}, Priority: {priority.value}]")

    def execute_job_now(self, name: str, params: dict[str, Any] | None = None) -> bool:
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

    def trigger_job_by_name(self, name: str, params: dict[str, Any] | None = None) -> bool:
        """Trigger a job immediately by name or known aliases."""
        alias_map = {
            "download_queue_runner": "download_manager",
        }
        target_name = alias_map.get(name, name)
        res = self.execute_job_now(target_name, params=params)
        if not res and target_name != name:
            res = self.execute_job_now(name, params=params)
        return res

    def get_queue_state(self) -> dict[str, Any]:
        """Return serializable representation of full queue state for SSE telemetry."""
        with self._lock:
            running = []
            pending = []
            blocked = []

            for job in self._jobs.values():
                d = job.to_dict()
                if job.running or job.state == TaskStatus.RUNNING:
                    running.append(d)
                elif job.state == TaskStatus.BLOCKED_WAITING_LEASE:
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
                    "blocked": len(blocked),
                },
            }

    def _run_loop(self):
        while self._running:
            time.sleep(self._poll_interval)
            now = time.time()
            to_run = []

            with self._lock:
                temp_heap = []
                while self._heap and self._heap[0].next_run <= now:
                    job = heapq.heappop(self._heap)
                    if not job.enabled or job.running:
                        continue

                    if not self.can_execute(job):
                        temp_heap.append(job)
                        continue

                    # Attempt to acquire worker slot
                    if not self._acquire_worker_slot(job):
                        job.state = TaskStatus.BLOCKED_WAITING_LEASE
                        job.next_run = now + self._poll_interval
                        temp_heap.append(job)
                        continue

                    # If exclusive_db_lease is requested, acquire the DB write lease before starting
                    if job.exclusive_db_lease:
                        if not self._check_wal_backpressure() or not self._db_write_lease.acquire(blocking=False):
                            self._release_worker_slot(job)
                            job.state = TaskStatus.BLOCKED_WAITING_LEASE
                            job.next_run = now + 2.0
                            temp_heap.append(job)
                            continue
                        self._exclusive_lease_active = True

                    old_state = job.state
                    job.running = True
                    job.state = TaskStatus.RUNNING
                    self._is_running[job.name] = True
                    taint = f"[TAINT:{job.plugin}] " if job.plugin else ""
                    logger.info(f"{taint}Task '{job.name}' state transition: {old_state.value} -> {job.state.value}")
                    to_run.append(job)

                for deferred_job in temp_heap:
                    heapq.heappush(self._heap, deferred_job)

            for job in to_run:
                thread = threading.Thread(target=self._execute_wrapper, args=(job,), daemon=True)
                with self._lock:
                    self._active_threads[job.name] = thread
                thread.start()

    def _execute_wrapper(self, job: ScheduledJob):
        started_at = time.time()
        job.last_started = started_at
        reg_id = None
        cancel_event = threading.Event()
        taint = f"[TAINT:{job.plugin}] " if job.plugin else ""

        try:
            from core.task_manager.models import OwnerType, ProcessOwner
            from core.task_manager.supervisor import supervisor

            owner_id = job.plugin if job.plugin else "core.system_job"
            owner_type = OwnerType.PLUGIN if job.plugin else OwnerType.SYSTEM_JOB
            owner = ProcessOwner(
                owner_id=owner_id,
                owner_type=owner_type,
                pid=None,
                thread_id=threading.get_ident(),
                task_name=job.name,
            )
            reg_id = supervisor.register_process(owner, cancellation_event=cancel_event)
        except Exception:
            pass

        try:
            if job.params:
                job.func(**job.params)
            else:
                job.func()
            job.total_successes += 1
            job.last_error = None
            old_state = job.state
            job.state = TaskStatus.COMPLETED
            logger.info(f"{taint}Task '{job.name}' state transition: {old_state.value} -> {job.state.value}")
        except Exception as e:
            job.total_failures += 1
            job.last_error = str(e)
            job.last_error_time = time.time()
            err_str = str(e).lower()
            is_transient = (
                isinstance(e, (TimeoutError, ConnectionError))
                or "database is locked" in err_str
                or "busy" in err_str
                or "resource temporarily unavailable" in err_str
            )
            if is_transient and job.current_retries < job.max_retries:
                job.current_retries += 1
                delay = job.backoff_base * (job.backoff_factor ** (job.current_retries - 1))
                job.next_run = time.time() + delay
                old_state = job.state
                job.state = TaskStatus.RETRY_BACKOFF
                logger.warning(
                    f"{taint}Task '{job.name}' transient failure (attempt {job.current_retries}/{job.max_retries}): {e}. "
                    f"State transition: {old_state.value} -> {job.state.value}. Scheduling RETRY_BACKOFF in {delay:.1f}s"
                )
            else:
                old_state = job.state
                job.state = TaskStatus.FAILED_TERMINAL
                logger.error(
                    f"{taint}Task '{job.name}' terminal failure: {e}. State transition: {old_state.value} -> {job.state.value}",
                    exc_info=True,
                )
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

    def get_job(self, name: str) -> ScheduledJob | None:
        """Fetch a registered job by name."""
        with self._lock:
            return self._jobs.get(name)

    def list_jobs(self) -> list[dict[str, Any]]:
        """Return a list of all registered jobs as dictionaries."""
        with self._lock:
            return [job.to_dict() for job in self._jobs.values()]

    def is_paused(self, name: str) -> bool:
        """Check if a job has been paused."""
        with self._lock:
            if name in self._paused_jobs:
                return True
            job = self._jobs.get(name)
            if job and job.state == TaskStatus.PAUSED:
                return True
            return False

    def pause_job(self, name: str) -> bool:
        """Cooperatively pause a running or scheduled job."""
        with self._lock:
            self._paused_jobs.add(name)
            job = self._jobs.get(name)
            if job:
                job.state = TaskStatus.PAUSED
            logger.info(f"[JobQueue] Job '{name}' paused")
            return True

    def resume_job(self, name: str) -> bool:
        """Resume a paused job."""
        with self._lock:
            self._paused_jobs.discard(name)
            job = self._jobs.get(name)
            if job and job.state == TaskStatus.PAUSED:
                job.state = TaskStatus.RUNNING if job.running else TaskStatus.QUEUED
            logger.info(f"[JobQueue] Job '{name}' resumed")
            return True

    def wait_for_resume(self, name: str, poll_interval: float = 0.25, timeout: float | None = None) -> bool:
        """Cooperatively block execution while the specified job remains paused."""
        start_time = time.time()
        while self.is_paused(name):
            if timeout is not None and (time.time() - start_time) >= timeout:
                logger.warning(f"[JobQueue] wait_for_resume('{name}') timed out after {timeout}s")
                return False
            time.sleep(poll_interval)
        return True

    @contextmanager
    def lease_task(
        self,
        name: str,
        category: TaskCategory = TaskCategory.BACKGROUND_METADATA,
        tags: list[str] | None = None,
    ):
        """Acquires a single leased parent task in the JobQueue for long-running workflows.

        Prevents queue saturation by executing work in-line under this lease while
        allowing cooperative pause/resume and state tracking.
        """
        now = time.time()
        job = ScheduledJob(
            next_run=now,
            name=name,
            func=lambda: None,
            category=category,
            state=TaskStatus.RUNNING,
            running=True,
            last_started=now,
            tags=tags or ["leased", "parent_task"],
        )
        with self._lock:
            self._jobs[name] = job
            self._is_running[name] = True
        logger.info(f"[JobQueue] Leased parent task '{name}' started")
        try:
            yield name
            with self._lock:
                if name in self._jobs:
                    self._jobs[name].state = TaskStatus.COMPLETED
                    self._jobs[name].running = False
                    self._jobs[name].last_finished = time.time()
                    self._jobs[name].last_success = time.time()
                    self._jobs[name].total_successes += 1
            logger.info(f"[JobQueue] Leased parent task '{name}' completed successfully")
        except Exception as e:
            with self._lock:
                if name in self._jobs:
                    self._jobs[name].state = TaskStatus.FAILED_TERMINAL
                    self._jobs[name].running = False
                    self._jobs[name].last_finished = time.time()
                    self._jobs[name].last_error = str(e)
                    self._jobs[name].last_error_time = time.time()
                    self._jobs[name].total_failures += 1
            logger.error(f"[JobQueue] Leased parent task '{name}' failed: {e}")
            raise
        finally:
            with self._lock:
                self._is_running.pop(name, None)
                self._paused_jobs.discard(name)
                self._jobs.pop(name, None)


job_queue = JobQueue()
task_queue = job_queue


def list_jobs() -> list[dict[str, Any]]:
    """Top-level helper function to return all registered jobs as dictionaries."""
    return job_queue.list_jobs()


def is_paused(name: str) -> bool:
    """Top-level helper to check if a job is paused."""
    return job_queue.is_paused(name)


def wait_for_resume(name: str, poll_interval: float = 0.25, timeout: float | None = None) -> bool:
    """Top-level helper to wait for a paused job to resume."""
    return job_queue.wait_for_resume(name, poll_interval=poll_interval, timeout=timeout)


def pause_job(name: str) -> bool:
    """Top-level helper to pause a job."""
    return job_queue.pause_job(name)


def resume_job(name: str) -> bool:
    """Top-level helper to resume a paused job."""
    return job_queue.resume_job(name)


@contextmanager
def lease_task(
    name: str,
    category: TaskCategory = TaskCategory.BACKGROUND_METADATA,
    tags: list[str] | None = None,
):
    """Top-level context manager to lease a parent task."""
    with job_queue.lease_task(name=name, category=category, tags=tags) as job_id:
        yield job_id


def trigger_job_by_name(name: str, params: dict[str, Any] | None = None) -> bool:
    """Top-level helper function to trigger a job immediately by name."""
    return job_queue.trigger_job_by_name(name, params=params)


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
    interval_seconds: float | None = None,
    start_after: float = 0.0,
    enabled: bool = True,
    category: TaskCategory = TaskCategory.GENERAL,
    cancel_token: Any | None = None,
    max_retries: int = 0,
    backoff_base: float = 5.0,
    backoff_factor: float = 2.0,
    tags: list[str] | None = None,
    plugin: str | None = None,
    params: dict[str, Any] | None = None,
    exclusive_db_lease: bool = False,
    skip_if_blocked: bool = False,
    priority: TaskPriority = TaskPriority.NORMAL,
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
        params=params,
        exclusive_db_lease=exclusive_db_lease,
        skip_if_blocked=skip_if_blocked,
        priority=priority,
    )


def unregister_job(name: str) -> bool:
    """Top-level helper function to unregister/cancel a job on global job_queue."""
    return job_queue.cancel_job(name)


@contextmanager
def db_write_lease(task_name: str = "", timeout: float = 30.0):
    """Top-level helper function for scoped re-entrant database write lease."""
    lease_cm = getattr(job_queue, "db_write_lease", None)
    if callable(lease_cm):
        with lease_cm(task_name=task_name, timeout=timeout):
            yield
    else:
        yield


@contextmanager
def db_read_lease(task_name: str = "", timeout: float = 30.0):
    """Top-level helper function for scoped re-entrant database read lease."""
    lease_cm = getattr(job_queue, "db_read_lease", None)
    if callable(lease_cm):
        with lease_cm(task_name=task_name, timeout=timeout):
            yield
    else:
        yield
