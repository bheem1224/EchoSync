
import pytest
from unittest.mock import MagicMock, patch, call
from core.plex_client import PlexClient, PlexTrackInfo
from plexapi.exceptions import NotFound

# --- Sample Config and Mock Objects ---

SAMPLE_CONFIG = {
    'base_url': 'http://plex.test',
    'token': 'test_plex_token'
}

@pytest.fixture
def mock_config_manager():
    """Fixture to mock the config_manager."""
    with patch('core.plex_client.config_manager') as mock_manager:
        mock_manager.get_plex_config.return_value = SAMPLE_CONFIG
        yield mock_manager

@pytest.fixture
def mock_plex_server():
    """Fixture to mock the plexapi.server.PlexServer."""
    with patch('core.plex_client.PlexServer') as mock_plex_server_class:
        # The mock instance that the class will return
        mock_server_instance = MagicMock()
        mock_server_instance.friendlyName = "TestPlexServer"
        
        # Mock library sections
        mock_music_section = MagicMock()
        mock_music_section.type = 'artist'
        mock_music_section.title = 'Music'
        mock_music_section.key = '1'
        
        mock_video_section = MagicMock()
        mock_video_section.type = 'movie'
        mock_video_section.title = 'Movies'

        mock_server_instance.library.sections.return_value = [mock_music_section, mock_video_section]
        
        # Mock Artist/Album/Track objects
        mock_artist = MagicMock(title='Test Artist', ratingKey='artist1')
        mock_album = MagicMock(title='Test Album', ratingKey='album1', artist=lambda: mock_artist)
        mock_track = MagicMock(
            title='Test Track',
            ratingKey='track1',
            artist=lambda: mock_artist,
            album=lambda: mock_album,
            duration=200000,
            trackNumber=1,
            year=2023,
            userRating=5.0
        )
        mock_artist.tracks.return_value = [mock_track]
        mock_album.tracks.return_value = [mock_track]
        
        mock_music_section.searchArtists.return_value = [mock_artist]
        mock_music_section.searchAlbums.return_value = [mock_album]
        mock_music_section.searchTracks.return_value = [mock_track]

        # Mock search
        mock_music_section.search.return_value = [mock_track]

        # Make the PlexServer class return our mock instance
        mock_plex_server_class.return_value = mock_server_instance
        # Ensure attributes used by PlexClient are present on the mock
        mock_server_instance._baseurl = SAMPLE_CONFIG['base_url']
        mock_server_instance._token = SAMPLE_CONFIG['token']
        
        yield mock_server_instance, mock_music_section

@pytest.fixture
def plex_client(mock_config_manager, mock_plex_server):
    """Fixture to get an instance of PlexClient with mocked dependencies."""
    return PlexClient()

# --- Tests ---

def test_initialization(plex_client):
    """Test the initial state of the PlexClient."""
    assert plex_client.server is None
    assert plex_client.music_library is None
    assert plex_client._connection_attempted is False

def test_ensure_connection_success(plex_client, mock_plex_server):
    """Test a successful connection and music library discovery."""
    mock_server, mock_library = mock_plex_server
    
    connected = plex_client.ensure_connection()

    assert connected is True
    assert plex_client.is_connected() is True
    assert plex_client.is_fully_configured() is True
    assert plex_client.server == mock_server
    assert plex_client.music_library == mock_library
    mock_server.library.sections.assert_called_once()

def test_ensure_connection_no_config(mock_config_manager):
    """Test connection failure when config is missing."""
    mock_config_manager.get_plex_config.return_value = {}
    client = PlexClient()
    assert client.ensure_connection() is False
    assert client.is_connected() is False

def test_ensure_connection_api_error(mock_config_manager):
    """Test connection failure on API error from plexapi."""
    with patch('core.plex_client.PlexServer', side_effect=NotFound("Server not found")) as mock_plex_class:
        client = PlexClient()
        assert client.ensure_connection() is False
        assert client.is_connected() is False
        mock_plex_class.assert_called_once()

def test_get_available_music_libraries(plex_client, mock_plex_server):
    """Test retrieval of available music libraries."""
    plex_client.ensure_connection() # Connect the client first
    
    libraries = plex_client.get_available_music_libraries()
    
    assert len(libraries) == 1
    assert libraries[0]['title'] == 'Music'
    assert libraries[0]['key'] == '1'

def test_search_tracks(plex_client, mock_plex_server):
    """Test the track search functionality."""
    plex_client.ensure_connection()
    mock_server, mock_library = mock_plex_server
    
    # Mock the artist search -> tracks path
    mock_artist = mock_library.searchArtists.return_value[0]
    
    results = plex_client.search_tracks(title="Test Track", artist="Test Artist")

    mock_library.searchArtists.assert_called_once_with(title="Test Artist", limit=1)
    mock_artist.tracks.assert_called_once()
    
    assert len(results) == 1
    track_info = results[0]
    assert isinstance(track_info, PlexTrackInfo)
    assert track_info.title == "Test Track"
    assert track_info.artist == "Test Artist"
    # Check that the original plex track is stored
    assert hasattr(track_info, '_original_plex_track')
    assert track_info._original_plex_track.ratingKey == 'track1'

def test_create_playlist(plex_client, mock_plex_server):
    """Test creating a new playlist."""
    plex_client.ensure_connection()
    mock_server, mock_library = mock_plex_server
    
    # Get the mock track from the search result, which has the _original_plex_track attribute
    track_to_add = plex_client.search_tracks(title="Test Track", artist="Test Artist")[0]
    
    success = plex_client.create_playlist("My Test Playlist", [track_to_add])
    
    assert success is True
    # The first argument is the playlist title, the second is the list of tracks
    # We check that the second argument is a list containing our original mock track object
    mock_server.createPlaylist.assert_called_once_with("My Test Playlist", [track_to_add._original_plex_track])

def test_update_playlist_new(plex_client, mock_plex_server):
    """Test updating a playlist that doesn't exist yet (should create it)."""
    plex_client.ensure_connection()
    mock_server, mock_library = mock_plex_server
    
    # Mock the server.playlist call to raise NotFound
    mock_server.playlist.side_effect = NotFound("Playlist not found")
    
    track_to_add = plex_client.search_tracks(title="Test Track", artist="Test Artist")[0]
    
    success = plex_client.update_playlist("New Playlist", [track_to_add])
    
    assert success is True
    mock_server.playlist.assert_called_once_with("New Playlist")
    mock_server.createPlaylist.assert_called_once_with("New Playlist", [track_to_add._original_plex_track])

@patch('core.plex_client.config_manager')
def test_update_playlist_existing(mock_cfg, plex_client, mock_plex_server):
    """Test updating an existing playlist."""
    plex_client.ensure_connection()
    mock_server, mock_library = mock_plex_server

    # Mock the config to enable backups
    mock_cfg.get.return_value = True

    # Mock an existing playlist
    mock_existing_playlist = MagicMock()
    mock_server.playlist.return_value = mock_existing_playlist
    mock_existing_playlist.items.return_value = [] # Backup source
    
    track_to_add = plex_client.search_tracks(title="Test Track", artist="Test Artist")[0]

    # Mock copy_playlist to return True
    plex_client.copy_playlist = MagicMock(return_value=True)

    success = plex_client.update_playlist("Existing Playlist", [track_to_add])

    assert success is True
    # Verify backup was attempted
    plex_client.copy_playlist.assert_called_once_with("Existing Playlist", "Existing Playlist Backup")
    # Verify the old playlist was deleted
    mock_existing_playlist.delete.assert_called_once()
    # Verify the new playlist was created
    mock_server.createPlaylist.assert_called_once_with("Existing Playlist", [track_to_add._original_plex_track])

def test_parse_update_timestamp(plex_client):
    """Test parsing the timestamp from an artist's summary."""
    mock_artist = MagicMock(summary="Some bio.\n\n-updatedAt2023-05-20")
    timestamp = plex_client.parse_update_timestamp(mock_artist)
    assert timestamp is not None
    assert timestamp.year == 2023
    assert timestamp.month == 5
    assert timestamp.day == 20

def test_is_artist_ignored(plex_client):
    """Test checking if an artist is marked as ignored."""
    mock_artist_ignored = MagicMock(summary="Bio text -IgnoreUpdate")
    mock_artist_not_ignored = MagicMock(summary="Bio text")
    
    assert plex_client.is_artist_ignored(mock_artist_ignored) is True
    assert plex_client.is_artist_ignored(mock_artist_not_ignored) is False

def test_update_artist_biography(plex_client):
    """Test that the artist biography/summary is updated with a timestamp."""
    from datetime import datetime
    mock_artist = MagicMock(summary="Original bio.")
    mock_artist.reload.return_value = None # Mock reload
    
    # Get today's date for the expected value
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # We need to simulate the edit call and then the reload
    def reload_effect():
        # When reload() is called, update the summary on the mock object
        mock_artist.summary = f"Original bio.\n\n-updatedAt{today_str}"
    
    mock_artist.reload.side_effect = reload_effect

    success = plex_client.update_artist_biography(mock_artist)
    
    assert success is True
    # Check that the edit call was made correctly
    expected_summary = f"Original bio.\n\n-updatedAt{today_str}"
    mock_artist.edit.assert_called_once_with(**{'summary.value': expected_summary})
    # Verify reload was called to fetch the changes
    mock_artist.reload.assert_called_once()

@patch('core.plex_client.requests.post')
def test_update_artist_poster(mock_post, plex_client, mock_plex_server):
    """Test uploading a new poster for an artist."""
    plex_client.ensure_connection()
    mock_server, _ = mock_plex_server
    mock_artist = MagicMock(ratingKey='artist1', title='Test Artist')
    
    # Mock the requests.post call
    mock_response = MagicMock(status_code=200)
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    image_data = b'imagedata'
    success = plex_client.update_artist_poster(mock_artist, image_data)

    assert success is True
    expected_url = f"{SAMPLE_CONFIG['base_url']}/library/metadata/artist1/posters"
    expected_headers = {
        'X-Plex-Token': SAMPLE_CONFIG['token'],
        'Content-Type': 'image/jpeg'
    }
    mock_post.assert_called_once_with(expected_url, data=image_data, headers=expected_headers)
    mock_artist.refresh.assert_called_once()
