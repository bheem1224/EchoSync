
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
try:
    from spotipy.cache_handler import CacheHandler
except Exception:
    CacheHandler = object  # Fallback if import path differs
from typing import Dict, List, Optional, Any
import time
from dataclasses import dataclass
from core.tiered_logger import get_logger
from core.settings import config_manager
from core.provider_base import ProviderBase
from core.matching_engine.soul_sync_track import SoulSyncTrack
from sdk.http_client import HttpClient, RetryConfig, RateLimitConfig
from core.provider import get_provider_capabilities, ProviderRegistry

logger = get_logger("spotify_client")


def convert_spotify_track_to_soulsync(spotify_track_data: Dict[str, Any]) -> Optional[SoulSyncTrack]:
    """
    Convert Spotify track data to SoulSyncTrack using direct instantiation.
    """
    try:
        from datetime import datetime, timezone

        # Extract basic fields
        raw_title = spotify_track_data.get('name')

        # Artist handling
        artists = spotify_track_data.get('artists', [])
        artist_name = ', '.join([a.get('name', '') for a in artists]) if artists else "Unknown Artist"

        # Album handling
        album = spotify_track_data.get('album', {})
        album_title = album.get('name')
        release_date = album.get('release_date', '')
        release_year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

        # Identifiers
        identifiers = []
        track_id = spotify_track_data.get('id')
        if track_id:
            identifiers.append({
                'provider_source': 'spotify',
                'provider_item_id': str(track_id),
                'raw_data': None # Avoid storing heavy object
            })

        # ISRC
        isrc = None
        external_ids = spotify_track_data.get('external_ids', {})
        if external_ids and 'isrc' in external_ids:
            isrc = external_ids['isrc']

        if not raw_title:
            return None

        return SoulSyncTrack(
            raw_title=raw_title,
            artist_name=artist_name,
            album_title=album_title,
            duration=spotify_track_data.get('duration_ms'),
            track_number=spotify_track_data.get('track_number'),
            disc_number=spotify_track_data.get('disc_number'),
            release_year=release_year,
            isrc=isrc,
            added_at=datetime.now(timezone.utc),
            identifiers=identifiers
        )
    except Exception as e:
        logger.error(f"Error converting Spotify track to SoulSyncTrack: {e}", exc_info=True)
        return None


@dataclass
class Track:
    id: str
    name: str
    artists: List[str]
    album: str
    duration_ms: int
    popularity: int
    isrc: Optional[str] = None  # International Standard Recording Code
    preview_url: Optional[str] = None
    external_urls: Optional[Dict[str, str]] = None
    
    @classmethod
    def from_spotify_track(cls, track_data: Dict[str, Any]) -> 'Track':
        # Extract ISRC from external_ids if available
        isrc = None
        if 'external_ids' in track_data and 'isrc' in track_data['external_ids']:
            isrc = track_data['external_ids']['isrc']
        
        return cls(
            id=track_data['id'],
            name=track_data['name'],
            artists=[artist['name'] for artist in track_data['artists']],
            album=track_data['album']['name'],
            duration_ms=track_data['duration_ms'],
            popularity=track_data['popularity'],
            isrc=isrc,
            preview_url=track_data.get('preview_url'),
            external_urls=track_data.get('external_urls')
        )

@dataclass
class Artist:
    id: str
    name: str
    popularity: int
    genres: List[str]
    followers: int
    image_url: Optional[str] = None
    external_urls: Optional[Dict[str, str]] = None
    
    @classmethod
    def from_spotify_artist(cls, artist_data: Dict[str, Any]) -> 'Artist':
        # Get the largest image URL if available
        image_url = None
        if artist_data.get('images') and len(artist_data['images']) > 0:
            image_url = artist_data['images'][0]['url']
        
        return cls(
            id=artist_data['id'],
            name=artist_data['name'],
            popularity=artist_data.get('popularity', 0),
            genres=artist_data.get('genres', []),
            followers=artist_data.get('followers', {}).get('total', 0),
            image_url=image_url,
            external_urls=artist_data.get('external_urls')
        )

@dataclass
class Album:
    id: str
    name: str
    artists: List[str]
    release_date: str
    total_tracks: int
    album_type: str
    image_url: Optional[str] = None
    external_urls: Optional[Dict[str, str]] = None
    
    @classmethod
    def from_spotify_album(cls, album_data: Dict[str, Any]) -> 'Album':
        # Get the largest image URL if available
        image_url = None
        if album_data.get('images') and len(album_data['images']) > 0:
            image_url = album_data['images'][0]['url']
        
        return cls(
            id=album_data['id'],
            name=album_data['name'],
            artists=[artist['name'] for artist in album_data['artists']],
            release_date=album_data.get('release_date', ''),
            total_tracks=album_data.get('total_tracks', 0),
            album_type=album_data.get('album_type', 'album'),
            image_url=image_url,
            external_urls=album_data.get('external_urls')
        )

@dataclass
class Playlist:
    id: str
    name: str
    description: Optional[str]
    owner: str
    public: bool
    collaborative: bool
    tracks: List[Track]
    total_tracks: int
    
    @classmethod
    def from_spotify_playlist(cls, playlist_data: Dict[str, Any], tracks: List[Track]) -> 'Playlist':
        return cls(
            id=playlist_data['id'],
            name=playlist_data['name'],
            description=playlist_data.get('description'),
            owner=playlist_data['owner']['display_name'],
            public=playlist_data['public'],
            collaborative=playlist_data['collaborative'],
            tracks=tracks,
            total_tracks=playlist_data['tracks']['total']
        )

class ConfigCacheHandler(CacheHandler):
    """Spotipy CacheHandler that persists tokens into ConfigManager for the active Spotify account."""
    def __init__(self, account_id: Optional[int]):
        self.account_id = account_id

    def get_cached_token(self):
        try:
            if not self.account_id:
                return None
            
            # Read token fields from config.db via StorageService
            from sdk.storage_service import get_storage_service
            storage = get_storage_service()
            token_data = storage.get_account_token(self.account_id)
            
            if not token_data:
                return None
            
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            expires_at = token_data.get('expires_at')
            scope = token_data.get('scope', "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email")
            
            # If we have an access token and expiry, return it
            if access_token and expires_at:
                return {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'expires_at': expires_at,
                    'scope': scope,
                    'token_type': 'Bearer'
                }
            # If we have only a refresh token, return minimal info to allow refresh
            if refresh_token:
                return {
                    'access_token': None,
                    'refresh_token': refresh_token,
                    'expires_at': 0,
                    'scope': scope,
                    'token_type': 'Bearer'
                }
            return None
        except Exception as e:
            logger.error(f"Error loading cached Spotify token: {e}")
            return None

    def save_token_to_cache(self, token_info):
        try:
            if not self.account_id:
                logger.warning("No account_id specified; cannot save Spotify tokens")
                return
            
            # Save token fields to config.db via StorageService
            from sdk.storage_service import get_storage_service
            storage = get_storage_service()
            
            access_token = token_info.get('access_token')
            refresh_token = token_info.get('refresh_token')
            expires_at = token_info.get('expires_at')
            scope = token_info.get('scope', "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email")
            
            if not access_token:
                logger.warning(f"No access token to save for Spotify account {self.account_id}")
                return
            
            # If refresh_token is not in token_info, try to preserve existing one
            if not refresh_token:
                existing_token = storage.get_account_token(self.account_id)
                if existing_token:
                    refresh_token = existing_token.get('refresh_token')
            
            success = storage.save_account_token(
                account_id=self.account_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type='Bearer',
                expires_at=expires_at,
                scope=scope
            )
            
            if success:
                logger.info(f"Saved Spotify tokens for account {self.account_id} to encrypted database")
                # Mark account as authenticated
                storage.mark_account_authenticated(self.account_id)
            else:
                logger.error(f"Failed to save Spotify tokens for account {self.account_id}")
        except Exception as e:
            logger.error(f"Error saving Spotify token to cache: {e}")

class SpotifyClient(ProviderBase):
    name = "spotify"

    def authenticate(self, **kwargs) -> bool:
        """Attempt to verify Spotify authentication status."""
        return self.is_authenticated()

    def search(self, query: str, limit: int = 10) -> list:
        # Stub implementation
        return []

    def get_user_playlists(self, user_id: Optional[str] = None) -> list:
        # Stub implementation
        return []

    def get_playlist_tracks(self, playlist_id: str) -> List[SoulSyncTrack]:
        """Get tracks from a Spotify playlist and return as SoulSyncTrack objects"""
        if not self.is_authenticated():
            return []
        
        try:
            # Get raw Spotify track data from API
            results = self.sp.playlist_tracks(playlist_id, limit=100)
            
            soul_sync_tracks = []
            
            while results:
                for item in results['items']:
                    if item['track'] and item['track']['id']:
                        # Convert Spotify track to SoulSyncTrack
                        soul_track = convert_spotify_track_to_soulsync(item['track'])
                        if soul_track:
                            soul_sync_tracks.append(soul_track)
                
                results = self.sp.next(results) if results['next'] else None
            
            return soul_sync_tracks
            
        except Exception as e:
            logger.error(f"Error getting playlist tracks: {e}", exc_info=True)
            return []

    def sync_playlist(self, playlist_id: str, target_provider: str) -> bool:
        # Stub implementation
        return False

    def get_track(self, track_id: str) -> dict:
        # Stub implementation
        return None

    def get_album(self, album_id: str) -> dict:
        # Stub implementation
        return None

    def get_artist(self, artist_id: str) -> dict:
        # Stub implementation
        return None

    def is_configured(self) -> bool:
        if self.sp is not None:
             return True
        return bool(getattr(self, 'client_id', None) and getattr(self, 'client_secret', None) and getattr(self, 'redirect_uri', None))

    def get_logo_url(self) -> str:
        return "/static/img/spotify_logo.png"
    
    def __init__(self, account_id: Optional[int] = None):
        self.sp: Optional[spotipy.Spotify] = None
        self.user_id: Optional[str] = None
        from core.provider import ProviderRegistry
        self.account_id: Optional[int] = account_id
        # Initialize centralized HTTP client for Spotify (5 requests/second rate limit)
        self._http = HttpClient(
            provider='spotify',
            retry=RetryConfig(max_retries=3, base_backoff=0.5, max_backoff=8.0),
            rate=RateLimitConfig(requests_per_second=5.0)
        )

        # Capability flags
        self.capabilities = get_provider_capabilities('spotify')
        self._setup_client()
        ProviderRegistry.register(SpotifyClient)
    
    def _setup_client(self):
        try:
            # Load credentials strictly from config.db via StorageService
            creds = {'client_id': None, 'client_secret': None, 'redirect_uri': None}
            from sdk.storage_service import get_storage_service
            storage = get_storage_service()
            creds['client_id'] = storage.get_service_config('spotify', 'client_id')
            creds['client_secret'] = storage.get_service_config('spotify', 'client_secret')
            creds['redirect_uri'] = storage.get_service_config('spotify', 'redirect_uri')
            if not creds['client_id'] or not creds['client_secret']:
                logger.warning("Spotify credentials not configured in config.db")
                return
            auth_manager = SpotifyOAuth(
                client_id=creds['client_id'],
                client_secret=creds['client_secret'],
                redirect_uri=creds['redirect_uri'],
                scope="user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email",
                cache_handler=ConfigCacheHandler(self.account_id)
            )
            try:
                cached = auth_manager.get_cached_token()
                if cached:
                    logger.debug(f"Loaded cached Spotify token for account {self.account_id}: has_access={bool(cached.get('access_token'))} has_refresh={bool(cached.get('refresh_token'))} expires_at={cached.get('expires_at')}")
                else:
                    logger.debug(f"No cached Spotify token found for account {self.account_id}")
            except Exception as _e:
                pass
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            self.user_id = None
            logger.info("Spotify client initialized (multi-account ready; user info will be fetched when needed)")
        except Exception as e:
            logger.error(f"Failed to authenticate with Spotify: {e}")
            self.sp = None
    
    def is_authenticated(self) -> bool:
        """Check if Spotify client is authenticated and working"""
        if self.sp is None:
            return False
        
        try:
            # Make a simple API call to verify authentication
            self.sp.current_user()
            return True
        except Exception as e:
            logger.debug(f"Spotify authentication check failed: {e}")
            return False
    
    def _ensure_user_id(self) -> bool:
        """Ensure user_id is loaded (may make API call)"""
        if self.user_id is None and self.sp is not None:
            try:
                user_info = self.sp.current_user()
                self.user_id = user_info['id']
                logger.info(f"Successfully authenticated with Spotify as {user_info['display_name']}")
                return True
            except Exception as e:
                logger.error(f"Failed to fetch user info: {e}")
                return False
        return self.user_id is not None
    
    def get_user_playlists(self) -> List[Playlist]:
        if not self.is_authenticated():
            logger.error("Not authenticated with Spotify")
            return []
        
        if not self._ensure_user_id():
            logger.error("Failed to get user ID")
            return []
        
        playlists = []
        
        try:
            results = self.sp.current_user_playlists(limit=50)
            
            while results:
                for playlist_data in results['items']:
                    if playlist_data['owner']['id'] == self.user_id or playlist_data['collaborative']:
                        logger.info(f"Fetching tracks for playlist: {playlist_data['name']}")
                        tracks = self._get_playlist_tracks(playlist_data['id'])
                        playlist = Playlist.from_spotify_playlist(playlist_data, tracks)
                        playlists.append(playlist)
                
                results = self.sp.next(results) if results['next'] else None
            
            logger.info(f"Retrieved {len(playlists)} playlists")
            return playlists
            
        except Exception as e:
            logger.error(f"Error fetching user playlists: {e}")
            return []
    
    def get_user_playlists_metadata_only(self) -> List[Playlist]:
        """Get playlists without fetching all track details for faster loading"""
        if not self.is_authenticated():
            logger.error("Not authenticated with Spotify")
            return []
        
        if not self._ensure_user_id():
            logger.error("Failed to get user ID")
            return []
        
        playlists = []
        
        try:
            # Fetch all playlists using pagination
            limit = 50  # Maximum allowed by Spotify API
            offset = 0
            total_fetched = 0
            
            while True:
                results = self.sp.current_user_playlists(limit=limit, offset=offset)
                
                if not results or 'items' not in results:
                    break
                
                batch_count = 0
                for playlist_data in results['items']:
                    if playlist_data['owner']['id'] == self.user_id or playlist_data['collaborative']:
                        # Create playlist with empty tracks list for now
                        playlist = Playlist.from_spotify_playlist(playlist_data, [])
                        playlists.append(playlist)
                        batch_count += 1
                
                total_fetched += batch_count
                logger.info(f"Retrieved {batch_count} playlists in batch (offset {offset}), total: {total_fetched}")
                
                # Check if we've fetched all playlists
                if len(results['items']) < limit or not results.get('next'):
                    break
                    
                offset += limit
            
            logger.info(f"Retrieved {len(playlists)} total playlist metadata")
            return playlists

        except Exception as e:
            logger.error(f"Error fetching user playlists metadata: {e}")
            return []

    def get_saved_tracks_count(self) -> int:
        """Get the total count of user's saved/liked songs without fetching all tracks"""
        if not self.is_authenticated():
            logger.error("Not authenticated with Spotify")
            return 0

        try:
            # Just fetch first page to get the total count
            results = self.sp.current_user_saved_tracks(limit=1)
            if results and 'total' in results:
                total_count = results['total']
                logger.info(f"User has {total_count} saved tracks")
                return total_count
            return 0
        except Exception as e:
            logger.error(f"Error fetching saved tracks count: {e}")
            return 0

    def get_saved_tracks(self) -> List[Track]:
        """Fetch all user's saved/liked songs from Spotify"""
        if not self.is_authenticated():
            logger.error("Not authenticated with Spotify")
            return []

        tracks = []

        try:
            limit = 50  # Maximum allowed by Spotify API
            offset = 0
            total_fetched = 0

            while True:
                results = self.sp.current_user_saved_tracks(limit=limit, offset=offset)

                if not results or 'items' not in results:
                    break

                batch_count = 0
                for item in results['items']:
                    if item['track'] and item['track']['id']:
                        track = Track.from_spotify_track(item['track'])
                        tracks.append(track)
                        batch_count += 1

                total_fetched += batch_count
                logger.info(f"Retrieved {batch_count} saved tracks in batch (offset {offset}), total: {total_fetched}")

                # Check if we've fetched all saved tracks
                if len(results['items']) < limit or not results.get('next'):
                    break

                offset += limit

            logger.info(f"Retrieved {len(tracks)} total saved tracks")
            return tracks

        except Exception as e:
            logger.error(f"Error fetching saved tracks: {e}")
            return []

    def _get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        if not self.is_authenticated():
            return []
        
        tracks = []
        
        try:
            results = self.sp.playlist_tracks(playlist_id, limit=100)
            
            while results:
                for item in results['items']:
                    if item['track'] and item['track']['id']:
                        track = Track.from_spotify_track(item['track'])
                        tracks.append(track)
                
                results = self.sp.next(results) if results['next'] else None
            
            return tracks
            
        except Exception as e:
            logger.error(f"Error fetching playlist tracks: {e}")
            return []
    
    def get_playlist_by_id(self, playlist_id: str) -> Optional[Playlist]:
        if not self.is_authenticated():
            return None
        
        try:
            playlist_data = self.sp.playlist(playlist_id)
            tracks = self._get_playlist_tracks(playlist_id)
            return Playlist.from_spotify_playlist(playlist_data, tracks)
            
        except Exception as e:
            logger.error(f"Error fetching playlist {playlist_id}: {e}")
            return None
    
    def search_tracks(self, query: str, limit: int = 20) -> List[Track]:
        if not self.is_authenticated():
            return []
        
        try:
            results = self.sp.search(q=query, type='track', limit=limit)
            tracks = []
            
            for track_data in results['tracks']['items']:
                track = Track.from_spotify_track(track_data)
                tracks.append(track)
            
            return tracks
            
        except Exception as e:
            logger.error(f"Error searching tracks: {e}")
            return []
    
    def search_artists(self, query: str, limit: int = 20) -> List[Artist]:
        """Search for artists using Spotify API"""
        if not self.is_authenticated():
            return []
        
        try:
            results = self.sp.search(q=query, type='artist', limit=limit)
            artists = []
            
            for artist_data in results['artists']['items']:
                artist = Artist.from_spotify_artist(artist_data)
                artists.append(artist)
            
            return artists
            
        except Exception as e:
            logger.error(f"Error searching artists: {e}")
            return []
    
    def search_albums(self, query: str, limit: int = 20) -> List[Album]:
        """Search for albums using Spotify API"""
        if not self.is_authenticated():
            return []
        
        try:
            results = self.sp.search(q=query, type='album', limit=limit)
            albums = []
            
            for album_data in results['albums']['items']:
                album = Album.from_spotify_album(album_data)
                albums.append(album)
            
            return albums
            
        except Exception as e:
            logger.error(f"Error searching albums: {e}")
            return []
    
    def get_track_details(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed track information including album data and track number"""
        if not self.is_authenticated():
            return None
        
        try:
            track_data = self.sp.track(track_id)
            
            # Enhance with additional useful metadata for our purposes
            if track_data:
                enhanced_data = {
                    'id': track_data['id'],
                    'name': track_data['name'],
                    'track_number': track_data['track_number'],
                    'disc_number': track_data['disc_number'],
                    'duration_ms': track_data['duration_ms'],
                    'explicit': track_data['explicit'],
                    'artists': [artist['name'] for artist in track_data['artists']],
                    'primary_artist': track_data['artists'][0]['name'] if track_data['artists'] else None,
                    'album': {
                        'id': track_data['album']['id'],
                        'name': track_data['album']['name'],
                        'total_tracks': track_data['album']['total_tracks'],
                        'release_date': track_data['album']['release_date'],
                        'album_type': track_data['album']['album_type'],
                        'artists': [artist['name'] for artist in track_data['album']['artists']]
                    },
                    'is_album_track': track_data['album']['total_tracks'] > 1,
                    'raw_data': track_data  # Keep original for fallback
                }
                return enhanced_data
            return track_data
            
        except Exception as e:
            logger.error(f"Error fetching track details: {e}")
            return None
    
    def get_track_features(self, track_id: str) -> Optional[Dict[str, Any]]:
        if not self.is_authenticated():
            return None
        
        try:
            features = self.sp.audio_features(track_id)
            return features[0] if features else None
            
        except Exception as e:
            logger.error(f"Error fetching track features: {e}")
            return None
    
    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        """Get album information including tracks"""
        if not self.is_authenticated():
            return None
        
        try:
            album_data = self.sp.album(album_id)
            return album_data
            
        except Exception as e:
            logger.error(f"Error fetching album: {e}")
            return None
    
    def get_album_tracks(self, album_id: str) -> Optional[Dict[str, Any]]:
        """Get album tracks with pagination to fetch all tracks"""
        if not self.is_authenticated():
            return None

        try:
            # Get first page of tracks
            first_page = self.sp.album_tracks(album_id)
            if not first_page or 'items' not in first_page:
                return None

            # Collect all tracks starting with first page
            all_tracks = first_page['items'][:]

            # Fetch remaining pages if they exist
            next_page = first_page
            while next_page.get('next'):
                next_page = self.sp.next(next_page)
                if next_page and 'items' in next_page:
                    all_tracks.extend(next_page['items'])

            # Log success
            logger.info(f"Retrieved {len(all_tracks)} tracks for album {album_id}")

            # Return structure with all tracks
            result = first_page.copy()
            result['items'] = all_tracks
            result['next'] = None  # No more pages
            result['limit'] = len(all_tracks)  # Update to reflect all tracks fetched

            return result

        except Exception as e:
            logger.error(f"Error fetching album tracks: {e}")
            return None
    
    def get_artist_albums(self, artist_id: str, album_type: str = 'album,single', limit: int = 50) -> List[Album]:
        """Get albums by artist ID"""
        if not self.is_authenticated():
            return []
        
        try:
            albums = []
            results = self.sp.artist_albums(artist_id, album_type=album_type, limit=limit)
            
            while results:
                for album_data in results['items']:
                    album = Album.from_spotify_album(album_data)
                    albums.append(album)
                
                # Get next batch if available
                results = self.sp.next(results) if results['next'] else None
            
            logger.info(f"Retrieved {len(albums)} albums for artist {artist_id}")
            return albums
            
        except Exception as e:
            logger.error(f"Error fetching artist albums: {e}")
            return []

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        if not self.is_authenticated():
            return None

        try:
            return self.sp.current_user()
        except Exception as e:
            logger.error(f"Error fetching user info: {e}")
            return None

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full artist details from Spotify API.

        Args:
            artist_id: Spotify artist ID

        Returns:
            Dictionary with artist data including images, genres, popularity
        """
        if not self.is_authenticated():
            return None

        try:
            return self.sp.artist(artist_id)
        except Exception as e:
            logger.error(f"Error fetching artist {artist_id}: {e}")
            return None
