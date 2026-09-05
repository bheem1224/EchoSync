from unittest.mock import MagicMock, patch

from core.db.echo_sync_track import EchosyncTrack
from database.working_database import ReviewTask, get_working_database
from web.routes.metadata_review import (
    MusicBrainzLookupRequest,
    lookup_review_queue_item_musicbrainz,
)


def test_musicbrainz_lookup_response_structure_on_match(tmp_path):
    file_path = tmp_path / "song.mp3"
    file_path.write_bytes(b"fake audio data")

    db = get_working_database()
    with db.session_scope() as session:
        task = ReviewTask(
            file_path=str(file_path),
            status="pending",
            track_data={"artist_name": "Adele", "title": "Hello"},
        )
        session.add(task)
        session.flush()
        task_id = task.id

    found_track = EchosyncTrack(
        raw_title="Hello",
        artist_name="Adele",
        album_title="25",
        release_year=2015,
        musicbrainz_id="mbid-12345",
    )

    with (
        patch("web.routes.metadata_review.plugin_loader.get_plugin") as mock_get_plugin,
        patch(
            "web.routes.metadata_review._musicbrainz_text_search",
            return_value=found_track,
        ),
    ):
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
            track_data={"artist_name": "Nonexistent", "title": "SongXYZ"},
        )
        session.add(task)
        session.flush()
        task_id = task.id

    with (
        patch("web.routes.metadata_review.plugin_loader.get_plugin") as mock_get_plugin,
        patch("web.routes.metadata_review._musicbrainz_text_search", return_value=None),
    ):
        mock_provider = MagicMock()
        mock_get_plugin.return_value = mock_provider

        req = MusicBrainzLookupRequest(
            metadata={"artist": "Nonexistent", "title": "SongXYZ"}
        )
        res = lookup_review_queue_item_musicbrainz(task_id, req)

        assert res["success"] is True
        assert res["match_found"] is False
        assert res["updated_fields"] == []
        assert res["message"] == "No matching record found in database"


def test_acoustid_contribution_trigger_on_approval(tmp_path):
    from web.routes.metadata_review import _submit_acoustid_contribution_async

    mock_provider = MagicMock()
    with patch(
        "web.routes.metadata_review.get_plugin_by_capability",
        return_value=mock_provider,
    ):
        # Valid UUID and fingerprint
        _submit_acoustid_contribution_async(
            fingerprint="AQAAZEmSJVkSRUkC",
            duration=180,
            mbid="8543e49e-b79e-4e4b-a25e-38d5e8964e52",
        )
        mock_provider.queue_fingerprint_submission.assert_called_once_with(
            fingerprint="AQAAZEmSJVkSRUkC",
            duration=180,
            mbid="8543e49e-b79e-4e4b-a25e-38d5e8964e52",
        )


def test_import_single_file_updates_existing_track_and_local_media(tmp_path):
    from database import _canonicalize_path
    from database.music_database import Album, Artist, LocalMedia, Track, get_database
    from web.routes.metadata_review import _import_single_file

    music_db = get_database()
    old_file = tmp_path / "old_artist" / "old_album" / "song.flac"
    old_file.parent.mkdir(parents=True, exist_ok=True)
    old_file.write_bytes(b"audio")

    new_file = tmp_path / "new_artist" / "new_album" / "song.flac"
    new_file.parent.mkdir(parents=True, exist_ok=True)
    new_file.write_bytes(b"audio")

    import uuid

    test_sid = f"sid_{uuid.uuid4().hex[:12]}"
    test_mid = f"mid_{uuid.uuid4().hex[:12]}"

    # Seed an existing track with Unknown Artist
    with music_db.session_scope() as session:
        artist = Artist(name="Unknown Artist", normalized_name="unknown artist")
        album = Album(
            title="Unknown Album", normalized_title="unknown album", artist=artist
        )
        track = Track(
            title="Black Rover",
            normalized_title="black rover",
            sync_id=test_sid,
            artist=artist,
            album=album,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            media_id=test_mid,
            file_path=_canonicalize_path(str(old_file)),
            file_format="flac",
        )
        session.add(media)
        session.commit()
        track_id = track.id

    # Call _import_single_file simulating review approval relocation
    metadata_to_apply = {
        "title": "Black Rover",
        "artist": "ビッケブランカ",
        "album": "ウララ",
        "year": 2018,
        "musicbrainz_id": "mbid-rover-123",
    }

    _import_single_file(new_file, metadata_to_apply, old_file_path=old_file)

    # Verify track and local_media were updated in-place without duplicate
    with music_db.session_scope() as session:
        updated_track = session.get(Track, track_id)
        assert updated_track is not None
        assert updated_track.title == "Black Rover"
        assert updated_track.artist.name == "ビッケブランカ"
        assert updated_track.album.title == "ウララ"
        assert updated_track.musicbrainz_id == "mbid-rover-123"

        updated_media = session.query(LocalMedia).filter_by(track_id=track_id).first()
        assert updated_media is not None
        assert updated_media.file_path == _canonicalize_path(str(new_file))
