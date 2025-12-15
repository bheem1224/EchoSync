
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# --- Mock Data Structures and Fixtures ---

class MockAiohttpResponse:
    def __init__(self, status, json_data):
        self.status = status
        self._json_data = json_data
        self.reason = "OK" if status == 200 else "Error"

    async def json(self):
        return self._json_data

    async def text(self):
        import json
        return json.dumps(self._json_data)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.fixture
def mock_aiohttp_session():
    """Mocks aiohttp.ClientSession."""
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session_instance = MagicMock()
        # Default successful response
        mock_session_instance.request.return_value = MockAiohttpResponse(200, {})
        mock_session_class.return_value = mock_session_instance
        yield mock_session_instance

@pytest.fixture
def mock_config_manager():
    """Mocks the config manager to provide a slskd URL."""
    with patch('core.soulseek_client.config_manager') as mock_manager:
        mock_manager.get_soulseek_config.return_value = {
            'slskd_url': 'http://slskd.test',
            'api_key': 'test_key'
        }
        yield mock_manager

@pytest.fixture
def soulseek_client(mock_config_manager, mock_aiohttp_session):
    """Provides a SoulseekClient instance with mocked dependencies."""
    from core.soulseek_client import SoulseekClient
    return SoulseekClient()

# --- Tests ---

@pytest.mark.asyncio
async def test_initialization(soulseek_client):
    """Test that the client initializes correctly with config."""
    assert soulseek_client.is_configured() is True
    assert soulseek_client.base_url == 'http://slskd.test'
    assert soulseek_client.api_key == 'test_key'

@pytest.mark.asyncio
async def test_initialization_no_config():
    """Test that the client is not configured if the URL is missing."""
    with patch('core.soulseek_client.config_manager') as mock_cfg:
        mock_cfg.get_soulseek_config.return_value = {}
        from core.soulseek_client import SoulseekClient
        client = SoulseekClient()
        assert client.is_configured() is False

@pytest.mark.asyncio
async def test_make_request_success(soulseek_client, mock_aiohttp_session):
    """Test a successful API request."""
    mock_aiohttp_session.request.return_value = MockAiohttpResponse(200, {"status": "ok"})
    
    response = await soulseek_client._make_request("GET", "test/endpoint")
    
    assert response == {"status": "ok"}
    mock_aiohttp_session.request.assert_called_once()
    args, kwargs = mock_aiohttp_session.request.call_args
    assert "http://slskd.test/api/v0/test/endpoint" in args
    assert kwargs['headers']['X-API-Key'] == 'test_key'

@pytest.mark.asyncio
async def test_make_request_failure(soulseek_client, mock_aiohttp_session):
    """Test a failed API request."""
    mock_aiohttp_session.request.return_value = MockAiohttpResponse(500, {"error": "server down"})
    
    response = await soulseek_client._make_request("GET", "test/endpoint")
    
    assert response is None

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
            {"filename": "Artist - Song.mp3", "size": 5000000, "bitRate": 320, "length": 180}
        ]}
    ]

    # Mock the sequence of responses: 1. Create search, 2. Poll (empty), 3. Poll (with results)
    mock_aiohttp_session.request.side_effect = [
        MockAiohttpResponse(200, {"id": search_id}),           # POST /searches
        MockAiohttpResponse(200, []),                          # GET /searches/{id}/responses (empty)
        MockAiohttpResponse(200, search_responses_data),       # GET /searches/{id}/responses (with data)
    ]
    
    with patch('asyncio.sleep', new_callable=AsyncMock): # Speed up the test
        tracks, albums = await soulseek_client.search("test query", timeout=5)

    # Verify calls
    post_call = mock_aiohttp_session.request.call_args_list[0]
    assert "POST" in post_call.args
    assert "searches" in post_call.args[1]

    get_call = mock_aiohttp_session.request.call_args_list[2] # 3rd call has results
    assert "GET" in get_call.args
    assert f"searches/{search_id}/responses" in get_call.args[1]

    # Verify results
    assert len(tracks) == 1
    assert len(albums) == 0
    assert tracks[0].title == "Song"
    assert tracks[0].artist == "Artist"

# Non-async test - exempt from asyncio marker by not using async def
def test_process_search_responses(soulseek_client):
    """Test the internal logic for processing raw search responses."""
    from core.soulseek_client import AlbumResult
    
    responses_data = [
        # Album 1 from user A
            {"username": "userA", "files": [
                {"filename": "Artist A - Album X/01 - Track 1.flac", "size": 25e6, "length": 180},
                {"filename": "Artist A - Album X/02 - Track 2.flac", "size": 26e6, "length": 190},
            ]},
        # Individual track from user B
        {"username": "userB", "files": [
            {"filename": "Artist B - Standalone.mp3", "size": 8e6, "length": 200, "bitRate": 320},
        ]},
        # Non-audio file to be ignored
        {"username": "userC", "files": [
            {"filename": "album_art.jpg", "size": 1e6},
        ]}
    ]
    
    tracks, albums = soulseek_client._process_search_responses(responses_data)
    
    assert len(tracks) == 1 # The standalone track
    assert tracks[0].username == "userB"

    assert len(albums) == 1
    album = albums[0]
    assert isinstance(album, AlbumResult)
    assert album.username == "userA"
    assert album.album_title == "Artist A - Album X"
    assert album.artist == "Artist A"
    assert album.track_count == 2
    assert album.dominant_quality == "flac"

@pytest.mark.asyncio
async def test_download(soulseek_client, mock_aiohttp_session):
    """Test the download functionality."""
    mock_aiohttp_session.request.return_value = MockAiohttpResponse(201, {"id": "download-123"})
    
    download_id = await soulseek_client.download("testuser", "Artist - Song.mp3", 5000000)
    
    assert download_id == "download-123"
    
    call_args, call_kwargs = mock_aiohttp_session.request.call_args
    assert "POST" in call_args
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
            {"id": "dl1", "filename": "song1.mp3", "state": "Completed", "size": 5e6}
        ]}]},
        {"username": "user2", "directories": [{"files": [
            {"id": "dl2", "filename": "song2.flac", "state": "Downloading", "progress": 50.0, "size": 25e6}
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
