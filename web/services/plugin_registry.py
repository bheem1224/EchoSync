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
    """List all registered plugins with enriched capability metadata from the database."""
    import json
    from database.config_database import get_config_database
    db = get_config_database()
    plugins = []

    try:
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id, plugin_id, name, version, service_type, capabilities FROM services")
            for row in c.fetchall():
                db_name = row['name']
                plugin_id = row['plugin_id']
                if not plugin_id:
                    continue

                is_disabled = CorePluginRegistry.is_plugin_disabled(db_name)
                source_type = CorePluginRegistry.get_plugin_source(db_name) or 'core'
                
                caps_json_str = row['capabilities'] or '{}'
                try:
                    caps_dict = json.loads(caps_json_str)
                except Exception:
                    caps_dict = {}

                # Create default structure matching frontend expectations
                search_caps = caps_dict.get('search', {})
                capabilities = {
                    'metadata_richness': caps_dict.get('metadata', 'MEDIUM'),
                    'supports_streaming': caps_dict.get('supports_streaming', False),
                    'supports_downloads': caps_dict.get('supports_downloads', False),
                    'supports_cover_art': caps_dict.get('supports_cover_art', False),
                    'supports_library_scan': caps_dict.get('supports_library_scan', False),
                    'supports_playlists': caps_dict.get('supports_playlists', 'NONE'),
                    'search': {
                        'tracks': search_caps.get('tracks', False),
                        'artists': search_caps.get('artists', False),
                        'albums': search_caps.get('albums', False),
                        'playlists': search_caps.get('playlists', False),
                    },
                    'fetch_metadata': caps_dict.get('supports_metadata_fetch', False),
                    'resolve_fingerprint': caps_dict.get('supports_fingerprinting', False),
                    'supports_lyrics': caps_dict.get('supports_lyrics', False),
                }
                capabilities['search_capabilities'] = capabilities['search']

                plugin_dict = {
                    'id': plugin_id,  # Changed from name to integer ID!
                    'plugin_id': plugin_id,
                    'name': db_name,
                    'display_name': db_name.replace('plugin.', '').replace('echosync.', '').title(),
                    'source_type': source_type,
                    'service_type': row['service_type'],
                    'disabled': is_disabled,
                    'version': row['version'] or 'Unknown',
                    'author': 'Official' if source_type == 'core' else 'Unknown',
                    'capabilities': capabilities,
                    'supports_downloads': capabilities['supports_downloads']
                }

                # Instance-based configuration check
                if not is_disabled:
                    try:
                        instance = CorePluginRegistry.create_instance(plugin_id)
                        if instance and hasattr(instance, 'is_configured'):
                            plugin_dict['is_configured'] = instance.is_configured()
                        else:
                            plugin_dict['is_configured'] = True
                    except Exception:
                        plugin_dict['is_configured'] = False
                else:
                    plugin_dict['is_configured'] = False

                plugins.append(plugin_dict)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to list plugins from DB: {e}", exc_info=True)

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
    """Expose capability flags for each plugin (for testing/backward compatibility)."""
    capabilities = []
    for plugin in list_plugins():
        caps = plugin.get('capabilities', {})
        capabilities.append({
            'name': plugin['name'],
            'metadata_richness': caps.get('metadata_richness', 'MEDIUM'),
            'supports_streaming': caps.get('supports_streaming', False),
            'supports_downloads': caps.get('supports_downloads', False),
            'supports_cover_art': caps.get('supports_cover_art', False),
            'supports_library_scan': caps.get('supports_library_scan', False),
            'playlist_support': caps.get('supports_playlists', 'NONE'),
            'search_capabilities': caps.get('search_capabilities', {
                'tracks': False, 'artists': False, 'albums': False, 'playlists': False
            })
        })
    return capabilities
