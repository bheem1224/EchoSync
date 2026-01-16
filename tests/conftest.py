import sys
import os
from pathlib import Path

# Add project root to Python path so tests can import modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import MagicMock, ANY

@pytest.fixture
def mock_config_manager(monkeypatch):
    """Mocks the config_manager singleton, providing a consistent configuration for tests."""
    mock_manager = MagicMock()
    
    # --- Default Test Configuration ---
    # This provides a predictable state for all tests.
    # Individual tests can override these values if needed.
    
    test_config = {
        "active_media_server": "plex",
        "spotify": {
            "client_id": "test_spotify_client_id",
            "client_secret": "test_spotify_client_secret",
            "redirect_uri": "http://localhost:8008/api/spotify/callback"
        },
        "spotify_accounts": [
            {
                "id": 1,
                "name": "Test Account",
                "client_id": "test_spotify_client_id",
                "client_secret": "test_spotify_client_secret",
                "redirect_uri": "http://localhost:8008/api/spotify/callback",
                "refresh_token": "test_refresh_token",
                "access_token": None
            }
        ],
        "active_spotify_account_id": 1,
        "plex": {
            "base_url": "http://mock-plex:32400",
            "token": "test_plex_token"
        },
        "jellyfin": {
            "base_url": "http://mock-jellyfin:8096",
            "api_key": "test_jellyfin_api_key"
        },
        "navidrome": {
            "base_url": "http://mock-navidrome:4533",
            "username": "testuser",
            "password": "testpassword"
        },
        "soulseek": {
            "slskd_url": "http://mock-slskd:5030",
            "api_key": "test_slskd_api_key",
            "download_path": "/tmp/downloads",
            "transfer_path": "/tmp/transfer"
        }
    }

    # --- Mock Implementations ---

    # Mock the specific getter methods
    mock_manager.get_spotify_config.return_value = test_config["spotify"]
    mock_manager.get_spotify_accounts.return_value = test_config["spotify_accounts"]
    mock_manager.get_active_spotify_account.return_value = test_config["spotify_accounts"][0]
    mock_manager.get_spotify_active_credentials.return_value = {
        'client_id': test_config["spotify_accounts"][0]['client_id'],
        'client_secret': test_config["spotify_accounts"][0]['client_secret'],
        'redirect_uri': test_config["spotify_accounts"][0]['redirect_uri'],
        'refresh_token': test_config["spotify_accounts"][0]['refresh_token'],
        'access_token': test_config["spotify_accounts"][0].get('access_token'),
        'id': test_config["spotify_accounts"][0]['id'],
        'name': test_config["spotify_accounts"][0]['name']
    }
    mock_manager.get_plex_config.return_value = test_config["plex"]
    mock_manager.get_jellyfin_config.return_value = test_config["jellyfin"]
    mock_manager.get_navidrome_config.return_value = test_config["navidrome"]
    mock_manager.get_soulseek_config.return_value = test_config["soulseek"]
    mock_manager.get_active_media_server.return_value = test_config["active_media_server"]

    # Mock the general-purpose .get() method
    def mock_get(key, default=None):
        """A more robust mock for the .get() method."""
        keys = key.split('.')
        value = test_config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    mock_manager.get.side_effect = mock_get
    
    # The set method can be a simple MagicMock for most tests,
    # as we just want to verify it was called.
    mock_manager.set.return_value = None

    return mock_manager

# Provide unittest.mock.ANY under pytest.ANY for tests that accidentally use it
pytest.ANY = ANY
