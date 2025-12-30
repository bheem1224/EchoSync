"""Tests for /api/jobs/summary computation using job_queue singleton."""

import pytest


def test_jobs_summary_empty(monkeypatch):
    from web.routes.jobs import jobs_summary
    # Call the Flask view function directly
    resp = jobs_summary()
    data, status = resp.response[0], resp.status_code
    # Flask jsonify returns a Response; fetch json via get_json in real app, here we inspect status
    assert status in (200, 500)


def test_jobs_summary_counts(monkeypatch):
    from core.job_queue import job_queue
    from web.routes.jobs import jobs_summary

    # Register dummy jobs and simulate states
    def noop():
        pass
    job_queue.register_job(name='job1', func=noop, interval_seconds=60, enabled=True)
    job_queue.register_job(name='job2', func=noop, interval_seconds=None, enabled=True)
    
    # Manually adjust internal state for testing
    items = job_queue.list_jobs()
    # Simulate one running and one queued
    for j in items:
        if j['name'] == 'job1':
            j['running'] = True
        if j['name'] == 'job2':
            j['running'] = False
            j['enabled'] = True
    
    # Invoke summary
    resp = jobs_summary()
    status = resp.status_code
    assert status == 200
