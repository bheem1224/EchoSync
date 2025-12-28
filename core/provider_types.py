from abc import abstractmethod
from core.provider_base import ProviderBase
from typing import Any, Dict, List, Optional

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
    Interface for media server providers (Plex, Jellyfin, Navidrome).
    """
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
