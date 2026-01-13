from typing import Dict, Type, List, Optional
from core.provider_base import ProviderBase
from core.provider_types import DownloaderProvider, MediaServerProvider, SyncServiceProvider
from utils.logging_config import get_logger

logger = get_logger("provider_registry")

class ProviderRegistry:
    """
    Central registry for all provider classes. Allows registration, lookup, and listing of available providers.
    Supports both bundled providers and community plugins with enable/disable functionality.
    """
    _providers: Dict[str, Type[ProviderBase]] = {}
    _provider_sources: Dict[str, str] = {}  # metadata: provider_name -> source_type
    _disabled_providers: set = set()  # Providers/plugins to skip at startup

    @classmethod
    def get_providers_by_type(cls, provider_type: str, exclude_disabled: bool = True) -> List[str]:
        """
        Return a list of provider names matching the given type.
        provider_type: 'downloader', 'mediaserver', 'syncservice'
        exclude_disabled: If True, skip disabled providers
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

    # Added method to filter providers by 'supports_downloads'
    @classmethod
    def get_download_clients(cls) -> List[str]:
        """
        Return a list of provider names that support downloads (excluding disabled ones).
        """
        clients = [name for name, cls_ in cls._providers.items() if getattr(cls_, 'supports_downloads', False)]
        return [name for name in clients if name.lower() not in cls._disabled_providers]

    @classmethod
    def disable_provider(cls, name: str) -> bool:
        """
        Disable a provider/plugin by name. Requires app restart to take effect.
        Returns True if provider was disabled, False if not found.
        """
        if name.lower() in cls._providers:
            cls._disabled_providers.add(name.lower())
            logger.info(f"Provider '{name}' disabled. Restart required to unload.")
            return True
        return False

    @classmethod
    def enable_provider(cls, name: str) -> bool:
        """
        Enable a previously disabled provider/plugin by name.
        Returns True if provider was enabled, False if not found.
        """
        if name.lower() in cls._providers:
            cls._disabled_providers.discard(name.lower())
            logger.info(f"Provider '{name}' enabled. Restart required to load.")
            return True
        return False

    @classmethod
    def is_provider_disabled(cls, name: str) -> bool:
        """
        Check if a provider/plugin is disabled.
        """
        return name.lower() in cls._disabled_providers

    @classmethod
    def set_disabled_providers(cls, disabled_list: List[str]) -> None:
        """
        Set the list of disabled providers from config.
        Called during startup to load disable list from settings.
        """
        cls._disabled_providers = set(name.lower() for name in disabled_list)
        if disabled_list:
            logger.info(f"Disabled providers: {', '.join(disabled_list)}")

    @classmethod
    def get_disabled_providers(cls) -> List[str]:
        """
        Get list of currently disabled providers.
        """
        return list(cls._disabled_providers)
