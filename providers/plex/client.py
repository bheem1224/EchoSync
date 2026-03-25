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
from core.user_history import UserTrackInteraction

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
                    token_backed_account = next(
                        (
                            account for account in accounts
                            if account.get('id') and storage.get_account_token(account.get('id'))
                        ),
                        None,
                    )
                    account_id = (token_backed_account or accounts[0]).get('id')
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
        
        DEPRECATED: Use add_tracks_to_playlist(playlist_id, provider_track_ids) instead.
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

    def add_tracks_to_playlist(self, playlist_id: str, provider_track_ids: List[str]) -> bool:
        """Add tracks to a Plex playlist using ratingKeys (provider-specific track IDs).
        
        NEW INTERFACE: Accepts only track IDs (ratingKeys), not full track objects.
        This is provider-agnostic and more efficient than passing full objects.
        
        Args:
            playlist_id: Plex playlist ID or name
            provider_track_ids: List of Plex ratingKeys as strings (e.g., ['123', '456'])
            
        Returns:
            True if successful, False otherwise
        """
        if not self.ensure_connection() or not self.server:
            logger.error("Plex not connected for add_tracks_to_playlist")
            return False
        
        try:
            # Find the playlist by ID or name
            try:
                # Try as ratingKey first (numeric ID)
                try:
                    playlist_id_int = int(playlist_id)
                    playlist = self.server.fetchItem(playlist_id_int)
                except (ValueError, TypeError):
                    # Try as name
                    playlist = self.server.playlist(playlist_id)
            except Exception as e:
                logger.error(f"Failed to find Plex playlist '{playlist_id}': {e}")
                return False
            
            if not playlist:
                logger.error(f"Playlist '{playlist_id}' not found on Plex server")
                return False
            
            # Convert string ratingKeys to actual track objects
            items = []
            for rk in provider_track_ids:
                try:
                    rk_int = int(rk)
                    item = self.server.fetchItem(rk_int)
                    if item:
                        items.append(item)
                    else:
                        logger.warning(f"Track with ratingKey {rk} not found on Plex server")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid ratingKey format: {rk}")
                except Exception as e:
                    logger.warning(f"Error fetching track {rk}: {e}")
            
            if not items:
                logger.error(f"No valid Plex items found for ratingKeys: {provider_track_ids}")
                return False
            
            # Add items to playlist
            try:
                playlist.addItems(items)
                logger.info(f"Successfully added {len(items)} tracks to Plex playlist '{playlist_id}'")
                return True
            except Exception as e:
                logger.error(f"Error adding items to Plex playlist '{playlist_id}': {e}")
                return False
        
        except Exception as e:
            logger.error(f"Error in add_tracks_to_playlist for '{playlist_id}': {e}", exc_info=True)
            return False

    def remove_tracks_from_playlist(self, playlist_id: str, provider_track_ids: List[str]) -> bool:
        """Remove tracks from a Plex playlist using ratingKeys."""
        if not self.ensure_connection() or not self.server:
            logger.error("Plex not connected for remove_tracks_from_playlist")
            return False

        if not provider_track_ids:
            logger.info("remove_tracks_from_playlist called with empty track list; nothing to do")
            return True

        try:
            try:
                try:
                    playlist = self.server.fetchItem(int(playlist_id))
                except (ValueError, TypeError):
                    playlist = self.server.playlist(playlist_id)
            except Exception as e:
                logger.error(f"Failed to find Plex playlist '{playlist_id}': {e}")
                return False

            if not playlist:
                logger.error(f"Playlist '{playlist_id}' not found on Plex server")
                return False

            removal_keys = {str(rk) for rk in provider_track_ids}
            existing_items = list(playlist.items())
            to_remove = [item for item in existing_items if str(getattr(item, 'ratingKey', '')) in removal_keys]

            if not to_remove:
                logger.info(f"No matching tracks found to remove from Plex playlist '{playlist_id}'")
                return True

            playlist.removeItems(to_remove)
            logger.info(f"Removed {len(to_remove)} track(s) from Plex playlist '{playlist_id}'")
            return True
        except Exception as e:
            logger.error(f"Error removing tracks from Plex playlist '{playlist_id}': {e}", exc_info=True)
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

    @staticmethod
    def _normalize_plex_identity(value: Any) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized.casefold() if normalized else None

    def _resolve_managed_user(self, target_user_id: Optional[str] = None, source_account_name: Optional[str] = None):
        """Resolve a Plex managed user using stored IDs first, then display-name fallbacks."""
        if not self.server:
            return None

        try:
            myplex_account = self.server.myPlexAccount()
        except Exception as e:
            logger.warning(f"Failed to load MyPlex account while resolving managed user: {e}")
            return None

        normalized_target_id = self._normalize_plex_identity(target_user_id)
        normalized_source_name = self._normalize_plex_identity(source_account_name)

        admin_ids = {
            normalized
            for normalized in [
                self._normalize_plex_identity(getattr(myplex_account, 'uuid', None)),
                self._normalize_plex_identity(getattr(myplex_account, 'id', None)),
                self._normalize_plex_identity(getattr(myplex_account, 'username', None)),
                self._normalize_plex_identity(getattr(myplex_account, 'title', None)),
                self._normalize_plex_identity(getattr(myplex_account, 'email', None)),
            ]
            if normalized
        }
        if normalized_target_id and normalized_target_id in admin_ids:
            return None

        try:
            users = myplex_account.users() or []
        except Exception as e:
            logger.warning(f"Failed to enumerate managed Plex users: {e}")
            return None

        for user in users:
            identities = {
                normalized
                for normalized in [
                    self._normalize_plex_identity(getattr(user, 'id', None)),
                    self._normalize_plex_identity(getattr(user, 'uuid', None)),
                    self._normalize_plex_identity(getattr(user, 'username', None)),
                    self._normalize_plex_identity(getattr(user, 'title', None)),
                    self._normalize_plex_identity(getattr(user, 'email', None)),
                ]
                if normalized
            }
            if normalized_target_id and normalized_target_id in identities:
                return user

        if normalized_source_name:
            for user in users:
                display_candidates = [
                    normalized
                    for normalized in [
                        self._normalize_plex_identity(getattr(user, 'username', None)),
                        self._normalize_plex_identity(getattr(user, 'title', None)),
                        self._normalize_plex_identity(getattr(user, 'email', None)),
                    ]
                    if normalized
                ]
                # Check if any Plex user identity is contained within the source account name
                # e.g. 'simi' in "simi's spotify" should match managed user 'Simi'
                for candidate in display_candidates:
                    if candidate in normalized_source_name:
                        logger.info(
                            f"Resolved managed Plex user by display-name fallback for source account '{source_account_name}'"
                        )
                        return user

        return None

    def _switch_to_user_server(self, user: Any):
        """Switch Plex context to a managed user using the first working identity key."""
        if not self.server or not user:
            return None

        switch_candidates = []
        for value in [
            getattr(user, 'username', None),
            getattr(user, 'title', None),
            getattr(user, 'email', None),
        ]:
            candidate = str(value).strip() if value is not None else ''
            if candidate and candidate not in switch_candidates:
                switch_candidates.append(candidate)

        last_error = None
        for candidate in switch_candidates:
            try:
                switched = self.server.switchUser(candidate)
                if switched:
                    logger.info(f"Switched Plex context using managed-user key '{candidate}'")
                    return switched
            except Exception as e:
                last_error = e
                logger.debug(f"Plex switchUser failed for candidate '{candidate}': {e}")

        if last_error:
            raise last_error
        return None

    def add_tracks_to_managed_playlist(
        self,
        playlist_name: str,
        rating_keys: List[str],
        marker: str = "⇄",
        overwrite: bool = True,
        source_account_name: str = None,
        target_user_id: str = None,
    ) -> bool:
        """Ensure managed playlist exists and overwrite with provided ratingKeys.

        Marker defaults to U+21C4 (⇄). Playlist is considered managed if either name contains marker
        or summary includes "managed by SoulSync".
        """
        if not self.ensure_connection() or not self.server or not self.music_library:
            return False

        # --- Managed Account Routing Logic ---
        target_server = self.server
        if target_user_id or source_account_name:
            try:
                matched_user = self._resolve_managed_user(
                    target_user_id=target_user_id,
                    source_account_name=source_account_name,
                )

                if matched_user:
                    logger.info(
                        f"Routing playlist '{playlist_name}' to managed user '{matched_user.title}' using Plex user_id '{target_user_id}'"
                    )
                    switched_server = self._switch_to_user_server(matched_user)
                    if switched_server:
                        target_server = switched_server
                    else:
                        logger.info(
                            f"Managed user '{matched_user.title}' resolved but Plex returned no switched server. "
                            f"Defaulting playlist '{playlist_name}' to main account."
                        )
                else:
                    logger.info(
                        f"No managed user found for Plex user_id '{target_user_id}' and source account '{source_account_name}'. "
                        f"Defaulting playlist '{playlist_name}' to main account."
                    )
            except Exception as routing_err:
                logger.warning(
                    f"Failed to route to managed account for Plex user_id '{target_user_id}': {routing_err}. Defaulting to main account."
                )

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

    def import_managed_users(self) -> List[Dict[str, Any]]:
        """Import the Plex admin account and managed users into config.db account rows."""
        if not self.ensure_connection() or not self.server:
            logger.error("Cannot import Plex managed users without an active Plex connection")
            return []

        from core.storage import get_storage_service

        storage = get_storage_service()
        token_data = storage.get_account_token(self.account_id) if self.account_id else None

        try:
            myplex_account = self.server.myPlexAccount()
        except Exception as e:
            logger.error(f"Failed to load MyPlex account details: {e}", exc_info=True)
            return []

        imported_ids: List[int] = []

        admin_user_id = (
            getattr(myplex_account, 'uuid', None)
            or getattr(myplex_account, 'id', None)
            or getattr(myplex_account, 'username', None)
        )
        admin_account_name = (
            getattr(myplex_account, 'username', None)
            or getattr(myplex_account, 'title', None)
            or getattr(myplex_account, 'email', None)
            or 'Plex Admin'
        )
        admin_email = getattr(myplex_account, 'email', None)

        admin_account_id = storage.upsert_account(
            'plex',
            account_name=admin_account_name,
            display_name=admin_account_name,
            user_id=str(admin_user_id) if admin_user_id is not None else None,
            account_email=admin_email,
            is_active=True,
            is_authenticated=True,
            account_id=self.account_id,
        )
        if admin_account_id:
            imported_ids.append(int(admin_account_id))
            self.account_id = int(admin_account_id)

            if token_data and token_data.get('access_token'):
                storage.save_account_token(
                    account_id=self.account_id,
                    access_token=token_data.get('access_token'),
                    refresh_token=token_data.get('refresh_token'),
                    token_type=token_data.get('token_type', 'Bearer'),
                    expires_at=token_data.get('expires_at'),
                    scope=token_data.get('scope'),
                )

        users = []
        try:
            users = myplex_account.users() or []
        except Exception as e:
            logger.warning(f"Failed to enumerate Plex managed users: {e}")

        for user in users:
            user_id = getattr(user, 'id', None) or getattr(user, 'uuid', None)
            username = getattr(user, 'username', None) or getattr(user, 'title', None)
            display_name = getattr(user, 'title', None) or getattr(user, 'username', None) or username
            email = getattr(user, 'email', None)

            managed_account_id = storage.upsert_account(
                'plex',
                account_name=username or display_name,
                display_name=display_name,
                user_id=str(user_id) if user_id is not None else None,
                account_email=email,
                is_active=True,
                is_authenticated=False,
            )
            if managed_account_id:
                imported_ids.append(int(managed_account_id))

        accounts = storage.list_accounts('plex') or []
        imported = [account for account in accounts if account.get('id') in set(imported_ids)]
        logger.info(f"Imported {len(imported)} Plex account rows (admin + managed users)")
        return imported
    
    def _find_music_library(self):
        """Automatically find and set active music library."""
        if not self.server:
            return
        
        try:
            self.music_library = self._find_music_library_for_server(self.server)
            if self.music_library:
                logger.info(f"Selected music library: {self.music_library.title}")
        
        except Exception as e:
            logger.error(f"Error finding music library: {e}")

    def _find_music_library_for_server(self, server: PlexServer) -> Optional[MusicSection]:
        """Find the preferred music library for a specific Plex server context."""
        music_sections = [section for section in server.library.sections() if section.type == 'artist']

        if not music_sections:
            logger.warning("No music library found on Plex server")
            return None

        for priority_name in ['Music', 'music', 'Audio', 'audio', 'Songs', 'songs']:
            for section in music_sections:
                if section.title == priority_name:
                    return section

        return music_sections[0]

    def _resolve_history_context(self, account_id: Optional[int]):
        """Resolve Plex server and library for an account-specific history query."""
        if not self.ensure_connection() or not self.server:
            return None, None

        target_server = self.server
        target_library = self.music_library

        if account_id is None:
            return target_server, target_library

        from core.storage import get_storage_service

        storage = get_storage_service()
        accounts = storage.list_accounts('plex') or []
        account = next((item for item in accounts if item.get('id') == account_id), None)
        if not account:
            logger.warning(f"No Plex account found for history sync account_id={account_id}")
            return target_server, target_library

        target_user_id = account.get('user_id')
        if not target_user_id:
            return target_server, target_library

        try:
            myplex_account = self.server.myPlexAccount()
            admin_ids = {
                str(value)
                for value in [
                    getattr(myplex_account, 'uuid', None),
                    getattr(myplex_account, 'id', None),
                    getattr(myplex_account, 'username', None),
                ]
                if value is not None
            }
            if str(target_user_id) in admin_ids:
                return target_server, target_library

            for user in myplex_account.users() or []:
                candidate_id = getattr(user, 'id', None) or getattr(user, 'uuid', None)
                if candidate_id is not None and str(candidate_id) == str(target_user_id):
                    target_server = self.server.switchUser(user.title)
                    target_library = self._find_music_library_for_server(target_server)
                    logger.info(
                        f"Resolved Plex history context for account_id={account_id} to managed user '{user.title}'"
                    )
                    return target_server, target_library
        except Exception as e:
            logger.warning(f"Failed to resolve Plex history context for account_id={account_id}: {e}")

        return target_server, target_library

    def _coerce_datetime(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc)
        except Exception:
            return None

    def _extract_user_rating(self, plex_item: Any) -> Optional[float]:
        """Normalize Plex user rating to the 0-10 scale used in working DB.

        Plex uses 0 for "unrated" in some payloads, so that should remain None.
        """
        raw_rating = getattr(plex_item, 'userRating', None)

        # Some payload shapes expose user state as a mapping-like object.
        if raw_rating in (None, ''):
            user_state = getattr(plex_item, 'userState', None)
            if isinstance(user_state, dict):
                raw_rating = user_state.get('rating')

        if raw_rating in (None, ''):
            return None

        try:
            parsed = float(raw_rating)
        except Exception:
            return None

        if parsed <= 0.0:
            return None
        # Plex wire format: userRating is 2× the displayed star count (0.5 stars → 1.0,
        # 5 stars → 10.0).  Divide by 2 to normalise to display stars (0.5–5.0) so
        # stars_to_ten_point() in consensus.py receives the correct input scale.
        display_stars = parsed / 2.0
        return min(5.0, display_stars)

    def _enrich_interactions_with_user_ratings(
        self,
        interactions: List[UserTrackInteraction],
        target_server: Any,
    ) -> None:
        """Backfill missing ratings by resolving metadata items in user context."""
        if not interactions or not target_server:
            return

        rating_cache: Dict[str, Optional[float]] = {}
        enriched_count = 0

        for interaction in interactions:
            if interaction.rating is not None:
                continue

            provider_item_id = str(getattr(interaction, 'provider_item_id', '') or '').strip()
            if not provider_item_id:
                continue

            if provider_item_id in rating_cache:
                cached_rating = rating_cache[provider_item_id]
                if cached_rating is not None:
                    interaction.rating = cached_rating
                    enriched_count += 1
                continue

            resolved_rating: Optional[float] = None
            try:
                try:
                    item = target_server.fetchItem(int(provider_item_id))
                except Exception:
                    item = target_server.fetchItem(f'/library/metadata/{provider_item_id}')

                if item is not None:
                    resolved_rating = self._extract_user_rating(item)
            except Exception as exc:
                logger.debug(f"Could not enrich rating for Plex item {provider_item_id}: {exc}")

            rating_cache[provider_item_id] = resolved_rating
            if resolved_rating is not None:
                interaction.rating = resolved_rating
                enriched_count += 1

        if enriched_count:
            logger.info(f"Enriched {enriched_count} Plex history interactions with user ratings")

    def _track_to_interaction(self, plex_track: Any) -> Optional[UserTrackInteraction]:
        """Convert a Plex history or library item into a standardized interaction."""
        converted = self._convert_track_to_soulsync(plex_track)
        if not converted:
            return None

        provider_item_id = str(getattr(plex_track, 'ratingKey', None) or converted.identifiers.get('plex') or '')
        play_count = int(getattr(plex_track, 'viewCount', 0) or 0)
        rating = self._extract_user_rating(plex_track)
        last_played_at = self._coerce_datetime(getattr(plex_track, 'lastViewedAt', None))

        return UserTrackInteraction(
            provider_item_id=provider_item_id,
            artist_name=converted.artist_name,
            track_title=converted.title,
            play_count=play_count,
            rating=rating,
            last_played_at=last_played_at,
        )

    def fetch_user_history(self, account_id: Optional[int] = None, limit: int = 100) -> List[UserTrackInteraction]:
        """Fetch account-specific listening history from Plex using exact managed-user context when available."""
        target_server, target_library = self._resolve_history_context(account_id)
        if not target_server or not target_library:
            logger.warning("Plex not connected or no music library for history")
            return []

        try:
            interactions: List[UserTrackInteraction] = []

            try:
                logger.debug(f"Fetching Plex play history for account_id={account_id} (limit={limit})")
                history_items = target_server.history(maxresults=limit)
                for item in history_items or []:
                    # Strictly filter for audio tracks to avoid crashing on photos/extras
                    if getattr(item, 'type', None) != 'track':
                        continue
                    interaction = self._track_to_interaction(item)
                    if interaction:
                        # Plex history rows often omit viewCount; each history row still
                        # represents at least one play event for the selected account.
                        if int(getattr(interaction, 'play_count', 0) or 0) <= 0:
                            interaction.play_count = 1
                        interactions.append(interaction)

                if interactions:
                    self._enrich_interactions_with_user_ratings(interactions, target_server)
                    logger.info(f"Fetched {len(interactions)} Plex history interactions for account_id={account_id}")
                    return interactions[:limit]
            except Exception as e:
                logger.warning(
                    f"Failed to fetch Plex history for account_id={account_id}: {e}. Falling back to lastViewedAt library query."
                )

            recent_tracks = target_library.searchTracks(maxresults=limit, sort='lastViewedAt:desc')
            for item in recent_tracks or []:
                interaction = self._track_to_interaction(item)
                if interaction:
                    interactions.append(interaction)

            self._enrich_interactions_with_user_ratings(interactions, target_server)

            logger.info(f"Fetched {len(interactions)} fallback Plex history interactions for account_id={account_id}")
            return interactions[:limit]

        except Exception as e:
            logger.error(f"Error fetching user history from Plex: {e}", exc_info=True)
            return []
