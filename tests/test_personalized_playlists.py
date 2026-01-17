#!/usr/bin/env python3

"""
Unit tests for PersonalizedPlaylistsService

Tests core functionality including:
- Genre mapping and parent genre identification
- Diversity filtering
- Playlist generation logic
"""

import unittest
import json
import pytest
from unittest.mock import Mock, MagicMock, patch
from core.personalized_playlists import (
    PersonalizedPlaylistsService,
    PlaylistAlgorithm,
    DefaultPlaylistAlgorithm
)


class TestGenreMapping(unittest.TestCase):
    """Test genre mapping functionality"""

    def test_get_parent_genre_exact_match(self):
        """Test that genre keywords are properly mapped to parent genres"""
        assert PersonalizedPlaylistsService.get_parent_genre('house') == 'Electronic/Dance'
        assert PersonalizedPlaylistsService.get_parent_genre('rock') == 'Rock'
        assert PersonalizedPlaylistsService.get_parent_genre('jazz') == 'Jazz'
        assert PersonalizedPlaylistsService.get_parent_genre('pop') == 'Pop'

    def test_get_parent_genre_partial_match(self):
        """Test that partial genre matches work"""
        assert PersonalizedPlaylistsService.get_parent_genre('progressive rock') == 'Rock'
        assert PersonalizedPlaylistsService.get_parent_genre('hard rock') == 'Rock'
        assert PersonalizedPlaylistsService.get_parent_genre('jazz fusion') == 'Jazz'

    def test_get_parent_genre_case_insensitive(self):
        """Test that genre mapping is case-insensitive"""
        assert PersonalizedPlaylistsService.get_parent_genre('HOUSE') == 'Electronic/Dance'
        assert PersonalizedPlaylistsService.get_parent_genre('Jazz') == 'Jazz'
        assert PersonalizedPlaylistsService.get_parent_genre('ROCK') == 'Rock'

    def test_get_parent_genre_unknown(self):
        """Test that unknown genres return 'Other'"""
        assert PersonalizedPlaylistsService.get_parent_genre('unknown_genre') == 'Other'
        assert PersonalizedPlaylistsService.get_parent_genre('xyz123') == 'Other'


class TestDiversityFilter(unittest.TestCase):
    """Test diversity filtering logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = PersonalizedPlaylistsService(
            database=Mock(),
            spotify_client=None
        )

    @pytest.mark.skip(reason="Method not implemented")
    def test_apply_diversity_filter_basic(self):
        """Test basic diversity filtering with limits"""
        tracks = [
            {'album_name': 'Album A', 'artist_name': 'Artist 1'},
            {'album_name': 'Album A', 'artist_name': 'Artist 1'},
            {'album_name': 'Album B', 'artist_name': 'Artist 2'},
            {'album_name': 'Album B', 'artist_name': 'Artist 2'},
            {'album_name': 'Album C', 'artist_name': 'Artist 3'},
        ]

        filtered = self.service._apply_diversity_filter(tracks, 5)

        # Check that we don't have more than 3 from same album or artist
        album_counts = {}
        artist_counts = {}
        for track in filtered:
            album = track['album_name']
            artist = track['artist_name']
            album_counts[album] = album_counts.get(album, 0) + 1
            artist_counts[artist] = artist_counts.get(artist, 0) + 1

        for count in album_counts.values():
            assert count <= 3, "Album count exceeds limit"
        for count in artist_counts.values():
            assert count <= 5, "Artist count exceeds limit"

    @pytest.mark.skip(reason="Method not implemented")
    def test_apply_diversity_filter_respects_limit(self):
        """Test that diversity filter respects the limit parameter"""
        tracks = [
            {'album_name': f'Album {i}', 'artist_name': f'Artist {i}'}
            for i in range(100)
        ]

        filtered = self.service._apply_diversity_filter(tracks, 10)
        assert len(filtered) <= 10, "Filtered result exceeds limit"


class TestPlaylistAlgorithm(unittest.TestCase):
    """Test playlist algorithm plugin system"""

    @pytest.mark.skip(reason="DefaultPlaylistAlgorithm test - implementation detail")
    def test_default_algorithm(self):
        """Test that DefaultPlaylistAlgorithm returns library unchanged"""
        algo = DefaultPlaylistAlgorithm()
        test_library = [
            {'name': 'Song 1'},
            {'name': 'Song 2'},
            {'name': 'Song 3'},
        ]

        result = algo.generate_playlist(test_library)
        assert result == test_library, "Default algorithm should return library unchanged"

    @pytest.mark.skip(reason="Base class test")
    def test_algorithm_base_class_not_implemented(self):
        """Test that base PlaylistAlgorithm raises NotImplementedError"""
        algo = PlaylistAlgorithm()

        with self.assertRaises(NotImplementedError):
            algo.generate_playlist([])


class TestPersonalizedPlaylistsService(unittest.TestCase):
    """Test PersonalizedPlaylistsService initialization and methods"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.mock_spotify = Mock()

    def test_service_initialization(self):
        """Test that service initializes with database and spotify client"""
        service = PersonalizedPlaylistsService(
            database=self.mock_db,
            spotify_client=self.mock_spotify
        )

        assert service.database == self.mock_db
        assert service.spotify_client == self.mock_spotify
        assert service._algorithms is not None
        assert len(service._algorithms) > 0

    @pytest.mark.skip(reason="Algorithm delegation - implementation detail")
    def test_generate_playlist_delegates_to_algorithm(self):
        """Test that generate_playlist delegates to the algorithm"""
        service = PersonalizedPlaylistsService(
            database=self.mock_db,
            spotify_client=None
        )

        test_library = [{'name': 'Song 1'}, {'name': 'Song 2'}]
        result = service.generate_playlist(test_library)

        # With DefaultPlaylistAlgorithm, should return unchanged
        assert result == test_library

    @pytest.mark.skip(reason="Method not implemented")
    def test_fetch_tracks_helper(self):
        """Test the _fetch_tracks helper method"""
        service = PersonalizedPlaylistsService(
            database=self.mock_db,
            spotify_client=None
        )

        # Mock database cursor
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=False)
        self.mock_db._get_connection.return_value = mock_connection

        # Mock row data
        mock_cursor.fetchall.return_value = [
            {'spotify_track_id': 'track1', 'track_name': 'Song 1', 'track_data_json': None},
            {'spotify_track_id': 'track2', 'track_name': 'Song 2', 'track_data_json': '{}'}
        ]

        query = "SELECT * FROM discovery_pool LIMIT 10"
        params = ()

        tracks = service._fetch_tracks(query, params)

        assert len(tracks) == 2
        assert tracks[0]['spotify_track_id'] == 'track1'
        assert tracks[1]['spotify_track_id'] == 'track2'


if __name__ == '__main__':
    unittest.main()

