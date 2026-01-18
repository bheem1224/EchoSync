import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path
from providers.slskd.client import SlskdProvider
from typing import Any

@pytest.fixture
def slskd_provider() -> SlskdProvider:
    """Fixture to initialize SlskdProvider."""
    provider = SlskdProvider()
    provider.http = AsyncMock()  # Mock the HTTP client
    return provider

@patch("providers.slskd.client.config_manager.get_soulseek_config")
def test_setup_client(mock_get_config: Any, slskd_provider: SlskdProvider) -> None:
    """Test the setup of the client indirectly through public methods."""
    mock_get_config.return_value = {
        "slskd_url": "http://localhost:5000",
        "api_key": "test_api_key",
        "download_path": "./downloads"
    }

    # Trigger setup indirectly
    slskd_provider.search("test query")

    assert slskd_provider.base_url == "http://localhost:5000"
    assert slskd_provider.api_key == "test_api_key"
    assert slskd_provider.download_path == Path("./downloads")

@pytest.mark.asyncio
async def test_search(slskd_provider: SlskdProvider) -> None:
    """Test the search method."""
    slskd_provider.http.request = AsyncMock(
        return_value=AsyncMock(
            json=AsyncMock(
                return_value=[
                    {
                        "username": "user1",
                        "files": [
                            {"filename": "track1.mp3", "size": 12345, "bitRate": 320, "length": 180}
                        ]
                    }
                ]
            )
        )
    )

    results = slskd_provider.search("test query")

    assert len(results) == 1
    assert results[0].title == "track1.mp3"
    assert results[0].bitrate == 320

@pytest.mark.asyncio
async def test_download(slskd_provider: SlskdProvider) -> None:
    """Test the download method."""
    slskd_provider.http.request = AsyncMock(
        return_value=AsyncMock(
            json=AsyncMock(return_value={"id": "download123"})
        )
    )

    download_id = slskd_provider.download("user1", "track1.mp3", 12345)

    assert download_id == "download123"

@pytest.mark.asyncio
async def test_get_download_status(slskd_provider: SlskdProvider) -> None:
    """Test the get_download_status method."""
    slskd_provider.http.request = AsyncMock(
        return_value=AsyncMock(
            json=AsyncMock(
                return_value={
                    "id": "download123",
                    "state": "downloading",
                    "percentComplete": 50,
                    "averageSpeed": 100,
                    "filename": "track1.mp3",
                    "size": 12345,
                    "timeRemaining": 30
                }
            )
        )
    )

    status = slskd_provider.get_download_status("download123")

    assert status is not None, "Status should not be None"
    assert status["status"] == "downloading"
    assert status["progress"] == 50
    assert status["speed"] == 100
    assert status["filename"] == "track1.mp3"
    assert status["size"] == 12345
    assert status["time_remaining"] == 30