
import pytest
from unittest.mock import MagicMock, patch, call
from core.navidrome_client import NavidromeClient, NavidromeArtist, NavidromeAlbum, NavidromeTrack

# --- Sample Config and API Responses ---

SAMPLE_CONFIG = {
    'base_url': 'http://navidrome.test',
    'username': 'testuser',
    'password': 'testpass'
}

# A successful Subsonic response is nested
def create_success_response(payload_key, payload):
    return {'subsonic-response': {'status': 'ok', payload_key: payload}}

def create_error_response(message):
    return {'subsonic-response': {'status': 'failed', 'error': {'code': 40, 'message': message}}}

SAMPLE_PING = create_success_response('version', '1.16.1')
SAMPLE_ARTISTS_INDEX = {'index': [{'name': 'T', 'artist': [{'id': 'artist1', 'name': 'Test Artist'}]}]}
SAMPLE_ARTISTS = create_success_response('artists', SAMPLE_ARTISTS_INDEX)
SAMPLE_ARTIST_DETAILS = create_success_response('artist', {'id': 'artist1', 'name': 'Test Artist', 'album': [{'id': 'album1', 'name': 'Test Album'}]})
SAMPLE_ALBUM_DETAILS = create_success_response('album', {'id': 'album1', 'name': 'Test Album', 'song': [{'id': 'track1', 'title': 'Test Track'}]})
SAMPLE_PLAYLISTS = create_success_response('playlists', {'playlist': [{'id': 'pl1', 'name': 'My Playlist'}]})
SAMPLE_CREATE_PLAYLIST = create_success_response('playlist', {'id': 'newpl', 'name': 'New Playlist'})

# --- Fixtures ---

@pytest.fixture
def mock_config_manager():
    """Fixture to mock the config_manager."""
    with patch('core.navidrome_client.config_manager') as mock_manager:
        mock_manager.get_navidrome_config.return_value = SAMPLE_CONFIG
        yield mock_manager

@pytest.fixture
def navidrome_client(mock_config_manager):
    """Fixture for a NavidromeClient instance with mocked dependencies."""
    # Mock the auth generation to be deterministic
    with patch('core.navidrome_client.secrets.token_hex', return_value='somesalt'), \
         patch('core.navidrome_client.hashlib.md5') as mock_md5:
        mock_md5.return_value.hexdigest.return_value = 'sometoken'
        
        client = NavidromeClient()
        
        # Replace the real HttpClient with a mock
        mock_http = MagicMock()
        # Default successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = SAMPLE_PING
        mock_http.get.return_value = mock_response
        
        # Replace the HttpClient instance with our mock
        client._http = mock_http
        client._http_mock = mock_http  # Store mock for test access
        
        yield client

# --- Tests ---

def test_initialization(navidrome_client):
    """Test the initial state of the NavidromeClient."""
    assert navidrome_client.base_url is None
    assert navidrome_client._connection_attempted is False

def test_ensure_connection_success(navidrome_client):
    """Test a successful connection to the Navidrome server."""
    connected = navidrome_client.ensure_connection()

    assert connected is True
    assert navidrome_client.is_connected() is True
    assert navidrome_client.base_url == 'http://navidrome.test'
    
    # Verify the 'ping' endpoint was called
    navidrome_client._http_mock.get.assert_called_once()
    args, kwargs = navidrome_client._http_mock.get.call_args
    assert 'ping' in args[0]
    assert 'u' in kwargs['params']

def test_ensure_connection_no_config(mock_config_manager):
    """Test connection failure when config is missing."""
    mock_config_manager.get_navidrome_config.return_value = {}
    client = NavidromeClient()
    assert client.ensure_connection() is False
    assert client.is_connected() is False

def test_make_request_api_error(navidrome_client):
    """Test that the client handles Subsonic API errors gracefully."""
    navidrome_client.ensure_connection() # Connect first
    
    navidrome_client._http_mock.get.return_value.json.return_value = create_error_response("Permission denied")
    
    response = navidrome_client._make_request('getArtists')
    assert response is None

def test_get_all_artists(navidrome_client):
    """Test fetching all artists."""
    navidrome_client.ensure_connection()
    navidrome_client._http_mock.get.return_value.json.return_value = SAMPLE_ARTISTS

    artists = navidrome_client.get_all_artists()

    # Verify the correct endpoint was called
    args, kwargs = navidrome_client._http_mock.get.call_args
    assert 'getArtists' in args[0]
    
    assert len(artists) == 1
    artist = artists[0]
    assert isinstance(artist, NavidromeArtist)
    assert artist.title == 'Test Artist'
    assert artist.ratingKey == 'artist1'

def test_get_albums_for_artist(navidrome_client):
    """Test fetching albums for a specific artist."""
    navidrome_client.ensure_connection()
    navidrome_client._http_mock.get.return_value.json.return_value = SAMPLE_ARTIST_DETAILS

    albums = navidrome_client.get_albums_for_artist('artist1')

    # Verify the correct endpoint and parameters were called
    args, kwargs = navidrome_client._http_mock.get.call_args
    assert 'getArtist' in args[0]
    assert kwargs['params']['id'] == 'artist1'
    
    assert len(albums) == 1
    album = albums[0]
    assert isinstance(album, NavidromeAlbum)
    assert album.title == 'Test Album'
    assert album.ratingKey == 'album1'

def test_get_tracks_for_album(navidrome_client):
    """Test fetching tracks for a specific album."""
    navidrome_client.ensure_connection()
    navidrome_client._http_mock.get.return_value.json.return_value = SAMPLE_ALBUM_DETAILS

    tracks = navidrome_client.get_tracks_for_album('album1')
    
    args, kwargs = navidrome_client._http_mock.get.call_args
    assert 'getAlbum' in args[0]
    assert kwargs['params']['id'] == 'album1'

    assert len(tracks) == 1
    track = tracks[0]
    assert isinstance(track, NavidromeTrack)
    assert track.title == 'Test Track'
    assert track.ratingKey == 'track1'

def test_get_all_playlists(navidrome_client):
    """Test fetching all playlists."""
    navidrome_client.ensure_connection()
    navidrome_client._http_mock.get.return_value.json.return_value = SAMPLE_PLAYLISTS

    playlists = navidrome_client.get_all_playlists()

    args, kwargs = navidrome_client._http_mock.get.call_args
    assert 'getPlaylists' in args[0]

    assert len(playlists) == 1
    assert playlists[0].title == 'My Playlist'

def test_create_playlist(navidrome_client):
    """Test creating a new playlist."""
    navidrome_client.ensure_connection()
    navidrome_client._http_mock.return_value.json.return_value = SAMPLE_CREATE_PLAYLIST
    
    # Mock tracks (can be simple objects with a ratingKey)
    mock_tracks = [MagicMock(ratingKey='track1'), MagicMock(ratingKey='track2')]
    
    success = navidrome_client.create_playlist("New Playlist", mock_tracks)
    
    assert success is True
    args, kwargs = navidrome_client._http_mock.get.call_args
    assert 'createPlaylist' in args[0]
    assert kwargs['params']['name'] == 'New Playlist'
    assert kwargs['params']['songId'] == ['track1', 'track2']

def test_update_playlist_new(navidrome_client):
    """Test updating a playlist that doesn't exist (should create it)."""
    navidrome_client.ensure_connection()

    # Clear any calls from initialization (ping) so assertions are about the update flow
    navidrome_client._http_mock.get.reset_mock()

    # Mock getPlaylists to return an empty list first
    navidrome_client._http_mock.get.side_effect = [
        MagicMock(json=lambda: create_success_response('playlists', {})), # for get_playlist_by_name
        MagicMock(json=lambda: SAMPLE_CREATE_PLAYLIST) # for create_playlist
    ]
    
    mock_tracks = [MagicMock(ratingKey='track1')]
    success = navidrome_client.update_playlist("A New One", mock_tracks)
    
    assert success is True
    
    # Check that getPlaylists was called, then createPlaylist
    call1 = navidrome_client._http_mock.get.call_args_list[0]
    assert 'getPlaylists' in call1.args[0]
    
    call2 = navidrome_client._http_mock.get.call_args_list[1]
    assert 'createPlaylist' in call2.args[0]
    assert call2.kwargs['params']['name'] == 'A New One'

@patch('core.navidrome_client.config_manager')
def test_update_playlist_existing(mock_cfg, navidrome_client):
    """Test updating an existing playlist."""
    navidrome_client.ensure_connection()
    # Clear any calls from initialization (ping) so assertions are about the update flow
    navidrome_client._http_mock.get.reset_mock()
    mock_cfg.get.return_value = True # Enable backups

    # Mock the sequence of API calls
    navidrome_client._http_mock.get.side_effect = [
        # 1. get_playlist_by_name finds the existing playlist
        MagicMock(json=lambda: SAMPLE_PLAYLISTS),
        # 2. copy_playlist -> get_playlist_by_name
        MagicMock(json=lambda: SAMPLE_PLAYLISTS),
        # 3. copy_playlist -> get_playlist_tracks
        MagicMock(json=lambda: create_success_response('playlist', {'entry': [{'id': 't1'}]})),
        # 4. copy_playlist -> get_playlist_by_name (for target) -> not found
        MagicMock(json=lambda: create_success_response('playlists', {})),
        # 5. copy_playlist -> create_playlist (for backup)
        MagicMock(json=lambda: create_success_response('playlist', {})),
        # 6. update_playlist -> deletePlaylist
        MagicMock(json=lambda: create_success_response('status', 'ok')),
        # 7. update_playlist -> create_playlist (for new one)
        MagicMock(json=lambda: create_success_response('playlist', {}))
    ]

    mock_tracks = [MagicMock(ratingKey='track1')]
    success = navidrome_client.update_playlist("My Playlist", mock_tracks)

    assert success is True
    
    # Verify the key API calls were made in order
    api_calls = [call[0][0] for call in navidrome_client._http_mock.get.call_args_list]
    assert 'rest/getPlaylists' in api_calls[0]
    assert 'rest/getPlaylist' in api_calls[2] # get tracks for backup
    assert 'rest/createPlaylist' in api_calls[4] # create backup
    assert 'rest/deletePlaylist' in api_calls[5] # delete original
    assert 'rest/createPlaylist' in api_calls[6] # create new

def test_clear_cache(navidrome_client):
    """Test that clear_cache resets internal caches."""
    navidrome_client._artist_cache['artist1'] = "data"
    navidrome_client._album_cache['album1'] = "data"
    navidrome_client._track_cache['track1'] = "data"

    navidrome_client.clear_cache()

    assert navidrome_client._artist_cache == {}
    assert navidrome_client._album_cache == {}
    assert navidrome_client._track_cache == {}


