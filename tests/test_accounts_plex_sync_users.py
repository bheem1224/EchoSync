from unittest.mock import MagicMock

import pytest


@pytest.fixture
def client():
    from web.api_app import create_app

    app = create_app()
    with app.test_client() as test_client:
        yield test_client


def test_sync_plex_users_endpoint_returns_updated_accounts(client, monkeypatch):
    fake_storage = MagicMock()
    fake_storage.list_accounts.return_value = [
        {'id': 1, 'display_name': 'Admin', 'user_id': 'admin-uuid'},
        {'id': 2, 'display_name': 'Kiddo', 'user_id': 'managed-1'},
    ]
    monkeypatch.setattr('web.routes.accounts.get_storage_service', lambda: fake_storage)

    fake_client = MagicMock()
    fake_client.import_managed_users.return_value = fake_storage.list_accounts.return_value
    monkeypatch.setattr('providers.plex.client.PlexClient', lambda *args, **kwargs: fake_client)

    response = client.post('/api/accounts/plex/sync_users')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['service'] == 'plex'
    assert payload['total'] == 2
    assert len(payload['accounts']) == 2