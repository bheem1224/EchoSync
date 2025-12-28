from typing import Dict, Type
from utils.logging_config import get_logger

logger = get_logger("adapter_registry")

class AdapterRegistry:
    """
    Central registry for ProviderAdapter classes.
    Allows registration, lookup, and instantiation.
    """
    _adapters: Dict[str, Type] = {}

    @classmethod
    def register(cls, name: str, adapter_cls: Type):
        if not name:
            raise ValueError("Adapter must have a name")
        cls._adapters[name.lower()] = adapter_cls

    @classmethod
    def get_adapter_class(cls, name: str):
        return cls._adapters.get(name.lower())

    @classmethod
    def list_adapters(cls):
        return list(cls._adapters.keys())

    @classmethod
    def create_instance(cls, name: str, *args, **kwargs):
        adapter_cls = cls.get_adapter_class(name)
        if not adapter_cls:
            raise ValueError(f"Adapter '{name}' not registered")
        instance = adapter_cls(*args, **kwargs)
        # AdapterRegistry manages runtime instances independently
        # PluginRegistry is ONLY for capability metadata
        return instance

# Register known adapters
try:
    from core.adapters.spotify_adapter import SpotifyAdapter
    AdapterRegistry.register("spotify", SpotifyAdapter)
except Exception as e:
    logger.debug(f"SpotifyAdapter registration deferred: {e}")

try:
    from core.adapters.tidal_adapter import TidalAdapter
    AdapterRegistry.register("tidal", TidalAdapter)
except Exception as e:
    logger.debug(f"TidalAdapter registration deferred: {e}")

try:
    from core.adapters.plex_adapter import PlexAdapter
    AdapterRegistry.register("plex", PlexAdapter)
except Exception as e:
    logger.debug(f"PlexAdapter registration deferred: {e}")

try:
    from core.adapters.jellyfin_adapter import JellyfinAdapter
    AdapterRegistry.register("jellyfin", JellyfinAdapter)
except Exception as e:
    logger.debug(f"JellyfinAdapter registration deferred: {e}")

try:
    from core.adapters.navidrome_adapter import NavidromeAdapter
    AdapterRegistry.register("navidrome", NavidromeAdapter)
except Exception as e:
    logger.debug(f"NavidromeAdapter registration deferred: {e}")

try:
    from core.adapters.soulseek_adapter import SoulseekAdapter
    AdapterRegistry.register("soulseek", SoulseekAdapter)
except Exception as e:
    logger.debug(f"SoulseekAdapter registration deferred: {e}")

try:
    from core.adapters.listenbrainz_adapter import ListenBrainzAdapter
    AdapterRegistry.register("listenbrainz", ListenBrainzAdapter)
except Exception as e:
    logger.debug(f"ListenBrainzAdapter registration deferred: {e}")
