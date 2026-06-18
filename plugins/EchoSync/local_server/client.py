import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator
from datetime import datetime

from core.nexus_framework.plugin_SDK import PluginBase
from core.nexus_framework.plugin_SDK import ProviderCapabilities, PlaylistSupport, SearchCapabilities, MetadataRichness
from core.enums import Capability
from core.matching_engine.echo_sync_track import EchosyncTrack

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

        supported_exts = {'.mp3', '.flac', '.ogg', '.m4a', '.aac', '.alac', '.ape', '.wav', '.dsd', '.dsf', '.dff'}
        file_handler = LocalFileHandler.get_instance()
        
        def process_file(path: Path) -> Optional[EchosyncTrack]:
            try:
                tags = file_handler.read_tags(path)
                title = tags.get('title')
                if not title:
                    title = path.stem

                _VA_TERMS = {'various artists', 'various', 'va'}
                _tag_artist   = (tags.get('artist')       or '').strip()
                _album_artist = (tags.get('album_artist') or '').strip()

                if _tag_artist and _tag_artist.lower() not in _VA_TERMS:
                    artist = _tag_artist
                elif _album_artist and _album_artist.lower() not in _VA_TERMS:
                    artist = _album_artist
                    logger.debug("Singer-First: '%s' — using album_artist '%s' (TPE1 was %r)", path.name, artist, _tag_artist or '<empty>')
                elif _tag_artist:
                    artist = _tag_artist
                else:
                    artist = ""

                duration_ms = tags.get('duration_ms')
                if duration_ms is None and tags.get('duration') is not None:
                     try:
                         duration_ms = int(float(tags.get('duration')) * 1000)
                     except (ValueError, TypeError):
                         pass

                isrc = tags.get('isrc')
                
                # Fetch additional technical metadata
                try:
                    file_stat = path.stat()
                    file_size_bytes = file_stat.st_size
                    added_at = int(file_stat.st_ctime)
                except Exception:
                    file_size_bytes = None
                    added_at = None

                import os
                if not title or not title.strip():
                    # Fallback to the raw filename without extension
                    title = path.stem if hasattr(path, 'stem') else os.path.splitext(os.path.basename(str(path)))[0]

                if not artist or not artist.strip():
                    # Fallback to the parent folder name
                    artist = path.parent.name if hasattr(path, 'parent') else os.path.basename(os.path.dirname(str(path)))

                return self.create_echo_sync_track(
                    title=title,
                    artist=artist,
                    album_artist=_album_artist if _album_artist else None,
                    album=tags.get('album'),
                    duration_ms=duration_ms,
                    isrc=isrc,
                    musicbrainz_id=tags.get('musicbrainz_id') or tags.get('recording_id'),
                    mb_release_id=tags.get('release_id') or tags.get('musicbrainz_albumid'),
                    acoustid_id=tags.get('acoustid_id') or tags.get('acoustid id'),
                    year=tags.get('year') or tags.get('date'),
                    track_number=tags.get('track_number') or tags.get('tracknumber'),
                    disc_number=tags.get('disc_number') or tags.get('discnumber'),
                    bitrate=tags.get('bitrate_kbps') or tags.get('bitrate'),
                    sample_rate=tags.get('sample_rate_hz') or tags.get('sample_rate'),
                    bit_depth=tags.get('bit_depth'),
                    file_format=tags.get('file_format'),
                    file_size_bytes=file_size_bytes,
                    added_at=datetime.fromtimestamp(added_at) if added_at else None,
                    file_path=str(path),
                    source=self.name,
                    # No provider_id to prevent writing an external identifier
                )
            except Exception as e:
                logger.warning(f"Failed to extract tags for {path}, falling back to filename: {e}")
                
                try:
                    file_stat = path.stat()
                    file_size_bytes = file_stat.st_size
                    added_at = int(file_stat.st_ctime)
                except Exception:
                    file_size_bytes = None
                    added_at = None
                    
                return self.create_echo_sync_track(
                    title=path.stem,
                    artist="Unknown Artist",
                    file_path=str(path),
                    source=self.name,
                    file_size_bytes=file_size_bytes,
                    added_at=datetime.fromtimestamp(added_at) if added_at else None,
                    # No provider_id
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
                        elif entry.is_file() and entry.suffix.lower() in supported_exts:
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
