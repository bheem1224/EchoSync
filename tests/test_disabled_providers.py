import pytest

from core.settings import config_manager
from core.provider import ProviderRegistry as CoreProviderRegistry
from web.services.provider_registry import list_providers
from web.services.library_service import LibraryAdapter


def setup_function(func):
    # Clear disabled list before each test
    config_manager.set_disabled_providers([])


def teardown_function(func):
    # Reset disabled list after test
    config_manager.set_disabled_providers([])


def test_list_providers_marks_disabled_and_skips_instantiation(monkeypatch):
    # disable tidal provider for this test
    config_manager.set_disabled_providers(['tidal'])

    created = []
    orig = CoreProviderRegistry.create_instance

    def spy(name, *args, **kwargs):
        created.append(name)
        return orig(name, *args, **kwargs)

    monkeypatch.setattr(CoreProviderRegistry, 'create_instance', spy)

    items = list_providers()
    # find tidal entry
    tidal_entry = next((p for p in items if p['id'] == 'tidal'), None)
    assert tidal_entry is not None, "tidal provider should still be listed"
    assert tidal_entry['disabled'] is True
    assert tidal_entry['is_configured'] is False

    # ensure create_instance was NOT called for tidal
    assert 'tidal' not in created


def test_library_overview_skips_disabled(monkeypatch):
    # disable navidrome provider
    config_manager.set_disabled_providers(['navidrome'])

    # monkeypatch ProviderRegistry.list_providers to return fixed set
    orig_list = CoreProviderRegistry.list_providers
    monkeypatch.setattr(CoreProviderRegistry, 'list_providers', lambda: ['plex', 'navidrome'])

    # also monkeypatch get_provider_capabilities to return simple objects
    class DummyCaps:
        supports_library_scan = True
        metadata = type('T', (), {'name': 'MEDIUM'})
    monkeypatch.setattr('web.services.library_service.get_provider_capabilities', lambda name: DummyCaps())

    adapter = LibraryAdapter()
    overview = adapter.overview()
    servers = overview.get('servers', [])
    names = [s['name'] for s in servers]
    assert 'navidrome' not in names
    # plex should still be present
    assert 'plex' in names

    # restore
    monkeypatch.setattr(CoreProviderRegistry, 'list_providers', orig_list)
