import pytest
import asyncio
from unittest.mock import MagicMock, patch
from web.services.search_service import SearchAdapter

@pytest.mark.asyncio
async def test_federated_discovery_filtering():
    """Verify that SearchAdapter.federated_discovery respects enabled_plugins filtering."""
    # Create mock providers
    spotify_provider = MagicMock()
    spotify_provider.name = "spotify"
    spotify_provider.search.return_value = [{"title": "Track 1", "artist": "Artist 1", "identifiers": {"spotify_id": "123"}}]

    tidal_provider = MagicMock()
    tidal_provider.name = "tidal"
    tidal_provider.search.return_value = []

    # Mock capabilities
    mock_caps = MagicMock()
    mock_caps.search.tracks = True

    # Setup mocks for PluginRegistry and capabilities
    with patch("web.services.search_service.PluginRegistry.list_plugins", return_value=[123, 456]), \
         patch("web.services.search_service.PluginRegistry.create_instance") as mock_create, \
         patch("web.services.search_service.get_plugin_capabilities", return_value=mock_caps), \
         patch("web.services.search_service.get_local_track_details", return_value=(False, None)):

        def side_effect(plugin_id, *args, **kwargs):
            if plugin_id == 123:
                return spotify_provider
            elif plugin_id == 456:
                return tidal_provider
            return None
        
        mock_create.side_effect = side_effect

        adapter = SearchAdapter()

        # 1. Search with only "spotify" enabled
        results = await adapter.federated_discovery("test", enabled_plugins=["spotify"])
        
        # Verify only spotify was searched
        spotify_provider.search.assert_called_once_with("test", "track", 20)
        tidal_provider.search.assert_not_called()

        assert len(results) == 1
        assert results[0]["title"] == "Track 1"
        assert results[0]["artist"] == "Artist 1"
        assert results[0]["source"] == "spotify"
        assert results[0]["is_local"] is False
        assert results[0]["external_url"] == "https://open.spotify.com/track/123"

        # Reset mocks
        spotify_provider.search.reset_mock()
        tidal_provider.search.reset_mock()

        # 2. Search with both enabled
        await adapter.federated_discovery("test", enabled_plugins=["spotify", "tidal"])
        spotify_provider.search.assert_called_once_with("test", "track", 20)
        tidal_provider.search.assert_called_once_with("test", "track", 20)


def test_aggregate_filtering_and_serialization():
    """Verify that SearchAdapter.aggregate supports plugin_names and search_types and serializes correctly."""
    spotify_provider = MagicMock()
    spotify_provider.name = "spotify"
    spotify_provider.search.return_value = [{"title": "Spotify Track", "artist": "Artist S", "identifiers": {"spotify_id": "456"}}]

    # Mock capabilities
    mock_caps = MagicMock()
    mock_caps.search.tracks = True
    mock_caps.search.artists = False

    with patch("web.services.search_service.PluginRegistry.list_plugins", return_value=[123]), \
         patch("web.services.search_service.PluginRegistry.create_instance", return_value=spotify_provider), \
         patch("web.services.search_service.get_plugin_capabilities", return_value=mock_caps), \
         patch("web.services.search_service.get_local_track_details", return_value=(True, 789)):

        adapter = SearchAdapter()

        # Aggregate tracks
        results = adapter.aggregate(
            query="test",
            plugin_names=["spotify"],
            search_types=["tracks"]
        )

        spotify_provider.search.assert_called_once_with("test", type="track", limit=10)
        assert len(results) == 1
        assert results[0]["title"] == "Spotify Track"
        assert results[0]["artist"] == "Artist S"
        assert results[0]["source"] == "spotify"
        assert results[0]["is_local"] is True
        assert results[0]["artist_id"] == 789
        assert results[0]["external_url"] == "https://open.spotify.com/track/456"
