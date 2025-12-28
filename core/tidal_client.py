
import secrets
import base64
import time
import threading
import urllib.parse
import hashlib
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any
from utils.logging_config import get_logger
from config.settings import config_manager
from .provider_types import SyncServiceProvider
from sdk.http_client import HttpClient, RetryConfig, RateLimitConfig
from core.provider_capabilities import get_provider_capabilities
from core.provider_capabilities import get_provider_capabilities

logger = get_logger("tidal_client")

class Track:
    def __init__(self, id, name, artists, album, duration):
        self.id = id
        self.name = name
        self.artists = artists
        self.album = album
        self.duration = duration

class Playlist:
    def __init__(self, id, name, tracks):
        self.id = id
        self.name = name
        self.tracks = tracks

class TidalClient(SyncServiceProvider):
    """Tidal API client for fetching user playlists and track data"""
    name = "tidal"

    def generate_pkce(self):
        """Generate PKCE code verifier and code challenge, set on instance, and return as tuple."""
        import secrets, hashlib, base64
        # Generate a high-entropy code verifier (43-128 chars)
        verifier = secrets.token_urlsafe(64)[:128]
        # Create the code challenge (SHA256, then base64-url-encoded, no padding)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        self.code_verifier = verifier
        self.code_challenge = challenge
        return verifier, challenge

    def get_logo_url(self) -> str:
        return "/static/img/tidal_logo.png"

    def __init__(self, account_id: Optional[str] = None):
        self.account_id = account_id
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = 0
        self.base_url = "https://openapi.tidal.com/v2"
        self.auth_url = "https://login.tidal.com/authorize"
        self.token_url = "https://auth.tidal.com/v1/oauth2/token"
        self.redirect_uri = "http://127.0.0.1:8008/tidal/callback"
        # Initialize centralized HTTP client for Tidal (2 requests/second rate limit)
        self._http = HttpClient(
            provider='tidal',
            retry=RetryConfig(max_retries=3, base_backoff=0.5, max_backoff=8.0),
            rate=RateLimitConfig(requests_per_second=2.0)
        )

        # Capability flags
        self.capabilities = get_provider_capabilities('tidal')
        self.auth_server = None
        self.auth_code = None
        self.code_verifier = None
        self.code_challenge = None
        self._load_config()
        self._load_saved_tokens()
        
        # Register as plugin with explicit declarations
        from core.plugin_system import PluginType, PluginScope, PluginDeclaration, register_plugin
        plugin_decl = PluginDeclaration(
            name='tidal_client',
            plugin_type=PluginType.PLAYLIST_SERVICE,
            provides=[
                'playlist.read',
                'search.tracks',
                'search.artists',
                'search.albums',
                'search.playlists',
                'track.title',
                'track.artist',
                'track.album',
                'track.duration_ms',
                'track.release_date',
                'album.artist',
                'album.type',
            ],
            consumes=['auth.oauth'],
            scope=[PluginScope.SYNC, PluginScope.SEARCH],
            version='1.0.0',
            description='TIDAL playlist and search provider',
            author='SoulSync',
            instance=self,
            priority=90,
        )
        register_plugin(plugin_decl)
    def _refresh_access_token(self):
        """Refresh the Tidal access token using the refresh token."""
        if not self.refresh_token or not self.client_id:
            logger.error("Cannot refresh Tidal token: missing refresh_token or client_id")
            return False
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id
        }
        try:
            response = self._http.post(self.token_url, data=data)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token', self.refresh_token)
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = time.time() + expires_in - 60
                # Persist refreshed tokens to config.db
                try:
                    if self.account_id and self.access_token:
                        from sdk.storage_service import get_storage_service
                        storage = get_storage_service()
                        storage.save_account_token(
                            account_id=int(self.account_id),
                            access_token=self.access_token,
                            refresh_token=self.refresh_token,
                            token_type='Bearer',
                            expires_at=int(self.token_expires_at),
                            scope=None,
                        )
                        storage.mark_account_authenticated(int(self.account_id))
                except Exception:
                    pass
                logger.info("Tidal access token refreshed successfully")
                return True
            else:
                logger.error(f"Failed to refresh Tidal token: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exception during Tidal token refresh: {e}")
            return False

    def authenticate(self, **kwargs) -> bool:
        # Stub implementation
        return False

    def search(self, query: str, type: str = "track", limit: int = 10) -> list:
        # Stub implementation
        return []

    def get_user_playlists(self, user_id: Optional[str] = None) -> list:
        # Stub implementation
        return []

    def get_playlist_tracks(self, playlist_id: str) -> list:
        # Stub implementation
        return []

    def sync_playlist(self, playlist_id: str, target_provider: str) -> bool:
        # Stub implementation
        return False

    def get_track(self, track_id: str) -> dict:
        # Stub implementation
        return {}

    def get_album(self, album_id: str) -> dict:
        # Stub implementation
        return {}

    def get_artist(self, artist_id: str) -> dict:
        # Stub implementation
        return {}

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)
    
    def _load_config(self):
        """Load Tidal configuration from database using centralized config_manager helper"""
        try:
            from sdk.storage_service import get_storage_service
            storage = get_storage_service()
            storage.ensure_service('tidal', display_name='Tidal', service_type='streaming', description='Tidal music streaming service')
            self.client_id = storage.get_service_config('tidal', 'client_id') or None
            self.client_secret = storage.get_service_config('tidal', 'client_secret') or None
            self.redirect_uri = storage.get_service_config('tidal', 'redirect_uri') or self.redirect_uri
            if not self.client_id or not self.client_secret:
                logger.warning("Tidal client ID or secret not configured in database")
                return False
            logger.info(f"Loaded Tidal config from config.db with client ID: {self.client_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to load Tidal configuration: {e}")
            return False
    
    def _load_saved_tokens(self):
        """Load saved tokens from encrypted database and refresh if needed"""
        try:
            if not self.account_id:
                logger.warning("No account_id specified for Tidal client")
                return
            from sdk.storage_service import get_storage_service
            storage = get_storage_service()
            token_data = storage.get_account_token(int(self.account_id))
            if token_data:
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_expires_at = token_data.get('expires_at', 0)
        except Exception as e:
            logger.error(f"Error loading Tidal tokens: {e}")
            return False
    
    def _start_callback_server(self):
        """Start HTTP server to receive OAuth callback"""
        # Skip starting server in Docker/production mode - web server handles callbacks
        import os
        if os.getenv('FLASK_ENV') == 'production' or os.path.exists('/.dockerenv'):
            logger.info("Docker/WebUI mode detected - skipping TidalClient callback server (web server handles callbacks)")
            return
            
        # Store reference to self for the callback handler
        tidal_client_ref = self
        
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_url = urllib.parse.urlparse(self.path)
                query_params = urllib.parse.parse_qs(parsed_url.query)

                # Debug: Log the full callback URL and parameters
                logger.info(f"Tidal callback received: {self.path}")
                logger.info(f"Query parameters: {query_params}")

                if 'code' in query_params:
                    tidal_client_ref.auth_code = query_params['code'][0]
                    logger.info(f"Received Tidal authorization code: {tidal_client_ref.auth_code[:10]}...")

                    # Send success response
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'<h1>Success!</h1><p>You can close this window and return to SoulSync.</p>')
                elif 'error' in query_params:
                    # Handle OAuth errors
                    error = query_params.get('error', ['unknown'])[0]
                    error_description = query_params.get('error_description', ['No description'])[0]
                    logger.error(f"Tidal OAuth error: {error} - {error_description}")

                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(f'<h1>OAuth Error</h1><p>Error: {error}</p><p>Description: {error_description}</p>'.encode())
                else:
                    logger.error("No authorization code or error in Tidal callback")
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'<h1>Error</h1><p>Authorization failed - no code received.</p>')

            def log_message(self, format, *args):
                pass  # Suppress server logs
        
        try:
            port = 8889
            self.auth_server = HTTPServer(('localhost', port), CallbackHandler)
            server_thread = threading.Thread(target=self.auth_server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            logger.info(f"Started Tidal callback server on port {port}")
        except Exception as e:
            logger.error(f"Failed to start Tidal callback server: {e}")
    
    def _exchange_code_for_tokens(self):
        """Exchange authorization code for access tokens using PKCE"""
        try:
            # PKCE flow: client_id + code_verifier (NO client_secret)
            data = {
                'grant_type': 'authorization_code',
                'code': self.auth_code,
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'code_verifier': self.code_verifier
            }
            
            client_id_safe = self.client_id or ""
            logger.info(f"Token exchange: client_id={client_id_safe[:8]}... redirect={self.redirect_uri} verifier_len={len(self.code_verifier) if self.code_verifier else 0}")
            
            time.sleep(0.1)
            response = self._http.post(
                self.token_url,
                data=data
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = time.time() + expires_in - 60
                
                logger.info("Successfully exchanged Tidal code for tokens")
                return True
            else:
                logger.error(f"Failed to exchange Tidal code: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error exchanging Tidal code for tokens: {e}")
            return False
    
    # Duplicate _load_saved_tokens removed
    
    def fetch_token_from_code(self, auth_code: str) -> bool:
        """Exchange authorization code for access tokens (for web server callback)"""
        try:
            if not self.code_verifier:
                logger.error("Cannot exchange token: code_verifier is missing!")
                return False
                
            logger.info(f"Starting token exchange with code: {auth_code[:20]}...")
            logger.info(f"PKCE verifier present: verifier_len={len(self.code_verifier)}")
            logger.info(f"Redirect URI: {self.redirect_uri}")
            
            self.auth_code = auth_code
            result = self._exchange_code_for_tokens()
            
            if result:
                logger.info("✅ Token exchange successful")
            else:
                logger.error("❌ Token exchange failed")
            
            return result
        except Exception as e:
            logger.error(f"Error in fetch_token_from_code: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def _ensure_valid_token(self):
        """Ensure we have a valid access token, refresh if needed"""
        if not self.access_token:
            logger.warning("No Tidal access token - re-authentication required")
            return False
        
        # Check if token is expired
        if time.time() >= self.token_expires_at:
            logger.info("Tidal access token expired - attempting to refresh...")
            # return self._refresh_access_token()  # Undefined in new framework
        
        return True
    
    def is_authenticated(self):
        """Check if client is authenticated"""
        # Don't trigger authentication automatically here, just check token status
        return (self.access_token is not None and 
                time.time() < self.token_expires_at)
    
    def _get_user_id(self):
        """Get current user's ID from /users/me endpoint"""
        try:
            endpoints_to_try = [
                (f"{self.base_url}/users/me", "v2")
            ]
            
            for endpoint, version in endpoints_to_try:
                try:
                    logger.info(f"Trying to get user ID from {version}: {endpoint}")

                    headers = {
                        'Authorization': f'Bearer {self.access_token}',
                        'accept': 'application/vnd.api+json',
                        'User-Agent': 'SoulSync/1.0'
                    }
                    params = {}
                    
                    response = self._http.get(endpoint, headers=headers, params=params)
                    logger.info(f"User ID response: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"User data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        
                        # --- START OF CORRECTION ---
                        # Correctly parse the nested JSON structure from your example
                        user_id = None
                        if 'data' in data and isinstance(data['data'], dict):
                            user_id = data['data'].get('id')
                        
                        # Fallback to the original checks for other API responses
                        if not user_id:
                             user_id = data.get('id') or data.get('userId') or data.get('uid') or data.get('user_id')
                        # --- END OF CORRECTION ---

                        if user_id:
                            logger.info(f"Found user ID: {user_id}")
                            return str(user_id), version
                        else:
                            logger.warning(f"No user ID found in response: {data}")
                    else:
                        logger.warning(f"Failed to get user ID: {response.status_code} - {response.text[:200]}")
                        
                except Exception as e:
                    logger.warning(f"Error getting user ID from {version}: {e}")
                    continue
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error in _get_user_id: {e}")
            return None, None

    def get_user_playlists_metadata_only(self):
        """Get user's playlists using the V2 filtered endpoint."""
        # ...existing code...
            
        
    
    def search_tracks(self, query: str, limit: int = 10) -> List[Any]:
        """Search for tracks using Tidal's search API"""
        if not self._ensure_valid_token():
            return []
        url = f"{self.base_url}/searchresults"
        params = {'query': query, 'type': 'tracks', 'limit': limit, 'countryCode': 'US'}
        headers = {'Authorization': f'Bearer {self.access_token}', 'User-Agent': 'SoulSync/1.0'}
        response = self._http.get(url, params=params, headers=headers)
        if response.status_code != 200:
            return []
        data = response.json()
        tracks = []
        for item in data.get('tracks', {}).get('items', []):
            track = Track(
                id=item.get('id'),
                name=item.get('title'),
                artists=[a['name'] for a in item.get('artists', [])],
                album=item.get('album', {}).get('title'),
                duration=item.get('duration')
            )
            tracks.append(track)
        return tracks
    
    def get_playlist(self, playlist_id: str):
        """Get playlist details including tracks using V2 API with pagination"""
        if not self._ensure_valid_token():
            return None
        # Simulate two requests: one for playlist meta, one for tracks
        url_meta = f"{self.base_url}/playlists/{playlist_id}"
        url_tracks = f"{self.base_url}/playlists/{playlist_id}/items"
        
        headers = {'Authorization': f'Bearer {self.access_token}'}
        meta_resp = self._http.get(url_meta, headers=headers)
        if meta_resp.status_code != 200:
            return None
        meta = meta_resp.json().get('data', {})
        tracks_resp = self._http.get(url_tracks, headers=headers)
        if tracks_resp.status_code != 200:
            return None
        tracks_data = tracks_resp.json()
        # Parse tracks from included
        included = tracks_data.get('included', [])
        id_to_artist = {a['id']: a['attributes']['name'] for a in included if a['type'] == 'artists'}
        id_to_album = {a['id']: a['attributes']['title'] for a in included if a['type'] == 'albums'}
        track_objs = []
        for item in tracks_data.get('data', []):
            if item['type'] == 'playlistItems':
                track_id = item['relationships']['track']['data']['id']
                track_info = next((t for t in included if t['type'] == 'tracks' and t['id'] == track_id), None)
                if track_info:
                    artists = [id_to_artist[a['id']] for a in track_info['relationships']['artists']['data'] if a['id'] in id_to_artist]
                    album = id_to_album.get(track_info['relationships']['album']['data']['id'], None)
                    track_objs.append(Track(
                        id=track_id,
                        name=track_info['attributes']['title'],
                        artists=artists,
                        album=album,
                        duration=track_info['attributes'].get('duration')
                    ))
        return Playlist(meta.get('id'), meta.get('attributes', {}).get('name'), track_objs)