import pytest
from unittest.mock import MagicMock, patch

from web.api_app import create_app


def make_client():
    app = create_app()
    return app.test_client()


def test_get_settings_uses_storage(monkeypatch):
    """GET /settings should query storage for api_key and return masked value."""
    client = make_client()

    fake_storage = MagicMock()
    fake_storage.get_service_config.return_value = 'secretkey'
    monkeypatch.setattr('core.storage.get_storage_service', lambda: fake_storage)

    # ensure config_manager.get still returns some values
    with patch('core.settings.config_manager.get', side_effect=lambda k, d=None: {
        'soulseek.slskd_url': 'http://example',
        'soulseek.server_name': 'foo'
    }.get(k, d)):
        resp = client.get('/api/providers/soulseek/settings')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['slskd_url'] == 'http://example'
    assert data['server_name'] == 'foo'
    assert data['api_key'] == '****'  # masked
    assert data['has_api_key'] is True

    # storage.get_service_config should have been called
    fake_storage.get_service_config.assert_called_with('soulseek', 'api_key')


def test_save_settings_writes_api_key_to_db(monkeypatch):
    """POST /settings should save api_key via storage service and not overwrite with empty."""
    client = make_client()

    fake_storage = MagicMock()
    monkeypatch.setattr('core.storage.get_storage_service', lambda: fake_storage)

    payload = {
        'slskd_url': 'http://example',
        'server_name': 'foo',
        'api_key': 'newkey'
    }

    # intercept config_manager.set calls
    sets = []
    monkeypatch.setattr('core.settings.config_manager.set', lambda k, v: sets.append((k, v)))

    resp = client.post('/api/providers/soulseek/settings', json=payload)
    assert resp.status_code == 200
    assert resp.get_json().get('success') is True

    # verify storage set_service_config was invoked with secret flag
    fake_storage.set_service_config.assert_called_with('soulseek', 'api_key', 'newkey', is_sensitive=True)

    # config_manager should have been updated for url/server_name and reflect api_key mirror
    assert ('soulseek.slskd_url', 'http://example') in sets
    assert ('soulseek.server_name', 'foo') in sets
    assert ('soulseek.api_key', 'newkey') in sets


def test_save_settings_does_not_overwrite_empty_key(monkeypatch):
    client = make_client()
    fake_storage = MagicMock()
    monkeypatch.setattr('core.storage.get_storage_service', lambda: fake_storage)
    sets = []
    monkeypatch.setattr('core.settings.config_manager.set', lambda k, v: sets.append((k, v)))

    payload = {'slskd_url': 'http://example', 'server_name': 'foo', 'api_key': ''}
    resp = client.post('/api/providers/soulseek/settings', json=payload)
    assert resp.status_code == 200
    # storage should not be called for empty api key
    fake_storage.set_service_config.assert_not_called()

    assert ('soulseek.slskd_url', 'http://example') in sets
    assert ('soulseek.server_name', 'foo') in sets
    assert all(k != 'soulseek.api_key' for k, _ in sets)
