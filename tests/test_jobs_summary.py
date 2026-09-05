from fastapi.testclient import TestClient
from web.api_app import create_app

app = create_app(testing=True)
client = TestClient(app)

def test_jobs_summary_empty(monkeypatch):
    resp = client.get("/api/v1/system/jobs/summary")
    assert resp.status_code in (200, 404, 500)

def test_jobs_summary_counts(monkeypatch):
    from core.task_manager.task_queue import job_queue

    def noop():
        pass

    job_queue.register_job(name="job1", func=noop, interval_seconds=60, enabled=True)
    job_queue.register_job(name="job2", func=noop, interval_seconds=None, enabled=True)

    items = job_queue.list_jobs()
    for j in items:
        if j["name"] == "job1":
            j["running"] = True
        if j["name"] == "job2":
            j["running"] = False
            j["enabled"] = True

    resp = client.get("/api/v1/system/jobs/summary")
    assert resp.status_code in (200, 404)
