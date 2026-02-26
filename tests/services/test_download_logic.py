"""
Verification tests for Critical Logic Bug Fixes (P0).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from services.download_manager import DownloadManager
from core.matching_engine.soul_sync_track import SoulSyncTrack
from database.music_database import Track, Artist, Download, ReviewTask, MusicDatabase

@pytest.fixture
def mock_db(tmp_path):
    """Create a temporary database"""
    db_path = tmp_path / "test_music_library.db"
    db = MusicDatabase(str(db_path))
    db.create_all()
    return db

class TestDownloadManagerLogic:
    """Task 1 Verification: Smart Queueing"""

    def test_queue_download_skips_existing(self, mock_db):
        """Verify that queue_download skips tracks already in the library."""
        manager = DownloadManager()
        manager.db = mock_db

        # 1. Setup: Add "Track A" to the library
        with mock_db.session_scope() as session:
            artist = Artist(name="The Artist")
            session.add(artist)
            session.flush()

            track = Track(
                title="Track A",
                artist=artist,
                file_path="/music/The Artist/Track A.mp3"
            )
            session.add(track)
            session.commit()

        # 2. Action: Attempt to queue "Track A"
        track_to_download = SoulSyncTrack(
            raw_title="Track A",
            artist_name="The Artist",
            album_title="Some Album"
        )

        result_id = manager.queue_download(track_to_download)

        # 3. Assert: Result should be 0 (skipped) and queue size 0
        assert result_id == 0

        with mock_db.session_scope() as session:
            count = session.query(Download).count()
            assert count == 0

    def test_startup_purge_removes_existing(self, mock_db):
        """Verify that startup purge removes queued items that exist in library."""
        manager = DownloadManager()
        manager.db = mock_db

        # 1. Setup: Add "Track B" to library AND download queue
        track_obj = SoulSyncTrack(
            raw_title="Track B",
            artist_name="The Artist",
            album_title="Some Album"
        )

        with mock_db.session_scope() as session:
            artist = Artist(name="The Artist")
            session.add(artist)
            session.flush()

            # Library entry
            track = Track(
                title="Track B",
                artist=artist,
                file_path="/music/The Artist/Track B.mp3"
            )
            session.add(track)

            # Queue entry (simulating stale state)
            download = Download(
                soul_sync_track=track_obj.to_dict(),
                status="queued"
            )
            session.add(download)
            session.commit()

        # 2. Action: Run purge
        manager._purge_existing_tracks_from_queue()

        # 3. Assert: Queue should be empty
        with mock_db.session_scope() as session:
            count = session.query(Download).count()
            assert count == 0

class TestAutoImportLogic:
    """Task 2 Verification: Memory Leak Fix"""

    def test_is_path_ignored_db_query(self, mock_db):
        """Verify that _is_path_ignored queries the DB correctly."""
        # Need to patch get_database inside the service module because it uses a global accessor
        with patch('services.auto_importer.get_database', return_value=mock_db):
            from services.auto_importer import AutoImportService
            # Mock get_metadata_enhancer to avoid instantiation issues
            with patch('services.auto_importer.get_metadata_enhancer'):
                # Also mock config_manager to avoid directory errors in __init__
                with patch('services.auto_importer.config_manager') as mock_config:
                    mock_config.get_library_dir.return_value = Path("/tmp/lib")
                    # We only need the instance to call the method
                    service = AutoImportService.get_instance()

                    # 1. Setup: Add ignored file to ReviewTask
                    ignored_path = "/downloads/ignored_song.mp3"
                    with mock_db.session_scope() as session:
                        task = ReviewTask(
                            file_path=ignored_path,
                            status="ignored"
                        )
                        session.add(task)

                        # Add a pending task (should NOT be treated as ignored)
                        pending_path = "/downloads/pending_song.mp3"
                        task2 = ReviewTask(
                            file_path=pending_path,
                            status="pending"
                        )
                        session.add(task2)
                        session.commit()

                    # 2. Assertions
                    assert service._is_path_ignored(ignored_path) is True
                    assert service._is_path_ignored(pending_path) is False
                    assert service._is_path_ignored("/downloads/new_song.mp3") is False
