from unittest.mock import MagicMock

from flask import Flask

from database.music_database import Artist, LocalMedia, Track
from database.working_database import ReviewTask


def _fake_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


def _setup_media_path(session, media_id, file_path):
    artist = Artist(name="Test Artist")
    session.add(artist)
    session.flush()

    track = Track(title="Test Track", artist_id=artist.id)
    session.add(track)
    session.flush()

    media = LocalMedia(
        media_id=media_id, track_id=track.id, file_path=file_path, file_size_bytes=1000
    )
    session.add(media)
    session.commit()


def test_get_media_file_path(monkeypatch, mock_db):
    from web.routes import metadata_review

    with mock_db.session_scope() as session:
        _setup_media_path(session, "media_123", "/data/library/artist/album/song.mp3")

    monkeypatch.setattr(metadata_review, "get_database", lambda: mock_db)

    path = metadata_review._get_media_file_path("media_123")
    assert path == "/data/library/artist/album/song.mp3"

    assert metadata_review._get_media_file_path("non_existent") is None


def test_serialize_task(monkeypatch, mock_db):
    from web.routes import metadata_review

    with mock_db.session_scope() as session:
        _setup_media_path(session, "media_123", "/data/library/artist/album/song.mp3")

    monkeypatch.setattr(metadata_review, "get_database", lambda: mock_db)

    task = ReviewTask(
        id=456,
        file_path="/data/library/artist/album/song.mp3",
        confidence_score=0.9,
        track_data={
            "title": "Song Title",
            "artist": "Artist Name",
            "album_title": "Album Title",
        },
    )

    # Mock _read_current_metadata to avoid actual file read
    monkeypatch.setattr(
        metadata_review, "_read_current_metadata", lambda t: {"title": "Existing Title"}
    )

    serialized = metadata_review._serialize_task(task)
    assert serialized["id"] == 456
    assert serialized["file_path"] == "/data/library/artist/album/song.mp3"
    assert serialized["media_id"] == "/data/library/artist/album/song.mp3"
    assert serialized["detected_metadata"]["title"] == "Song Title"
    assert serialized["current_metadata"] == {"title": "Existing Title"}


def test_approve_review_queue_item(monkeypatch, mock_db, mock_work_db, tmp_path):
    from web.routes import metadata_review

    # Setup a physical file in tmp_path to act as the original file
    original_file = tmp_path / "song.mp3"
    original_file.touch()

    # Setup mock_work_db with ReviewTask
    with mock_work_db.session_scope() as session:
        session.add(
            ReviewTask(
                id=1,
                file_path=str(original_file),
                confidence_score=0.8,
                status="pending",
                track_data={
                    "title": "Song Title",
                    "artist": "Artist Name",
                    "album_title": "Album Title",
                },
            )
        )

    # Monkeypatch databases
    monkeypatch.setattr(metadata_review, "get_database", lambda: mock_db)
    monkeypatch.setattr(metadata_review, "get_working_database", lambda: mock_work_db)

    # Mock config_manager to return tmp_path as library_dir
    def mock_config_get(key, default=None):
        if "dir" in key:
            return str(tmp_path)
        return default

    monkeypatch.setattr(metadata_review.config_manager, "get", mock_config_get)

    # Mock tag_file to do nothing
    mock_enhancer = MagicMock()
    monkeypatch.setattr(metadata_review, "get_metadata_enhancer", lambda: mock_enhancer)

    # Track one-off job execution synchronously
    executed_jobs = []

    class FakeJobQueue:
        def register_job(self, name, func, interval_seconds=None):
            self.func = func

        def execute_job_now(self, name):
            self.func()
            executed_jobs.append(name)

    fake_job_queue = FakeJobQueue()
    import core.job_queue

    monkeypatch.setattr(core.job_queue, "job_queue", fake_job_queue)

    # Call approve
    from web.routes.metadata_review import ApproveReviewQueueRequest

    res = metadata_review.approve_review_queue_item(
        1,
        ApproveReviewQueueRequest(
            metadata={"artist": "Artist", "album": "Album", "title": "New Title"}
        ),
    )
    if isinstance(res, tuple):
        response, status_code = res
    else:
        response, status_code = res, 202

    assert status_code == 202
    assert len(executed_jobs) == 1

    # Verify that:
    # 1. File was relocated to the library structure: tmp_path / Artist / Album / New Title.mp3
    expected_relocated_path = tmp_path / "Artist" / "Album" / "New Title.mp3"
    assert expected_relocated_path.exists()

    # 2. LocalMedia and Track were created in music_library.db (mock_db)
    with mock_db.session_scope() as session:
        from database import _canonicalize_path

        media = (
            session.query(LocalMedia)
            .filter(
                LocalMedia.file_path == _canonicalize_path(str(expected_relocated_path))
            )
            .first()
        )
        assert media is not None

        # 3. Track was upserted in music_library.db and bound to the updated LocalMedia row
        track = session.query(Track).filter(Track.title == "New Title").first()
        assert track is not None
        assert media.track_id == track.id

    # 4. ReviewTask was deleted from working.db (mock_work_db)
    with mock_work_db.session_scope() as session:
        task = session.query(ReviewTask).filter(ReviewTask.id == 1).first()
        assert task is None


def test_get_media_file_path_raw_path(monkeypatch, mock_db):
    from web.routes import metadata_review

    monkeypatch.setattr(metadata_review, "get_database", lambda: mock_db)

    p = "/data/downloads/Alan Walker - Paradise/PARADISE FX.wav"
    assert metadata_review._get_media_file_path(p) == p

    p2 = "C:\\data\\downloads\\song.mp3"
    assert metadata_review._get_media_file_path(p2) == p2

    p3 = "virtual://placeholder"
    assert metadata_review._get_media_file_path(p3) == p3
