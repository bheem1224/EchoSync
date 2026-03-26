import os
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator

from core.provider_base import ProviderBase
from core.provider import ProviderCapabilities
from core.enums import Capability
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.settings import config_manager
from core.file_handling.local_io import LocalFileHandler
from core.tiered_logger import get_logger

logger = get_logger("local_server_provider")

class LocalServerProvider(ProviderBase):
    name = 'local_server'
    category = 'provider'
    supports_downloads = False
    enabled = True

    capabilities = ProviderCapabilities(
        capabilities=[
            Capability.SYNC_LIBRARY,
            Capability.STREAM_AUDIO
        ]
    )

    def get_library_tracks(self) -> Generator[SoulSyncTrack, None, None]:
        """
        Yields SoulSyncTrack objects by crawling the local library.
        Extracts duration, isrc, title, and artist via local tags.
        """
        library_dir = config_manager.get_library_dir()
        if not library_dir or not library_dir.exists():
            logger.warning(f"Library directory not configured or does not exist: {library_dir}")
            return

        supported_exts = {'.mp3', '.flac', '.ogg', '.m4a', '.aac', '.alac', '.ape', '.wav', '.dsd', '.dsf', '.dff'}
        file_handler = LocalFileHandler.get_instance()

        for root, _, files in os.walk(library_dir):
            for file in files:
                path = Path(root) / file
                if path.suffix.lower() not in supported_exts:
                    continue

                try:
                    tags = file_handler.read_tags(path)

                    # Fallback to basic filename parsing if tags are missing or empty
                    title = tags.get('title')
                    if not title:
                        title = path.stem

                    artist = tags.get('artist')
                    if not artist:
                        artist = "Unknown Artist"

                    duration_ms = tags.get('duration_ms')
                    # Local tags might return duration in seconds, check key 'duration' if 'duration_ms' is missing
                    if duration_ms is None and tags.get('duration') is not None:
                         # Attempt to convert to ms
                         try:
                             duration_ms = int(float(tags.get('duration')) * 1000)
                         except (ValueError, TypeError):
                             pass

                    isrc = tags.get('isrc')

                    track = self.create_soul_sync_track(
                        title=title,
                        artist=artist,
                        duration_ms=duration_ms,
                        isrc=isrc,
                        file_path=str(path),
                        source=self.name,
                        provider_id=str(path) # Use path as the unique provider item ID
                    )

                    if track:
                        yield track

                except Exception as e:
                    logger.debug(f"Failed to extract tags for {path}, falling back to filename: {e}")

                    track = self.create_soul_sync_track(
                        title=path.stem,
                        artist="Unknown Artist",
                        file_path=str(path),
                        source=self.name,
                        provider_id=str(path)
                    )

                    if track:
                        yield track

    def get_stream_url(self, track_id_or_path: str) -> str:
        """
        Returns a formatted internal API route string for streaming.
        All characters including '/' are percent-encoded so the value is
        unambiguous as a query parameter and safe through reverse proxies.
        """
        encoded_path = urllib.parse.quote(track_id_or_path, safe='')
        return f"/api/local_server/stream?path={encoded_path}"

    def authenticate(self, **kwargs) -> bool:
        return True

    def search(self, query: str, type: str = "track", limit: int = 10, quality_profile: Optional[Dict[str, Any]] = None) -> List[SoulSyncTrack]:
        return []

    def get_track(self, track_id: str) -> Optional[SoulSyncTrack]:
        return None

    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def get_playlist_tracks(self, playlist_id: str) -> List[SoulSyncTrack]:
        return []

    def is_configured(self) -> bool:
        return True

    def get_logo_url(self) -> str:
        return ""
