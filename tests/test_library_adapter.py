"""Tests for LibraryAdapter overview and library route."""

from flask import Flask


def _fake_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


def test_library_adapter_overview(monkeypatch):
    import web.services.library_service as lib_service
    from plugins.plugin_system import PluginRegistry, PluginDeclaration, PluginType, PluginScope
    from core.provider_capabilities import ProviderCapabilities, SearchCapabilities, MetadataRichness, PlaylistSupport

    registry = PluginRegistry()
    monkeypatch.setattr(lib_service, "plugin_registry", registry)

    caps_map = {
        'plex': ProviderCapabilities('plex', supports_playlists=PlaylistSupport.READ, search=SearchCapabilities(tracks=True), metadata=MetadataRichness.HIGH, supports_library_scan=True),
    }
    monkeypatch.setattr(lib_service, "get_provider_capabilities", lambda name: caps_map[name])

    registry.register(PluginDeclaration(name='plex', plugin_type=PluginType.LIBRARY_PROVIDER, scope=[PluginScope.LIBRARY], enabled=True))

    adapter = lib_service.LibraryAdapter()
    data = adapter.overview()

    assert data['servers'][0]['name'] == 'plex'
    assert data['servers'][0]['metadata_richness'] == 'HIGH'
    assert data['stats']['total_tracks'] >= 1
    assert data['tracks'][0]['source_provider'] == 'plex'
    assert data['tracks'][0]['metadata_completeness'] in ('standard', 'complete')


def test_library_route(monkeypatch):
    import web.routes.library as lib_route
    import web.services.library_service as lib_service

    app = _fake_app()

    class StubAdapter:
        def overview(self):
            return {"servers": [{"name": "stub", "metadata_richness": "MEDIUM"}], "stats": {"total_tracks": 1}, "tracks": [], "artists": []}

    monkeypatch.setattr(lib_route, "LibraryAdapter", lambda: StubAdapter())

    with app.test_request_context('/api/library'):
        resp = lib_route.library_overview()
        assert resp[1] == 200
        assert resp[0].get_json()['servers'][0]['name'] == 'stub'
