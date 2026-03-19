"""
Plex Music Provider - Refactored
Simplified implementation using SoulSyncTrack and new core features.
"""

from core.provider_base import ProviderBase
from core.provider import ProviderCapabilities, PlaylistSupport, SearchCapabilities, MetadataRichness
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.settings import config_manager
from core.path_mapper import PathMapper
from core.health_check import register_health_check_job, HealthCheckResult
from plexapi.server import PlexServer
from plexapi.library import MusicSection
from plexapi.audio import Track as PlexTrack
from plexapi.exceptions import NotFound
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import time
from core.tiered_logger import get_logger

logger = get_logger("plex_client")


class PlexClient(ProviderBase):
    """Plex music provider - streams music from Plex media server."""
    
    name = "plex"
    category = "provider"
    supports_downloads = False
    capabilities = ProviderCapabilities(
        name='plex',
        supports_playlists=PlaylistSupport.READ_WRITE,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=False),
        metadata=MetadataRichness.HIGH,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=True,
        supports_streaming=False,
        supports_downloads=False,
    )
    
    def __init__(self, account_id: Optional[int] = None):
        """Initialize Plex provider."""
        super().__init__()
        self.server: Optional[PlexServer] = None
        self.music_library: Optional[MusicSection] = None
        self.path_mapper: Optional[PathMapper] = None
        self._connection_attempted = False
        self._is_connecting = False
        self._last_connection_attempt = 0
        self._connection_check_interval = 30

        # Auto-detect active account if not provided
        if account_id is None:
            try:
                from core.storage import get_storage_service
                storage = get_storage_service()
                accounts = storage.list_accounts('plex')
                if accounts:
                    account_id = accounts[0].get('id')
                    logger.info(f"No Plex account explicitly requested, defaulting to account: {account_id}")
            except Exception as e:
                logger.warning(f"Failed to auto-detect Plex account: {e}")

        self.account_id = account_id
        self._register_health_check()
    
    def _register_health_check(self):
        """Register periodic health check for Plex server."""
        if not self.is_configured():
            return
        
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
        
        register_health_check_job("plex_health_check", plex_health_check, interval_seconds=300)
    
    def authenticate(self, **kwargs) -> bool:
        """Authenticate with Plex server."""
        return self.ensure_connection()
    
    def is_configured(self) -> bool:
        """Check if Plex is configured (has credentials)."""
        # A Plex account requires an associated access token and a server base_url
        if not self.account_id:
            return False

        from core.storage import get_storage_service
        from core.settings import config_manager
        storage = get_storage_service()

        # Check token existence (Secure SQLite DB)
        token_data = storage.get_account_token(self.account_id)
        token = token_data.get('access_token') if token_data else None

        # Check base_url existence from config.json (Hybrid approach)
        plex_config = config_manager.get('plex', {})
        base_url = plex_config.get('base_url') or plex_config.get('server_url')

        # Fallback to older config format just in case
        if not base_url:
            base_url = config_manager.get('plex.base_url') or config_manager.get('plex.server_url')

        return bool(base_url and token)
    
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

    def delete_track(self, rating_key: str) -> bool:
        """Delete a track from Plex server by ratingKey."""
        from database.config_database import get_config_database
        config_db = get_config_database()
        service_id = config_db.get_or_create_service_id('plex')
        base_url = config_db.get_service_config(service_id, 'base_url') or config_db.get_service_config(service_id, 'server_url')
        token = config_db.get_service_config(service_id, 'token')

        if not base_url or not token:
            logger.error("Plex not configured, cannot delete track")
            return False

        # Construct URL
        url = f"{base_url.rstrip('/')}/library/metadata/{rating_key}"

        # Headers
        headers = {
            'X-Plex-Token': token,
            'Accept': 'application/json'
        }

        try:
            # Use self.http as mandated by ProviderBase
            response = self.http.delete(url, headers=headers)

            if response.status_code == 200:
                logger.info(f"Successfully deleted track {rating_key} from Plex")
                return True
            elif response.status_code == 403:
                logger.warning(f"Plex server does not allow file deletion (403 Forbidden) for track {rating_key}")
                return False
            elif response.status_code == 404:
                logger.warning(f"Track {rating_key} not found on Plex (404)")
                return False
            else:
                logger.error(f"Failed to delete track {rating_key}: {response.status_code} {response.reason}")
                return False
        except Exception as e:
            logger.error(f"Exception deleting track {rating_key}: {e}")
            return False

    # ===== SYNC HELPERS =====
    def _find_managed_playlist(self, desired_name: str, marker: str = "⇄", management_tag: str = "managed by SoulSync"):
        """Find a managed playlist by name using the 3-step rule:

        1) Base name matches when stripping marker
        2) Accept if summary/description contains management_tag OR name contains marker
        Returns playlist or None
        """
        if not self.ensure_connection() or not self.server:
            return None

        try:
            for playlist in self.server.playlists():
                if not playlist:
                    continue
                title = getattr(playlist, 'title', '') or ''
                summary = getattr(playlist, 'summary', '') or ''

                base_title = title.replace(marker, '').strip()
                if base_title != desired_name:
                    continue

                cond_name_has_marker = marker in title
                cond_summary_managed = management_tag.lower() in summary.lower()

                if (cond_name_has_marker and base_title == desired_name) or (cond_summary_managed and base_title == desired_name):
                    return playlist
        except Exception as e:
            logger.debug(f"Error while scanning Plex playlists for managed match: {e}")
        return None

    def add_tracks_to_managed_playlist(
        self,
        playlist_name: str,
        rating_keys: List[str],
        marker: str = "⇄",
        overwrite: bool = True,
        source_account_name: str = None,
    ) -> bool:
        """Ensure managed playlist exists and overwrite with provided ratingKeys.

        Marker defaults to U+21C4 (⇄). Playlist is considered managed if either name contains marker
        or summary includes "managed by SoulSync".
        """
        if not self.ensure_connection() or not self.server or not self.music_library:
            return False

        # --- Managed Account Routing Logic ---
        target_server = self.server
        if source_account_name:
            try:
                # Attempt to find a managed user that matches the source account name
                source_name_lower = source_account_name.lower()
                matched_user = None

                # Check MyPlex users if available (this gets home users / managed users)
                myplex_account = self.server.myPlexAccount()
                if myplex_account:
                    users = myplex_account.users()

                    # 1. Exact match (highest confidence)
                    for u in users:
                        if u.title.lower() == source_name_lower:
                            matched_user = u
                            break

                    # 2. Case-insensitive substring match: if managed_account.name.lower() in source_account_name.lower()
                    if not matched_user:
                        for u in users:
                            managed_name_lower = u.title.lower()
                            if managed_name_lower in source_name_lower:
                                matched_user = u
                                break

                if matched_user:
                    logger.info(f"Routing playlist '{playlist_name}' to managed user '{matched_user.title}'")
                    target_server = self.server.switchUser(matched_user.title)
                else:
                    logger.info(f"No managed user match found for '{source_account_name}'. Defaulting to main account.")
            except Exception as routing_err:
                logger.warning(f"Failed to route to managed account for '{source_account_name}': {routing_err}. Defaulting to main account.")

        management_tag = "managed by SoulSync"
        if source_account_name:
            management_tag = f"managed by SoulSync. Synced from {source_account_name}."
        create_name = f"{playlist_name} {marker}".strip()

        original_server = self.server

        try:
            # Update server reference for the rest of the method
            # We also need to re-find the playlist and library on the target_server
            self.server = target_server
            playlist = self._find_managed_playlist(playlist_name, marker=marker, management_tag=management_tag)

            items = []
            # Deduplicate rating keys while preserving order to avoid redundant fetches
            seen_rks = set()
            deduped_rating_keys = []
            for rk in rating_keys:
                if not rk:
                    continue
                if rk in seen_rks:
                    continue
                seen_rks.add(rk)
                deduped_rating_keys.append(rk)

            for rk in deduped_rating_keys:
                try:
                    # Ensure ratingKey is an integer
                    try:
                        rk_int = int(rk) if rk else None
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid ratingKey format: {rk}")
                        continue
                    
                    if not rk_int:
                        logger.warning("Empty or invalid ratingKey")
                        continue
                    
                    item = self.server.fetchItem(rk_int)
                    logger.debug(f"fetchItem({rk_int}) returned: {type(item).__name__} - {item}")
                    if item:
                        items.append(item)
                        logger.debug(f"Added item to list, total items now: {len(items)}")
                    else:
                        logger.warning(f"fetchItem returned None or falsy value for ratingKey {rk_int}")
                except Exception as fe:
                    logger.error(f"Exception fetching item for ratingKey {rk}: {fe}", exc_info=True)
            logger.info(f"Fetched {len(items)} valid items from {len(deduped_rating_keys)} unique rating keys (requested {len(rating_keys)})")
            
            if not items:
                logger.error(f"No valid Plex items resolved for playlist sync - all {len(rating_keys)} ratingKeys failed to fetch")
                return False

            if playlist is None:
                logger.debug(f"Playlist not found, creating new one. Items list type: {type(items)}, length: {len(items)}")
                if items:
                    logger.debug(f"First item type: {type(items[0])}, value: {items[0]}")
                
                from plexapi.playlist import Playlist
                try:
                    logger.debug(f"About to call Playlist.create with {len(items)} items")
                    created_playlist = Playlist.create(self.server, create_name, items=items)
                    logger.info(f"Playlist.create() succeeded, returned: {created_playlist}")
                    try:
                        if hasattr(created_playlist, 'editSummary'):
                            created_playlist.editSummary(management_tag)
                    except Exception as tag_err:
                        logger.debug(f"Failed to add management tag: {tag_err}")
                except Exception as create_err:
                    logger.error(f"Playlist.create() failed: {create_err}", exc_info=True)
                    raise
                # Verify created playlist contents against requested rating keys
                try:
                    created_items = list(created_playlist.items()) if created_playlist else []
                    created_rks = set(str(getattr(i, 'ratingKey', '')) for i in created_items)
                    requested_rks = set(str(rk) for rk in deduped_rating_keys)
                    missing = requested_rks - created_rks
                    if missing:
                        sample_missing = list(missing)[:10]
                        logger.warning(f"Playlist created but {len(missing)} requested items are missing from Plex playlist (showing up to 10): {sample_missing}")
                    logger.info(f"Created Plex playlist '{create_name}' with {len(created_items)} tracks (requested {len(deduped_rating_keys)})")
                except Exception as verify_err:
                    logger.debug(f"Failed to verify created playlist contents: {verify_err}")
                return True

            if overwrite:
                try:
                    existing_items = list(playlist.items())
                    if existing_items:
                        playlist.removeItems(existing_items)
                except Exception as clear_err:
                    logger.debug(f"Failed to clear playlist '{playlist.title}': {clear_err}")

            playlist.addItems(items)
            logger.info(f"Updated Plex playlist '{playlist.title}' with {len(items)} tracks (overwrite={overwrite})")
            try:
                if hasattr(playlist, 'editSummary'):
                    playlist.editSummary(management_tag)
            except Exception:
                pass
            # Post-update verification: re-fetch playlist and compare rating keys
            try:
                refreshed = self.server.playlist(playlist.title)
                refreshed_items = list(refreshed.items()) if refreshed else []
                refreshed_rks = set(str(getattr(i, 'ratingKey', '')) for i in refreshed_items)
                requested_rks = set(str(rk) for rk in deduped_rating_keys)
                missing = requested_rks - refreshed_rks
                if missing:
                    sample_missing = list(missing)[:10]
                    logger.warning(f"After update, {len(missing)} requested items are missing from Plex playlist (showing up to 10): {sample_missing}")
            except Exception as verify_err:
                logger.debug(f"Failed to verify updated playlist contents: {verify_err}")
            return True
        except Exception as e:
            logger.error(f"Error syncing Plex playlist '{playlist_name}': {e}")
            return False
        finally:
            # Restore original server
            self.server = original_server

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
                # Filter for music playlists only (robustly handle None and alternate attribute names)
                if not playlist:
                    continue

                # Support both 'playlistType' and possible variants like 'playlist_type'
                playlist_type = ''
                if hasattr(playlist, 'playlistType'):
                    playlist_type = getattr(playlist, 'playlistType') or ''
                elif hasattr(playlist, 'playlist_type'):
                    playlist_type = getattr(playlist, 'playlist_type') or ''

                if str(playlist_type).lower() != 'audio':
                    continue

                playlists.append({
                    'id': str(getattr(playlist, 'ratingKey', None)),
                    'name': getattr(playlist, 'title', None),
                    'description': getattr(playlist, 'summary', None),
                    'track_count': getattr(playlist, 'leafCount', 0),
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
    
    def _extract_version_suffix(self, text: str) -> tuple[str, Optional[str]]:
        """Extract version suffix from text in parentheses or common edition suffixes.
        
        E.g., "Wake Me Up (Avicii by Avicii)" -> ("Wake Me Up", "Avicii by Avicii")
        E.g., "All the Things She Said" Music Video -> ("All the Things She Said", "Music Video")
        E.g., "True (Avicii by Avicii)" -> ("True", "Avicii by Avicii")
        """
        import re
        
        # First check for common edition suffixes (case-insensitive)
        edition_patterns = [
            r'\s+(?:Music\s+Video|Official\s+Video|Video|Live\s+Version|Acoustic\s+Version|Remix|Remaster|Extended\s+Version)\s*$',
            r'\s*\(([^)]*)\)\s*$'  # Then try parentheses
        ]
        
        for pattern in edition_patterns:
            if pattern == r'\s*\(([^)]*)\)\s*$':
                match = re.search(pattern, text)
                if match:
                    base = text[: match.start()].strip()
                    version = match.group(1).strip()
                    if base and version:
                        return base, version
            else:
                match = re.search(pattern, text)
                if match:
                    base = text[: match.start()].strip()
                    version = match.group(0).strip().lower()
                    return base, version
        
        return text, None
    
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
                logger.debug(f"Failed to get artist via plex_track.artist() for '{title}': {e}")
            
            # Fallback to grandparentTitle attribute if artist() method failed
            if not artist:
                artist = getattr(plex_track, 'grandparentTitle', None)
                if artist:
                    logger.debug(f"Using grandparentTitle fallback for '{title}': artist={artist}")
                else:
                    logger.warning(f"Failed to extract artist for track '{title}' via both artist() and grandparentTitle")
            
            album = None
            try:
                album_obj = plex_track.album()
                album = getattr(album_obj, 'title', None) or ""
            except (NotFound, AttributeError, Exception) as e:
                logger.debug(f"Failed to get album for track '{title}': {e}")
                # Fallback to parentTitle (album name in Plex XML structure)
                album = getattr(plex_track, 'parentTitle', None) or ""
            
            if not title:
                logger.warning("Skipping track - missing title")
                return None
            
            if not artist:
                logger.warning(f"Skipping track '{title}' - missing artist (both artist() and grandparentTitle failed)")
                return None
            
            # Remove version suffix from title if it matches album version
            # E.g., if title is "Wake Me Up (Avicii by Avicii)" and album is "True (Avicii by Avicii)"
            # Extract "(Avicii by Avicii)" from both and remove from title if they match
            title_base, title_version = self._extract_version_suffix(title)
            album_base, album_version = self._extract_version_suffix(album)
            
            if title_version and album_version and title_version.lower() == album_version.lower():
                logger.debug(f"Removing matching version suffix '{title_version}' from title '{title}'")
                title = title_base
            elif album and title.lower().endswith(f"({album.lower()})"):
                # Fallback to original logic for exact album name matches
                logger.debug(f"Removing album name '{album}' from title '{title}'")
                title = title[: -(len(album) + 2)].strip()  # Remove " (Album Name)"

            # Extract other metadata
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
                    # Map remote path to local path
                    if file_path and self.path_mapper:
                        file_path = self.path_mapper.map_to_local(file_path)
            
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
            
            # Direct instantiation of SoulSyncTrack
            # Extract technical metadata
            sample_rate = None
            bit_depth = None
            file_size_bytes = None

            if hasattr(plex_track, 'media') and plex_track.media:
                media = plex_track.media[0]
                if hasattr(media, 'parts') and media.parts:
                    part = media.parts[0]
                    file_size_bytes = getattr(part, 'size', None)

                    if hasattr(part, 'streams') and part.streams:
                        for stream in part.streams:
                            # streamType 2 is typically audio
                            if getattr(stream, 'streamType', None) == 2 or getattr(stream, 'codec', None):
                                sample_rate = getattr(stream, 'samplingRate', None)
                                bit_depth = getattr(stream, 'bitDepth', None)
                                break

            # Timestamps
            added_at = None
            if hasattr(plex_track, 'addedAt') and plex_track.addedAt:
                try:
                    # Plex uses seconds for addedAt
                    added_at = datetime.fromtimestamp(int(plex_track.addedAt), tz=timezone.utc)
                except (ValueError, TypeError):
                    pass
            if not added_at:
                added_at = datetime.now(timezone.utc)

            identifiers = []
            if plex_track_id:
                identifiers.append({
                    'provider_source': 'plex',
                    'provider_item_id': plex_track_id,
                    'raw_data': None # Avoid storing heavy object
                })

            track = SoulSyncTrack(
                raw_title=title,
                artist_name=artist,
                album_title=album,
                # Optional fields
                sort_title=getattr(plex_track, 'titleSort', None),
                artist_sort_name=getattr(plex_track, 'grandparentSortTitle', None),
                album_sort_title=getattr(plex_track, 'parentSortTitle', None),
                duration=duration_ms,
                track_number=track_number,
                disc_number=disc_number,
                bitrate=bitrate,
                file_path=file_path,
                file_format=file_format,
                release_year=year,
                added_at=added_at,
                sample_rate=sample_rate,
                bit_depth=bit_depth,
                file_size_bytes=file_size_bytes,
                identifiers=identifiers
            )
            
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
        if not self.account_id:
            logger.warning("No Plex account_id provided to setup connection")
            return

        from core.storage import get_storage_service
        from core.security import decrypt_string
        storage = get_storage_service()

        # Load tokens from account_tokens securely
        token_data = storage.get_account_token(self.account_id)
        if not token_data or not token_data.get('access_token'):
            logger.error(f"Plex token not configured for account {self.account_id}")
            return
        token = decrypt_string(token_data.get('access_token'))

        from core.settings import config_manager

        # Fetch Settings from JSON (Hybrid Config approach)
        plex_config = config_manager.get('plex', {})

        base_url = plex_config.get('base_url') or plex_config.get('server_url')
        if not base_url:
            # Fallback to explicit dot-notation just in case
            base_url = config_manager.get('plex.base_url') or config_manager.get('plex.server_url')

        if not base_url:
            logger.warning("Plex server URL not configured")
            return

        # Initialize PathMapper from config.json
        import json
        mappings_raw = plex_config.get('path_mappings')
        if not mappings_raw:
            mappings_raw = config_manager.get('plex.path_mappings')

        mappings = []
        if mappings_raw:
            try:
                mappings = json.loads(mappings_raw) if isinstance(mappings_raw, str) else mappings_raw
            except Exception:
                mappings = []

        self.path_mapper = PathMapper(mappings)
        
        try:
            # 15 second timeout to prevent hangs on slow servers
            self.server = PlexServer(base_url, token, timeout=15)
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
