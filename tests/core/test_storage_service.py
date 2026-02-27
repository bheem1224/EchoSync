import pytest

from core.storage import StorageService
from core import storage as storage_module
from core import account_manager as account_module
from core.settings import config_manager


class DummyDB:
    def __init__(self, accounts=None):
        self.accounts = accounts or []
        self._sid = 99

    def get_or_create_service_id(self, name):
        # just return a fixed id so callers can form queries
        return self._sid

    def get_accounts(self, service_id=None, is_active=None):
        # ignore filters for simplicity
        return list(self.accounts)


def test_list_accounts_prefers_database(monkeypatch):
    fake_accounts = [
        {'id': 1, 'service_id': 99, 'account_name': 'db1'},
        {'id': 2, 'service_id': 99, 'account_name': 'db2'},
    ]
    dummy = DummyDB(accounts=fake_accounts)
    monkeypatch.setattr('database.config_database.get_config_database', lambda: dummy)

    storage = StorageService()
    # spotify should use db results when present
    result = storage.list_accounts('spotify')
    assert result == fake_accounts

    # tidal should behave the same
    result = storage.list_accounts('tidal')
    assert result == fake_accounts


def test_list_accounts_fallback_to_legacy(monkeypatch):
    # database returns empty -> legacy config_manager used
    dummy = DummyDB(accounts=[])
    monkeypatch.setattr('database.config_database.get_config_database', lambda: dummy)

    monkeypatch.setattr(config_manager, 'get_spotify_accounts', lambda: [{'id': 5}])
    monkeypatch.setattr(config_manager, 'get_tidal_accounts', lambda: [{'id': 6}])

    storage = StorageService()
    assert storage.list_accounts('spotify') == [{'id': 5}]
    assert storage.list_accounts('tidal') == [{'id': 6}]


def test_account_manager_list_accounts(monkeypatch):
    # replicate same behaviour via AccountManager wrapper
    fake_accounts = [{'id': 7}]
    dummy = DummyDB(accounts=fake_accounts)
    monkeypatch.setattr('database.config_database.get_config_database', lambda: dummy)

    assert account_module.AccountManager.list_accounts('spotify') == fake_accounts
    assert account_module.AccountManager.list_accounts('tidal') == fake_accounts

    # fallback scenario
    dummy.accounts = []
    monkeypatch.setattr(config_manager, 'get_spotify_accounts', lambda: [{'id': 8}])
    monkeypatch.setattr(config_manager, 'get_tidal_accounts', lambda: [{'id': 9}])

    assert account_module.AccountManager.list_accounts('spotify') == [{'id': 8}]
    assert account_module.AccountManager.list_accounts('tidal') == [{'id': 9}]
