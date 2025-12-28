"""
Strict plugin-based architecture with explicit, Track-centric declarations.

ARCHITECTURE RULES
- Plugins NEVER own data
- music_database is the ONLY persistent store
- Plugins only create track stubs, enrich fields, attach provider_refs, update status flags
- All Track operations go through music_database using the canonical Track model
- Zero inference: only declared fields may be populated
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Type, Set
from enum import Enum
from utils.logging_config import get_logger

logger = get_logger("plugin_system")


# ============================================================================
# PLUGIN TYPE DEFINITIONS (Data-flow roles)
# ============================================================================

class PluginType(Enum):
    """
    Plugin roles aligned to the Track data lifecycle.
    IMPORTANT: Plugins do NOT own data. They:
    - Create track stubs
    - Enrich missing fields
    - Attach provider_refs
    - Update status flags
    """
    PLAYLIST_PROVIDER = "playlist_provider"      # Creates track stubs from playlists (Spotify, TIDAL)
    SEARCH_PROVIDER = "search_provider"          # Finds download candidates (Soulseek)
    DOWNLOAD_CLIENT = "download_client"          # Attaches files / manages downloads
    METADATA_PROVIDER = "metadata_provider"      # Enriches tracks (MusicBrainz, AcousticID)
    LIBRARY_PROVIDER = "library_provider"        # Scans existing files (Plex, Jellyfin, Navidrome)
    PLAYER_PROVIDER = "player_provider"          # Playback only, no data writes
    UTILITY = "utility"                          # Logging, caching, helpers

    # --- Legacy aliases for migration compatibility ---
    PLAYLIST_SERVICE = "playlist_provider"       # Alias of PLAYLIST_PROVIDER
    LIBRARY_MANAGER = "library_provider"         # Alias of LIBRARY_PROVIDER


class PluginScope(Enum):
    """Where the plugin operates."""
    LIBRARY = "library"                           # Local library operations
    SYNC = "sync"                                 # Playlist sync operations
    SEARCH = "search"                             # Search operations
    DOWNLOAD = "download"                         # Download operations
    METADATA = "metadata"                         # Metadata enrichment operations
    PLAYBACK = "playback"                         # Playback operations
    UTILITY = "utility"                           # Utility operations


# ============================================================================
# CANONICAL TRACK FIELDS & LEGACY CAPABILITIES
# ============================================================================
TRACK_FIELDS: Set[str] = {
    # Core identity
    "track_id",
    # Basic metadata
    "title",
    "artists",
    "album",
    "duration_ms",
    # Global identifiers
    "isrc",
    "musicbrainz_recording_id",
    "acoustid",
    # Provider references
    "provider_refs",
    # Download management
    "download_status",
    "file_path",
    "file_format",
    "bitrate",
    # Quality & confidence
    "confidence_score",
    # Extended metadata
    "album_artist",
    "track_number",
    "disc_number",
    "release_year",
    "genres",
    # System fields
    "created_at",
    "updated_at",
}

# Legacy capability flags (kept for compatibility during migration)
METADATA_CAPABILITIES = {
    "track.title",
    "track.artist",
    "track.album",
    "track.duration_ms",
    "track.track_number",
    "track.disc_number",
    "track.release_date",
    "track.isrc",
    "track.acoustid",
    "album.artist",
    "album.release_id",
    "album.type",
    "audio.codec",
    "audio.container",
    "audio.bit_depth",
    "audio.sample_rate",
    "audio.bitrate",
    "audio.channels",
    "audio.is_lossless",
    "audio.source_confidence",
    "playlist.read",
    "playlist.write",
    "playlist.sync",
    "search.tracks",
    "search.artists",
    "search.albums",
    "search.playlists",
    "download.http",
    "download.torrent",
    "download.p2p",
    "library.scan",
    "library.file_move",
    "library.tag_write",
    "library.cover_art",
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
    
    # Track field contracts (preferred)
    provides_fields: List[str] = field(default_factory=list)   # Track fields this plugin can populate
    consumes_fields: List[str] = field(default_factory=list)   # Track fields this plugin requires
    requires_auth: bool = False                                # Does this plugin require auth?
    
    # Explicit capability flags
    supports_streaming: bool = False      # Can stream audio playback
    supports_downloads: bool = False      # Can download/acquire files
    supports_library_scan: bool = False   # Can scan existing library files
    supports_cover_art: bool = False      # Can fetch/provide cover art
    supports_lyrics: bool = False         # Can fetch/provide lyrics
    
    # Legacy capability flags (kept during migration)
    provides: List[str] = field(default_factory=list)          # Capabilities this plugin provides
    consumes: List[str] = field(default_factory=list)          # Capabilities this plugin requires
    
    # Scope
    scope: List[PluginScope] = field(default_factory=list)     # Where this plugin operates
    
    # Metadata
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    
    # Instance & Config
    instance: Optional[Any] = None         # DEPRECATED: Do not use. AdapterRegistry manages runtime instances.
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Validation
    enabled: bool = True
    priority: int = 0                      # Higher priority = preferred when multiple provide same capability

    def validate(self) -> bool:
        """Check that declared fields/capabilities are valid names."""
        # Validate Track fields
        for field_name in self.provides_fields + self.consumes_fields:
            if field_name not in TRACK_FIELDS:
                logger.warning(f"Plugin '{self.name}' declares unknown track field: {field_name}")
        # Legacy capability validation
        for cap in self.provides + self.consumes:
            if cap not in METADATA_CAPABILITIES:
                logger.warning(f"Plugin '{self.name}' declares unknown capability: {cap}")
        return True

    def to_dict(self) -> dict:
        """Serialize declaration to dict (for API responses)."""
        return {
            'name': self.name,
            'plugin_type': self.plugin_type.value,
            'provides_fields': self.provides_fields,
            'consumes_fields': self.consumes_fields,
            'requires_auth': self.requires_auth,
            'supports_streaming': self.supports_streaming,
            'supports_downloads': self.supports_downloads,
            'supports_library_scan': self.supports_library_scan,
            'supports_cover_art': self.supports_cover_art,
            'supports_lyrics': self.supports_lyrics,
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
        self._by_field: Dict[str, List[PluginDeclaration]] = {}
    
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

        # Index by provided Track fields (with priority sort)
        for field_name in declaration.provides_fields:
            if field_name not in self._by_field:
                self._by_field[field_name] = []
            self._by_field[field_name].append(declaration)
        for field_name in declaration.provides_fields:
            self._by_field[field_name].sort(key=lambda p: p.priority, reverse=True)
        
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

    def get_provider_for_field(self, field_name: str) -> Optional[PluginDeclaration]:
        """Get highest-priority plugin that can populate a Track field."""
        providers = self._by_field.get(field_name, [])
        return providers[0] if providers else None

    def get_providers_for_field(self, field_name: str) -> List[PluginDeclaration]:
        """Get all plugins that can populate a Track field (sorted by priority)."""
        return self._by_field.get(field_name, [])
    
    def list_all(self) -> List[PluginDeclaration]:
        """Get all registered plugins."""
        return list(self._plugins.values())
    
    def list_all_dict(self) -> List[dict]:
        """Get all registered plugins as dicts (for API responses)."""
        return [p.to_dict() for p in self._plugins.values()]

    def set_plugin_instance(self, name: str, instance: Any) -> bool:
        """
        DEPRECATED: PluginRegistry should NOT store runtime instances.
        Use AdapterRegistry.create_instance() instead.
        
        PluginRegistry is for capability discovery (what plugins exist, what they can do).
        AdapterRegistry is for runtime execution (creating instances, running operations).
        """
        logger.warning(
            f"set_plugin_instance() is deprecated. "
            f"Use AdapterRegistry.create_instance('{name}') for runtime instances."
        )
        return False
    
    def validate_capability_chain(self, required_caps: List[str]) -> bool:
        """Check if all required capabilities are provided by registered plugins."""
        for cap in required_caps:
            if not self.get_provider_for_capability(cap):
                logger.warning(f"No plugin provides capability: {cap}")
                return False
        return True

    def get_missing_fields(self, required_fields: List[str]) -> List[str]:
        """Return list of Track fields not provided by any plugin."""
        missing = []
        for field_name in required_fields:
            if not self.get_provider_for_field(field_name):
                missing.append(field_name)
        return missing
    
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
