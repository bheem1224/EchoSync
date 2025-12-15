
import pytest
from unittest.mock import MagicMock, patch, mock_open
from core.lyrics_client import LyricsClient

# --- Fixtures ---

@pytest.fixture
def mock_lrclib_api():
    """Fixture to mock the LrcLibAPI class."""
    with patch('core.lyrics_client.LrcLibAPI') as mock_api_class:
        mock_api_instance = MagicMock()
        mock_api_class.return_value = mock_api_instance
        # Yield the mocked class so tests can assert it was instantiated
        yield mock_api_class

@pytest.fixture
def lyrics_client(mock_lrclib_api):
    """Fixture for a LyricsClient instance with a mocked API."""
    return LyricsClient()

# --- Mock Data ---

class MockLyrics:
    def __init__(self, synced=None, plain=None):
        self.synced_lyrics = synced
        self.plain_lyrics = plain

SYNCED_LRC = "[00:01.00]Hello World"
PLAIN_LRC = "Hello World"
MOCK_LYRICS_SYNCED = MockLyrics(synced=SYNCED_LRC)
MOCK_LYRICS_PLAIN = MockLyrics(plain=PLAIN_LRC)
MOCK_LYRICS_EMPTY = MockLyrics()

# --- Tests ---

def test_initialization_success(mock_lrclib_api):
    """Test that the client initializes the API successfully."""
    client = LyricsClient()
    assert client.api is not None
    mock_lrclib_api.assert_called_once()

@patch('core.lyrics_client.LrcLibAPI', None)
def test_initialization_no_lrclib():
    """Test graceful failure when lrclib is not installed."""
    # This simulates 'from lrclib import LrcLibAPI' failing
    # by temporarily removing it from the context. A bit of a hack.
    with patch.dict('sys.modules', {'lrclib': None}):
        client = LyricsClient()
        assert client.api is None

def test_create_lrc_api_not_available():
    """Test that LRC creation is skipped if the API is not available."""
    client = LyricsClient()
    client.api = None # Manually disable API
    
    result = client.create_lrc_file('audio.mp3', 'Track', 'Artist')
    assert result is False

@patch('os.path.exists', return_value=True)
def test_create_lrc_file_already_exists(mock_exists, lyrics_client):
    """Test that LRC creation is skipped if the file already exists."""
    result = lyrics_client.create_lrc_file('audio.mp3', 'Track', 'Artist')
    
    assert result is True
    mock_exists.assert_called_once_with('audio.lrc')
    # The API should not be called if the file exists
    lyrics_client.api.get_lyrics.assert_not_called()
    lyrics_client.api.search_lyrics.assert_not_called()

@patch('os.path.exists', return_value=False)
@patch('builtins.open', new_callable=mock_open)
def test_create_lrc_exact_match_success(mock_file, mock_exists, lyrics_client):
    """Test creating an LRC file from an exact match with synced lyrics."""
    lyrics_client.api.get_lyrics.return_value = MOCK_LYRICS_SYNCED
    
    result = lyrics_client.create_lrc_file(
        'audio.mp3',
        track_name='Test Track',
        artist_name='Test Artist',
        album_name='Test Album',
        duration_seconds=120
    )
    
    assert result is True
    # Verify exact match was attempted
    lyrics_client.api.get_lyrics.assert_called_once_with(
        track_name='Test Track',
        artist_name='Test Artist',
        album_name='Test Album',
        duration=120
    )
    # Search should not be called
    lyrics_client.api.search_lyrics.assert_not_called()
    # Verify file was written
    mock_file.assert_called_once_with('audio.lrc', 'w', encoding='utf-8')
    mock_file().write.assert_called_once_with(SYNCED_LRC)

@patch('os.path.exists', return_value=False)
@patch('builtins.open', new_callable=mock_open)
def test_create_lrc_search_fallback_success(mock_file, mock_exists, lyrics_client):
    """Test creating an LRC file using the search fallback."""
    # Exact match fails
    lyrics_client.api.get_lyrics.return_value = None
    # Search succeeds
    lyrics_client.api.search_lyrics.return_value = [MOCK_LYRICS_SYNCED, MOCK_LYRICS_PLAIN]

    result = lyrics_client.create_lrc_file(
        'audio.mp3',
        track_name='Test Track',
        artist_name='Test Artist',
        album_name='Test Album',
        duration_seconds=120
    )
    
    assert result is True
    lyrics_client.api.get_lyrics.assert_called_once()
    lyrics_client.api.search_lyrics.assert_called_once_with(
        track_name='Test Track',
        artist_name='Test Artist'
    )
    # Should write the content of the *first* search result
    mock_file().write.assert_called_once_with(SYNCED_LRC)

@patch('os.path.exists', return_value=False)
@patch('builtins.open', new_callable=mock_open)
def test_create_lrc_plain_lyrics_fallback(mock_file, mock_exists, lyrics_client):
    """Test that plain lyrics are used if synced lyrics are not available."""
    lyrics_client.api.get_lyrics.return_value = MOCK_LYRICS_PLAIN

    result = lyrics_client.create_lrc_file('audio.mp3', 'Track', 'Artist', duration_seconds=120)
    
    assert result is True
    mock_file().write.assert_called_once_with(PLAIN_LRC)

@patch('os.path.exists', return_value=False)
@patch('builtins.open', new_callable=mock_open)
def test_create_lrc_no_lyrics_found(mock_file, mock_exists, lyrics_client):
    """Test the case where no lyrics are found by any method."""
    lyrics_client.api.get_lyrics.return_value = None
    lyrics_client.api.search_lyrics.return_value = []

    result = lyrics_client.create_lrc_file('audio.mp3', 'Track', 'Artist', duration_seconds=120)

    assert result is False
    lyrics_client.api.get_lyrics.assert_called_once()
    lyrics_client.api.search_lyrics.assert_called_once()
    # File should not be opened or written to
    mock_file.assert_not_called()

@patch('os.path.exists', return_value=False)
@patch('builtins.open', new_callable=mock_open)
def test_create_lrc_no_usable_content(mock_file, mock_exists, lyrics_client):
    """Test when lyrics are found but have no synced or plain content."""
    lyrics_client.api.get_lyrics.return_value = MOCK_LYRICS_EMPTY
    
    result = lyrics_client.create_lrc_file('audio.mp3', 'Track', 'Artist', duration_seconds=120)

    assert result is False
    mock_file.assert_not_called()

@patch('os.path.exists', return_value=False)
def test_create_lrc_api_exception(mock_exists, lyrics_client):
    """Test that the function handles exceptions from the API gracefully."""
    lyrics_client.api.get_lyrics.side_effect = Exception("API is down")

    result = lyrics_client.create_lrc_file('audio.mp3', 'Track', 'Artist', duration_seconds=120)
    
    assert result is False
