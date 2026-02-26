import pytest
from unittest.mock import MagicMock, patch
from flask import Flask

# reuse client fixture from other tests

def create_test_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    # register blueprints manually if necessary
    from web.api_app import create_app
    return create_app()

@pytest.fixture
def client():
    from flask import Flask
    from web.api_app import create_app
    app = create_app()
    with app.test_client() as c:
        yield c


def test_provider_settings_route_uses_service_config(client, monkeypatch):
    """GET /api/providers/<provider>/settings should surface database credentials.

    This test exercises the end-to-end path used by the web UI.  We patch
    ``config_manager`` such that the "database" value differs from the
    legacy config and ensure the route prefers the former.
    """
    monkeypatch.setattr('core.settings.config_manager.get_service_credentials',
                        lambda svc: {'client_id': 'db1', 'client_secret': 'db2', 'redirect_uri': 'db3'})
    # legacy getter returns a different value so we can tell which one was used
    monkeypatch.setattr('core.settings.config_manager.get', lambda key, default=None: 'legacy')

    resp = client.get('/api/providers/spotify/settings')
    assert resp.status_code == 200
    data = resp.get_json()
    settings = data.get('settings', {})
    assert settings.get('client_id') == 'db1'
    assert settings.get('client_secret') == 'db2'
    assert settings.get('redirect_uri') == 'db3'


def test_providers_playlist_route_includes_account_id(client, monkeypatch):
    """The providers playlist endpoint should return playlists with account_id for multi-account providers."""
    # fake account manager to return two spotify accounts
    monkeypatch.setattr('core.account_manager.AccountManager.list_accounts',
                        lambda service: [
                            {'id': 1, 'display_name': 'First', 'client_id': 'id1', 'client_secret': 'sec1'},
                            {'id': 2, 'display_name': 'Second', 'client_id': 'id2', 'client_secret': 'sec2'}
                        ] if service == 'spotify' else [])

    # fake SpotifyClient to return one playlist per account with distinctive id
    class FakeSpotifyClient:
        # provider registry expects a `name` attribute on the class
        name = "spotify"
        def __init__(self, account_id=None):
            self.account_id = account_id
        def is_configured(self):
            return True
        def get_user_playlists(self):
            # return a list with a single dict
            return [{'id': f'pl{self.account_id}', 'name': f'Playlist {self.account_id}', 'track_count': 5}]

    monkeypatch.setattr('providers.spotify.client.SpotifyClient', FakeSpotifyClient)

    resp = client.get('/api/providers/spotify/playlists')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['provider'] == 'spotify'
    items = data['items']
    # we should have two items, one per account
    assert len(items) == 2
    # each item should include account_id field
    assert any(item.get('account_id') == 1 for item in items)
    assert any(item.get('account_id') == 2 for item in items)
    # names should contain account name suffix
    assert 'First' in items[0]['name'] or 'Second' in items[0]['name']


def test_analyze_playlists_honors_account_id(client, monkeypatch):
    """analyze_playlists should instantiate provider per-account when account_id supplied."""
    # Mock AccountManager to return fake accounts when needed
    monkeypatch.setattr('core.account_manager.AccountManager.list_accounts',
                        lambda service: [{'id': 1, 'client_id': '1'}, {'id': 2, 'client_id': '2'}] if service == 'spotify' else [])

    called = []

    class FakeSpotifyClient:
        def __init__(self, account_id=None):
            self.account_id = account_id
        def is_configured(self):
            return True
        def get_playlist_tracks(self, playlist_id):
            # record invocation for assertion
            called.append((self.account_id, playlist_id))
            # return a minimal track object with attributes used in analysis
            class Track:
                def __init__(self, title, artist_name, album_title, duration):
                    self.title = title
                    self.artist_name = artist_name
                    self.album_title = album_title
                    self.duration = duration
                    self.identifiers = {}
            return [Track(f"t_{playlist_id}", "A", "B", 1234)]

    monkeypatch.setattr('providers.spotify.client.SpotifyClient', FakeSpotifyClient)

    payload = {
        'source': 'spotify',
        'playlists': [
            {'id': 'p1', 'name': 'P1', 'account_id': 1},
            {'id': 'p2', 'name': 'P2', 'account_id': 2},
        ],
        'quality_profile': 'Auto',
        'target': 'plex'
    }

    resp = client.post('/api/playlists/analyze', json=payload)
    assert resp.status_code == 200
    # ensure provider was called separately for each account/playlist
    assert (1, 'p1') in called
    assert (2, 'p2') in called
