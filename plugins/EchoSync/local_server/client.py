import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator
from datetime import datetime

from core.nexus_framework.plugin_SDK import PluginBase
from core.nexus_framework.plugin_SDK import ProviderCapabilities, PlaylistSupport, SearchCapabilities, MetadataRichness
from core.enums import Capability
from core.matching_engine.echo_sync_track import EchosyncTrack
from core.file_handling.audio_inspector import inspect_audio_file, SUPPORTED_AUDIO_EXTENSIONS
from core.file_handling.local_io import LocalFileHandler
from core.tiered_logger import get_logger

logger = get_logger("local_server_provider")

class LocalServerProvider(PluginBase):
    name = 'EchoSync.local_server'
    category = 'provider'
    supports_downloads = False
    enabled = True

    capabilities = ProviderCapabilities(
        name='EchoSync.local_server',
        supports_playlists=PlaylistSupport.NONE,
        search=SearchCapabilities(tracks=False),
        metadata=MetadataRichness.LOW,
        supports_library_scan=True,
        supports_streaming=True,
    )

    def get_all_tracks(self) -> Generator[EchosyncTrack, None, None]:
        """
        Yields EchosyncTrack objects by crawling the local library.
        Extracts duration, isrc, title, and artist via local tags.
        """
        library_dir_str = self.sdk.config.get("library_dir")
        if not library_dir_str:
            from core.settings import config_manager
            library_dir_str = config_manager.get('storage.library_dir') or config_manager.get('library_dir')

        if not library_dir_str:
            logger.warning("Library directory not configured globally or locally.")
            return

        library_dir = Path(library_dir_str)
        if not library_dir.exists():
            logger.warning(f"Library directory does not exist: {library_dir}")
            return

        def process_file(path: Path) -> Optional[EchosyncTrack]:
            try:
                result = inspect_audio_file(path)

                if result.artist_source != "tpe1":
                    logger.debug(
                        "Singer-First fallback: '%s' artist='%s' (source=%s)",
                        path.name, result.artist, result.artist_source,
                    )

                return self.create_echo_sync_track(
                    title=result.title,
                    artist=result.artist,
                    album_artist=result.album_artist,
                    album=result.album,
                    duration_ms=result.duration_ms,
                    isrc=result.isrc,
                    musicbrainz_id=result.musicbrainz_id,
                    mb_release_id=result.release_id,
                    acoustid_id=result.acoustid_id,
                    year=result.year,
                    track_number=result.track_number,
                    disc_number=result.disc_number,
                    bitrate=result.bitrate_kbps,
                    sample_rate=result.sample_rate_hz,
                    bit_depth=result.bit_depth,
                    file_format=result.file_format,
                    file_size_bytes=result.file_size_bytes,
                    added_at=datetime.fromtimestamp(path.stat().st_ctime) if path.exists() else None,
                    file_path=str(path),
                    source=self.name,
                    # No provider_id to prevent writing an external identifier
                )
            except Exception as e:
                logger.warning("Failed to process '%s', falling back to filename: %s", path.name, e)
                try:
                    file_stat = path.stat()
                    file_size_bytes = file_stat.st_size
                    added_at = datetime.fromtimestamp(file_stat.st_ctime)
                except Exception:
                    file_size_bytes = None
                    added_at = None
                return self.create_echo_sync_track(
                    title=path.stem,
                    artist="Various Artists",
                    file_path=str(path),
                    source=self.name,
                    file_size_bytes=file_size_bytes,
                    added_at=added_at,
                )

        import concurrent.futures
        
        def _iter_audio_files(root: Path) -> Generator[Path, None, None]:
            """Walk the directory tree, yielding audio files while tolerating
            per-directory PermissionError/OSError."""
            try:
                for entry in root.iterdir():
                    if entry.name == '.zfs':
                        logger.debug(f"Skipping ZFS directory: {entry}")
                        continue
                    try:
                        if entry.is_symlink():
                            try:
                                resolved = entry.resolve(strict=True)
                                if not resolved.exists():
                                    continue
                            except (OSError, RuntimeError):
                                continue

                        if entry.is_dir():
                            yield from _iter_audio_files(entry)
                        elif entry.is_file() and entry.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS:
                            yield entry
                    except PermissionError:
                        logger.warning(f"Permission denied, skipping: {entry}")
                    except OSError as e:
                        logger.warning(f"OS error scanning {entry}: {e}")
            except PermissionError:
                logger.warning(f"Permission denied, skipping directory: {root}")
            except OSError as e:
                logger.warning(f"OS error scanning directory {root}: {e}")

        # Collect all valid files first using the safe generator
        files = list(_iter_audio_files(library_dir))
        logger.info(f"Local crawler discovered {len(files)} audio files under {library_dir}")
        
        # Process concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_path = {executor.submit(process_file, path): path for path in files}
            for future in concurrent.futures.as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    track = future.result()
                    if track:
                        yield track
                except Exception as e:
                    logger.warning(f"Failed to process {path}: {e}")

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
