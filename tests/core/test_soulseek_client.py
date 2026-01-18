
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

# --- Mock Data Structures and Fixtures ---

class MockAiohttpResponse:
    def __init__(self, status, json_data, reason="OK"):
        self.status = status
        self._json_data = json_data
        self.reason = reason if status != 200 else "OK"
        self.text_data = None

    async def json(self):
        return self._json_data

    async def text(self):
        if self.text_data is not None:
            return self.text_data
        import json
        return json.dumps(self._json_data)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.fixture
def mock_aiohttp_session():
    """Mocks aiohttp.ClientSession."""
    mock_session_instance = MagicMock()
    mock_session_instance.close = AsyncMock()
    # Default successful response
    mock_session_instance.request = MagicMock(return_value=MockAiohttpResponse(200, {}))
    
    with patch('aiohttp.ClientSession', return_value=mock_session_instance):
        yield mock_session_instance

@pytest.fixture
def mock_config_manager():
    """Mocks the config manager to provide a slskd URL."""
    with patch('providers.soulseek.client.config_manager') as mock_manager:
        mock_manager.get_soulseek_config.return_value = {
            'slskd_url': 'http://slskd.test',
            'api_key': 'test_key',
            'download_path': './downloads',
            'transfer_path': './Transfer'
        }
        mock_manager.get_all.return_value = {
            'storage': {
                'download_dir': './downloads',
                'transfer_dir': './Transfer'
            }
        }
        yield mock_manager

@pytest.fixture
def soulseek_client(mock_config_manager, mock_aiohttp_session):
    """Provides a SoulseekClient instance with mocked dependencies."""
    with patch('os.path.exists', return_value=False):  # Not in Docker
        from providers.soulseek.client import SoulseekClient
        return SoulseekClient()

# --- Tests ---

def test_initialization(soulseek_client):
    """Test that the client initializes correctly with config."""
    assert soulseek_client.base_url == 'http://slskd.test'
    assert soulseek_client.api_key == 'test_key'
    assert soulseek_client.download_path == Path('./downloads')

def test_initialization_no_config():
    """Test that the client is not configured if the URL is missing."""
    with patch('providers.soulseek.client.config_manager') as mock_cfg:
        mock_cfg.get_soulseek_config.return_value = {}
        mock_cfg.get_all.return_value = {}
        from providers.soulseek.client import SoulseekClient
        with patch('os.path.exists', return_value=False):
            client = SoulseekClient()
            assert client.base_url is None

@pytest.mark.asyncio
async def test_make_request_success(soulseek_client, mock_aiohttp_session):
    """Test a successful API request."""
    mock_response = MockAiohttpResponse(200, {"status": "ok"})
    mock_aiohttp_session.request.return_value = mock_response
    
    response = await soulseek_client._make_request("GET", "test/endpoint")
    
    assert response == {"status": "ok"}
    mock_aiohttp_session.request.assert_called_once()
    args, kwargs = mock_aiohttp_session.request.call_args
    assert args[0] == "GET"
    assert "http://slskd.test/api/v0/test/endpoint" in args[1]
    assert kwargs['headers']['X-API-Key'] == 'test_key'

@pytest.mark.asyncio
async def test_make_request_failure(soulseek_client, mock_aiohttp_session):
    """Test a failed API request."""
    mock_response = MockAiohttpResponse(500, {"error": "server down"}, reason="Internal Server Error")
    mock_response.text_data = '{"error": "server down"}'
    mock_aiohttp_session.request.return_value = mock_response
    
    response = await soulseek_client._make_request("GET", "test/endpoint")
    
    assert response is None

@pytest.mark.asyncio
async def test_make_request_empty_response(soulseek_client, mock_aiohttp_session):
    """Test successful request with empty response (201 Created)."""
    mock_response = MockAiohttpResponse(201, {})
    mock_response.text_data = ''
    mock_aiohttp_session.request.return_value = mock_response
    
    response = await soulseek_client._make_request("POST", "test/endpoint")
    
    assert response == {}

@pytest.mark.asyncio
async def test_rate_limiting(soulseek_client):
    """Test that the rate limiter waits when the threshold is reached."""
    # Set a very low limit for testing
    soulseek_client.max_searches_per_window = 2
    soulseek_client.rate_limit_window = 10 # 10 seconds

    # Mock time and sleep (use a counter to avoid StopIteration)
    import itertools
    counter = itertools.count(100)
    with patch('time.time', side_effect=lambda: next(counter)), \
         patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:

        # First two calls should be fine
        await soulseek_client._wait_for_rate_limit()
        await soulseek_client._wait_for_rate_limit()
        
        # The third call should trigger the wait
        await soulseek_client._wait_for_rate_limit()

        mock_sleep.assert_called_once()
        # Ensure we waited a positive amount of time (exact timing depends on mocking)
        assert mock_sleep.call_args[0][0] > 0

@pytest.mark.asyncio
async def test_search_flow(soulseek_client, mock_aiohttp_session):
    """Test the full search and poll flow."""
    search_id = "test-search-123"
    search_responses_data = [
        {"username": "user1", "files": [
            {"filename": "Artist - Song.mp3", "size": 5000000, "bitRate": 320, "length": 180, "extension": "mp3"}
        ]}
    ]

    # Mock the sequence of responses: 1. Create search, 2. Poll (empty), 3. Poll (with results)
    call_count = [0]
    def mock_request_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:  # POST /searches
            return MockAiohttpResponse(200, {"id": search_id})
        elif call_count[0] == 2:  # GET /searches/{id}/responses (empty)
            return MockAiohttpResponse(200, [])
        else:  # GET /searches/{id}/responses (with data)
            return MockAiohttpResponse(200, search_responses_data)
    
    mock_aiohttp_session.request.side_effect = mock_request_side_effect
    
    with patch('asyncio.sleep', new_callable=AsyncMock): # Speed up the test
        tracks, albums = await soulseek_client.search("test query", timeout=5)

    # Verify calls
    assert mock_aiohttp_session.request.call_count >= 3
    first_call = mock_aiohttp_session.request.call_args_list[0]
    assert first_call[0][0] == "POST"
    assert "searches" in first_call[0][1]

    # Verify results
    assert len(tracks) == 1
    assert len(albums) == 0
    assert tracks[0].title == "Song"
    assert tracks[0].artist == "Artist"

# Non-async test
def test_process_search_responses(soulseek_client):
    """Test the internal logic for processing raw search responses."""
    from providers.soulseek.client import AlbumResult
    
    responses_data = [
        # Album 1 from user A
        {"username": "userA", "files": [
            {"filename": "Artist A - Album X/01 - Track 1.flac", "size": 25e6, "length": 180, "extension": "flac"},
            {"filename": "Artist A - Album X/02 - Track 2.flac", "size": 26e6, "length": 190, "extension": "flac"},
        ]},
        # Individual track from user B
        {"username": "userB", "files": [
            {"filename": "Artist B - Standalone.mp3", "size": 8e6, "length": 200, "bitRate": 320, "extension": "mp3"},
        ]},
        # Non-audio file to be ignored
        {"username": "userC", "files": [
            {"filename": "album_art.jpg", "size": 1e6, "extension": "jpg"},
        ]}
    ]
    
    tracks, albums = soulseek_client._process_search_responses(responses_data)
    
    assert len(tracks) == 1 # The standalone track
    assert tracks[0].username == "userB"

    assert len(albums) == 1
    album = albums[0]
    assert isinstance(album, AlbumResult)
    assert album.username == "userA"
    assert album.album_title == "Album X"
    assert album.artist == "Artist A"
    assert album.track_count == 2
    assert album.dominant_quality == "flac"

@pytest.mark.asyncio
async def test_download(soulseek_client, mock_aiohttp_session):
    """Test the download functionality."""
    mock_response = MockAiohttpResponse(201, {"id": "download-123"})
    mock_response.text_data = ''
    mock_aiohttp_session.request.return_value = mock_response
    
    download_id = await soulseek_client.download("testuser", "Artist - Song.mp3", 5000000)
    
    assert download_id == "download-123"
    
    call_args, call_kwargs = mock_aiohttp_session.request.call_args
    assert call_args[0] == "POST"
    assert "transfers/downloads/testuser" in call_args[1]
    
    # Check the JSON payload
    sent_data = call_kwargs['json'][0]
    assert sent_data['filename'] == "Artist - Song.mp3"
    assert str(soulseek_client.download_path) in sent_data['path']

@pytest.mark.asyncio
async def test_get_all_downloads(soulseek_client, mock_aiohttp_session):
    """Test fetching and parsing all active downloads."""
    download_data = [
        {"username": "user1", "directories": [{"files": [
            {"id": "dl1", "filename": "song1.mp3", "state": "Completed", "size": 5e6, "bytesTransferred": 5e6, "averageSpeed": 0}
        ]}]},
        {"username": "user2", "directories": [{"files": [
            {"id": "dl2", "filename": "song2.flac", "state": "Downloading", "bytesTransferred": 12.5e6, "size": 25e6, "averageSpeed": 1024000}
        ]}]}
    ]
    mock_aiohttp_session.request.return_value = MockAiohttpResponse(200, download_data)
    
    downloads = await soulseek_client.get_all_downloads()
    
    assert len(downloads) == 2
    
    completed = next(d for d in downloads if d.id == "dl1")
    downloading = next(d for d in downloads if d.id == "dl2")
    
    assert completed.progress == 100.0
    assert downloading.progress == 50.0
    assert downloading.username == "user2"
    assert downloading.filename == "song2.flac"
