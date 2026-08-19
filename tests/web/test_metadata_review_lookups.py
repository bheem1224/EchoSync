import pytest
from unittest.mock import MagicMock, patch
from database.working_database import ReviewTask, get_working_database
from web.routes.metadata_review import lookup_review_queue_item_musicbrainz, lookup_review_queue_item_acoustid, lookup_review_queue_item_isrc, MusicBrainzLookupRequest, ISRCLookupRequest
from core.db.echo_sync_track import EchosyncTrack

def test_musicbrainz_lookup_response_structure_on_match(tmp_path):
    file_path = tmp_path / "song.mp3"
    file_path.write_bytes(b"fake audio data")

    db = get_working_database()
    with db.session_scope() as session:
        task = ReviewTask(
            file_path=str(file_path),
            status="pending",
            track_data={"artist_name": "Adele", "title": "Hello"}
        )
        session.add(task)
        session.flush()
        task_id = task.id

    found_track = EchosyncTrack(
        raw_title="Hello",
        artist_name="Adele",
        album_title="25",
        release_year=2015,
        musicbrainz_id="mbid-12345"
    )

    with patch("web.routes.metadata_review.plugin_loader.get_plugin") as mock_get_plugin, \
         patch("web.routes.metadata_review._musicbrainz_text_search", return_value=found_track):
        mock_provider = MagicMock()
        mock_get_plugin.return_value = mock_provider

        req = MusicBrainzLookupRequest(metadata={"artist": "Adele", "title": "Hello"})
        res = lookup_review_queue_item_musicbrainz(task_id, req)

        assert res["success"] is True
        assert res["match_found"] is True
        assert "title" in res["updated_fields"]
        assert "artist" in res["updated_fields"]
        assert "album" in res["updated_fields"]
        assert res["message"] == "Match found"
        assert res["metadata"]["title"] == "Hello"
        assert res["metadata"]["artist"] == "Adele"

def test_musicbrainz_lookup_response_structure_on_no_match(tmp_path):
    file_path = tmp_path / "unknown.mp3"
    file_path.write_bytes(b"fake audio data")

    db = get_working_database()
    with db.session_scope() as session:
        task = ReviewTask(
            file_path=str(file_path),
            status="pending",
            track_data={"artist_name": "Nonexistent", "title": "SongXYZ"}
        )
        session.add(task)
        session.flush()
        task_id = task.id

    with patch("web.routes.metadata_review.plugin_loader.get_plugin") as mock_get_plugin, \
         patch("web.routes.metadata_review._musicbrainz_text_search", return_value=None):
        mock_provider = MagicMock()
        mock_get_plugin.return_value = mock_provider

        req = MusicBrainzLookupRequest(metadata={"artist": "Nonexistent", "title": "SongXYZ"})
        res = lookup_review_queue_item_musicbrainz(task_id, req)

        assert res["success"] is True
        assert res["match_found"] is False
        assert res["updated_fields"] == []
        assert res["message"] == "No matching record found in database"
