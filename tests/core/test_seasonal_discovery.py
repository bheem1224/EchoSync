
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from core.seasonal_discovery import SeasonalDiscoveryService, SEASONAL_CONFIG

# --- Mock Data and Fixtures ---

class MockDatabase:
    def __init__(self):
        self.conn = MagicMock()
        # Make the mocked connection usable as a context manager
        self.conn.__enter__.return_value = self.conn
        self.conn.__exit__.return_value = False
        self.cursor = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.cursor.fetchone.return_value = None
        self.cursor.fetchall.return_value = []
        # Make get_watchlist_artists a MagicMock so tests can set return_value easily
        self.get_watchlist_artists = MagicMock(return_value=[])

    def _get_connection(self):
        # Return a context manager whose __enter__ returns the mocked connection
        class Ctx:
            def __init__(self, conn):
                self._conn = conn
            def __enter__(self):
                return self._conn
            def __exit__(self, exc_type, exc, tb):
                return False

        return Ctx(self.conn)

    def get_watchlist_artists(self):
        # Default to empty list; tests may patch this to return values
        return []

@pytest.fixture
def mock_db():
    return MockDatabase()

@pytest.fixture
def mock_spotify_client():
    client = MagicMock()
    client.is_authenticated.return_value = True
    return client

@pytest.fixture
def service(mock_spotify_client, mock_db):
    """Provides a SeasonalDiscoveryService instance with mocked dependencies."""
    return SeasonalDiscoveryService(spotify_client=mock_spotify_client, database=mock_db)

# --- Tests ---

def test_initialization_and_schema_creation(mock_spotify_client):
    """Test that the database schema is created on initialization."""
    mock_db_instance = MockDatabase()
    # Don't patch the whole class, just the get_connection method
    with patch.object(mock_db_instance, '_get_connection') as mock_get_conn:
        mock_get_conn.return_value = mock_db_instance.conn
        
        service = SeasonalDiscoveryService(spotify_client=mock_spotify_client, database=mock_db_instance)
        
        # Verify that CREATE TABLE was called for all seasonal tables
        execute_calls = service.database.cursor.execute.call_args_list
        sql_statements = " ".join([call.args[0] for call in execute_calls])
        
        assert "CREATE TABLE IF NOT EXISTS seasonal_albums" in sql_statements
        assert "CREATE TABLE IF NOT EXISTS seasonal_tracks" in sql_statements
        assert "CREATE TABLE IF NOT EXISTS curated_seasonal_playlists" in sql_statements
        assert "CREATE TABLE IF NOT EXISTS seasonal_metadata" in sql_statements
        assert service.database.conn.commit.called

@pytest.mark.parametrize("month,expected_season", [
    (10, "halloween"), # October -> Halloween (priority over autumn)
    (12, "christmas"), # December -> Christmas
    (2, "valentines"), # February -> Valentines
    (7, "summer"),     # July -> Summer
    (1, None),         # January -> No season
])
@patch('core.seasonal_discovery.datetime')
def test_get_current_season(mock_datetime, service, month, expected_season):
    """Test that the correct season is identified for a given month."""
    mock_datetime.now.return_value = datetime(2023, month, 15)
    assert service.get_current_season() == expected_season

@patch('core.seasonal_discovery.datetime')
def test_get_all_active_seasons(mock_datetime, service):
    """Test getting all active seasons, e.g., in October."""
    mock_datetime.now.return_value = datetime(2023, 10, 15) # October
    seasons = service.get_all_active_seasons()
    assert "halloween" in seasons
    assert "autumn" in seasons

def test_should_populate_content_no_data(service, mock_db):
    """Test should_populate returns True when there's no metadata."""
    mock_db.cursor.fetchone.return_value = None
    assert service.should_populate_seasonal_content("christmas") is True

@patch('core.seasonal_discovery.datetime')
def test_should_populate_content_recently_populated(mock_dt, service, mock_db):
    """Test should_populate returns False if populated recently."""
    # Simulate now being Oct 10, 2023 and last populated on Oct 8, 2023
    now = datetime(2023, 10, 10)
    last_populated = datetime(2023, 10, 8).isoformat()
    mock_dt.now.return_value = now
    mock_db.cursor.fetchone.return_value = {'last_populated_at': last_populated}

    assert service.should_populate_seasonal_content("halloween", days_threshold=7) is False

@patch('core.seasonal_discovery.datetime')
def test_should_populate_content_stale_data(mock_dt, service, mock_db):
    """Test should_populate returns True if data is stale."""
    now = datetime(2023, 10, 20)
    last_populated = datetime(2023, 10, 1).isoformat()
    mock_dt.now.return_value = now
    mock_db.cursor.fetchone.return_value = {'last_populated_at': last_populated}

    assert service.should_populate_seasonal_content("halloween", days_threshold=7) is True

def test_populate_seasonal_content_orchestration(service: SeasonalDiscoveryService):
    """Test that the main populate method calls its helpers."""
    with patch.object(service, '_clear_seasonal_content') as mock_clear, \
         patch.object(service, '_search_discovery_pool_seasonal', return_value=[]) as mock_search_pool, \
         patch.object(service, '_search_watchlist_seasonal_albums', return_value=[]) as mock_search_watchlist, \
         patch.object(service, '_search_spotify_seasonal_albums', return_value=[]) as mock_search_spotify, \
         patch.object(service, '_update_seasonal_metadata') as mock_update_meta:
        
        service.populate_seasonal_content("christmas")

        mock_clear.assert_called_once_with("christmas")
        mock_search_pool.assert_called_once_with("christmas")
        mock_search_watchlist.assert_called_once_with("christmas")
        mock_search_spotify.assert_called_once_with("christmas", limit=50)
        mock_update_meta.assert_called_once()

def test_search_discovery_pool_seasonal(service: SeasonalDiscoveryService, mock_db):
    """Test searching the discovery pool with seasonal keywords."""
    season_key = "halloween"
    keywords = SEASONAL_CONFIG[season_key]['keywords']
    
    # Clear any initialization-related execute calls so we only assert on the search
    mock_db.cursor.execute.reset_mock()

    service._search_discovery_pool_seasonal(season_key)
    
    mock_db.cursor.execute.assert_called_once()
    sql, params = mock_db.cursor.execute.call_args[0]
    
    # Check that the query contains LIKE clauses for the keywords
    for keyword in keywords:
        assert f"LOWER(track_name) LIKE ?" in sql or f"LOWER(album_name) LIKE ?" in sql
    # Check that the params match the keywords
    assert len(params) == len(keywords) * 2
    assert f"%{keywords[0]}%" in params
    
def test_search_watchlist_seasonal_albums(service: SeasonalDiscoveryService, mock_db, mock_spotify_client):
    """Test searching for seasonal albums from watchlist artists."""
    mock_db.get_watchlist_artists.return_value = [MagicMock(spotify_artist_id="artist1", artist_name="Artist One")]
    
    # Mock Spotify client to return one matching and one non-matching album
    mock_album_match = MagicMock(id='album1', name="An Album for Christmas", artists=[{'name':'Artist One'}])
    mock_album_no_match = MagicMock(id='album2', name="A Normal Album", artists=[{'name':'Artist One'}])
    mock_spotify_client.get_artist_albums.return_value = [mock_album_match, mock_album_no_match]
    
    albums = service._search_watchlist_seasonal_albums("christmas")
    
    assert len(albums) == 1
    assert albums[0]['album_name'] == "An Album for Christmas"
    mock_spotify_client.get_artist_albums.assert_called_once_with("artist1", album_type='album,single,ep', limit=50)

def test_curate_seasonal_playlist(service: SeasonalDiscoveryService, mock_db, mock_spotify_client):
    """Test the curation logic for creating a balanced seasonal playlist."""
    season_key = "christmas"
    
    # Mock DB to return some tracks and albums
    mock_db.cursor.fetchall.side_effect = [
        [{"track_name": "DB Track 1", "artist_name": "Artist A", "popularity": 80, "spotify_track_id": "db1"}], # Tracks from seasonal_tracks
        [{"album_name": "Christmas Album", "artist_name": "Artist B", "popularity": 70, "spotify_album_id": "album1"}], # Albums from seasonal_albums
    ]
    
    # Mock Spotify to return tracks for the album
    mock_spotify_client.get_album.return_value = {
        "id": "album1", "tracks": {"items": [
            {"id": "spotify1", "name": "Spotify Track 1", "artists": [{"name": "Artist B"}], "popularity": 75},
            {"id": "spotify2", "name": "Spotify Track 2", "artists": [{"name": "Artist C"}], "popularity": 30}, # Deep cut
        ]}
    }
    
    with patch.object(service, '_save_curated_playlist') as mock_save:
        service.curate_seasonal_playlist(season_key)
        
        # Verify it tries to save the curated playlist
        mock_save.assert_called_once()
        saved_track_ids = mock_save.call_args[0][1]
        
        # Check that tracks from both sources are included
        assert "db1" in saved_track_ids
        assert "spotify1" in saved_track_ids
        assert "spotify2" in saved_track_ids
        
        # Check that the size is correct (or at least attempted)
        assert len(saved_track_ids) <= SEASONAL_CONFIG[season_key]['playlist_size']
