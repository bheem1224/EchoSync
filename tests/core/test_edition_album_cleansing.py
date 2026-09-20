"""Tests for Edition / Version field handling and album release title cleansing."""

from unittest.mock import MagicMock

from core.db.echo_sync_track import EchosyncTrack
from core.metadata.adapter import ResolutionAdapter
from core.metadata.engine import _create_resolved_track
from database.music_database import Album, Artist, Track
from database.working_database import ReviewTask, get_working_database
from fastapi.testclient import TestClient
from web.api_app import create_app


def test_echosync_track_cleanses_album_release_title_and_extracts_edition():
    """Verify that EchosyncTrack strips version descriptors from album_title and sets edition."""
    track = EchosyncTrack(
        raw_title="Dusk Till Dawn",
        artist_name="ZAYN feat. Sia",
        album_title="Dusk Till Dawn (Radio Edit)",
    )
    assert track.title == "Dusk Till Dawn"
    assert track.album_title == "Dusk Till Dawn"
    assert track.edition.lower() == "radio edit"


def test_create_resolved_track_cleanses_album_edition():
    """Verify that _create_resolved_track extracts edition from release title if title lacks edition."""
    track = _create_resolved_track(
        title="Midnight City",
        artist="M83",
        album="Midnight City (Remixes)",
    )
    assert track.title == "Midnight City"
    assert track.album_title == "Midnight City"
    assert track.edition.lower() == "remixes"


def test_hydrate_track_persists_edition_and_cleanses_album_title():
    """Verify ResolutionAdapter.hydrate_track properly assigns edition to Track ORM model."""
    adapter = ResolutionAdapter()
    session = MagicMock()

    artist = Artist(name="ZAYN", normalized_name="zayn")
    album = Album(title="Dusk Till Dawn (Radio Edit)", artist=artist)
    track_orm = Track(title="Dusk Till Dawn", artist=artist, album=album)

    result = EchosyncTrack(
        raw_title="Dusk Till Dawn",
        artist_name="ZAYN",
        album_title="Dusk Till Dawn (Radio Edit)",
        edition="Radio Edit",
    )

    updated_track = adapter.hydrate_track(result, session, track_orm)
    assert updated_track.edition.lower() == "radio edit"
    assert updated_track.album.title == "Dusk Till Dawn"


def test_review_task_detected_metadata_property_and_setter():
    """Verify ReviewTask detected_metadata property and setter round-trip edition."""
    task = ReviewTask(file_path="/music/test.flac")
    task.detected_metadata = {
        "title": "Song",
        "edition": "Deluxe Edition",
        "artist": "Artist",
        "album": "Album",
    }
    assert task.detected_metadata["edition"] == "Deluxe Edition"
    assert task.track_data["edition"] == "Deluxe Edition"


def test_metadata_review_route_updates_edition(tmp_path):
    """Verify PUT /api/v1/core/metadata_review/{id} updates edition in track_data."""
    app = create_app()
    client = TestClient(app)
    work_db = get_working_database()

    dummy_file = tmp_path / "song.flac"
    dummy_file.write_bytes(b"0" * 1000)

    with work_db.session_scope() as session:
        t = ReviewTask(
            file_path=str(dummy_file),
            status="pending",
            track_data={"title": "Song", "artist": "Artist"},
        )
        session.add(t)
        session.commit()
        task_id = t.id

    res = client.put(
        f"/api/v1/core/metadata_review/{task_id}",
        json={"metadata": {"title": "Song", "edition": "Club Mix", "artist": "Artist"}},
    )
    assert res.status_code == 200

    with work_db.session_scope() as session:
        updated = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        assert updated.detected_metadata["edition"] == "Club Mix"
        assert updated.track_data["edition"] == "Club Mix"

