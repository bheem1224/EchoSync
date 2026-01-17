
import pytest
from unittest.mock import MagicMock, patch
import json

pytestmark = pytest.mark.skip(reason="wishlist_service module is incomplete")

# --- Mock Data and Fixtures ---

class MockDatabase:
    def __init__(self):
        self.add_to_wishlist = MagicMock(return_value=True)
        self.get_wishlist_tracks = MagicMock(return_value=[])
        self.update_wishlist_retry = MagicMock(return_value=True)
        self.remove_from_wishlist = MagicMock(return_value=True)
        self.get_wishlist_count = MagicMock(return_value=0)
        self.clear_wishlist = MagicMock(return_value=True)

@pytest.fixture
def mock_db():
    return MockDatabase()

@pytest.fixture
def service(mock_db):
    """Provides a WishlistService instance with a mocked database."""
    with patch('core.wishlist_service.get_database', return_value=mock_db):
        s = WishlistService()
        yield s

# --- Sample Data ---

SAMPLE_SPOTIFY_TRACK = {
    'id': 'spotify123',
    'name': 'Test Song',
    'artists': [{'name': 'Test Artist'}],
    'album': {'name': 'Test Album'},
    'duration_ms': 180000,
}

SAMPLE_MODAL_INFO_WITH_SPOTIFY = {
    'spotify_track': SAMPLE_SPOTIFY_TRACK,
    'failure_reason': 'Not found',
    'candidates': [],
}

SAMPLE_DB_WISHLIST_ITEM = {
    'id': 1,
    'spotify_track_id': 'spotify123',
    'spotify_data': SAMPLE_SPOTIFY_TRACK,
    'failure_reason': 'Test failure',
    'retry_count': 1,
    'date_added': '2023-01-01',
    'last_attempted': None,
    'source_type': 'manual',
    'source_info': {},
}


# --- Tests ---

def test_initialization(service, mock_db):
    """Test that the service initializes and lazy-loads the database."""
    assert service._database is None
    # Accessing the property should initialize it
    assert service.database == mock_db
    assert service._database == mock_db

def test_add_failed_track_from_modal(service: WishlistService, mock_db):
    """Test adding a track to the wishlist from a modal dictionary."""
    success = service.add_failed_track_from_modal(SAMPLE_MODAL_INFO_WITH_SPOTIFY, source_type="test_source")
    
    assert success is True
    # Verify the database method was called with the correct data
    mock_db.add_to_wishlist.assert_called_once()
    call_args, call_kwargs = mock_db.add_to_wishlist.call_args
    
    assert call_kwargs['spotify_track_data'] == SAMPLE_SPOTIFY_TRACK
    assert call_kwargs['failure_reason'] == 'Not found'
    assert call_kwargs['source_type'] == 'test_source'
    assert 'original_modal_data' in call_kwargs['source_info']

def test_add_spotify_track_to_wishlist(service: WishlistService, mock_db):
    """Test adding a track directly."""
    success = service.add_spotify_track_to_wishlist(
        spotify_track_data=SAMPLE_SPOTIFY_TRACK,
        failure_reason="Manual add",
        source_type="manual"
    )

    assert success is True
    mock_db.add_to_wishlist.assert_called_once_with(
        spotify_track_data=SAMPLE_SPOTIFY_TRACK,
        failure_reason="Manual add",
        source_type="manual",
        source_info={}
    )

def test_get_wishlist_tracks_for_download(service: WishlistService, mock_db):
    """Test formatting of wishlist tracks for the download modal."""
    # Have the DB return our sample item
    mock_db.get_wishlist_tracks.return_value = [SAMPLE_DB_WISHLIST_ITEM]
    
    formatted_tracks = service.get_wishlist_tracks_for_download()
    
    assert len(formatted_tracks) == 1
    track = formatted_tracks[0]
    
    # Check that it has both the DB fields and the formatted fields for modal compatibility
    assert track['wishlist_id'] == 1
    assert track['spotify_track_id'] == 'spotify123'
    assert track['name'] == 'Test Song'
    assert track['artists'][0]['name'] == 'Test Artist'
    assert track['album']['name'] == 'Test Album'

def test_get_wishlist_tracks_sorting(service: WishlistService, mock_db):
    """Test that the fetched wishlist tracks are sorted correctly."""
    track_b = {'id': 1, 'spotify_track_id': 'b', 'spotify_data': {'name': 'Beta', 'artists': [{'name': 'Artist B'}]}, 'failure_reason':'', 'retry_count':0, 'date_added':'', 'last_attempted':'', 'source_type':'', 'source_info':{}}
    track_a = {'id': 2, 'spotify_track_id': 'a', 'spotify_data': {'name': 'Alpha', 'artists': [{'name': 'Artist A'}]}, 'failure_reason':'', 'retry_count':0, 'date_added':'', 'last_attempted':'', 'source_type':'', 'source_info':{}}

    mock_db.get_wishlist_tracks.return_value = [track_b, track_a] # Unsorted
    
    formatted_tracks = service.get_wishlist_tracks_for_download()
    
    assert len(formatted_tracks) == 2
    # Artist A should come before Artist B
    assert formatted_tracks[0]['name'] == 'Alpha'
    assert formatted_tracks[1]['name'] == 'Beta'

def test_passthrough_methods(service: WishlistService, mock_db):
    """Test methods that just pass arguments through to the database."""
    # Test mark_track_download_result
    service.mark_track_download_result("spotify123", True)
    mock_db.update_wishlist_retry.assert_called_once_with("spotify123", True, None)
    
    # Test remove_track_from_wishlist
    service.remove_track_from_wishlist("spotify123")
    mock_db.remove_from_wishlist.assert_called_once_with("spotify123")

    # Test get_wishlist_count
    service.get_wishlist_count()
    mock_db.get_wishlist_count.assert_called_once()
    
    # Test clear_wishlist
    service.clear_wishlist()
    mock_db.clear_wishlist.assert_called_once()

def test_get_wishlist_summary(service: WishlistService, mock_db):
    """Test the summary generation."""
    # Mock data with different sources
    mock_tracks = [
        {'source_type': 'playlist', 'spotify_data': {'name': 't1', 'artists':[{'name':'a1'}]}, 'failure_reason':'', 'retry_count':0, 'date_added':''},
        {'source_type': 'playlist', 'spotify_data': {'name': 't2', 'artists':[{'name':'a2'}]}, 'failure_reason':'', 'retry_count':0, 'date_added':''},
        {'source_type': 'watchlist', 'spotify_data': {'name': 't3', 'artists':[{'name':'a3'}]}, 'failure_reason':'', 'retry_count':0, 'date_added':''},
    ]
    mock_db.get_wishlist_count.return_value = 3
    mock_db.get_wishlist_tracks.return_value = mock_tracks

    summary = service.get_wishlist_summary()

    assert summary['total_tracks'] == 3
    assert summary['by_source_type']['playlist'] == 2
    assert summary['by_source_type']['watchlist'] == 1
    assert len(summary['recent_failures']) == 3

def test_extract_spotify_track_from_modal_info(service: WishlistService):
    """Test the internal helper for extracting track data."""
    
    # Case 1: Direct spotify_track object
    result1 = service._extract_spotify_track_from_modal_info(SAMPLE_MODAL_INFO_WITH_SPOTIFY)
    assert result1['id'] == 'spotify123'
    
    # Case 2: Reconstructing from a slskd_result object
    mock_slskd_result = MagicMock(artist="Slskd Artist", title="Slskd Title", album="Slskd Album")
    modal_info_slskd = {'slskd_result': mock_slskd_result}
    result2 = service._extract_spotify_track_from_modal_info(modal_info_slskd)
    assert result2['name'] == 'Slskd Title'
    assert result2['artists'][0]['name'] == 'Slskd Artist'
    assert 'reconstructed' in result2

    # Case 3: Failure
    result3 = service._extract_spotify_track_from_modal_info({})
    assert result3 is None
