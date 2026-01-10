"""
LRClib Metadata Provider
Inherits from ProviderBase with enable/disable support
"""

from typing import List, Dict, Optional, Any
from utils.logging_config import get_logger
from core.provider_base import ProviderBase
from core.settings import get_setting, set_setting
from .client import LRCLibClient

logger = get_logger("lrclib_provider")


class LRCLibProvider(ProviderBase):
    """
    LRClib lyrics provider for creating .lrc sidecar files.
    Can be enabled/disabled via configuration.
    """

    name = "lrclib"
    type = "provider"
    supports_downloads = False

    # Track field contracts
    provides_fields = [
        "lyrics_sidecar"
    ]

    # Capabilities
    supports_lyrics = True
    supports_library_scan = False
    supports_streaming = False

    def __init__(self):
        """Initialize LRClib provider"""
        self.client = LRCLibClient()
        self._enabled = self._load_enabled_state()
        
        logger.info(f"✅ LRClib provider initialized (enabled={self._enabled})")

    def _load_enabled_state(self) -> bool:
        """Load enabled state from config"""
        try:
            return get_setting("providers.lrclib.enabled", default=True)
        except Exception as e:
            logger.warning(f"Could not load lrclib enabled state: {e}")
            return True

    # ========================================================================
    # ProviderBase Required Methods
    # ========================================================================

    def authenticate(self, **kwargs) -> bool:
        """LRClib doesn't require authentication"""
        return self.client.api is not None

    def search(self, query: str, type: str = "track", limit: int = 10) -> List[Dict[str, Any]]:
        """LRClib doesn't support search"""
        return []

    def get_track(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Not implemented for LRClib"""
        return None

    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        """Not implemented for LRClib"""
        return None

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """Not implemented for LRClib"""
        return None

    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Not applicable for LRClib"""
        return []

    def get_playlist_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Not applicable for LRClib"""
        return []

    def is_configured(self) -> bool:
        """Check if provider is configured and enabled"""
        return self._enabled and self.client.api is not None

    def get_logo_url(self) -> str:
        """Get provider logo URL"""
        return "https://lrclib.net/favicon.ico"

    # ========================================================================
    # LRClib Specific Methods
    # ========================================================================

    def enable(self):
        """Enable LRClib lyrics generation"""
        if not self._enabled:
            self._enabled = True
            set_setting("providers.lrclib.enabled", True)
            logger.info("✅ LRClib provider enabled")

    def disable(self):
        """Disable LRClib lyrics generation"""
        if self._enabled:
            self._enabled = False
            set_setting("providers.lrclib.enabled", False)
            logger.info("⚠️  LRClib provider disabled")

    def is_enabled(self) -> bool:
        """Check if provider is enabled"""
        return self._enabled

    def create_lyrics_file(self, audio_file_path: str, track_name: str, artist_name: str,
                          album_name: str = None, duration_seconds: int = None) -> bool:
        """
        Create .lrc lyrics sidecar file for audio track.

        Args:
            audio_file_path: Path to audio file
            track_name: Track title
            artist_name: Artist name
            album_name: Album name (optional)
            duration_seconds: Track duration in seconds (optional)

        Returns:
            bool: True if successfully created or already exists
        """
        if not self.is_enabled():
            logger.debug("LRClib provider disabled - skipping lyrics generation")
            return False

        return self.client.create_lrc_file(
            audio_file_path=audio_file_path,
            track_name=track_name,
            artist_name=artist_name,
            album_name=album_name,
            duration_seconds=duration_seconds
        )


# Global instance for backward compatibility
lrclib_provider = LRCLibProvider()
