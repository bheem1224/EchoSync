
import spotipy
from spotipy.oauth2 import SpotifyOAuth
try:
    from spotipy.cache_handler import CacheHandler
except Exception:
    CacheHandler = object
from typing import Dict, List, Optional, Any, Union
import time
from dataclasses import dataclass
from core.tiered_logger import get_logger
from core.provider_base import ProviderBase
from core.provider import SyncServiceProvider, get_provider_capabilities, ProviderRegistry
from core.matching_engine.soul_sync_track import SoulSyncTrack
from sdk.http_client import HttpClient, RetryConfig, RateLimitConfig

logger = get_logger("spotify_client")

class ConfigCacheHandler(CacheHandler):
    """Spotipy CacheHandler that persists tokens into ConfigManager for the active Spotify account."""
    def __init__(self, account_id: Optional[int]):
        self.account_id = account_id
        logger.debug(f"Initialized ConfigCacheHandler for account {account_id}")

    def get_cached_token(self):
        """Load cached token from storage database.
        
        Returns a dict with access_token, refresh_token, expires_at, and scope if available,
        or None if no token is stored.
        """
        try:
            if not self.account_id:
                logger.debug("No account_id specified, cannot load token")
                return None
            
            from sdk.storage_service import get_storage_service
            storage = get_storage_service()
            token_data = storage.get_account_token(self.account_id)
            
            if not token_data:
                logger.debug(f"No token data found in storage for account {self.account_id}")
                return None
            
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            expires_at = token_data.get('expires_at')
            scope = token_data.get('scope', "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email playlist-modify-public playlist-modify-private")
            
            logger.debug(f"Loaded token data for account {self.account_id}: access={bool(access_token)}, refresh={bool(refresh_token)}, expires={expires_at}")
            
            # Return full token info - Spotipy will handle refresh if needed
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_at': expires_at or 0,
                'scope': scope,
                'token_type': 'Bearer'
            }
        except Exception as e:
            logger.error(f"Error loading cached Spotify token for account {self.account_id}: {e}")
            return None

    def save_token_to_cache(self, token_info):
        """Save token to storage database.
        
        This is called by Spotipy after getting a new token or refreshing.
        Ensures both access_token and refresh_token are persisted.
        """
        try:
            if not self.account_id:
                logger.warning("No account_id specified; cannot save Spotify tokens")
                return
            
            if not token_info:
                logger.warning(f"No token_info provided to save for account {self.account_id}")
                return
            
            from sdk.storage_service import get_storage_service
            storage = get_storage_service()
            
            access_token = token_info.get('access_token')
            refresh_token = token_info.get('refresh_token')
            expires_at = token_info.get('expires_at')
            scope = token_info.get('scope', "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email playlist-modify-public playlist-modify-private")
            
            if not access_token:
                logger.warning(f"No access_token in token_info for account {self.account_id}")
                return
            
            # If no refresh token provided, try to preserve existing one
            if not refresh_token:
                existing_token = storage.get_account_token(self.account_id)
                if existing_token and existing_token.get('refresh_token'):
                    refresh_token = existing_token.get('refresh_token')
                    logger.debug(f"Preserving existing refresh_token for account {self.account_id}")
            
            logger.debug(f"Saving token for account {self.account_id}: access={bool(access_token)}, refresh={bool(refresh_token)}, expires={expires_at}")
            
            success = storage.save_account_token(
                account_id=self.account_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type='Bearer',
                expires_at=expires_at,
                scope=scope
            )
            
            if success:
                logger.info(f"Successfully persisted Spotify tokens for account {self.account_id}")
                try:
                    storage.mark_account_authenticated(self.account_id)
                except Exception as e:
                    logger.debug(f"Failed to mark account as authenticated: {e}")
            else:
                logger.error(f"Failed to save Spotify tokens for account {self.account_id}")
        except Exception as e:
            logger.error(f"Error saving Spotify token to cache for account {self.account_id}: {e}")

class SpotifyClient(SyncServiceProvider):
    name = "spotify"
    category = "provider"
    supports_downloads = False

    def __init__(self, account_id: Optional[int] = None):
        self.sp: Optional[spotipy.Spotify] = None
        self.user_id: Optional[str] = None

        # Auto-detect active account if not provided
        if account_id is None:
            from core.settings import config_manager
            account_id = config_manager.get('active_spotify_account_id')

        self.account_id: Optional[int] = account_id

        # Initialize centralized HTTP client for Spotify (5 requests/second rate limit)
        self._http = HttpClient(
            provider='spotify',
            retry=RetryConfig(max_retries=3, base_backoff=0.5, max_backoff=8.0),
            rate=RateLimitConfig(requests_per_second=5.0)
        )

        self._setup_client()
        ProviderRegistry.register(SpotifyClient)

    def _setup_client(self):
        try:
            creds = {'client_id': None, 'client_secret': None, 'redirect_uri': None}
            from sdk.storage_service import get_storage_service
            storage = get_storage_service()
            creds['client_id'] = storage.get_service_config('spotify', 'client_id')
            creds['client_secret'] = storage.get_service_config('spotify', 'client_secret')
            creds['redirect_uri'] = storage.get_service_config('spotify', 'redirect_uri')

            if not creds['client_id'] or not creds['client_secret']:
                logger.warning("Spotify credentials not configured in config.db")
                return

            # Updated scope to include write permissions
            scope = "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email playlist-modify-public playlist-modify-private"

            # Create auth manager WITHOUT requesting authorization on init
            auth_manager = SpotifyOAuth(
                client_id=creds['client_id'],
                client_secret=creds['client_secret'],
                redirect_uri=creds['redirect_uri'],
                scope=scope,
                cache_handler=ConfigCacheHandler(self.account_id),
                show_dialog=False
            )

            try:
                # Check if we have a valid cached token
                cached = auth_manager.get_cached_token()
                if cached and cached.get('access_token'):
                    # We have a valid access token
                    logger.info(f"Using valid cached access token for Spotify account {self.account_id}")
                elif cached and cached.get('refresh_token'):
                    # We have a refresh token but no valid access token - refresh it silently
                    logger.debug(f"Refresh token found for account {self.account_id}, attempting silent refresh")
                    try:
                        new_token = auth_manager.refresh_access_token(cached.get('refresh_token'))
                        if new_token and new_token.get('access_token'):
                            logger.info(f"Successfully refreshed Spotify token for account {self.account_id}")
                            # Cache handler will save it automatically via SpotifyOAuth
                        else:
                            logger.warning(f"Refresh token refresh returned no access token for account {self.account_id}")
                    except Exception as e:
                        logger.warning(f"Failed to refresh Spotify token for account {self.account_id}: {e}")
                else:
                    logger.debug(f"No cached tokens found for account {self.account_id}. User authentication required.")
            except Exception as e:
                logger.debug(f"Error checking/refreshing cached token: {e}")

            # Initialize Spotipy with the auth manager
            # Use the auth_manager's get_access_token which won't trigger browser if token exists
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            self.user_id = None
            logger.info("Spotify client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Spotify client: {e}")
            self.sp = None

    def authenticate(self, **kwargs) -> bool:
        return self.is_authenticated()

    def is_authenticated(self) -> bool:
        """Check if currently authenticated with Spotify.
        
        Returns True if valid token exists (not expired and can call API).
        Returns False if token is invalid, expired, or missing.
        Does NOT attempt to open browser or trigger auth flow.
        """
        if self.sp is None:
            logger.debug("Spotify client not initialized")
            return False
        try:
            self.sp.current_user()
            return True
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 401:
                logger.warning(f"Spotify authentication failed (401 Unauthorized) for account {self.account_id}. User needs to re-authenticate.")
            else:
                logger.error(f"Spotify API error: {e}")
            return False
        except Exception as e:
            logger.debug(f"Error checking Spotify authentication: {e}")
            return False

    def is_configured(self) -> bool:
        if self.sp is not None:
             return True
        # Check storage if we can potentially configure it
        from sdk.storage_service import get_storage_service
        storage = get_storage_service()
        return bool(storage.get_service_config('spotify', 'client_id') and
                    storage.get_service_config('spotify', 'client_secret'))

    def get_logo_url(self) -> str:
        return "/static/img/spotify_logo.png"

    def _ensure_user_id(self) -> bool:
        if self.user_id is None and self.sp is not None:
            try:
                user_info = self.sp.current_user()
                self.user_id = user_info['id']
                return True
            except Exception as e:
                logger.error(f"Failed to fetch user info: {e}")
                return False
        return self.user_id is not None

    def _convert_track(self, spotify_track_data: Dict[str, Any]) -> Optional[SoulSyncTrack]:
        """Convert Spotify track data to SoulSyncTrack."""
        if not spotify_track_data or not spotify_track_data.get('name'):
            return None

        try:
            # Extract basic fields
            raw_title = spotify_track_data.get('name')
            
            # Artist handling
            artists = spotify_track_data.get('artists', [])
            artist_name = artists[0].get('name') if artists else "Unknown Artist"
            
            # Album handling
            album = spotify_track_data.get('album', {})
            album_title = album.get('name')
            release_date = album.get('release_date', '')
            release_year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

            # IDs
            track_id = spotify_track_data.get('id')
            isrc = None
            external_ids = spotify_track_data.get('external_ids', {})
            if external_ids:
                isrc = external_ids.get('isrc')

            return self.create_soul_sync_track(
                title=raw_title,
                artist=artist_name,
                album=album_title,
                duration_ms=spotify_track_data.get('duration_ms'),
                track_number=spotify_track_data.get('track_number'),
                disc_number=spotify_track_data.get('disc_number'),
                year=release_year,
                isrc=isrc,
                provider_id=track_id,
                source='spotify',
                popularity=spotify_track_data.get('popularity'),
                preview_url=spotify_track_data.get('preview_url')
            )
        except Exception as e:
            logger.error(f"Error converting Spotify track: {e}")
            return None

    # ==========================================
    # ProviderBase Implementations
    # ==========================================

    def search(self, query: str, type: str = "track", limit: int = 10) -> List[SoulSyncTrack]:
        if not self.is_authenticated():
            return []
        
        try:
            results = self.sp.search(q=query, type=type, limit=limit)
            tracks = []
            
            if type == 'track' and 'tracks' in results:
                for item in results['tracks']['items']:
                    track = self._convert_track(item)
                    if track:
                        tracks.append(track)
            
            return tracks
        except Exception as e:
            logger.error(f"Error searching Spotify: {e}")
            return []

    def get_track(self, track_id: str) -> Optional[SoulSyncTrack]:
        if not self.is_authenticated():
            return None
        
        try:
            track_data = self.sp.track(track_id)
            return self._convert_track(track_data)
        except Exception as e:
            logger.error(f"Error getting track {track_id}: {e}")
            return None
            
    # Alias for Provider protocol compatibility if needed,
    # though ProviderBase uses get_track
    def get_track_by_id(self, item_id: str) -> Optional[SoulSyncTrack]:
        return self.get_track(item_id)

    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        if not self.is_authenticated():
            return None
        try:
            return self.sp.album(album_id)
        except Exception as e:
            logger.error(f"Error getting album {album_id}: {e}")
            return None

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        if not self.is_authenticated():
            return None
        try:
            return self.sp.artist(artist_id)
        except Exception as e:
            logger.error(f"Error getting artist {artist_id}: {e}")
            return None
            
    def get_artist_details(self, artist_id: str) -> Dict[str, Any]:
        """Protocol requirement alias."""
        res = self.get_artist(artist_id)
        return res if res else {}

    # ==========================================
    # SyncServiceProvider Implementations
    # ==========================================

    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_authenticated():
            return []
        
        if not self._ensure_user_id():
            return []
            
        playlists = []
        try:
            results = self.sp.current_user_playlists(limit=50)
            while results:
                for item in results['items']:
                    # Filter for owned or collaborative playlists if needed,
                    # but usually we want to see everything available to the user.
                    playlists.append({
                        'id': item['id'],
                        'name': item['name'],
                        'description': item.get('description'),
                        'track_count': item['tracks']['total'],
                        'owner': item['owner']['display_name'],
                        'public': item.get('public'),
                        'collaborative': item.get('collaborative')
                    })
                results = self.sp.next(results) if results['next'] else None
            return playlists
        except Exception as e:
            logger.error(f"Error getting user playlists: {e}")
            return []

    def get_playlist_tracks(self, playlist_id: str) -> List[SoulSyncTrack]:
        if not self.is_authenticated():
            return []

        tracks = []
        try:
            results = self.sp.playlist_tracks(playlist_id, limit=100)
            while results:
                for item in results['items']:
                    if item.get('track') and item['track'].get('id'):
                        track = self._convert_track(item['track'])
                        if track:
                            tracks.append(track)
                results = self.sp.next(results) if results['next'] else None
            return tracks
        except Exception as e:
            logger.error(f"Error getting playlist tracks: {e}")
            return []

    def sync_playlist(self, playlist_id: str, target_provider: str) -> bool:
        """
        Sync a Spotify playlist TO another provider.
        (Implementation depends on how we access the target provider instance)
        """
        logger.info(f"Sync requested for Spotify playlist {playlist_id} to {target_provider}")
        # In a real implementation, we would:
        # 1. Fetch tracks from Spotify playlist
        # 2. Get target provider instance from Registry
        # 3. Search/Match tracks on target
        # 4. Create playlist on target
        # 5. Add tracks to target

        # For now, we stub this as False or basic logging, as the core sync engine
        # usually handles the orchestration. If the provider itself must do it:

        try:
            from core.provider import ProviderRegistry
            target = ProviderRegistry.create_instance(target_provider)
            if not target:
                logger.error(f"Target provider {target_provider} not found")
                return False

            # Logic would go here. For now, returning False to indicate not fully implemented
            # or relying on external sync engine.
            return False
        except Exception as e:
            logger.error(f"Error syncing playlist: {e}")
            return False

    # ==========================================
    # Write Capabilities (Spotify as Target)
    # ==========================================

    def create_playlist(self, name: str, description: str = "", public: bool = False) -> Optional[str]:
        """Create a new playlist on Spotify and return its ID."""
        if not self.is_authenticated() or not self._ensure_user_id():
            return None

        try:
            playlist = self.sp.user_playlist_create(
                user=self.user_id,
                name=name,
                public=public,
                description=description
            )
            return playlist['id']
        except Exception as e:
            logger.error(f"Error creating playlist '{name}': {e}")
            return None

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]) -> bool:
        """Add tracks to a Spotify playlist."""
        if not self.is_authenticated():
            return False

        try:
            # Spotify allows max 100 tracks per request
            for i in range(0, len(track_uris), 100):
                batch = track_uris[i:i+100]
                self.sp.playlist_add_items(playlist_id, batch)
            return True
        except Exception as e:
            logger.error(f"Error adding tracks to playlist {playlist_id}: {e}")
            return False

    def search_and_get_uri(self, track: SoulSyncTrack) -> Optional[str]:
        """
        Helper to find a Spotify URI for a SoulSyncTrack.
        Useful when Spotify is the target.
        """
        query = f"track:{track.title} artist:{track.artist_name}"
        results = self.search(query, limit=1)
        if results:
            # We need the URI, but search returns SoulSyncTrack.
            # We stored the ID in identifiers.
            found = results[0]
            # Retrieve ID from identifiers
            # identifiers structure: [{'provider_source': 'spotify', 'provider_item_id': '...'}]
            # or dict if normalized. SoulSyncTrack normalizes to dict in post_init?
            # Let's check SoulSyncTrack definition. It has 'identifiers' dict by default.

            # The factory `create_soul_sync_track` adds it as a list item first,
            # then `SoulSyncTrack.__post_init__` converts list to dict if needed.

            # Safe retrieval
            if isinstance(found.identifiers, dict):
                tid = found.identifiers.get('spotify')
            elif isinstance(found.identifiers, list):
                 # fallback search in list
                 tid = next((x['provider_item_id'] for x in found.identifiers if x['provider_source'] == 'spotify'), None)
            else:
                tid = None

            if tid:
                return f"spotify:track:{tid}"
        return None
