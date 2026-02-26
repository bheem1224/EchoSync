"""Tests for the download manager status job registration."""

from core.job_queue import job_queue


def test_register_download_manager_job_default_interval(monkeypatch):
    # ensure a clean queue
    job_queue._jobs.clear()
    job_queue._heap.clear()

    from services.download_manager import register_download_manager_job

    # call without arguments (should use default six hours)
    register_download_manager_job()
    jobs = job_queue.list_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    assert job['name'] == 'download_manager_status'
    assert job['interval_seconds'] == 6 * 3600
    assert job['enabled'] is False

    # registering again with a custom value should override
    register_download_manager_job(interval_seconds=123)
    jobs = job_queue.list_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    assert job['interval_seconds'] == 123


def test_register_download_manager_job_custom(monkeypatch):
    job_queue._jobs.clear()
    job_queue._heap.clear()

    from services.download_manager import register_download_manager_job

    register_download_manager_job(interval_seconds=0)  # zero is technically allowed
    jobs = job_queue.list_jobs()
    assert jobs[0]['interval_seconds'] == 0
    assert jobs[0]['enabled'] is False


def test_register_respects_config(monkeypatch):
    """If a status_interval_seconds value exists in the config it should be used."""
    job_queue._jobs.clear()
    job_queue._heap.clear()

    from services.download_manager import register_download_manager_job
    from core.settings import config_manager

    # pretend the user set a custom interval in configuration
    config_manager.config_data.setdefault('download', {})['status_interval_seconds'] = 999

    register_download_manager_job()
    jobs = job_queue.list_jobs()
    assert jobs[0]['interval_seconds'] == 999
    assert jobs[0]['enabled'] is False
