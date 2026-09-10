from unittest.mock import MagicMock

from flask import Flask


def _fake_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


def test_review_queue_includes_current_metadata(monkeypatch, mock_work_db, tmp_path):
    from database.working_database import ReviewTask
    from web.routes import metadata_review

    file_path = tmp_path / "queue-track.wav"
    file_path.write_bytes(b"not-a-real-wave-file")

    with mock_work_db.session_scope() as session:
        session.add(
            ReviewTask(
                file_path=str(file_path),
                status="pending",
                detected_metadata={
                    "title": "Matched Title",
                    "artist": "Matched Artist",
                },
                confidence_score=0.95,
            )
        )

    enhancer = MagicMock()
    enhancer.read_tags.return_value = {
        "title": "Current Title",
        "artist": "Current Artist",
        "album": "Current Album",
    }

    def mock_get(key, default=None):
        if "library_dir" in key or "download_dir" in key:
            return str(tmp_path)
        return default

    monkeypatch.setattr(metadata_review.config_manager, "get", mock_get)
    monkeypatch.setattr(metadata_review, "get_working_database", lambda: mock_work_db)
    monkeypatch.setattr(metadata_review, "get_metadata_enhancer", lambda: enhancer)

    payload = metadata_review.get_review_queue()
    assert isinstance(payload, dict)
    assert len(payload["tasks"]) == 1


def test_acoustid_lookup_returns_match_or_fails_fast(
    monkeypatch, mock_work_db, tmp_path
):
    import pytest
    from fastapi import HTTPException

    from core.metadata.schemas import ResolutionResult
    from database.working_database import ReviewTask
    from web.routes import metadata_review

    file_path = tmp_path / "scan-me.flac"
    file_path.write_bytes(b"fake-audio-data")

    with mock_work_db.session_scope() as session:
        task_rec = ReviewTask(
            file_path=str(file_path),
            status="pending",
            detected_metadata={"title": "Known Song"},
            confidence_score=0.1,
        )
        session.add(task_rec)
        session.flush()
        task_id = task_rec.id

    def mock_get(key, default=None):
        if "library_dir" in key or "download_dir" in key:
            return str(tmp_path)
        return default

    monkeypatch.setattr(metadata_review.config_manager, "get", mock_get)
    monkeypatch.setattr(metadata_review, "get_working_database", lambda: mock_work_db)

    # Test 1: Successful AcoustID match
    class MockEngineSuccess:
        def resolve_track(self, req):
            return ResolutionResult(
                media_id=req.media_id,
                confidence_score=0.95,
                resolution_method="acoustid",
                acoustid_id="9b6f42f0-demo-acoustid",
                musicbrainz_track_id="mb-track-123",
                title="Known Song",
                artist="Known Artist",
                chromaprint="fake-fingerprint",
                duration_ms=180000,
            )

    monkeypatch.setattr(
        "core.metadata.engine.MetadataResolutionEngine", MockEngineSuccess
    )

    payload = metadata_review.lookup_review_queue_item_acoustid(task_id)
    detected = payload["task"]["detected_metadata"]
    assert detected["acoustid_id"] == "9b6f42f0-demo-acoustid"
    assert detected["musicbrainz_id"] == "mb-track-123"
    assert detected["title"] == "Known Song"
    assert payload["resolution_result"]["musicbrainz_track_id"] == "mb-track-123"

    # Test 2: Fail-fast when confidence is 0.0 or resolution_method is not acoustid
    class MockEngineFail:
        def resolve_track(self, req):
            return ResolutionResult(
                media_id=req.media_id,
                title="Unverified Guess",
                artist="Unknown Artist",
                confidence_score=0.0,
                resolution_method="none",
            )

    monkeypatch.setattr(
        "core.metadata.engine.MetadataResolutionEngine", MockEngineFail
    )

    with pytest.raises(HTTPException) as exc_info:
        metadata_review.lookup_review_queue_item_acoustid(task_id)
    assert exc_info.value.status_code == 404
    assert "AcoustID could not verify a matching track" in exc_info.value.detail


def test_build_native_tag_payload_version_separation():
    from services.metadata_enhancer import build_native_tag_payload

    # Test 1: Single with version tag not in title
    track_1 = {
        "title": "Don't You Worry Child",
        "artist": "Swedish House Mafia",
        "album": "Until Now",
        "version": "Radio Edit",
        "release_year": 2012,
        "isrc": "SEUM71200101",
        "mbid": "mbid-1234",
    }
    payload_1 = build_native_tag_payload(track_1)
    assert payload_1["title"] == "Don't You Worry Child (Radio Edit)"
    assert payload_1["sort_title"] == "Don't You Worry Child"
    assert payload_1["subtitle"] == "Radio Edit"
    assert payload_1["version"] == "Radio Edit"
    assert payload_1["artist"] == "Swedish House Mafia"
    assert payload_1["isrc"] == "SEUM71200101"
    assert payload_1["musicbrainz_trackid"] == "mbid-1234"

    # Test 2: Title already containing version
    track_2 = {
        "title": "Levels (Radio Edit)",
        "artist": "Avicii",
        "version": "Radio Edit",
    }
    payload_2 = build_native_tag_payload(track_2)
    assert payload_2["title"] == "Levels (Radio Edit)"
    assert payload_2["sort_title"] == "Levels (Radio Edit)"
    assert payload_2["subtitle"] == "Radio Edit"


def test_reject_and_delete_review_queue_item(monkeypatch, mock_work_db, tmp_path):
    from database.working_database import ReviewTask
    from web.routes import metadata_review

    file_path = tmp_path / "reject-me.flac"
    file_path.write_bytes(b"dummy-flac-content")
    assert file_path.exists()

    with mock_work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(file_path),
            status="pending",
            detected_metadata={"title": "Reject Me"},
            confidence_score=0.1,
        )
        session.add(task)
        session.commit()
        task_id = task.id

    def mock_get(key, default=None):
        if "library_dir" in key or "download_dir" in key or "poor_metadata" in key:
            return str(tmp_path)
        return default

    monkeypatch.setattr(metadata_review.config_manager, "get", mock_get)
    monkeypatch.setattr(metadata_review, "get_working_database", lambda: mock_work_db)

    events_published = []
    from core.event_bus import event_bus

    monkeypatch.setattr(
        event_bus,
        "publish",
        lambda *args, **kwargs: events_published.append((args, kwargs)),
    )

    # Call endpoint
    res = metadata_review.reject_and_delete_review_queue_item(task_id)

    assert res["success"] is True
    assert res["status"] == "rejected"
    # Physical file should be unlinked
    assert not file_path.exists()

    # DB status should be rejected
    with mock_work_db.session_scope() as session:
        refreshed = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        assert refreshed.status == "rejected"

    # Event should be published
    assert any("REVIEW_TASK_REJECTED" in str(e) for e in events_published)
