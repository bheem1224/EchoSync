"""Unit tests for retry_aged_review_tasks job and force_check bypass option."""

from datetime import timedelta

from fastapi.testclient import TestClient

from database.working_database import ReviewTask, get_working_database
from services.auto_importer import AutoImportService
from time_utils import utc_now
from web.api_app import create_app
from web.schemas.job import JobRunRequest


def test_job_run_request_schema_force_check():
    """Verify JobRunRequest correctly parses force_check."""
    req = JobRunRequest(name="retry_aged_review_tasks", force_check=True)
    assert req.force_check is True

    req2 = JobRunRequest(name="retry_aged_review_tasks", params={"force_check": True})
    assert req2.params["force_check"] is True


def test_retry_aged_review_tasks_force_check_bypasses_age(tmp_path, monkeypatch):
    """Verify force_check=True re-evaluates review tasks updated < 7 days ago."""
    service = AutoImportService()
    work_db = get_working_database()

    recent_file = tmp_path / "recent.flac"
    recent_file.write_bytes(b"0" * 70000)

    aged_file = tmp_path / "aged.flac"
    aged_file.write_bytes(b"0" * 70000)

    two_days_ago = utc_now() - timedelta(days=2)
    eight_days_ago = utc_now() - timedelta(days=8)

    with work_db.session_scope() as session:
        t_recent = ReviewTask(
            file_path=str(recent_file),
            status="pending",
            updated_at=two_days_ago,
            last_checked_at=two_days_ago,
            retry_count=0,
        )
        t_aged = ReviewTask(
            file_path=str(aged_file),
            status="pending",
            updated_at=eight_days_ago,
            last_checked_at=eight_days_ago,
            retry_count=0,
        )
        session.add_all([t_recent, t_aged])
        session.commit()
        recent_id = t_recent.id
        aged_id = t_aged.id

    # Mock enhancer
    monkeypatch.setattr(
        service.enhancer,
        "identify_file",
        lambda p: ({"title": f"Retried {p.name}", "artist": "Retried Artist"}, 0.95),
    )

    # 1. Standard run (force_check=False) -> only aged task is processed
    service._retry_aged_review_tasks(force_check=False)

    with work_db.session_scope() as session:
        recent_task = session.query(ReviewTask).filter(ReviewTask.id == recent_id).first()
        aged_task = session.query(ReviewTask).filter(ReviewTask.id == aged_id).first()
        assert recent_task.retry_count == 0  # skipped
        assert aged_task.retry_count == 1   # processed

    # 2. Force run (force_check=True) -> recent task is now processed
    service._retry_aged_review_tasks(force_check=True)

    with work_db.session_scope() as session:
        recent_task = session.query(ReviewTask).filter(ReviewTask.id == recent_id).first()
        aged_task = session.query(ReviewTask).filter(ReviewTask.id == aged_id).first()
        assert recent_task.retry_count == 1  # processed on force run
        assert aged_task.retry_count == 2    # processed again
        assert recent_task.detected_metadata["title"] == "Retried recent.flac"


def test_jobs_route_force_check_parameter_propagation(monkeypatch):
    """Verify web/routes/jobs.py extracts force_check and forwards it to execute_job_now."""
    app = create_app()
    client = TestClient(app)

    captured_params = {}

    def mock_execute(job_name, params=None):
        captured_params["job_name"] = job_name
        captured_params["params"] = params or {}
        return True

    from core.job_queue import job_queue

    monkeypatch.setattr(job_queue, "execute_job_now", mock_execute)
    monkeypatch.setattr(
        "web.routes.jobs.jq_list_jobs",
        lambda: [{"name": "retry_aged_review_tasks", "running": False, "enabled": True}],
    )

    # Test top-level payload force_check
    res = client.post(
        "/api/v1/system/jobs/run",
        json={"name": "retry_aged_review_tasks", "force_check": True},
    )
    assert res.status_code == 200
    assert captured_params["params"].get("force_check") is True

    # Test nested params payload force_check
    res = client.post(
        "/api/v1/system/jobs/run",
        json={"name": "retry_aged_review_tasks", "params": {"force_check": True}},
    )
    assert res.status_code == 200
    assert captured_params["params"].get("force_check") is True

    # Test query param force_check
    res = client.post(
        "/api/v1/system/jobs/run?job_name=retry_aged_review_tasks&force_check=true",
        json={},
    )
    assert res.status_code == 200
    assert captured_params["params"].get("force_check") is True
