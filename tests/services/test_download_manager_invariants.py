import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from database.working_database import DownloadQueue, ReviewTask
from database.music_database import Track, Artist
from core.db.echo_sync_track import EchosyncTrack
from core.event_bus import event_bus
from time_utils import utc_now
from services.download_manager import DownloadManager
from services.auto_importer import AutoImportService
from services.library_watcher import suppress_path, is_path_suppressed, _is_path_ignored


@pytest.fixture()
def dm(mock_db, mock_work_db):
    DownloadManager._instance = None
    with patch("services.download_manager.get_database", return_value=mock_db), \
         patch("services.download_manager.get_working_database", return_value=mock_work_db):
        mgr = DownloadManager.get_instance()
    mgr.db = mock_db
    mgr.work_db = mock_work_db
    yield mgr
    DownloadManager._instance = None


def test_recover_stuck_items_resets_searching_and_downloading(dm, mock_work_db):
    with mock_work_db.session_scope() as session:
        item1 = DownloadQueue(
            sync_id="sync-1",
            status="searching",
            provider_id="provider_a",
            retry_count=1,
            echo_sync_track={"title": "Song 1", "artist_name": "Artist 1"},
        )
        item2 = DownloadQueue(
            sync_id="sync-2",
            status="downloading",
            provider_id="user|file.flac",
            retry_count=2,
            echo_sync_track={"title": "Song 2", "artist_name": "Artist 2"},
        )
        session.add_all([item1, item2])

    import asyncio
    asyncio.run(dm._recover_stuck_items())

    with mock_work_db.session_scope() as session:
        items = session.query(DownloadQueue).all()
        for item in items:
            assert item.status == "queued"
            assert item.provider_id is None


def test_requeue_retryable_failed_items_exponential_backoff(dm, mock_work_db):
    now = utc_now()

    with mock_work_db.session_scope() as session:
        # Item with retry_count=0: delay is 2^0 * 60 = 60s. Updated 30s ago -> should NOT requeue
        item_not_ready = DownloadQueue(
            sync_id="sync-1",
            status="failed",
            retry_count=0,
            updated_at=now - timedelta(seconds=30),
            echo_sync_track={"title": "Song 1", "artist_name": "Artist 1"},
        )
        # Item with retry_count=0: updated 120s ago -> SHOULD requeue
        item_ready = DownloadQueue(
            sync_id="sync-2",
            status="failed",
            retry_count=0,
            updated_at=now - timedelta(seconds=120),
            echo_sync_track={"title": "Song 2", "artist_name": "Artist 2"},
        )
        # Item with retry_count=5 -> should NOT requeue (capped)
        item_capped = DownloadQueue(
            sync_id="sync-3",
            status="failed",
            retry_count=5,
            updated_at=now - timedelta(days=1),
            echo_sync_track={"title": "Song 3", "artist_name": "Artist 3"},
        )
        session.add_all([item_not_ready, item_ready, item_capped])

    requeued = dm._requeue_retryable_failed_items(limit=10)
    assert requeued == 1

    with mock_work_db.session_scope() as session:
        i1 = session.query(DownloadQueue).filter_by(id=item_not_ready.id).first()
        i2 = session.query(DownloadQueue).filter_by(id=item_ready.id).first()
        i3 = session.query(DownloadQueue).filter_by(id=item_capped.id).first()

        assert i1.status == "failed"
        assert i2.status == "queued"
        assert i2.retry_count == 1
        assert i3.status == "failed"


def test_auto_importer_compound_eviction_and_orphan_deletion(mock_work_db, tmp_path):
    poor_meta_dir = tmp_path / "downloads" / "poor_metadata"
    poor_meta_dir.mkdir(parents=True, exist_ok=True)
    orphan_file = poor_meta_dir / "quarantined_track.flac"
    orphan_file.write_bytes(b"dummy audio content")

    with mock_work_db.session_scope() as session:
        # Task 1: matches by ISRC
        task1 = ReviewTask(
            status="pending",
            file_path=str(orphan_file),
            detected_metadata={"isrc": "USRC12345678", "artist": "Daft Punk", "title": "Get Lucky"},
            track_data={"isrc": "USRC12345678", "artist": "Daft Punk", "title": "Get Lucky", "duration_ms": 240000},
        )
        # Task 2: matches by Artist + Title + Duration within 2000ms
        task2 = ReviewTask(
            status="pending",
            file_path=str(tmp_path / "downloads" / "another.flac"),
            detected_metadata={"artist": "Justice", "title": "Genesis"},
            track_data={"artist": "Justice", "title": "Genesis", "duration_ms": 230000},
        )
        session.add_all([task1, task2])

    with patch("services.auto_importer.get_working_database", return_value=mock_work_db):
        AutoImportService._instance = None
        service = AutoImportService.get_instance()

        # Directly invoke _on_track_imported for Daft Punk track
        service._on_track_imported({
            "track": {
                "isrc": "USRC12345678",
                "artist_name": "Daft Punk",
                "title": "Get Lucky",
                "duration_ms": 240000,
            }
        })

        with mock_work_db.session_scope() as session:
            t1 = session.query(ReviewTask).filter_by(id=task1.id).first()
            assert t1.status == "approved"
            assert not orphan_file.exists()

        # Directly invoke _on_track_imported for Justice track (duration 231000ms, within 2000ms of 230000ms)
        service._on_track_imported({
            "track": {
                "artist_name": "Justice",
                "title": "Genesis",
                "duration_ms": 231000,
            }
        })

        with mock_work_db.session_scope() as session:
            t2 = session.query(ReviewTask).filter_by(id=task2.id).first()
            assert t2.status == "approved"


def test_library_watcher_suppress_path_and_path_ignored(tmp_path):
    target = tmp_path / "Music" / "Artist" / "Album" / "track.flac"
    str_path = str(target)

    assert not is_path_suppressed(str_path)
    with suppress_path(str_path):
        assert is_path_suppressed(str_path)
    assert not is_path_suppressed(str_path)

    # Test path exclusions
    poor_path = tmp_path / "poor_metadata" / "track.flac"
    tmp_file = tmp_path / "downloads" / "track.tmp"
    regular_file = tmp_path / "downloads" / "track.flac"

    assert _is_path_ignored(str(poor_path))
    assert _is_path_ignored(str(tmp_file))
    assert not _is_path_ignored(str(regular_file))
