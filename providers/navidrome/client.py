import hashlib
import secrets
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json
from core.tiered_logger import get_logger
from core.settings import config_manager
from core.request_manager import RequestManager, RetryConfig, RateLimitConfig, HttpError
from core.provider import get_provider_capabilities

logger = get_logger("navidrome_client")

@dataclass
class NavidromeTrackInfo:
    id: str
    title: str
    artist: str
    album: str
    duration: int
    track_number: Optional[int] = None
    year: Optional[int] = None
    rating: Optional[float] = None

@dataclass
class NavidromePlaylistInfo:
    id: str
    title: str
    description: Optional[str]
    duration: int
    leaf_count: int
    tracks: List[NavidromeTrackInfo]

class NavidromeArtist:
    """Wrapper class to mimic Plex artist object interface"""
    def __init__(self, navidrome_data: Dict[str, Any], client: 'NavidromeClient'):
        self._data = navidrome_data
        self._client = client
        self.ratingKey = navidrome_data.get('id', '')
        self.title = navidrome_data.get('name', 'Unknown Artist')
        self.addedAt = self._parse_date(navidrome_data.get('dateAdded'))

        # Create genres property from Navidrome data
        self.genres = []
        # TODO: Map Navidrome genre data to match Plex format

        # Create summary property (used for timestamp storage)
        self.summary = navidrome_data.get('biography', '') or ''

        # Create thumb property for artist images
        self.thumb = self._get_artist_image_url()

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Navidrome date string to datetime"""
        if not date_str:
            return None
        try:
            # Navidrome uses ISO format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None

    def _get_artist_image_url(self) -> Optional[str]:
        """Generate Navidrome artist image URL using Subsonic getCoverArt API"""
        if not self.ratingKey:
            return None

        # Subsonic getCoverArt API for artist images
        return f"/rest/getCoverArt?id={self.ratingKey}"

    def albums(self) -> List['NavidromeAlbum']:
        """Get all albums for this artist"""
        return self._client.get_albums_for_artist(self.ratingKey)

class NavidromeAlbum:
    """Wrapper class to mimic Plex album object interface"""
    def __init__(self, navidrome_data: Dict[str, Any], client: 'NavidromeClient'):
        self._data = navidrome_data
        self._client = client
        self.ratingKey = navidrome_data.get('id', '')
        self.title = navidrome_data.get('name', 'Unknown Album')
        self.year = navidrome_data.get('year')
        self.addedAt = self._parse_date(navidrome_data.get('created'))
        self._artist_id = navidrome_data.get('artistId', '')

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None

    def artist(self) -> Optional[NavidromeArtist]:
        """Get the album artist"""
        if self._artist_id:
            return self._client.get_artist_by_id(self._artist_id)
        return None

    def tracks(self) -> List['NavidromeTrack']:
        """Get all tracks for this album"""
        return self._client.get_tracks_for_album(self.ratingKey)

class NavidromeTrack:
    """Wrapper class to mimic Plex track object interface"""
    def __init__(self, navidrome_data: Dict[str, Any], client: 'NavidromeClient'):
        self._data = navidrome_data
        self._client = client
        self.ratingKey = navidrome_data.get('id', '')
        self.title = navidrome_data.get('title', 'Unknown Track')
        self.duration = navidrome_data.get('duration', 0) * 1000  # Convert to milliseconds
        self.trackNumber = navidrome_data.get('track')
        self.year = navidrome_data.get('year')
        self.userRating = navidrome_data.get('userRating')
        self.addedAt = self._parse_date(navidrome_data.get('created'))

        self._album_id = navidrome_data.get('albumId', '')
        self._artist_id = navidrome_data.get('artistId', '')

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None

    def artist(self) -> Optional[NavidromeArtist]:
        """Get the track artist"""
        if self._artist_id:
            return self._client.get_artist_by_id(self._artist_id)
        return None

    def album(self) -> Optional[NavidromeAlbum]:
        """Get the track's album"""
        if self._album_id:
            return self._client.get_album_by_id(self._album_id)
        return None

from core.provider import MediaServerProvider

class NavidromeClient(MediaServerProvider):
    name = "navidrome"
    def authenticate(self, **kwargs) -> bool:
        return self.ensure_connection()

    def search(self, query: str, limit: int = 10) -> list:
        if not self.ensure_connection():
            return []
        # Stub: implement actual search logic
        return []

    def get_library_stats(self) -> Dict[str, int]:
        # Stub implementation
        return {}

    def get_all_artists(self) -> list:
        # Stub implementation
        return []

    def get_all_albums(self) -> list:
        # Stub implementation
        return []

    def get_all_tracks(self) -> list:
        # Stub implementation
        return []

    def get_track(self, track_id: str) -> dict:
        # Stub implementation
        return None

    def get_album(self, album_id: str) -> dict:
        # Stub implementation
        return None

    def get_artist(self, artist_id: str) -> dict:
        # Stub implementation
        return None

    def get_user_playlists(self, user_id: Optional[str] = None) -> list:
        # Stub implementation
        return []

    def get_playlist_tracks(self, playlist_id: str) -> list:
        # Stub implementation
        return []

    def get_logo_url(self) -> str:
        return "/static/img/navidrome_logo.png"

    def is_configured(self) -> bool:
        return self.base_url is not None
    def __init__(self):
        super().__init__()
        self.base_url: Optional[str] = None
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self._connection_attempted = False
        self._is_connecting = False

        # Cache for performance
        self._artist_cache = {}
        self._album_cache = {}
        self._track_cache = {}

        # Progress callback for UI updates
        self._progress_callback = None
        
        # Initialize centralized HTTP client for Navidrome (10 requests/second)
        self._http = RequestManager(
            provider='navidrome',
            retry=RetryConfig(max_retries=3, base_backoff=0.5, max_backoff=8.0),
            rate=RateLimitConfig(requests_per_second=10.0)
        )

        # Capability flags
        self.capabilities = get_provider_capabilities('navidrome')
        
        self._register_health_check()
        
        # Legacy plugin_system registration removed - now uses ProviderRegistry for auto-registration
    
    def _register_health_check(self):
        """Register periodic health check for Navidrome server."""
        if not self.is_configured():
            return
        
        from core.health_check import register_health_check_job, HealthCheckResult
        
        def navidrome_health_check() -> HealthCheckResult:
            try:
                connected = self.ensure_connection()
                status = "healthy" if connected else "unhealthy"
                message = "Navidrome server is reachable" if connected else "Navidrome server connection failed"
                return HealthCheckResult(
                    service_name="navidrome",
                    status=status,
                    message=message,
                )
            except Exception as e:
                return HealthCheckResult(
                    service_name="navidrome",
                    status="unhealthy",
                    message=f"Navidrome connection error: {str(e)}",
                )
        
        register_health_check_job("navidrome_health_check", navidrome_health_check, interval_seconds=300)

    def set_progress_callback(self, callback):
        """Set callback function for progress updates"""
        self._progress_callback = callback

    def ensure_connection(self) -> bool:
        """Ensure connection to Navidrome server with lazy initialization."""
        if self._connection_attempted:
            return self.base_url is not None and self.username is not None

        if self._is_connecting:
            return False

        self._is_connecting = True
        try:
            self._setup_client()
            return self.base_url is not None and self.username is not None
        finally:
            self._is_connecting = False
            self._connection_attempted = True

    def _setup_client(self):
        """Setup Navidrome client configuration"""
        config = config_manager.get_navidrome_config()

        if not config.get('base_url'):
            logger.warning("Navidrome server URL not configured")
            return

        if not config.get('username') or not config.get('password'):
            logger.warning("Navidrome username/password not configured")
            return

        self.base_url = config['base_url'].rstrip('/')
        self.username = config['username']
        self.password = config['password']

        try:
            # Test connection with ping
            response = self._make_request('ping')
            if response and response.get('status') == 'ok':
                server_version = response.get('version', 'Unknown')
                logger.info(f"Successfully connected to Navidrome server version: {server_version}")
            else:
                logger.error("Failed to connect to Navidrome server")
                self.base_url = None
                self.username = None
                self.password = None

        except Exception as e:
            logger.error(f"Failed to connect to Navidrome server: {e}")
            self.base_url = None
            self.username = None
            self.password = None

    def _generate_auth_params(self) -> Dict[str, str]:
        """Generate authentication parameters for Subsonic API"""
        if not self.username or not self.password:
            return {}

        # Generate random salt (at least 6 characters)
        salt = secrets.token_hex(8)
        # Calculate token: md5(password + salt)
        token = hashlib.md5((self.password + salt).encode()).hexdigest()

        return {
            'u': self.username,
            't': token,
            's': salt,
            'v': '1.16.1',  # API version
            'c': 'SoulSync',  # Client name
            'f': 'json'  # Response format
        }

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make authenticated request to Navidrome Subsonic API"""
        if not self.base_url or not self.username:
            return None

        url = f"{self.base_url}/rest/{endpoint}"

        # Add authentication parameters
        auth_params = self._generate_auth_params()
        if params:
            auth_params.update(params)

        try:
            response = self._http.get(url, params=auth_params)
            response.raise_for_status()

            data = response.json()

            # Check for Subsonic API errors
            subsonic_response = data.get('subsonic-response', {})
            if subsonic_response.get('status') == 'failed':
                error = subsonic_response.get('error', {})
                error_message = error.get('message', 'Unknown error')
                logger.error(f"Navidrome API error: {error_message}")
                return None

            return subsonic_response

        except HttpError as e:
            logger.error(f"Navidrome API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Navidrome response: {e}")
            return None

    def is_connected(self) -> bool:
        """Check if connected to Navidrome server"""
        if not self._connection_attempted:
            if not self._is_connecting:
                self.ensure_connection()
        return (self.base_url is not None and
                self.username is not None and
                self.password is not None)

    def get_all_artists(self) -> List[NavidromeArtist]:
        """Get all artists from the music library"""
        if not self.ensure_connection():
            logger.error("Not connected to Navidrome server")
            return []

        try:
            if self._progress_callback:
                self._progress_callback("Fetching artists from Navidrome...")

            response = self._make_request('getArtists')
            if not response:
                return []

            if self._progress_callback:
                self._progress_callback("Processing artist data...")

            artists = []
            indexes = response.get('artists', {}).get('index', [])
            total_indexes = len(indexes)

            for i, index in enumerate(indexes):
                if self._progress_callback and total_indexes > 1:
                    progress_pct = int((i / total_indexes) * 100)
                    self._progress_callback(f"Processing artist index {i+1}/{total_indexes} ({progress_pct}%)")

                for artist_data in index.get('artist', []):
                    artist = NavidromeArtist(artist_data, self)
                    # Cache the artist for quick lookup
                    self._artist_cache[artist.ratingKey] = artist
                    artists.append(artist)

            if self._progress_callback:
                self._progress_callback(f"Retrieved {len(artists)} artists from Navidrome")

            logger.info(f"Retrieved {len(artists)} artists from Navidrome")
            return artists

        except Exception as e:
            logger.error(f"Error getting artists from Navidrome: {e}")
            return []

    def get_albums_for_artist(self, artist_id: str) -> List[NavidromeAlbum]:
        """Get all albums for a specific artist"""
        # Check cache first
        if artist_id in self._album_cache:
            return self._album_cache[artist_id]

        if not self.ensure_connection():
            return []

        try:
            # Get artist name for progress display
            artist_name = "Unknown Artist"
            if hasattr(self, '_artist_cache'):
                for cached_artist in self._artist_cache.values():
                    if getattr(cached_artist, 'ratingKey', None) == artist_id:
                        artist_name = getattr(cached_artist, 'title', 'Unknown Artist')
                        break

            if self._progress_callback:
                self._progress_callback(f"Fetching albums for artist {artist_name}...")

            response = self._make_request('getArtist', {'id': artist_id})
            if not response:
                return []

            albums = []
            artist_data = response.get('artist', {})
            album_list = artist_data.get('album', [])

            if self._progress_callback and album_list:
                self._progress_callback(f"Processing {len(album_list)} albums...")

            for album_data in album_list:
                albums.append(NavidromeAlbum(album_data, self))

            # Cache the result
            self._album_cache[artist_id] = albums

            return albums

        except Exception as e:
            logger.error(f"Error getting albums for artist {artist_id}: {e}")
            return []

    def get_tracks_for_album(self, album_id: str) -> List[NavidromeTrack]:
        """Get all tracks for a specific album"""
        # Check cache first
        if album_id in self._track_cache:
            return self._track_cache[album_id]

        if not self.ensure_connection():
            return []

        try:
            # Get album name for progress display
            album_name = "Unknown Album"
            if hasattr(self, '_album_cache'):
                for artist_albums in self._album_cache.values():
                    for cached_album in artist_albums:
                        if getattr(cached_album, 'ratingKey', None) == album_id:
                            album_name = getattr(cached_album, 'title', 'Unknown Album')
                            break
                    if album_name != "Unknown Album":
                        break

            if self._progress_callback:
                self._progress_callback(f"Fetching tracks for album {album_name}...")

            response = self._make_request('getAlbum', {'id': album_id})
            if not response:
                return []

            tracks = []
            album_data = response.get('album', {})
            track_list = album_data.get('song', [])

            if self._progress_callback and track_list:
                self._progress_callback(f"Processing {len(track_list)} tracks...")

            for track_data in track_list:
                tracks.append(NavidromeTrack(track_data, self))

            # Cache the result
            self._track_cache[album_id] = tracks

            return tracks

        except Exception as e:
            logger.error(f"Error getting tracks for album {album_id}: {e}")
            return []

    def get_artist_by_id(self, artist_id: str) -> Optional[NavidromeArtist]:
        """Get a specific artist by ID"""
        # Check cache first
        if artist_id in self._artist_cache:
            return self._artist_cache[artist_id]

        if not self.ensure_connection():
            return None

        try:
            response = self._make_request('getArtist', {'id': artist_id})
            if response and 'artist' in response:
                artist = NavidromeArtist(response['artist'], self)
                # Cache for future use
                self._artist_cache[artist_id] = artist
                return artist
            return None

        except Exception as e:
            logger.error(f"Error getting artist {artist_id}: {e}")
            return None

    def get_album_by_id(self, album_id: str) -> Optional[NavidromeAlbum]:
        """Get a specific album by ID"""
        if not self.ensure_connection():
            return None

        try:
            response = self._make_request('getAlbum', {'id': album_id})
            if response and 'album' in response:
                return NavidromeAlbum(response['album'], self)
            return None

        except Exception as e:
            logger.error(f"Error getting album {album_id}: {e}")
            return None

    def get_library_stats(self) -> Dict[str, int]:
        """Get library statistics"""
        if not self.ensure_connection():
            return {}

        try:
            # Get counts by making API calls
            stats = {}

            # Get artist count
            artists = self.get_all_artists()
            stats['artists'] = len(artists)

            # For albums and tracks, we'd need to iterate through all artists
            # This is expensive, so let's use reasonable estimates or make separate calls
            # For now, return what we can efficiently get
            stats['albums'] = 0
            stats['tracks'] = 0

            # TODO: Implement more efficient counting if Navidrome provides bulk stats

            return stats

        except Exception as e:
            logger.error(f"Error getting library stats: {e}")
            return {}

    def get_all_playlists(self) -> List[NavidromePlaylistInfo]:
        """Get all playlists from Navidrome server"""
        if not self.ensure_connection():
            return []

        try:
            response = self._make_request('getPlaylists')
            if not response:
                return []

            playlists = []
            playlists_data = response.get('playlists', {}).get('playlist', [])

            for playlist_data in playlists_data:
                playlist_info = NavidromePlaylistInfo(
                    id=playlist_data.get('id', ''),
                    title=playlist_data.get('name', 'Unknown Playlist'),
                    description=playlist_data.get('comment'),
                    duration=playlist_data.get('duration', 0) * 1000,  # Convert to milliseconds
                    leaf_count=playlist_data.get('songCount', 0),
                    tracks=[]  # Will be populated when needed
                )
                playlists.append(playlist_info)

            logger.info(f"Retrieved {len(playlists)} playlists from Navidrome")
            return playlists

        except Exception as e:
            logger.error(f"Error getting playlists from Navidrome: {e}")
            return []

    def get_playlist_by_name(self, name: str) -> Optional[NavidromePlaylistInfo]:
        """Get a specific playlist by name"""
        playlists = self.get_all_playlists()
        for playlist in playlists:
            if playlist.title.lower() == name.lower():
                return playlist
        return None

    def create_playlist(self, name: str, tracks) -> bool:
        """Create a new playlist with given tracks"""
        if not self.ensure_connection():
            return False

        try:
            # Convert tracks to Navidrome track IDs
            track_ids = []
            for track in tracks:
                if hasattr(track, 'ratingKey'):
                    track_ids.append(str(track.ratingKey))
                elif hasattr(track, 'id'):
                    track_ids.append(str(track.id))

            if not track_ids:
                logger.warning(f"No valid tracks provided for playlist '{name}'")
                return False

            logger.info(f"Creating Navidrome playlist '{name}' with {len(track_ids)} tracks")

            # Create playlist with tracks
            params = {
                'name': name,
                'songId': track_ids  # Subsonic API accepts multiple songId parameters
            }

            response = self._make_request('createPlaylist', params)

            if response and response.get('status') == 'ok':
                logger.info(f"✅ Created Navidrome playlist '{name}' with {len(track_ids)} tracks")
                return True
            else:
                logger.error(f"Failed to create Navidrome playlist '{name}'")
                return False

        except Exception as e:
            logger.error(f"Error creating Navidrome playlist '{name}': {e}")
            return False

    def copy_playlist(self, source_name: str, target_name: str) -> bool:
        """Copy a playlist to create a backup"""
        if not self.ensure_connection():
            return False

        try:
            # Get the source playlist
            source_playlist = self.get_playlist_by_name(source_name)
            if not source_playlist:
                logger.error(f"Source playlist '{source_name}' not found")
                return False

            # Get tracks from source playlist
            source_tracks = self.get_playlist_tracks(source_playlist.id)
            logger.debug(f"Retrieved {len(source_tracks) if source_tracks else 0} tracks from source playlist")

            # Validate tracks
            if not source_tracks:
                logger.warning(f"Source playlist '{source_name}' has no tracks to copy")
                return False

            # Delete target playlist if it exists (for overwriting backup)
            try:
                target_playlist = self.get_playlist_by_name(target_name)
                if target_playlist:
                    self._make_request('deletePlaylist', {'id': target_playlist.id})
                    logger.info(f"Deleted existing backup playlist '{target_name}'")
            except Exception:
                pass  # Target doesn't exist, which is fine

            # Create new playlist with copied tracks
            try:
                success = self.create_playlist(target_name, source_tracks)
                if success:
                    logger.info(f"✅ Created backup playlist '{target_name}' with {len(source_tracks)} tracks")
                    return True
                else:
                    logger.error(f"Failed to create backup playlist '{target_name}'")
                    return False
            except Exception as create_error:
                logger.error(f"Failed to create backup playlist: {create_error}")
                return False

        except Exception as e:
            logger.error(f"Error copying playlist '{source_name}' to '{target_name}': {e}")
            return False

    def get_playlist_tracks(self, playlist_id: str) -> List[NavidromeTrack]:
        """Get all tracks from a specific playlist"""
        if not self.ensure_connection():
            return []

        try:
            response = self._make_request('getPlaylist', {'id': playlist_id})
            if not response:
                return []

            tracks = []
            playlist_data = response.get('playlist', {})

            for track_data in playlist_data.get('entry', []):
                tracks.append(NavidromeTrack(track_data, self))

            logger.debug(f"Retrieved {len(tracks)} tracks from playlist {playlist_id}")
            return tracks

        except Exception as e:
            logger.error(f"Error getting tracks for playlist {playlist_id}: {e}")
            return []

    def update_playlist(self, playlist_name: str, tracks) -> bool:
        """Update an existing playlist or create it if it doesn't exist"""
        if not self.ensure_connection():
            return False

        try:
            existing_playlist = self.get_playlist_by_name(playlist_name)

            # Check if backup is enabled in config
            from core.settings import config_manager
            create_backup = config_manager.get('playlist_sync.create_backup', True)

            if existing_playlist and create_backup:
                backup_name = f"{playlist_name} Backup"
                logger.info(f"🛡️ Creating backup playlist '{backup_name}' before sync")

                if self.copy_playlist(playlist_name, backup_name):
                    logger.info(f"✅ Backup created successfully")
                else:
                    logger.warning(f"⚠️ Failed to create backup, continuing with sync")

            if existing_playlist:
                # Delete existing playlist
                response = self._make_request('deletePlaylist', {'id': existing_playlist.id})
                if response and response.get('status') == 'ok':
                    logger.info(f"Deleted existing Navidrome playlist '{playlist_name}'")
                else:
                    logger.warning(f"Could not delete existing playlist '{playlist_name}', creating anyway")

            # Create new playlist with tracks
            return self.create_playlist(playlist_name, tracks)

        except Exception as e:
            logger.error(f"Error updating Navidrome playlist '{playlist_name}': {e}")
            return False

    def _trigger_scan_api(self, path: Optional[str] = None) -> bool:
        """
        Navidrome-specific: Trigger library scan.
        Navidrome doesn't require explicit scans - library is always current.
        """
        logger.info(f"Navidrome doesn't require library scans - library is always current")
        return True

    def _get_scan_status_api(self) -> Dict[str, Any]:
        """
        Navidrome-specific: Get library scan status.
        Navidrome doesn't have scanning - always idle.
        """
        return {
            'scanning': False,
            'progress': 100,
            'eta_seconds': None,
            'error': None
        }

    def get_content_changes_since(self, last_update: Optional[datetime] = None):
        """
        Get content changes since last update using Navidrome-specific incremental detection.
        Uses date-sorted album approach since Navidrome doesn't have direct recent content APIs.
        """
        from core.content_models import ContentChanges
        
        if not self.ensure_connection():
            logger.error("Not connected to Navidrome server")
            return ContentChanges()
        
        # If no last_update provided, return all content (full refresh)
        if last_update is None:
            logger.info("No last_update provided - performing full content retrieval")
            artists = self.get_all_artists()
            return ContentChanges(
                artists=artists,
                albums=[],  # Will be fetched per-artist during processing
                tracks=[],  # Will be fetched per-album during processing
                full_refresh=True,
                last_checked=datetime.now()
            )
        
        try:
            logger.info(f"Getting Navidrome content changes since {last_update}")
            
            # Navidrome doesn't have direct "recent albums" API
            # Get albums from sample of artists and sort by date
            all_artists = self.get_all_artists()
            if not all_artists:
                logger.info("No artists found")
                return ContentChanges(last_checked=datetime.now())
            
            # Sample first 200 artists to get recent albums
            sample_artists = all_artists[:200]
            all_albums = []
            
            for artist in sample_artists:
                try:
                    artist_albums = self.get_albums_for_artist(artist.ratingKey)
                    all_albums.extend(artist_albums)
                except Exception as e:
                    logger.warning(f"Error getting albums for artist: {e}")
                    continue
            
            if not all_albums:
                logger.info("No albums found")
                return ContentChanges(last_checked=datetime.now())
            
            # Sort by addedAt date (newest first) and take recent ones
            try:
                def get_sort_date(album):
                    date_val = getattr(album, 'addedAt', None)
                    if date_val is None:
                        return 0
                    return date_val
                
                all_albums.sort(key=get_sort_date, reverse=True)
                recent_albums = all_albums[:400]  # Take most recent 400
                
                logger.info(f"Found {len(recent_albums)} recent albums from Navidrome")
            except Exception as e:
                logger.warning(f"Error sorting albums: {e}")
                recent_albums = all_albums[:400]
            
            # Extract unique artists from recent albums
            processed_artist_ids = set()
            artists_to_return = []
            
            for album in recent_albums:
                try:
                    album_artist = album.artist()
                    if album_artist:
                        artist_id = str(album_artist.ratingKey)
                        if artist_id not in processed_artist_ids:
                            processed_artist_ids.add(artist_id)
                            artists_to_return.append(album_artist)
                except Exception as e:
                    logger.debug(f"Error getting artist for album: {e}")
                    continue
            
            logger.info(f"Navidrome incremental: Found {len(artists_to_return)} artists with recent albums")
            
            return ContentChanges(
                artists=artists_to_return,
                albums=recent_albums,
                tracks=[],  # Will be fetched per-album during processing
                full_refresh=False,
                last_checked=datetime.now(),
                metadata={'recent_albums_checked': len(recent_albums), 'sample_artists': len(sample_artists)}
            )
            
        except Exception as e:
            logger.error(f"Error getting Navidrome content changes: {e}")
            return ContentChanges()

    # Metadata update methods for compatibility with metadata updater
    def update_artist_genres(self, artist, genres: List[str]):
        """Update artist genres - not implemented for Navidrome"""
        try:
            logger.debug(f"Genre update not implemented for Navidrome artist: {artist.title}")
            return True
        except Exception as e:
            logger.error(f"Error updating genres for {artist.title}: {e}")
            return False

    def update_artist_poster(self, artist, image_data: bytes):
        """Update artist poster image - not implemented for Navidrome"""
        try:
            logger.debug(f"Poster update not implemented for Navidrome artist: {artist.title}")
            return True
        except Exception as e:
            logger.error(f"Error updating poster for {artist.title}: {e}")
            return False

    def update_album_poster(self, album, image_data: bytes):
        """Update album poster image - not implemented for Navidrome"""
        try:
            logger.debug(f"Poster update not implemented for Navidrome album: {album.title}")
            return True
        except Exception as e:
            logger.error(f"Error updating poster for album {album.title}: {e}")
            return False

    def update_artist_biography(self, artist) -> bool:
        """Update artist biography - not implemented for Navidrome"""
        try:
            logger.debug(f"Biography update not implemented for Navidrome artist: {artist.title}")
            return True
        except Exception as e:
            logger.error(f"Error updating biography for {artist.title}: {e}")
            return False

    def needs_update_by_age(self, artist, refresh_interval_days: int) -> bool:
        """Check if artist needs updating based on age threshold - simplified for Navidrome"""
        try:
            # For now, just return True for all artists since we don't have timestamp tracking yet
            return True
        except Exception as e:
            logger.debug(f"Error checking update age for {artist.title}: {e}")
            return True

    def is_artist_ignored(self, artist) -> bool:
        """Check if artist is manually marked to be ignored - simplified for Navidrome"""
        try:
            # For now, no artists are ignored
            return False
        except Exception as e:
            logger.debug(f"Error checking ignore status for {artist.title}: {e}")
            return False

    def parse_update_timestamp(self, artist) -> Optional[datetime]:
        """Parse the last update timestamp from artist summary - not implemented for Navidrome"""
        try:
            return None
        except Exception as e:
            logger.debug(f"Error parsing timestamp for {artist.title}: {e}")
            return None

    def get_cache_stats(self):
        """Get cache statistics for debugging/logging"""
        return {
            'artists_cached': len(self._artist_cache),
            'albums_cached': len(self._album_cache),
            'tracks_cached': len(self._track_cache),
            'bulk_albums_cached': len(self._album_cache),  # For compatibility with Jellyfin interface
            'bulk_tracks_cached': len(self._track_cache)   # For compatibility with Jellyfin interface
        }

    def clear_cache(self):
        """Clear all caches to force fresh data on next request"""
        self._artist_cache.clear()
        self._album_cache.clear()
        self._track_cache.clear()
        logger.info("Navidrome client cache cleared")

    def search_tracks(self, title: str, artist: str, limit: int = 15) -> List[NavidromeTrackInfo]:
        """Search for tracks using Navidrome search API"""
        if not self.ensure_connection():
            logger.warning("Navidrome not connected. Cannot perform search.")
            return []

        try:
            # Use Subsonic search3 API for music search
            query = f"{artist} {title}".strip()
            response = self._make_request('search3', {
                'query': query,
                'songCount': limit,
                'artistCount': 0,
                'albumCount': 0
            })

            if not response:
                return []

            tracks = []
            search_result = response.get('searchResult3', {})

            for track_data in search_result.get('song', []):
                track_info = NavidromeTrackInfo(
                    id=track_data.get('id', ''),
                    title=track_data.get('title', ''),
                    artist=track_data.get('artist', ''),
                    album=track_data.get('album', ''),
                    duration=track_data.get('duration', 0) * 1000,  # Convert to milliseconds
                    track_number=track_data.get('track'),
                    year=track_data.get('year'),
                    rating=track_data.get('userRating')
                )

                # Store reference to original track for playlist creation
                track_info._original_navidrome_track = NavidromeTrack(track_data, self)
                tracks.append(track_info)

            logger.info(f"Found {len(tracks)} tracks for '{title}' by '{artist}'")
            return tracks

        except Exception as e:
            logger.error(f"Error searching for tracks: {e}")
            return []
    
    def get_album_tracks_as_soulsync(self, album) -> List:
        """
        Get all tracks from a Navidrome album converted to SoulSyncTrack objects.
        
        Args:
            album: Navidrome album object (NavidromeAlbum wrapper)
            
        Returns:
            List of SoulSyncTrack objects with ISRC/MBID extracted
        """
        from core.matching_engine.soul_sync_track import SoulSyncTrack
        from providers.navidrome.adapter import convert_navidrome_track_to_soulsync
        
        soul_sync_tracks = []
        
        try:
            # Get album ID from the album object
            album_id = getattr(album, 'id', getattr(album, 'ratingKey', None))
            if not album_id:
                logger.warning("Could not get album ID for Navidrome album")
                return soul_sync_tracks
            
            # Get tracks for this album
            tracks = self.get_tracks_for_album(album_id)
            logger.debug(f"Getting {len(tracks)} tracks from Navidrome album '{getattr(album, 'title', 'Unknown')}'")
            
            failed_count = 0
            for track in tracks:
                try:
                    soul_track = convert_navidrome_track_to_soulsync(track)
                    if soul_track:
                        soul_sync_tracks.append(soul_track)
                    else:
                        failed_count += 1
                        logger.warning(f"Converter returned None for Navidrome track at album {album_id}")
                except Exception as track_err:
                    failed_count += 1
                    logger.error(f"Error converting Navidrome track: {track_err}")
            
            if failed_count > 0:
                logger.warning(f"⚠️ Navidrome album '{getattr(album, 'title', 'Unknown')}': {len(tracks)} tracks, {len(soul_sync_tracks)} converted, {failed_count} failed")
                
        except Exception as e:
            logger.error(f"Error getting Navidrome album tracks as SoulSyncTrack: {e}")
        
        return soul_sync_tracks