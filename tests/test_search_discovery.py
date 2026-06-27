import pytest
import asyncio
from unittest.mock import MagicMock, patch
from web.services.search_service import SearchAdapter

@pytest.mark.asyncio
async def test_federated_discovery_filtering():
    """Verify that SearchAdapter.federated_discovery respects enabled_providers filtering."""
    # Create mock providers
    spotify_provider = MagicMock()
    spotify_provider.name = "spotify"
    spotify_provider.search.return_value = []

    tidal_provider = MagicMock()
    tidal_provider.name = "tidal"
    tidal_provider.search.return_value = []

    # Mock capabilities
    mock_caps = MagicMock()
    mock_caps.search.tracks = True

    # Setup mocks for PluginRegistry and capabilities
    with patch("web.services.search_service.PluginRegistry.list_plugins", return_value=[123, 456]), \
         patch("web.services.search_service.PluginRegistry.create_instance") as mock_create, \
         patch("web.services.search_service.get_plugin_capabilities", return_value=mock_caps):

        def side_effect(plugin_id, *args, **kwargs):
            if plugin_id == 123:
                return spotify_provider
            elif plugin_id == 456:
                return tidal_provider
            return None
        
        mock_create.side_effect = side_effect

        adapter = SearchAdapter()

        # 1. Search with only "spotify" enabled
        results = await adapter.federated_discovery("test", enabled_providers=["spotify"])
        
        # Verify only spotify was searched
        spotify_provider.search.assert_called_once_with("test", "track", 20)
        tidal_provider.search.assert_not_called()

        # Reset mocks
        spotify_provider.search.reset_mock()
        tidal_provider.search.reset_mock()

        # 2. Search with both enabled
        await adapter.federated_discovery("test", enabled_providers=["spotify", "tidal"])
        spotify_provider.search.assert_called_once_with("test", "track", 20)
        tidal_provider.search.assert_called_once_with("test", "track", 20)
