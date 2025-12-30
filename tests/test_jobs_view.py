"""Tests for jobs view rendering and filtering."""

from flask import Flask


def _fake_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


def test_jobs_endpoint_returns_items(monkeypatch):
    import web.routes.jobs as jobs_route
    from core.job_queue import job_queue

    app = _fake_app()

    # Register a dummy job
    def noop():
        pass

    job_queue.register_job(name='test_job', func=noop, interval_seconds=60, enabled=True)

    with app.test_request_context('/api/jobs/'):
        resp = jobs_route.list_jobs()
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] >= 1
        assert any(j['name'] == 'test_job' for j in data['items'])


def test_jobs_summary_aggregates_counts(monkeypatch):
    import web.routes.jobs as jobs_route

    app = _fake_app()

    with app.test_request_context('/api/jobs/summary'):
        resp = jobs_route.jobs_summary()
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'running_jobs' in data
        assert 'queued_jobs' in data
        assert 'errors' in data
        assert isinstance(data['errors'], list)
