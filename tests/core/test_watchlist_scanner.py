
import pytest

pytestmark = pytest.mark.skip(reason="Watchlist scanner depends on incomplete musicmap service")

from unittest.mock import MagicMock, patch, ANY
from datetime import datetime, timedelta, timezone
from core.watchlist_scanner import WatchlistScanner, ScanResult, clean_track_name_for_search
from providers.spotify.client import SpotifyClient
from database.music_database import WatchlistArtist

# --- Helper Function Tests ---

def test_clean_track_name_for_search():
    assert clean_track_name_for_search("Song Title (Explicit)") == "Song Title"
    assert clean_track_name_for_search("Song Title (feat. Some Guy)") == "Song Title"
    assert clean_track_name_for_search("Song Title (Radio Edit)") == "Song Title"
    # Should keep important version info
    assert clean_track_name_for_search("Song Title (Remix)") == "Song Title (Remix)"
    assert clean_track_name_for_search("Song Title (Acoustic)") == "Song Title (Acoustic)"
    assert clean_track_name_for_search("Song Title - Live") == "Song Title - Live"

# --- Fixtures ---

@pytest.fixture
def mock_spotify_client():
    client = MagicMock(spec=SpotifyClient)
    client.is_authenticated.return_value = True
    return client

@pytest.fixture
def mock_db():
    db = MagicMock()
    # Default to track not existing
    db.check_track_exists.return_value = (None, 0.0) 
    # Default to successful add
    db.add_to_wishlist.return_value = True
    return db

@pytest.fixture
def scanner(mock_spotify_client, mock_db):
    """Provides a WatchlistScanner instance with mocked dependencies."""
    # We can patch the properties to inject our mocks
    with patch.object(WatchlistScanner, 'database', new=mock_db), \
         patch.object(WatchlistScanner, 'wishlist_service', new=MagicMock()), \
         patch.object(WatchlistScanner, 'matching_engine', new=MagicMock()):
        s = WatchlistScanner(spotify_client=mock_spotify_client)
        yield s

# --- WatchlistScanner Tests ---

def test_scan_artist_new_release(scanner: WatchlistScanner, mock_spotify_client, mock_db):
    """Test scanning an artist and finding a new track."""
    # 1. Setup Mocks
    artist_to_scan = MagicMock()
    artist_to_scan.id = 1
    artist_to_scan.spotify_artist_id = "artist1"
    artist_to_scan.artist_name = "Artist One"
    artist_to_scan.last_scan_timestamp = None
    artist_to_scan.include_albums = True
    artist_to_scan.include_eps = True
    artist_to_scan.include_singles = True
    # Mock Spotify to return a new album and its tracks
    mock_album = MagicMock(id='album1', name='New Album', release_date='2025-12-14')
    mock_spotify_client.get_artist_albums.return_value = [mock_album]
    mock_spotify_client.get_album.return_value = {
        "id": "album1", "name": "New Album", "tracks": {"items": [{"id": "track1", "name": "New Song", "artists": [{"name": "Artist One"}]}]}
    }
    
    # 2. Call the method
    with patch('time.sleep'), \
         patch.object(scanner, '_get_lookback_period_setting', return_value='all'), \
         patch.object(scanner.matching_engine, 'clean_title', return_value='New Song'):
        result = scanner.scan_artist(artist_to_scan)

    # 3. Assertions
    assert result.success is True
    assert result.new_tracks_found == 1
    assert result.tracks_added_to_wishlist == 1
    
    # Verify DB calls
    mock_db.check_track_exists.assert_called_once()
    mock_db.add_to_wishlist.assert_called_once()
    mock_db.update_artist_scan_timestamp.assert_called_once_with("artist1")

def test_scan_artist_track_exists(scanner: WatchlistScanner, mock_spotify_client, mock_db):
    """Test scanning an artist where the track already exists in the library."""
    artist_to_scan = MagicMock()
    artist_to_scan.id = 1
    artist_to_scan.spotify_artist_id = "artist1"
    artist_to_scan.artist_name = "Artist One"
    artist_to_scan.last_scan_timestamp = None
    artist_to_scan.include_albums = True
    artist_to_scan.include_eps = True
    artist_to_scan.include_singles = True
    mock_album = MagicMock(id='album1', name='Existing Album', release_date='2025-01-01')
    mock_spotify_client.get_artist_albums.return_value = [mock_album]
    mock_spotify_client.get_album.return_value = {
        "id": "album1", "name": "Existing Album", "tracks": {"items": [{"id": "track1", "name": "Existing Song", "artists": [{"name": "Artist One"}]}]}
    }
    # Mock DB to say the track EXISTS
    mock_db.check_track_exists.return_value = (MagicMock(), 0.95)

    with patch('time.sleep'):
        result = scanner.scan_artist(artist_to_scan)
        
    assert result.success is True
    assert result.new_tracks_found == 0
    assert result.tracks_added_to_wishlist == 0
    # Wishlist should not be called if track exists
    mock_db.add_to_wishlist.assert_not_called()

def test_scan_artist_skips_by_release_type(scanner: WatchlistScanner, mock_spotify_client, mock_db):
    """Test that releases are skipped based on user preferences."""
    # User does NOT want singles
    artist_to_scan = MagicMock()
    artist_to_scan.id = 1
    artist_to_scan.spotify_artist_id = "artist1"
    artist_to_scan.artist_name = "Artist One"
    artist_to_scan.last_scan_timestamp = None
    artist_to_scan.include_albums = True
    artist_to_scan.include_eps = True
    artist_to_scan.include_singles = False
    
    # This is a single (1 track)
    mock_single = MagicMock(id='single1', name='New Single', release_date='2025-10-10')
    mock_spotify_client.get_artist_albums.return_value = [mock_single]
    mock_spotify_client.get_album.return_value = {
        "id": "single1", "name": "New Single", "tracks": {"items": [{"id": "track1", "name": "A-Side"}]}
    }

    with patch('time.sleep'):
        result = scanner.scan_artist(artist_to_scan)
        
    assert result.success is True
    # No new tracks should be "found" because the release was skipped
    assert result.new_tracks_found == 0
    mock_db.check_track_exists.assert_not_called()

def test_is_album_after_timestamp(scanner: WatchlistScanner):
    """Test the date comparison logic for filtering releases."""
    cutoff = datetime(2023, 6, 1, tzinfo=timezone.utc)
    
    # Album with full date string
    album_new = MagicMock(release_date='2023-07-01')
    assert scanner.is_album_after_timestamp(album_new, cutoff) is True
    
    album_old = MagicMock(release_date='2023-05-31')
    assert scanner.is_album_after_timestamp(album_old, cutoff) is False
    
    # Album with year-month string
    album_new_month = MagicMock(release_date='2023-06')
    # Treated as 2023-06-01, which is not > 2023-06-01, but we can test the boundary
    assert scanner.is_album_after_timestamp(album_new_month, datetime(2023, 5, 31, tzinfo=timezone.utc)) is True
    
    # Album with year only
    album_new_year = MagicMock(release_date='2024')
    assert scanner.is_album_after_timestamp(album_new_year, cutoff) is True
    
    album_old_year = MagicMock(release_date='2022')
    assert scanner.is_album_after_timestamp(album_old_year, cutoff) is False

def test_scan_all_artists_smart_selection(scanner: WatchlistScanner, mock_db):
    """Test the smart selection logic for scanning artists."""
    seven_days_ago = datetime.now() - timedelta(days=7)
    eight_days_ago = datetime.now() - timedelta(days=8)
    one_day_ago = datetime.now() - timedelta(days=1)
    
    artists = []
    a1 = MagicMock(); a1.id = 1; a1.spotify_artist_id = 'a1'; a1.artist_name = 'Must Scan 1 (Old)'; a1.last_scan_timestamp = eight_days_ago
    a2 = MagicMock(); a2.id = 2; a2.spotify_artist_id = 'a2'; a2.artist_name = 'Must Scan 2 (Never)'; a2.last_scan_timestamp = None
    a3 = MagicMock(); a3.id = 3; a3.spotify_artist_id = 'a3'; a3.artist_name = 'Can Skip 1'; a3.last_scan_timestamp = one_day_ago
    a4 = MagicMock(); a4.id = 4; a4.spotify_artist_id = 'a4'; a4.artist_name = 'Can Skip 2'; a4.last_scan_timestamp = one_day_ago
    artists.extend([a1, a2, a3, a4])
    mock_db.get_watchlist_artists.return_value = artists
    
    # Mock the actual scanning part
    with patch.object(scanner, 'scan_artist') as mock_scan_artist, \
         patch('time.sleep'), \
         patch.object(scanner, 'populate_discovery_pool'), \
         patch.object(scanner, '_populate_seasonal_content'):
        
        # Limit to 3 artists total for this scan
        with patch.object(scanner, 'MAX_ARTISTS_PER_SCAN', 3):
             scanner.scan_all_watchlist_artists()

    assert mock_scan_artist.call_count == 3
    
    scanned_artist_names = [call.args[0].artist_name for call in mock_scan_artist.call_args_list]
    
    # The two "must scan" artists must be in the list
    assert "Must Scan 1 (Old)" in scanned_artist_names
    assert "Must Scan 2 (Never)" in scanned_artist_names
    # The third one is a random choice from the "can skip" list
    assert "Can Skip 1" in scanned_artist_names or "Can Skip 2" in scanned_artist_names

def test_fetch_similar_artists_from_musicmap(scanner: WatchlistScanner, mock_spotify_client):
    """Test scraping music-map.com and matching to Spotify."""
    # Mock the HTML response from music-map
    mock_html = """
    <html><body><div id="gnodMap">
        <a href="//www.music-map.com/some+artist.html">Some Artist</a>
        <a href="//www.music-map.com/similar+one.html">Similar One</a>
        <a href="//www.music-map.com/similar+two.html">Similar Two</a>
    </div></body></html>
    """
    
    # Mock the HttpClient get method
    mock_response = MagicMock(status_code=200, text=mock_html)
    mock_response.raise_for_status.return_value = None
    
    # Create and inject mock HttpClient
    mock_http = MagicMock()
    mock_http.get.return_value = mock_response
    scanner._http_musicmap = mock_http

    # Mock Spotify search to return matches for the scraped names
    # Return objects where .id and .name are plain attributes (not mock internals)
    m0 = MagicMock(); m0.id = 'searched_artist_id';
    m1 = MagicMock(); m1.id = 'sim1'; m1.name = 'Similar One'
    m2 = MagicMock(); m2.id = 'sim2'; m2.name = 'Similar Two'
    mock_spotify_client.search_artists.side_effect = [[m0], [m1], [m2]]
    
    similar_artists = scanner._fetch_similar_artists_from_musicmap("Some Artist")

    assert len(similar_artists) == 2
    assert similar_artists[0]['name'] == 'Similar One'
    assert similar_artists[1]['id'] == 'sim2'
    
    # Verify music-map was called
    from unittest.mock import ANY
    mock_http.get.assert_called_once_with('https://www.music-map.com/some+artist', headers=ANY)
