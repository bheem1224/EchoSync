
import pytest
from unittest.mock import MagicMock, patch
from providers.spotify.client import SpotifyClient

@pytest.fixture
def spotify_client():
    # Use a dummy client ID so ConfigCacheHandler doesn't fail if it tries to init
    with patch('core.settings.ConfigManager.get_spotify_config') as mock_config:
        mock_config.return_value = {'client_id': 'fake', 'client_secret': 'fake'}
        client = SpotifyClient()
        return client

def test_initialization(spotify_client):
    assert spotify_client.name == 'spotify'
    assert spotify_client.supports_downloads is False
    # sp may be initialized or None depending on credentials
    assert hasattr(spotify_client, 'sp')

def test_is_configured_false(spotify_client):
    # Reset sp to test unconfigured state
    spotify_client.sp = None
    with patch('sdk.storage_service.get_storage_service') as mock_storage:
        mock_storage_instance = MagicMock()
        mock_storage_instance.get_service_config.return_value = None
        mock_storage.return_value = mock_storage_instance
        assert spotify_client.is_configured() is False

def test_is_configured_true(spotify_client):
    spotify_client.sp = MagicMock()
    assert spotify_client.is_configured() is True


def test_existing_token_scope_does_not_invalidate(monkeypatch):
    """If an account already has tokens with a narrower set of scopes, the
    client should not treat the account as unauthenticated when initializing.
    """
    # prepare a token with read-only scopes (missing modify permissions)
    limited_scope = (
        "user-library-read user-read-private playlist-read-private "
        "playlist-read-collaborative user-read-email"
    )
    limited_token = {
        'access_token': 'x',
        'refresh_token': 'y',
        'expires_at': int(__import__('time').time()) + 3600,
        'scope': limited_scope,
        'token_type': 'Bearer'
    }

    # patch ConfigCacheHandler methods to return our limited token
    def fake_get_cached_token(self):
        return limited_token
    def fake_save_token(self, token_info):
        pass
    monkeypatch.setattr('providers.spotify.client.ConfigCacheHandler.get_cached_token', fake_get_cached_token)
    monkeypatch.setattr('providers.spotify.client.ConfigCacheHandler.save_token_to_cache', fake_save_token)

    # fake SpotifyOAuth to capture the requested scope and use our dummy token
    created = {}
    class FakeSpotifyOAuth:
        def __init__(self, client_id, client_secret, redirect_uri, scope, cache_handler, show_dialog, open_browser):
            created['scope'] = scope
            self.cache_handler = cache_handler
        def get_cached_token(self):
            return self.cache_handler.get_cached_token()
        def refresh_access_token(self, refresh_token):
            return limited_token

    # patch the reference used inside spotify.client module
    monkeypatch.setattr('providers.spotify.client.SpotifyOAuth', FakeSpotifyOAuth)

    # patch storage service to provide dummy credentials
    with patch('sdk.storage_service.get_storage_service') as mock_storage:
        ms = MagicMock()
        ms.get_service_config.return_value = 'fake'
        mock_storage.return_value = ms

        client = SpotifyClient(account_id=5)
        # initialization should have used the existing token's scope
        assert created.get('scope') == limited_scope
        assert client.is_authenticated() is True


def test_cached_scope_used_even_if_oauth_invalidates(monkeypatch):
    """Even if SpotifyOAuth reports no valid token, the client should still
    initialize using the scope string from the preloaded token instead of
    falling back to the full default set.
    """
    limited_scope = (
        "user-library-read user-read-private playlist-read-private "
        "playlist-read-collaborative user-read-email"
    )
    limited_token = {
        'access_token': 'x',
        'refresh_token': 'y',
        'expires_at': int(__import__('time').time()) + 3600,
        'scope': limited_scope,
        'token_type': 'Bearer'
    }

    # token will be returned by preloading step
    def fake_get_cached_token2(self):
        return limited_token
    def fake_save_token2(token_info):
        pass
    monkeypatch.setattr('providers.spotify.client.ConfigCacheHandler.get_cached_token', fake_get_cached_token2)
    monkeypatch.setattr('providers.spotify.client.ConfigCacheHandler.save_token_to_cache', fake_save_token2)

    # simulate SpotifyOAuth dropping the token during validation
    created = {}
    class FakeSpotifyOAuth2:
        def __init__(self, client_id, client_secret, redirect_uri, scope, cache_handler, show_dialog, open_browser):
            created['scope'] = scope
            self.cache_handler = cache_handler
        def get_cached_token(self):
            # OAuth will return None because it deemed token invalid
            return None
        def refresh_access_token(self, refresh_token):
            return None

    monkeypatch.setattr('providers.spotify.client.SpotifyOAuth', FakeSpotifyOAuth2)

    with patch('sdk.storage_service.get_storage_service') as mock_storage:
        ms = MagicMock()
        ms.get_service_config.return_value = 'fake'
        mock_storage.return_value = ms
        client = SpotifyClient(account_id=6)
        # we should still have initialized with the limited scope value
        assert created.get('scope') == limited_scope
        # authentication check will still be False because OAuth said token invalid
        assert client.is_authenticated() is False
