import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.tidal_client import TidalClient, Track, Playlist

class TestTidalClient(unittest.TestCase):

    @patch('core.tidal_client.config_manager')
    def test_initialization_with_config(self, mock_config_manager):
        """Test client initializes correctly with config and saved tokens."""
        mock_config_manager.get.side_effect = [
            {'client_id': 'test_id', 'client_secret': 'test_secret'}, # tidal config
            {'access_token': 'saved_access', 'refresh_token': 'saved_refresh', 'expires_at': time.time() + 3600} # tidal_tokens
        ]
        
        client = TidalClient()

        self.assertEqual(client.client_id, 'test_id')
        self.assertEqual(client.client_secret, 'test_secret')
        self.assertEqual(client.access_token, 'saved_access')
        self.assertEqual(client.session.headers['Authorization'], 'Bearer saved_access')
        
    @patch('core.tidal_client.config_manager')
    def test_initialization_no_config(self, mock_config_manager):
        """Test client initialization with no config."""
        mock_config_manager.get.return_value = {}
        
        client = TidalClient()
        
        self.assertIsNone(client.client_id)
        self.assertIsNone(client.access_token)

    @patch('requests.Session.post')
    @patch('core.tidal_client.config_manager')
    def test_refresh_access_token_success(self, mock_config_manager, mock_post):
        """Test successful token refresh."""
        mock_config_manager.get.return_value = {'client_id': 'test_id', 'client_secret': 'test_secret'}
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'access_token': 'new_access_token',
            'expires_in': 3600
        }
        
        client = TidalClient()
        client.refresh_token = 'old_refresh_token'
        
        result = client._refresh_access_token()
        
        self.assertTrue(result)
        self.assertEqual(client.access_token, 'new_access_token')
        self.assertEqual(client.session.headers['Authorization'], 'Bearer new_access_token')
        mock_post.assert_called_once()
        # Verify that tokens are saved
        mock_config_manager.set.assert_called_with('tidal_tokens', unittest.mock.ANY)

    @patch('requests.Session.get')
    @patch('core.tidal_client.config_manager')
    def test_get_playlist_success(self, mock_config_manager, mock_get):
        """Test successfully fetching a single playlist with tracks."""
        mock_config_manager.get.return_value = {'client_id': 'test_id', 'client_secret': 'test_secret'}
        
        client = TidalClient()
        client._ensure_valid_token = MagicMock(return_value=True)

        # Mock response for playlist metadata
        mock_playlist_meta = MagicMock()
        mock_playlist_meta.status_code = 200
        mock_playlist_meta.json.return_value = {'id': 'playlist1', 'title': 'My Playlist'}

        # Mock response for playlist tracks (one page)
        mock_tracks_page = MagicMock()
        mock_tracks_page.status_code = 200
        mock_tracks_page.json.return_value = {
            'items': [
                {'item': {'id': 't1', 'title': 'Track 1', 'artists': [{'name': 'Artist 1'}], 'album': {'title': 'Album 1'}, 'duration': 180}, 'type': 'track'}
            ],
            'limit': 1,
            'offset': 0,
            'totalNumberOfItems': 1
        }
        
        mock_get.side_effect = [mock_playlist_meta, mock_tracks_page]
        
        playlist = client.get_playlist('playlist1')
        
        self.assertIsNotNone(playlist)
        self.assertIsInstance(playlist, Playlist)
        self.assertEqual(playlist.name, 'My Playlist')
        self.assertEqual(len(playlist.tracks), 1)
        self.assertEqual(playlist.tracks[0].name, 'Track 1')
        self.assertEqual(mock_get.call_count, 2)

    @patch('requests.Session.get')
    @patch('core.tidal_client.config_manager')
    def test_search_tracks_success(self, mock_config_manager, mock_get):
        """Test successfully searching for tracks."""
        mock_config_manager.get.return_value = {'client_id': 'test_id', 'client_secret': 'test_secret'}
        
        client = TidalClient()
        client._ensure_valid_token = MagicMock(return_value=True)

        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            'tracks': {
                'items': [
                    {'id': 't1', 'title': 'Search Result', 'artists': [{'name': 'Artist'}], 'album': {'title': 'Album'}, 'duration': 200}
                ]
            }
        }
        mock_get.return_value = mock_search_response
        
        tracks = client.search_tracks('test query')
        
        self.assertEqual(len(tracks), 1)
        self.assertIsInstance(tracks[0], Track)
        self.assertEqual(tracks[0].name, 'Search Result')
        mock_get.assert_called_once_with(
            f"{client.base_url}/searchresults",
            params={'query': 'test query', 'type': 'tracks', 'limit': 10, 'countryCode': 'US'},
            timeout=10
        )

if __name__ == '__main__':
    unittest.main()
