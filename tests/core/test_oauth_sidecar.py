from unittest.mock import patch

from core.oauth.sidecar import app


def test_oauth_sidecar_plugins_callback_proxies_to_plugin_route(monkeypatch):
    monkeypatch.setattr('core.oauth.sidecar.get_lan_ip', lambda: '192.168.1.11')
    monkeypatch.setattr('core.oauth.sidecar.get_main_app_port', lambda: 5000)

    with app.test_client() as client:
        resp = client.get('/api/oauth/callback/plugins/spotify?code=testcode&state=1')

    assert resp.status_code == 302
    assert resp.headers['Location'] == 'http://192.168.1.11:5000/api/plugins/spotify/callback?code=testcode&state=1'
