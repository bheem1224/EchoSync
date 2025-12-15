
import pytest
from unittest.mock import MagicMock, patch, call
from core.listenbrainz_client import ListenBrainzClient
import requests

# --- Sample API Responses ---

VALID_TOKEN_RESPONSE = {'valid': True, 'user_name': 'test_user'}
INVALID_TOKEN_RESPONSE = {'valid': False}
CREATED_FOR_PLAYLISTS = {'playlists': [{'playlist': {'title': 'My Weekly Mix'}}]}
USER_PLAYLISTS = {'playlists': [{'playlist': {'title': 'My Personal Jams'}}]}
PLAYLIST_DETAILS = {'playlist': {'title': 'My Weekly Mix', 'track': [{'title': 'A Great Song'}]}}

# --- Fixtures ---

@pytest.fixture
def mock_config_manager():
    """Fixture to mock config_manager."""
    with patch('core.listenbrainz_client.config_manager') as mock_manager:
        # Default to having a token
        mock_manager.get.return_value = 'test_token'
        yield mock_manager

@pytest.fixture
def mock_session():
    """Fixture to mock the requests.Session object."""
    with patch('core.listenbrainz_client.requests.Session') as mock_session_class:
        mock_session_instance = MagicMock()
        
        # Default response for a successful GET request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = VALID_TOKEN_RESPONSE
        
        mock_session_instance.get.return_value = mock_response
        mock_session_instance.post.return_value = mock_response # For future use

        mock_session_class.return_value = mock_session_instance
        yield mock_session_instance

# --- Tests ---

def test_initialization_valid_token(mock_config_manager, mock_session):
    """Test successful initialization with a valid token."""
    client = ListenBrainzClient()
    
    # Verify validate-token was called
    mock_session.get.assert_called_once_with(
        'https://api.listenbrainz.org/1/validate-token',
        headers={'Authorization': 'Token test_token'},
        timeout=10
    )
    
    assert client.is_authenticated() is True
    assert client.username == 'test_user'
    assert client.token == 'test_token'

def test_initialization_invalid_token(mock_config_manager, mock_session):
    """Test initialization with an invalid token."""
    mock_session.get.return_value.json.return_value = INVALID_TOKEN_RESPONSE
    
    client = ListenBrainzClient()
    
    assert client.is_authenticated() is False
    assert client.username is None

def test_initialization_no_token(mock_config_manager, mock_session):
    """Test initialization when no token is in the config."""
    mock_config_manager.get.return_value = "" # No token
    
    client = ListenBrainzClient()
    
    # The session should not be used to validate if there's no token
    mock_session.get.assert_not_called()
    assert client.is_authenticated() is False

def test_make_request_with_retry(mock_config_manager, mock_session):
    """Test the retry logic on connection errors."""
    # Simulate a ConnectionError for the first two calls, then a success
    mock_success_response = MagicMock(status_code=200)
    # Create client first so __init__ doesn't consume the side_effect
    client = ListenBrainzClient()

    mock_session.get.side_effect = [
        requests.exceptions.ConnectionError("Failed to connect"),
        requests.exceptions.ConnectionError("Failed to connect again"),
        mock_success_response
    ]
    
    # Patch time.sleep to avoid waiting during the test
    with patch('core.listenbrainz_client.time.sleep') as mock_sleep:
        # Clear previous calls (initialization may have used the session)
        mock_session.get.reset_mock()

        # This call would normally happen in __init__, but we test the retry mechanism directly
        response = client._make_request_with_retry('get', 'http://test.url', max_retries=3)
        
        assert response == mock_success_response
        assert mock_session.get.call_count == 3
        mock_sleep.assert_has_calls([call(2), call(4)])

def test_get_playlists_created_for_user(mock_config_manager, mock_session):
    """Test fetching playlists created for the user."""
    client = ListenBrainzClient() # Inits and authenticates
    
    # Setup the mock response for the specific playlist call
    mock_session.get.return_value.json.return_value = CREATED_FOR_PLAYLISTS
    
    playlists = client.get_playlists_created_for_user()
    
    # The first call is validate-token, the second is the actual playlist fetch
    last_call_args, last_call_kwargs = mock_session.get.call_args
    assert f'user/{client.username}/playlists/createdfor' in last_call_args[0]
    assert last_call_kwargs['params'] == {'count': 25, 'offset': 0}
    
    assert len(playlists) == 1
    assert playlists[0]['playlist']['title'] == 'My Weekly Mix'

def test_get_user_playlists_authenticated(mock_config_manager, mock_session):
    """Test fetching a user's own playlists when authenticated."""
    client = ListenBrainzClient()
    mock_session.get.return_value.json.return_value = USER_PLAYLISTS
    
    playlists = client.get_user_playlists()
    
    last_call_args, last_call_kwargs = mock_session.get.call_args
    assert f'user/{client.username}/playlists' in last_call_args[0]
    assert 'Authorization' in last_call_kwargs['headers']
    assert last_call_kwargs['headers']['Authorization'] == 'Token test_token'
    
    assert len(playlists) == 1
    assert playlists[0]['playlist']['title'] == 'My Personal Jams'

def test_get_user_playlists_unauthenticated(mock_config_manager, mock_session):
    """Test that fetching user playlists fails when not authenticated."""
    mock_config_manager.get.return_value = "" # No token
    client = ListenBrainzClient()

    # Clear mock calls from initialization
    mock_session.get.reset_mock()
    
    playlists = client.get_user_playlists()
    
    assert playlists == []
    mock_session.get.assert_not_called()

def test_get_playlist_details(mock_config_manager, mock_session):
    """Test fetching the full details of a playlist."""
    client = ListenBrainzClient()
    mock_session.get.return_value.json.return_value = PLAYLIST_DETAILS
    
    playlist_mbid = 'some-mbid-123'
    details = client.get_playlist_details(playlist_mbid)

    last_call_args, last_call_kwargs = mock_session.get.call_args
    assert f'playlist/{playlist_mbid}' in last_call_args[0]
    # Auth header should be present for potentially private playlists
    assert 'Authorization' in last_call_kwargs['headers']
    
    assert details is not None
    assert details['playlist']['title'] == 'My Weekly Mix'
    assert len(details['playlist']['track']) == 1

def test_get_playlist_details_404_error(mock_config_manager, mock_session):
    """Test that fetching a non-existent playlist returns None."""
    client = ListenBrainzClient()
    mock_session.get.return_value.status_code = 404
    
    details = client.get_playlist_details('non-existent-mbid')
    
    assert details is None

@patch('core.listenbrainz_client.requests.get')
def test_search_playlists(mock_standalone_get, mock_config_manager):
    """Test playlist search. Uses a separate mock as it's a standalone requests call."""
    mock_config_manager.get.return_value = "" # No auth needed for search
    client = ListenBrainzClient()

    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = CREATED_FOR_PLAYLISTS
    mock_standalone_get.return_value = mock_response
    
    query = "My Mix"
    results = client.search_playlists(query)
    
    mock_standalone_get.assert_called_once_with(
        'https://api.listenbrainz.org/1/playlist/search',
        headers={},
        params={'query': query},
        timeout=10
    )
    
    assert len(results) == 1
    assert results[0]['playlist']['title'] == 'My Weekly Mix'

def test_search_playlists_query_too_short(mock_config_manager):
    """Test that search is rejected if the query is too short."""
    client = ListenBrainzClient()
    results = client.search_playlists("ab")
    assert results == []
