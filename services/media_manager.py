import os
from typing import Dict, Optional, List, Any
from core.settings import config_manager
from core.provider import ProviderRegistry
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
        file_path = self.db.get_track_path(track_id)
        if file_path and os.path.exists(file_path):
            return file_path

        if file_path:
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
