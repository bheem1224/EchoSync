
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import asyncio

from services.download_manager import DownloadManager
from core.matching_engine.echo_sync_track import EchosyncTrack
from database.music_database import Track, Artist, Album, MusicDatabase
from database.working_database import Download, ReviewTask, WorkingDatabase


class TestDownloadManagerLogic:
    """Task 1 Verification: Infinite Polling Fix"""

    def test_queue_download_skips_existing(self, mock_db, mock_work_db):
        """Verify that queue_download skips tracks already in the library."""
        manager = DownloadManager.get_instance()
        manager.db = mock_db
        manager.work_db = mock_work_db

        # 1. Setup: Add "Track A" to the library
        with mock_db.session_scope() as session:
            artist = Artist(name="The Artist")
            session.add(artist)
            session.flush()

            album = Album(title="Some Album", artist=artist)
            session.add(album)
            track = Track(
                title="Track A",
                artist=artist,
                album=album,
                file_path="/music/The Artist/Track A.mp3"
            )
            session.add(track)
            session.commit()

        # 2. Action: Attempt to queue "Track A"
        track_to_download = EchosyncTrack(
            raw_title="Track A",
            artist_name="The Artist",
            album_title="Some Album"
        )

        with patch('services.download_manager.get_database', return_value=mock_db):
            with patch('services.download_manager.get_working_database', return_value=mock_work_db):
                result_id = manager.queue_download(track_to_download)
                # 3. Assert: Result should be 0 (skipped) and queue size 0
                assert result_id == 0

    def test_startup_purge_removes_existing(self, mock_db, mock_work_db):
        """Verify that startup purge removes queued items that exist in library."""
        manager = DownloadManager.get_instance()
        manager.db = mock_db
        manager.work_db = mock_work_db

        # 1. Setup: Add "Track B" to library AND download queue
        track_obj = EchosyncTrack(
            raw_title="Track B",
            artist_name="The Artist",
            album_title="Some Album"
        )

        with mock_db.session_scope() as session:
            artist = Artist(name="The Artist")
            session.add(artist)
            session.flush()

            # Library entry
            album = Album(title="Some Album", artist=artist)
            session.add(album)
            track = Track(
                title="Track B",
                artist=artist,
                album=album,
                file_path="/music/The Artist/Track B.mp3"
            )
            session.add(track)
            session.commit()

        with mock_work_db.session_scope() as session:
            # Queue entry (simulating stale state)
            download = Download(
                sync_id=track_obj.sync_id,
                echo_sync_track=track_obj.to_dict(),
                status="queued"
            )
            session.add(download)
            session.commit()

        # 2. Action: Run purge
        with patch('services.download_manager.get_database', return_value=mock_db):
            with patch('services.download_manager.get_working_database', return_value=mock_work_db):
                manager._purge_existing_tracks_from_queue()

        # 3. Assert: Queue should be empty
        with mock_work_db.session_scope() as session:
            count = session.query(Download).count()
            assert count == 0

    @pytest.mark.asyncio
    async def test_process_queue_skips_failed_terminal(self, mock_db, mock_work_db):
        """Verify that _process_queue doesn't infinitely process terminal fail states."""
        manager = DownloadManager.get_instance()
        manager.db = mock_db
        manager.work_db = mock_work_db

        track_obj = EchosyncTrack(
            raw_title="Track C",
            artist_name="The Artist",
            album_title="Some Album"
        )

        with mock_work_db.session_scope() as session:
            # Add item in terminal failure state
            download = Download(
                sync_id=track_obj.sync_id,
                echo_sync_track=track_obj.to_dict(),
                status="failed_max_retries"
            )
            session.add(download)
            session.commit()

        # Attempt process
        with patch('services.download_manager.get_database', return_value=mock_db):
            with patch('services.download_manager.get_working_database', return_value=mock_work_db):
                    await manager._process_queued_items()

        # Should still be failed_max_retries (not requeued or searching)
        with mock_work_db.session_scope() as session:
            dl = session.query(Download).first()
            assert dl.status == "failed_max_retries"

class TestAutoImportLogic:
    """Task 2 Verification: Memory Leak Fix"""

    def test_is_path_ignored_db_query(self, mock_work_db):
        """Verify that _is_path_ignored queries the DB correctly.

        Expected behaviour after the 48-hour Review Queue backoff was introduced:
        - 'ignored' tasks  → always skipped (True)
        - 'pending' tasks created < 48 h ago  → skipped (True)  [API-spam guard]
        - 'pending' tasks created > 48 h ago  → NOT skipped (False) [allow retry]
        - unknown paths                        → NOT skipped (False)
        """
        from datetime import timedelta
        from services.auto_importer import AutoImportService
        from time_utils import utc_now

        service = AutoImportService.get_instance()
        service.work_db = mock_work_db

        ignored_path = "/downloads/ignored_song.mp3"
        pending_recent_path = "/downloads/pending_recent.mp3"
        pending_old_path = "/downloads/pending_old.mp3"

        old_timestamp = utc_now() - timedelta(hours=72)

        with mock_work_db.session_scope() as session:
            session.add(ReviewTask(file_path=ignored_path, status="ignored"))
            # Recent pending task — within the 48-hour backoff window
            session.add(ReviewTask(file_path=pending_recent_path, status="pending"))
            # Old pending task — outside the backoff window; safe to retry
            old_task = ReviewTask(
                file_path=pending_old_path,
                status="pending",
                created_at=old_timestamp,
            )
            # Directly set updated_at if the column exists on the model
            if hasattr(old_task, 'updated_at'):
                old_task.updated_at = old_timestamp
            session.add(old_task)
            session.commit()

        with patch('services.auto_importer.get_working_database', return_value=mock_work_db):
            with patch('services.auto_importer.get_metadata_enhancer'):
                with patch('services.auto_importer.config_manager') as mock_config:
                    mock_config.get_library_dir.return_value = Path("/tmp/lib")
                    # 'ignored' → always skip
                    assert service._is_path_ignored(ignored_path) is True
                    # recent 'pending' → skip (API-spam guard)
                    assert service._is_path_ignored(pending_recent_path) is True
                    # old 'pending' → allow retry
                    assert service._is_path_ignored(pending_old_path) is False
                    # unknown path → don't skip
                    assert service._is_path_ignored("/downloads/random.mp3") is False
