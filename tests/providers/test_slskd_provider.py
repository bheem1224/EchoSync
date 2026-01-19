import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from providers.slskd.client import SlskdProvider

# Mock aiohttp response
class MockResponse:
    def __init__(self, status, data):
        self.status_code = status
        self.content = True
        self._data = data

    def json(self):
        return self._data

@pytest.fixture
def provider():
    # Mock config
    with patch('providers.slskd.client.config_manager') as cfg:
        cfg.get_soulseek_config.return_value = {'slskd_url': 'http://test', 'api_key': 'key'}
        # Avoid creating directories
        with patch('pathlib.Path.mkdir'):
            p = SlskdProvider()
            p.http = AsyncMock() # Mock RequestManager
            return p

@pytest.mark.asyncio
async def test_search_atomic_flow(provider):
    # Mock sequence: POST search -> GET results (empty) -> GET results (data) -> DELETE

    search_id = "s123"
    results = [{"username": "u1", "files": [{"filename": "song.mp3", "size": 1000, "bitRate": 320, "length": 180}]}]

    provider.http.request.side_effect = [
        MockResponse(200, {"id": search_id}), # POST
        MockResponse(200, []),                # Poll 1
        MockResponse(200, results),           # Poll 2
        MockResponse(204, {})                 # DELETE
    ]

    # Speed up polling
    with patch('asyncio.sleep', new_callable=AsyncMock):
        # Increase timeout to ensure loop runs at least once (timeout > poll_interval of 2.0)
        tracks = await provider._async_search("query", timeout=5)

    assert len(tracks) == 1
    assert tracks[0].title == "song"
    assert tracks[0].identifiers['bitrate'] == 320

    # Verify DELETE called
    delete_call = provider.http.request.call_args_list[-1]
    assert delete_call[0][0] == "DELETE"
    assert f"searches/{search_id}" in delete_call[0][1]

@pytest.mark.asyncio
async def test_download(provider):
    provider.http.request.return_value = MockResponse(200, {"id": "dl_123"})

    res = await provider._async_download("user", "file.mp3", 100)

    assert res == "dl_123"
    provider.http.request.assert_called()
    assert "POST" in provider.http.request.call_args[0]
