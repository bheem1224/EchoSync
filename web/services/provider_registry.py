from typing import List, Optional, Dict
from core.provider import ProviderRegistry as CoreProviderRegistry
from core.provider import get_provider_capabilities as fetch_capabilities

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
    for name in CoreProviderRegistry.list_providers():
        cls = CoreProviderRegistry.get_provider_class(name)
        if cls:
            is_disabled = CoreProviderRegistry.is_provider_disabled(name)
            provider_dict = {
                'id': name,  # Add id field for frontend
                'name': name,
                'display_name': name.title(),  # Add display name
                'category': getattr(cls, 'category', 'provider'),
                'service_type': getattr(cls, 'service_type', None),  # Add service_type
                'disabled': is_disabled,
                'supports_downloads': getattr(cls, 'supports_downloads', False)
            }
            
            # Only instantiate if the provider is not disabled; this avoids
            # configuration warnings and unnecessary health checks for
            # disabled plugins.
            if not is_disabled:
                try:
                    instance = CoreProviderRegistry.create_instance(name)
                    if instance and hasattr(instance, 'is_configured'):
                        provider_dict['is_configured'] = instance.is_configured()
                    else:
                        provider_dict['is_configured'] = True  # Assume configured if method not available
                except Exception:
                    provider_dict['is_configured'] = False
            else:
                provider_dict['is_configured'] = False
            
            try:
                caps = fetch_capabilities(name)
                search_caps = {
                    'tracks': caps.search.tracks,
                    'artists': caps.search.artists,
                    'albums': caps.search.albums,
                    'playlists': caps.search.playlists,
                }
                provider_dict['capabilities'] = {
                    'metadata_richness': caps.metadata.name,
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
                # Provider not in capability registry, check class-level capabilities
                from core.enums import Capability
                class_caps = getattr(cls, 'capabilities', [])
                
                default_search = {'tracks': False, 'artists': False, 'albums': False, 'playlists': False}
                provider_dict['capabilities'] = {
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
            providers.append(provider_dict)
    return providers

def get_providers_for_capability(capability: str) -> List[Dict]:
    """Get providers that support a specific capability."""
    providers = []
    # Filter by capability and also exclude disabled providers
    for provider in list_providers():
        if provider.get('disabled'):
            continue
        caps = provider.get('capabilities') or {}
        # simple check: provider must either support playlists/search/etc.
        # this helper is mostly used by the frontend so keep it lightweight
        if caps.get('supports_playlists') != 'NONE' or caps.get('search', {}).get('tracks'):
            providers.append(provider)
    return providers

def get_provider(provider_name: str) -> Optional[Dict]:
    """Get a specific provider by name."""
    cls = CoreProviderRegistry.get_provider_class(provider_name)
    if cls:
        return {
            'name': provider_name,
            'category': getattr(cls, 'category', 'provider'),
            'disabled': CoreProviderRegistry.is_provider_disabled(provider_name),
            'supports_downloads': getattr(cls, 'supports_downloads', False)
        }
    return None

def get_provider_capabilities() -> List[Dict]:
    """Expose capability flags for each provider."""
    capabilities = []
    for name in CoreProviderRegistry.list_providers():
        cls = CoreProviderRegistry.get_provider_class(name)
        if cls:
            try:
                caps = fetch_capabilities(name)
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
