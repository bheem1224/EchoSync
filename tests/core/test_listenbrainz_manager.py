
import pytest
import sqlite3
from unittest.mock import MagicMock, patch, call
from core.listenbrainz_manager import ListenBrainzManager

# --- Mock Data and Fixtures ---

@pytest.fixture
def mock_lb_client():
    """Mocks the ListenBrainzClient."""
    with patch('core.listenbrainz_manager.ListenBrainzClient') as mock_client_class:
        mock_instance = MagicMock()
        mock_instance.is_authenticated.return_value = True
        
        # Sample playlist data
        mock_instance.get_playlists_created_for_user.return_value = [
            {"playlist": {"identifier": "mbid1", "title": "Weekly Mix", "creator": "LB", "track": [{"title": "t1"}]}}
        ]
        mock_instance.get_user_playlists.return_value = []
        mock_instance.get_collaborative_playlists.return_value = []

        mock_client_class.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_db_conn():
    """Mocks the sqlite3 connection and cursor."""
    with patch('sqlite3.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Default fetchone to return None (item doesn't exist)
        mock_cursor.fetchone.return_value = None
        # Default fetchall to return empty list
        mock_cursor.fetchall.return_value = []
        
        yield mock_conn, mock_cursor

@pytest.fixture
def lb_manager(mock_lb_client, mock_db_conn):
    """Provides a ListenBrainzManager instance with mocked dependencies."""
    return ListenBrainzManager(db_path=":memory:")

# --- Tests ---

def test_initialization(lb_manager):
    """Test that the manager initializes correctly."""
    assert lb_manager.client is not None
    assert lb_manager.db_path == ":memory:"

def test_update_all_playlists_unauthenticated(lb_manager, mock_lb_client):
    """Test that updates are skipped if the client is not authenticated."""
    mock_lb_client.is_authenticated.return_value = False
    
    result = lb_manager.update_all_playlists()
    
    assert result['success'] is False
    assert "Not authenticated" in result['error']
    mock_lb_client.get_playlists_created_for_user.assert_not_called()

def test_update_all_playlists_success(lb_manager, mock_lb_client, mock_db_conn):
    """Test a successful run of updating all playlist types."""
    # Mock the internal methods to isolate the test to this function's logic
    with patch.object(lb_manager, '_update_playlist', return_value="new") as mock_update, \
         patch.object(lb_manager, '_cleanup_old_playlists') as mock_cleanup:
        
        result = lb_manager.update_all_playlists()

        assert result['success'] is True
        # Check that the fetch functions were called
        mock_lb_client.get_playlists_created_for_user.assert_called_once()
        mock_lb_client.get_user_playlists.assert_called_once()
        mock_lb_client.get_collaborative_playlists.assert_called_once()

        # Check that _update_playlist was called for the one playlist we provided
        mock_update.assert_called_once()
        
        # Check that cleanup was called at the end
        mock_cleanup.assert_called_once()

        # Check summary
        assert result['summary']['created_for']['new'] == 1

def test_update_playlist_new(lb_manager, mock_db_conn):
    """Test adding a brand new playlist to the database."""
    mock_conn, mock_cursor = mock_db_conn
    mock_cursor.fetchone.return_value = None # Playlist does not exist
    
    playlist_data = {"playlist": {"identifier": "mbid_new", "title": "New", "track": [{"title": "t1"}]}}
    
    with patch.object(lb_manager, '_cache_tracks') as mock_cache_tracks:
        result = lb_manager._update_playlist(playlist_data, "user")
        
        assert result == "new"
        # Verify an INSERT was performed
        insert_call = next((c for c in mock_cursor.execute.call_args_list if "INSERT INTO listenbrainz_playlists" in c.args[0]), None)
        assert insert_call is not None
        assert insert_call.args[1] == ("mbid_new", "New", "ListenBrainz", "user", 1, '{}')
        
        # Verify tracks were cached
        mock_cache_tracks.assert_called_once()
        mock_conn.commit.assert_called_once()

def test_update_playlist_updated(lb_manager, mock_db_conn):
    """Test updating an existing playlist that has a different track count."""
    mock_conn, mock_cursor = mock_db_conn
    # Playlist exists with 1 track, but the new data has 2 tracks
    mock_cursor.fetchone.return_value = (1, 1, "2023-01-01") # db_id, track_count, last_updated
    
    playlist_data = {"playlist": {"identifier": "mbid_upd", "title": "Updated", "track": [{"title": "t1"}, {"title": "t2"}]}}
    
    with patch.object(lb_manager, '_cache_tracks') as mock_cache_tracks:
        result = lb_manager._update_playlist(playlist_data, "user")
        
        assert result == "updated"
        # Verify old tracks were deleted
        mock_cursor.execute.assert_any_call("DELETE FROM listenbrainz_tracks WHERE playlist_id = ?", (1,))
        # Verify an UPDATE was performed on the playlist
        update_call = next((c for c in mock_cursor.execute.call_args_list if "UPDATE listenbrainz_playlists" in c.args[0]), None)
        assert update_call is not None
        assert update_call.args[1] == ("Updated", "ListenBrainz", 2, 1)

        mock_cache_tracks.assert_called_once()
        mock_conn.commit.assert_called_once()

def test_update_playlist_skipped(lb_manager, mock_db_conn):
    """Test skipping an existing playlist with the same track count."""
    mock_conn, mock_cursor = mock_db_conn
    # Playlist exists with 1 track, and new data also has 1 track
    mock_cursor.fetchone.return_value = (1, 1, "2023-01-01")
    
    playlist_data = {"playlist": {"identifier": "mbid_skip", "title": "Skipped", "track": [{"title": "t1"}]}}
    
    with patch.object(lb_manager, '_cache_tracks') as mock_cache_tracks:
        result = lb_manager._update_playlist(playlist_data, "user")
        
        assert result == "skipped"
        # Verify the DB was not modified
        assert not any("UPDATE" in c.args[0] for c in mock_cursor.execute.call_args_list)
        assert not any("DELETE" in c.args[0] for c in mock_cursor.execute.call_args_list)
        mock_cache_tracks.assert_not_called()
        mock_conn.commit.assert_not_called()

def test_fetch_cover_art_parallel(lb_manager):
    """Test the parallel fetching of cover art URLs."""
    # Mock HttpClient to avoid actual network calls
    mock_http = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "images": [{"front": True, "thumbnails": {"small": "http://example.com/cover.jpg"}}]
    }
    mock_http.get.return_value = mock_response

    # Sample track data list
    track_data_list = [
        {'position': 0, 'release_mbid': 'release1', 'album_cover_url': None},
        {'position': 1, 'release_mbid': None, 'album_cover_url': None}, # No release MBID
        {'position': 2, 'release_mbid': 'release2', 'album_cover_url': None},
    ]

    # Patch HttpClient constructor to return our mock (patch at the import location)
    with patch('sdk.http_client.HttpClient', return_value=mock_http):
        lb_manager._fetch_cover_art_parallel(track_data_list)
    
    # Should have been called twice (for the two tracks with release_mbid)
    assert mock_http.get.call_count == 2
    mock_http.get.assert_any_call("https://coverartarchive.org/release/release1", timeout=3)
    mock_http.get.assert_any_call("https://coverartarchive.org/release/release2", timeout=3)
    
    # Check that the URLs were updated in the list
    assert track_data_list[0]['album_cover_url'] == "http://example.com/cover.jpg"
    assert track_data_list[1]['album_cover_url'] is None
    assert track_data_list[2]['album_cover_url'] == "http://example.com/cover.jpg"

def test_cleanup_old_playlists(lb_manager, mock_db_conn):
    """Test that old playlists are correctly cleaned up."""
    mock_conn, mock_cursor = mock_db_conn
    # Simulate finding 5 old playlist IDs to delete for the 'created_for' type
    mock_cursor.fetchall.return_value = [(10,), (9,), (8,), (7,), (6,)]

    lb_manager._cleanup_old_playlists()
    
    # Verify the SELECT query to find old playlists was run for each type
    assert mock_cursor.execute.call_count >= 3
    
    # Verify the DELETE queries were run for the found IDs
    placeholders = '?,?,?,?,?'
    mock_cursor.execute.assert_any_call(f"DELETE FROM listenbrainz_tracks WHERE playlist_id IN ({placeholders})", [10, 9, 8, 7, 6])
    mock_cursor.execute.assert_any_call(f"DELETE FROM listenbrainz_playlists WHERE id IN ({placeholders})", [10, 9, 8, 7, 6])
    
    mock_conn.commit.assert_called_once()
