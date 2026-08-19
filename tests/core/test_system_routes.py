"""
Tests for system routes.
Focuses on ensuring endpoints correctly resolve plugins and their capabilities
and safely interact with the configuration database.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from web.auth import require_auth

import web.routes.system as route_module

@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(route_module.router)
    app.dependency_overrides[require_auth] = lambda: True
    return app

@pytest.fixture
def client(app):
    return TestClient(app)

def test_system_accounts_list(client, monkeypatch):
    """Verifies that music services are properly filtered by capabilities."""
    
    mock_db = MagicMock()
    mock_db.get_service_name.return_value = 'plex'
    mock_db.get_or_create_service_id.return_value = 1
    mock_db.upsert_account.return_value = 1
    mock_db.get_account_mappings.return_value = []
    
    # Mock some accounts returned by config_db
    mock_db.get_accounts.side_effect = lambda service_id=None, **kwargs: [
        {'id': 1, 'display_name': 'Test User', 'user_id': '12345'}
    ]
    monkeypatch.setattr('database.config_database.get_config_database', lambda: mock_db)

    # Mock list_plugins
    mock_plugins = [
        {'plugin_id': 'plex', 'name': 'Plex', 'service_type': 'media_server'},
        {'plugin_id': 'jellyfin', 'name': 'Jellyfin', 'service_type': 'media_server'},
        {'plugin_id': 'spotify', 'name': 'Spotify', 'service_type': 'metadata'}
    ]
    monkeypatch.setattr('web.services.plugin_registry.list_plugins', lambda: mock_plugins)

    # Mock PluginRegistry
    class MockPluginRegistry:
        @staticmethod
        def get_active_services_by_type(t):
            return [1] # Plex internal ID
            
        @staticmethod
        def get_plugin_class(plugin_id):
            mock_cls = MagicMock()
            from core.nexus_framework.plugin_SDK import PlaylistSupport
            # We mock the capabilities directly on the class
            mock_cls.capabilities.supports_playlists = PlaylistSupport.READ_WRITE
            
            # Mock Plex client behavior to avoid MagicMock in JSON
            mock_client = MagicMock()
            mock_client.ensure_connection.return_value = True
            
            mock_myplex = MagicMock()
            mock_myplex.id = 123
            mock_myplex.username = 'test_plex_user'
            mock_myplex.title = 'Test Plex User'
            mock_myplex.users.return_value = []
            
            mock_client.server.myPlexAccount.return_value = mock_myplex
            
            mock_cls.return_value = mock_client
            return mock_cls

    monkeypatch.setattr('core.nexus_framework.plugin_loader.PluginRegistry', MockPluginRegistry)

    response = client.get('/api/v1/system/accounts')
    assert response.status_code == 200
    
    data = response.json()
    assert 'music_accounts' in data
    assert 'media_users' in data

    # The active server is Plex, so 'plex' accounts should be skipped in music_accounts
    # Jellyfin and Spotify should be included since they are mock_cls (which has READ_WRITE)
    music_service_names = [s['service'] for s in data['music_accounts']]
    assert 'plex' not in music_service_names
    assert 'jellyfin' in music_service_names
    assert 'spotify' in music_service_names

def test_map_system_accounts(client, monkeypatch):
    """Verifies that account mapping endpoint handles correct parameters safely."""
    
    mock_db = MagicMock()
    monkeypatch.setattr('database.config_database.get_config_database', lambda: mock_db)

    # Make request
    payload = {
        'user_id': 100,
        'account_ids': [200, 300]
    }
    
    response = client.post('/api/v1/system/accounts/map', json=payload)
    assert response.status_code == 200
    assert response.json()['success'] is True

    # Verify deletions and sets
    mock_db.delete_account_mappings_for_account.assert_called_once_with(100)
    assert mock_db.set_account_mapping.call_count == 2
    mock_db.set_account_mapping.assert_any_call(100, 200)
    mock_db.set_account_mapping.assert_any_call(100, 300)
