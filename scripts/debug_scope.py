from providers.spotify.client import SpotifyClient, ConfigCacheHandler
import spotipy

# fake storage service
from sdk.storage_service import get_storage_service as real_get_storage

def fake_get_storage():
    class S:
        def get_service_config(self, k):
            return 'fake'
    return S()

import sdk.storage_service
sdk.storage_service.get_storage_service = fake_get_storage

limited_scope = "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email"
limited_token = {
    'access_token':'x',
    'refresh_token':'y',
    'expires_at':int(__import__('time').time())+3600,
    'scope':limited_scope,
    'token_type':'Bearer'
}

# patch cache handler
ConfigCacheHandler.get_cached_token = lambda self: limited_token
ConfigCacheHandler.save_token_to_cache = lambda self, t: None

# fake OAuth
class FakeSpotifyOAuth:
    def __init__(self, client_id, client_secret, redirect_uri, scope, cache_handler, show_dialog, open_browser):
        print('FakeSpotifyOAuth init scope=',scope)
        self.cache_handler = cache_handler
    def get_cached_token(self):
        return self.cache_handler.get_cached_token()
    def refresh_access_token(self, refresh_token):
        print('Fake refresh called')
        return limited_token

spotipy.oauth2.SpotifyOAuth = FakeSpotifyOAuth

print('Creating client')
client = SpotifyClient(account_id=5)
print('client sp:', client.sp)
print('is_authenticated', client.is_authenticated())
