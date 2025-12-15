
import pytest
from unittest.mock import MagicMock, patch, call
from core.jellyfin_client import JellyfinClient, JellyfinArtist, JellyfinAlbum, JellyfinTrack
import requests

# --- Sample Jellyfin API Responses ---

SAMPLE_CONFIG = {
    'base_url': 'http://jellyfin.test',
    'api_key': 'test_api_key'
}

SAMPLE_SYSTEM_INFO = {'ServerName': 'TestJellyfin'}
SAMPLE_USERS = [{'Id': 'user1', 'Name': 'Test User'}]
SAMPLE_VIEWS = {'Items': [{'Id': 'lib1', 'Name': 'Music', 'CollectionType': 'music'}]}
SAMPLE_ARTISTS = {'Items': [{'Id': 'artist1', 'Name': 'Test Artist', 'DateCreated': '2023-01-01T00:00:00.000Z'}]}
SAMPLE_ALBUMS = {'Items': [{'Id': 'album1', 'Name': 'Test Album', 'DateCreated': '2023-01-01T00:00:00.000Z', 'AlbumArtists': [{'Id': 'artist1'}]}]}
SAMPLE_TRACKS = {'Items': [{'Id': 'track1', 'Name': 'Test Track', 'RunTimeTicks': 2000000000, 'AlbumId': 'album1', 'ArtistItems': [{'Id': 'artist1'}]}]}
SAMPLE_PLAYLIST_ITEM = {'Id': 'playlist1', 'Name': 'Test Playlist', 'ChildCount': 1}

# --- Fixtures ---

@pytest.fixture
def mock_config_manager():
    """Fixture to mock the config_manager."""
    with patch('core.jellyfin_client.config_manager') as mock_manager:
        mock_manager.get_jellyfin_config.return_value = SAMPLE_CONFIG
        yield mock_manager

@pytest.fixture
def mock_requests():
    """Fixture to mock the requests library."""
    with patch('core.jellyfin_client.requests') as mock_req:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        # Default mock for any GET request
        mock_response.json.return_value = {}
        mock_req.get.return_value = mock_response

        # Mock for POST requests
        mock_post_response = MagicMock()
        mock_post_response.raise_for_status.return_value = None
        mock_post_response.json.return_value = {'Id': 'new_playlist_id'}
        mock_req.post.return_value = mock_post_response
        
        yield mock_req

@pytest.fixture
def jellyfin_client(mock_config_manager, mock_requests):
    """Fixture to get an instance of JellyfinClient with mocked dependencies."""
    return JellyfinClient()

# --- Tests ---

def test_initialization(jellyfin_client):
    """Test the initial state of the JellyfinClient."""
    assert jellyfin_client.base_url is None
    assert jellyfin_client.api_key is None
    assert jellyfin_client._connection_attempted is False

def test_ensure_connection_success(jellyfin_client, mock_requests):
    """Test a successful connection and setup."""
    # Mock the sequence of API calls made during _setup_client
    mock_requests.get.side_effect = [
        # /System/Info
        MagicMock(status_code=200, json=lambda: SAMPLE_SYSTEM_INFO),
        # /Users
        MagicMock(status_code=200, json=lambda: SAMPLE_USERS),
        # /Users/{user_id}/Views
        MagicMock(status_code=200, json=lambda: SAMPLE_VIEWS),
    ]

    connected = jellyfin_client.ensure_connection()

    assert connected is True
    assert jellyfin_client.is_connected() is True
    assert jellyfin_client.base_url == 'http://jellyfin.test'
    assert jellyfin_client.api_key == 'test_api_key'
    assert jellyfin_client.user_id == 'user1'
    assert jellyfin_client.music_library_id == 'lib1'
    
    # Verify the correct API calls were made
    expected_calls = [
        call('http://jellyfin.test/System/Info', headers=pytest.ANY, params=None, timeout=5),
        call('http://jellyfin.test/Users', headers=pytest.ANY, params=None, timeout=5),
        call('http://jellyfin.test/Users/user1/Views', headers=pytest.ANY, params=None, timeout=5),
    ]
    mock_requests.get.assert_has_calls(expected_calls)


def test_ensure_connection_no_config(mock_config_manager):
    """Test connection failure when config is missing."""
    mock_config_manager.get_jellyfin_config.return_value = {}
    client = JellyfinClient()
    assert client.ensure_connection() is False
    assert client.is_connected() is False

def test_ensure_connection_api_error(jellyfin_client, mock_requests):
    """Test connection failure on API request error."""
    mock_requests.get.side_effect = requests.exceptions.RequestException("Connection timed out")
    
    assert jellyfin_client.ensure_connection() is False
    assert jellyfin_client.is_connected() is False

def test_get_all_artists(jellyfin_client, mock_requests):
    """Test fetching all artists."""
    # First, ensure the client is "connected"
    jellyfin_client.base_url = SAMPLE_CONFIG['base_url']
    jellyfin_client.api_key = SAMPLE_CONFIG['api_key']
    jellyfin_client.user_id = 'user1'
    jellyfin_client.music_library_id = 'lib1'

    # Mock the response for the artists endpoint
    mock_requests.get.return_value.json.return_value = SAMPLE_ARTISTS
    
    artists = jellyfin_client.get_all_artists()

    assert len(artists) == 1
    artist = artists[0]
    assert isinstance(artist, JellyfinArtist)
    assert artist.title == 'Test Artist'
    mock_requests.get.assert_called_with(
        'http://jellyfin.test/Artists/AlbumArtists',
        headers=pytest.ANY,
        params={'ParentId': 'lib1', 'Recursive': True, 'SortBy': 'SortName', 'SortOrder': 'Ascending'},
        timeout=5
    )


def test_jellyfin_artist_wrapper(jellyfin_client):
    """Test the JellyfinArtist wrapper class."""
    artist = JellyfinArtist(SAMPLE_ARTISTS['Items'][0], jellyfin_client)
    assert artist.title == "Test Artist"
    assert artist.ratingKey == "artist1"
    
    # Mock the client's get_albums_for_artist method
    jellyfin_client.get_albums_for_artist = MagicMock(return_value=[JellyfinAlbum(SAMPLE_ALBUMS['Items'][0], jellyfin_client)])
    
    albums = artist.albums()
    jellyfin_client.get_albums_for_artist.assert_called_once_with('artist1')
    assert len(albums) == 1
    assert albums[0].title == "Test Album"

def test_jellyfin_album_wrapper(jellyfin_client):
    """Test the JellyfinAlbum wrapper class."""
    album_data = SAMPLE_ALBUMS['Items'][0]
    album = JellyfinAlbum(album_data, jellyfin_client)
    
    assert album.title == "Test Album"
    assert album.ratingKey == "album1"

    # Mock the client methods called by the wrapper
    jellyfin_client.get_artist_by_id = MagicMock(return_value=JellyfinArtist(SAMPLE_ARTISTS['Items'][0], jellyfin_client))
    jellyfin_client.get_tracks_for_album = MagicMock(return_value=[JellyfinTrack(SAMPLE_TRACKS['Items'][0], jellyfin_client)])

    artist = album.artist()
    jellyfin_client.get_artist_by_id.assert_called_once_with('artist1')
    assert artist.title == "Test Artist"

    tracks = album.tracks()
    jellyfin_client.get_tracks_for_album.assert_called_once_with('album1')
    assert len(tracks) == 1
    assert tracks[0].title == "Test Track"

def test_jellyfin_track_wrapper(jellyfin_client):
    """Test the JellyfinTrack wrapper class."""
    track_data = SAMPLE_TRACKS['Items'][0]
    track = JellyfinTrack(track_data, jellyfin_client)

    assert track.title == "Test Track"
    assert track.ratingKey == "track1"
    assert track.duration == 200000 # Ticks to ms

    # Mock client methods
    jellyfin_client.get_artist_by_id = MagicMock(return_value=JellyfinArtist(SAMPLE_ARTISTS['Items'][0], jellyfin_client))
    jellyfin_client.get_album_by_id = MagicMock(return_value=JellyfinAlbum(SAMPLE_ALBUMS['Items'][0], jellyfin_client))

    artist = track.artist()
    jellyfin_client.get_artist_by_id.assert_called_once_with('artist1')
    assert artist.title == "Test Artist"

    album = track.album()
    jellyfin_client.get_album_by_id.assert_called_once_with('album1')
    assert album.title == "Test Album"
    
def test_get_recently_added_albums(jellyfin_client, mock_requests):
    """Test fetching recently added albums."""
    jellyfin_client.ensure_connection = MagicMock(return_value=True)
    jellyfin_client.music_library_id = 'lib1'
    jellyfin_client.user_id = 'user1'
    mock_requests.get.return_value.json.return_value = SAMPLE_ALBUMS

    albums = jellyfin_client.get_recently_added_albums(max_results=10)
    
    assert len(albums) == 1
    assert albums[0].title == "Test Album"
    mock_requests.get.assert_called_with(
        'http://jellyfin.test/Users/user1/Items',
        headers=pytest.ANY,
        params={
            'ParentId': 'lib1',
            'IncludeItemTypes': 'MusicAlbum',
            'Recursive': True,
            'SortBy': 'DateCreated',
            'SortOrder': 'Descending',
            'Limit': 10
        },
        timeout=5
    )

def test_create_playlist_large(jellyfin_client, mock_requests):
    """Test creating a large playlist, which should trigger the batching logic."""
    jellyfin_client.ensure_connection = MagicMock(return_value=True)
    jellyfin_client.user_id = 'user1'

    # Mock tracks with valid GUIDs
    tracks_to_add = [
        MagicMock(ratingKey='a' * 32),
        MagicMock(ratingKey='b' * 32)
    ]
    
    # Mock the POST requests for creating and adding to the playlist
    mock_create_response = MagicMock(status_code=200, json=lambda: {'Id': 'new_playlist_id'})
    mock_add_response = MagicMock(status_code=204) # No content on success

    mock_requests.post.side_effect = [
        mock_create_response, # Create empty playlist
        mock_add_response     # Add tracks batch
    ]

    success = jellyfin_client.create_playlist("My Large Playlist", tracks_to_add)

    assert success is True
    
    expected_calls = [
        # Call 1: Create the empty playlist
        call(
            'http://jellyfin.test/Playlists',
            json={'Name': 'My Large Playlist', 'UserId': 'user1', 'MediaType': 'Audio'},
            headers=pytest.ANY,
            timeout=10
        ),
        # Call 2: Add the tracks in a batch
        call(
            'http://jellyfin.test/Playlists/new_playlist_id/Items',
            params={'Ids': f'{"a" * 32},{"b" * 32}', 'UserId': 'user1'},
            headers=pytest.ANY,
            timeout=30
        )
    ]
    mock_requests.post.assert_has_calls(expected_calls)


def test_is_valid_guid():
    """Test the GUID validation utility."""
    client = JellyfinClient()
    assert client._is_valid_guid('1234567890abcdef1234567890abcdef') is True
    assert client._is_valid_guid('12345678-90ab-cdef-1234-567890abcdef') is True
    assert client._is_valid_guid('not-a-guid') is False
    assert client._is_valid_guid(None) is False
    assert client._is_valid_guid('1234') is False
    assert client._is_valid_guid('g' * 32) is False # 'g' is not a hex char

def test_clear_cache(jellyfin_client):
    """Test that clear_cache resets all internal caches."""
    jellyfin_client._artist_cache['artist1'] = "data"
    jellyfin_client._album_cache['album1'] = "data"
    jellyfin_client._track_cache['track1'] = "data"
    jellyfin_client._cache_populated = True

    jellyfin_client.clear_cache()

    assert jellyfin_client._artist_cache == {}
    assert jellyfin_client._album_cache == {}
    assert jellyfin_client._track_cache == {}
    assert jellyfin_client._cache_populated is False
