import os
from typing import Dict, Optional, List, Any
from core.settings import config_manager
from core.provider import ProviderRegistry
from core.path_mapper import PathMapper
from database.music_database import get_database, Track
from core.tiered_logger import get_logger

logger = get_logger("media_manager")

class MediaManagerService:
    def __init__(self):
        self.db = get_database()

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
