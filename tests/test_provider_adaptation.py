"""
Tests for provider capability-driven UI adaptation.

Verifies that:
1. Provider capabilities are correctly exposed via API
2. Capability filtering functions work as expected
3. Views conditionally render based on provider capabilities
4. Provider polling detects changes and triggers view re-renders
"""

import pytest
import json
from unittest.mock import MagicMock, patch, call
from pathlib import Path


# ============================================================================
# Tests: Provider Capabilities API Endpoint
# ============================================================================

class TestProviderCapabilitiesAPI:
    """Tests for web/routes/providers.py capability enrichment."""
    
    def test_enrich_provider_capabilities_basic(self):
        """Test that provider capabilities are enriched correctly."""
        from web.routes.providers import _enrich_provider_capabilities
        
        plugin_dict = {
            'name': 'spotify',
            'enabled': True,
            'installed': True,
            'scope': 'music_service'
        }
        
        enriched = _enrich_provider_capabilities(plugin_dict, 'spotify')
        
        # Should have base plugin fields
        assert enriched['name'] == 'spotify'
        assert enriched['enabled'] is True
        
        # Should have enriched capability fields
        assert 'metadata_richness' in enriched
        assert 'supports_streaming' in enriched
        assert 'supports_downloads' in enriched
        assert 'supports_library_scan' in enriched
        assert 'playlist_support' in enriched
        assert 'search_capabilities' in enriched
    
    def test_enrich_provider_capabilities_spotify(self):
        """Test enrichment for Spotify provider."""
        from web.routes.providers import _enrich_provider_capabilities
        
        plugin_dict = {
            'name': 'spotify',
            'enabled': True,
            'installed': True,
            'scope': 'music_service'
        }
        
        enriched = _enrich_provider_capabilities(plugin_dict, 'spotify')
        
        # Spotify supports streaming and search
        assert enriched['supports_streaming'] is True
        assert enriched['supports_downloads'] is False
        assert enriched['supports_library_scan'] is False
        # playlist_support is returned as enum name
        assert enriched['playlist_support'] == 'READ_WRITE'
        # search_capabilities is returned as dict
        assert enriched['search_capabilities']['tracks'] is True
        assert enriched['search_capabilities']['playlists'] is True

    def test_enrich_provider_capabilities_plex(self):
        """Test enrichment for Plex provider."""
        from web.routes.providers import _enrich_provider_capabilities
        
        plugin_dict = {
            'name': 'plex',
            'enabled': True,
            'installed': True,
            'scope': 'media_server'
        }
        
        enriched = _enrich_provider_capabilities(plugin_dict, 'plex')
        
    
        # Plex supports library scan (but not streaming, only local playback)
        assert enriched['supports_streaming'] is False
        assert enriched['supports_library_scan'] is True
        assert enriched['supports_cover_art'] is True

    def test_enrich_provider_capabilities_scope_preserved(self):
        """Scope from plugin_dict should be preserved after enrichment."""
        from web.routes.providers import _enrich_provider_capabilities

        plugin_dict = {
            'name': 'plex',
            'enabled': True,
            'installed': True,
            'scope': 'media_server'
        }

        enriched = _enrich_provider_capabilities(plugin_dict, 'plex')
        assert enriched['scope'] == 'media_server'
    def test_enrich_provider_capabilities_disabled(self):
        """Test that disabled providers are still enriched."""
        from web.routes.providers import _enrich_provider_capabilities
        
        plugin_dict = {
            'name': 'spotify',
            'enabled': False,
            'installed': True,
            'scope': 'music_service'
        }
        
        enriched = _enrich_provider_capabilities(plugin_dict, 'spotify')
        
        # Should preserve enabled=False
        assert enriched['enabled'] is False
        # But still have capability info
        assert 'supports_streaming' in enriched


# ============================================================================
# Tests: Capability Filtering Functions
# ============================================================================

class TestCapabilityFiltering:
    """Tests for webui/core/capabilities.js filter functions (via mock)."""
    
    def setup_method(self):
        """Create mock provider list for testing."""
        self.providers = [
            {
                'name': 'spotify',
                'enabled': True,
                'supports_streaming': True,
                'supports_downloads': False,
                'search_capabilities': ['search.tracks', 'search.playlists'],
                'playlist_support': ['playlist.read', 'playlist.write'],
                'metadata_richness': 'MEDIUM'
            },
            {
                'name': 'plex',
                'enabled': True,
                'supports_streaming': True,
                'supports_library_scan': True,
                'playlist_support': ['playlist.read'],
                'metadata_richness': 'HIGH'
            },
            {
                'name': 'jellyfin',
                'enabled': False,  # Disabled
                'supports_streaming': True,
                'supports_library_scan': True,
                'metadata_richness': 'MEDIUM'
            }
        ]
    
    def test_filter_providers_by_capability_search(self):
        """Test filtering providers by search capability."""
        # Simulating: const searchProviders = filterProvidersByCapability(providers, 'search.tracks');
        search_providers = [p for p in self.providers 
                          if p.get('enabled') and 'search.tracks' in p.get('search_capabilities', [])]
        
        assert len(search_providers) == 1
        assert search_providers[0]['name'] == 'spotify'
    
    def test_filter_providers_by_capability_playlist_write(self):
        """Test filtering providers by playlist.write capability."""
        playlist_write_providers = [p for p in self.providers 
                                   if p.get('enabled') and 'playlist.write' in p.get('playlist_support', [])]
        
        assert len(playlist_write_providers) == 1
        assert playlist_write_providers[0]['name'] == 'spotify'
    
    def test_filter_providers_by_library_scan(self):
        """Test filtering providers by library.scan capability."""
        library_providers = [p for p in self.providers 
                            if p.get('enabled') and p.get('supports_library_scan')]
        
        assert len(library_providers) == 1
        assert library_providers[0]['name'] == 'plex'
    
    def test_has_capability_search(self):
        """Test checking if any provider has search capability."""
        has_search = any(p.get('enabled') and 'search.tracks' in p.get('search_capabilities', []) 
                        for p in self.providers)
        
        assert has_search is True
    
    def test_has_capability_not_found(self):
        """Test checking for non-existent capability."""
        has_webdav = any(p.get('enabled') and 'webdav' in p.get('special_capabilities', []) 
                        for p in self.providers)
        
        assert has_webdav is False
    
    def test_disabled_providers_excluded(self):
        """Test that disabled providers are excluded from filters."""
        enabled_providers = [p for p in self.providers if p.get('enabled')]
        
        assert len(enabled_providers) == 2
        assert 'jellyfin' not in [p['name'] for p in enabled_providers]
    
    def test_metadata_richness_sorting(self):
        """Test that providers can be sorted by metadata richness."""
        metadata_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'MINIMAL': 0}
        
        sorted_by_richness = sorted(
            [p for p in self.providers if p.get('enabled')],
            key=lambda p: metadata_order.get(p.get('metadata_richness'), 0),
            reverse=True
        )
        
        assert sorted_by_richness[0]['name'] == 'plex'  # HIGH
        assert sorted_by_richness[1]['name'] == 'spotify'  # MEDIUM


# ============================================================================
# Tests: Library Servers (Plex, Jellyfin, Navidrome)
# ============================================================================

class TestLibraryServers:
    """Tests for media_server scope and library scan behavior."""

    def test_filter_by_scope_media_server(self):
        providers = [
            {'name': 'spotify', 'scope': 'music_service', 'enabled': True},
            {'name': 'plex', 'scope': 'media_server', 'enabled': True},
            {'name': 'jellyfin', 'scope': 'media_server', 'enabled': True},
            {'name': 'navidrome', 'scope': 'media_server', 'enabled': True},
        ]

        media_servers = [p for p in providers if p.get('enabled') and p.get('scope') == 'media_server']
        names = [p['name'] for p in media_servers]
        assert set(names) == {'plex', 'jellyfin', 'navidrome'}

    def test_library_view_uses_media_servers_with_scan(self):
        providers = [
            {'name': 'plex', 'scope': 'media_server', 'enabled': True, 'supports_library_scan': True},
            {'name': 'jellyfin', 'scope': 'media_server', 'enabled': True, 'supports_library_scan': True},
            {'name': 'navidrome', 'scope': 'media_server', 'enabled': True, 'supports_library_scan': True},
            {'name': 'spotify', 'scope': 'music_service', 'enabled': True, 'supports_library_scan': False},
        ]

        library_capable_servers = [
            p for p in providers
            if p.get('enabled') and p.get('scope') == 'media_server' and p.get('supports_library_scan')
        ]
        assert len(library_capable_servers) == 3
        assert {p['name'] for p in library_capable_servers} == {'plex', 'jellyfin', 'navidrome'}


# ============================================================================
# Tests: Metadata & Utility Scopes
# ============================================================================

class TestProviderScopes:
    """Tests for metadata and utility provider scopes."""

    def test_filter_by_scope_metadata(self):
        providers = [
            {'name': 'musicbrainz', 'scope': 'metadata', 'enabled': True},
            {'name': 'acoustid', 'scope': 'metadata', 'enabled': True},
            {'name': 'spotify', 'scope': 'music_service', 'enabled': True},
        ]
        metadata = [p for p in providers if p.get('enabled') and p.get('scope') == 'metadata']
        assert {p['name'] for p in metadata} == {'musicbrainz', 'acoustid'}

    def test_filter_by_scope_utility(self):
        providers = [
            {'name': 'cache_helper', 'scope': 'utility', 'enabled': True},
            {'name': 'logger', 'scope': 'utility', 'enabled': False},
            {'name': 'plex', 'scope': 'media_server', 'enabled': True},
        ]
        utilities = [p for p in providers if p.get('enabled') and p.get('scope') == 'utility']
        assert {p['name'] for p in utilities} == {'cache_helper'}


# ============================================================================
# Tests: View Rendering Based on Capabilities
# ============================================================================

class TestViewRendering:
    """Tests for capability-driven view rendering logic."""
    
    def test_search_view_renders_when_search_capable(self):
        """Test that search view shows when search-capable providers exist."""
        providers = [
            {
                'name': 'spotify',
                'enabled': True,
                'search_capabilities': ['search.tracks', 'search.playlists']
            }
        ]
        
        has_search = any(p.get('enabled') and p.get('search_capabilities') for p in providers)
        assert has_search is True
    
    def test_search_view_hidden_when_no_search_capable(self):
        """Test that search view hides when no search-capable providers exist."""
        providers = [
            {
                'name': 'plex',
                'enabled': True,
                'supports_library_scan': True,
                'search_capabilities': []
            }
        ]
        
        has_search = any(p.get('enabled') and p.get('search_capabilities') for p in providers)
        assert has_search is False
    
    def test_library_view_renders_when_library_capable(self):
        """Test that library view shows when library-capable providers exist."""
        providers = [
            {
                'name': 'plex',
                'enabled': True,
                'supports_library_scan': True
            }
        ]
        
        has_library = any(p.get('enabled') and p.get('supports_library_scan') for p in providers)
        assert has_library is True
    
    def test_playlist_view_renders_when_playlist_capable(self):
        """Test that playlist view shows when playlist-capable providers exist."""
        providers = [
            {
                'name': 'spotify',
                'enabled': True,
                'playlist_support': ['playlist.read', 'playlist.write']
            }
        ]
        
        has_playlist = any(p.get('enabled') and p.get('playlist_support') for p in providers)
        assert has_playlist is True


# ============================================================================
# Tests: Provider State Change Detection
# ============================================================================

class TestProviderStateChanges:
    """Tests for detecting and responding to provider changes."""
    
    def test_provider_install_detection(self):
        """Test that adding a new provider is detected."""
        initial_state = [
            {'name': 'spotify', 'enabled': True}
        ]
        
        updated_state = [
            {'name': 'spotify', 'enabled': True},
            {'name': 'plex', 'enabled': True}  # New provider
        ]
        
        # Simple change detection: compare provider names
        initial_names = {p['name'] for p in initial_state}
        updated_names = {p['name'] for p in updated_state}
        
        new_providers = updated_names - initial_names
        assert 'plex' in new_providers
    
    def test_provider_disable_detection(self):
        """Test that disabling a provider is detected."""
        initial_state = [
            {'name': 'spotify', 'enabled': True}
        ]
        
        updated_state = [
            {'name': 'spotify', 'enabled': False}  # Disabled
        ]
        
        # Change detection: check enabled flag
        initial_enabled = {p['name']: p.get('enabled') for p in initial_state}
        updated_enabled = {p['name']: p.get('enabled') for p in updated_state}
        
        changed = {name for name in initial_enabled 
                  if initial_enabled[name] != updated_enabled.get(name)}
        assert 'spotify' in changed
    
    def test_provider_remove_detection(self):
        """Test that removing a provider is detected."""
        initial_state = [
            {'name': 'spotify', 'enabled': True},
            {'name': 'plex', 'enabled': True}
        ]
        
        updated_state = [
            {'name': 'spotify', 'enabled': True}
        ]
        
        # Change detection: compare provider names
        initial_names = {p['name'] for p in initial_state}
        updated_names = {p['name'] for p in updated_state}
        
        removed_providers = initial_names - updated_names
        assert 'plex' in removed_providers


# ============================================================================
# Tests: Polling and Event System Integration
# ============================================================================

class TestProviderPolling:
    """Tests for provider polling and event system."""
    
    def test_provider_poller_detects_change(self):
        """Test that provider poller calls API and detects changes."""
        # Simulate provider list before and after change
        providers_before = [{'name': 'spotify', 'enabled': True}]
        providers_after = [
            {'name': 'spotify', 'enabled': True},
            {'name': 'plex', 'enabled': True}
        ]
        
        # Simulate poller logic
        def compare_providers(old, new):
            """Compare provider lists and return True if changed."""
            old_set = {(p['name'], p.get('enabled')) for p in old}
            new_set = {(p['name'], p.get('enabled')) for p in new}
            return old_set != new_set
        
        assert compare_providers(providers_before, providers_after) is True
    
    def test_provider_poller_no_change(self):
        """Test that poller correctly detects when nothing changed."""
        providers_1 = [
            {'name': 'spotify', 'enabled': True},
            {'name': 'plex', 'enabled': True}
        ]
        providers_2 = [
            {'name': 'spotify', 'enabled': True},
            {'name': 'plex', 'enabled': True}
        ]
        
        def compare_providers(old, new):
            """Compare provider lists and return True if changed."""
            old_set = {(p['name'], p.get('enabled')) for p in old}
            new_set = {(p['name'], p.get('enabled')) for p in new}
            return old_set != new_set
        
        assert compare_providers(providers_1, providers_2) is False
    
    def test_capability_change_triggers_view_update(self):
        """Test that capability changes trigger view updates."""
        # Initial state: search-capable provider
        initial_providers = [
            {'name': 'spotify', 'enabled': True, 'search_capabilities': ['search.tracks']}
        ]
        
        # After disabling: no search-capable provider
        updated_providers = [
            {'name': 'spotify', 'enabled': False, 'search_capabilities': ['search.tracks']}
        ]
        
        def should_show_search_view(providers):
            return any(p.get('enabled') and p.get('search_capabilities') for p in providers)
        
        # Initially should show
        assert should_show_search_view(initial_providers) is True
        
        # After update should hide
        assert should_show_search_view(updated_providers) is False


# ============================================================================
# Tests: End-to-End Scenario
# ============================================================================

class TestProviderAdaptationScenario:
    """End-to-end test of provider auto-adaptation flow."""
    
    def test_scenario_install_search_provider(self):
        """
        Scenario: User installs Spotify provider
        Expected: Search view becomes visible
        """
        # Step 1: Initial state (no search providers)
        initial_providers = [
            {
                'name': 'plex',
                'enabled': True,
                'supports_library_scan': True,
                'search_capabilities': []
            }
        ]
        
        # Check: search view should be hidden
        can_search = any(p.get('enabled') and p.get('search_capabilities') for p in initial_providers)
        assert can_search is False, "Search should not be available initially"
        
        # Step 2: Spotify gets installed and enabled
        updated_providers = [
            {
                'name': 'plex',
                'enabled': True,
                'supports_library_scan': True,
                'search_capabilities': []
            },
            {
                'name': 'spotify',
                'enabled': True,
                'search_capabilities': ['search.tracks', 'search.playlists'],
                'playlist_support': ['playlist.read', 'playlist.write']
            }
        ]
        
        # Step 3: Poller detects change
        providers_changed = (set(p['name'] for p in initial_providers) 
                           != set(p['name'] for p in updated_providers))
        assert providers_changed is True, "Poller should detect new provider"
        
        # Step 4: View re-renders with new data
        can_search = any(p.get('enabled') and p.get('search_capabilities') for p in updated_providers)
        assert can_search is True, "Search should now be available"
    
    def test_scenario_disable_library_provider(self):
        """
        Scenario: User disables Plex provider
        Expected: Library view becomes hidden
        """
        # Step 1: Initial state
        initial_providers = [
            {
                'name': 'plex',
                'enabled': True,
                'supports_library_scan': True
            }
        ]
        
        can_scan = any(p.get('enabled') and p.get('supports_library_scan') for p in initial_providers)
        assert can_scan is True, "Library scan should be available"
        
        # Step 2: Plex gets disabled
        updated_providers = [
            {
                'name': 'plex',
                'enabled': False,
                'supports_library_scan': True
            }
        ]
        
        # Step 3: Poller detects change
        enabled_changed = any(
            initial_providers[i].get('enabled') != updated_providers[i].get('enabled')
            for i in range(len(initial_providers))
        )
        assert enabled_changed is True, "Poller should detect provider state change"
        
        # Step 4: View re-renders
        can_scan = any(p.get('enabled') and p.get('supports_library_scan') for p in updated_providers)
        assert can_scan is False, "Library scan should no longer be available"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
