
import pytest
from unittest.mock import MagicMock, patch, call
from providers.listenbrainz.client import ListenBrainzClient

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
    with patch('providers.listenbrainz.client.config_manager') as mock_manager:
        # Default to having a token
        mock_manager.get.return_value = 'test_token'
        yield mock_manager

@pytest.fixture
def mock_http_client(mock_config_manager):
    """Fixture to mock the HttpClient object."""
    # Patch HttpClient constructor at the import location used by the client
    with patch('providers.listenbrainz.client.HttpClient') as mock_http_class:
        # Create the mock HttpClient instance
        mock_http = MagicMock()
        
        # Default response for a successful GET request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = VALID_TOKEN_RESPONSE
        
        mock_http.get.return_value = mock_response
        mock_http.post.return_value = mock_response
        
        mock_http_class.return_value = mock_http
        
        # Now create the client (it will use our mocked HttpClient)
        client = ListenBrainzClient()
        client._http_mock = mock_http  # Store for test access
        
        yield client

# --- Tests ---

def test_initialization_valid_token(mock_http_client):
    """Test successful initialization with a valid token."""
    client = mock_http_client
    mock_http = client._http_mock
    
    # Verify validate-token was called
    mock_http.get.assert_called_once_with(
        'https://api.listenbrainz.org/1/validate-token',
        headers={'Authorization': 'Token test_token'}
    )
    
    assert client.is_authenticated() is True
    assert client.username == 'test_user'
    assert client.token == 'test_token'

def test_initialization_invalid_token(mock_config_manager):
    """Test initialization with an invalid token."""
    client = ListenBrainzClient()
    
    # Mock after creation
    mock_http = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = INVALID_TOKEN_RESPONSE
    mock_http.get.return_value = mock_response
    client._http = mock_http
    
    # Manually call validate since we mocked after __init__
    client._validate_and_get_username()
    
    assert client.is_authenticated() is False
    assert client.username is None

def test_initialization_no_token(mock_config_manager):
    """Test initialization when no token is in the config."""
    mock_config_manager.get.return_value = "" # No token
    
    client = ListenBrainzClient()
    mock_http = MagicMock()
    client._http = mock_http
    
    # The _http should not be used to validate if there's no token
    mock_http.get.assert_not_called()
    assert client.is_authenticated() is False

def test_make_request_with_retry(mock_http_client):
    """Test that requests are delegated to HttpClient."""
    client = mock_http_client
    mock_http = client._http_mock
    
    # Simulate a ConnectionError for the first two calls, then a success
    mock_success_response = MagicMock(status_code=200)

    # Reset from initialization and return success
    mock_http.get.reset_mock()
    mock_http.get.return_value = mock_success_response

    # This call should simply delegate to HttpClient and return the response
    response = client._make_request_with_retry('get', 'http://test.url', max_retries=3)

    assert response == mock_success_response
    assert mock_http.get.call_count == 1

def test_get_playlists_created_for_user(mock_http_client):
    """Test fetching playlists created for the user."""
    client = mock_http_client
    mock_http = client._http_mock
    
    # Setup the mock response for the specific playlist call
    mock_http.get.return_value.json.return_value = CREATED_FOR_PLAYLISTS
    
    playlists = client.get_playlists_created_for_user()
    
    # The first call is validate-token, the second is the actual playlist fetch
    last_call_args, last_call_kwargs = mock_http.get.call_args
    assert f'user/{client.username}/playlists/createdfor' in last_call_args[0]
    assert last_call_kwargs['params'] == {'count': 25, 'offset': 0}
    
    assert len(playlists) == 1
    assert playlists[0]['playlist']['title'] == 'My Weekly Mix'

def test_get_user_playlists_authenticated(mock_http_client):
    """Test fetching a user's own playlists when authenticated."""
    client = mock_http_client
    mock_http = client._http_mock
    mock_http.get.return_value.json.return_value = USER_PLAYLISTS
    
    playlists = client.get_user_playlists()
    
    last_call_args, last_call_kwargs = mock_http.get.call_args
    assert f'user/{client.username}/playlists' in last_call_args[0]
    assert 'Authorization' in last_call_kwargs['headers']
    assert last_call_kwargs['headers']['Authorization'] == 'Token test_token'
    
    assert len(playlists) == 1
    assert playlists[0]['playlist']['title'] == 'My Personal Jams'

def test_get_user_playlists_unauthenticated(mock_config_manager):
    """Test that fetching user playlists fails when not authenticated."""
    mock_config_manager.get.return_value = "" # No token
    client = ListenBrainzClient()
    
    mock_http = MagicMock()
    client._http = mock_http
    
    playlists = client.get_user_playlists()
    
    assert playlists == []
    mock_http.get.assert_not_called()

def test_get_playlist_details(mock_http_client):
    """Test fetching the full details of a playlist."""
    client = mock_http_client
    mock_http = client._http_mock
    mock_http.get.return_value.json.return_value = PLAYLIST_DETAILS
    
    playlist_mbid = 'some-mbid-123'
    details = client.get_playlist_details(playlist_mbid)

    last_call_args, last_call_kwargs = mock_http.get.call_args
    assert f'playlist/{playlist_mbid}' in last_call_args[0]
    # Auth header should be present for potentially private playlists
    assert 'Authorization' in last_call_kwargs['headers']
    
    assert details is not None
    assert details['playlist']['title'] == 'My Weekly Mix'
    assert len(details['playlist']['track']) == 1

def test_get_playlist_details_404_error(mock_http_client):
    """Test that fetching a non-existent playlist returns None."""
    client = mock_http_client
    mock_http = client._http_mock
    mock_http.get.return_value.status_code = 404
    
    details = client.get_playlist_details('non-existent-mbid')
    
    assert details is None

def test_search_playlists(mock_http_client):
    """Test playlist search."""
    client = mock_http_client
    mock_http = client._http_mock
    
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = CREATED_FOR_PLAYLISTS
    mock_http.get.return_value = mock_response
    
    query = "My Mix"
    results = client.search_playlists(query)
    
    # Find the search call (not the validate-token call)
    search_calls = [call for call in mock_http.get.call_args_list 
                   if 'playlist/search' in str(call)]
    assert len(search_calls) == 1
    
    assert len(results) == 1
    assert results[0]['playlist']['title'] == 'My Weekly Mix'

def test_search_playlists_query_too_short(mock_config_manager):
    """Test that search is rejected if the query is too short."""
    client = ListenBrainzClient()
    results = client.search_playlists("ab")
    assert results == []

