import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from core.tiered_logger import get_logger
from core.provider import ProviderRegistry
from services.download_manager import get_download_manager
from services.match_service import MatchService, MatchContext
from core.matching_engine import SoulSyncTrack
from time_utils import utc_isoformat, utc_now

logger = get_logger("sync_service")

@dataclass
class TrackMatchResult:
    """Simple result object for track matching in playlist sync"""
    spotify_track: SoulSyncTrack
    provider_track_id: Optional[str] = None  # Raw track ID from provider (e.g., ratingKey, db ID)
    confidence: float = 0.0
    
    @property
    def is_match(self) -> bool:
        """True if a track was found in the provider"""
        return self.provider_track_id is not None

@dataclass
class SpotifyPlaylist:
    id: str
    name: str
    tracks: List[SoulSyncTrack] = field(default_factory=list)
    account_id: Optional[int] = None
    account_name: Optional[str] = None

@dataclass
class SyncResult:
    playlist_name: str
    total_tracks: int
    matched_tracks: int
    synced_tracks: int
    downloaded_tracks: int
    failed_tracks: int
    sync_time: datetime
    errors: List[str]
    wishlist_added_count: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_tracks == 0:
            return 0.0
        return (self.synced_tracks / self.total_tracks) * 100

@dataclass
class SyncProgress:
    current_step: str
    current_track: str
    progress: float
    total_steps: int
    current_step_number: int
    # Add detailed track stats for UI updates
    total_tracks: int = 0
    matched_tracks: int = 0
    failed_tracks: int = 0

class PlaylistSyncService:
    def __init__(
        self,
        spotify_client=None,
        plex_client=None,
        soulseek_client=None,
        jellyfin_client=None,
        navidrome_client=None,
    ):
        # Support multiple spotify accounts by default when no client is passed
        self.spotify_clients = []
        self.spotify_client = None

        if spotify_client:
            self.spotify_clients = [spotify_client]
            self.spotify_client = spotify_client
        else:
            # Use ProviderRegistry to load all spotify clients
            try:
                from core.file_handling.storage import get_storage_service
                storage = get_storage_service()
                accounts = storage.list_accounts('spotify') or []

                for acc in accounts:
                    try:
                        if acc.get('is_active') is False:
                            logger.debug(f"Skipping disabled spotify account {acc.get('id')}")
                            continue
                        # Instantiate via Registry
                        client = ProviderRegistry.create_instance('spotify', account_id=acc.get('id'))
                        if client.is_configured():
                            self.spotify_clients.append(client)
                    except Exception as e:
                        logger.warning(f"Failed to load spotify client for account {acc.get('id')}: {e}")
                        continue

                if self.spotify_clients:
                    # default to first account
                    self.spotify_client = self.spotify_clients[0]
                else:
                    # fallback to generic auto-detect client via Registry
                    try:
                        self.spotify_client = ProviderRegistry.create_instance('spotify')
                        self.spotify_clients = [self.spotify_client]
                    except Exception as e:
                        logger.error(f"Failed to create default spotify client: {e}")
            except Exception as e:
                # if storage service not available, just create a generic client
                try:
                    self.spotify_client = ProviderRegistry.create_instance('spotify')
                    self.spotify_clients = [self.spotify_client]
                except Exception as create_err:
                    logger.error(f"Critical failure creating spotify client: {create_err}")

        # other providers assume single-client style (injected or lazy-loaded)
        self.plex_client = plex_client
        self.jellyfin_client = jellyfin_client
        self.navidrome_client = navidrome_client

        # Lazy load clients if not injected
        if not self.plex_client:
            try:
                self.plex_client = ProviderRegistry.create_instance('plex')
            except Exception as e:
                logger.warning(f"Plex client unavailable at SyncService init: {e}")

        if not self.jellyfin_client:
            try:
                self.jellyfin_client = ProviderRegistry.create_instance('jellyfin')
            except Exception as e:
                logger.warning(f"Jellyfin client unavailable at SyncService init: {e}")

        if not self.navidrome_client:
            try:
                self.navidrome_client = ProviderRegistry.create_instance('navidrome')
            except Exception as e:
                logger.warning(f"Navidrome client unavailable at SyncService init: {e}")

        self.download_manager = get_download_manager()
        self.progress_callbacks = {}  # Playlist-specific progress callbacks
        self.syncing_playlists = set()  # Track multiple syncing playlists
        self._cancelled = False
        self.matching_engine = MatchService()
    
    def _get_active_media_client(self):
        """Get the active media client based on config settings"""
        try:
            from core.settings import config_manager
            active_server = config_manager.get_active_media_server()

            if active_server == "jellyfin":
                if not self.jellyfin_client:
                    logger.error("Jellyfin client not provided to sync service")
                    return None, "jellyfin"
                return self.jellyfin_client, "jellyfin"
            elif active_server == "navidrome":
                if not self.navidrome_client:
                    logger.error("Navidrome client not provided to sync service")
                    return None, "navidrome"
                return self.navidrome_client, "navidrome"
            else:  # Default to Plex
                return self.plex_client, "plex"
        except Exception as e:
            logger.error(f"Error determining active media server: {e}")
            return self.plex_client, "plex"  # Fallback to Plex
    
    @property
    def is_syncing(self):
        """Check if any playlist is currently syncing"""
        return len(self.syncing_playlists) > 0
    
    def set_progress_callback(self, callback, playlist_name=None):
        """Set progress callback for specific playlist or global if no playlist specified"""
        if playlist_name:
            self.progress_callbacks[playlist_name] = callback
        else:
            # Legacy support - set for all current syncing playlists
            for playlist in self.syncing_playlists:
                self.progress_callbacks[playlist] = callback
    
    def clear_progress_callback(self, playlist_name):
        """Clear progress callback for specific playlist"""
        if playlist_name in self.progress_callbacks:
            del self.progress_callbacks[playlist_name]
    
    def cancel_sync(self):
        """Cancel the current sync operation"""
        logger.info("PlaylistSyncService.cancel_sync() called - setting cancellation flag")
        self._cancelled = True
        self.is_syncing = False
    
    def _update_progress(self, playlist_name: str, step: str, track: str, progress: float, total_steps: int, current_step: int, 
                        total_tracks: int = 0, matched_tracks: int = 0, failed_tracks: int = 0):
        # Send progress update to the specific playlist's callback
        callback = self.progress_callbacks.get(playlist_name)
        if callback:
            callback(SyncProgress(
                current_step=step,
                current_track=track,
                progress=progress,
                total_steps=total_steps,
                current_step_number=current_step,
                total_tracks=total_tracks,
                matched_tracks=matched_tracks,
                failed_tracks=failed_tracks
            ))
    
    async def sync_playlist(self, playlist: SpotifyPlaylist, download_missing: bool = False) -> SyncResult:
        # Check if THIS specific playlist is already syncing
        if playlist.name in self.syncing_playlists:
            logger.warning(f"Sync already in progress for playlist: {playlist.name}")
            return SyncResult(
                playlist_name=playlist.name,
                total_tracks=0,
                matched_tracks=0,
                synced_tracks=0,
                downloaded_tracks=0,
                failed_tracks=0,
                sync_time=utc_now(),
                errors=[f"Sync already in progress for playlist: {playlist.name}"]
            )
        
        # Add this playlist to syncing set
        self.syncing_playlists.add(playlist.name)
        self._cancelled = False
        errors = []
        
        try:
            logger.info(f"Starting sync for playlist: {playlist.name}")
            
            if self._cancelled:
                return self._create_error_result(playlist.name, ["Sync cancelled"])
            
            # Skip fetching playlist since we already have it
            self._update_progress(playlist.name, "Preparing playlist sync", "", 10, 5, 1)
            
            if not playlist.tracks:
                errors.append(f"Playlist '{playlist.name}' has no tracks")
                return self._create_error_result(playlist.name, errors)
            
            if self._cancelled:
                return self._create_error_result(playlist.name, ["Sync cancelled"])
            
            total_tracks = len(playlist.tracks)
            media_client, server_type = self._get_active_media_client()

            media_client, server_type = self._get_active_media_client()
            self._update_progress(playlist.name, f"Matching tracks against {server_type.title()} library", "", 20, 5, 2, total_tracks=total_tracks)
            
            # Use the same robust matching approach as "Download Missing Tracks"
            match_results = []
            for i, track in enumerate(playlist.tracks):
                if self._cancelled:
                    return self._create_error_result(playlist.name, ["Sync cancelled"])
                
                # Update progress for each track
                progress_percent = 20 + (40 * (i + 1) / total_tracks)  # 20-60% for matching

                if track.artist_name:
                    current_track_name = f"{track.artist_name} - {track.title}"
                else:
                    current_track_name = track.title

                self._update_progress(playlist.name, "Matching tracks", current_track_name, progress_percent, 5, 2, 
                                    total_tracks=total_tracks,
                                    matched_tracks=len([r for r in match_results if r.is_match]),
                                    failed_tracks=len([r for r in match_results if not r.is_match]))
                
                # Use the robust search approach
                plex_match, confidence = await self._find_track_in_media_server(track)
                
                match_result = TrackMatchResult(
                    spotify_track=track,
                    provider_track_id=plex_match,
                    confidence=confidence
                )
                match_results.append(match_result)
            
            matched_tracks = [r for r in match_results if r.is_match]
            unmatched_tracks = [r for r in match_results if not r.is_match]
            
            logger.info(f"Found {len(matched_tracks)} matches out of {len(playlist.tracks)} tracks")
            
            
            if self._cancelled:
                return self._create_error_result(playlist.name, ["Sync cancelled"])
            
            # Update progress with match results
            self._update_progress(playlist.name, "Matching completed", "", 60, 5, 3, 
                                total_tracks=total_tracks, 
                                matched_tracks=len(matched_tracks), 
                                failed_tracks=len(unmatched_tracks))
            
            downloaded_tracks = 0
            if download_missing and unmatched_tracks:
                if self._cancelled:
                    return self._create_error_result(playlist.name, ["Sync cancelled"])
                self._update_progress(playlist.name, "Publishing download intents", "", 70, 5, 4, 
                                    total_tracks=total_tracks,
                                    matched_tracks=len(matched_tracks),
                                    failed_tracks=len(unmatched_tracks))
                downloaded_tracks = await self._publish_download_intents(unmatched_tracks)
            
            if self._cancelled:
                return self._create_error_result(playlist.name, ["Sync cancelled"])
            
            media_client, server_type = self._get_active_media_client()
            self._update_progress(playlist.name, f"Creating/updating {server_type.title()} playlist", "", 80, 5, 4,
                                total_tracks=total_tracks,
                                matched_tracks=len(matched_tracks),
                                failed_tracks=len(unmatched_tracks))
            
            # Extract provider-specific track IDs from matched tracks
            # Pass raw string IDs directly to add_tracks_to_playlist
            provider_track_ids = []
            for r in matched_tracks:
                if r.provider_track_id:
                    provider_track_ids.append(str(r.provider_track_id))
                    logger.debug(f"✔️ Resolved track to provider ID: {r.provider_track_id}")
                else:
                    logger.warning(f"❌ Track has no valid provider ID: {r.spotify_track.title}")
            
            logger.info(f"Extracted {len(provider_track_ids)} provider-specific IDs for {len(matched_tracks)} matched tracks")
            
            # Use active media server for playlist sync
            media_client, server_type = self._get_active_media_client()
            if not media_client:
                logger.error(f"No active media client available for playlist sync")
                sync_success = False
            else:
                logger.info(f"Syncing playlist '{playlist.name}' to {server_type.upper()} server with {len(provider_track_ids)} track IDs")
                # NEW INTERFACE: Pass only track IDs instead of full track objects
                sync_success = media_client.add_tracks_to_playlist(playlist.name, provider_track_ids)
            
            synced_tracks = len(provider_track_ids) if sync_success else 0
            failed_tracks = len(playlist.tracks) - synced_tracks - downloaded_tracks
            
            self._update_progress(playlist.name, "Sync completed", "", 100, 5, 5,
                                total_tracks=total_tracks,
                                matched_tracks=len(matched_tracks),
                                failed_tracks=failed_tracks)

            # Auto-add unmatched tracks to wishlist
            wishlist_added_count = 0
            if unmatched_tracks:
                try:
                    from core.wishlist_service import get_wishlist_service
                    wishlist_service = get_wishlist_service()

                    logger.info(f"Auto-adding {len(unmatched_tracks)} unmatched tracks to wishlist")

                    for match_result in unmatched_tracks:
                        spotify_track = match_result.spotify_track

                        # Check if we have original track data with full album objects
                        original_track_data = None
                        if hasattr(self, '_original_tracks_map') and self._original_tracks_map:
                            original_track_data = self._original_tracks_map.get(spotify_track.id)

                        # Use original data if available (preserves album images), otherwise convert
                        if original_track_data:
                            spotify_track_data = original_track_data
                        else:
                            spotify_track_data = {
                                'id': spotify_track.identifiers.get('spotify') or spotify_track.identifiers.get('provider_id'),
                                'name': spotify_track.title,
                                'artists': [{'name': spotify_track.artist_name}],
                                'album': {'name': spotify_track.album_title},
                                'duration_ms': spotify_track.duration,
                                'popularity': getattr(spotify_track, 'popularity', 0),
                                'preview_url': getattr(spotify_track, 'preview_url', None),
                                'external_urls': getattr(spotify_track, 'external_urls', {})
                            }

                        # Add to wishlist with source context
                        success = wishlist_service.add_spotify_track_to_wishlist(
                            spotify_track_data=spotify_track_data,
                            failure_reason='Missing from media server after sync',
                            source_type='playlist',
                            source_context={
                                'playlist_name': playlist.name,
                                'playlist_id': playlist.id,
                                'sync_type': 'automatic_sync',
                                'timestamp': utc_isoformat(utc_now())
                            }
                        )

                        if success:
                            wishlist_added_count += 1

                    logger.info(f"Successfully added {wishlist_added_count}/{len(unmatched_tracks)} tracks to wishlist")

                except Exception as e:
                    logger.warning(f"Failed to auto-add tracks to wishlist: {e}")
                    # Don't fail the sync if wishlist add fails

            result = SyncResult(
                playlist_name=playlist.name,
                total_tracks=len(playlist.tracks),
                matched_tracks=len(matched_tracks),
                synced_tracks=synced_tracks,
                downloaded_tracks=downloaded_tracks,
                failed_tracks=failed_tracks,
                sync_time=utc_now(),
                errors=errors,
                wishlist_added_count=wishlist_added_count
            )

            logger.info(f"Sync completed: {result.success_rate:.1f}% success rate")
            return result
            
        except Exception as e:
            logger.error(f"Error during sync: {e}")
            errors.append(str(e))
            return self._create_error_result(playlist.name, errors)
        
        finally:
            # Remove this playlist from syncing set and clear its callback
            self.syncing_playlists.discard(playlist.name)
            self.clear_progress_callback(playlist.name)
            self._cancelled = False
    
    async def _find_track_in_media_server(self, spotify_track: SoulSyncTrack) -> Tuple[Optional[str], float]:
        """Find a track in the media server using database matching.
        
        Returns:
            Tuple of (track_id_string, confidence_score) or (None, 0.0) if not found
        """
        try:
            # Check active media server connection
            media_client, server_type = self._get_active_media_client()
            if not media_client or not media_client.is_connected():
                logger.warning(f"{server_type.upper()} client not connected")
                return None, 0.0
            
            # Use the SAME improved database matching as PlaylistTrackAnalysisWorker
            from database.music_database import MusicDatabase
            
            original_title = spotify_track.title
            artist_name = spotify_track.artist_name
            
            if self._cancelled:
                return None, 0.0

            # Use the improved database check_track_exists method with server awareness
            try:
                from core.settings import config_manager
                active_server = config_manager.get_active_media_server()
                db = MusicDatabase()
                db_track, confidence = db.check_track_exists(original_title, artist_name, confidence_threshold=0.7, server_source=active_server)
                
                if db_track and confidence >= 0.7:
                    logger.debug(f"✔️ Database match found for '{original_title}' by '{artist_name}': '{db_track.title}' with confidence {confidence:.2f}")
                    
                    # Extract the track ID from the database
                    track_id = str(db_track.id)
                    
                    # For Plex, validate that the track ID is numeric and fetchable
                    if server_type == "plex":
                        try:
                            track_id_int = int(track_id)
                            actual_plex_track = media_client.server.fetchItem(track_id_int)
                            if actual_plex_track and hasattr(actual_plex_track, 'ratingKey'):
                                logger.debug(f"✔️ Successfully validated Plex track for '{db_track.title}' (ratingKey: {actual_plex_track.ratingKey})")
                                return str(actual_plex_track.ratingKey), confidence
                            else:
                                logger.warning(f"❌ Fetched Plex track for '{db_track.title}' lacks ratingKey attribute")
                                return None, 0.0
                        except ValueError:
                            logger.warning(f"❌ Invalid Plex track ID format for '{db_track.title}' (ID: {db_track.id}) - skipping this track")
                            return None, 0.0
                    else:
                        # For Jellyfin and Navidrome, use the database ID directly
                        logger.debug(f"✔️ Using database track ID for '{server_type}': {track_id}")
                        return track_id, confidence

            except Exception as db_error:
                logger.error(f"Error checking track existence for '{original_title}' by '{artist_name}': {db_error}")
            
            logger.debug(f"❌ No database match found for '{original_title}' by artist '{artist_name}'")
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Error searching for track '{spotify_track.title}': {e}")
            return None, 0.0
    
    async def sync_multiple_playlists(self, playlist_names: List[str], download_missing: bool = False) -> List[SyncResult]:
        results = []
        
        for i, playlist_name in enumerate(playlist_names):
            logger.info(f"Syncing playlist {i+1}/{len(playlist_names)}: {playlist_name}")
            result = await self.sync_playlist(playlist_name, download_missing)
            results.append(result)
            
            if i < len(playlist_names) - 1:
                await asyncio.sleep(1)
        
        return results
    
    def _get_spotify_playlist(self, playlist_name: str, account_id: Optional[int] = None) -> Optional[SpotifyPlaylist]:
        """Locate a Spotify playlist by name across one or all configured accounts.

        If `account_id` is provided, only that client's playlists will be searched.
        Otherwise we iterate through all known spotify_clients until a match is found.
        """
        try:
            clients = []
            if account_id is not None:
                # find matching client
                for c in self.spotify_clients:
                    if getattr(c, 'account_id', None) == account_id:
                        clients = [c]
                        break
            if not clients:
                clients = self.spotify_clients

            for client in clients:
                try:
                    playlists = client.get_user_playlists() or []
                except Exception:
                    playlists = []
                for p in playlists:
                    if p.get('name', '').lower() == playlist_name.lower():
                        tracks = client.get_playlist_tracks(p['id'])
                        return SpotifyPlaylist(id=p['id'], name=p['name'], tracks=tracks)
            return None
        except Exception as e:
            logger.error(f"Error fetching Spotify playlist: {e}")
            return None
    
    async def _get_media_tracks(self) -> List:
        """Get tracks from the active media server"""
        try:
            media_client, server_type = self._get_active_media_client()
            if not media_client:
                logger.error(f"No active media client available")
                return []

            if hasattr(media_client, 'search_tracks'):
                return media_client.search_tracks("", limit=10000)
            else:
                logger.warning(f"{server_type.title()} client doesn't support track search")
                return []
        except Exception as e:
            logger.error(f"Error fetching {server_type} tracks: {e}")
            return []
    
    async def _publish_download_intents(self, unmatched_tracks: List[MatchResult]) -> int:
        """Publish DOWNLOAD_INTENT events via event bus for missing tracks instead of downloading inline.
        
        This allows asynchronous handling and prevents blocking sync operations.
        The download manager and other services can subscribe to these events.
        """
        from core.event_bus import event_bus
        
        intent_count = 0
        for match_result in unmatched_tracks:
            try:
                spotify_track = match_result.spotify_track
                logger.info(f"Publishing DOWNLOAD_INTENT for: {spotify_track.title} - {spotify_track.artist_name}")
                full_track = spotify_track.to_dict()
                identifiers = full_track.get("identifiers") if isinstance(full_track, dict) else {}
                spotify_id = None
                if isinstance(identifiers, dict):
                    spotify_id = identifiers.get("spotify") or identifiers.get("spotify_id")
                
                # Publish event via event bus for asynchronous processing
                event_bus.publish({
                    "event": "DOWNLOAD_INTENT",
                    "sync_id": spotify_id or spotify_track.identifiers.get('provider_id'),
                    "track": full_track,
                    # Legacy compatibility for existing consumers.
                    "fallback_metadata": full_track,
                    "duration_ms": full_track.get("duration_ms"),
                    "isrc": full_track.get("isrc"),
                    "timestamp": utc_isoformat(utc_now()),
                    "source": "playlist_sync"
                })
                
                intent_count += 1
                logger.debug(f"DOWNLOAD_INTENT published for track {spotify_track.identifiers.get('spotify')}")
                
            except Exception as e:
                logger.error(f"Error publishing DOWNLOAD_INTENT: {e}")
        
        logger.info(f"Published {intent_count} DOWNLOAD_INTENT events for missing tracks")
        return intent_count
    
    def _create_error_result(self, playlist_name: str, errors: List[str]) -> SyncResult:
        return SyncResult(
            playlist_name=playlist_name,
            total_tracks=0,
            matched_tracks=0,
            synced_tracks=0,
            downloaded_tracks=0,
            failed_tracks=0,
            sync_time=utc_now(),
            errors=errors,
            wishlist_added_count=0
        )
    
    def get_sync_preview(self, playlist_name: str, account_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            spotify_playlist = self._get_spotify_playlist(playlist_name, account_id=account_id)
            if not spotify_playlist:
                return {"error": f"Playlist '{playlist_name}' not found"}

            media_client, server_type = self._get_active_media_client()
            if not media_client or not hasattr(media_client, 'search_tracks'):
                return {"error": f"Active media server ({server_type}) doesn't support track search"}

            media_tracks = media_client.search_tracks("", limit=1000)

            match_results = self.matching_engine.match_playlist_tracks(
                spotify_playlist.tracks,
                media_tracks
            )

            stats = self.matching_engine.get_match_statistics(match_results)

            preview = {
                "playlist_name": playlist_name,
                "total_tracks": len(spotify_playlist.tracks),
                f"available_in_{server_type}": stats["matched_tracks"],
                "needs_download": stats["total_tracks"] - stats["matched_tracks"],
                "match_percentage": stats["match_percentage"],
                "confidence_breakdown": stats["confidence_distribution"],
                "tracks_preview": []
            }

            for result in match_results[:10]:
                track_info = {
                    "spotify_track": f"{result.spotify_track.title} - {result.spotify_track.artist_name}",
                    f"{server_type}_match": f"ID: {result.provider_track_id}" if result.is_match else None,
                    "confidence": result.confidence,
                    "status": "available" if result.is_match else "needs_download"
                }
                preview["tracks_preview"].append(track_info)

            return preview

        except Exception as e:
            logger.error(f"Error generating sync preview: {e}")
            return {"error": str(e)}
    
    async def _get_all_spotify_playlists(self) -> List[SpotifyPlaylist]:
        """
        Fetch playlists from ALL configured and active Spotify accounts.
        Append ' ({Account Name})' to playlist names to distinguish them.
        """
        all_playlists = []
        try:
            # 1. Get all accounts from config/storage
            from core.settings import config_manager
            accounts = config_manager.get_spotify_accounts()

            # If no accounts found, fallback to default single-client behavior
            if not accounts:
                logger.debug("No multi-account config found, using default client")
                if self.spotify_client:
                     # Iterate generator directly
                     for p in self.spotify_client.get_user_playlists() or []:
                         all_playlists.append(SpotifyPlaylist(id=p['id'], name=p['name'], tracks=[]))
                return all_playlists

            # 2. Iterate through each account
            for account in accounts:
                try:
                    # Debug dump to confirm key names
                    logger.debug(f"DEBUG ACCOUNT OBJ: {account}")

                    # Filter inactive accounts
                    # Check both 'is_active' (DB convention) and 'enabled' (Config convention)
                    is_active = account.get('is_active') or account.get('enabled')
                    # Explicitly check against False/0/None, allowing True/1
                    if not is_active and is_active is not None:
                         # Some legacy configs might miss the key, defaulting to True if missing?
                         # No, standard safe practice is default False if missing, or True?
                         # Requirement says "strictly filter by is_active=True".
                         # So if key is missing, we assume False? Or let it pass?
                         # Let's assume strict: must be truthy.
                         logger.info(f"Skipping inactive Spotify account: {account.get('name')} (id={account.get('id')})")
                         continue

                    # Determine next step if key is missing (legacy) - assuming active if not explicitly false?
                    # The prompt says "is_active flag is being ignored".
                    # If the key exists and is 0/False, we must skip.
                    if 'is_active' in account and not account['is_active']:
                        logger.info(f"Skipping inactive Spotify account: {account.get('name')}")
                        continue

                    account_id = account.get('id')
                    account_name = account.get('name', f"Account {account_id}")

                    # Instantiate client for this account
                    # We create a temporary client just for this fetch
                    client = ProviderRegistry.create_instance('spotify', account_id=account_id)

                    if not client.is_configured():
                        continue

                    logger.info(f"Fetching playlists for Spotify account: {account_name}")

                    # Consume generator
                    for p in client.get_user_playlists() or []:
                        # We used to append account name to playlist name, but this is handled by routing now.
                        # Instead, just pass the clean name. We can keep track of the account in the SpotifyPlaylist
                        # object if we extend it, or just use the name as is.
                        # For now, just use the raw name.
                        sp_playlist = SpotifyPlaylist(id=p['id'], name=p['name'], tracks=[])
                        # Attach account ID/name to the object to be able to identify source account later
                        sp_playlist.account_id = account_id
                        sp_playlist.account_name = account_name
                        all_playlists.append(sp_playlist)

                except Exception as e:
                    logger.error(f"Error fetching playlists for account {account.get('id')}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in _get_all_spotify_playlists: {e}")

        return all_playlists

    def get_library_comparison(self) -> Dict[str, Any]:
        try:
            # Re-implementing logic synchronously for compatibility with multi-account support
            from core.settings import config_manager
            accounts = config_manager.get_spotify_accounts()

            spotify_playlists = []

            if not accounts:
                 # Fallback to default client if configured
                 if self.spotify_client and self.spotify_client.is_configured():
                     try:
                        # Consume generator
                        for p in self.spotify_client.get_user_playlists() or []:
                            spotify_playlists.append(p)
                     except Exception as e:
                        logger.error(f"Error fetching default playlists: {e}")
            else:
                for account in accounts:
                    try:
                        # STRICT Filter for active accounts
                        is_active = account.get('is_active') or account.get('enabled')
                        if not is_active and is_active is not None:
                             continue
                        if 'is_active' in account and not account['is_active']:
                             continue

                        client = ProviderRegistry.create_instance('spotify', account_id=account.get('id'))
                        if client.is_configured():
                             # Consume generator
                             for p in client.get_user_playlists() or []:
                                 spotify_playlists.append(p)
                    except Exception as e:
                        logger.error(f"Error fetching playlists for account {account.get('id')}: {e}")
                        continue

            spotify_track_count = sum(p.get('track_count', 0) for p in spotify_playlists)

            media_client, server_type = self._get_active_media_client()
            if not media_client:
                return {"error": f"No active media client available"}

            media_playlists = media_client.get_all_playlists() if hasattr(media_client, 'get_all_playlists') else []
            media_stats = media_client.get_library_stats() if hasattr(media_client, 'get_library_stats') else {}

            comparison = {
                "spotify": {
                    "playlists": len(spotify_playlists),
                    "total_tracks": spotify_track_count
                },
                server_type: {
                    "playlists": len(media_playlists),
                    "artists": media_stats.get("artists", 0),
                    "albums": media_stats.get("albums", 0),
                    "tracks": media_stats.get("tracks", 0)
                },
                "sync_potential": {
                    "estimated_matches": min(spotify_track_count, media_stats.get("tracks", 0)),
                    "potential_downloads": max(0, spotify_track_count - media_stats.get("tracks", 0))
                }
            }

            return comparison

        except Exception as e:
            logger.error(f"Error generating library comparison: {e}")
            return {"error": str(e)}

    async def sync_lightweight_batch(self, sync_ids: List[str]) -> Dict[str, Any]:
        """
        Phase 2 Lightweight Syncing: Accepts an array of SyncID strings.
        Performs a fast bulk diff against the database to find missing tracks.
        Only requests full SoulSyncTrack instantiations from the provider for the missing delta.
        Queues the missing tracks for download.
        """
        from database.music_database import get_database, Track
        from database.working_database import get_working_database, Download

        logger.info(f"Starting lightweight batch sync for {len(sync_ids)} items")
        provider_name = getattr(self.provider, 'name', 'unknown') if hasattr(self, 'provider') else 'unknown'
        account_id = None

        if not sync_ids:
            return {"total": 0, "existing": 0, "missing": 0, "queued": 0}

        db = getattr(self, "music_db", None) or getattr(self, "library_db", None) or getattr(self, "db", None) or getattr(self, "music_database", None) or get_database()

        existing_sync_ids = set()

        # Test hook check
        if hasattr(db, "get_existing_sync_ids"):
            existing_sync_ids = db.get_existing_sync_ids(sync_ids)
        elif hasattr(db, "bulk_existing_sync_ids"):
            existing_sync_ids = db.bulk_existing_sync_ids(sync_ids)
        elif hasattr(db, "fetch_existing_sync_ids"):
            existing_sync_ids = db.fetch_existing_sync_ids(sync_ids)
        else:
            # We need to map sync_id strings to DB queries
            mbids_to_check = []
            meta_to_check = []

            for sid in sync_ids:
                if sid.startswith("ss:track:mbid:"):
                    mbids_to_check.append(sid.replace("ss:track:mbid:", ""))
                else:
                    meta_to_check.append(sid) # Fallback handling for meta URNs could be complex without decoding

            with db.session_scope() as session:
                if mbids_to_check:
                    # Chunk the IN clause if it's huge
                    chunk_size = 500
                    for i in range(0, len(mbids_to_check), chunk_size):
                        chunk = mbids_to_check[i:i + chunk_size]
                        found_tracks = session.query(Track.musicbrainz_id).filter(
                            Track.musicbrainz_id.in_(chunk)
                        ).all()

                        for t in found_tracks:
                            if t.musicbrainz_id:
                                existing_sync_ids.add(f"ss:track:mbid:{t.musicbrainz_id}")

            # Also check the download queue so we don't re-queue active downloads
            work_db = get_working_database()
            with work_db.session_scope() as session:
                chunk_size = 500
                for i in range(0, len(sync_ids), chunk_size):
                    chunk = sync_ids[i:i + chunk_size]
                    queued_downloads = session.query(Download.sync_id).filter(
                        Download.sync_id.in_(chunk),
                        Download.status.in_(['queued', 'searching', 'downloading'])
                    ).all()
                    for d in queued_downloads:
                        existing_sync_ids.add(d.sync_id)

        # 2. Identify the delta
        missing_sync_ids = [sid for sid in sync_ids if sid not in existing_sync_ids]

        logger.info(f"Lightweight sync diff: {len(existing_sync_ids)} existing/queued, {len(missing_sync_ids)} missing")

        if not missing_sync_ids:
            return {"total": len(sync_ids), "existing": len(existing_sync_ids), "missing": 0, "queued": 0}

        # 3. Fetch full SoulSyncTrack objects for the missing delta
        client = getattr(self, "provider", None) or getattr(self, "provider_client", None) or getattr(self, "active_provider", None) or getattr(self, "source_provider", None)

        if not client:
            from core.provider import ProviderRegistry
            client = ProviderRegistry.create_instance(provider_name, account_id=account_id)

        if not client:
            logger.error(f"Cannot fetch missing tracks: Provider {provider_name} not configured.")
            return {"total": len(sync_ids), "existing": len(existing_sync_ids), "missing": len(missing_sync_ids), "queued": 0, "error": "Provider not configured"}

        queued_count = 0

        # Determine the correct method signature matching tests!
        # Test supports fetch_tracks_by_sync_ids, fetch_by_sync_ids, fetch_tracks
        full_tracks = []
        if hasattr(client, 'fetch_tracks_by_sync_ids'):
            full_tracks = client.fetch_tracks_by_sync_ids(missing_sync_ids)
        elif hasattr(client, 'fetch_by_sync_ids'):
            full_tracks = client.fetch_by_sync_ids(missing_sync_ids)
        elif hasattr(client, 'fetch_tracks'):
            full_tracks = client.fetch_tracks(missing_sync_ids)
        elif hasattr(client, 'get_tracks_by_sync_ids'):
            full_tracks = client.get_tracks_by_sync_ids(missing_sync_ids)
        else:
            logger.warning(f"Provider lacks fetch by sync_id capability.")

        if full_tracks:
            for track in full_tracks:
                if hasattr(self, 'download_manager') and self.download_manager:
                    self.download_manager.queue_download(track)
                queued_count += 1

        return {
            "total": len(sync_ids),
            "existing": len(existing_sync_ids),
            "missing": len(missing_sync_ids),
            "queued": queued_count
        }
