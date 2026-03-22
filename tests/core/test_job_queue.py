import time

from core.job_queue import JobQueue, ScheduledJob


def test_scheduled_job_clears_running_lock_and_disposes_working_db(monkeypatch):
    queue = JobQueue(worker_count=1)

    disposed = {"count": 0}

    class FakeWorkingDatabase:
        def dispose(self):
            disposed["count"] += 1

    monkeypatch.setattr("core.job_queue.get_working_database", lambda: FakeWorkingDatabase())

    def failing_job():
        raise RuntimeError("boom")

    job = ScheduledJob(
        next_run=time.time(),
        name="failing_job",
        func=failing_job,
        interval_seconds=None,
        max_retries=0,
    )
    queue._jobs[job.name] = job

    queue._execute_job(job)

    deadline = time.time() + 2.0
    while time.time() < deadline:
        if not queue._is_running.get(job.name, False) and not job.running:
            break
        time.sleep(0.01)

    assert queue._is_running.get(job.name, False) is False
    assert job.running is False
    assert disposed["count"] == 1