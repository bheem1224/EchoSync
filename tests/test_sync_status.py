"""Tests for the sync status builder and endpoint stub."""

import pytest


def test_build_sync_status_basic():
    from web.routes.sync import build_sync_status
    status = build_sync_status()
    assert 'last_run' in status
    assert 'running_jobs' in status
    assert 'queued_jobs' in status
    assert 'errors' in status
    assert 'active_sync_providers' in status
    assert isinstance(status['errors'], list)


def test_build_sync_status_sync_providers_count(monkeypatch):
    from web.routes.sync import build_sync_status
    from plugins.plugin_system import PluginDeclaration, PluginScope, plugin_registry, PluginType

    # Temporarily register fake sync-scoped plugins
    decl1 = PluginDeclaration(name='test_sync_1', plugin_type=PluginType.PLAYLIST_PROVIDER, scope=[PluginScope.SYNC], enabled=True)
    decl2 = PluginDeclaration(name='test_sync_2', plugin_type=PluginType.PLAYLIST_PROVIDER, scope=[PluginScope.SYNC], enabled=False)

    plugin_registry.register(decl1)
    plugin_registry.register(decl2)

    status = build_sync_status()
    # Only enabled sync providers counted
    assert status['active_sync_providers'] >= 1
