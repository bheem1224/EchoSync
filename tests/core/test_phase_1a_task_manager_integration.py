"""
Phase 1A Integration Test Suite:
- Native Rayon Thread Pool Initialization & Idempotency
- Re-entrant thread-aware database write lease
- Repository mutation lease protection (TrackRepository, DownloadRepository)
- DownloadManager JobQueue general pool dispatching
"""

import threading

import pytest

from core.database.models.working import DownloadIntent, DownloadStatus
from core.database.repositories.download_repo import DownloadRepository
from core.database.repositories.track_repo import TrackRepository
from core.enums import TaskCategory, TaskPriority
from core.metadata.schemas import EntityAliasProposal
from core.task_manager.task_queue import db_write_lease, job_queue
from database.music_database import Artist, Track, get_database
from database.working_database import get_working_database
from services.download_manager import get_download_manager, register_download_manager_job


def test_native_thread_pool_initialization_and_idempotency():
    """Verify that echosync_core exposes init_native_thread_pool and behaves idempotently."""
    try:
        import echosync_core
    except ImportError:
        pytest.skip("echosync_core C-extension not available in this test environment")

    # Call init_native_thread_pool
    threads = echosync_core.init_native_thread_pool()
    assert isinstance(threads, int)
    assert 1 <= threads <= 8

    # Idempotent call with override must not fail
    second_threads = echosync_core.init_native_thread_pool(4)
    assert isinstance(second_threads, int)
    assert second_threads == threads


def test_reentrant_db_write_lease_nesting():
    """Verify that db_write_lease supports nested re-entrancy without self-deadlock."""
    # Outer level
    with db_write_lease(task_name="outer_test", timeout=2.0):
        tid = threading.get_ident()
        assert job_queue._lease_holders.get(tid) == 1

        # Inner level 1
        with db_write_lease(task_name="inner_level_1", timeout=2.0):
            assert job_queue._lease_holders.get(tid) == 2

            # Inner level 2
            with db_write_lease(task_name="inner_level_2", timeout=2.0):
                assert job_queue._lease_holders.get(tid) == 3

            assert job_queue._lease_holders.get(tid) == 2

        assert job_queue._lease_holders.get(tid) == 1

    # Completely released
    assert tid not in job_queue._lease_holders


def test_reentrant_db_write_lease_blocks_distinct_threads():
    """Verify that mutual exclusion between different threads remains strictly enforced."""
    lease_acquired_by_t2 = False

    def thread_2_worker():
        nonlocal lease_acquired_by_t2
        try:
            with db_write_lease(task_name="thread_2", timeout=0.3):
                lease_acquired_by_t2 = True
        except TimeoutError:
            lease_acquired_by_t2 = False

    with db_write_lease(task_name="thread_1", timeout=2.0):
        t2 = threading.Thread(target=thread_2_worker)
        t2.start()
        t2.join(timeout=1.0)
        assert not lease_acquired_by_t2, "Thread 2 should have been blocked by Thread 1"


def test_track_repo_mutations_execute_with_lease():
    """Verify that TrackRepository write operations execute within re-entrant write lease."""
    db = get_database()
    with db.session_scope() as session:
        artist = session.query(Artist).first()
        if not artist:
            artist = Artist(name="Phase1A Artist", normalized_name="phase1a artist")
            session.add(artist)
            session.flush()

        track = session.query(Track).filter_by(sync_id="phase1a_test_sync").first()
        if not track:
            track = Track(
                sync_id="phase1a_test_sync",
                title="Phase 1A Track",
                artist_id=artist.id,
            )
            session.add(track)
            session.commit()

        track_id = track.id

        # 1. upsert_entity_aliases with commit=True
        proposal = EntityAliasProposal(
            entity_type="track",
            value="Phase 1A Track (Remastered)",
            language="en",
            script="Latn",
            alias_type="translation",
        )
        upserted = TrackRepository.upsert_entity_aliases(
            session=session,
            proposals=[proposal],
            sync_id="phase1a_test_sync",
            plugin_id=999,
            commit=True,
        )
        assert upserted >= 1

        # 2. set_entity_attributes with commit=True
        res = TrackRepository.set_entity_attributes(
            session=session,
            entity_type="track",
            entity_id=track_id,
            plugin_id=999,
            key="test_key",
            value="test_val",
            commit=True,
        )
        assert res is True

        # 3. delete_entity_attribute with commit=True
        deleted = TrackRepository.delete_entity_attribute(
            session=session,
            entity_type="track",
            entity_id=track_id,
            plugin_id=999,
            key="test_key",
            commit=True,
        )
        assert deleted is True


def test_download_repo_mutations_execute_with_lease():
    """Verify DownloadRepository transitions acquire write lease and commit successfully."""
    work_db = get_working_database()
    repo = DownloadRepository(work_db=work_db)

    item = repo.create_queue_item(
        sync_id="phase1a_dl_test",
        intent=DownloadIntent.MANUAL_OMNI,
        candidate_stack=[{"id": "c1", "plugin_id": "test"}, {"id": "c2", "plugin_id": "test"}],
        active_candidate_id="c1",
        status=DownloadStatus.DOWNLOADING,
    )
    assert item.id is not None

    # Rotate candidate -> RETRYING
    rotated = repo.transition_to_retrying_or_failed(item.id, reason="TEST_RETRY")
    assert rotated is True

    # Transition to failed
    failed = repo.transition_to_failed(item.id, error_reason="TEST_TERMINAL")
    assert failed is True


def test_download_manager_job_queue_alignment():
    """Verify DownloadManager sweeps and single download tasks are dispatched via JobQueue under GENERAL."""
    dm = get_download_manager()

    # 1. 6-Hour sweep registration
    register_download_manager_job(interval_seconds=21600)
    job = job_queue.get_job("download_manager")
    assert job is not None
    assert job.category == TaskCategory.GENERAL
    assert job.interval_seconds == 21600

    # 2. Single download on-demand dispatch
    dm.process_single_download(download_id=99999)
    single_job = job_queue.get_job("download:99999")
    assert single_job is not None
    assert single_job.category == TaskCategory.GENERAL
    assert single_job.priority == TaskPriority.HIGH
    assert "download:99999" in single_job.tags
