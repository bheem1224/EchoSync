import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from database.music_database import Artist, Base, LocalMedia, Track, close_database, get_database
from database.working_database import WorkingBase, close_working_database, get_working_database
from web.api_app import create_app


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    """Set up isolated music and working databases for web API tests."""
    close_database()
    close_working_database()

    db_path = tmp_path / "music_test.db"
    working_path = tmp_path / "working_test.db"

    test_music_db = get_database(str(db_path))
    Base.metadata.create_all(test_music_db.engine)

    test_working_db = get_working_database(str(working_path))
    WorkingBase.metadata.create_all(test_working_db.engine)

    # Point global get_database and get_working_database to test databases
    monkeypatch.setattr("database.music_database.get_database", lambda *a, **kw: test_music_db)
    monkeypatch.setattr("database.get_database", lambda *a, **kw: test_music_db)
    monkeypatch.setattr("database.working_database.get_working_database", lambda *a, **kw: test_working_db)

    # Point media_manager singletons to the test music database using monkeypatch
    import web.routes.stream as stream_route
    import web.routes.library as library_route

    monkeypatch.setattr(library_route.media_manager, "db", test_music_db)
    monkeypatch.setattr(stream_route.media_manager, "db", test_music_db)

    app = create_app(testing=True)
    with TestClient(app) as client:
        yield client, test_music_db, test_working_db, tmp_path

    close_database()
    close_working_database()


def test_stream_media_by_nanoid_success(app_env):
    """Ensure GET /api/v1/core/stream/media/{media_id} streams the audio file when media_id is valid."""
    client, music_db, _, tmp_path = app_env

    flac_file = tmp_path / "audio_edition_1.flac"
    audio_content = b"fLaC" + b"\x00" * 512
    flac_file.write_bytes(audio_content)

    with music_db.session_scope() as session:
        artist = Artist(name="Boundary Artist")
        session.add(artist)
        session.flush()

        track = Track(
            sync_id="sync_track_001",
            title="Boundary Test Track",
            artist_id=artist.id,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            media_id="M_nanoid_edition_001",
            track_id=track.id,
            file_path=str(flac_file),
            file_format="FLAC",
        )
        session.add(media)

    resp = client.get("/api/v1/core/stream/media/M_nanoid_edition_001")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/flac")
    assert resp.content == audio_content

    # Test route alias
    resp_alias = client.get("/api/v1/stream/media/M_nanoid_edition_001")
    assert resp_alias.status_code == 200
    assert resp_alias.content == audio_content


def test_stream_media_missing_returns_404(app_env):
    """GET /api/v1/core/stream/media/{media_id} returns 404 when media_id is not in database."""
    client, _, _, _ = app_env
    resp = client.get("/api/v1/core/stream/media/M_nonexistent_nanoid")
    assert resp.status_code == 404


def test_stream_media_integer_pk_rejected(app_env):
    """GET /api/v1/core/stream/media/{media_id} rejects integer primary keys with 400 Bad Request."""
    client, _, _, _ = app_env
    resp = client.get("/api/v1/core/stream/media/123")
    assert resp.status_code == 400
    assert "Integer primary keys are not allowed" in resp.text


def test_delete_media_edition_retention(app_env):
    """
    Ensure DELETE /api/v1/core/library/media/{media_id} removes only the targeted
    LocalMedia row, leaving sibling editions and the parent Track intact.
    """
    client, music_db, _, tmp_path = app_env

    file1 = tmp_path / "song_flac.flac"
    file1.write_bytes(b"flac audio")
    file2 = tmp_path / "song_mp3.mp3"
    file2.write_bytes(b"mp3 audio")

    with music_db.session_scope() as session:
        artist = Artist(name="Multi Edition Artist")
        session.add(artist)
        session.flush()

        parent_track = Track(
            sync_id="sync_multi_edition_track",
            title="Multi Edition Track",
            artist_id=artist.id,
        )
        session.add(parent_track)
        session.flush()

        media1 = LocalMedia(
            media_id="M_flac_edition_target",
            track_id=parent_track.id,
            file_path=str(file1),
            file_format="FLAC",
        )
        media2 = LocalMedia(
            media_id="M_mp3_sibling_edition",
            track_id=parent_track.id,
            file_path=str(file2),
            file_format="MP3",
        )
        session.add(media1)
        session.add(media2)

    with patch("core.io_gatekeeper.Gatekeeper.authorize_and_execute"):
        del_resp = client.delete("/api/v1/core/library/media/M_flac_edition_target")

    assert del_resp.status_code == 200
    assert del_resp.json().get("success") is True

    # Verify sibling edition and parent track retention in database
    with music_db.session_scope() as session:
        deleted_media = session.query(LocalMedia).filter(LocalMedia.media_id == "M_flac_edition_target").first()
        assert deleted_media is None, "Targeted media edition must be deleted from database"

        sibling_media = session.query(LocalMedia).filter(LocalMedia.media_id == "M_mp3_sibling_edition").first()
        assert sibling_media is not None, "Sibling media edition must remain intact"

        track = session.query(Track).filter(Track.sync_id == "sync_multi_edition_track").first()
        assert track is not None, "Parent Track must remain intact when sibling editions exist"


def test_stream_media_range_request(app_env):
    """Ensure GET /api/v1/core/stream/media/{media_id} handles HTTP Range slicing correctly."""
    client, music_db, _, tmp_path = app_env

    flac_file = tmp_path / "large_audio.flac"
    audio_content = b"fLaC" + (b"\xaa" * 2044)  # 2048 bytes
    flac_file.write_bytes(audio_content)

    with music_db.session_scope() as session:
        artist = Artist(name="Range Artist")
        session.add(artist)
        session.flush()

        track = Track(
            sync_id="sync_range_001",
            title="Range Test Track",
            artist_id=artist.id,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            media_id="M_range_edition_001",
            track_id=track.id,
            file_path=str(flac_file),
            file_format="FLAC",
        )
        session.add(media)

    # Request first 1024 bytes: 0-1023
    resp = client.get(
        "/api/v1/core/stream/media/M_range_edition_001",
        headers={"Range": "bytes=0-1023"},
    )
    assert resp.status_code == 206
    assert resp.content == audio_content[0:1024]
    assert resp.headers.get("content-range") == "bytes 0-1023/2048"


def test_delete_last_media_edition_prunes_parent_track(app_env):
    """
    Ensure DELETE /api/v1/core/library/media/{media_id} removes the LocalMedia row
    and prunes the parent Track when no other media editions remain.
    """
    client, music_db, _, tmp_path = app_env

    file1 = tmp_path / "sole_song.flac"
    file1.write_bytes(b"sole flac audio")

    with music_db.session_scope() as session:
        artist = Artist(name="Sole Edition Artist")
        session.add(artist)
        session.flush()

        parent_track = Track(
            sync_id="sync_sole_edition_track",
            title="Sole Edition Track",
            artist_id=artist.id,
        )
        session.add(parent_track)
        session.flush()

        media1 = LocalMedia(
            media_id="M_sole_flac_edition",
            track_id=parent_track.id,
            file_path=str(file1),
            file_format="FLAC",
        )
        session.add(media1)

    with patch("core.io_gatekeeper.Gatekeeper.authorize_and_execute"):
        del_resp = client.delete("/api/v1/core/library/media/M_sole_flac_edition")

    assert del_resp.status_code == 200
    assert del_resp.json().get("success") is True

    with music_db.session_scope() as session:
        deleted_media = session.query(LocalMedia).filter(LocalMedia.media_id == "M_sole_flac_edition").first()
        assert deleted_media is None, "Targeted media edition must be deleted from database"

        track = session.query(Track).filter(Track.sync_id == "sync_sole_edition_track").first()
        assert track is None, "Parent Track must be pruned when no media files remain"


def test_integer_primary_key_rejections(app_env):
    """
    Enforce contract: all endpoints expecting NanoIDs (sync_id or media_id)
    MUST reject integer primary keys (.isdigit()) with HTTP 400.
    """
    client, _, _, _ = app_env

    # 1. Stream media by ID
    resp = client.get("/api/v1/core/stream/media/123")
    assert resp.status_code == 400, f"Expected 400 for integer media_id in stream, got {resp.status_code}"
    assert "Integer primary keys are not allowed" in resp.text

    # 2. Delete media by ID
    resp = client.delete("/api/v1/core/library/media/123")
    assert resp.status_code == 400, f"Expected 400 for integer media_id in delete media, got {resp.status_code}"
    assert "Integer primary keys are not allowed" in resp.text

    # 3. Delete track by ID
    resp = client.delete("/api/v1/core/library/123")
    assert resp.status_code == 400, f"Expected 400 for integer sync_id in delete track, got {resp.status_code}"
    assert "Integer primary keys are not allowed" in resp.text

    # 4. Stream track by ID
    resp = client.get("/api/v1/core/library/stream/123")
    assert resp.status_code == 400, f"Expected 400 for integer sync_id in library stream, got {resp.status_code}"
    assert "Integer primary keys are not allowed" in resp.text

    # 5. Core media telemetry by media_id
    resp = client.get("/api/v1/core/media/123")
    assert resp.status_code == 400, f"Expected 400 for integer media_id in core media, got {resp.status_code}"
    assert "Integer primary keys are not allowed" in resp.text

    # 6. Core track by sync_id
    resp = client.get("/api/v1/core/tracks/123")
    assert resp.status_code == 400, f"Expected 400 for integer sync_id in core tracks, got {resp.status_code}"
    assert "Integer primary keys are not allowed" in resp.text

    # 7. Core track PATCH by sync_id
    resp = client.patch("/api/v1/core/tracks/123", json={"title": "New Title"})
    assert resp.status_code == 400, f"Expected 400 for integer sync_id in PATCH tracks, got {resp.status_code}"
    assert "Integer primary keys are not allowed" in resp.text

    # 8. Metadata review task creation with integer media_id
    resp = client.post("/api/v1/core/metadata_review", json={"media_id": "123"})
    assert resp.status_code == 400, f"Expected 400 for integer media_id in metadata_review, got {resp.status_code}"
    assert "Integer primary keys are not allowed" in resp.text

    # 9. Review tasks route alias with integer media_id
    resp = client.post("/api/v1/review/tasks", json={"media_id": "123"})
    assert resp.status_code == 400, f"Expected 400 for integer media_id in review tasks alias, got {resp.status_code}"
    assert "Integer primary keys are not allowed" in resp.text

    # 10. Library media edition stream route with integer media_id
    resp = client.get("/api/v1/core/library/media/123/stream")
    assert resp.status_code == 400, f"Expected 400 for integer media_id in library edition stream, got {resp.status_code}"
    assert "Integer primary keys are not allowed" in resp.text

    # 11. Whitespace padded integer rejection
    resp = client.get("/api/v1/core/stream/media/%20123%20")
    assert resp.status_code == 400, f"Expected 400 for whitespace-padded integer media_id, got {resp.status_code}"


def test_metadata_review_create_task_with_nanoid(app_env):
    """Ensure POST /api/v1/core/metadata_review properly indexes a ReviewTask by string NanoID."""
    client, music_db, working_db, tmp_path = app_env

    audio_file = tmp_path / "review_track.flac"
    audio_file.write_bytes(b"dummy audio for review")

    with music_db.session_scope() as session:
        artist = Artist(name="Review Artist")
        session.add(artist)
        session.flush()

        track = Track(
            sync_id="sync_review_test",
            title="Before Review Title",
            artist_id=artist.id,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            media_id="M_review_nanoid_456",
            track_id=track.id,
            file_path=str(audio_file),
            file_format="FLAC",
        )
        session.add(media)

    resp = client.post("/api/v1/core/metadata_review", json={"media_id": "M_review_nanoid_456"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["task"]["media_id"] == "M_review_nanoid_456"
    assert data["task"]["file_path"] == str(audio_file)

    task_id = data["id"]

    # Test update_review_queue_item rejects integer media_id
    patch_int = client.patch(f"/api/v1/core/metadata_review/{task_id}/save", json={"media_id": "999"})
    assert patch_int.status_code == 400

    # Test update_review_queue_item accepts new string NanoID media_id
    patch_ok = client.patch(
        f"/api/v1/core/metadata_review/{task_id}/save",
        json={"media_id": "M_updated_nanoid_789"},
    )
    assert patch_ok.status_code == 200


def test_metadata_review_serialized_media_id_never_leaks_file_path():
    """Ensure ReviewTask with no media_id serializes media_id as None, never leaking file_path."""
    from database.working_database import ReviewTask
    from web.routes.metadata_review import _serialize_task

    task = ReviewTask(
        id=101,
        file_path="/var/music/albums/song.mp3",
        status="pending",
        track_data={"title": "No Media ID Track"},
    )
    serialized = _serialize_task(task)
    assert serialized["media_id"] is None
    assert serialized["file_path"] == "/var/music/albums/song.mp3"

