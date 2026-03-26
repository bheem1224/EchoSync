import pytest
from unittest.mock import MagicMock, patch
from flask import Flask
from core.matching_engine.soul_sync_track import SoulSyncTrack

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
    ``ConfigDatabase`` such that the "database" value differs from the
    legacy config and ensure the route prefers the former.
    """
    class FakeConfigDB:
        def get_or_create_service_id(self, name):
            return 1
        def get_service_config(self, sid, key):
            if key == 'client_id': return 'db1'
            if key == 'client_secret': return 'db2'
            if key == 'redirect_uri': return 'db3'
            return None

    with patch('database.config_database.get_config_database', return_value=FakeConfigDB()):
        resp = client.get('/api/providers/spotify/settings')
        assert resp.status_code == 200
        data = resp.get_json()
        settings = data.get('settings', {})
        assert settings.get('client_id') == 'db1'
        assert settings.get('client_secret') == 'db2'
        # The new dynamic routing ensures redirect_uri contains the sidecar proxy format
        assert 'https://' in settings.get('redirect_uri')
        assert ':5001/api/oauth/callback/spotify' in settings.get('redirect_uri')


def test_providers_playlist_route_includes_account_id(client, monkeypatch):
    """The providers playlist endpoint should return playlists with account_id for multi-account providers."""
    class FakeConfigDB:
        def get_or_create_service_id(self, name):
            return 77

        def get_accounts(self, service_id=None, is_active=None):
            assert service_id == 77
            assert is_active is True
            return [
                {'id': 10, 'display_name': 'First', 'account_name': 'First', 'user_id': 'plex-user-1'},
                {'id': 20, 'display_name': 'Second', 'account_name': 'Second', 'user_id': 'plex-user-2'},
            ]

    # fake storage service to return two spotify accounts
    fake_storage = MagicMock()
    fake_storage.list_accounts.return_value = [
        {'id': 1, 'display_name': 'First'},
        {'id': 2, 'display_name': 'Second'}
    ]
    monkeypatch.setattr('core.file_handling.storage.get_storage_service', lambda: fake_storage)
    monkeypatch.setattr('database.config_database.get_config_database', lambda: FakeConfigDB())

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
    assert any(item.get('target_user_id') == 'plex-user-1' for item in items)
    assert any(item.get('target_user_id') == 'plex-user-2' for item in items)
    # Since we removed account name suffix from the UI string, we check source_account_name instead
    assert items[0]['source_account_name'] in ['First', 'Second']


def test_analyze_playlists_honors_account_id(client, monkeypatch):
    """analyze_playlists should instantiate provider per-account when account_id supplied."""
    fake_storage = MagicMock()
    fake_storage.list_accounts.return_value = [{'id': 1}, {'id': 2}]
    monkeypatch.setattr('core.file_handling.storage.get_storage_service', lambda: fake_storage)

    called = []

    class FakeSpotifyClient:
        # Add capabilities to bypass strict capability check in analyze route
        from core.provider import ProviderCapabilities, PlaylistSupport, SearchCapabilities, MetadataRichness
        capabilities = ProviderCapabilities(
            name='spotify',
            supports_playlists=PlaylistSupport.READ_WRITE,
            search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=True),
            metadata=MetadataRichness.HIGH
        )

        def __init__(self, account_id=None):
            self.account_id = account_id
        def is_configured(self):
            return True
        def get_playlist_tracks(self, playlist_id, **kwargs):
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


def test_download_missing_hydrates_from_full_source_track_payload(client, monkeypatch):
    queued = []
    process_calls = []

    class FakeDownloadManager:
        def queue_download(self, track):
            queued.append(track)
            return 123

        def process_downloads_now(self):
            process_calls.append(True)

    monkeypatch.setattr('services.download_manager.get_download_manager', lambda: FakeDownloadManager())

    source_track = SoulSyncTrack(
        raw_title='My Song',
        artist_name='My Artist',
        album_title='My Album',
        duration=210000,
        isrc='USRC17607839',
        identifiers={'spotify': 'spotify-track-id'},
    )

    resp = client.post('/api/playlists/download-missing', json={
        'missing': [{
            'title': 'My Song',
            'artist': 'My Artist',
            'album': 'My Album',
            'source_track': source_track.to_dict(),
        }]
    })

    assert resp.status_code == 200
    assert len(queued) == 1
    assert queued[0].duration == 210000
    assert queued[0].isrc == 'USRC17607839'
    assert process_calls == [True]


def test_download_missing_preserves_duration_and_isrc_from_fallback_fields(client, monkeypatch):
    queued = []
    process_calls = []

    class FakeDownloadManager:
        def queue_download(self, track):
            queued.append(track)
            return 124

        def process_downloads_now(self):
            process_calls.append(True)

    monkeypatch.setattr('services.download_manager.get_download_manager', lambda: FakeDownloadManager())

    resp = client.post('/api/playlists/download-missing', json={
        'missing': [{
            'title': 'Fallback Song',
            'artist': 'Fallback Artist',
            'album': 'Fallback Album',
            'duration': 198000,
            'isrc': 'GBUM71029604',
            'source_identifier': 'spotify-fallback-id',
        }]
    })

    assert resp.status_code == 200
    assert len(queued) == 1
    assert queued[0].duration == 198000
    assert queued[0].isrc == 'GBUM71029604'
    assert queued[0].identifiers.get('spotify') == 'spotify-fallback-id'
    assert process_calls == [True]
