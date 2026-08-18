import time
import os
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest

from database.working_database import ReviewTask, get_working_database
from database.music_database import get_database, Track, Artist
from core.db.echo_sync_track import EchosyncTrack, EchosyncMedia
from time_utils import utc_now
from services.library_watcher import _AudioEventHandler, _process_new_file
from services.auto_importer import AutoImportService


def test_library_watcher_ignores_filtered_paths():
    handler = _AudioEventHandler()
    with patch.object(handler, '_fire') as mock_fire:
        handler._schedule("/music/downloads/poor_metadata/track.flac")
        handler._schedule("C:\\music\\downloads\\incomplete\\track.mp3")
        handler._schedule("/downloads/temp/song.tmp")
        handler._schedule("/downloads/temp/song.part")
        assert len(handler._pending) == 0


def test_library_watcher_upserts_with_track_repository(tmp_path, monkeypatch):
    # Create fake audio file > 64KB
    test_file = tmp_path / "test_track.flac"
    test_file.write_bytes(b"0" * 70000)

    monkeypatch.setattr(
        "services.library_watcher.echosync_core.extract_metadata",
        lambda p: {"title": "Test Title", "artist": "Test Artist", "album": "Test Album", "duration_ms": 120000}
    )

    published_events = []
    monkeypatch.setattr("services.library_watcher.event_bus.publish", lambda ev: published_events.append(ev))

    _process_new_file(test_file)

    # Verify track in DB
    db = get_database()
    with db.session_factory() as session:
        track = session.query(Track).filter_by(title="Test Title").first()
        assert track is not None
        assert track.artist is not None
        assert track.artist.name == "Test Artist"

    assert len(published_events) == 1
    assert published_events[0]["event"] == "TRACK_IMPORTED"
    assert published_events[0]["track"]["title"] == "Test Title"


def test_auto_importer_io_safety_lock_and_path_filter(tmp_path, monkeypatch):
    service = AutoImportService()

    # Small file (<=64KB)
    small_file = tmp_path / "small.mp3"
    small_file.write_bytes(b"0" * 1000)

    # Fresh file (mtime < 15s ago)
    fresh_file = tmp_path / "fresh.mp3"
    fresh_file.write_bytes(b"0" * 70000)

    # Ignored subdir file
    poor_dir = tmp_path / "poor_metadata"
    poor_dir.mkdir()
    poor_file = poor_dir / "poor.mp3"
    poor_file.write_bytes(b"0" * 70000)
    # set mtime old
    old_time = time.time() - 100
    os.utime(poor_file, (old_time, old_time))

    # Valid mature file
    valid_file = tmp_path / "valid.mp3"
    valid_file.write_bytes(b"0" * 70000)
    os.utime(valid_file, (old_time, old_time))

    def mock_config(key, default=None):
        if "dir" in key:
            return str(tmp_path)
        if "metadata_enhancement" in key:
            return {"enabled": True, "auto_import": False}
        return default

    monkeypatch.setattr("core.settings.config_manager.get", mock_config)

    processed_batches = []
    monkeypatch.setattr(service, "process_batch", lambda files: processed_batches.extend(files))

    service.scan_and_process()

    # Only valid_file should be collected for batch processing
    assert len(processed_batches) == 1
    assert processed_batches[0].name == "valid.mp3"


def test_auto_importer_retry_aged_review_tasks(tmp_path, monkeypatch):
    service = AutoImportService()
    work_db = get_working_database()

    aged_file = tmp_path / "aged.flac"
    aged_file.write_bytes(b"0" * 70000)

    # Insert an aged review task (updated 8 days ago)
    eight_days_ago = utc_now() - timedelta(days=8)
    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(aged_file),
            status="pending",
            updated_at=eight_days_ago,
            last_checked_at=eight_days_ago,
            retry_count=0
        )
        session.add(task)
        session.commit()
        task_id = task.id

    # Mock enhancer to return match
    monkeypatch.setattr(
        service.enhancer,
        "identify_file",
        lambda p: ({"title": "Retried Title", "artist": "Retried Artist"}, 0.95)
    )

    service._retry_aged_review_tasks()

    with work_db.session_scope() as session:
        updated_task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        assert updated_task is not None
        assert updated_task.retry_count == 1
        assert updated_task.confidence_score == 0.95
        assert updated_task.detected_metadata["title"] == "Retried Title"
        assert updated_task.last_checked_at > eight_days_ago
