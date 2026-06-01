from unittest.mock import patch

from core.oauth.sidecar import app


def test_oauth_sidecar_plugins_callback_proxies_to_plugin_route(monkeypatch):
    monkeypatch.setattr('core.oauth.sidecar.get_lan_ip', lambda: '192.168.1.11')
    monkeypatch.setattr('core.oauth.sidecar.get_main_app_port', lambda: 5000)

    class FakePlugin:
        name = 'EchoSync.spotify'

    monkeypatch.setattr(
        'core.nexus_framework.plugin_loader.PluginRegistry.get_plugin_class',
        staticmethod(lambda name: FakePlugin if name == 'spotify' else None),
    )

    with app.test_client() as client:
        resp = client.get('/api/oauth/callback/plugins/spotify?code=testcode&state=1')

    assert resp.status_code == 302
    assert resp.headers['Location'] == 'http://192.168.1.11:5000/api/plugins/spotify/callback?code=testcode&state=1'


def test_oauth_sidecar_tidal_callback_proxies_to_plugin_route(monkeypatch):
    monkeypatch.setattr('core.oauth.sidecar.get_lan_ip', lambda: '192.168.1.11')
    monkeypatch.setattr('core.oauth.sidecar.get_main_app_port', lambda: 5000)

    class FakePlugin:
        name = 'EchoSync.tidal'

    monkeypatch.setattr(
        'core.nexus_framework.plugin_loader.PluginRegistry.get_plugin_class',
        staticmethod(lambda name: FakePlugin if name == 'tidal' else None),
    )

    with app.test_client() as client:
        resp = client.get('/api/oauth/callback/plugins/tidal?code=testcode&state=1')

    assert resp.status_code == 302
    assert resp.headers['Location'] == 'http://192.168.1.11:5000/api/plugins/tidal/callback?code=testcode&state=1'
