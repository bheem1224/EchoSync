
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
    plex_client.account_id = None
    assert plex_client.is_configured() is False

def test_is_configured_true(plex_client):
    plex_client.account_id = 1
    with patch('core.storage.get_storage_service') as mock_get_storage, \
         patch('core.settings.config_manager.get') as mock_config_get:
        mock_storage = MagicMock()

        def mock_get_account_token(acc_id):
            return {'access_token': 'encrypted_abc'}

        mock_storage.get_account_token.side_effect = mock_get_account_token
        mock_get_storage.return_value = mock_storage

        def mock_config(key, default=None):
            if key == 'plex':
                return {'base_url': 'http://plex'}
            return default

        mock_config_get.side_effect = mock_config

        assert plex_client.is_configured() is True
