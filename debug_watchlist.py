#!/usr/bin/env python3
from unittest.mock import MagicMock, patch
from core.watchlist_scanner import WatchlistScanner
from core.spotify_client import SpotifyClient

# Setup mocks
mock_spotify = MagicMock(spec=SpotifyClient)
mock_album = MagicMock(id='album1', name='New Album', release_date='2025-12-14')
mock_spotify.get_artist_albums.return_value = [mock_album]

mock_db = MagicMock()
mock_db.check_track_exists.return_value = (None, 0.0)  # Track missing
mock_db.add_to_wishlist.return_value = True

with patch.object(WatchlistScanner, 'database', new=mock_db), \
     patch.object(WatchlistScanner, 'wishlist_service', new=MagicMock()), \
     patch.object(WatchlistScanner, 'matching_engine', new=MagicMock()):
    scanner = WatchlistScanner(spotify_client=mock_spotify)
    
    # Test discography
    print("Testing get_artist_discography...")
    albums = scanner.get_artist_discography('artist1', None)
    print(f"Returned albums: {albums}")
    print(f"Albums type: {type(albums)}")
    print(f"Albums length: {len(albums) if albums else 0}")
