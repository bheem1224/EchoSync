"""Comprehensive test suite for Ingress Migration & Path Invariance (Stage 3).

Verifies:
1. AutoImportService routes identification through MetadataResolutionEngine and stages to review queue on low confidence.
2. Review queue AcoustID lookup returns identical ResolutionResult payload as background engine.
3. Path invariance moves existing library files through Gatekeeper when metadata changes, updating local_media.file_path.
4. patch_canonical_track strictly rejects attempts to modify physical audio metrics.
"""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

import echosync_core
from core.database.repositories.track_repo import TrackRepository
from core.db.echo_sync_track import EchosyncMedia, EchosyncTrack
from core.io_gatekeeper import Gatekeeper
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest, ResolutionResult
from core.path_formatter import ensure_path_invariance
import uuid
from database.music_database import (
    Album,
    Artist,
    AudioFingerprint,
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
from services.auto_importer import AutoImportService
from web.routes.metadata_review import lookup_review_queue_item_acoustid
from web.routes.tracks import patch_canonical_track
from web.schemas.track import TrackPatchRequest


@pytest.fixture
def isolated_dbs(tmp_path, monkeypatch):
    """Provide clean working and music databases in tmp_path."""
    close_database()
    close_working_database()

    music_db_path = tmp_path / "test_music.db"
    working_db_path = tmp_path / "test_working.db"
    library_dir = tmp_path / "library"
    download_dir = tmp_path / "downloads"
    library_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)

    def mock_config(key, default=None):
        if key in ("storage.library_dir", "library_dir"):
            return str(library_dir)
        if key in ("storage.download_dir", "download_dir"):
            return str(download_dir)
        if key == "metadata_enhancement":
            return {"enabled": True, "auto_import": False, "confidence_threshold": 90}
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
    monkeypatch.setattr("database.working_database.get_working_database", lambda *a, **kw: working_db)

    yield {
        "music_db": music_db,
        "working_db": working_db,
        "library_dir": library_dir,
        "download_dir": download_dir,
    }

    close_database()
    close_working_database()


def test_auto_importer_uses_metadata_resolution_engine(isolated_dbs, tmp_path, monkeypatch):
    """Verifies incoming files route through MetadataResolutionEngine.

    On low confidence, stages to ReviewTask with detected_metadata.
    On high confidence + auto_import=True, finalizes import and moves file.
    """
    download_dir = isolated_dbs["download_dir"]
    library_dir = isolated_dbs["library_dir"]

    # Create test audio file
    low_conf_file = download_dir / "unknown_track.flac"
    low_conf_file.write_bytes(b"0" * 70000)
    old_time = time.time() - 100
    os.utime(low_conf_file, (old_time, old_time))

    service = AutoImportService(library_root=library_dir)

    # 1. Test low confidence resolution -> stages to review queue
    mock_low_result = ResolutionResult(
        media_id="test_low",
        chromaprint="DUMMY_CHROMAPRINT_FOR_TESTING_PURPOSES_ONLY_1234567890",
        confidence_score=0.45,
        resolution_method="text_waterfall",
        title="Unknown Title",
        artist="Unknown Artist",
        album="Unknown Album",
    )

    with patch.object(service.engine, "resolve_track", return_value=mock_low_result) as mock_resolve:
        stats = service.process_batch([low_conf_file])
        assert mock_resolve.called
        assert stats["imported"] == 0
        assert stats["pending_review"] == 1

        # Verify staged ReviewTask in working.db
        work_db = isolated_dbs["working_db"]
        with work_db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.file_path == str(low_conf_file)).first()
            assert task is not None
            assert task.status == "pending"
            assert task.confidence_score == 0.45
            assert task.detected_metadata is not None
            assert task.detected_metadata.get("title") == "Unknown Title"

    # 2. Test high confidence resolution + auto_import=True -> imports and moves file
    high_conf_file = download_dir / "known_track.flac"
    high_conf_file.write_bytes(b"0" * 70000)
    os.utime(high_conf_file, (old_time, old_time))

    def mock_config_auto(key, default=None):
        if key in ("storage.library_dir", "library_dir"):
            return str(library_dir)
        if key in ("storage.download_dir", "download_dir"):
            return str(download_dir)
        if key == "metadata_enhancement":
            return {"enabled": True, "auto_import": True, "confidence_threshold": 90}
        return default

    monkeypatch.setattr("core.settings.config_manager.get", mock_config_auto)

    mock_high_result = ResolutionResult(
        media_id="test_high",
        chromaprint="DUMMY_CHROMAPRINT_FOR_HIGH_CONFIDENCE_1234567890",
        acoustid_id="acoustid-9999",
        musicbrainz_track_id="mbid-canon-1234",
        confidence_score=0.98,
        resolution_method="acoustid",
        title="Canon Title",
        artist="Canon Artist",
        album="Canon Album",
    )

    with patch.object(service.engine, "resolve_track", return_value=mock_high_result):
        with patch.object(service.enhancer, "tag_file_verified", return_value={"title": "Canon Title", "artist": "Canon Artist"}):
            stats = service.process_batch([high_conf_file])
            assert stats["imported"] == 1

            # Destination file should exist in library_dir / Canon Artist / Canon Album / Canon Title.flac
            dest = library_dir / "Canon Artist" / "Canon Album" / "Canon Title.flac"
            assert dest.exists()


def test_review_queue_acoustid_lookup_parity(isolated_dbs, tmp_path, monkeypatch):
    """Verifies review queue lookup returns identical ResolutionResult payload as background engine."""
    download_dir = isolated_dbs["download_dir"]
    track_file = download_dir / "parity_track.mp3"
    track_file.write_bytes(b"0" * 70000)

    work_db = isolated_dbs["working_db"]
    task_id = None
    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(track_file),
            status="pending",
            track_data={"raw_title": "Original Title", "artist_name": "Original Artist"},
            confidence_score=0.0,
        )
        session.add(task)
        session.flush()
        task_id = task.id

    mock_engine_result = ResolutionResult(
        media_id=str(task_id),
        chromaprint="PARITY_CHROMAPRINT_STRING_ABCDEFGHIJK123456789",
        acoustid_id="acoustid-parity-101",
        musicbrainz_track_id="mbid-parity-202",
        confidence_score=0.95,
        resolution_method="acoustid",
        title="Resolved Title",
        artist="Resolved Artist",
        album="Resolved Album",
        year=2024,
        isrc="USABC2400001",
    )

    with patch("core.metadata.engine.MetadataResolutionEngine.resolve_track", return_value=mock_engine_result):
        resp = lookup_review_queue_item_acoustid(task_id=task_id)
        assert resp["success"] is True
        assert resp["match_found"] is True
        assert resp["acoustid_match"] is True
        assert "resolution_result" in resp

        res_dict = resp["resolution_result"]
        assert res_dict["musicbrainz_track_id"] == mock_engine_result.musicbrainz_track_id
        assert res_dict["acoustid_id"] == mock_engine_result.acoustid_id
        assert res_dict["title"] == mock_engine_result.title
        assert res_dict["artist"] == mock_engine_result.artist
        assert res_dict["confidence_score"] == mock_engine_result.confidence_score

        # Also verify database task state updated
        with work_db.session_scope() as session:
            updated_task = session.query(ReviewTask).filter_by(id=task_id).first()
            assert updated_task.confidence_score == 0.95
            assert updated_task.track_data.get("musicbrainz_id") == "mbid-parity-202"
            assert updated_task.track_data.get("acoustid") == "acoustid-parity-101"


def test_path_invariance_moves_file_on_metadata_change(isolated_dbs, tmp_path):
    """Changes artist/album on a library track and confirms Gatekeeper relocates

    the file and updates local_media.file_path while pruning empty source dirs.
    """
    library_dir = isolated_dbs["library_dir"]
    music_db = isolated_dbs["music_db"]

    old_dir = library_dir / "Old Artist" / "Old Album"
    old_dir.mkdir(parents=True, exist_ok=True)
    old_file = old_dir / "Old Song.flac"
    old_file.write_bytes(b"0" * 70000)

    track_sync_id = f"track:test-invariance-{uuid.uuid4().hex}"
    with music_db.session_scope() as session:
        artist = Artist(name="Old Artist")
        album = Album(title="Old Album", artist=artist)
        track = Track(
            title="Old Song",
            artist=artist,
            album=album,
            sync_id=track_sync_id,
        )
        media = LocalMedia(
            file_path=str(old_file),
            file_format="flac",
            track=track,
        )
        session.add_all([artist, album, track, media])
        session.flush()

        # Update metadata to new Artist and Album
        new_artist = Artist(name="New Artist")
        new_album = Album(title="New Album", artist=new_artist)
        session.add_all([new_artist, new_album])
        session.flush()

        track.artist = new_artist
        track.album = new_album
        track.artist_id = new_artist.id
        track.album_id = new_album.id

        # Execute path invariance
        new_target = ensure_path_invariance(session, track, media)

        expected_target = library_dir / "New Artist" / "New Album" / "Old Song.flac"
        assert new_target.resolve() == expected_target.resolve()
        assert expected_target.exists()
        assert not old_file.exists()
        assert media.file_path == str(expected_target)
        # Empty old directory should be pruned
        assert not old_dir.exists()


@pytest.mark.asyncio
async def test_patch_canonical_track_rejects_physical_properties(isolated_dbs):
    """Asserts HTTP 400 when attempting to patch duration, bitrate, or channels."""
    music_db = isolated_dbs["music_db"]
    test_sync_id = f"track:physical-immutability-{uuid.uuid4().hex}"

    with music_db.session_scope() as session:
        artist = Artist(name="Test Artist")
        album = Album(title="Test Album", artist=artist)
        track = Track(
            title="Original Track",
            artist=artist,
            album=album,
            duration=200000,
            sync_id=test_sync_id,
        )
        session.add_all([artist, album, track])
        session.commit()

    # 1. Reject duration
    with pytest.raises(HTTPException) as exc_info:
        payload = TrackPatchRequest(title="Valid Title", duration=150000)  # type: ignore[call-arg]
        await patch_canonical_track(sync_id=test_sync_id, payload=payload)
    assert exc_info.value.status_code == 400
    assert "Cannot PATCH physical file properties" in exc_info.value.detail["error"]
    assert "duration" in exc_info.value.detail["rejected_fields"]

    # 2. Reject bitrate
    with pytest.raises(HTTPException) as exc_info2:
        payload = TrackPatchRequest(bitrate=320000)  # type: ignore[call-arg]
        await patch_canonical_track(sync_id=test_sync_id, payload=payload)
    assert exc_info2.value.status_code == 400
    assert "bitrate" in exc_info2.value.detail["rejected_fields"]

    # 3. Valid update succeeds
    valid_payload = TrackPatchRequest(title="Updated Clean Title", track_number=5)
    updated = await patch_canonical_track(sync_id=test_sync_id, payload=valid_payload)
    assert updated.title == "Updated Clean Title"

    with music_db.session_scope() as session:
        db_track = TrackRepository.get_track_by_sync_id(session, test_sync_id)
        assert db_track.title == "Updated Clean Title"
        assert db_track.track_number == 5
        # Duration remained completely unmutated
        assert db_track.duration == 200000
