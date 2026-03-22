from core import system_jobs


def test_register_all_system_jobs_registers_expected_defaults(monkeypatch):
    calls = []

    class FakeJobQueue:
        def register_job(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(system_jobs, "job_queue", FakeJobQueue())

    system_jobs.register_all_system_jobs()

    by_name = {call["name"]: call for call in calls}

    assert "database_update" in by_name
    assert by_name["database_update"]["enabled"] is True
    assert by_name["database_update"]["interval_seconds"] == 21600

    assert "media_server_scan" in by_name
    assert by_name["media_server_scan"]["enabled"] is True
    assert by_name["media_server_scan"]["interval_seconds"] == 10800

    assert "suggestion_engine_daily_playlists" in by_name
    assert by_name["suggestion_engine_daily_playlists"]["enabled"] is True
    assert by_name["suggestion_engine_daily_playlists"]["interval_seconds"] == 86400
