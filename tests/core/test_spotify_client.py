
import pytest
from unittest.mock import MagicMock, patch
from providers.spotify.client import SpotifyClient

@pytest.fixture
def spotify_client():
    # Use a dummy client ID so ConfigCacheHandler doesn't fail if it tries to init
    with patch('core.settings.ConfigManager.get_spotify_config') as mock_config:
        mock_config.return_value = {'client_id': 'fake', 'client_secret': 'fake'}
        client = SpotifyClient()
        return client

def test_initialization(spotify_client):
    assert spotify_client.name == 'spotify'
    assert spotify_client.supports_downloads is False
    # sp may be initialized or None depending on credentials
    assert hasattr(spotify_client, 'sp')

def test_is_configured_false(spotify_client):
    # Reset sp to test unconfigured state
    spotify_client.sp = None
    with patch('sdk.storage_service.get_storage_service') as mock_storage:
        mock_storage_instance = MagicMock()
        mock_storage_instance.get_service_config.return_value = None
        mock_storage.return_value = mock_storage_instance
        assert spotify_client.is_configured() is False

def test_is_configured_true(spotify_client):
    spotify_client.sp = MagicMock()
    assert spotify_client.is_configured() is True
