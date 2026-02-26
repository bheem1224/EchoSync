"""
Verification tests for Phase 2 Memory Optimization.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from core.matching_engine.soul_sync_track import SoulSyncTrack
from database.bulk_operations import LibraryManager
from providers.spotify.client import SpotifyClient
from services.sync_service import PlaylistSyncService, SpotifyPlaylist

class TestBulkImportGenerator:
    def test_bulk_import_accepts_generator(self):
        """Verify bulk_import works with a generator input."""
        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)

        manager = LibraryManager(mock_session_factory)

        # Generator function yielding tracks
        def track_generator():
            for i in range(5):
                yield SoulSyncTrack(
                    raw_title=f"Track {i}",
                    artist_name="Artist",
                    album_title="Album"
                )

        # Call bulk_import with generator
        processed = manager.bulk_import(track_generator())

        # Verify it processed 5 tracks
        assert processed == 5
        # Verify session commits (at least once at end)
        assert mock_session.commit.called

class TestSpotifyPagination:
    def test_get_user_playlists_yields_results(self):
        """Verify get_user_playlists yields results page by page."""
        client = SpotifyClient(account_id=1)
        client.sp = MagicMock()
        client.is_authenticated = MagicMock(return_value=True)
        client._ensure_user_id = MagicMock(return_value=True)

        # Mock pages with required 'tracks' structure
        page1 = {'items': [{'id': '1', 'name': 'P1', 'tracks': {'total': 10}, 'owner': {'display_name': 'Me'}}], 'next': 'url2'}
        page2 = {'items': [{'id': '2', 'name': 'P2', 'tracks': {'total': 5}, 'owner': {'display_name': 'Me'}}], 'next': None}

        # Setup mock return values
        client.sp.current_user_playlists.return_value = page1
        client.sp.next.return_value = page2

        # Execute generator
        playlists = list(client.get_user_playlists())

        # Verify
        assert len(playlists) == 2
        assert playlists[0]['id'] == '1'
        assert playlists[1]['id'] == '2'

        # Verify calls
        client.sp.current_user_playlists.assert_called_with(limit=50)
        client.sp.next.assert_called_with(page1)

class TestSyncServiceConsumption:
    def test_get_all_spotify_playlists_consumes_generator(self):
        """Verify SyncService correctly consumes the generator."""
        # Mock dependencies during initialization
        with patch('services.sync_service.ProviderRegistry') as mock_registry:
            # Mock default client creation
            mock_client = MagicMock()
            mock_registry.create_instance.return_value = mock_client

            service = PlaylistSyncService()

            # Setup service state manually
            service.spotify_client = mock_client
            service.spotify_clients = [mock_client]

            # Mock generator returning 3 playlists
            def playlist_gen():
                yield {'id': '1', 'name': 'P1'}
                yield {'id': '2', 'name': 'P2'}
                yield {'id': '3', 'name': 'P3'}

            mock_client.get_user_playlists.return_value = playlist_gen()
            mock_client.is_configured.return_value = True

            # Mock config to return one account
            with patch('core.settings.config_manager.get_spotify_accounts', return_value=[{'id': 1, 'name': 'Test', 'is_active': True}]):
                # The service uses ProviderRegistry.create_instance inside _get_all_spotify_playlists too
                mock_registry.create_instance.return_value = mock_client
                playlists = asyncio_run(service._get_all_spotify_playlists())

            assert len(playlists) == 3
            assert playlists[0].name == "P1 (Test)"
            assert playlists[2].id == "3"

def asyncio_run(coro):
    """Helper for async test"""
    import asyncio
    return asyncio.run(coro)
