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


def test_system_jobs_accept_kwargs(monkeypatch):
    """Verify all registered system job functions tolerate **kwargs without raising TypeError."""
    calls = []

    class FakeJobQueue:
        def register_job(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(system_jobs, "job_queue", FakeJobQueue())
    system_jobs.register_all_system_jobs()

    for call in calls:
        func = call["func"]
        # Verify function can be invoked with arbitrary kwargs without raising TypeError
        try:
            func(force_scan=True, full_refresh=True, extraneous_param="test")
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                raise AssertionError(f"Job function for '{call['name']}' failed kwargs tolerance: {e}")
        except Exception:
            # Other runtime exceptions (e.g. DB connection) are acceptable here as long as signature accepts kwargs
            pass

