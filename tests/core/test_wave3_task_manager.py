"""Wave 3 Task Manager remediation unit tests.

Covers:
1. ProcessSupervisor._release_db_sessions_for_thread targeting only worker tid.
2. ProcessSupervisor.spawn_supervised_thread pre-registration & start-barrier sync.
3. JobQueue.lease_task collision preservation with recurring jobs.
4. JobQueue._check_wal_backpressure dynamic WAL resolution across config, music, and working DBs.
5. health_service.get_system_health clean SQLAlchemy text() import and query execution.
"""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from core.enums import TaskCategory, TaskStatus
from core.task_manager.models import OwnerType, ProcessCategory
from core.task_manager.supervisor import ProcessSupervisor
from core.task_manager.task_queue import JobQueue


# ── 1. ProcessSupervisor._release_db_sessions_for_thread ────────────────────


def test_release_db_sessions_removes_only_target_thread_in_scoped_registry(tmp_path):
    """Verify ScopedRegistry cleanup removes ONLY target worker tid and preserves caller session."""
    work_engine = create_engine(f"sqlite:///{tmp_path / 'working.db'}")
    music_engine = create_engine(f"sqlite:///{tmp_path / 'music.db'}")

    work_reg = scoped_session(sessionmaker(bind=work_engine), scopefunc=threading.get_ident)
    music_reg = scoped_session(sessionmaker(bind=music_engine), scopefunc=threading.get_ident)

    caller_tid = threading.get_ident()
    caller_work_sess = work_reg()
    caller_music_sess = music_reg()

    worker_tid_holder: dict[str, int] = {}
    worker_sessions: dict[str, object] = {}
    worker_ready = threading.Event()
    release_worker = threading.Event()

    def worker():
        worker_tid_holder["tid"] = threading.get_ident()
        worker_sessions["work"] = work_reg()
        worker_sessions["music"] = music_reg()
        worker_ready.set()
        release_worker.wait(timeout=5.0)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    assert worker_ready.wait(timeout=2.0)

    worker_tid = worker_tid_holder["tid"]
    assert worker_tid != caller_tid
    assert caller_tid in work_reg.registry.registry
    assert worker_tid in work_reg.registry.registry
    assert caller_tid in music_reg.registry.registry
    assert worker_tid in music_reg.registry.registry

    sup = ProcessSupervisor()
    try:
        with (
            patch("database.working_database.working_session_registry", work_reg),
            patch("database.music_database.music_session_registry", music_reg),
            patch.object(worker_sessions["work"], "close", wraps=worker_sessions["work"].close) as mock_w_close,
            patch.object(worker_sessions["music"], "close", wraps=worker_sessions["music"].close) as mock_m_close,
            patch.object(caller_work_sess, "close", wraps=caller_work_sess.close) as mock_caller_w_close,
            patch.object(caller_music_sess, "close", wraps=caller_music_sess.close) as mock_caller_m_close,
        ):
            sup._release_db_sessions_for_thread(worker_tid)

            # Target worker thread's sessions were popped and closed
            assert worker_tid not in work_reg.registry.registry
            assert worker_tid not in music_reg.registry.registry
            mock_w_close.assert_called_once()
            mock_m_close.assert_called_once()

            # Caller thread's sessions remain registered and open
            assert caller_tid in work_reg.registry.registry
            assert caller_tid in music_reg.registry.registry
            assert work_reg() is caller_work_sess
            assert music_reg() is caller_music_sess
            mock_caller_w_close.assert_not_called()
            mock_caller_m_close.assert_not_called()
    finally:
        release_worker.set()
        t.join(timeout=2.0)
        work_reg.remove()
        music_reg.remove()
        work_engine.dispose()
        music_engine.dispose()


def test_release_db_sessions_preserves_caller_under_thread_local_registry(tmp_path):
    """Verify ThreadLocalRegistry never wipes caller thread's session when targeting a worker tid."""
    work_engine = create_engine(f"sqlite:///{tmp_path / 'working_tl.db'}")
    music_engine = create_engine(f"sqlite:///{tmp_path / 'music_tl.db'}")

    work_reg = scoped_session(sessionmaker(bind=work_engine))
    music_reg = scoped_session(sessionmaker(bind=music_engine))

    caller_tid = threading.get_ident()
    caller_work_sess = work_reg()
    caller_music_sess = music_reg()
    other_tid = caller_tid + 12345

    sup = ProcessSupervisor()
    try:
        with (
            patch("database.working_database.working_session_registry", work_reg),
            patch("database.music_database.music_session_registry", music_reg),
        ):
            # None tid -> no-op
            sup._release_db_sessions_for_thread(None)
            assert work_reg.registry.has()
            assert music_reg.registry.has()
            assert work_reg() is caller_work_sess
            assert music_reg() is caller_music_sess

            # Cross-thread tid -> caller session MUST remain intact
            sup._release_db_sessions_for_thread(other_tid)
            assert work_reg.registry.has()
            assert music_reg.registry.has()
            assert work_reg() is caller_work_sess
            assert music_reg() is caller_music_sess

            # Same-thread tid -> removes caller's own session cleanly
            sup._release_db_sessions_for_thread(caller_tid)
            assert not work_reg.registry.has()
            assert not music_reg.registry.has()
    finally:
        work_reg.remove()
        music_reg.remove()
        work_engine.dispose()
        music_engine.dispose()


# ── 2. ProcessSupervisor.spawn_supervised_thread synchronization ─────────────


def test_spawn_supervised_thread_synchronizes_before_target_and_no_fast_exit_leak():
    """Fast-exiting threads must see synchronized registration/thread_id and never leave zombies."""
    sup = ProcessSupervisor()
    observed: list[tuple[int, object, str | None]] = []
    lock = threading.Lock()

    def fast_target(expected_event: threading.Event):
        tid = threading.get_ident()
        cancel_ev = sup.get_cancellation_event(tid)
        active = sup.get_active_processes("test.fast")
        matching_name = next((p.task_name for p in active if p.thread_id == tid), None)
        with lock:
            observed.append((tid, cancel_ev, matching_name))

    threads = []
    events = []
    for i in range(40):
        ev = threading.Event()
        events.append(ev)
        t, _reg_id = sup.spawn_supervised_thread(
            target=fast_target,
            name=f"fast_worker_{i}",
            owner_id="test.fast",
            owner_type=OwnerType.CORE,
            category=ProcessCategory.WORKER_THREAD,
            args=(ev,),
            cancellation_event=ev,
            bound_to_general_pool=False,
        )
        threads.append(t)

    for t in threads:
        t.join(timeout=3.0)

    assert len(observed) == 40
    for idx, (tid, cancel_ev, matching_name) in enumerate(observed):
        assert tid > 0
        assert cancel_ev is events[idx]
        assert matching_name == f"fast_worker_{idx}"

    # Zero leaked zombie entries in ProcessSupervisor
    assert sup.get_active_processes("test.fast") == []
    assert sup._processes == {}
    assert sup._cancellation_events == {}


def test_spawn_supervised_thread_unregisters_on_start_failure():
    """If Thread.start() fails, pre-registered ProcessOwner entry is rolled back."""
    sup = ProcessSupervisor()

    with patch("threading.Thread.start", side_effect=RuntimeError("thread start failure")):
        with pytest.raises(RuntimeError, match="thread start failure"):
            sup.spawn_supervised_thread(
                target=lambda: None,
                name="fail_start",
                owner_id="test.fail",
                bound_to_general_pool=False,
            )

    assert sup._processes == {}
    assert sup._cancellation_events == {}


def test_spawn_supervised_thread_bound_to_general_pool_cleans_up():
    """Verify supervised thread bound to general pool acquires/releases semaphore and unregisters."""
    from core.task_manager.task_queue import job_queue

    sup = ProcessSupervisor()
    ran = threading.Event()

    t, reg_id = sup.spawn_supervised_thread(
        target=ran.set,
        name="pooled_fast_worker",
        owner_id="test.pooled",
        bound_to_general_pool=True,
    )
    assert ran.wait(timeout=2.0)
    t.join(timeout=2.0)

    assert sup.get_active_processes("test.pooled") == []
    assert reg_id not in sup._processes
    # General pool slots are all released back (can acquire full count)
    assert job_queue._general_workers.acquire(blocking=False) is True
    job_queue._general_workers.release()


# ── 3. JobQueue.lease_task colliding recurring job protection ──────────────


def test_lease_task_preserves_colliding_recurring_job():
    """Leasing a task with the same name as a recurring job must not overwrite or delete it."""
    queue = JobQueue(worker_count=1)
    recurring_calls = 0

    def recurring_fn():
        nonlocal recurring_calls
        recurring_calls += 1

    queue.register_job(
        name="library_sync",
        func=recurring_fn,
        interval_seconds=3600.0,
        start_after=60.0,
        category=TaskCategory.DATABASE_WRITE_HEAVY,
    )
    original_job = queue.get_job("library_sync")
    assert original_job is not None

    with queue.lease_task("library_sync", category=TaskCategory.BACKGROUND_METADATA) as lease_id:
        assert lease_id != "library_sync"
        leased_job = queue.get_job(lease_id)
        assert leased_job is not None
        assert leased_job.running is True
        assert leased_job.state == TaskStatus.RUNNING
        assert queue.is_job_running("library_sync") is True

        # Original recurring job remains intact during the lease
        still_there = queue.get_job("library_sync")
        assert still_there is original_job
        assert still_there.interval_seconds == 3600.0
        assert still_there.func is recurring_fn

    # After lease exit, lease entry is cleaned up AND recurring job remains intact in _jobs & _heap
    assert queue.get_job(lease_id) is None
    persisted = queue.get_job("library_sync")
    assert persisted is original_job
    assert persisted.interval_seconds == 3600.0
    assert persisted.func is recurring_fn
    assert persisted in queue._heap


def test_lease_task_preserves_colliding_recurring_job_on_exception():
    """Leased task failure must still clean up the lease while preserving the recurring job."""
    queue = JobQueue(worker_count=1)

    def recurring_fn():
        return None

    queue.register_job(
        name="metadata_sync",
        func=recurring_fn,
        interval_seconds=1800.0,
        start_after=30.0,
    )

    with pytest.raises(RuntimeError, match="lease exploded"):
        with queue.lease_task("metadata_sync") as lease_id:
            assert lease_id != "metadata_sync"
            raise RuntimeError("lease exploded")

    assert queue.get_job(lease_id) is None
    persisted = queue.get_job("metadata_sync")
    assert persisted is not None
    assert persisted.interval_seconds == 1800.0
    assert persisted in queue._heap


def test_register_recurring_job_during_active_lease_is_preserved():
    """Registering a recurring job while a lease of the same name is active must survive lease exit."""
    queue = JobQueue(worker_count=1)

    def recurring_fn():
        return "ok"

    with queue.lease_task("metadata_enhancement", category=TaskCategory.BACKGROUND_METADATA) as lease_id:
        assert lease_id == "metadata_enhancement"
        queue.register_job(
            name="metadata_enhancement",
            func=recurring_fn,
            interval_seconds=900.0,
            start_after=15.0,
            category=TaskCategory.DATABASE_WRITE_HEAVY,
        )

    scheduled = queue.get_job("metadata_enhancement")
    assert scheduled is not None
    assert scheduled.interval_seconds == 900.0
    assert scheduled.func is recurring_fn
    assert scheduled.running is False
    assert scheduled.state == TaskStatus.QUEUED
    assert scheduled in queue._heap


# ── 4. JobQueue._check_wal_backpressure dynamic WAL resolution ──────────────


@pytest.mark.parametrize(
    ("env_target", "filename", "expected_db_kind"),
    [
        ("ECHOSYNC_DATA_DIR", "music_library.db-wal", "music"),
        ("ECHOSYNC_DATA_DIR", "working.db-wal", "working"),
        ("ECHOSYNC_CONFIG_DIR", "config.db-wal", "config"),
    ],
)
def test_check_wal_backpressure_resolves_all_three_wals_via_env(
    tmp_path, monkeypatch, env_target, filename, expected_db_kind
):
    """_check_wal_backpressure dynamically resolves config, music, and working WAL files via env vars."""
    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    data_dir.mkdir()
    config_dir.mkdir()

    monkeypatch.setenv("ECHOSYNC_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ECHOSYNC_CONFIG_DIR", str(config_dir))

    # Create small healthy WALs for the other files so we prove the loop doesn't stop early
    (data_dir / "music_library.db-wal").write_bytes(b"0" * 1024)
    (data_dir / "working.db-wal").write_bytes(b"0" * 1024)
    (config_dir / "config.db-wal").write_bytes(b"0" * 1024)

    target_dir = data_dir if env_target == "ECHOSYNC_DATA_DIR" else config_dir
    oversized_wal = target_dir / filename
    oversized_wal.write_bytes(b"0" * (33 * 1024 * 1024))

    mock_engine = MagicMock()
    mock_engine.dialect.name = "sqlite"
    mock_engine.url.database = None
    queue = JobQueue(engine=mock_engine)

    checkpointed: list[str] = []
    with patch.object(queue, "_checkpoint_sqlite_wal", side_effect=checkpointed.append):
        assert queue._check_wal_backpressure() is False

    assert checkpointed == [expected_db_kind]


def test_check_wal_backpressure_passes_when_all_wals_below_threshold(tmp_path, monkeypatch):
    """Returns True when all 3 resolved WAL files are below 32 MB."""
    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    data_dir.mkdir()
    config_dir.mkdir()

    monkeypatch.setenv("ECHOSYNC_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ECHOSYNC_CONFIG_DIR", str(config_dir))

    (data_dir / "music_library.db-wal").write_bytes(b"0" * 2048)
    (data_dir / "working.db-wal").write_bytes(b"0" * 2048)
    (config_dir / "config.db-wal").write_bytes(b"0" * 2048)

    mock_engine = MagicMock()
    mock_engine.dialect.name = "sqlite"
    mock_engine.url.database = None
    queue = JobQueue(engine=mock_engine)

    with patch.object(queue, "_checkpoint_sqlite_wal") as mock_ckpt:
        assert queue._check_wal_backpressure() is True
        mock_ckpt.assert_not_called()


def test_check_wal_backpressure_resolves_active_db_singletons_without_env(tmp_path, monkeypatch):
    """When env vars are unset, active DB singleton paths are inspected dynamically."""
    monkeypatch.delenv("ECHOSYNC_DATA_DIR", raising=False)
    monkeypatch.delenv("ECHOSYNC_CONFIG_DIR", raising=False)

    custom_working = tmp_path / "custom_working.db"
    custom_working_wal = Path(f"{custom_working}-wal")
    custom_working_wal.write_bytes(b"0" * (33 * 1024 * 1024))

    custom_music = tmp_path / "custom_music.db"
    custom_config = tmp_path / "custom_config.db"

    mock_engine = MagicMock()
    mock_engine.dialect.name = "sqlite"
    mock_engine.url.database = None
    queue = JobQueue(engine=mock_engine)

    with (
        patch("database.music_database._db_instance", SimpleNamespace(database_path=custom_music)),
        patch("database.working_database._working_db_instance", SimpleNamespace(database_path=custom_working)),
        patch("database.config_database._config_db", SimpleNamespace(database_path=custom_config)),
        patch.object(queue, "_checkpoint_sqlite_wal") as mock_ckpt,
    ):
        assert queue._check_wal_backpressure() is False
        mock_ckpt.assert_called_once_with("working")


def test_checkpoint_sqlite_wal_executes_against_real_databases(tmp_path, monkeypatch):
    """Verify _checkpoint_sqlite_wal runs PRAGMA wal_checkpoint(PASSIVE) cleanly on all 3 DBs."""
    from database.config_database import ConfigDatabase
    from database.music_database import Base, MusicDatabase
    from database.working_database import WorkingBase, WorkingDatabase

    monkeypatch.setenv("ECHOSYNC_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ECHOSYNC_CONFIG_DIR", str(tmp_path))

    music_db = MusicDatabase(str(tmp_path / "music_library.db"))
    Base.metadata.create_all(music_db.engine)
    working_db = WorkingDatabase(str(tmp_path / "working.db"))
    WorkingBase.metadata.create_all(working_db.engine)
    config_db = ConfigDatabase(db_path=str(tmp_path / "config.db"))

    queue = JobQueue(engine=music_db.engine)
    try:
        with (
            patch("database.music_database.get_database", return_value=music_db),
            patch("database.working_database.get_working_database", return_value=working_db),
            patch("database.config_database.get_config_database", return_value=config_db),
        ):
            queue._checkpoint_sqlite_wal("engine")
            queue._checkpoint_sqlite_wal("music")
            queue._checkpoint_sqlite_wal("working")
            queue._checkpoint_sqlite_wal("config")
    finally:
        music_db.dispose()
        working_db.dispose()


# ── 5. health_service.get_system_health SQLAlchemy text() and query check ──


def test_get_system_health_executes_text_query_and_stats_cleanly(tmp_path, monkeypatch, caplog):
    """get_system_health imports sqlalchemy.text cleanly and runs all health queries without NameError."""
    from core.task_manager import health_service
    from database.config_database import ConfigDatabase
    from database.music_database import Base, MusicDatabase

    monkeypatch.setenv("ECHOSYNC_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ECHOSYNC_CONFIG_DIR", str(tmp_path))

    import zlib

    music_db = MusicDatabase(str(tmp_path / "music_library.db"))
    Base.metadata.create_all(music_db.engine)
    config_db = ConfigDatabase(db_path=str(tmp_path / "config.db"))
    # Seed an active non-auth service so active_services SQL query and provider loop are exercised
    svc_name = "echosync.test_health_svc"
    svc_plugin_id = zlib.crc32(svc_name.encode("utf-8")) & 0xFFFFFFFF
    with config_db._get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO services (name, plugin_id, service_type, is_active) VALUES (?, ?, ?, 1)",
            (svc_name, svc_plugin_id, "metadata"),
        )
        conn.commit()

    try:
        with (
            patch("database.get_database", return_value=music_db),
            patch("database.music_database.get_database", return_value=music_db),
            patch("database.config_database.get_config_database", return_value=config_db),
            patch.object(health_service.config_manager, "get_disabled_plugins", return_value=[]),
            patch.object(health_service.health_check_registry, "get_all_last_results", return_value={}),
        ):
            result = health_service.get_system_health()

        assert result["status"] == "healthy"
        assert result["results"]["core"]["status"] == "healthy"
        assert result["results"]["core"]["message"] == "Core services operational"
        assert result["summary"]["total"] >= 2
        assert result["summary"]["operational"] >= 1
        assert result["library"] == {
            "total_tracks": 0,
            "total_files": 0,
            "total_albums": 0,
            "storage_used": "0 B",
        }
        assert "fallback" not in caplog.text.lower()
    finally:
        music_db.dispose()


def test_get_system_health_reports_unhealthy_on_db_error(tmp_path, monkeypatch):
    """get_system_health degrades cleanly to unhealthy when DB SELECT 1 fails."""
    from core.task_manager import health_service
    from database.config_database import ConfigDatabase

    monkeypatch.setenv("ECHOSYNC_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ECHOSYNC_CONFIG_DIR", str(tmp_path))

    config_db = ConfigDatabase(db_path=str(tmp_path / "config.db"))
    broken_db = MagicMock()
    broken_db.session_scope.side_effect = RuntimeError("DB offline")
    broken_db.count_tracks.side_effect = RuntimeError("DB offline")

    with (
        patch("database.get_database", return_value=broken_db),
        patch("database.music_database.get_database", return_value=broken_db),
        patch("database.config_database.get_config_database", return_value=config_db),
        patch.object(health_service.config_manager, "get_disabled_plugins", return_value=[]),
        patch.object(health_service.health_check_registry, "get_all_last_results", return_value={}),
    ):
        result = health_service.get_system_health()

    assert result["status"] == "unhealthy"
    assert result["results"]["core"]["status"] == "unhealthy"
    assert result["summary"]["operational"] == 0
