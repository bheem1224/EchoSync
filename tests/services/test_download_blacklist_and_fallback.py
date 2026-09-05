from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from database.working_database import DownloadQueue
from plugins.EchoSync.slskd.client import SlskdProvider
from services.download_manager import DownloadManager


@pytest.mark.asyncio
async def test_slskd_composite_state_parsing():
    """Verify that SlskdProvider parses compound state strings correctly."""
    provider = SlskdProvider()
    provider.base_url = "http://localhost:5030"
    provider.download_path = Path("/downloads")

    # Mock _make_request response with composite status strings
    mock_transfers = {
        "alice": {
            "directories": [
                {
                    "directory": "/music",
                    "files": [
                        {
                            "filename": "track1.flac",
                            "state": "Completed, Succeeded",
                            "percentComplete": 100,
                            "size": 1000,
                        },
                        {
                            "filename": "track2.flac",
                            "state": "Completed, Errored",
                            "percentComplete": 10,
                            "size": 1000,
                        },
                        {
                            "filename": "track3.flac",
                            "state": "Completed, Rejected",
                            "percentComplete": 0,
                            "size": 1000,
                        },
                        {
                            "filename": "track4.flac",
                            "state": "Queued, QueuedRemotely",
                            "percentComplete": 0,
                            "size": 1000,
                        },
                        {
                            "filename": "track5.flac",
                            "state": "InProgress",
                            "percentComplete": 50,
                            "size": 1000,
                        },
                    ],
                }
            ]
        }
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_transfers

        # 1. Completed, Succeeded -> complete
        status1 = await provider._async_get_download_status("alice|track1.flac")
        assert status1 is not None
        assert status1["status"] == "complete"

        # 2. Completed, Errored -> failed
        status2 = await provider._async_get_download_status("alice|track2.flac")
        assert status2 is not None
        assert status2["status"] == "failed"

        # 3. Completed, Rejected -> failed
        status3 = await provider._async_get_download_status("alice|track3.flac")
        assert status3 is not None
        assert status3["status"] == "failed"

        # 4. Queued, QueuedRemotely -> queued
        status4 = await provider._async_get_download_status("alice|track4.flac")
        assert status4 is not None
        assert status4["status"] == "queued"

        # 5. InProgress -> downloading
        status5 = await provider._async_get_download_status("alice|track5.flac")
        assert status5 is not None
        assert status5["status"] == "downloading"


@pytest.mark.asyncio
async def test_slskd_cancel_download():
    """Verify that _async_cancel_download correctly calls DELETE endpoints."""
    provider = SlskdProvider()
    provider.base_url = "http://localhost:5030"

    mock_transfers = {
        "alice": {
            "directories": [
                {
                    "directory": "/music",
                    "files": [{"id": "file-123", "filename": "song.flac"}],
                }
            ]
        }
    }

    with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_transfers

        success = await provider._async_cancel_download("alice|song.flac")
        assert success is True
        # Check DELETE transfers/downloads/alice/file-123 was called
        mock_req.assert_any_call("DELETE", "transfers/downloads/alice/file-123")


@pytest.mark.asyncio
async def test_ghost_transfer_fallback_and_blacklist(mock_work_db, mock_db):
    """Verify that a disappeared/ghost transfer triggers failure handling and candidate blacklisting."""
    dm = DownloadManager.get_instance()
    dm.work_db = mock_work_db
    dm.db = mock_db

    # Create initial queued download item
    with mock_work_db.session_scope() as session:
        item = DownloadQueue(
            sync_id="test1234",
            echo_sync_track={
                "sync_id": "test1234",
                "raw_title": "Test Title",
                "artist_name": "Test Artist",
                "album_title": "Test Album",
                "duration": 200000,
                "media": [],
            },
            status="downloading",
            provider_id="peer1|test.flac",
        )
        session.add(item)
        session.flush()
        db_id = item.id

    mock_provider = MagicMock()
    mock_provider.name = "EchoSync.slskd"
    mock_provider._async_get_download_status = AsyncMock(
        return_value=None
    )  # Disappeared
    mock_provider._async_cancel_download = AsyncMock(return_value=True)

    with patch.object(
        dm, "_get_active_download_providers", return_value=[mock_provider]
    ):
        with patch.object(
            dm, "_execute_waterfall_search_and_download", new_callable=AsyncMock
        ) as mock_waterfall:
            await dm._check_active_downloads()

            # Verify cancellation was called
            mock_provider._async_cancel_download.assert_called_once_with(
                "peer1|test.flac"
            )

            # Verify DB record updated: status="searching", blacklist updated
            with mock_work_db.session_scope() as session:
                refreshed = session.query(DownloadQueue).get(db_id)
                assert refreshed is not None
                assert refreshed.status == "searching"
                assert refreshed.provider_id is None
                blacklist = refreshed.echo_sync_track.get("blacklisted_candidates", [])
                assert "peer1|test.flac" in blacklist
                assert "test.flac" in blacklist
