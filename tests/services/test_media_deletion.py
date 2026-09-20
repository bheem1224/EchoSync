import uuid

import pytest
from fastapi.testclient import TestClient

from database.music_database import Artist, LocalMedia, Track, get_database
from services.media_manager import MediaManagerService
from web.api_app import create_app


@pytest.fixture(autouse=True)
def configure_library_dir(tmp_path, monkeypatch):
    """Ensure library_dir points to tmp_path so safety check passes for test files."""
    from core.settings import config_manager

    orig_get = config_manager.get

    def mock_get(key, default=None):
        if key in ("storage.library_dir", "library_dir"):
            return str(tmp_path)
        return orig_get(key, default)

    monkeypatch.setattr(config_manager, "get", mock_get)


def test_delete_media_file_preserves_sibling(tmp_path):
    """Deleting one edition preserves sibling editions and the parent track."""
    db = get_database()
    service = MediaManagerService()
    uid = uuid.uuid4().hex[:8]

    file1 = tmp_path / f"song_{uid}_1.flac"
    file2 = tmp_path / f"song_{uid}_2.mp3"
    file1.write_text("dummy audio 1")
    file2.write_text("dummy audio 2")

    with db.session_scope() as session:
        artist = Artist(name=f"Artist {uid}", normalized_name=f"artist {uid}")
        session.add(artist)
        session.flush()

        track = Track(
            title=f"Song {uid}",
            artist_id=artist.id,
            duration=180000,
            sync_id=f"sync_{uid}",
        )
        session.add(track)
        session.flush()

        m1 = LocalMedia(
            track_id=track.id,
            media_id=f"m1_{uid}",
            file_path=str(file1),
            file_format="flac",
            bitrate=1411,
        )
        m2 = LocalMedia(
            track_id=track.id,
            media_id=f"m2_{uid}",
            file_path=str(file2),
            file_format="mp3",
            bitrate=320,
        )
        session.add_all([m1, m2])
        session.flush()
        track_id = track.id
        media_id_1 = m1.media_id
        media_id_2 = m2.media_id

    # Delete first media file
    success = service.delete_media_file(media_id_1, delete_physical=True)
    assert success is True
    assert not file1.exists()
    assert file2.exists()

    with db.session_scope() as session:
        t = session.query(Track).filter(Track.id == track_id).first()
        assert t is not None
        assert len(t.media_files) == 1
        assert t.media_files[0].media_id == media_id_2


def test_delete_last_media_file_prunes_parent_track(tmp_path):
    """Deleting the last remaining edition deletes the media and prunes the parent track."""
    db = get_database()
    service = MediaManagerService()
    uid = uuid.uuid4().hex[:8]

    file_sole = tmp_path / f"sole_{uid}.flac"
    file_sole.write_text("dummy sole audio")

    with db.session_scope() as session:
        artist = Artist(name=f"Sole Artist {uid}", normalized_name=f"sole artist {uid}")
        session.add(artist)
        session.flush()

        track = Track(
            title=f"Sole Track {uid}",
            artist_id=artist.id,
            duration=200000,
            sync_id=f"sync_sole_{uid}",
        )
        session.add(track)
        session.flush()

        m = LocalMedia(
            track_id=track.id,
            media_id=f"sm_{uid}",
            file_path=str(file_sole),
            file_format="flac",
        )
        session.add(m)
        session.flush()
        track_id = track.id
        media_id = m.media_id

    success = service.delete_media_file(media_id, delete_physical=True)
    assert success is True
    assert not file_sole.exists()

    with db.session_scope() as session:
        t = session.query(Track).filter(Track.id == track_id).first()
        assert t is None
        remaining_media = session.query(LocalMedia).filter(LocalMedia.media_id == media_id).first()
        assert remaining_media is None


def test_delete_track_cascades_all_media(tmp_path):
    """Calling delete_track deletes the track and all linked physical media."""
    db = get_database()
    service = MediaManagerService()
    uid = uuid.uuid4().hex[:8]

    file_a = tmp_path / f"track_{uid}_a.flac"
    file_b = tmp_path / f"track_{uid}_b.mp3"
    file_a.write_text("audio a")
    file_b.write_text("audio b")

    with db.session_scope() as session:
        artist = Artist(name=f"Cascade Artist {uid}", normalized_name=f"cascade artist {uid}")
        session.add(artist)
        session.flush()

        track = Track(
            title=f"Cascade Track {uid}",
            artist_id=artist.id,
            duration=150000,
            sync_id=f"sync_casc_{uid}",
        )
        session.add(track)
        session.flush()

        m1 = LocalMedia(
            track_id=track.id,
            media_id=f"cm1_{uid}",
            file_path=str(file_a),
        )
        m2 = LocalMedia(
            track_id=track.id,
            media_id=f"cm2_{uid}",
            file_path=str(file_b),
        )
        session.add_all([m1, m2])
        session.flush()
        track_id = track.id

    success = service.delete_track(track_id, delete_physical=True)
    assert success is True
    assert not file_a.exists()
    assert not file_b.exists()

    with db.session_scope() as session:
        t = session.query(Track).filter(Track.id == track_id).first()
        assert t is None
        assert session.query(LocalMedia).filter(LocalMedia.track_id == track_id).count() == 0


def test_delete_nonexistent_returns_false():
    """Attempting to delete a nonexistent track or media returns False gracefully."""
    service = MediaManagerService()
    assert service.delete_track(999999999) is False
    assert service.delete_media_file("nonexistent_nanoid") is False


def test_delete_missing_physical_file_does_not_crash(tmp_path):
    """Missing physical files are handled without FileNotFoundError."""
    db = get_database()
    service = MediaManagerService()
    uid = uuid.uuid4().hex[:8]

    missing_path = tmp_path / f"nonexistent_{uid}.flac"

    with db.session_scope() as session:
        artist = Artist(name=f"Missing Artist {uid}", normalized_name=f"missing artist {uid}")
        session.add(artist)
        session.flush()

        track = Track(
            title=f"Missing Track {uid}",
            artist_id=artist.id,
            duration=120000,
            sync_id=f"sync_miss_{uid}",
        )
        session.add(track)
        session.flush()

        m = LocalMedia(
            track_id=track.id,
            media_id=f"mm_{uid}",
            file_path=str(missing_path),
        )
        session.add(m)
        session.flush()
        track_id = track.id
        media_id = m.media_id

    # Should succeed at DB deletion without crashing on nonexistent physical file
    success = service.delete_media_file(media_id, delete_physical=True)
    assert success is True

    with db.session_scope() as session:
        assert session.query(LocalMedia).filter(LocalMedia.media_id == media_id).first() is None
        assert session.query(Track).filter(Track.id == track_id).first() is None


def test_api_endpoints_delete_media_and_track(tmp_path):
    """Test FastAPI DELETE /api/v1/core/library/media/{media_id} and DELETE /api/v1/core/library/{track_id}."""
    app = create_app(testing=True)
    client = TestClient(app)
    db = get_database()
    uid = uuid.uuid4().hex[:8]

    with db.session_scope() as session:
        artist = Artist(name=f"API Artist {uid}", normalized_name=f"api artist {uid}")
        session.add(artist)
        session.flush()

        track = Track(
            title=f"API Delete Track {uid}",
            artist_id=artist.id,
            duration=140000,
            sync_id=f"sync_api_{uid}",
        )
        session.add(track)
        session.flush()

        m1 = LocalMedia(
            track_id=track.id,
            media_id=f"ap1_{uid}",
            file_path=f"virtual://api_test_1_{uid}.flac",
        )
        m2 = LocalMedia(
            track_id=track.id,
            media_id=f"ap2_{uid}",
            file_path=f"virtual://api_test_2_{uid}.mp3",
        )
        session.add_all([m1, m2])
        session.flush()
        track_id = track.id
        media_id_1 = m1.media_id
        media_id_2 = m2.media_id

    # 1. Delete single media edition via API
    res = client.delete(f"/api/v1/core/library/media/{media_id_1}")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True

    # Check that parent track still exists and has 1 media file
    with db.session_scope() as session:
        t = session.query(Track).filter(Track.id == track_id).first()
        assert t is not None
        assert len(t.media_files) == 1
        assert t.media_files[0].media_id == media_id_2

    # 2. Delete track via API
    res = client.delete(f"/api/v1/core/library/{track_id}")
    assert res.status_code == 200
    assert res.json()["success"] is True

    with db.session_scope() as session:
        assert session.query(Track).filter(Track.id == track_id).first() is None

    # 3. Subsequent delete calls should return 404
    res_404_track = client.delete(f"/api/v1/core/library/{track_id}")
    assert res_404_track.status_code == 404

    res_404_media = client.delete(f"/api/v1/core/library/media/{media_id_1}")
    assert res_404_media.status_code == 404
