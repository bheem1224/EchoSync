from abc import abstractmethod
from core.provider_base import ProviderBase
from core.content_models import ContentChanges
from typing import Any, Dict, List, Optional
from datetime import datetime
from utils.logging_config import get_logger

logger = get_logger("provider_types")

class DownloaderProvider(ProviderBase):
    """
    Interface for downloader-style providers (Soulseek/slskd).
    """
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[Any]:
        pass

    @abstractmethod
    def download(self, username: str, filename: str, file_size: int = 0) -> Optional[str]:
        pass

    @abstractmethod
    def get_download_status(self, download_id: str) -> Optional[Dict[str, Any]]:
        pass

class MediaServerProvider(ProviderBase):
    """
    Base interface for media server providers (Plex, Jellyfin, Navidrome).
    Provides shared library scan polling logic; subclasses implement server-specific API calls.
    """
    def __init__(self):
        super().__init__()
        self._scan_state = {
            'scanning': False,
            'progress': 0.0,
            'eta_seconds': None,
            'error': None
        }

    @abstractmethod
    def get_library_stats(self) -> Dict[str, int]:
        pass

    @abstractmethod
    def get_all_artists(self) -> List[Any]:
        pass

    @abstractmethod
    def get_all_albums(self) -> List[Any]:
        pass

    @abstractmethod
    def get_all_tracks(self) -> List[Any]:
        pass

    def trigger_library_scan(self, path: Optional[str] = None) -> bool:
        """
        Public method: Trigger a library refresh/scan on the media server.
        Calls server-specific _trigger_scan_api() implementation.
        Args:
            path: Optional library section/path to scan (server-specific format)
        Returns:
            True if scan initiated successfully, False otherwise
        """
        try:
            success = self._trigger_scan_api(path)
            if success:
                self._scan_state['scanning'] = True
                self._scan_state['error'] = None
                logger.info(f"{self.name} library scan initiated")
            return success
        except Exception as e:
            logger.error(f"Error triggering {self.name} scan: {e}", exc_info=True)
            self._scan_state['error'] = str(e)
            return False

    @abstractmethod
    def _trigger_scan_api(self, path: Optional[str] = None) -> bool:
        """
        Server-specific: Trigger scan on the media server API.
        Subclasses implement (Plex library scan, Jellyfin refresh, Navidrome scan).
        Returns: True if API call succeeded.
        """
        pass

    def get_scan_status(self) -> Dict[str, Any]:
        """
        Public method: Get current scan status. Calls server-specific _get_scan_status_api().
        Returns:
            {
                'scanning': bool,
                'progress': float (0-100 or -1 if unknown),
                'eta_seconds': int or None,
                'error': str or None
            }
        """
        try:
            api_status = self._get_scan_status_api()
            # Merge API status into cached state
            self._scan_state.update(api_status)
            return self._scan_state.copy()
        except Exception as e:
            logger.error(f"Error getting {self.name} scan status: {e}", exc_info=True)
            self._scan_state['error'] = str(e)
            return self._scan_state.copy()

    @abstractmethod
    def _get_scan_status_api(self) -> Dict[str, Any]:
        """
        Server-specific: Poll scan status from the media server API.
        Subclasses implement (Plex section refresh status, Jellyfin progress, etc.).
        Returns: partial dict with 'scanning', 'progress', 'eta_seconds', 'error' keys.
        """
        pass

    @abstractmethod
    def get_content_changes_since(self, last_update: Optional[datetime] = None) -> 'ContentChanges':
        """
        Get content changes since the last update timestamp.
        Enables incremental syncs by detecting only new/modified content.
        
        Args:
            last_update: Timestamp of last successful sync. If None, returns all content.
        
        Returns:
            ContentChanges object with lists of changed artists, albums, tracks.
            
        Provider Implementation Guide:
            - Use server-specific APIs to find recently added/updated content
            - Implement early-stopping logic to avoid checking entire library
            - Return empty ContentChanges if no changes detected
            - Set full_refresh=True if last_update is None or too old
        """
        pass

class SyncServiceProvider(ProviderBase):
    """
    Interface for sync service providers (Spotify, Tidal).
    """
    @abstractmethod
    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Any]:
        pass

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: str) -> List[Any]:
        pass

    @abstractmethod
    def sync_playlist(self, playlist_id: str, target_provider: str) -> bool:
        pass
