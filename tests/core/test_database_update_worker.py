
import pytest
from unittest.mock import MagicMock, patch, call
from core.database_update_worker import DatabaseUpdateWorker, DatabaseStatsWorker

# Since the worker can run without PyQt6, we can test the core logic.
# We'll mock the QThread parts we don't need.

# --- Mocks for Dependencies ---

class MockMediaClient:
    def __init__(self, server_type="plex"):
        self.__class__.__name__ = f"{server_type}Client"
        self.server_type = server_type
        self.ensure_connection = MagicMock(return_value=True)
        self.get_all_artists = MagicMock(return_value=[])
        self.get_recently_added_albums = MagicMock(return_value=[])
        self.get_recently_updated_albums = MagicMock(return_value=[])
        self.clear_cache = MagicMock()
        
        # Mock artists, albums, tracks
        self.mock_artist = MagicMock(ratingKey='artist1', title='Artist One')
        self.mock_album = MagicMock(ratingKey='album1', title='Album One', artist=lambda: self.mock_artist)
        self.mock_track = MagicMock(ratingKey='track1', title='Track One', album=lambda: self.mock_album, artist=lambda: self.mock_artist)
        
        self.mock_album.tracks.return_value = [self.mock_track]
        self.mock_artist.albums.return_value = [self.mock_album]
        self.get_all_artists.return_value = [self.mock_artist]
        # Provide a Plex-specific recent albums helper so tests can patch or call it
        def _get_recent_albums_plex():
            return self.get_recently_added_albums()

        self._get_recent_albums_plex = _get_recent_albums_plex

class MockMusicDatabase:
    def __init__(self):
        self.clear_server_data = MagicMock()
        self.insert_or_update_media_artist = MagicMock(return_value=True)
        self.insert_or_update_media_album = MagicMock(return_value=True)
        self.insert_or_update_media_track = MagicMock(return_value=True)
        self.track_exists_by_server = MagicMock(return_value=False)
        self.get_database_info_for_server = MagicMock(return_value={'tracks': 500}) # Assume enough tracks for incremental
        self.record_full_refresh_completion = MagicMock()
        self.cleanup_orphaned_records = MagicMock()

@pytest.fixture
def mock_db():
    return MockMusicDatabase()

@pytest.fixture
def mock_plex_client():
    return MockMediaClient(server_type="plex")

@pytest.fixture
def mock_jellyfin_client():
    return MockMediaClient(server_type="jellyfin")

# --- Fixtures for the Worker ---

@pytest.fixture
def db_worker(mock_plex_client, mock_db):
    # Patch the get_database function to return our mock db
    with patch('core.database_update_worker.get_database', return_value=mock_db):
        # The worker is initialized for headless mode, so we can test its core 'run' logic
        worker = DatabaseUpdateWorker(
            media_client=mock_plex_client,
            server_type='plex',
            full_refresh=True,
            force_sequential=True # Force sequential for easier testing
        )
        # Mock the signal emission
        worker._emit_signal = MagicMock()
        yield worker

# --- Tests ---

def test_initialization(db_worker, mock_plex_client):
    """Test that the worker initializes correctly."""
    assert db_worker.media_client == mock_plex_client
    assert db_worker.server_type == "plex"
    assert db_worker.full_refresh is True
    assert db_worker.force_sequential is True

def test_run_full_refresh(db_worker, mock_db, mock_plex_client):
    """Test the main logic flow for a full refresh."""
    db_worker.run()

    # 1. Check that the database was cleared
    mock_db.clear_server_data.assert_called_once_with("plex")
    
    # 2. Check that it tried to get all artists
    mock_plex_client.get_all_artists.assert_called_once()
    
    # 3. Check that artist, album, and track were processed and inserted
    mock_db.insert_or_update_media_artist.assert_called_once()
    mock_db.insert_or_update_media_album.assert_called_once()
    mock_db.insert_or_update_media_track.assert_called_once()
    
    # 4. Check that final signals were emitted with correct counts
    # It should call artist_processed and finished
    db_worker._emit_signal.assert_any_call('artist_processed', 'Artist One', True, 'Updated with 1 albums, 1 tracks', 1, 1)
    db_worker._emit_signal.assert_any_call('finished', 1, 1, 1, 1, 0)
    
    # 5. Check that full refresh completion was recorded
    mock_db.record_full_refresh_completion.assert_called_once()


def test_run_incremental_update(mock_plex_client, mock_db):
    """Test the main logic flow for an incremental (smart) update."""
    # Setup for incremental update
    mock_plex_client.get_recently_added_albums.return_value = [mock_plex_client.mock_album]
    mock_plex_client.music_library = MagicMock() # Plex client checks for this
    
    with patch('core.database_update_worker.get_database', return_value=mock_db):
        worker = DatabaseUpdateWorker(
            media_client=mock_plex_client,
            server_type='plex',
            full_refresh=False, # Incremental
            force_sequential=True
        )
        worker._emit_signal = MagicMock()

        # The mock track doesn't exist in the db, so it should be processed
        mock_db.track_exists_by_server.return_value = False

        worker.run()
        
        # Should not clear the database
        mock_db.clear_server_data.assert_not_called()
        
        # Should call a "recent" method, not get_all_artists
        mock_plex_client.get_all_artists.assert_not_called()
        
        # Should process the "new" content
        mock_db.insert_or_update_media_artist.assert_called_once()
        mock_db.insert_or_update_media_album.assert_called_once()
        mock_db.insert_or_update_media_track.assert_called_once()
        
        # Should emit finished signal
        worker._emit_signal.assert_any_call('finished', 1, 1, 1, 1, 0)

        # Should run cleanup at the end of incremental
        mock_db.cleanup_orphaned_records.assert_called_once()

def test_incremental_update_stops_early(mock_plex_client, mock_db):
    """Test the early-stopping logic in incremental updates."""
    # Create 30 mock albums that are "already processed"
    processed_albums = []
    for i in range(30):
        album = MagicMock(ratingKey=f'old_album_{i}', title=f'Old Album {i}')
        album.artist.return_value = MagicMock(ratingKey=f'old_artist_{i}')
        album.tracks.return_value = [MagicMock(ratingKey=f'old_track_{i}')]
        processed_albums.append(album)

    # All tracks will "exist" in the database
    mock_db.track_exists_by_server.return_value = True
    
    # Mock the Plex client to return these albums
    mock_plex_client.music_library = MagicMock()
    # The client method returns a generator in reality, so a list is fine for mock
    with patch.object(mock_plex_client, '_get_recent_albums_plex', return_value=processed_albums):
        with patch('core.database_update_worker.get_database', return_value=mock_db):
            worker = DatabaseUpdateWorker(
                media_client=mock_plex_client,
                server_type='plex',
                full_refresh=False,
                force_sequential=True
            )
            worker._emit_signal = MagicMock()
            
            worker.run()

    # Since it stopped early, no artists should have been processed
    mock_db.insert_or_update_media_artist.assert_not_called()
    
    # The finished signal should report 0s.
    worker._emit_signal.assert_any_call('finished', 0, 0, 0, 0, 0)

def test_run_jellyfin_fast_incremental(mock_jellyfin_client, mock_db):
    """Test the fast path for Jellyfin incremental updates using recent tracks."""
    # Jellyfin's recent tracks methods are called
    new_track = mock_jellyfin_client.mock_track
    mock_jellyfin_client.get_recently_added_tracks = MagicMock(return_value=[new_track])
    mock_jellyfin_client.get_recently_updated_tracks = MagicMock(return_value=[])

    # The track does not exist in the db
    mock_db.track_exists_by_server.return_value = False

    with patch('core.database_update_worker.get_database', return_value=mock_db):
        worker = DatabaseUpdateWorker(
            media_client=mock_jellyfin_client,
            server_type='jellyfin',
            full_refresh=False,
            force_sequential=True
        )
        worker._emit_signal = MagicMock()

        worker.run()
        
        # Verify the fast path was taken
        mock_jellyfin_client.get_recently_added_tracks.assert_called_once()
        # Verify it processes the artist/album/track from the new track
        mock_db.insert_or_update_media_artist.assert_called_once()
        mock_db.insert_or_update_media_album.assert_called_once()
        mock_db.insert_or_update_media_track.assert_called_once()

def test_stats_worker(mock_db):
    """Test the DatabaseStatsWorker."""
    with patch('core.database_update_worker.get_database', return_value=mock_db):
        stats_worker = DatabaseStatsWorker()
        stats_worker._emit_signal = MagicMock()
        
        stats_worker.run()

        mock_db.get_database_info_for_server.assert_called_once()
        stats_worker._emit_signal.assert_called_once_with('stats_updated', {'tracks': 500})
