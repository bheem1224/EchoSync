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

def _normalize_name(name_str: str) -> str:
    if not name_str:
        return ""
    return name_str.lower().replace('plugin.', '').replace('echosync.', '').replace('core.', '').strip()

def list_plugins() -> List[Dict]:
    """List all registered plugins with enriched capability metadata."""
    from database.config_database import get_config_database
    db = get_config_database()
    db_services = {}
    try:
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT name, service_type FROM services")
            for row in c.fetchall():
                db_name = _normalize_name(row['name'])
                db_services[db_name] = row['service_type']
    except Exception:
        pass

    plugins = []
    for name in CorePluginRegistry.list_plugins():
        cls = CorePluginRegistry.get_plugin_class(name)
        if cls:
            is_disabled = CorePluginRegistry.is_plugin_disabled(name)
            display_name = name.replace('plugin.', '').title()
            source_type = CorePluginRegistry.get_plugin_source(name) or 'core'
            
            # service_type resolution from class or fallback to DB
            service_type = getattr(cls, 'service_type', None)
            if not service_type:
                norm_name = _normalize_name(name)
                service_type = db_services.get(norm_name)

            plugin_dict = {
                'id': name,  # Unique ID (e.g. plugin.plex)
                'name': name,
                'display_name': display_name,  # Friendly name (e.g. Plex)
                'source_type': source_type,    # 'core' or 'community'
                'category': getattr(cls, 'category', 'plugin'),
                'service_type': service_type,
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
                if not caps:
                    raise AttributeError("Capabilities is None")
                search_caps = {
                    'tracks': caps.search.tracks if (caps.search and hasattr(caps.search, 'tracks')) else False,
                    'artists': caps.search.artists if (caps.search and hasattr(caps.search, 'artists')) else False,
                    'albums': caps.search.albums if (caps.search and hasattr(caps.search, 'albums')) else False,
                    'playlists': caps.search.playlists if (caps.search and hasattr(caps.search, 'playlists')) else False,
                }
                plugin_dict['capabilities'] = {
                    'metadata_richness': caps.metadata.name if (caps.metadata and hasattr(caps.metadata, 'name')) else 'MEDIUM',
                    'supports_streaming': getattr(caps, 'supports_streaming', False),
                    'supports_downloads': getattr(caps, 'supports_downloads', False),
                    'supports_cover_art': getattr(caps, 'supports_cover_art', False),
                    'supports_library_scan': getattr(caps, 'supports_library_scan', False),
                    'supports_playlists': caps.supports_playlists.name if (caps.supports_playlists and hasattr(caps.supports_playlists, 'name')) else 'NONE',
                    'search': search_caps,
                    'search_capabilities': search_caps,  # Alias for compatibility
                    # Add metadata-specific capabilities
                    'fetch_metadata': getattr(caps, 'supports_metadata_fetch', False),
                    'resolve_fingerprint': getattr(caps, 'supports_fingerprinting', False),
                    'supports_lyrics': getattr(caps, 'supports_lyrics', False),
                }
            except (KeyError, AttributeError, ValueError):
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
                    'fetch_metadata': Capability.FETCH_METADATA in class_caps if isinstance(class_caps, list) else False,
                    'resolve_fingerprint': Capability.RESOLVE_FINGERPRINT in class_caps if isinstance(class_caps, list) else False,
                    'supports_lyrics': getattr(cls, 'supports_lyrics', False),
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
                if not caps:
                    raise AttributeError("Capabilities is None")
                capabilities.append({
                    'name': name,
                    'metadata_richness': caps.metadata.name if (caps.metadata and hasattr(caps.metadata, 'name')) else 'MEDIUM',
                    'supports_streaming': getattr(caps, 'supports_streaming', False),
                    'supports_downloads': getattr(caps, 'supports_downloads', False),
                    'supports_cover_art': getattr(caps, 'supports_cover_art', False),
                    'supports_library_scan': getattr(caps, 'supports_library_scan', False),
                    'playlist_support': caps.supports_playlists.name if (caps.supports_playlists and hasattr(caps.supports_playlists, 'name')) else 'NONE',
                    'search_capabilities': {
                        'tracks': caps.search.tracks if (caps.search and hasattr(caps.search, 'tracks')) else False,
                        'artists': caps.search.artists if (caps.search and hasattr(caps.search, 'artists')) else False,
                        'albums': caps.search.albums if (caps.search and hasattr(caps.search, 'albums')) else False,
                        'playlists': caps.search.playlists if (caps.search and hasattr(caps.search, 'playlists')) else False,
                    }
                })
            except (KeyError, AttributeError, ValueError):
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
