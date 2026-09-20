import pytest
from unittest.mock import MagicMock, patch
from starlette.requests import Request

from web.schemas.job import JobRunRequest
from web.routes.jobs import run_job
from core.task_manager.task_queue import job_queue
from core.task_manager.system_jobs import register_retroactive_metadata_enhancement_job


def test_job_run_request_schema():
    """Verify JobRunRequest supports force, force_refresh, and extra fields."""
    req1 = JobRunRequest(job_name="retroactive_metadata_enhancement", force=True, batch_size=25)
    assert req1.force is True
    assert req1.batch_size == 25

    req2 = JobRunRequest.model_validate({
        "job_name": "retroactive_metadata_enhancement",
        "force_refresh": True,
        "custom_key": "custom_value",
    })
    assert req2.force_refresh is True
    assert req2.custom_key == "custom_value"


@pytest.mark.asyncio
async def test_run_job_force_payload_propagation():
    """Verify run_job properly propagates force / force_refresh from payload into job execution params."""
    with patch.object(job_queue, "execute_job_now", return_value=True) as mock_exec, \
         patch("web.routes.jobs.jq_list_jobs", return_value=[{"name": "retroactive_metadata_enhancement", "running": False}]):

        # Scenario 1: Top-level force=True
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/system/jobs/run",
            "headers": [],
            "query_string": b"",
        }
        req = Request(scope)
        payload = JobRunRequest(job_name="retroactive_metadata_enhancement", force=True)

        resp = await run_job(req, payload)
        mock_exec.assert_called_with("retroactive_metadata_enhancement", params={
            "force_refresh": True,
            "force": True,
        })

        # Scenario 2: Top-level force_refresh=True with batch_size & check_all_files
        mock_exec.reset_mock()
        payload2 = JobRunRequest(
            job_name="retroactive_metadata_enhancement",
            force_refresh=True,
            check_all_files=True,
            batch_size=150,
            limit=500,
        )
        await run_job(req, payload2)
        mock_exec.assert_called_with("retroactive_metadata_enhancement", params={
            "force_refresh": True,
            "force": True,
            "check_all_files": True,
            "batch_size": 150,
            "limit": 500,
        })

        # Scenario 3: Passed in nested params dict
        mock_exec.reset_mock()
        payload3 = JobRunRequest(
            job_name="retroactive_metadata_enhancement",
            params={"force": True, "batch_size": 50},
        )
        await run_job(req, payload3)
        mock_exec.assert_called_with("retroactive_metadata_enhancement", params={
            "force": True,
            "force_refresh": True,
            "batch_size": 50,
        })


@pytest.mark.asyncio
async def test_run_job_query_params_propagation():
    """Verify run_job extracts and normalizes force parameters from query string."""
    with patch.object(job_queue, "execute_job_now", return_value=True) as mock_exec, \
         patch("web.routes.jobs.jq_list_jobs", return_value=[{"name": "retroactive_metadata_enhancement", "running": False}]):

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/system/jobs/run",
            "headers": [],
            "query_string": b"job_name=retroactive_metadata_enhancement&force=true&check_all_files=1&batch_size=80",
        }
        req = Request(scope)
        await run_job(req, None)

        mock_exec.assert_called_with("retroactive_metadata_enhancement", params={
            "force_refresh": True,
            "force": True,
            "check_all_files": True,
            "batch_size": 80,
        })


@pytest.mark.asyncio
async def test_run_job_check_all_files_infers_force_refresh():
    """Verify run_job infers force_refresh=True when check_all_files=True is passed without explicit force flag."""
    with patch.object(job_queue, "execute_job_now", return_value=True) as mock_exec, \
         patch("web.routes.jobs.jq_list_jobs", return_value=[{"name": "retroactive_metadata_enhancement", "running": False}]):

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/system/jobs/run",
            "headers": [],
            "query_string": b"",
        }
        req = Request(scope)
        payload = JobRunRequest(
            job_name="retroactive_metadata_enhancement",
            params={"check_all_files": True, "batch_size": 50},
        )
        await run_job(req, payload)
        mock_exec.assert_called_with("retroactive_metadata_enhancement", params={
            "check_all_files": True,
            "force_refresh": True,
            "force": True,
            "batch_size": 50,
        })


def test_get_tracks_for_enhancement_pagination_with_exclude_ids(tmp_path):
    """Verify get_tracks_for_enhancement properly paginates using exclude_ids across batches."""
    from database.music_database import (
        Album,
        Artist,
        Base,
        LocalMedia,
        MusicDatabase,
        Track,
    )
    from core.database.repositories.track_repo import TrackRepository

    db = MusicDatabase(tmp_path / "test_pagination.db")
    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        artist = Artist(name="Artist Test")
        album = Album(title="Album Test", artist=artist)
        session.add_all([artist, album])
        session.flush()

        # Add 5 tracks
        for i in range(1, 6):
            t = Track(
                id=i,
                title=f"Track {i}",
                artist=artist,
                album=album,
                musicbrainz_id=f"mbid-{i}",
                metadata_status={"enhanced": True},
            )
            session.add(t)
            session.flush()

            m = LocalMedia(
                track_id=t.id,
                file_path=str(tmp_path / f"track_{i}.flac"),
                file_format="flac",
                media_id=f"m_{i}",
            )
            session.add(m)

    with db.session_scope() as session:
        processed_ids = set()

        # Batch 1 (size=2)
        batch1 = TrackRepository.get_tracks_for_enhancement(
            session, batch_size=2, force_refresh=True, exclude_ids=processed_ids
        )
        assert len(batch1) == 2
        for t in batch1:
            processed_ids.add(t.id)
        assert processed_ids == {1, 2}

        # Batch 2 (size=2, exclude {1, 2})
        batch2 = TrackRepository.get_tracks_for_enhancement(
            session, batch_size=2, force_refresh=True, exclude_ids=processed_ids
        )
        assert len(batch2) == 2
        for t in batch2:
            processed_ids.add(t.id)
        assert processed_ids == {1, 2, 3, 4}

        # Batch 3 (size=2, exclude {1, 2, 3, 4})
        batch3 = TrackRepository.get_tracks_for_enhancement(
            session, batch_size=2, force_refresh=True, exclude_ids=processed_ids
        )
        assert len(batch3) == 1
        for t in batch3:
            processed_ids.add(t.id)
        assert processed_ids == {1, 2, 3, 4, 5}

        # Batch 4 (all excluded) -> 0 items
        batch4 = TrackRepository.get_tracks_for_enhancement(
            session, batch_size=2, force_refresh=True, exclude_ids=processed_ids
        )
        assert len(batch4) == 0


def test_system_job_run_metadata_enhancement_kwargs():
    """Verify run_metadata_enhancement in system_jobs extracts force/force_refresh and launches worker process."""
    from core.task_manager import system_jobs, task_queue

    test_queue = task_queue.JobQueue()
    with patch.object(system_jobs, "job_queue", test_queue):
        system_jobs.register_retroactive_metadata_enhancement_job(interval_seconds=86400, enabled=True)

        job = test_queue.get_job("retroactive_metadata_enhancement")
        assert job is not None
        assert "force_refresh" in job.params

        func = job.func

        with patch("multiprocessing.Process") as mock_proc:
            instance = MagicMock()
            instance.pid = 9999
            instance.exitcode = 0
            mock_proc.return_value = instance

            # Call with force=True in kwargs
            func(batch_size=50, force=True, check_all_files=True)

            mock_proc.assert_called_once()
            _, kwargs = mock_proc.call_args
            target_args = kwargs["args"]
            # args = (batch_size, check_all_files, limit, force_refresh)
            assert target_args[0] == 50
            assert target_args[1] is True
            assert target_args[2] is None
            assert target_args[3] is True

