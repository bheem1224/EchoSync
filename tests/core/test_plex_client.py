
import pytest
from unittest.mock import MagicMock, patch
from providers.plex.client import PlexClient

@pytest.fixture
def plex_client():
    with patch('providers.plex.client.config_manager') as mock_cm:
        mock_cm.get_plex_config.return_value = {}
        client = PlexClient()
        return client

def test_initialization(plex_client):
    assert plex_client.name == 'plex'
    assert plex_client.supports_downloads is False
    assert plex_client.server is None
    assert plex_client.music_library is None

def test_is_configured_false(plex_client):
    with patch('providers.plex.client.config_manager') as mock_cm:
        mock_cm.get_plex_config.return_value = {}
        assert plex_client.is_configured() is False

def test_is_configured_true(plex_client):
    with patch('providers.plex.client.config_manager') as mock_cm:
        mock_cm.get_plex_config.return_value = {'base_url': 'http://plex', 'token': 'abc'}
        assert plex_client.is_configured() is True
