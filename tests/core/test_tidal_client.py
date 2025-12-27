
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.tidal_client import TidalClient, Playlist, Track

class TestTidalClient(unittest.TestCase):
    @patch('sdk.storage_service.get_storage_service')
    def test_initialization_with_config(self, mock_storage):
        storage = MagicMock()
        mock_storage.return_value = storage
        storage.get_service_config.side_effect = lambda service, key: {
            'client_id': 'test_id',
            'client_secret': 'test_secret',
            'redirect_uri': 'http://127.0.0.1:8008/tidal/callback'
        }[key]
        storage.get_account_token.return_value = {
            'access_token': 'saved_access',
            'refresh_token': 'saved_refresh',
            'expires_at': time.time() + 3600
        }
        client = TidalClient(account_id='1')
        self.assertEqual(client.client_id, 'test_id')
        self.assertEqual(client.client_secret, 'test_secret')
        self.assertEqual(client.access_token, 'saved_access')
        # HttpClient manages auth headers per-request, not globally on session
        self.assertIsNotNone(client._http)

    @patch('sdk.storage_service.get_storage_service')
    def test_initialization_no_config(self, mock_storage):
        storage = MagicMock()
        mock_storage.return_value = storage
        storage.get_service_config.side_effect = lambda service, key: ''
        storage.get_account_token.return_value = None
        client = TidalClient(account_id='1')
        self.assertIsNone(client.client_id)
        self.assertIsNone(client.access_token)

    @patch('sdk.http_client.HttpClient.post')
    @patch('sdk.storage_service.get_storage_service')
    def test_refresh_access_token_success(self, mock_storage, mock_post):
        storage = MagicMock()
        mock_storage.return_value = storage
        storage.get_service_config.side_effect = lambda service, key: 'test_id' if key == 'client_id' else 'test_secret'
        storage.get_account_token.return_value = {
            'access_token': 'old_access',
            'refresh_token': 'old_refresh_token',
            'expires_at': time.time() - 100
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'access_token': 'new_access_token',
            'expires_in': 3600
        }
        client = TidalClient(account_id='1')
        client.refresh_token = 'old_refresh_token'
        result = client._refresh_access_token()
        self.assertTrue(result)
        self.assertEqual(client.access_token, 'new_access_token')
        # HttpClient manages auth per-request, not globally
        self.assertIsNotNone(client._http)
        self.assertGreaterEqual(mock_post.call_count, 1)

    @patch('sdk.storage_service.get_storage_service')
    def test_get_playlist_success(self, mock_storage):
        storage = MagicMock()
        mock_storage.return_value = storage
        storage.get_service_config.side_effect = lambda service, key: 'test_id' if key == 'client_id' else 'test_secret'
        storage.get_account_token.return_value = {
            'access_token': 'saved_access',
            'refresh_token': 'saved_refresh',
            'expires_at': time.time() + 3600
        }
        client = TidalClient(account_id='1')
        client._ensure_valid_token = MagicMock(return_value=True)
        
        # Mock the HttpClient.get method
        mock_http = MagicMock()
        mock_playlist_meta = MagicMock()
        mock_playlist_meta.status_code = 200
        mock_playlist_meta.json.return_value = {
            'data': {
                'id': 'playlist1',
                'attributes': {
                    'name': 'My Playlist',
                    'description': '',
                    'accessType': 'PUBLIC'
                }
            }
        }
        mock_tracks_page = MagicMock()
        mock_tracks_page.status_code = 200
        mock_tracks_page.json.return_value = {
            'data': [
                {
                    'type': 'playlistItems',
                    'id': 'pi1',
                    'relationships': {
                        'track': {
                            'data': {
                                'type': 'tracks',
                                'id': 't1'
                            }
                        }
                    }
                }
            ],
            'included': [
                {
                    'type': 'tracks',
                    'id': 't1',
                    'attributes': {
                        'title': 'Track 1',
                        'duration': 180
                    },
                    'relationships': {
                        'artists': {
                            'data': [
                                {'type': 'artists', 'id': 'a1'}
                            ]
                        },
                        'album': {
                            'data': {'type': 'albums', 'id': 'alb1'}
                        }
                    }
                },
                {
                    'type': 'artists',
                    'id': 'a1',
                    'attributes': {
                        'name': 'Artist 1'
                    }
                },
                {
                    'type': 'albums',
                    'id': 'alb1',
                    'attributes': {
                        'title': 'Album 1'
                    }
                }
            ]
        }
        mock_http.get.side_effect = [mock_playlist_meta, mock_tracks_page]
        client._http = mock_http
        
        playlist = client.get_playlist('playlist1')
        self.assertIsNotNone(playlist)
        self.assertIsInstance(playlist, Playlist)
        self.assertEqual(playlist.name, 'My Playlist')
        self.assertEqual(len(playlist.tracks), 1)
        self.assertEqual(playlist.tracks[0].name, 'Track 1')
        self.assertEqual(playlist.tracks[0].artists, ['Artist 1'])
        self.assertEqual(playlist.tracks[0].album, 'Album 1')
        self.assertEqual(mock_http.get.call_count, 2)

    @patch('sdk.http_client.HttpClient.get')
    @patch('sdk.storage_service.get_storage_service')
    def test_search_tracks_success(self, mock_storage, mock_get):
        storage = MagicMock()
        mock_storage.return_value = storage
        storage.get_service_config.side_effect = lambda service, key: 'test_id' if key == 'client_id' else 'test_secret'
        storage.get_account_token.return_value = {
            'access_token': 'saved_access',
            'refresh_token': 'saved_refresh',
            'expires_at': time.time() + 3600
        }
        client = TidalClient(account_id='1')
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
        # HttpClient.get is called with headers parameter
        self.assertEqual(mock_get.call_count, 1)

if __name__ == '__main__':
    unittest.main()
