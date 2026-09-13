"""Regression test suite for EchoSync Task Manager and JobQueue modern architecture.

Verifies:
1. Two-tier worker pool throttling (Critical vs. General pools).
2. Scoped database write lease mutual exclusion and engine scaling.
3. Deduplicated hybrid eviction policy (100 cap, name deduplication, recurring eviction).
4. SQLite WAL backpressure check and proactive checkpointing.
5. Structured error classification (transient retry backoff vs. terminal failure).
6. System jobs alignment with TaskCategory.DATABASE_WRITE_HEAVY.
"""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.enums import TaskCategory, TaskPriority, TaskStatus
from core.task_manager.task_queue import (
    JobQueue,
    QueueFullError,
    ScheduledJob,
    TaskState,
)


def test_worker_pool_throttling_enforced():
    """Verify that JobQueue(worker_count=2) throttles general workers to at most 2 concurrent threads."""
    queue = JobQueue(worker_count=2, poll_interval=0.05)
    active_count = 0
    max_concurrent = 0
    count_lock = threading.Lock()

    def worker_func():
        nonlocal active_count, max_concurrent
        with count_lock:
            active_count += 1
            if active_count > max_concurrent:
                max_concurrent = active_count
        try:
            time.sleep(0.15)
        finally:
            with count_lock:
                active_count -= 1

    for i in range(5):
        queue.register_job(
            name=f"general_worker_{i}",
            func=worker_func,
            interval_seconds=None,
            start_after=0.0,
            category=TaskCategory.GENERAL,
        )

    queue.start()
    try:
        deadline = time.time() + 3.0
        while time.time() < deadline:
            with count_lock:
                # Once all 5 have completed, active_count returns to 0
                if len(queue._jobs) == 0 and active_count == 0:
                    break
            time.sleep(0.05)

        # Verified: Exactly 2 concurrent threads were allowed at any moment
        assert max_concurrent == 2, f"Expected general pool to throttle at 2, but observed {max_concurrent}"
    finally:
        queue.stop(timeout=2.0)


def test_critical_pool_reservation():
    """Verify that CRITICAL jobs run in dedicated core workers even when general pool is saturated."""
    queue = JobQueue(worker_count=1, poll_interval=0.05)
    general_running = threading.Event()
    general_hold = threading.Event()
    critical_executed = threading.Event()

    def general_task():
        general_running.set()
        general_hold.wait(timeout=2.0)

    def critical_task():
        critical_executed.set()

    # Saturated general worker
    queue.register_job(
        name="blocking_general",
        func=general_task,
        category=TaskCategory.GENERAL,
    )

    queue.start()
    try:
        assert general_running.wait(timeout=2.0)

        # Now submit CRITICAL job while general worker is 100% saturated
        queue.register_job(
            name="immediate_critical",
            func=critical_task,
            category=TaskCategory.CRITICAL,
        )

        # Critical task must execute immediately via _core_workers
        assert critical_executed.wait(timeout=2.0)
    finally:
        general_hold.set()
        queue.stop(timeout=2.0)


def test_scoped_db_write_lease_mutual_exclusion():
    """Verify that db_write_lease() enforces single-writer mutual exclusion under SQLite."""
    queue = JobQueue()
    assert queue._max_writers == 1

    concurrent_writers = 0
    max_concurrent_writers = 0
    lease_lock = threading.Lock()

    def write_task():
        nonlocal concurrent_writers, max_concurrent_writers
        with queue.db_write_lease(task_name="test_writer"):
            with lease_lock:
                concurrent_writers += 1
                if concurrent_writers > max_concurrent_writers:
                    max_concurrent_writers = concurrent_writers
            time.sleep(0.1)
            with lease_lock:
                concurrent_writers -= 1

    threads = [threading.Thread(target=write_task) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=3.0)

    assert max_concurrent_writers == 1


def test_db_dialect_scaling():
    """Verify dialect detection scales concurrency to database.max_workers when PostgreSQL is detected."""
    mock_pg_engine = MagicMock()
    mock_pg_engine.dialect.name = "postgresql"

    queue = JobQueue(worker_count=4, engine=mock_pg_engine)
    assert queue._dialect == "postgresql"
    assert queue._max_writers == 4


def test_queue_capacity_deduplicated_hybrid_eviction():
    """Verify capacity cap at 100 jobs, name deduplication, and recurring eviction for one-time requests."""
    queue = JobQueue(poll_interval=0.1)
    queue._max_pending_jobs = 5  # Scaled down for unit test

    # 1. Register 5 recurring jobs
    for i in range(5):
        queue.register_job(
            name=f"recurring_job_{i}",
            func=lambda: None,
            interval_seconds=3600,
            start_after=100.0,
            priority=TaskPriority.LOW if i == 0 else TaskPriority.NORMAL,
        )

    assert len(queue._jobs) == 5

    # 2. Submitting a 6th recurring job is dropped to its next interval (not admitted)
    queue.register_job(
        name="overflow_recurring",
        func=lambda: None,
        interval_seconds=3600,
        start_after=100.0,
    )
    assert len(queue._jobs) == 5
    assert "overflow_recurring" not in queue._jobs

    # 3. Submitting a one-time job evicts the lowest-priority recurring job (recurring_job_0)
    queue.register_job(
        name="user_interactive_action",
        func=lambda: None,
        interval_seconds=None,
    )
    assert len(queue._jobs) == 5
    assert "user_interactive_action" in queue._jobs
    assert "recurring_job_0" not in queue._jobs

    # 4. Strict deduplication by name
    queue.register_job(
        name="user_interactive_action",
        func=lambda: None,
        interval_seconds=None,
        params={"updated": True},
    )
    assert len(queue._jobs) == 5
    assert queue._jobs["user_interactive_action"].params == {"updated": True}


def test_wal_backpressure_proactive_checkpoint(tmp_path):
    """Verify that when WAL size exceeds 32 MB, proactive checkpointing is evaluated."""
    queue = JobQueue()

    # Mock Path to simulate a 35 MB WAL file
    fake_wal = tmp_path / "music_library.db-wal"
    fake_wal.write_bytes(b"0" * (35 * 1024 * 1024))

    with patch("core.task_manager.task_queue.Path") as mock_path:
        mock_path.return_value = fake_wal
        with patch.object(queue, "_detect_db_dialect", return_value="sqlite"):
            # WAL exceeds 32 MB -> triggers checkpoint attempt
            with patch("sqlalchemy.text") as mock_text:
                result = queue._check_wal_backpressure()
                # Since fake_wal was not truncated by real SQLite engine, backpressure remains active (False)
                assert result is False


def test_transient_error_backoff_and_terminal_failure():
    """Verify that transient errors trigger exponential backoff and deterministic errors fail terminally."""
    queue = JobQueue()

    # 1. Transient error: 'database is locked' -> RETRY_BACKOFF
    def lock_fail():
        raise RuntimeError("OperationalError: database is locked")

    queue.register_job(
        name="transient_task",
        func=lock_fail,
        interval_seconds=None,
        max_retries=2,
        backoff_base=2.0,
        backoff_factor=2.0,
    )

    job = queue._jobs["transient_task"]
    queue._execute_wrapper(job)

    assert job.current_retries == 1
    assert job.state == TaskStatus.RETRY_BACKOFF
    assert "transient_task" in queue._jobs

    # 2. Terminal error: syntax or integrity error -> FAILED_TERMINAL
    def fatal_fail():
        raise SyntaxError("Deterministic parse crash")

    queue.register_job(
        name="fatal_task",
        func=fatal_fail,
        interval_seconds=None,
        max_retries=3,
    )

    fatal_job = queue._jobs["fatal_task"]
    queue._execute_wrapper(fatal_job)

    assert fatal_job.state == TaskStatus.FAILED_TERMINAL
    # One-shot terminal failure is removed from queue
    assert "fatal_task" not in queue._jobs


def test_system_jobs_category_registration():
    """Verify that key write-heavy system jobs are registered with DATABASE_WRITE_HEAVY."""
    from core.task_manager import system_jobs

    test_queue = JobQueue()
    system_jobs.job_queue = test_queue

    try:
        system_jobs.register_retroactive_metadata_enhancement_job(interval_seconds=3600, enabled=False)
        system_jobs.register_database_update_job(interval_seconds=3600, enabled=False)
        system_jobs.register_duplicate_scan_job(interval_seconds=3600, enabled=False)
        system_jobs.register_stale_track_scan_job(interval_seconds=3600, enabled=False)

        assert test_queue._jobs["retroactive_metadata_enhancement"].category == TaskCategory.DATABASE_WRITE_HEAVY
        assert test_queue._jobs["database_update"].category == TaskCategory.DATABASE_WRITE_HEAVY
        assert test_queue._jobs["duplicate_scan_job"].category == TaskCategory.DATABASE_WRITE_HEAVY
        assert test_queue._jobs["stale_track_scan_job"].category == TaskCategory.DATABASE_WRITE_HEAVY
    finally:
        system_jobs.job_queue = JobQueue()
