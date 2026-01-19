import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from services.download_manager import DownloadManager
from core.matching_engine.soul_sync_track import SoulSyncTrack
from datetime import datetime

@pytest.fixture
def mock_db():
    with patch('services.download_manager.get_database') as mock:
        db_instance = MagicMock()
        session = MagicMock()
        db_instance.session_scope.return_value.__enter__.return_value = session
        mock.return_value = db_instance
        yield db_instance, session

@pytest.fixture
def mock_provider():
    with patch('core.provider.ProviderRegistry.create_instance') as mock:
        provider = AsyncMock()
        mock.return_value = provider
        yield provider

@pytest.fixture
def mock_matcher():
    with patch('services.download_manager.WeightedMatchingEngine') as mock:
        matcher = MagicMock()
        mock.return_value = matcher
        yield matcher

@pytest.fixture
def download_manager(mock_db, mock_provider, mock_matcher):
    # Reset singleton
    DownloadManager._instance = None
    dm = DownloadManager.get_instance()
    # Mock internal components
    dm.db = mock_db[0]
    dm._provider = mock_provider
    dm.matcher = mock_matcher
    return dm

def test_queue_download(download_manager, mock_db):
    _, session = mock_db
    track = SoulSyncTrack(raw_title="Test Track", artist_name="Test Artist", album_title="Test Album")

    # Mock DB behavior
    mock_download_obj = MagicMock()
    mock_download_obj.id = 123
    # When session.add is called, we don't return anything, but we can inspect calls

    # We need to mock session.add to set the id on the object if possible,
    # but DownloadManager just reads .id from the object passed to add.
    # So we can't easily mock the ID generation without a real DB or more complex mocking.
    # However, we can verify the call.

    # Let's mock the Download constructor or verify add is called.
    with patch('services.download_manager.Download') as MockDownload:
        # Configure the mock to accept kwargs and set them as attributes (simplified)
        def download_side_effect(**kwargs):
            m = MagicMock()
            m.id = 123
            for k, v in kwargs.items():
                setattr(m, k, v)
            return m

        MockDownload.side_effect = download_side_effect

        dl_id = download_manager.queue_download(track)

        assert dl_id == 123
        # Capture the object passed to add
        added_obj = session.add.call_args[0][0]
        assert added_obj.id == 123
        assert added_obj.status == "queued"

@pytest.mark.asyncio
async def test_process_queue_success(download_manager, mock_db, mock_provider, mock_matcher):
    db, session = mock_db

    # Setup queued item
    mock_download = MagicMock()
    mock_download.id = 1
    mock_download.status = "queued"
    mock_download.soul_sync_track = {
        "raw_title": "Song", "artist_name": "Artist", "album_title": "Album"
    }

    # Mock query flow for _process_queued_items
    # First query finds queued items
    session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_download]

    # Mock query flow for _execute_search_and_download (reloads item)
    # We need to handle multiple calls to session.query().get()
    session.query.return_value.get.return_value = mock_download

    # Mock provider search result
    candidate = SoulSyncTrack(raw_title="Song.mp3", artist_name="Artist", album_title="")
    candidate.identifiers = {'username': 'user', 'provider_item_id': 'file.mp3', 'size': 100}
    mock_provider._async_search.return_value = [candidate]

    # Mock matching
    mock_matcher.select_best_download_candidate.return_value = candidate

    # Mock download
    mock_provider._async_download.return_value = "remote_id_123"

    # Run
    await download_manager._process_queued_items()

    # Verify
    mock_provider._async_search.assert_called_once()
    mock_matcher.select_best_download_candidate.assert_called_once()
    mock_provider._async_download.assert_called_once_with('user', 'file.mp3', 100)

    # Status update verification (complex due to mock chaining)
    # The manager calls self._update_status which does a DB lookup
    assert mock_download.status == "downloading"
    assert mock_download.provider_id == "remote_id_123"

@pytest.mark.asyncio
async def test_check_active_downloads(download_manager, mock_db, mock_provider):
    _, session = mock_db

    # Setup active item
    mock_download = MagicMock()
    mock_download.id = 1
    mock_download.status = "downloading"
    mock_download.provider_id = "remote_id_123"

    session.query.return_value.filter.return_value.all.return_value = [mock_download]
    session.query.return_value.get.return_value = mock_download

    # Mock provider status
    mock_provider._async_get_download_status.return_value = {
        'id': 'remote_id_123',
        'status': 'complete'
    }

    await download_manager._check_active_downloads()

    assert mock_download.status == "completed"
