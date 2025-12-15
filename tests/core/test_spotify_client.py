import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.spotify_client import SpotifyClient

class TestSpotifyClientFinal(unittest.TestCase):

    @patch('core.spotify_client.config_manager')
    @patch('core.spotify_client.spotipy')
    @patch('core.spotify_client.SpotifyOAuth')
    def test_initialization_success(self, mock_spotify_oauth, mock_spotipy, mock_config_manager):
        """Test client initializes correctly."""
        mock_config_manager.get_spotify_config.return_value = {'client_id': 'id', 'client_secret': 'secret'}
        client = SpotifyClient()
        self.assertIsNotNone(client.sp)
        mock_config_manager.get_spotify_config.assert_called_once()
        mock_spotify_oauth.assert_called_once()
        mock_spotipy.Spotify.assert_called_once()

    @patch('core.spotify_client.config_manager')
    @patch('core.spotify_client.spotipy')
    @patch('core.spotify_client.SpotifyOAuth')
    def test_initialization_no_credentials(self, mock_spotify_oauth, mock_spotipy, mock_config_manager):
        """Test client does not initialize without credentials."""
        mock_config_manager.get_spotify_config.return_value = {}
        client = SpotifyClient()
        self.assertIsNone(client.sp)
        mock_config_manager.get_spotify_config.assert_called_once()
        mock_spotify_oauth.assert_not_called()

    @patch('core.spotify_client.config_manager')
    @patch('core.spotify_client.spotipy')
    @patch('core.spotify_client.SpotifyOAuth')
    def test_get_user_playlists_metadata_only(self, mock_spotify_oauth, mock_spotipy, mock_config_manager):
        """Test fetching playlist metadata."""
        mock_config_manager.get_spotify_config.return_value = {'client_id': 'id', 'client_secret': 'secret'}
        mock_sp_instance = mock_spotipy.Spotify.return_value
        
        client = SpotifyClient()
        client.user_id = 'test_user'
        client.is_authenticated = MagicMock(return_value=True)
        client._ensure_user_id = MagicMock(return_value=True)

        mock_playlist_page = {
            'items': [
                {'id': 'p1', 'name': 'Playlist 1', 'owner': {'id': 'test_user', 'display_name': 'Test User'}, 'collaborative': False, 'public': True, 'description': '', 'tracks': {'total': 10}},
                {'id': 'p2', 'name': 'Playlist 2', 'owner': {'id': 'other_user', 'display_name': 'Other User'}, 'collaborative': True, 'public': True, 'description': '', 'tracks': {'total': 5}}
            ],
            'next': None 
        }
        mock_sp_instance.current_user_playlists.return_value = mock_playlist_page

        playlists = client.get_user_playlists_metadata_only()

        self.assertEqual(len(playlists), 2)
        mock_sp_instance.current_user_playlists.assert_called_once()

    @patch('core.spotify_client.config_manager')
    @patch('core.spotify_client.spotipy')
    @patch('core.spotify_client.SpotifyOAuth')
    def test_get_saved_tracks(self, mock_spotify_oauth, mock_spotipy, mock_config_manager):
        """Test fetching saved tracks."""
        mock_config_manager.get_spotify_config.return_value = {'client_id': 'id', 'client_secret': 'secret'}
        mock_sp_instance = mock_spotipy.Spotify.return_value
        
        client = SpotifyClient()
        client.is_authenticated = MagicMock(return_value=True)

        mock_track_data = {'id': 't1', 'name': 'Saved Track', 'artists': [{'name': 'Artist'}], 'album': {'name': 'Album'}, 'duration_ms': 200000, 'popularity': 70, 'preview_url': None, 'external_urls': None, 'track': True}
        mock_sp_instance.current_user_saved_tracks.return_value = {'items': [{'track': mock_track_data}], 'next': None}
        
        tracks = client.get_saved_tracks()
        
        self.assertEqual(len(tracks), 1)
        mock_sp_instance.current_user_saved_tracks.assert_called_once()

    @patch('core.spotify_client.config_manager')
    @patch('core.spotify_client.spotipy')
    @patch('core.spotify_client.SpotifyOAuth')
    def test_is_authenticated_true(self, mock_spotify_oauth, mock_spotipy, mock_config_manager):
        """Test is_authenticated returns True."""
        mock_config_manager.get_spotify_config.return_value = {'client_id': 'id', 'client_secret': 'secret'}
        mock_sp_instance = mock_spotipy.Spotify.return_value
        
        client = SpotifyClient()
        
        mock_sp_instance.current_user.return_value = {'id': 'test_user'}
        self.assertTrue(client.is_authenticated())

    @patch('core.spotify_client.config_manager')
    @patch('core.spotify_client.spotipy')
    @patch('core.spotify_client.SpotifyOAuth')
    def test_is_authenticated_false(self, mock_spotify_oauth, mock_spotipy, mock_config_manager):
        """Test is_authenticated returns False on exception."""
        mock_config_manager.get_spotify_config.return_value = {'client_id': 'id', 'client_secret': 'secret'}
        mock_sp_instance = mock_spotipy.Spotify.return_value
        
        client = SpotifyClient()
        
        mock_sp_instance.current_user.side_effect = Exception("Auth failed")
        self.assertFalse(client.is_authenticated())


if __name__ == '__main__':
    unittest.main()
