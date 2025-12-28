"""
Strict plugin-based architecture with explicit capability declarations.
Plugins NEVER assume other plugins exist. Plugins ONLY interact via declared provides/consumes.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Type
from enum import Enum
from utils.logging_config import get_logger

logger = get_logger("plugin_system")


# ============================================================================
# PLUGIN TYPE DEFINITIONS
# ============================================================================

class PluginType(Enum):
    """High-level roles for plugins."""
    PLAYLIST_SERVICE = "playlist_service"        # Spotify, TIDAL, YouTube Music
    SEARCH_PROVIDER = "search_provider"          # slskd search, torrent index, API search
    DOWNLOAD_CLIENT = "download_client"          # slskd, torrent client, direct HTTP
    METADATA_PROVIDER = "metadata_provider"      # MusicBrainz, AcoustID, Picard-like
    METADATA_ENHANCER = "metadata_enhancer"      # duration validation, quality detection
    LIBRARY_MANAGER = "library_manager"          # file moving, tagging, Plex integration
    PLAYER = "player"                             # optional playback
    AUTH_PROVIDER = "auth_provider"               # OAuth, token refresh, account management
    UTILITY = "utility"                           # logging, caching, rate-limit handling


class PluginScope(Enum):
    """Where the plugin operates."""
    LIBRARY = "library"                           # Local library operations
    SYNC = "sync"                                 # Playlist sync operations
    SEARCH = "search"                             # Search operations
    DOWNLOAD = "download"                         # Download operations
    PLAYBACK = "playback"                         # Playback operations
    UTILITY = "utility"                           # Utility operations


# ============================================================================
# METADATA CAPABILITIES (EXPLICIT FLAGS)
# ============================================================================

METADATA_CAPABILITIES = {
    # Track-level metadata
    "track.title",
    "track.artist",
    "track.album",
    "track.duration_ms",
    "track.track_number",
    "track.disc_number",
    "track.release_date",
    "track.isrc",
    "track.acoustid",
    
    # Album-level metadata
    "album.artist",
    "album.release_id",
    "album.type",  # album/single/ep
    
    # Audio technical metadata
    "audio.codec",
    "audio.container",
    "audio.bit_depth",
    "audio.sample_rate",
    "audio.bitrate",
    "audio.channels",
    "audio.is_lossless",
    "audio.source_confidence",  # official / rip / unknown
    
    # Playlist operations
    "playlist.read",
    "playlist.write",
    "playlist.sync",
    
    # Search capabilities
    "search.tracks",
    "search.artists",
    "search.albums",
    "search.playlists",
    
    # Download capabilities
    "download.http",
    "download.torrent",
    "download.p2p",
    
    # Library operations
    "library.scan",
    "library.file_move",
    "library.tag_write",
    "library.cover_art",
    
    # Auth operations
    "auth.oauth",
    "auth.token_refresh",
    "auth.credentials",
}


# ============================================================================
# PLUGIN DECLARATION
# ============================================================================

@dataclass
class PluginDeclaration:
    """Explicit plugin declaration with zero inference."""
    # Identity
    name: str                              # Unique plugin name (e.g., "spotify_client")
    plugin_type: PluginType                # High-level role
    
    # Capabilities
    provides: List[str] = field(default_factory=list)  # Capabilities this plugin provides
    consumes: List[str] = field(default_factory=list)  # Capabilities this plugin requires
    scope: List[PluginScope] = field(default_factory=list)  # Where this plugin operates
    
    # Metadata
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    
    # Instance & Config
    instance: Optional[Any] = None         # Actual plugin instance (set by registry)
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Validation
    enabled: bool = True
    priority: int = 0                      # Higher priority = preferred when multiple provide same capability
    
    def validate(self) -> bool:
        """Check that declared provides/consumes are valid capability names."""
        for cap in self.provides + self.consumes:
            if cap not in METADATA_CAPABILITIES:
                logger.warning(f"Plugin '{self.name}' declares unknown capability: {cap}")
                # Don't fail validation; just warn. Plugins may declare new capabilities.
        return True
    
    def to_dict(self) -> dict:
        """Serialize declaration to dict (for API responses)."""
        return {
            'name': self.name,
            'plugin_type': self.plugin_type.value,
            'provides': self.provides,
            'consumes': self.consumes,
            'scope': [s.value for s in self.scope],
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'enabled': self.enabled,
            'priority': self.priority,
        }


# ============================================================================
# PLUGIN REGISTRY
# ============================================================================

class PluginRegistry:
    """Central registry for all plugins. Manages loading, validation, and querying."""
    
    def __init__(self):
        self._plugins: Dict[str, PluginDeclaration] = {}
        self._by_type: Dict[PluginType, List[PluginDeclaration]] = {t: [] for t in PluginType}
        self._by_capability: Dict[str, List[PluginDeclaration]] = {}
    
    def register(self, declaration: PluginDeclaration) -> None:
        """Register a plugin with validation."""
        if not declaration.enabled:
            logger.debug(f"Skipping disabled plugin: {declaration.name}")
            return
        
        if declaration.name in self._plugins:
            logger.warning(f"Plugin '{declaration.name}' already registered; skipping duplicate")
            return
        
        # Validate declaration
        if not declaration.validate():
            logger.error(f"Plugin '{declaration.name}' validation failed")
            return
        
        # Store by name
        self._plugins[declaration.name] = declaration
        
        # Index by type
        self._by_type[declaration.plugin_type].append(declaration)
        
        # Index by capability (with priority sort)
        for cap in declaration.provides:
            if cap not in self._by_capability:
                self._by_capability[cap] = []
            self._by_capability[cap].append(declaration)
        
        # Sort by priority (descending)
        for cap in declaration.provides:
            self._by_capability[cap].sort(key=lambda p: p.priority, reverse=True)
        
        logger.info(f"✓ Registered plugin: {declaration.name} ({declaration.plugin_type.value})")
    
    def get_plugin(self, name: str) -> Optional[PluginDeclaration]:
        """Get plugin by name."""
        return self._plugins.get(name)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginDeclaration]:
        """Get all plugins of a specific type."""
        return self._by_type.get(plugin_type, [])
    
    def get_plugins_by_scope(self, scope: PluginScope) -> List[PluginDeclaration]:
        """Get all plugins that operate in a specific scope."""
        return [p for p in self._plugins.values() if scope in p.scope]
    
    def get_provider_for_capability(self, capability: str) -> Optional[PluginDeclaration]:
        """Get highest-priority plugin providing a capability."""
        providers = self._by_capability.get(capability, [])
        return providers[0] if providers else None
    
    def get_providers_for_capability(self, capability: str) -> List[PluginDeclaration]:
        """Get all plugins providing a capability (sorted by priority)."""
        return self._by_capability.get(capability, [])
    
    def list_all(self) -> List[PluginDeclaration]:
        """Get all registered plugins."""
        return list(self._plugins.values())
    
    def list_all_dict(self) -> List[dict]:
        """Get all registered plugins as dicts (for API responses)."""
        return [p.to_dict() for p in self._plugins.values()]
    
    def validate_capability_chain(self, required_caps: List[str]) -> bool:
        """Check if all required capabilities are provided by registered plugins."""
        for cap in required_caps:
            if not self.get_provider_for_capability(cap):
                logger.warning(f"No plugin provides capability: {cap}")
                return False
        return True
    
    def get_missing_capabilities(self, required_caps: List[str]) -> List[str]:
        """Return list of required capabilities not provided by any plugin."""
        missing = []
        for cap in required_caps:
            if not self.get_provider_for_capability(cap):
                missing.append(cap)
        return missing


# ============================================================================
# GLOBAL REGISTRY INSTANCE
# ============================================================================

plugin_registry = PluginRegistry()


def register_plugin(declaration: PluginDeclaration) -> None:
    """Convenience function to register a plugin globally."""
    plugin_registry.register(declaration)


def get_plugin(name: str) -> Optional[PluginDeclaration]:
    """Convenience function to get a plugin by name."""
    return plugin_registry.get_plugin(name)
