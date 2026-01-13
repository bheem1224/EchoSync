
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
    assert spotify_client.sp is None

def test_is_configured_false(spotify_client):
    assert spotify_client.is_configured() is False

def test_is_configured_true(spotify_client):
    spotify_client.sp = MagicMock()
    assert spotify_client.is_configured() is True
