"""
Plex Music Provider - Refactored
Simplified implementation using SoulSyncTrack and new core features.
"""

from core.provider_base import ProviderBase
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.settings import config_manager
from core.health_check import register_health_check_job, HealthCheckResult
from plexapi.server import PlexServer
from plexapi.library import MusicSection
from plexapi.audio import Track as PlexTrack
from plexapi.exceptions import NotFound
from typing import List, Optional, Dict, Any
import time
from utils.logging_config import get_logger

logger = get_logger("plex_client")


class PlexClient(ProviderBase):
    """Plex music provider - streams music from Plex media server."""
    
    name = "plex"
    category = "provider"
    supports_downloads = False
    
    def __init__(self):
        """Initialize Plex provider."""
        super().__init__()
        self.server: Optional[PlexServer] = None
        self.music_library: Optional[MusicSection] = None
        self._connection_attempted = False
        self._is_connecting = False
        self._last_connection_attempt = 0
        self._connection_check_interval = 30
        self._register_health_check()
    
    def _register_health_check(self):
        """Register periodic health check for Plex server."""
        def plex_health_check() -> HealthCheckResult:
            try:
                connected = self.ensure_connection()
                status = "healthy" if connected else "unhealthy"
                message = "Plex server is reachable" if connected else "Plex server connection failed"
                return HealthCheckResult(
                    service_name="plex",
                    status=status,
                    message=message,
                )
            except Exception as e:
                return HealthCheckResult(
                    service_name="plex",
                    status="unhealthy",
                    message=f"Plex connection error: {str(e)}",
                )
        
        register_health_check_job("plex_health_check", plex_health_check, interval_seconds=60)
    
    def authenticate(self, **kwargs) -> bool:
        """Authenticate with Plex server."""
        return self.ensure_connection()
    
    def is_configured(self) -> bool:
        """Check if Plex is configured and connected."""
        return self.server is not None
    
    def get_logo_url(self) -> str:
        """Return Plex logo URL."""
        return "/static/img/plex_logo.png"
    
    def is_connected(self) -> bool:
        """Compatibility method used by sync service."""
        return self.ensure_connection()

    def search_tracks(self, query: str, limit: int = 10) -> List[SoulSyncTrack]:
        """Compatibility wrapper for services expecting search_tracks()."""
        return self.search(query=query, type="track", limit=limit)

    def update_playlist(self, name: str, tracks: List[Any]) -> bool:
        """Create or replace a Plex playlist with provided native Plex track items.

        Expects `tracks` to be native Plex Track objects with ratingKey attributes.
        """
        if not self.ensure_connection() or not self.server:
            return False
        try:
            # Try to remove existing playlist with same name (if exists)
            try:
                existing = self.server.playlist(name)
                try:
                    existing.delete()
                except Exception:
                    # Fallback: remove items if delete not permitted
                    try:
                        items = list(existing.items())
                        if items:
                            existing.removeItems(items)
                    except Exception:
                        pass
            except Exception:
                pass

            # Create new playlist with provided tracks
            from plexapi.playlist import Playlist
            Playlist.create(self.server, name, tracks, playlistType='audio')
            logger.info(f"Updated Plex playlist: {name} with {len(tracks)} tracks")
            return True
        except Exception as e:
            logger.error(f"Error updating Plex playlist '{name}': {e}")
            return False

    # ===== CORE METHODS =====
    
    def search(self, query: str, type: str = "track", limit: int = 10) -> List[SoulSyncTrack]:
        """Search for tracks in Plex library."""
        if not self.ensure_connection() or not self.music_library:
            logger.warning("Plex not connected or no music library")
            return []
        
        try:
            results = self.music_library.search(query, libtype=type, maxresults=limit)
            tracks = []
            
            for result in results:
                if isinstance(result, PlexTrack):
                    track = self._convert_track_to_soulsync(result)
                    if track:
                        tracks.append(track)
            
            logger.debug(f"Search '{query}' returned {len(tracks)} tracks")
            return tracks
        
        except Exception as e:
            logger.error(f"Error searching Plex: {e}")
            return []
    
    def get_track(self, track_id: str) -> Optional[SoulSyncTrack]:
        """Fetch single track by Plex ratingKey."""
        if not self.ensure_connection() or not self.music_library:
            return None
        
        try:
            track = self.music_library.fetchItem(int(track_id))
            if isinstance(track, PlexTrack):
                return self._convert_track_to_soulsync(track)
        except Exception as e:
            logger.error(f"Error fetching track {track_id}: {e}")
        
        return None
    
    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        """Fetch album by ID (stub - not typically needed)."""
        # Albums are accessed through search/playlist methods
        return None
    
    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """Fetch artist by ID (stub - not typically needed)."""
        # Artists are accessed through search/playlist methods
        return None
    
    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get playlists from Plex server."""
        if not self.ensure_connection() or not self.server:
            return []
        
        try:
            playlists = []
            for playlist in self.server.playlists():
                # Filter for music playlists only
                if hasattr(playlist, 'playlistType') and playlist.playlistType == 'audio':
                    playlists.append({
                        'id': str(playlist.ratingKey),
                        'name': playlist.title,
                        'description': getattr(playlist, 'summary', None),
                        'track_count': playlist.leafCount if hasattr(playlist, 'leafCount') else 0,
                    })
            
            logger.debug(f"Found {len(playlists)} music playlists")
            return playlists
        
        except Exception as e:
            logger.error(f"Error fetching playlists: {e}")
            return []
    
    def get_playlist_tracks(self, playlist_id: str) -> List[SoulSyncTrack]:
        """Get all tracks from a playlist."""
        if not self.ensure_connection() or not self.server:
            return []
        
        try:
            playlist = self.server.playlist(int(playlist_id))
            tracks = []
            
            for item in playlist.items():
                if isinstance(item, PlexTrack):
                    track = self._convert_track_to_soulsync(item)
                    if track:
                        tracks.append(track)
            
            logger.debug(f"Playlist {playlist_id} has {len(tracks)} tracks")
            return tracks
        
        except Exception as e:
            logger.error(f"Error fetching playlist {playlist_id}: {e}")
            return []
    
    # ===== LIBRARY METHODS =====
    
    def get_music_libraries(self) -> List[Dict[str, str]]:
        """Get all music library sections from Plex server."""
        if not self.ensure_connection() or not self.server:
            return []
        
        try:
            libraries = []
            for section in self.server.library.sections():
                if section.type == 'artist':
                    libraries.append({
                        'title': section.title,
                        'key': str(section.key)
                    })
            
            logger.debug(f"Found {len(libraries)} music libraries")
            return libraries
        
        except Exception as e:
            logger.error(f"Error fetching libraries: {e}")
            return []
    
    def set_music_library(self, library_key: str) -> bool:
        """Set active music library by key."""
        if not self.ensure_connection() or not self.server:
            return False
        
        try:
            section = self.server.library.section(library_key)
            if section.type == 'artist':
                self.music_library = section
                logger.info(f"Set music library to: {section.title}")
                return True
        except Exception as e:
            logger.error(f"Error setting music library: {e}")
        
        return False
    
    def get_all_tracks(self, limit: Optional[int] = None) -> List[SoulSyncTrack]:
        """Get all tracks from active music library."""
        if not self.ensure_connection() or not self.music_library:
            logger.warning("No active music library")
            return []
        
        try:
            tracks = []
            
            # Use maxresults parameter to fetch tracks (Plex doesn't support offset for searchTracks)
            # searchTracks will fetch all matching tracks up to maxresults limit
            max_results = limit if limit else 999999
            logger.info(f"Calling Plex searchTracks with maxresults={max_results}")
            all_tracks = self.music_library.searchTracks(maxresults=max_results)
            
            logger.info(f"Plex returned {len(all_tracks)} raw tracks from library")
            
            conversion_errors = 0
            skipped_non_track = 0
            successful_conversions = 0
            
            for idx, item in enumerate(all_tracks):
                # Log progress every 100 items to see if loop is hanging
                if idx % 100 == 0 and idx > 0:
                    logger.debug(
                        "Processing tracks: %s/%s (%s converted, %s errors)",
                        idx,
                        len(all_tracks),
                        successful_conversions,
                        conversion_errors,
                    )
                
                if isinstance(item, PlexTrack):
                    try:
                        track = self._convert_track_to_soulsync(item)
                        if track:
                            tracks.append(track)
                            successful_conversions += 1
                            if idx < 5:  # Log first 5 tracks for debugging
                                logger.debug(
                                    "Converted track #%s: %s by %s",
                                    idx + 1,
                                    track.title,
                                    track.artist_name,
                                )
                        else:
                            conversion_errors += 1
                            if conversion_errors <= 3:  # Log first 3 conversion failures
                                logger.warning(f"Conversion returned None for track: {getattr(item, 'title', 'Unknown')}")
                    except Exception as e:
                        conversion_errors += 1
                        if conversion_errors <= 3:
                            logger.error(f"Error converting track '{getattr(item, 'title', 'Unknown')}': {e}", exc_info=True)
                else:
                    skipped_non_track += 1
                
                if limit and len(tracks) >= limit:
                    tracks = tracks[:limit]
                    break
            
            logger.info(f"Track conversion complete: {successful_conversions} tracks successfully converted, {conversion_errors} errors, {skipped_non_track} non-track items skipped")
            return tracks
        
        except Exception as e:
            logger.error(f"Error fetching all tracks from Plex: {e}", exc_info=True)
            return []
    
    def get_all_albums(self) -> List[Dict[str, Any]]:
        """Get all albums from active music library."""
        if not self.ensure_connection() or not self.music_library:
            return []
        
        try:
            albums = self.music_library.searchAlbums(limit=99999)
            logger.info(f"Found {len(albums)} albums in Plex library")
            return [
                {
                    'id': str(album.ratingKey),
                    'title': album.title,
                    'artist': album.artist().title if album.artist() else 'Unknown',
                }
                for album in albums
            ]
        except Exception as e:
            logger.error(f"Error fetching albums: {e}")
            return []
    
    def get_library_stats(self) -> Dict[str, int]:
        """Get statistics about active library."""
        if not self.ensure_connection() or not self.music_library:
            return {}
        
        try:
            return {
                'total_tracks': self.music_library.totalSize if hasattr(self.music_library, 'totalSize') else 0,
                'albums': len(self.music_library.searchAlbums(limit=99999)),
                'artists': len(self.music_library.searchArtists(limit=99999)),
            }
        except Exception as e:
            logger.error(f"Error getting library stats: {e}")
            return {}
    
    # ===== INTERNAL METHODS =====
    
    def _convert_track_to_soulsync(self, plex_track: PlexTrack) -> Optional[SoulSyncTrack]:
        """Convert Plex track to SoulSyncTrack using factory method."""
        try:
            # Extract basic metadata
            title = getattr(plex_track, 'title', None)
            
            # Handle artist and album gracefully
            artist = None
            try:
                artist_obj = plex_track.artist()
                artist = getattr(artist_obj, 'title', None) if artist_obj else None
                logger.debug(f"Extracted artist for '{title}': artist_obj={artist_obj}, artist_title={artist}")
            except (NotFound, AttributeError, Exception) as e:
                logger.warning(f"Failed to get artist for track '{title}': {e}")
            
            album = None
            try:
                album_obj = plex_track.album()
                album = getattr(album_obj, 'title', None) if album_obj else None
            except (NotFound, AttributeError, Exception) as e:
                logger.debug(f"Failed to get album for track '{title}': {e}")
            
            if not title:
                logger.warning(f"Skipping track - missing title")
                return None
            
            if not artist:
                logger.warning(f"Skipping track '{title}' - missing artist (artist_obj extraction failed)")
                return None
            
            # Extract audio metadata
            duration_ms = getattr(plex_track, 'duration', None)
            year = getattr(plex_track, 'year', None)
            track_number = getattr(plex_track, 'trackNumber', None)
            disc_number = getattr(plex_track, 'discNumber', None)
            
            # Extract file metadata
            file_path = None
            file_format = None
            bitrate = None
            
            if hasattr(plex_track, 'media') and plex_track.media:
                media = plex_track.media[0]
                bitrate = getattr(media, 'bitrate', None)
                
                if hasattr(media, 'container'):
                    file_format = getattr(media, 'container', None)
                
                if hasattr(media, 'parts') and media.parts:
                    file_path = getattr(media.parts[0], 'file', None)
            
            # Extract Plex track ID (ratingKey)
            plex_track_id = str(getattr(plex_track, 'ratingKey', None))
            
            if not plex_track_id or plex_track_id == 'None':
                logger.warning(f"Track '{title}' by '{artist}' has no ratingKey - cannot save to database")
                return None
            
            logger.debug(
                "Plex track data before factory: title='%s' artist='%s' album='%s' "
                "duration=%s year=%s track#=%s disc#=%s bitrate=%s format=%s id=%s",
                title, artist, album, duration_ms, year, track_number, disc_number,
                bitrate, file_format, plex_track_id
            )
            
            # Build data dict for factory
            track_data = {
                'title': title,
                'titleSort': getattr(plex_track, 'titleSort', None),
                'grandparentTitle': getattr(plex_track, 'grandparentTitle', None) or artist,
                'grandparentSortTitle': getattr(plex_track, 'grandparentSortTitle', None),
                'parentTitle': getattr(plex_track, 'parentTitle', None) or album,
                'parentSortTitle': getattr(plex_track, 'parentSortTitle', None),
                'year': year,
                'index': track_number,
                'parentIndex': disc_number,
                'duration': duration_ms,
                'ratingKey': plex_track_id,
                'addedAt': getattr(plex_track, 'addedAt', None),
                # Construct Media/Part structure for tech metadata
                'Media': []
            }

            # Reconstruct Media parts if available
            if hasattr(plex_track, 'media') and plex_track.media:
                media_item = plex_track.media[0]
                media_data = {
                    'bitrate': getattr(media_item, 'bitrate', None),
                    'container': getattr(media_item, 'container', None),
                    'Part': []
                }

                if hasattr(media_item, 'parts') and media_item.parts:
                    part = media_item.parts[0]
                    part_data = {
                        'file': getattr(part, 'file', None),
                        'size': getattr(part, 'size', None),
                        'Stream': []
                    }

                    if hasattr(part, 'streams') and part.streams:
                        for stream in part.streams:
                            stream_data = {
                                'streamType': getattr(stream, 'streamType', None),
                                'codec': getattr(stream, 'codec', None),
                                'samplingRate': getattr(stream, 'samplingRate', None),
                                'bitDepth': getattr(stream, 'bitDepth', None),
                                'bitrate': getattr(stream, 'bitrate', None)
                            }
                            part_data['Stream'].append(stream_data)

                    media_data['Part'].append(part_data)

                track_data['Media'].append(media_data)

            # Use new factory method
            track = SoulSyncTrack.from_plex(track_data)
            
            if track:
                logger.debug(
                    "Successfully created SoulSyncTrack: '%s' by '%s' with identifiers=%s",
                    track.title,
                    track.artist_name,
                    track.identifiers,
                )
            else:
                logger.warning(f"create_soul_sync_track returned None for '{title}' by '{artist}'")
            
            return track
        
        except Exception as e:
            logger.error(f"Error converting Plex track '{getattr(plex_track, 'title', 'Unknown')}': {e}", exc_info=True)
            return None
    
    def ensure_connection(self) -> bool:
        """Ensure connection to Plex server with lazy initialization."""
        # Test existing connection
        if self.server is not None:
            try:
                self.server.library.sections()
                return True
            except Exception:
                logger.info("Plex connection lost, reconnecting...")
                self.server = None
        
        # Avoid concurrent connection attempts
        if self._is_connecting:
            return False
        
        # Back off if recent attempt failed
        now = time.time()
        if self._connection_attempted and (now - self._last_connection_attempt < self._connection_check_interval):
            return self.server is not None
        
        self._is_connecting = True
        try:
            self._last_connection_attempt = now
            self._setup_connection()
            return self.server is not None
        finally:
            self._is_connecting = False
            self._connection_attempted = True
    
    def _setup_connection(self):
        """Establish connection to Plex server."""
        config = config_manager.get_plex_config()
        
        if not config.get('base_url'):
            logger.warning("Plex server URL not configured")
            return
        
        if not config.get('token'):
            logger.error("Plex token not configured")
            return
        
        try:
            # 15 second timeout to prevent hangs on slow servers
            self.server = PlexServer(config['base_url'], config['token'], timeout=15)
            self._find_music_library()
            logger.debug(f"Connected to Plex: {self.server.friendlyName}")
        
        except Exception as e:
            logger.error(f"Failed to connect to Plex: {e}")
            self.server = None
    
    def _find_music_library(self):
        """Automatically find and set active music library."""
        if not self.server:
            return
        
        try:
            # Collect all music libraries
            music_sections = [
                section for section in self.server.library.sections()
                if section.type == 'artist'
            ]
            
            if not music_sections:
                logger.warning("No music library found on Plex server")
                return
            
            # Try priority names first
            for priority_name in ['Music', 'music', 'Audio', 'audio', 'Songs', 'songs']:
                for section in music_sections:
                    if section.title == priority_name:
                        self.music_library = section
                        logger.info(f"Selected music library: {section.title}")
                        return
            
            # Fall back to first music library found
            self.music_library = music_sections[0]
            logger.info(f"Selected music library: {self.music_library.title}")
        
        except Exception as e:
            logger.error(f"Error finding music library: {e}")
