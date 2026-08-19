
import pytest
from unittest.mock import MagicMock, patch
from plugins.EchoSync.Spotify.client import SpotifyClient

@pytest.fixture
def spotify_client():
    # Use a dummy client ID so ConfigCacheHandler doesn't fail if it tries to init
    with patch('core.settings.ConfigManager.get_service_credentials') as mock_creds:
        mock_creds.return_value = {'client_id': 'fake', 'client_secret': 'fake'}
        client = SpotifyClient()
        return client

def test_initialization(spotify_client):
    assert spotify_client.name == 'EchoSync.spotify'
    assert spotify_client.supports_downloads is False
    # sp may be initialized or None depending on credentials
    assert hasattr(spotify_client, 'sp')

def test_is_configured_false(spotify_client):
    # Reset sp to test unconfigured state
    spotify_client.sp = None
    with patch('core.file_handling.storage.get_storage_service') as mock_storage, \
         patch('database.config_database.get_config_database') as mock_db_fn:
        mock_db = MagicMock()
        mock_db.get_service_id.return_value = None
        mock_db.get_or_create_service_id.return_value = None
        mock_db.get_service_config.return_value = None
        mock_db_fn.return_value = mock_db
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
    monkeypatch.setattr('plugins.EchoSync.Spotify.client.ConfigCacheHandler.get_cached_token', fake_get_cached_token)
    monkeypatch.setattr('plugins.EchoSync.Spotify.client.ConfigCacheHandler.save_token_to_cache', fake_save_token)

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
    monkeypatch.setattr('plugins.EchoSync.Spotify.client.SpotifyOAuth', FakeSpotifyOAuth)

    # patch account manager to provide dummy credentials
    with patch('core.account_manager.AccountManager.get_account', return_value={'client_id': 'fake', 'client_secret': 'fake'}):
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
    monkeypatch.setattr('plugins.EchoSync.Spotify.client.ConfigCacheHandler.get_cached_token', fake_get_cached_token2)
    monkeypatch.setattr('plugins.EchoSync.Spotify.client.ConfigCacheHandler.save_token_to_cache', fake_save_token2)

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

    monkeypatch.setattr('plugins.EchoSync.Spotify.client.SpotifyOAuth', FakeSpotifyOAuth2)

    with patch('core.account_manager.AccountManager.get_account', return_value={'client_id': 'fake', 'client_secret': 'fake'}):
        with patch('core.account_manager.AccountManager.get_account_token', return_value=limited_token):
            client = SpotifyClient(account_id=6)
            # we should still have initialized with the limited scope value
            assert created.get('scope') == limited_scope
            # authentication check should be True because we verify cached token in is_authenticated()
            # even if OAuth object failed to initialize fully
            assert client.is_authenticated() is True


def test_setup_client_prefers_account_creds(monkeypatch):
    """Instantiation should pull credentials from the named account."""
    captured = {}
    class FakeSpotifyOAuth3:
        def __init__(self, client_id, client_secret, redirect_uri, scope, cache_handler, show_dialog, open_browser):
            captured['client_id'] = client_id
            captured['client_secret'] = client_secret
            captured['redirect_uri'] = redirect_uri
            self.cache_handler = cache_handler
        def get_cached_token(self):
            return None
        def refresh_access_token(self, refresh_token):
            return None

    monkeypatch.setattr('plugins.EchoSync.Spotify.client.SpotifyOAuth', FakeSpotifyOAuth3)
    # no global credentials present
    monkeypatch.setattr('core.account_manager.AccountManager.get_service_config', lambda svc, key: None)
    # return an account with its own creds
    monkeypatch.setattr('core.account_manager.AccountManager.get_account',
                        lambda svc, aid: {'client_id': 'acctid', 'client_secret': 'acctsec', 'redirect_uri': 'acct://cb'})

    client = SpotifyClient(account_id=99)
    assert captured.get('client_id') == 'acctid'
    assert captured.get('client_secret') == 'acctsec'
    assert captured.get('redirect_uri') == 'acct://cb'


def test_search_by_isrc_with_default_account(monkeypatch):
    """search_by_isrc resolves the default active account and executes query."""
    dummy_track = {
        'id': 'spotify123',
        'name': 'Midnight City',
        'artists': [{'name': 'M83'}],
        'album': {'name': 'Hurry Up, We\'re Dreaming', 'release_date': '2011-10-18'},
        'duration_ms': 243000,
        'external_ids': {'isrc': 'FRUM71100370'}
    }

    mock_sp = MagicMock()
    mock_sp.search.return_value = {'tracks': {'items': [dummy_track]}}

    with patch('core.settings.ConfigManager.get_service_credentials', return_value={'client_id': 'id', 'client_secret': 'sec'}), \
         patch('core.account_manager.AccountManager.list_accounts', return_value=[{'id': 42, 'is_active': True}]):
        client = SpotifyClient(account_id=None)
        client.sp = mock_sp

        track = client.search_by_isrc('FR-UM7-11-00370')
        assert track is not None
        assert track.raw_title == 'Midnight City'
        assert track.artist_name == 'M83'
        assert track.album_title == "Hurry Up, We're Dreaming"
        assert track.release_year == 2011
        assert track.isrc == 'FRUM71100370'
        assert track.identifiers.get('source') == 'EchoSync.spotify'
        mock_sp.search.assert_called_once_with(q='isrc:FRUM71100370', type='track', limit=1)


def test_client_credentials_fallback_when_no_user_accounts(monkeypatch):
    """When no user accounts exist, client uses SpotifyClientCredentials."""
    captured = {}
    class FakeClientCredentials:
        def __init__(self, client_id, client_secret):
            captured['client_id'] = client_id
            captured['client_secret'] = client_secret

    import sys
    for mod_name in list(sys.modules.keys()):
        if 'spotify.client' in mod_name.lower():
            mod = sys.modules[mod_name]
            if hasattr(mod, 'SpotifyClientCredentials'):
                monkeypatch.setattr(mod, 'SpotifyClientCredentials', FakeClientCredentials)
    monkeypatch.setattr('spotipy.oauth2.SpotifyClientCredentials', FakeClientCredentials)

    mock_storage = MagicMock()
    mock_storage.list_accounts.return_value = []

    with patch('core.settings.ConfigManager.get_service_credentials', return_value={'client_id': 'app_id', 'client_secret': 'app_sec'}), \
         patch('core.account_manager.AccountManager.list_accounts', return_value=[]), \
         patch('core.file_handling.storage.get_storage_service', return_value=mock_storage), \
         patch('core.account_manager.AccountManager.get_service_config', side_effect=lambda svc, key: {'client_id': 'app_id', 'client_secret': 'app_sec'}.get(key)):
        client = SpotifyClient(account_id=None)
        assert captured.get('client_id') == 'app_id'
        assert captured.get('client_secret') == 'app_sec'
        assert client.is_authenticated() is True

