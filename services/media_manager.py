import os
import base64
from typing import Dict, Optional, List, Any

from sqlalchemy import func

from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
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
            
            # The Routing Matrix Subscriptions
            event_bus.subscribe("user_request_upgrade", self.handle_lifecycle_event)
            event_bus.subscribe("user_request_delete", self.handle_lifecycle_event)
            event_bus.subscribe("suggested_upgrade", self.handle_lifecycle_event)
            event_bus.subscribe("suggested_delete", self.handle_lifecycle_event)
            event_bus.subscribe("system_duplicate", self.handle_lifecycle_event)
            
            self._subscribed = True
        except Exception as e:
            logger.warning(f"Failed to subscribe media manager events: {e}")

    AUTO_DELETE_CONFIDENCE_THRESHOLD = 95.0

    def handle_lifecycle_event(self, event_data: Dict[str, Any]) -> None:
        """The Routing Matrix for core events."""
        event_type = event_data.get('event_type')
        if not event_type:
            # Fallback if publisher didn't include it in payload
            return

        # The Strict Manual Review Guardrail
        if event_data.get('requires_manual_review'):
            logger.info(f"Event {event_type} explicitly flagged for manual review. Bypassing all automation.")
            self._stage_pending_action(event_type, event_data)
            return

        # The Confidence Gate
        if event_type == "system_duplicate":
            confidence_score = event_data.get('confidence_score', 0.0)
            if confidence_score < self.AUTO_DELETE_CONFIDENCE_THRESHOLD:
                logger.info(f"Confidence {confidence_score:.1f}% below threshold {self.AUTO_DELETE_CONFIDENCE_THRESHOLD}%. Routing to manual review.")
                reason = event_data.get('reason', f'Lifecycle Action: {event_type}')
                event_data['reason'] = f"{reason} | Warning: Confidence too low for auto-resolve."
                self._stage_pending_action(event_type, event_data)
                return
            
        manager_config = config_manager.get("manager", {}) or {}
        auto_level = manager_config.get("automation_level", "Level 0")
        
        auto_allowed = False
        if "Hygiene" in auto_level or "Level 1" in auto_level:
            if event_type == "system_duplicate":
                auto_allowed = True
        elif "Level 2" in auto_level or "Full" in auto_level:
            auto_allowed = True

        delete_ids = event_data.get('delete_ids', [])
        
        if auto_allowed and delete_ids:
            logger.info(f"Event {event_type} auto-approved. Deleting {len(delete_ids)} tracks.")
            self.execute_delete(delete_ids)
        else:
            logger.info(f"Event {event_type} requires manual review. Staging to pending actions.")
            self._stage_pending_action(event_type, event_data)

    def _stage_pending_action(self, event_type: str, payload: Dict[str, Any]):
        from database.working_database import get_working_database, SuggestionStagingQueue
        db = get_working_database()
        with db.session_scope() as session:
            reason = payload.get('reason', f'Lifecycle Action: {event_type}')
            keep_id = payload.get('keep_id')
            
            intent_map = {
                "user_request_upgrade": "USER_UPGRADE_REQUEST",
                "user_request_delete": "USER_DELETE_REQUEST",
                "suggested_upgrade": "SYSTEM_UPGRADE_SUGGESTION",
                "suggested_delete": "SYSTEM_DELETE_SUGGESTION",
                "system_duplicate": "HYGIENE_DUPLICATION",
            }
            intent_type = intent_map.get(event_type, "SYSTEM_DELETE_SUGGESTION")
            system_user_id = db.get_system_user_id()
            
            staging = SuggestionStagingQueue(
                user_id=system_user_id,
                music_db_track_id=keep_id,
                reason=reason,
                intent_type=intent_type,
                ui_label=f"Review needed for {event_type}",
                context_data=payload,
                status="pending"
            )
            session.add(staging)

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

            provider_track_id = self.db.get_external_identifier(active_server, track_id)
            if not provider_track_id:
                logger.warning(f"No external identifier for track {track_id} on provider {active_server}")
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
            from core.nexus_framework.plugin_loader import PluginRegistry
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


    def execute_delete(self, track_ids: List[int]) -> bool:
        """
        The strict, protected central execution point for deleting tracks.
        This is the ONLY place in the backend where physical os.remove() and
        local track database deletions are executed.
        """
        from core.nexus_framework.plugin_loader import PluginRegistry
        from pathlib import Path

        # Fetch library pool for safety check
        _lib = config_manager.get('storage.library_dir') or config_manager.get('library_dir')
        library_root = Path(_lib).resolve() if _lib else None

        active_servers = PluginRegistry.get_active_services_by_type('media_server')
        all_success = True

        for track_id in track_ids:
            # 1. Remote Deletion
            if active_servers:
                for active_server in active_servers:
                    try:
                        server_type = active_server.split('.')[-1]
                        plugin_item_id = self.db.get_external_identifier(server_type, track_id)
                        if plugin_item_id:
                            provider = PluginRegistry.create_instance(active_server)
                            if hasattr(provider, 'delete_track'):
                                provider.delete_track(plugin_item_id)
                                logger.info(f"Successfully deleted track {track_id} from {active_server}")
                    except Exception as e:
                        logger.error(f"Error remote delete on {active_server}: {e}")

            # 2. Local Deletion
            try:
                with self.db.session_scope() as session:
                    track = session.query(Track).filter(Track.id == track_id).first()
                    if not track:
                        continue

                    # Safety Check and Physical Deletion
                    if track.file_path and os.path.exists(track.file_path):
                        track_path = Path(track.file_path).resolve()
                        
                        if library_root and not str(track_path).startswith(str(library_root)):
                            logger.critical(f"Aborting deletion! Path {track_path} is OUTSIDE the library pool {library_root}.")
                            all_success = False
                            continue

                        from core.hook_manager import hook_manager
                        plugin_decision = hook_manager.apply_filters('ON_CORRUPTION_DETECTED', None, file_path=str(track_path))
                        if plugin_decision == "SKIP":
                            logger.info(f"Plugin quarantined/skipped deletion for file: {track_path}")
                            all_success = False
                            continue

                        os.remove(track_path)
                        logger.info(f"Deleted physical file: {track_path}")

                    # Database Deletion
                    session.delete(track)
                    logger.info(f"Deleted track {track_id} from local database")
            except Exception as e:
                logger.error(f"Failed to delete local track {track_id}: {e}", exc_info=True)
                all_success = False

        return all_success
