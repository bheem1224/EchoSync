"""Tests for path invariance guards, collision resolution, and library watcher scoping."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.path_formatter import ensure_path_invariance
from core.settings import config_manager
from database.music_database import Album, Artist, Base, LocalMedia, Track
from services.library_watcher import LibraryWatcherService


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_ensure_path_invariance_aborts_on_default_artist(tmp_path, memory_db):
    """ensure_path_invariance must not move or rename files when artist_id is default 'Unknown Artist'."""
    session = memory_db

    default_artist = Artist(name="Unknown Artist", normalized_name="unknown artist")
    session.add(default_artist)
    session.flush()

    valid_album = Album(title="Real Album", normalized_title="real album", artist_id=default_artist.id)
    session.add(valid_album)
    session.flush()

    track = Track(
        title="Valid Title",
        normalized_title="valid title",
        artist_id=default_artist.id,
        album_id=valid_album.id,
        echosync_signature="SIG_123",
        track_number=1,
    )
    session.add(track)
    session.flush()

    source_file = tmp_path / "original_file.flac"
    source_file.write_bytes(b"dummy flac audio")

    media = LocalMedia(
        track_id=track.id,
        file_path=str(source_file),
    )
    session.add(media)
    session.flush()

    res = ensure_path_invariance(session, track, media)

    # Invariant: File was NOT moved and returned current path
    assert res.resolve() == source_file.resolve()
    assert source_file.exists()
    assert media.file_path == str(source_file)


def test_ensure_path_invariance_aborts_on_default_album(tmp_path, memory_db):
    """ensure_path_invariance must not move or rename files when album_id is default 'Unknown Album'."""
    session = memory_db

    valid_artist = Artist(name="Real Artist", normalized_name="real artist")
    session.add(valid_artist)
    session.flush()

    default_album = Album(title="Unknown Album", normalized_title="unknown album", artist_id=valid_artist.id)
    session.add(default_album)
    session.flush()

    track = Track(
        title="Valid Title",
        normalized_title="valid title",
        artist_id=valid_artist.id,
        album_id=default_album.id,
        echosync_signature="SIG_123",
        track_number=1,
    )
    session.add(track)
    session.flush()

    source_file = tmp_path / "original_album.flac"
    source_file.write_bytes(b"dummy flac audio")

    media = LocalMedia(
        track_id=track.id,
        file_path=str(source_file),
    )
    session.add(media)
    session.flush()

    res = ensure_path_invariance(session, track, media)

    assert res.resolve() == source_file.resolve()
    assert source_file.exists()
    assert media.file_path == str(source_file)


def test_ensure_path_invariance_aborts_without_signature_or_verification(tmp_path, memory_db):
    """ensure_path_invariance must not move or rename files when unverified and lacking ECHOSYNC_SIGNATURE."""
    session = memory_db

    valid_artist = Artist(name="Real Artist", normalized_name="real artist")
    session.add(valid_artist)
    session.flush()

    valid_album = Album(title="Real Album", normalized_title="real album", artist_id=valid_artist.id)
    session.add(valid_album)
    session.flush()

    track = Track(
        title="Valid Title",
        normalized_title="valid title",
        artist_id=valid_artist.id,
        album_id=valid_album.id,
        echosync_signature=None,  # No signature
        track_number=1,
    )
    track.is_verified = False  # Not verified
    session.add(track)
    session.flush()

    source_file = tmp_path / "unsigned_track.flac"
    source_file.write_bytes(b"dummy audio")

    media = LocalMedia(
        track_id=track.id,
        file_path=str(source_file),
    )
    session.add(media)
    session.flush()

    res = ensure_path_invariance(session, track, media)

    assert res.resolve() == source_file.resolve()
    assert source_file.exists()
    assert media.file_path == str(source_file)


def test_ensure_path_invariance_resolves_collision(tmp_path, memory_db, monkeypatch):
    """ensure_path_invariance appends collision suffix (n) when target exists on disk or in DB."""
    session = memory_db

    library_dir = tmp_path / "library"
    library_dir.mkdir(parents=True, exist_ok=True)

    def mock_get(k, default=None):
        if k in ("storage.library_dir", "library_dir", "storage_locations.library"):
            return str(library_dir)
        if k in (
            "auto_import.file_organization_pattern",
            "library_import.renaming_pattern",
            "metadata_enhancement.naming_template",
        ):
            return "{Artist}/{Album}/{Track} - {Title}.{ext}"
        return default

    monkeypatch.setattr(config_manager, "get", mock_get)

    valid_artist = Artist(name="ArtistName", normalized_name="artistname")
    session.add(valid_artist)
    session.flush()

    valid_album = Album(title="AlbumTitle", normalized_title="albumtitle", artist_id=valid_artist.id)
    session.add(valid_album)
    session.flush()

    track = Track(
        title="Song Title",
        normalized_title="song title",
        artist_id=valid_artist.id,
        album_id=valid_album.id,
        echosync_signature="SIG_VALID",
        track_number=1,
    )
    session.add(track)
    session.flush()

    source_file = library_dir / "input_track.flac"
    source_file.write_bytes(b"dummy audio")

    media = LocalMedia(
        track_id=track.id,
        file_path=str(source_file),
    )
    session.add(media)
    session.flush()

    # Pre-create standard target path on disk: ArtistName/AlbumTitle/01 - Song Title.flac
    colliding_disk_file = library_dir / "ArtistName" / "AlbumTitle" / "01 - Song Title.flac"
    colliding_disk_file.parent.mkdir(parents=True, exist_ok=True)
    colliding_disk_file.write_bytes(b"preexisting file")

    # Also pre-create first collision in database: ArtistName/AlbumTitle/01 - Song Title (1).flac
    colliding_db_path = library_dir / "ArtistName" / "AlbumTitle" / "01 - Song Title (1).flac"
    other_media = LocalMedia(
        track_id=99999,
        file_path=str(colliding_db_path),
    )
    session.add(other_media)
    session.flush()

    res = ensure_path_invariance(session, track, media)

    # Invariant: Since target.flac and target (1).flac collided, target (2).flac must be selected
    expected_path = library_dir / "ArtistName" / "AlbumTitle" / "01 - Song Title (2).flac"
    assert res.resolve() == expected_path.resolve()
    assert expected_path.exists()
    assert media.file_path == str(expected_path)
    assert not source_file.exists()


def test_library_watcher_targets_downloads_not_library(tmp_path, monkeypatch):
    """LibraryWatcherService must schedule watcher exclusively on downloads directory, never library directory."""
    downloads_dir = tmp_path / "downloads"
    library_dir = tmp_path / "library"
    library_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config_manager, "get_downloads_dir", lambda: downloads_dir)
    monkeypatch.setattr(config_manager, "get_library_dir", lambda: library_dir)

    watcher = LibraryWatcherService()

    scheduled_targets = []

    mock_observer = MagicMock()

    def mock_schedule(handler, path, recursive=True):
        scheduled_targets.append((path, recursive))

    mock_observer.schedule.side_effect = mock_schedule
    monkeypatch.setattr("services.library_watcher.Observer", lambda: mock_observer)

    watcher.start()

    # Invariant: downloads directory was automatically created
    assert downloads_dir.exists()

    # Invariant: Observer scheduled exclusively on downloads directory
    assert len(scheduled_targets) == 1
    scheduled_path, recursive = scheduled_targets[0]
    assert Path(scheduled_path).resolve() == downloads_dir.resolve()
    assert Path(scheduled_path).resolve() != library_dir.resolve()
    assert recursive is True

    watcher.stop()
