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

    from core.task_manager.task_queue import job_queue

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


def test_retry_aged_review_tasks_auto_dismisses_missing_files(tmp_path):
    """Ghost review tasks whose physical files no longer exist on disk are marked ignored."""
    service = AutoImportService()
    work_db = get_working_database()

    missing_path = tmp_path / "gone_forever.flac"
    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(missing_path),
            status="pending",
            updated_at=utc_now(),
            last_checked_at=utc_now(),
            retry_count=0,
        )
        session.add(task)
        session.commit()
        task_id = task.id

    service._retry_aged_review_tasks(force_check=True)

    with work_db.session_scope() as session:
        refreshed = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        assert refreshed is not None
        assert refreshed.status == "ignored"


def test_retry_aged_review_tasks_auto_imports_high_confidence_with_dotted_setting(tmp_path, monkeypatch):
    """High-confidence tasks auto-import when metadata_enhancement.auto_import is enabled and mark approved."""
    from core.settings import config_manager

    service = AutoImportService()
    work_db = get_working_database()

    audio_file = tmp_path / "100_percent_track.flac"
    audio_file.write_bytes(b"0" * 70000)

    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(audio_file),
            status="pending",
            updated_at=utc_now(),
            last_checked_at=utc_now(),
            retry_count=0,
        )
        session.add(task)
        session.commit()
        task_id = task.id

    # Simulate dotted key storage (nested dict returns None)
    def fake_get(key, default=None):
        if key == "metadata_enhancement":
            return None
        if key == "metadata_enhancement.auto_import":
            return "true"
        if key == "metadata_enhancement.confidence_threshold":
            return 90
        return default

    monkeypatch.setattr(config_manager, "get", fake_get)

    captured_calls = []
    monkeypatch.setattr(
        service.enhancer,
        "identify_file",
        lambda p, ignore_cache=False: (
            captured_calls.append(ignore_cache)
            or {"title": "Don't You Worry Child", "artist_name": "Swedish House Mafia"},
            1.0,
        ),
    )

    imported = []
    monkeypatch.setattr(
        service,
        "finalize_import",
        lambda p, meta: imported.append((p, meta)),
    )

    service._retry_aged_review_tasks(force_check=True)

    assert captured_calls and all(captured_calls)
    assert any(p == audio_file for p, _ in imported)
    with work_db.session_scope() as session:
        refreshed = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        assert refreshed is not None
        assert refreshed.status == "approved"


def test_retry_caps_placeholder_and_mojibake_confidence_and_auto_imports_verified_signature(tmp_path, monkeypatch):
    """Ensure 'Unknown Artist' / '???' never stay at 100% confidence, while valid Stage 0/ISRC 100% tasks auto-import even without force_check."""
    from core.models.entities import EchosyncTrack
    from core.settings import config_manager

    service = AutoImportService()
    work_db = get_working_database()

    bad_unknown = tmp_path / "03 - CREED (7).flac"
    bad_unknown.write_bytes(b"0" * 70000)

    bad_mojibake = tmp_path / "04 - cjk_mojibake.mp3"
    bad_mojibake.write_bytes(b"0" * 70000)

    good_sig = tmp_path / "01 - Dont You Worry Child.flac"
    good_sig.write_bytes(b"0" * 70000)

    with work_db.session_scope() as session:
        t1 = ReviewTask(file_path=str(bad_unknown), status="pending", confidence_score=1.0, updated_at=utc_now())
        t2 = ReviewTask(file_path=str(bad_mojibake), status="pending", confidence_score=1.0, updated_at=utc_now())
        t3 = ReviewTask(file_path=str(good_sig), status="pending", confidence_score=1.0, updated_at=utc_now())
        session.add_all([t1, t2, t3])
        session.commit()
        id_unknown, id_mojibake, id_good = t1.id, t2.id, t3.id

    monkeypatch.setattr(
        config_manager,
        "get",
        lambda key, default=None: {"auto_import": True, "confidence_threshold": 90}
        if key == "metadata_enhancement"
        else default,
    )

    # identify_file returns None so engine fallback runs
    monkeypatch.setattr(service.enhancer, "identify_file", lambda p, ignore_cache=False: (None, 0.0))

    def fake_resolve(req):
        fp = str(req.file_path)
        if "CREED" in fp:
            return EchosyncTrack(
                raw_title="CREED (9)",
                title="CREED (9)",
                artist_name="Unknown Artist",
                confidence_score=1.0,
                resolution_method="signature_verified",
            )
        if "mojibake" in fp:
            return EchosyncTrack(
                raw_title="????????",
                title="????????",
                artist_name="???",
                confidence_score=1.0,
                resolution_method="signature_verified",
            )
        return EchosyncTrack(
            raw_title="Don't You Worry Child",
            title="Don't You Worry Child",
            artist_name="Swedish House Mafia",
            album_title="The Singles",
            isrc="GBAAA1200728",
            confidence_score=1.0,
            resolution_method="signature_verified",
        )

    monkeypatch.setattr(service.engine, "resolve_track", fake_resolve)

    imported_paths = []
    monkeypatch.setattr(service, "finalize_import", lambda p, meta: imported_paths.append(p))

    # Even with force_check=False, auto_import=True sweeps pending tasks with confidence_score >= threshold!
    service._retry_aged_review_tasks(force_check=False)

    assert good_sig in imported_paths
    assert bad_unknown not in imported_paths
    assert bad_mojibake not in imported_paths

    with work_db.session_scope() as session:
        r_unknown = session.query(ReviewTask).filter(ReviewTask.id == id_unknown).first()
        r_mojibake = session.query(ReviewTask).filter(ReviewTask.id == id_mojibake).first()
        r_good = session.query(ReviewTask).filter(ReviewTask.id == id_good).first()
        assert r_unknown.status == "pending"
        assert r_unknown.confidence_score == 0.0
        assert r_mojibake.status == "pending"
        assert r_mojibake.confidence_score == 0.0
        assert r_good.status == "approved"
