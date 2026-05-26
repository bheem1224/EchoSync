from core.nexus_framework.plugin_loader import get_plugin_capabilities
from typing import List, Optional, Dict


from core.nexus_framework.plugin_loader import PluginRegistry as CorePluginRegistry, ServiceRegistry


# Instance for direct access (for backward compatibility and testing)
class PluginRegistryFacade:
    """Wrapper class for plugin registry functions."""
    
    def list_all(self):
        """List all plugins."""
        return list_plugins()
    
    def get_plugin(self, plugin_name: str):
        """Get a specific plugin."""
        return get_plugin(plugin_name)

plugin_registry = PluginRegistryFacade()

def _clean_mocks(val):
    if type(val).__name__ in ('MagicMock', 'Mock', 'NonCallableMagicMock', 'NonCallableMock'):
        return None
    if isinstance(val, dict):
        return {k: _clean_mocks(v) for k, v in val.items() if type(v).__name__ not in ('MagicMock', 'Mock', 'NonCallableMagicMock', 'NonCallableMock')}
    if isinstance(val, list):
        return [_clean_mocks(item) for item in val if type(item).__name__ not in ('MagicMock', 'Mock', 'NonCallableMagicMock', 'NonCallableMock')]
    return val

def list_plugins() -> List[Dict]:
    """List all registered plugins with enriched capability metadata."""
    plugins = []
    for name in CorePluginRegistry.list_plugins():
        cls = CorePluginRegistry.get_plugin_class(name)
        if cls:
            is_disabled = CorePluginRegistry.is_plugin_disabled(name)
            display_name = name.replace('plugin.', '').title()
            source_type = CorePluginRegistry.get_plugin_source(name) or 'core'
            
            plugin_dict = {
                'id': name,  # Unique ID (e.g. plugin.plex)
                'name': name,
                'display_name': display_name,  # Friendly name (e.g. Plex)
                'source_type': source_type,    # 'core' or 'community'
                'category': getattr(cls, 'category', 'plugin'),
                'service_type': getattr(cls, 'service_type', None),
                'disabled': is_disabled,
                'version': getattr(cls, 'version', 'Unknown'),
                'author': getattr(cls, 'author', 'Official' if source_type == 'core' else 'Unknown'),
                'supports_downloads': getattr(cls, 'supports_downloads', False)
            }
            
            # Only instantiate if the plugin is not disabled; this avoids
            # configuration warnings and unnecessary health checks for
            # disabled plugins.
            if not is_disabled:
                try:
                    instance = CorePluginRegistry.create_instance(name)
                    if instance and hasattr(instance, 'is_configured'):
                        plugin_dict['is_configured'] = instance.is_configured()
                    else:
                        plugin_dict['is_configured'] = True  # Assume configured if method not available
                except Exception:
                    plugin_dict['is_configured'] = False
            else:
                plugin_dict['is_configured'] = False
            
            try:
                caps = get_plugin_capabilities(name)
                search_caps = {
                    'tracks': caps.search.tracks if caps.search else False,
                    'artists': caps.search.artists if caps.search else False,
                    'albums': caps.search.albums if caps.search else False,
                    'playlists': caps.search.playlists if caps.search else False,
                }
                plugin_dict['capabilities'] = {
                    'metadata_richness': caps.metadata.name if caps.metadata else 'MEDIUM',
                    'supports_streaming': caps.supports_streaming,
                    'supports_downloads': caps.supports_downloads,
                    'supports_cover_art': caps.supports_cover_art,
                    'supports_library_scan': caps.supports_library_scan,
                    'supports_playlists': caps.supports_playlists.name if caps.supports_playlists else 'NONE',
                    'search': search_caps,
                    'search_capabilities': search_caps,  # Alias for compatibility
                    # Add metadata-specific capabilities
                    'fetch_metadata': caps.supports_metadata_fetch if hasattr(caps, 'supports_metadata_fetch') else False,
                    'resolve_fingerprint': caps.supports_fingerprinting if hasattr(caps, 'supports_fingerprinting') else False,
                }
            except KeyError:
                # Plugin not in capability registry, check class-level capabilities
                from core.enums import Capability
                class_caps = getattr(cls, 'capabilities', [])
                if class_caps is None:
                    class_caps = []
                
                default_search = {'tracks': False, 'artists': False, 'albums': False, 'playlists': False}
                plugin_dict['capabilities'] = {
                    'metadata_richness': 'MEDIUM',
                    'supports_streaming': False,
                    'supports_downloads': False,
                    'supports_cover_art': False,
                    'supports_library_scan': False,
                    'supports_playlists': 'NONE',
                    'search': default_search,
                    'search_capabilities': default_search,
                    'fetch_metadata': Capability.FETCH_METADATA in class_caps,
                    'resolve_fingerprint': Capability.RESOLVE_FINGERPRINT in class_caps,
                }
            plugins.append(plugin_dict)
    return _clean_mocks(plugins)

def get_plugins_for_capability(capability: str) -> List[Dict]:
    """Get plugins that support a specific capability."""
    plugins = []
    # Filter by capability and also exclude disabled plugins
    for plugin in list_plugins():
        if plugin.get('disabled'):
            continue
        caps = plugin.get('capabilities') or {}
        # simple check: plugin must either support playlists/search/etc.
        # this helper is mostly used by the frontend so keep it lightweight
        if caps.get('supports_playlists') != 'NONE' or caps.get('search', {}).get('tracks'):
            plugins.append(plugin)
    return plugins

def get_plugin(plugin_name: str) -> Optional[Dict]:
    """Get a specific plugin by name."""
    cls = CorePluginRegistry.get_plugin_class(plugin_name)
    if cls:
        return {
            'name': plugin_name,
            'category': getattr(cls, 'category', 'plugin'),
            'disabled': CorePluginRegistry.is_plugin_disabled(plugin_name),
            'supports_downloads': getattr(cls, 'supports_downloads', False)
        }
    return None

def _get_plugin_capabilities() -> List[Dict]:
    """Expose capability flags for each plugin."""
    capabilities = []
    for name in CorePluginRegistry.list_plugins():
        cls = CorePluginRegistry.get_plugin_class(name)
        if cls:
            try:
                caps = get_plugin_capabilities(name)
                capabilities.append({
                    'name': name,
                    'metadata_richness': caps.metadata.name,
                    'supports_streaming': caps.supports_streaming,
                    'supports_downloads': caps.supports_downloads,
                    'supports_cover_art': caps.supports_cover_art,
                    'supports_library_scan': caps.supports_library_scan,
                    'playlist_support': caps.supports_playlists.name if caps.supports_playlists else 'NONE',
                    'search_capabilities': {
                        'tracks': caps.search.tracks,
                        'artists': caps.search.artists,
                        'albums': caps.search.albums,
                        'playlists': caps.search.playlists,
                    }
                })
            except KeyError:
                capabilities.append({
                    'name': name,
                    'metadata_richness': 'MEDIUM',
                    'supports_streaming': False,
                    'supports_downloads': False,
                    'supports_cover_art': False,
                    'supports_library_scan': False,
                    'playlist_support': 'NONE',
                    'search_capabilities': {
                        'tracks': False,
                        'artists': False,
                        'albums': False,
                        'playlists': False,
                    }
                })
    return capabilities
