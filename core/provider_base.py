from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class ProviderBase(ABC):
    """
    Abstract base class for all music providers (Spotify, Tidal, YouTube, etc.).
    All providers must implement these methods for plugin compatibility.
    """
    name: str  # Unique provider name (e.g., 'spotify', 'tidal', 'youtube')
    supports_downloads: bool = False  # Indicates if the provider supports downloads

    @abstractmethod
    def authenticate(self, **kwargs) -> bool:
        """Authenticate the provider (OAuth, API key, etc.)."""
        pass

    @abstractmethod
    def search(self, query: str, type: str = "track", limit: int = 10) -> List[Dict[str, Any]]:
        """Search for tracks, albums, or artists."""
        pass

    @abstractmethod
    def get_track(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single track by ID."""
        pass

    @abstractmethod
    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single album by ID."""
        pass

    @abstractmethod
    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single artist by ID."""
        pass

    @abstractmethod
    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch playlists for a user (if supported)."""
        pass

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Fetch tracks for a playlist."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if provider is configured and ready to use."""
        pass

    @abstractmethod
    def get_logo_url(self) -> str:
        """Return a URL or path to the provider's logo/icon."""
        pass
