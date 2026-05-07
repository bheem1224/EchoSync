import os
import base64
from typing import Dict, Optional, List, Any

from sqlalchemy import func

from core.plugin_loader import PluginRegistry, ServiceRegistry
from core.file_handling.path_mapper import PathMapper
from core.event_bus import event_bus
from database.music_database import get_database, Track, Artist
from core.settings import config_manager
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

            active_server = config_manager.get('active_media_server')
            if not active_server:
                logger.warning("No active media server configured for suggestion playlist removal")
                return

            track_id = self._resolve_track_id_from_sync_id(sync_id)
            if not track_id:
                logger.warning(f"Unable to resolve track_id from sync_id: {sync_id}")
                return

            from database.config_database import get_config_database
            config_db = get_config_database()
            plugin_id = config_db.get_or_create_service_id(active_server)

            provider_track_id = self.db.get_external_identifier(plugin_id, track_id)
            if not provider_track_id:
                logger.warning(f"No external identifier for track {track_id} on provider {active_server} (id {plugin_id})")
                return

            provider = PluginRegistry.create_instance(active_server)
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
            from core.plugin_loader import PluginRegistry
            from core.file_handling.storage import get_storage_service
            import json

            storage = get_storage_service()
            active_servers = PluginRegistry.get_active_services_by_type('media_server')

            if not active_servers:
                logger.warning("No active media server configured to check path mappings")
                return None

            for active_server in active_servers:
                try:
                    server_type = active_server.split('.')[-1]
                    service_id = storage.get_or_create_service_id(server_type)
                    mappings_str = storage.get_service_config(service_id, 'path_mappings')

                    mappings = []
                    if mappings_str:
                        try:
                            mappings = json.loads(mappings_str)
                        except Exception:
                            mappings = []

                    if mappings:
                        mapper = PathMapper(mappings)
                        mapped_path = mapper.map_to_local(file_path)

                        if mapped_path != file_path and os.path.exists(mapped_path):
                            logger.debug(f"Mapped remote path '{file_path}' to '{mapped_path}' using {server_type} mappings")
                            return mapped_path
                        elif mapped_path != file_path:
                            logger.warning(f"Mapped path does not exist: {mapped_path} (original: {file_path})")
                except Exception as e:
                    logger.error(f"Error applying path mappings for server {active_server}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error checking local path for track {track_id}: {e}")

        logger.warning(f"File path for track {track_id} does not exist: {file_path}")
        return None

    def deduce_path_mapping(self, local_path: str, provider_path: str) -> Optional[tuple]:
        """
        Calculates and saves the container-to-host directory mapping.
        Steps backward through a confirmed local file path and a Plex/Jellyfin
        file path to find the divergence point.
        """
        import os
        import re

        if not local_path or not provider_path:
            return None

        def split_path(path: str) -> list[str]:
            normalized = path.replace('\\', '/').strip()
            if not normalized:
                return []

            if normalized.startswith('/'):
                parts = [p for p in normalized.split('/') if p]
                return ['/'] + parts

            drive_match = re.match(r'^([A-Za-z]:)(?:/|$)', normalized)
            if drive_match:
                drive = drive_match.group(1)
                remainder = normalized[len(drive):].lstrip('/')
                parts = [p for p in remainder.split('/') if p]
                return [drive] + parts

            return [p for p in normalized.split('/') if p]

        def join_local(parts: list[str], original_path: str) -> str:
            if not parts:
                return ''

            if parts[0] == '/':
                return '/' + '/'.join(parts[1:]) if len(parts) > 1 else '/'

            if re.match(r'^[A-Za-z]:$', parts[0]):
                if '\\' in original_path:
                    return '\\'.join(parts)
                return '/'.join(parts)

            return os.path.join(*parts)

        def join_provider(parts: list[str]) -> str:
            if not parts:
                return ''
            if parts[0] == '/':
                return '/' + '/'.join(parts[1:]) if len(parts) > 1 else '/'
            return '/'.join(parts)

        local_parts = split_path(local_path)
        provider_parts = split_path(provider_path)

        local_idx = len(local_parts) - 1
        prov_idx = len(provider_parts) - 1

        while local_idx >= 0 and prov_idx >= 0:
            if local_parts[local_idx] == provider_parts[prov_idx]:
                local_idx -= 1
                prov_idx -= 1
            else:
                break

        if local_idx == len(local_parts) - 1 or prov_idx == len(provider_parts) - 1:
            logger.warning(f"No path overlap found between local '{local_path}' and remote '{provider_path}'")
            return None

        local_prefix = join_local(local_parts[:local_idx + 1], local_path) if local_idx >= 0 else '/'
        remote_prefix = join_provider(provider_parts[:prov_idx + 1]) if prov_idx >= 0 else '/'

        mapping = {"local": local_prefix, "remote": remote_prefix}
        logger.info(f"Deduced path mapping: {mapping}")

        # Save to active media server config
        try:
            from core.plugin_loader import PluginRegistry
            from database.config_database import get_config_database
            import json

            active_servers = PluginRegistry.get_active_services_by_type('media_server')
            if not active_servers:
                logger.warning("No active media server configured to deduce path mapping")
                return (local_prefix, remote_prefix)

            for active_server in active_servers:
                try:
                    server_type = active_server.split('.')[-1]
                    db = get_config_database()
                    service_id = db.get_or_create_service_id(server_type)

                    current_mappings = db.get_service_config(service_id, 'path_mappings')
                    if not current_mappings:
                        current_mappings = []
                    elif isinstance(current_mappings, str):
                        try:
                            current_mappings = json.loads(current_mappings)
                        except Exception:
                            current_mappings = []

                    exists = any(m.get('local') == mapping['local'] and m.get('remote') == mapping['remote'] for m in current_mappings)

                    if not exists:
                        current_mappings.append(mapping)
                        db.set_service_config(service_id, 'path_mappings', json.dumps(current_mappings), is_sensitive=False)
                        logger.info(f"Saved new path mapping for {server_type}")
                except Exception as e:
                    logger.error(f"Failed to save deduced path mapping for server {active_server}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error deducing path mapping: {e}")

        return (local_prefix, remote_prefix)

    def delete_track(self, track_id: int) -> bool:
        """
        Delete a track from the media server (if applicable) and local database.
        """
        from core.plugin_loader import PluginRegistry
        active_servers = PluginRegistry.get_active_services_by_type('media_server')

        remote_delete_success = False
        any_server_attempted = False

        if not active_servers:
            logger.warning("No active media server configured for track deletion")
            remote_delete_success = True  # We have no remote to delete from, proceed to local
        else:
            for active_server in active_servers:
                try:
                    server_type = active_server.split('.')[-1]
                    provider_item_id = self.db.get_external_identifier(server_type, track_id)

                    if provider_item_id:
                        any_server_attempted = True
                        provider = PluginRegistry.create_instance(active_server)
                        if hasattr(provider, 'delete_track'):
                            success = provider.delete_track(provider_item_id)
                            if success:
                                logger.info(f"Successfully deleted track {track_id} from {active_server}")
                                remote_delete_success = True
                            else:
                                logger.error(f"Failed to delete track {track_id} (ID: {provider_item_id}) from {active_server}")
                        else:
                            logger.warning(f"Provider {active_server} does not support delete_track")
                    else:
                        logger.info(f"Track {track_id} not linked to {server_type}, skipping remote delete")

                except Exception as e:
                    logger.error(f"Error deleting from provider {active_server}: {e}")
                    continue

            # If we didn't attempt to delete on ANY server because there were no external identifiers,
            # treat it as a success so we can still clean up the local DB.
            if not any_server_attempted:
                remote_delete_success = True

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
