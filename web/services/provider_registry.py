from typing import List, Optional, Dict
from plugins.plugin_system import plugin_registry
from core.provider_capabilities import get_provider_capabilities as fetch_capabilities

# Instance for direct access (for backward compatibility and testing)
class ProviderRegistry:
    """Wrapper class for provider registry functions."""
    
    def list_all(self):
        """List all providers."""
        return list_providers()
    
    def get_provider(self, provider_name: str):
        """Get a specific provider."""
        return get_provider(provider_name)

provider_registry = ProviderRegistry()

def list_providers() -> List[Dict]:
    """List all registered providers with enriched capability metadata."""
    providers = []
    for plugin in plugin_registry.list_all():
        plugin_dict = plugin.to_dict()
        try:
            caps = fetch_capabilities(plugin.name)
            plugin_dict['metadata_richness'] = caps.metadata.name
            plugin_dict['supports_streaming'] = caps.supports_streaming
            plugin_dict['supports_downloads'] = caps.supports_downloads
            plugin_dict['supports_cover_art'] = caps.supports_cover_art
            plugin_dict['supports_library_scan'] = caps.supports_library_scan
            plugin_dict['playlist_support'] = caps.supports_playlists.name if caps.supports_playlists else 'NONE'
            plugin_dict['search_capabilities'] = {
                'tracks': caps.search.tracks,
                'artists': caps.search.artists,
                'albums': caps.search.albums,
                'playlists': caps.search.playlists,
            }
        except KeyError:
            # Provider not in capability registry, use defaults
            plugin_dict['metadata_richness'] = 'MEDIUM'
            plugin_dict['supports_streaming'] = False
            plugin_dict['supports_downloads'] = False
            plugin_dict['supports_cover_art'] = False
            plugin_dict['supports_library_scan'] = False
            plugin_dict['playlist_support'] = 'NONE'
            plugin_dict['search_capabilities'] = {'tracks': False, 'artists': False, 'albums': False, 'playlists': False}
        providers.append(plugin_dict)
    return providers

def get_providers_for_capability(capability: str) -> List[Dict]:
    """Get providers that support a specific capability."""
    providers = []
    for plugin in plugin_registry.get_providers_for_capability(capability):
        providers.append(plugin.to_dict())
    return providers

def get_provider(provider_name: str) -> Optional[Dict]:
    """Get a specific provider by name."""
    plugin = plugin_registry.get_plugin(provider_name)
    if plugin:
        return plugin.to_dict()
    return None
def get_provider_capabilities() -> List[Dict]:
    """Expose capability flags for each provider."""
    capabilities = []
    for plugin in plugin_registry.list_all():
        try:
            caps = fetch_capabilities(plugin.name)
            capabilities.append({
                'name': plugin.name,
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
                'name': plugin.name,
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
