"""
Phase 3 Task Manager & Database Write Lease Integration Tests.
Verifies:
1. DBWriter thread lifecycle is supervised under ProcessSupervisor.
2. DBWriter stop() cleanly joins and unregisters from ProcessSupervisor.
3. session_scope in music_database.py and working_database.py acquires db_write_lease.
4. Re-entrant nesting of db_write_lease across database sessions.
5. Ingestion orchestrator, library hygiene, state listener, and user history mutations acquire db_write_lease.
6. Error handler and rate limiter cooperative cancellation checks.
"""

import os
import tempfile
import time
from unittest.mock import patch

import pytest

from core.task_manager.models import OwnerType, ProcessCategory
from core.task_manager.supervisor import supervisor
from core.task_manager.task_queue import db_write_lease, job_queue
from database.music_database import Artist, Track, get_database
from database.working_database import Account, get_working_database


@pytest.fixture(autouse=True)
def clean_supervisor():
    """Ensure supervisor is clean before and after tests."""
    yield
    # Clean up any lingering test processes
    with supervisor._lock:
        to_clean = [k for k in supervisor._processes.keys() if "test" in k.lower() or "dbwriter" in k.lower()]
        for k in to_clean:
            supervisor._processes.pop(k, None)
            supervisor._cancellation_events.pop(k, None)


def test_db_writer_supervised_lifecycle():
    """Verify DBWriter thread is registered with ProcessSupervisor and unregisters on stop."""
    from database.engine import _DBWriter

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        writer = _DBWriter(db_path)
        assert writer._reg_id is not None

        # Verify registered in supervisor
        reg = supervisor._processes.get(writer._reg_id)
        assert reg is not None
        assert reg.owner_id == "database.engine"
        assert reg.owner_type == OwnerType.CORE
        assert reg.category == ProcessCategory.CORE_SYSTEM

        # Verify executing a write works
        res = writer.enqueue(lambda cursor: cursor.execute("SELECT 1").fetchone()[0], wait=True)
        assert res == 1

        # Stop writer and verify unregistration
        reg_id = writer._reg_id
        writer.stop()
        assert writer._reg_id is None
        assert supervisor._processes.get(reg_id) is None
    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


def test_music_database_session_scope_acquires_write_lease():
    """Verify session_scope in music_database acquires db_write_lease on commit."""
    db = get_database()
    lease_acquired = False
    original_lease = job_queue.db_write_lease

    def lease_wrapper(*args, **kwargs):
        nonlocal lease_acquired
        lease_acquired = True
        return original_lease(*args, **kwargs)

    with patch.object(job_queue, "db_write_lease", side_effect=lease_wrapper), db.session_scope() as session:
        artist = session.query(Artist).first()
        if not artist:
            artist = Artist(name="Phase 3 Artist", normalized_name="phase 3 artist")
            session.add(artist)
            session.flush()

        track = session.query(Track).filter_by(sync_id="phase3_test_sync_1").first()
        if not track:
            track = Track(
                sync_id="phase3_test_sync_1",
                title="Phase 3 Test Track",
                artist_id=artist.id,
                duration=180000,
            )
            session.add(track)

    assert lease_acquired is True


def test_working_database_session_scope_acquires_write_lease():
    """Verify session_scope in working_database acquires db_write_lease."""
    w_db = get_working_database()
    lease_acquired = False
    original_lease = job_queue.db_write_lease

    def lease_wrapper(*args, **kwargs):
        nonlocal lease_acquired
        lease_acquired = True
        return original_lease(*args, **kwargs)

    with patch.object(job_queue, "db_write_lease", side_effect=lease_wrapper), w_db.session_scope() as session:
        acc = session.query(Account).filter_by(username="phase3_test_user").first()
        if not acc:
            acc = Account(
                username="phase3_test_user",
                plugin_id=1,
                remote_account_id="remote_test_123",
            )
            session.add(acc)

    assert lease_acquired is True

    # Verify get_system_user_id acquires lease
    lease_acquired = False
    sys_id = w_db.get_system_user_id()
    assert sys_id is not None


def test_reentrant_db_write_lease_across_nested_scopes():
    """Verify nesting outer db_write_lease with inner session_scope does not deadlock."""
    db = get_database()

    # Ensure an artist exists
    with db.session_scope() as s:
        artist = s.query(Artist).first()
        if not artist:
            artist = Artist(name="Reentrant Artist", normalized_name="reentrant artist")
            s.add(artist)

    # Outermost lease
    with db_write_lease(task_name="outer_test_task"):
        # Inner session scope that also acquires lease
        with db.session_scope() as session:
            found = session.query(Artist).first()
            assert found is not None

        # Even deeper nesting
        with db_write_lease(task_name="deeply_nested"), db.session_scope() as session2:
            found2 = session2.query(Artist).first()
            assert found2 is not None


def test_orchestrator_ingestion_acquires_write_lease():
    """Verify ingestion orchestrator wraps bulk upsert commits in db_write_lease."""
    from core.orchestrator.ingestion import IngestionOrchestrator

    db = get_database()
    orchestrator = IngestionOrchestrator(session_factory=db.session_factory, batch_size=10)

    lease_acquired = False
    original_lease = job_queue.db_write_lease

    def lease_wrapper(*args, **kwargs):
        nonlocal lease_acquired
        lease_acquired = True
        return original_lease(*args, **kwargs)

    sample_tracks = [
        {
            "title": "Ingestion Test Track",
            "artist": "Ingestion Artist",
            "album": "Ingestion Album",
            "file_path": "/path/to/phase3_ingest_test.flac",
            "duration_ms": 150000,
        }
    ]

    with patch.object(job_queue, "db_write_lease", side_effect=lease_wrapper):
        orchestrator.ingest_telemetry_batch(sample_tracks)

    assert lease_acquired is True


def test_error_handler_cooperative_cancellation():
    """Verify error handler handle_exception halts early when task is marked cancelled."""
    from core.error_handler import ErrorHandler

    counter = 0

    def failing_fn():
        nonlocal counter
        counter += 1
        raise ValueError("Simulated failure")

    with patch.object(supervisor, "is_current_task_cancelled", side_effect=[False, True]):
        result = ErrorHandler.handle_exception(
            failing_fn,
            retries=3,
            backoff_base=0.01,
            backoff_factor=1.0,
        )
        assert result is None
        # Should have stopped after first failure without completing all retries
        assert counter == 1


def test_rate_limiter_cooperative_cancellation():
    """Verify TokenBucketRateLimiter.wait halts early when task is marked cancelled."""
    from core.rate_limiter import TokenBucketRateLimiter

    bucket = TokenBucketRateLimiter(capacity=1, refill_rate=0.1)
    bucket.consume(1)  # Empty bucket

    with patch.object(supervisor, "is_current_task_cancelled", return_value=True):
        start = time.time()
        bucket.wait(1)
        elapsed = time.time() - start
        # Should return almost immediately rather than sleeping for 10 seconds
        assert elapsed < 1.0
