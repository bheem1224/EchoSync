"""Tests for search aggregation adapter and endpoint filters."""

import pytest
from flask import Flask


def _fake_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


def test_search_adapter_filters_enabled(monkeypatch):
    import web.services.search_service as search_service
    from plugins.plugin_system import PluginRegistry, PluginDeclaration, PluginType, PluginScope
    from core.provider_capabilities import ProviderCapabilities, SearchCapabilities, MetadataRichness, PlaylistSupport

    registry = PluginRegistry()
    monkeypatch.setattr(search_service, "plugin_registry", registry)

    caps_map = {
        'search_a': ProviderCapabilities('search_a', supports_playlists=PlaylistSupport.NONE, search=SearchCapabilities(tracks=True), metadata=MetadataRichness.HIGH),
        'search_b': ProviderCapabilities('search_b', supports_playlists=PlaylistSupport.NONE, search=SearchCapabilities(tracks=False), metadata=MetadataRichness.MEDIUM),
    }
    monkeypatch.setattr(search_service, "get_provider_capabilities", lambda name: caps_map[name])

    registry.register(PluginDeclaration(name='search_a', plugin_type=PluginType.PLAYLIST_PROVIDER, scope=[PluginScope.SEARCH], enabled=True))
    registry.register(PluginDeclaration(name='search_b', plugin_type=PluginType.PLAYLIST_PROVIDER, scope=[PluginScope.SEARCH], enabled=False))

    adapter = search_service.SearchAdapter()
    results = adapter.aggregate("hello", search_types=["tracks"])

    assert any(r['provider'] == 'search_a' for r in results)
    assert all(r['provider'] != 'search_b' for r in results)


def test_search_endpoint_respects_provider_filter(monkeypatch):
    import web.routes.search as search_route
    import web.services.search_service as search_service

    app = _fake_app()

    # Stub adapter to capture provider_names
    captured = {}

    class StubAdapter:
        def aggregate(self, q, provider_names=None, search_types=None):
            captured['q'] = q
            captured['provider_names'] = provider_names
            captured['search_types'] = search_types
            return []

    monkeypatch.setattr(search_route, "SearchAdapter", lambda: StubAdapter())

    with app.test_request_context('/api/search?q=beat&providers=a,b&types=tracks,artists'):
        resp = search_route.aggregate_search()
        assert resp[1] == 200
        assert captured['q'] == 'beat'
        assert captured['provider_names'] == ['a', 'b']
        assert set(captured['search_types']) == {'tracks', 'artists'}


def test_search_route_endpoint_validation(monkeypatch):
    import web.routes.search as search_route
    import web.services.search_service as search_service
    app = _fake_app()

    class StubAdapter:
        def route_result(self, item=None, action=None, target=None):
            if not item or action != 'download':
                return {"accepted": False}
            return {"accepted": True}

    monkeypatch.setattr(search_route, "SearchAdapter", lambda: StubAdapter())

    with app.test_request_context('/api/search/route', json={"item": {"title": "t"}, "action": "download"}):
        resp = search_route.route_search_result()
        assert resp[1] == 202

    with app.test_request_context('/api/search/route', json={"item": None, "action": "download"}):
        resp = search_route.route_search_result()
        assert resp[1] == 400
