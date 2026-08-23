import pytest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch
from database.music_database import get_database, Track, Artist, Album, LocalMedia
from database.working_database import get_working_database, ReviewTask
from web.routes.manager import fetch_metadata

def test_fetch_metadata_creates_review_task_for_library_track(tmp_path):
    # Setup real test audio file on disk
    file_path = tmp_path / "test_track.mp3"
    file_path.write_bytes(b"dummy mp3 data")

    # Setup database records
    db = get_database()
    with db.session_scope() as session:
        artist = Artist(name="Test Artist", normalized_name="test artist")
        album = Album(title="Test Album", normalized_title="test album", artist=artist, release_date=date(2024, 1, 1))
        session.add_all([artist, album])
        session.flush()

        media = LocalMedia(file_path=str(file_path), file_format="mp3")
        track = Track(
            title="Test Song",
            normalized_title="test song",
            artist_id=artist.id,
            album_id=album.id,
            track_number=1,
            disc_number=1,
            duration=180000,
            media_files=[media]
        )
        session.add(track)
        session.flush()
        track_id = track.id

    mock_enhancer = MagicMock()
    mock_enhancer.identify_file.return_value = (
        {
            "title": "Identified Song",
            "artist": "Test Artist",
            "album": "Identified Album",
            "year": 2024,
            "musicbrainz_id": "mbid-xyz-999"
        },
        0.95
    )

    with patch("web.routes.manager.get_metadata_enhancer", return_value=mock_enhancer):
        response = fetch_metadata(track_id=track_id)

    assert response.get("success") is True
    assert "task" in response
    task_dict = response["task"]
    assert task_dict["id"] is not None
    assert task_dict["file_path"] == str(file_path)
    assert task_dict["detected_metadata"]["title"] == "Identified Song"
    assert task_dict["detected_metadata"]["artist"] == "Test Artist"
    assert task_dict["detected_metadata"]["album"] == "Identified Album"

    # Verify task was persisted in working.db
    working_db = get_working_database()
    with working_db.session_scope() as w_session:
        task_row = w_session.query(ReviewTask).filter(ReviewTask.id == task_dict["id"]).first()
        assert task_row is not None
        assert task_row.file_path == str(file_path)
        assert task_row.status == "pending"

def test_fetch_metadata_returns_error_if_track_or_file_missing(tmp_path):
    response = fetch_metadata(track_id=999999)
    assert response.get("error") == "Track not found"
