import pytest

from core import settings
from core.account_manager import AccountManager


def test_get_service_config_prefers_service_credentials(monkeypatch):
    """Values stored via ``get_service_credentials`` should take precedence.

    The old implementation always read Spotify/Tidal keys from the in-memory
    config_data, which meant that database entries (the UI writes) were
    ignored.  Verify that the new behaviour returns the credentials coming
    from ``config_manager.get_service_credentials`` regardless of what
    ``config_manager.get`` would otherwise provide.
    """
    # simulate database-backed credentials
    monkeypatch.setattr(settings.config_manager, "get_service_credentials", lambda svc: {"client_id": "db-id"})
    monkeypatch.setattr(settings.config_manager, "get", lambda key, default=None: "legacy-id")

    assert AccountManager.get_service_config("spotify", "client_id") == "db-id"
    # non-spotify service should behave the same
    assert AccountManager.get_service_config("plex", "client_id") == "db-id"


def test_get_service_config_legacy_fallback(monkeypatch):
    """When no credentials exist in the DB, fall back to the legacy config.

    This ensures backwards compatibility with older setups that still
    populate ``config_data`` and have not migrated to the service_config
    table.
    """
    monkeypatch.setattr(settings.config_manager, "get_service_credentials", lambda svc: {})
    monkeypatch.setattr(settings.config_manager, "get", lambda key, default=None: f"legacy-{key}")

    assert AccountManager.get_service_config("spotify", "client_id") == "legacy-spotify.client_id"
    assert AccountManager.get_service_config("foobar", "xyz") == "legacy-foobar.xyz"


def test_get_service_config_missing(monkeypatch):
    """If nothing is stored anywhere, ``None`` is returned."""
    monkeypatch.setattr(settings.config_manager, "get_service_credentials", lambda svc: {})
    monkeypatch.setattr(settings.config_manager, "get", lambda key, default=None: default)

    assert AccountManager.get_service_config("spotify", "client_id") is None
    assert AccountManager.get_service_config("foo", "bar") is None
