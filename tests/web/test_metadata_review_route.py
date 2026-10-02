import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from core.db.echo_sync_track import EchosyncTrack
from database.working_database import ReviewTask, get_working_database
from web.api_app import create_app


@pytest.fixture
def client():
    app = create_app(testing=True)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_task(tmp_path):
    """Create a temporary audio file and a pending ReviewTask in working.db."""
    test_file = tmp_path / "test_track.flac"
    test_file.write_bytes(b"dummy audio content")

    work_db = get_working_database()
    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(test_file),
            status="pending",
            confidence_score=0.45,
            track_data={
                "action": "RESOLVE_METADATA_CONFLICT",
                "title": "Old Title",
                "artist": "Old Artist",
                "album": "Old Album",
            },
        )
        session.add(task)
        session.flush()
        task_id = task.id

    yield task_id, test_file

    # Cleanup
    with work_db.session_scope() as session:
        t = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        if t:
            session.delete(t)


def test_simulate_pipeline_success_acoustid(client, sample_task):
    task_id, test_file = sample_task

    mock_track = EchosyncTrack(
        raw_title="Just Like a Pill",
        artist_name="P!nk",
        album_title="M!ssundaztood",
        release_year=2001,
        musicbrainz_id="b7145749-0f04-4c47-aa72-8d76db86f5c5",
        isrc="USAR10100806",
        confidence_score=0.95,
        resolution_method="acoustid",
        diagnostics=[
            {
                "stage": "Stage 3: AcoustID",
                "status": "hit",
                "message": "AcoustID matched recording 'Just Like a Pill'",
                "candidates": [
                    {
                        "mbid": "b7145749-0f04-4c47-aa72-8d76db86f5c5",
                        "title": "Just Like a Pill",
                        "artist": "P!nk",
                        "status": "WINNER",
                        "total_score": 92.5,
                    },
                    {
                        "mbid": "c7145749-0f04-4c47-aa72-8d76db86f5c6",
                        "title": "Just Like a Pill (Cover)",
                        "artist": "Jun Sung Ahn",
                        "status": "DROPPED_ARTIST_FILTER",
                    },
                ],
            }
        ],
    )

    with patch(
        "web.routes.metadata_review._resolve_task_file",
        return_value=test_file,
    ), patch(
        "core.metadata.engine.MetadataResolutionEngine.resolve_track",
        return_value=mock_track,
    ):
        resp = client.post(f"/api/v1/core/metadata_review/{task_id}/simulate-pipeline")
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "success"
        assert data["winning_stage"] == "Stage 3: AcoustID"
        assert data["resolved_metadata"]["title"] == "Just Like a Pill"
        assert data["resolved_metadata"]["artist"] == "P!nk"
        assert data["resolved_metadata"]["album"] == "M!ssundaztood"
        assert data["resolved_metadata"]["musicbrainz_id"] == "b7145749-0f04-4c47-aa72-8d76db86f5c5"
        assert len(data["diagnostics"]) == 1
        assert data["diagnostics"][0]["stage"] == "Stage 3: AcoustID"
        assert len(data["diagnostics"][0]["candidates"]) == 2


def test_simulate_pipeline_review_tasks_alias(client, sample_task):
    task_id, test_file = sample_task

    mock_track = EchosyncTrack(
        raw_title="Just Like a Pill",
        artist_name="P!nk",
        album_title="M!ssundaztood",
        resolution_method="acoustid",
        diagnostics=[],
    )

    with patch(
        "web.routes.metadata_review._resolve_task_file",
        return_value=test_file,
    ), patch(
        "core.metadata.engine.MetadataResolutionEngine.resolve_track",
        return_value=mock_track,
    ):
        resp = client.post(f"/api/v1/review/tasks/{task_id}/simulate-pipeline")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["winning_stage"] == "Stage 3: AcoustID"


def test_simulate_pipeline_text_waterfall_fallback(client, sample_task):
    task_id, test_file = sample_task

    mock_track = EchosyncTrack(
        raw_title="Sober",
        artist_name="P!nk",
        album_title="Funhouse",
        release_year=2008,
        resolution_method="text_waterfall",
        diagnostics=[
            {"stage": "Stage 3: AcoustID", "status": "miss", "message": "No match"},
            {"stage": "Stage 5: Text Waterfall", "status": "hit", "message": "Matched text query"},
        ],
    )

    with patch(
        "web.routes.metadata_review._resolve_task_file",
        return_value=test_file,
    ), patch(
        "core.metadata.engine.MetadataResolutionEngine.resolve_track",
        return_value=mock_track,
    ):
        resp = client.post(f"/api/v1/core/metadata_review/{task_id}/simulate-pipeline")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["winning_stage"] == "Stage 5: Text Waterfall"
        assert data["resolved_metadata"]["title"] == "Sober"
        assert len(data["diagnostics"]) == 2


def test_simulate_pipeline_task_not_found(client):
    resp = client.post("/api/v1/core/metadata_review/999999/simulate-pipeline")
    assert resp.status_code == 404
    assert "Task not found" in resp.json()["detail"]


def test_simulate_pipeline_file_not_found(client):
    work_db = get_working_database()
    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path="/definitely/nonexistent/music/ghost_track.flac",
            status="pending",
            track_data={"action": "RESOLVE_METADATA_CONFLICT"},
        )
        session.add(task)
        session.flush()
        ghost_task_id = task.id

    try:
        resp = client.post(f"/api/v1/core/metadata_review/{ghost_task_id}/simulate-pipeline")
        assert resp.status_code == 404
        assert "not found on disk" in resp.json()["detail"]
    finally:
        with work_db.session_scope() as session:
            t = session.query(ReviewTask).filter(ReviewTask.id == ghost_task_id).first()
            if t:
                session.delete(t)


def test_simulate_pipeline_readonly_contract(client, sample_task):
    task_id, test_file = sample_task

    mock_track = EchosyncTrack(
        raw_title="Simulated Winner",
        artist_name="Simulated Artist",
        album_title="Simulated Album",
        resolution_method="acoustid",
        diagnostics=[],
    )

    with patch(
        "web.routes.metadata_review._resolve_task_file",
        return_value=test_file,
    ), patch(
        "core.metadata.engine.MetadataResolutionEngine.resolve_track",
        return_value=mock_track,
    ):
        resp = client.post(f"/api/v1/core/metadata_review/{task_id}/simulate-pipeline")
        assert resp.status_code == 200

    # Verify task in working_db was NOT mutated or approved
    work_db = get_working_database()
    with work_db.session_scope() as session:
        task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        assert task is not None
        assert task.status == "pending"
        # track_data should still be original
        assert task.track_data.get("title") == "Old Title"


def test_echosync_track_resolution_stage_property():
    track = EchosyncTrack(resolution_method="acoustid")
    assert track.resolution_stage == "Stage 3: AcoustID"

    track.resolution_method = "text_waterfall"
    assert track.resolution_stage == "Stage 5: Text Waterfall"

    track.resolution_method = "isrc"
    assert track.resolution_stage == "Stage 4: ISRC"

    track.resolution_method = "local_cache"
    assert track.resolution_stage == "Stage 2: Local Cache"

    track.resolution_method = "embedded_mbid"
    assert track.resolution_stage == "Fast-Path: Embedded MBID"

    track.resolution_method = "signature_verified"
    assert track.resolution_stage == "Stage 0: Signature Verified"
