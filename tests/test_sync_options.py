"""Tests for sync options builder to ensure dynamic source/target discovery."""


def test_build_sync_options_sources_and_targets(monkeypatch):
    import web.routes.sync as sync
    from plugins.plugin_system import PluginRegistry, PluginDeclaration, PluginType, PluginScope

    registry = PluginRegistry()
    monkeypatch.setattr(sync, "plugin_registry", registry)

    registry.register(PluginDeclaration(name='src_a', plugin_type=PluginType.PLAYLIST_PROVIDER, scope=[PluginScope.SYNC], enabled=True))
    registry.register(PluginDeclaration(name='src_b', plugin_type=PluginType.PLAYLIST_PROVIDER, scope=[PluginScope.SYNC], provides=['playlist.write'], enabled=True))
    registry.register(PluginDeclaration(name='lib_a', plugin_type=PluginType.LIBRARY_PROVIDER, scope=[PluginScope.LIBRARY], enabled=True))

    options = sync.build_sync_options()

    source_names = {p['name'] for p in options['sources']}
    provider_target_names = {p['name'] for p in options['targets']['providers']}
    library_target_names = {p['name'] for p in options['targets']['libraries']}

    assert 'src_a' in source_names
    assert 'src_b' in provider_target_names
    assert 'lib_a' in library_target_names
    assert options['multi_source_supported'] is True
    assert options['multi_target_supported'] is True


def test_build_sync_options_skips_disabled(monkeypatch):
    import web.routes.sync as sync
    from plugins.plugin_system import PluginRegistry, PluginDeclaration, PluginType, PluginScope

    registry = PluginRegistry()
    monkeypatch.setattr(sync, "plugin_registry", registry)

    registry.register(PluginDeclaration(name='active_src', plugin_type=PluginType.PLAYLIST_PROVIDER, scope=[PluginScope.SYNC], enabled=True))
    registry.register(PluginDeclaration(name='disabled_src', plugin_type=PluginType.PLAYLIST_PROVIDER, scope=[PluginScope.SYNC], enabled=False))

    options = sync.build_sync_options()
    names = {p['name'] for p in options['sources']}

    assert 'active_src' in names
    assert 'disabled_src' not in names
