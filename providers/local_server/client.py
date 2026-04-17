import os
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator

from core.provider_base import ProviderBase
from core.provider import ProviderCapabilities
from core.enums import Capability
from core.matching_engine.echo_sync_track import EchosyncTrack
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

    def get_library_tracks(self) -> Generator[EchosyncTrack, None, None]:
        """
        Yields EchosyncTrack objects by crawling the local library.
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

                    # ── Singer-First prioritization rule ─────────────────────
                    # tagging_io reads:
                    #   tags['artist']       ← TPE1 / ARTIST   (individual track performer)
                    #   tags['album_artist'] ← TPE2 / ALBUMARTIST (album-level, often 'Various Artists')
                    #
                    # Rule: prefer the individual track artist (TPE1).  Only
                    # fall back to the album artist when TPE1 is completely
                    # absent.  Critically, if TPE1 itself reads 'Various
                    # Artists' (mis-tagged compilation), treat it as absent so
                    # Track.artist_id is never linked to that placeholder when
                    # a real per-track performer is stored elsewhere.
                    _VA_TERMS = {'various artists', 'various', 'va'}

                    _tag_artist   = (tags.get('artist')       or '').strip()
                    _album_artist = (tags.get('album_artist') or '').strip()

                    if _tag_artist and _tag_artist.lower() not in _VA_TERMS:
                        # TPE1 has a real performer — always use it.
                        artist = _tag_artist
                    elif _album_artist and _album_artist.lower() not in _VA_TERMS:
                        # TPE1 is absent or is a VA placeholder, but TPE2
                        # carries a specific band/artist name (uncommon but
                        # valid for certain compilation formats).
                        artist = _album_artist
                        logger.debug(
                            "Singer-First: '%s' — using album_artist '%s' "
                            "(TPE1 was %r)",
                            path.name, artist, _tag_artist or '<empty>',
                        )
                    elif _tag_artist:
                        # TPE1 exists but is 'Various Artists'; keep it so the
                        # metadata_enhancer's Step 0.5 can back-fill the real
                        # artist from online sources or the file structure.
                        artist = _tag_artist
                    else:
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

                    track = self.create_echo_sync_track(
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

                    track = self.create_echo_sync_track(
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

    def search(self, query: str, type: str = "track", limit: int = 10, quality_profile: Optional[Dict[str, Any]] = None) -> List[EchosyncTrack]:
        return []

    def get_track(self, track_id: str) -> Optional[EchosyncTrack]:
        return None

    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def get_playlist_tracks(self, playlist_id: str) -> List[EchosyncTrack]:
        return []

    def is_configured(self) -> bool:
        return True

    def get_logo_url(self) -> str:
        return ""
