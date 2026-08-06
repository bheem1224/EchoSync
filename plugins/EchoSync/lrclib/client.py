#!/usr/bin/env python3

from pathlib import Path
from core.tiered_logger import get_logger
from core.nexus_framework.plugin_SDK import ProviderCapabilities, PlaylistSupport, SearchCapabilities, MetadataRichness

from typing import Any, Optional

def _safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """AST-compliant alternative to getattr()."""
    if hasattr(obj, attr):
        try:
            return obj.__getattribute__(attr)
        except AttributeError:
            return default
    return default

logger = get_logger("lrclib_client")

# Optional import of lrclib for graceful fallback
try:
    from lrclib import LrcLibAPI
except Exception:
    LrcLibAPI = None


from core.nexus_framework.plugin_SDK import PluginBase

class LRCLibClient(PluginBase):
    """
    LRClib API client for fetching synchronized lyrics.
    Creates .lrc sidecar files during post-processing.
    """
    name = "EchoSync.lrclib"
    capabilities = ProviderCapabilities(
        name='EchoSync.lrclib',
        supports_playlists=PlaylistSupport.NONE,
        search=SearchCapabilities(tracks=False, artists=False, albums=False, playlists=False),
        metadata=MetadataRichness.LOW,
        supports_cover_art=False,
        supports_lyrics=True,
        supports_user_auth=False,
        supports_library_scan=False,
        supports_streaming=False,
        supports_downloads=False,
    )

    def __init__(self):
        super().__init__()
        self.api = None
        self._init_api()

    def authenticate(self, **kwargs) -> bool:
        return True

    def search(self, query: str, type: str = "track", limit: int = 10) -> list:
        return []

    def get_track(self, track_id: str) -> Any:
        return None

    def get_album(self, album_id: str) -> Any:
        return None

    def get_artist(self, artist_id: str) -> Any:
        return None

    def get_user_playlists(self, user_id: Optional[str] = None) -> list:
        return []

    def get_playlist_tracks(self, playlist_id: str) -> list:
        return []

    def is_configured(self) -> bool:
        return self.api is not None

    def get_logo_url(self) -> str:
        return "https://lrclib.net/logo.png"

    def _init_api(self):
        """Initialize LRClib API with graceful fallback"""
        try:
            if LrcLibAPI is None:
                raise ImportError("lrclib not available")

            self.api = LrcLibAPI(user_agent="Echosync/1.0")
            logger.debug("LRClib API client initialized")
        except ImportError:
            logger.warning("LRClib API not available - lyrics functionality disabled")
            self.api = None
        except Exception as e:
            logger.error(f"Error initializing LRClib API: {e}")
            self.api = None

    def create_lrc_file(self, audio_file_path: str, track_name: str, artist_name: str,
                       album_name: str = None, duration_seconds: int = None) -> bool:
        """
        Create .lrc sidecar file for the given audio file.

        Args:
            audio_file_path: Path to the audio file
            track_name: Track title
            artist_name: Artist name
            album_name: Album name (optional)
            duration_seconds: Track duration in seconds (optional)

        Returns:
            bool: True if LRC file was created successfully
        """
        if not self.api:
            logger.debug("LRClib API not available - skipping lyrics")
            return False

        try:
            # Generate LRC file path (same name as audio file, .lrc extension)
            audio_path = Path(audio_file_path)
            lrc_path = audio_path.with_suffix('.lrc')

            # Skip if LRC file already exists
            if lrc_path.exists():
                logger.debug(f"LRC file already exists: {lrc_path.name}")
                return True

            # Fetch lyrics from LRClib
            logger.debug(f"Fetching lyrics for: {artist_name} - {track_name}")

            lyrics_data = None

            # Primary attempt: ask API for lyrics (pass album/duration if available)
            try:
                logger.debug(f"Attempting get_lyrics: {track_name} by {artist_name}")
                lyrics_data = self.api.get_lyrics(
                    track_name=track_name,
                    artist_name=artist_name,
                    album_name=album_name,
                    duration=duration_seconds
                )
                if lyrics_data:
                    logger.debug("get_lyrics returned a result")
            except Exception as e:
                logger.debug(f"get_lyrics failed: {e}")

            # Fallback: search if get_lyrics didn't return anything
            if not lyrics_data:
                try:
                    logger.debug(f"Trying search: {track_name} by {artist_name}")
                    search_results = self.api.search_lyrics(
                        track_name=track_name,
                        artist_name=artist_name
                    )
                    if search_results:
                        lyrics_data = search_results[0]  # Take first result
                        logger.debug(f"Search found {len(search_results)} results, using first")
                except Exception as e:
                    logger.debug(f"Search fallback failed: {e}")

            # No lyrics found
            if not lyrics_data:
                logger.debug(f"No lyrics found for: {artist_name} - {track_name}")
                return False

            # Prefer synced lyrics, fallback to plain text
            lrc_content = _safe_getattr(lyrics_data, 'synced_lyrics', None) or _safe_getattr(lyrics_data, 'plain_lyrics', None)

            logger.debug(f"Synced lyrics available: {bool(_safe_getattr(lyrics_data, 'synced_lyrics', None))}")
            logger.debug(f"Plain lyrics available: {bool(_safe_getattr(lyrics_data, 'plain_lyrics', None))}")

            if not lrc_content:
                logger.debug(f"No usable lyrics content for: {artist_name} - {track_name}")
                return False

            # Write LRC file
            lrc_path.write_text(lrc_content, encoding='utf-8')

            lyrics_type = "synced" if _safe_getattr(lyrics_data, 'synced_lyrics', None) else "plain"
            logger.info(f"✅ Created {lyrics_type} LRC file: {lrc_path.name}")
            return True

        except Exception as e:
            logger.error(f"Error creating LRC file for {track_name}: {e}")
            return False
