
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
    with patch('database.config_database.get_config_database') as mock_get_db:
        mock_db = MagicMock()
        mock_db.get_service_config.return_value = None
        mock_get_db.return_value = mock_db
        assert plex_client.is_configured() is False

def test_is_configured_true(plex_client):
    with patch('database.config_database.get_config_database') as mock_get_db:
        mock_db = MagicMock()
        def side_effect(service_id, key):
            if key in ('base_url', 'server_url'):
                return 'http://plex'
            elif key == 'token':
                return 'abc'
            return None
        mock_db.get_service_config.side_effect = side_effect
        mock_get_db.return_value = mock_db
        assert plex_client.is_configured() is True
