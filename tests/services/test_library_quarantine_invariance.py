"""Tests for non-destructive library retention and infinite loop elimination.

Verifies:
1. Library tracks missing core metadata are NEVER ejected to /data/downloads/poor_metadata
   and are NOT deleted from the database; they are enrolled in ReviewTask(action="RESOLVE_LIBRARY_ORPHAN").
2. Unidentifiable media in library sync is retained on disk and enrolled in ReviewTask without ejection.
3. Failed metadata enhancement attempts increment attempts counter and cap at 5, transitioning to
   musicbrainz_id="NOT_FOUND" and creating an orphan review task, breaking infinite retry loops.
"""

import wave
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.database.repositories.track_repo import TrackRepository
from core.metadata.schemas import ResolutionResult
from database.music_database import (
    Album,
    Artist,
    Base,
    LocalMedia,
    Track,
    close_database,
    get_database,
)
from database.working_database import (
    ReviewTask,
    WorkingBase,
    close_working_database,
    get_working_database,
)
from services.library_reorganizer import LibraryReorganizerService
from services.library_sync_service import LibrarySyncService
from services.metadata_enhancer import MetadataEnhancerService


def _create_synthetic_audio(path: Path, duration_sec: float = 0.5) -> None:
    """Generate a clean uncompressed PCM WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x01\x00\x02\x00" * int(44100 * duration_sec))


@pytest.fixture
def isolated_dbs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide isolated test SQLite databases and directory roots."""
    close_database()
    close_working_database()

    music_db_path = tmp_path / "music.db"
    working_db_path = tmp_path / "working.db"
    library_dir = tmp_path / "library"
    download_dir = tmp_path / "downloads"

    library_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)

    def mock_config(key, default=None):
        if key in ("storage.library_dir", "library_dir"):
            return str(library_dir)
        if key in ("storage.download_dir", "download_dir"):
            return str(download_dir)
        if key == "system.quarantine_dir":
            return str(download_dir / "quarantine")
        if key == "auto_import.file_organization_pattern":
            return "{Artist}/{Album}/{Title}{ext}"
        return default

    monkeypatch.setattr("core.settings.config_manager.get", mock_config)

    music_db = get_database(str(music_db_path))
    working_db = get_working_database(str(working_db_path))

    Base.metadata.create_all(music_db.engine)
    WorkingBase.metadata.create_all(working_db.engine)

    monkeypatch.setattr("database.music_database.get_database", lambda *a, **kw: music_db)
    monkeypatch.setattr("database.get_database", lambda *a, **kw: music_db)
    monkeypatch.setattr(
        "database.working_database.get_working_database", lambda *a, **kw: working_db
    )

    yield {
        "music_db": music_db,
        "working_db": working_db,
        "library_dir": library_dir,
        "download_dir": download_dir,
    }

    close_database()
    close_working_database()


def test_library_reorganizer_does_not_eject_unidentified_track(isolated_dbs, monkeypatch):
    """Library tracks with unknown metadata must NEVER be moved to /data/downloads/poor_metadata

    or deleted from the database. They must stay stationary and create a ReviewTask.
    """
    library_dir = isolated_dbs["library_dir"]
    music_db = isolated_dbs["music_db"]
    working_db = isolated_dbs["working_db"]

    # Create established library track with Unknown Artist and Unknown Album
    file_path = library_dir / "Unknown Artist" / "Unknown Album" / "track_01.wav"
    _create_synthetic_audio(file_path)

    with music_db.session_scope() as session:
        artist = Artist(name="Unknown Artist")
        album = Album(title="Unknown Album", artist=artist)
        track = Track(
            title="track_01",
            artist=artist,
            album=album,
            sync_id="orphan01",
        )
        media = LocalMedia(
            file_path=str(file_path),
            track=track,
            media_id="media_orphan01",
        )
        session.add_all([artist, album, track, media])
        session.flush()
        track_id = track.id
        media_id = media.id

    # Mock library preferences to point to our test library_dir
    monkeypatch.setattr(
        "services.library_reorganizer.get_library_preferences",
        lambda: (str(library_dir), "{Artist}/{Album}/{Title}{ext}"),
    )

    reorganizer = LibraryReorganizerService()
    reorganizer.reorganize_library(track_ids=[track_id])

    # 1. File must remain on disk in library_dir
    assert file_path.exists(), f"File {file_path} was unexpectedly deleted or moved!"
    poor_metadata_dir = isolated_dbs["download_dir"] / "poor_metadata"
    assert not poor_metadata_dir.exists() or len(list(poor_metadata_dir.glob("*"))) == 0

    # 2. LocalMedia and Track records must NOT be deleted from music_db
    with music_db.session_scope() as session:
        t = session.get(Track, track_id)
        assert t is not None, "Track was destructively deleted from database!"
        m = session.get(LocalMedia, media_id)
        assert m is not None, "LocalMedia was destructively deleted from database!"
        assert m.file_path == str(file_path)

    # 3. ReviewTask with action='RESOLVE_LIBRARY_ORPHAN' must be enqueued in working_db
    with working_db.session_scope() as w_session:
        task = w_session.query(ReviewTask).filter(ReviewTask.file_path == str(file_path)).first()
        assert task is not None, "No ReviewTask was created for the library orphan!"
        assert task.track_data.get("action") == "RESOLVE_LIBRARY_ORPHAN"
        assert task.track_data.get("track_id") == track_id


def test_library_sync_does_not_quarantine_unidentifiable_file(isolated_dbs, monkeypatch):
    """Unidentifiable files detected during library sync must remain on disk in library_dir,

    and enroll in a RESOLVE_LIBRARY_ORPHAN review task rather than being purged or moved to quarantine.
    """
    library_dir = isolated_dbs["library_dir"]
    working_db = isolated_dbs["working_db"]

    # Create unidentifiable file with generic name and no tags
    unidentifiable_file = library_dir / "track_99.wav"
    _create_synthetic_audio(unidentifiable_file)

    sync_service = LibrarySyncService()
    # Mock gatekeeper validate_path
    monkeypatch.setattr(sync_service.gatekeeper, "validate_path", lambda p: True)

    # Run sync
    sync_service.sync_library(scan_mode="incremental")

    # 1. File must still exist in library_dir
    assert unidentifiable_file.exists(), "File was moved out of library!"

    # 2. Quarantine directory must not have received this file
    quarantine_dir = isolated_dbs["download_dir"] / "quarantine"
    if quarantine_dir.exists():
        assert not (quarantine_dir / unidentifiable_file.name).exists()

    # 3. ReviewTask must be enqueued in working_db
    with working_db.session_scope() as w_session:
        task = w_session.query(ReviewTask).filter(ReviewTask.file_path == str(unidentifiable_file)).first()
        assert task is not None, "No ReviewTask was enqueued for unidentifiable sync file!"
        assert task.track_data.get("action") == "RESOLVE_LIBRARY_ORPHAN"


def test_enhancement_attempts_increment_and_cap_at_five(isolated_dbs, monkeypatch):
    """Failed enhancement attempts increment enhancement_attempts counter, set last_enhancement_attempt,

    and at attempt 5 transition to musicbrainz_id='NOT_FOUND' and create an orphan ReviewTask, breaking infinite loops.
    """
    music_db = isolated_dbs["music_db"]
    working_db = isolated_dbs["working_db"]
    library_dir = isolated_dbs["library_dir"]

    track_file = library_dir / "Unknown Artist" / "Unknown Album" / "rare_track.wav"
    _create_synthetic_audio(track_file)

    with music_db.session_scope() as session:
        artist = Artist(name="Unknown Artist")
        album = Album(title="Unknown Album", artist=artist)
        track = Track(
            title="rare_track",
            artist=artist,
            album=album,
            sync_id="rare0001",
            musicbrainz_id=None,
            metadata_status={},
        )
        media = LocalMedia(
            file_path=str(track_file),
            track=track,
            media_id="media_rare0001",
        )
        session.add_all([artist, album, track, media])
        session.flush()
        track_id = track.id

    # Mock resolution engine to always return zero confidence (unresolvable track)
    mock_engine = MagicMock()
    mock_engine.resolve_track.return_value = ResolutionResult(
        media_id="media_rare0001",
        sync_id="rare0001",
        title="rare_track",
        artist="Unknown Artist",
        album="Unknown Album",
        confidence_score=0.0,
        musicbrainz_track_id=None,
        resolution_method="text_waterfall",
    )
    monkeypatch.setattr("core.metadata.engine.MetadataResolutionEngine", lambda *a, **kw: mock_engine)

    enhancer = MetadataEnhancerService()

    # Attempts 1 to 4: Should increment attempts, keep musicbrainz_id as None
    for attempt_num in range(1, 5):
        enhancer.enhance_track(track_id)
        with music_db.session_scope() as session:
            t = session.get(Track, track_id)
            assert t.metadata_status.get("enhancement_attempts") == attempt_num
            assert "last_enhancement_attempt" in t.metadata_status
            assert t.musicbrainz_id is None, f"musicbrainz_id should remain None on attempt {attempt_num}"

    # Attempt 5: Caps attempts, sets musicbrainz_id = "NOT_FOUND", enhanced = False, and creates ReviewTask
    enhancer.enhance_track(track_id)
    with music_db.session_scope() as session:
        t = session.get(Track, track_id)
        assert t.metadata_status.get("enhancement_attempts") == 5
        assert t.metadata_status.get("enhanced") is False
        assert t.musicbrainz_id == "NOT_FOUND"

        # Verify TrackRepository.get_tracks_for_enhancement no longer selects this track
        candidates = TrackRepository.get_tracks_for_enhancement(session, batch_size=10, check_all_files=False)
        candidate_ids = [c.id for c in candidates]
        assert track_id not in candidate_ids, "Track was selected again despite reaching 5 attempts (infinite loop)!"

    # Verify ReviewTask was enqueued on attempt 5
    with working_db.session_scope() as w_session:
        task = w_session.query(ReviewTask).filter(ReviewTask.file_path == str(track_file)).first()
        assert task is not None, "No ReviewTask was created when enhancement capped at attempt 5!"
        assert task.track_data.get("action") == "RESOLVE_LIBRARY_ORPHAN"
        assert task.track_data.get("attempts") == 5
