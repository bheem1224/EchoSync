"""
Core Provider Module for SoulSync.

This module consolidates the internal machinery for the provider system, including:
1. The `Provider` Protocol (Contract).
2. Specialized Provider Types (ABCs like `MediaServerProvider`).
3. Provider Capabilities (Metadata about what a provider can do).
4. The `ProviderRegistry` (Central registry for loaded plugins).

Developer SDK:
    For building new providers, inherit from `core.provider_base.ProviderBase`.
    Do not modify this file unless you are changing the internal plugin architecture.
"""

from typing import Protocol, List, Optional, Dict, Any, Type
from abc import abstractmethod
from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime

from core.provider_base import ProviderBase
from core.content_models import ContentChanges
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.tiered_logger import get_logger

logger = get_logger("core.provider")


# ==============================================================================
# 1. The Provider Protocol (Contract)
# ==============================================================================

class Provider(Protocol):
    """
    Strict Contract that all future providers (Python or Rust) must adhere to.
    """

    def search_tracks(self, query: str) -> List[SoulSyncTrack]:
        """
        Search for tracks based on a query string.
        """
        ...

    def get_track_by_id(self, item_id: str) -> Optional[SoulSyncTrack]:
        """
        Retrieve a specific track by its ID.
        """
        ...

    def get_artist_details(self, artist_id: str) -> Dict[str, Any]:
        """
        Retrieve details about an artist.
        """
        ...


# ==============================================================================
# 2. Specialized Provider Types
# ==============================================================================

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
        Returns: True if API call succeeded.
        """
        pass

    def get_scan_status(self) -> Dict[str, Any]:
        """
        Public method: Get current scan status. Calls server-specific _get_scan_status_api().
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
        Returns: partial dict with 'scanning', 'progress', 'eta_seconds', 'error' keys.
        """
        pass

    @abstractmethod
    def get_content_changes_since(self, last_update: Optional[datetime] = None) -> 'ContentChanges':
        """
        Get content changes since the last update timestamp.
        Enables incremental syncs by detecting only new/modified content.
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


# ==============================================================================
# 3. Provider Capabilities
# ==============================================================================

class PlaylistSupport(Enum):
    NONE = auto()
    READ = auto()
    READ_WRITE = auto()


class MetadataRichness(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


@dataclass(frozen=True)
class SearchCapabilities:
    tracks: bool = False
    artists: bool = False
    albums: bool = False
    playlists: bool = False


@dataclass(frozen=True)
class ProviderCapabilities:
    name: str
    supports_playlists: PlaylistSupport
    search: SearchCapabilities
    metadata: MetadataRichness
    supports_cover_art: bool = False
    supports_lyrics: bool = False
    supports_user_auth: bool = False
    supports_library_scan: bool = False
    supports_streaming: bool = False
    supports_downloads: bool = False
    playlist_algorithms: list = None  # List of algorithm IDs (e.g., ['spotify_mood'])


# Central registry of known provider capabilities
CAPABILITY_REGISTRY: Dict[str, ProviderCapabilities] = {
    'spotify': ProviderCapabilities(
        name='spotify',
        supports_playlists=PlaylistSupport.READ,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=True),
        metadata=MetadataRichness.HIGH,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=False,
        supports_streaming=True,
        supports_downloads=False,
        playlist_algorithms=['spotify_mood', 'spotify_energy', 'spotify_newness'],
    ),
    'tidal': ProviderCapabilities(
        name='tidal',
        supports_playlists=PlaylistSupport.READ,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=True),
        metadata=MetadataRichness.HIGH,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=False,
        supports_streaming=True,
        supports_downloads=False,
    ),
    'plex': ProviderCapabilities(
        name='plex',
        supports_playlists=PlaylistSupport.READ_WRITE,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=False),
        metadata=MetadataRichness.HIGH,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=True,
        supports_streaming=False,
        supports_downloads=False,
    ),
    'jellyfin': ProviderCapabilities(
        name='jellyfin',
        supports_playlists=PlaylistSupport.READ_WRITE,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=False),
        metadata=MetadataRichness.MEDIUM,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=True,
        supports_streaming=False,
        supports_downloads=False,
    ),
    'navidrome': ProviderCapabilities(
        name='navidrome',
        supports_playlists=PlaylistSupport.READ_WRITE,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=True),
        metadata=MetadataRichness.MEDIUM,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=True,
        supports_streaming=False,
        supports_downloads=False,
    ),
    'soulseek': ProviderCapabilities(
        name='soulseek',
        supports_playlists=PlaylistSupport.NONE,
        search=SearchCapabilities(tracks=True, artists=False, albums=False, playlists=False),
        metadata=MetadataRichness.LOW,
        supports_cover_art=False,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=False,
        supports_streaming=False,
        supports_downloads=True,
    ),
    'listenbrainz': ProviderCapabilities(
        name='listenbrainz',
        supports_playlists=PlaylistSupport.READ,
        search=SearchCapabilities(tracks=False, artists=False, albums=False, playlists=True),
        metadata=MetadataRichness.MEDIUM,
        supports_cover_art=False,
        supports_lyrics=False,
        supports_user_auth=False,
        supports_library_scan=False,
        supports_streaming=False,
        supports_downloads=False,
    ),
}


def get_provider_capabilities(provider: str) -> ProviderCapabilities:
    """Return capabilities for a provider key, raising KeyError if unknown."""
    return CAPABILITY_REGISTRY[provider]


# ==============================================================================
# 4. The Provider Registry
# ==============================================================================

class ProviderRegistry:
    """
    Central registry for all provider classes. Allows registration, lookup, and listing.
    Supports both bundled providers and community plugins with enable/disable functionality.
    """
    _providers: Dict[str, Type[ProviderBase]] = {}
    _provider_sources: Dict[str, str] = {}  # metadata: provider_name -> source_type
    _disabled_providers: set = set()

    @classmethod
    def get_providers_by_type(cls, provider_type: str, exclude_disabled: bool = True) -> List[str]:
        """
        Return a list of provider names matching the given type.
        provider_type: 'downloader', 'mediaserver', 'syncservice'
        """
        type_map = {
            'downloader': DownloaderProvider,
            'mediaserver': MediaServerProvider,
            'syncservice': SyncServiceProvider
        }
        base_type = type_map.get(provider_type.lower())
        if not base_type:
            raise ValueError(f"Unknown provider type: {provider_type}")

        providers = [name for name, cls_ in cls._providers.items() if issubclass(cls_, base_type)]
        if exclude_disabled:
            providers = [name for name in providers if name.lower() not in cls._disabled_providers]
        return providers

    @classmethod
    def create_instance_by_type(cls, provider_type: str, *args, **kwargs) -> List[ProviderBase]:
        """
        Instantiate all providers of a given type (excluding disabled ones).
        """
        names = cls.get_providers_by_type(provider_type, exclude_disabled=True)
        instances = []
        for name in names:
            try:
                instances.append(cls.create_instance(name, *args, **kwargs))
            except Exception as e:
                logger.error(f"Failed to instantiate provider '{name}': {e}")
        return instances

    @classmethod
    def register(cls, provider_cls: Type[ProviderBase], source_type: str = 'core'):
        """
        Register a provider class.

        Args:
            provider_cls: The class implementing ProviderBase.
            source_type: 'core' for bundled providers, 'community' for plugins.
        """
        name = getattr(provider_cls, 'name', None)
        if not name:
            raise ValueError("Provider class must have a 'name' attribute")
        cls._providers[name.lower()] = provider_cls
        cls._provider_sources[name.lower()] = source_type
        logger.debug(f"Registered provider '{name}' (source: {source_type})")

    @classmethod
    def get_provider_class(cls, name: str) -> Optional[Type[ProviderBase]]:
        return cls._providers.get(name.lower())

    @classmethod
    def list_providers(cls):
        return list(cls._providers.keys())

    @classmethod
    def get_provider_source(cls, name: str) -> Optional[str]:
        return cls._provider_sources.get(name.lower())

    @classmethod
    def create_instance(cls, name: str, *args, **kwargs) -> ProviderBase:
        if name.lower() in cls._disabled_providers:
            raise ValueError(f"Provider '{name}' is disabled")
        provider_cls = cls.get_provider_class(name)
        if not provider_cls:
            raise ValueError(f"Provider '{name}' not registered")
        return provider_cls(*args, **kwargs)

    @classmethod
    def get_download_clients(cls) -> List[str]:
        """
        Return a list of provider names that support downloads (excluding disabled ones).
        """
        clients = [name for name, cls_ in cls._providers.items() if getattr(cls_, 'supports_downloads', False)]
        return [name for name in clients if name.lower() not in cls._disabled_providers]

    @classmethod
    def disable_provider(cls, name: str) -> bool:
        if name.lower() in cls._providers:
            cls._disabled_providers.add(name.lower())
            logger.info(f"Provider '{name}' disabled. Restart required to unload.")
            return True
        return False

    @classmethod
    def enable_provider(cls, name: str) -> bool:
        if name.lower() in cls._providers:
            cls._disabled_providers.discard(name.lower())
            logger.info(f"Provider '{name}' enabled. Restart required to load.")
            return True
        return False

    @classmethod
    def is_provider_disabled(cls, name: str) -> bool:
        return name.lower() in cls._disabled_providers

    @classmethod
    def set_disabled_providers(cls, disabled_list: List[str]) -> None:
        cls._disabled_providers = set(name.lower() for name in disabled_list)
        if disabled_list:
            logger.info(f"Disabled providers: {', '.join(disabled_list)}")

    @classmethod
    def get_disabled_providers(cls) -> List[str]:
        return list(cls._disabled_providers)
