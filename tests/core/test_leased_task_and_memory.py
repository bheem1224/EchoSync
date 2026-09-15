import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from core.enums import TaskCategory, TaskStatus
from core.task_manager import (
    is_paused,
    job_queue,
    lease_task,
    pause_job,
    resume_job,
    wait_for_resume,
)
from plugins.EchoSync.musicbrainz.client import MusicBrainzClient
from services.metadata_enhancer import RetroactiveEnhancer


def test_lease_task_lifecycle():
    """Verify lease_task properly registers a running parent job and cleans up on exit."""
    task_name = "test_parent_workflow"

    # Verify not running initially
    assert job_queue.get_job(task_name) is None
    assert not job_queue.is_job_running(task_name)

    with lease_task(task_name, category=TaskCategory.BACKGROUND_METADATA) as job_id:
        assert job_id == task_name
        job = job_queue.get_job(task_name)
        assert job is not None
        assert job.state == TaskStatus.RUNNING
        assert job.category == TaskCategory.BACKGROUND_METADATA
        assert "leased" in job.tags
        assert "parent_task" in job.tags
        assert job_queue.is_job_running(task_name)

    # After exit, job must be cleaned up from active jobs
    assert job_queue.get_job(task_name) is None
    assert not job_queue.is_job_running(task_name)


def test_lease_task_failure_cleanup():
    """Verify lease_task properly cleans up its tracking state even when an unhandled exception occurs."""
    task_name = "test_failing_workflow"

    with pytest.raises(RuntimeError, match="Simulated worker crash"):
        with lease_task(task_name, category=TaskCategory.CRITICAL):
            job = job_queue.get_job(task_name)
            assert job is not None
            assert job.state == TaskStatus.RUNNING
            raise RuntimeError("Simulated worker crash")

    # Verify cleanup occurred in finally block
    assert job_queue.get_job(task_name) is None
    assert not job_queue.is_job_running(task_name)


def test_cooperative_pause_and_resume():
    """Verify cooperative pause/resume signaling and preemption waiting."""
    job_name = "cooperative_enhancement_job"

    # Initially not paused
    assert not is_paused(job_name)

    # Pause job
    assert pause_job(job_name)
    assert is_paused(job_name)

    # wait_for_resume times out while paused
    resumed = wait_for_resume(job_name, poll_interval=0.01, timeout=0.05)
    assert not resumed

    # Resume job in background after 50ms
    def background_resume():
        time.sleep(0.05)
        resume_job(job_name)

    t = threading.Thread(target=background_resume)
    t.start()

    # wait_for_resume blocks until background_resume unpauses
    resumed = wait_for_resume(job_name, poll_interval=0.01, timeout=1.0)
    assert resumed
    assert not is_paused(job_name)
    t.join()


def test_musicbrainz_get_metadata_pruned_payload():
    """Verify MusicBrainz client get_metadata does not retain massive raw releases dictionary in result."""
    client = MusicBrainzClient()

    mock_mb_payload = {
        "id": "rec-12345",
        "title": "Pruned Track Title",
        "length": 210000,
        "artist-credit": [
            {"name": "Pruned Artist", "joinphrase": ""},
        ],
        "releases": [
            {
                "id": "rel-001",
                "title": "Canonical Studio Album",
                "date": "2021-05-20",
                "release-group": {
                    "id": "rg-001",
                    "primary-type": "Album",
                    "secondary-types": [],
                },
                "status": "Official",
                "media": [
                    {
                        "position": 1,
                        "tracks": [
                            {
                                "id": "tr-001",
                                "number": "3",
                                "recording": {"id": "rec-12345"},
                            }
                        ],
                    }
                ],
            }
        ],
        "isrcs": ["USXX12345678"],
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_mb_payload

    with patch.object(client.http, "get", return_value=mock_response):
        result = client.get_metadata("rec-12345")

    assert result is not None
    assert result["title"] == "Pruned Track Title"
    assert result["artist"] == "Pruned Artist"
    assert result["album"] == "Canonical Studio Album"
    assert result["track_number"] == 3
    assert result["disc_number"] == 1
    assert result["isrc"] == "USXX12345678"
    assert result["year"] == 2021

    # Invariant: Raw releases tree MUST NOT be retained in the result payload
    assert "releases" not in result


def test_enhancer_default_batch_and_lease():
    """Verify RetroactiveEnhancer default batch_size is clamped to 10 and acquires lease_task."""
    import inspect

    sig = inspect.signature(RetroactiveEnhancer.enhance_library_metadata)
    assert sig.parameters["batch_size"].default == 10

    enhancer = RetroactiveEnhancer()
    with patch.object(enhancer, "_enhance_library_metadata_loop") as mock_loop:
        enhancer.enhance_library_metadata(batch_size=10, limit=5)
        mock_loop.assert_called_once()
        call_kwargs = mock_loop.call_args[1]
        assert call_kwargs["job_id"] == "metadata_enhancement"
        assert call_kwargs["batch_size"] == 10
        assert call_kwargs["limit"] == 5
