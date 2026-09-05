import time

from core.job_queue import JobQueue, ScheduledJob


def test_scheduled_job_clears_running_lock_and_disposes_working_db(monkeypatch):
    queue = JobQueue(worker_count=1)

    removed_working = {"count": 0}
    removed_music = {"count": 0}

    class FakeRegistry:
        def __init__(self, counter):
            self.counter = counter

        def remove(self):
            self.counter["count"] += 1

    monkeypatch.setattr(
        "database.working_database.working_session_registry",
        FakeRegistry(removed_working),
    )
    monkeypatch.setattr(
        "database.music_database.music_session_registry", FakeRegistry(removed_music)
    )

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
    assert job.name not in queue._jobs
    assert removed_working["count"] >= 1
    assert removed_music["count"] >= 1
