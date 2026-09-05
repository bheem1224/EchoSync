from fastapi.testclient import TestClient
from web.api_app import create_app

app = create_app(testing=True)
client = TestClient(app)

def test_jobs_endpoint_returns_items(monkeypatch):
    from core.task_manager.task_queue import job_queue

    def noop():
        pass

    job_queue.register_job(
        name="test_job", func=noop, interval_seconds=60, enabled=True
    )

    resp = client.get("/api/v1/system/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(j["name"] == "test_job" for j in data["items"])

def test_jobs_summary_aggregates_counts(monkeypatch):
    resp = client.get("/api/v1/system/jobs/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "running_jobs" in data
    assert "queued_jobs" in data
    assert "errors" in data
    assert isinstance(data["errors"], list)
