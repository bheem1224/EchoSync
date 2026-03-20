import os
import base64
from typing import Dict, Optional, List, Any

from sqlalchemy import func

from core.settings import config_manager
from core.provider import ProviderRegistry
from core.path_mapper import PathMapper
from core.event_bus import event_bus
from database.music_database import get_database, Track, Artist
from core.tiered_logger import get_logger

logger = get_logger("media_manager")

class MediaManagerService:
    def __init__(self):
        self.db = get_database()
        self._subscribed = False
        self._subscribe_events()

    def _subscribe_events(self) -> None:
        if self._subscribed:
            return
        try:
            event_bus.subscribe("SUGGESTION_PLAYLIST_REMOVE_INTENT", self.handle_suggestion_playlist_remove_intent)
            self._subscribed = True
        except Exception as e:
            logger.warning(f"Failed to subscribe media manager events: {e}")

    def _resolve_track_id_from_sync_id(self, sync_id: str) -> Optional[int]:
        base_sync_id = str(sync_id or "").split("?")[0]

        # Handle mbid URI path.
        if base_sync_id.startswith("ss:track:mbid:"):
            mbid = base_sync_id.split("ss:track:mbid:", 1)[1]
            if not mbid:
                return None
            with self.db.session_scope() as session:
                row = session.query(Track.id).filter(Track.musicbrainz_id == mbid).first()
                return int(row[0]) if row else None

        # Handle meta URI path: ss:track:meta:{base64(artist|title)}
        if not base_sync_id.startswith("ss:track:meta:"):
            return None

        encoded = base_sync_id.split("ss:track:meta:", 1)[1]
        if not encoded:
            return None

        try:
            decoded = base64.b64decode(encoded.encode("ascii")).decode("utf-8")
            artist_name, title = decoded.split("|", 1)
        except Exception:
            return None

        with self.db.session_scope() as session:
            row = (
                session.query(Track.id)
                .join(Artist, Track.artist_id == Artist.id)
                .filter(
                    func.lower(Artist.name) == artist_name.lower(),
                    func.lower(Track.title) == title.lower(),
                )
                .first()
            )
            return int(row[0]) if row else None

    def handle_suggestion_playlist_remove_intent(self, event_data: Dict[str, Any]) -> None:
        """Handle SUGGESTION_PLAYLIST_REMOVE_INTENT by invoking provider playlist removal."""
        try:
            sync_id = event_data.get("sync_id")
            playlist_id = event_data.get("playlist_name", "Suggestions for You")

            if not sync_id:
                logger.warning("SUGGESTION_PLAYLIST_REMOVE_INTENT missing sync_id")
                return

            active_server = config_manager.get_active_media_server()
            if not active_server:
                logger.warning("No active media server configured for suggestion playlist removal")
                return

            track_id = self._resolve_track_id_from_sync_id(sync_id)
            if not track_id:
                logger.warning(f"Unable to resolve track_id from sync_id: {sync_id}")
                return

            provider_track_id = self.db.get_external_identifier(active_server, track_id)
            if not provider_track_id:
                logger.warning(f"No external identifier for track {track_id} on provider {active_server}")
                return

            provider = ProviderRegistry.create_instance(active_server)
            if not hasattr(provider, "remove_tracks_from_playlist"):
                logger.warning(f"Provider {active_server} does not support remove_tracks_from_playlist")
                return

            success = provider.remove_tracks_from_playlist(str(playlist_id), [str(provider_track_id)])
            if success:
                logger.info(
                    f"Removed sync_id {sync_id} (provider id {provider_track_id}) from playlist '{playlist_id}' on {active_server}"
                )
            else:
                logger.warning(
                    f"Provider {active_server} failed removing sync_id {sync_id} from playlist '{playlist_id}'"
                )
        except Exception as e:
            logger.error(f"Error handling SUGGESTION_PLAYLIST_REMOVE_INTENT: {e}", exc_info=True)

    def get_library_index(self) -> List[Dict]:
        """Return the library hierarchy (Artist -> Album -> Tracks)."""
        return self.db.get_library_hierarchy()

    def get_track_stream(self, track_id: int) -> Optional[str]:
        """
        Get the local file path for a track.
        Returns None if track not found or file missing.
        """
        # 1. Get raw path from database
        file_path = self.db.get_track_path(track_id)
        if not file_path:
            return None

        # 2. Check if file exists as-is (already local/mapped)
        if os.path.exists(file_path):
            return file_path

        # 3. If not found, try to apply path mappings from the active media server
        try:
            active_server = config_manager.get_active_media_server()
            server_config = config_manager.get_active_media_server_config()

            # Check for mappings (Plex stores them in 'path_mappings', others might vary)
            mappings = server_config.get('path_mappings', [])

            if mappings:
                mapper = PathMapper(mappings)
                mapped_path = mapper.map_to_local(file_path)

                if mapped_path != file_path and os.path.exists(mapped_path):
                    logger.debug(f"Mapped remote path '{file_path}' to '{mapped_path}'")
                    return mapped_path
                elif mapped_path != file_path:
                    logger.warning(f"Mapped path does not exist: {mapped_path} (original: {file_path})")

        except Exception as e:
            logger.error(f"Error applying path mappings for track {track_id}: {e}")

        logger.warning(f"File path for track {track_id} does not exist: {file_path}")
        return None

    def delete_track(self, track_id: int) -> bool:
        """
        Delete a track from the media server (if applicable) and local database.
        """
        active_server = config_manager.get_active_media_server()
        remote_delete_success = True

        # 1. Try to delete from remote provider if configured
        if active_server:
            try:
                # Get the external identifier for this track on the active server
                provider_item_id = self.db.get_external_identifier(active_server, track_id)

                if provider_item_id:
                    try:
                        provider = ProviderRegistry.create_instance(active_server)
                        if hasattr(provider, 'delete_track'):
                            success = provider.delete_track(provider_item_id)
                            if not success:
                                logger.error(f"Failed to delete track {track_id} (ID: {provider_item_id}) from {active_server}")
                                remote_delete_success = False
                            else:
                                logger.info(f"Successfully deleted track {track_id} from {active_server}")
                        else:
                            logger.warning(f"Provider {active_server} does not support delete_track")
                    except Exception as e:
                        logger.error(f"Failed to instantiate provider {active_server}: {e}")
                        remote_delete_success = False
                else:
                     logger.info(f"Track {track_id} not linked to {active_server}, skipping remote delete")

            except Exception as e:
                logger.error(f"Error deleting from provider {active_server}: {e}")
                remote_delete_success = False

        if not remote_delete_success:
            return False

        # 2. Delete from local database
        try:
            with self.db.session_scope() as session:
                track = session.query(Track).filter(Track.id == track_id).first()
                if track:
                    session.delete(track)
                    logger.info(f"Deleted track {track_id} from local database")
                    return True
                else:
                    logger.warning(f"Track {track_id} not found in database")
                    return False
        except Exception as e:
            logger.error(f"Error deleting track {track_id} from database: {e}")
            return False
