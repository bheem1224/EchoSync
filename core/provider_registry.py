from typing import Dict, Type, List
from core.provider_base import ProviderBase
from core.provider_types import DownloaderProvider, MediaServerProvider, SyncServiceProvider

class ProviderRegistry:
    """
    Central registry for all provider classes. Allows registration, lookup, and listing of available providers.
    """
    _providers: Dict[str, Type[ProviderBase]] = {}
    @classmethod
    def get_providers_by_type(cls, provider_type: str) -> List[str]:
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
        return [name for name, cls_ in cls._providers.items() if issubclass(cls_, base_type)]

    @classmethod
    def create_instance_by_type(cls, provider_type: str, *args, **kwargs) -> List[ProviderBase]:
        """
        Instantiate all providers of a given type.
        """
        names = cls.get_providers_by_type(provider_type)
        return [cls.create_instance(name, *args, **kwargs) for name in names]

    @classmethod
    def register(cls, provider_cls: Type[ProviderBase]):
        name = getattr(provider_cls, 'name', None)
        if not name:
            raise ValueError("Provider class must have a 'name' attribute")
        cls._providers[name.lower()] = provider_cls

    @classmethod
    def get_provider_class(cls, name: str) -> Type[ProviderBase]:
        return cls._providers.get(name.lower())

    @classmethod
    def list_providers(cls):
        return list(cls._providers.keys())

    @classmethod
    def create_instance(cls, name: str, *args, **kwargs) -> ProviderBase:
        provider_cls = cls.get_provider_class(name)
        if not provider_cls:
            raise ValueError(f"Provider '{name}' not registered")
        return provider_cls(*args, **kwargs)


# Register all provider clients for plugin discovery
from providers.spotify.client import SpotifyClient
from providers.tidal.client import TidalClient
from providers.soulseek.client import SoulseekClient
from providers.plex.client import PlexClient
from providers.jellyfin.client import JellyfinClient
from providers.navidrome.client import NavidromeClient
ProviderRegistry.register(SpotifyClient)
ProviderRegistry.register(TidalClient)
ProviderRegistry.register(SoulseekClient)
ProviderRegistry.register(PlexClient)
ProviderRegistry.register(JellyfinClient)
ProviderRegistry.register(NavidromeClient)
