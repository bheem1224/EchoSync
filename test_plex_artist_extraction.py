#!/usr/bin/env python3
"""
Test script to verify Plex artist extraction fix.

This script tests that the Plex provider can extract artist information using 
both the artist() method and the grandparentTitle fallback.
"""

import sys
from unittest.mock import Mock, MagicMock

# Test the conversion logic
def test_artist_extraction():
    """Test that artist extraction works with fallback to grandparentTitle."""
    from providers.plex.client import PlexClient
    from plexapi.audio import Track as PlexTrack
    
    # Create a mock Plex track that simulates the issue
    mock_track = Mock(spec=PlexTrack)
    mock_track.title = "Test Song"
    mock_track.ratingKey = "12345"
    mock_track.duration = 180000
    mock_track.year = 2023
    mock_track.trackNumber = 1
    mock_track.discNumber = 1
    
    # Simulate failure in artist() method
    mock_track.artist = Mock(side_effect=Exception("Artist lookup failed"))
    
    # But provide grandparentTitle as fallback
    mock_track.grandparentTitle = "Test Artist"
    mock_track.grandparentSortTitle = "Artist, Test"
    
    # Simulate album method working
    mock_album = Mock()
    mock_album.title = "Test Album"
    mock_track.album = Mock(return_value=mock_album)
    
    # No media info
    mock_track.media = None
    mock_track.addedAt = None
    mock_track.titleSort = None
    mock_track.parentSortTitle = None
    mock_track.parentTitle = "Test Album"
    
    # Create client
    client = PlexClient()
    
    # Test conversion
    result = client._convert_track_to_soulsync(mock_track)
    
    # Verify
    assert result is not None, "Track conversion should not return None"
    assert result.title == "Test Song", f"Title mismatch: {result.title}"
    assert result.artist_name == "Test Artist", f"Artist name should be 'Test Artist' (from grandparentTitle fallback), got: {result.artist_name}"
    assert result.album_title == "Test Album", f"Album mismatch: {result.album_title}"
    assert result.identifiers.get('plex') == "12345", f"Plex ID mismatch: {result.identifiers}"
    
    print("✓ Test passed: Artist extraction fallback works correctly")
    return True

def test_identifiers_conversion():
    """Test that identifiers list is properly converted to dict."""
    from core.matching_engine.soul_sync_track import SoulSyncTrack
    
    # Test legacy list format (what Plex client creates)
    identifiers_list = [
        {
            'provider_source': 'plex',
            'provider_item_id': '12345',
            'raw_data': None
        }
    ]
    
    track = SoulSyncTrack(
        raw_title="Test Song",
        artist_name="Test Artist",
        album_title="Test Album",
        identifiers=identifiers_list
    )
    
    # Verify conversion happened
    assert isinstance(track.identifiers, dict), f"Identifiers should be dict after conversion, got: {type(track.identifiers)}"
    assert track.identifiers.get('plex') == '12345', f"Expected plex ID '12345', got: {track.identifiers}"
    
    print("✓ Test passed: Identifiers list properly converted to dict")
    return True

if __name__ == "__main__":
    try:
        print("Running Plex artist extraction tests...")
        print()
        
        test_identifiers_conversion()
        test_artist_extraction()
        
        print()
        print("All tests passed! The fix is working correctly.")
        sys.exit(0)
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error running test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
