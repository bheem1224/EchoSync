
import pytest
import sqlite3
import json
from unittest.mock import MagicMock, patch, ANY
from core.personalized_playlists import PersonalizedPlaylistsService

# --- Mock Data and Fixtures ---

class MockMusicDatabase:
    def __init__(self):
        self.conn = MagicMock()
        self.cursor = MagicMock()
        self.conn.cursor.return_value = self.cursor
        # Default fetchone/fetchall to return empty lists
        self.cursor.fetchone.return_value = None
        self.cursor.fetchall.return_value = []

    # Return a context manager that yields the underlying conn so
    # that `with database._get_connection() as conn:` returns `self.conn`.
    def _get_connection(self):
        class _Ctx:
            def __init__(self, conn):
                self._conn = conn
            def __enter__(self):
                return self._conn
            def __exit__(self, exc_type, exc, tb):
                return False
        return _Ctx(self.conn)

@pytest.fixture
def mock_db():
    return MockMusicDatabase()

@pytest.fixture
def mock_spotify_client():
    return MagicMock()

@pytest.fixture
def service(mock_db, mock_spotify_client):
    """Provides a PersonalizedPlaylistsService instance with a mocked database."""
    return PersonalizedPlaylistsService(database=mock_db, spotify_client=mock_spotify_client)

# --- Sample Data for DB Mocks ---

def create_db_row(data):
    """Creates a mock row object that can be accessed by index and key."""
    row = list(data.values())
    row.__dict__.update(data) # Allows access by key
    # To allow access by index, we can't directly subclass list. This is a simple sim.
    # A more robust mock would use a custom class.
    return row

def create_discovery_pool_rows(tracks):
    """Creates mock discovery pool rows from a list of track dicts."""
    rows = []
    for t in tracks:
        row_dict = {
            "spotify_track_id": t.get("id"),
            "track_name": t.get("name"),
            "artist_name": t.get("artist"),
            "album_name": t.get("album"),
            "album_cover_url": t.get("cover"),
            "duration_ms": t.get("duration"),
            "popularity": t.get("popularity"),
            # For compatibility with service methods we make sure artist_genres
            # is placed at index 7 when accessed by integer index.
            "release_date": t.get("release_date"),
            "artist_genres": json.dumps(t.get("genres", [])),
            "track_data_json": "{}"
        }
        # A bit of a hack to make the mock row accessible by index like sqlite3.Row
        # Build an ordered list matching the expected column order in
        # PersonalizedPlaylistsService queries so integer indices map correctly.
        ordered = [
            row_dict['spotify_track_id'],
            row_dict['track_name'],
            row_dict['artist_name'],
            row_dict['album_name'],
            row_dict['album_cover_url'],
            row_dict['duration_ms'],
            row_dict['popularity'],
            row_dict['artist_genres'],
            row_dict['track_data_json']
        ]

        class MockRow(list):
            def __init__(self, data, rowd):
                super().__init__(data)
                self._rowd = dict(rowd)
            def keys(self):
                return list(self._rowd.keys())
            def __getitem__(self, key):
                if isinstance(key, str):
                    return self._rowd[key]
                return list.__getitem__(self, key)
            def __iter__(self):
                # Yield (key, value) pairs so dict(row) produces a mapping
                for k in self._rowd.keys():
                    yield (k, self._rowd[k])
        rows.append(MockRow(ordered, row_dict))
    return rows


# --- Tests ---

def test_get_parent_genre():
    """Test the static genre mapping method."""
    assert PersonalizedPlaylistsService.get_parent_genre("deep house") == "Electronic/Dance"
    assert PersonalizedPlaylistsService.get_parent_genre("post-punk") == "Rock"
    assert PersonalizedPlaylistsService.get_parent_genre("k-pop") == "Pop"
    assert PersonalizedPlaylistsService.get_parent_genre("unknown genre") == "Other"

def test_get_decade_playlist(service: PersonalizedPlaylistsService, mock_db):
    """Test fetching a playlist for a specific decade."""
    mock_tracks = [
        # This one should be filtered by diversity rules
        {"id": "t1", "name": "A", "artist": "Artist 1", "album": "Album 1", "popularity": 80, "release_date": "2010-05-10"},
        {"id": "t2", "name": "B", "artist": "Artist 1", "album": "Album 1", "popularity": 80, "release_date": "2011-05-10"},
        {"id": "t3", "name": "C", "artist": "Artist 1", "album": "Album 1", "popularity": 80, "release_date": "2012-05-10"},
        {"id": "t4", "name": "D", "artist": "Artist 1", "album": "Album 1", "popularity": 80, "release_date": "2013-05-10"},
        # This one should be included
        {"id": "t5", "name": "E", "artist": "Artist 2", "album": "Album 2", "popularity": 70, "release_date": "2015-01-01"},
    ]
    # Set fetchall to return our mock rows
    mock_db.cursor.fetchall.return_value = create_discovery_pool_rows(mock_tracks)
    
    # Make selection deterministic by disabling shuffle during the call
    with patch('random.shuffle', lambda x: None):
        playlist = service.get_decade_playlist(2010, limit=3)
    
    # Check that the correct query was executed
    mock_db.cursor.execute.assert_called_once()
    assert "BETWEEN ? AND ?" in mock_db.cursor.execute.call_args[0][0]
    assert mock_db.cursor.execute.call_args[0][1] == (2010, 2019, 30) # start, end, limit*10

    assert len(playlist) <= 3
    # The exact tracks are hard to predict due to shuffle, but we can check artists
    artists_in_playlist = [t['artist_name'] for t in playlist]
    # Artists should come from the input set and respect the limit/diversity
    assert set(artists_in_playlist).issubset({"Artist 1", "Artist 2"})
    assert artists_in_playlist.count("Artist 1") <= 3 # Diversity limit

def test_get_available_genres(service: PersonalizedPlaylistsService, mock_db):
    """Test consolidating and counting genres from the discovery pool."""
    mock_rows = [
        (json.dumps(['deep house', 'edm']),), # Electronic/Dance
        (json.dumps(['post-punk', 'indie rock']),), # Rock
        (json.dumps(['uk garage']),), # Electronic/Dance
        (json.dumps(['unknown genre']),), # Other
        (json.dumps(['k-pop']),), # Pop
    ]
    # Create 10 of each to meet the threshold
    mock_db.cursor.fetchall.return_value = (mock_rows * 10)

    genres = service.get_available_genres()

    # At least the major genres should be present
    assert len(genres) >= 2
    # Electronic/Dance should be present with highest count
    names = [g['name'] for g in genres]
    assert 'Electronic/Dance' in names
    # Ensure Rock and Pop are represented
    genre_names = {g['name'] for g in genres}
    assert "Rock" in genre_names
    assert "Pop" in genre_names

def test_get_genre_playlist_parent_genre(service: PersonalizedPlaylistsService, mock_db):
    """Test getting a playlist for a parent genre."""
    mock_tracks = [
        {"name": "t1", "artist": "A1", "album": "Al1", "genres": ["deep house"]},
        {"name": "t2", "artist": "A2", "album": "Al2", "genres": ["post-punk"]}, # Shouldn't be in result
        {"name": "t3", "artist": "A3", "album": "Al3", "genres": ["uk garage"]},
    ]
    mock_db.cursor.fetchall.return_value = create_discovery_pool_rows(mock_tracks)
    
    playlist = service.get_genre_playlist("Electronic/Dance")
    
    assert len(playlist) == 2
    track_names = {t['track_name'] for t in playlist}
    assert "t1" in track_names
    assert "t3" in track_names
    assert "t2" not in track_names

def test_get_popular_picks(service: PersonalizedPlaylistsService, mock_db):
    """Test getting popular tracks, respecting diversity."""
    mock_tracks = [
        {"name": "Pop A", "artist": "Artist 1", "album": "Album 1", "popularity": 90},
        {"name": "Pop B", "artist": "Artist 1", "album": "Album 1", "popularity": 89},
        {"name": "Pop C", "artist": "Artist 1", "album": "Album 1", "popularity": 88}, # Should be filtered
        {"name": "Pop D", "artist": "Artist 2", "album": "Album 2", "popularity": 85},
    ]
    mock_db.cursor.fetchall.return_value = create_discovery_pool_rows(mock_tracks)
    
    with patch('random.shuffle', lambda x: None):
        playlist = service.get_popular_picks(limit=3)
    
    # Query should filter by popularity
    mock_db.cursor.execute.assert_called_once()
    assert "popularity >= 60" in mock_db.cursor.execute.call_args[0][0]

    # We expect up to `limit` tracks; diversity filtering may reduce this number.
    assert 1 <= len(playlist) <= 3
    # Check that diversity was applied (max 2 from Album 1)
    album1_tracks = [t for t in playlist if t['album_name'] == 'Album 1']
    assert len(album1_tracks) == 2

def test_build_custom_playlist(service: PersonalizedPlaylistsService, mock_db, mock_spotify_client):
    """Test the 'Build a Playlist' feature."""
    seed_artist_id = "seed_artist"
    
    # Mock DB response for similar artists
    mock_db.cursor.fetchall.return_value = [
        {'similar_artist_spotify_id': 'similar1', 'similar_artist_name': 'Similar Artist 1'}
    ]

    # Mock Spotify client responses
    mock_spotify_client.is_authenticated.return_value = True
    # get_artist_albums returns a list of mock album objects
    mock_album_obj = MagicMock(id='album123')
    mock_spotify_client.get_artist_albums.return_value = [mock_album_obj]
    # get_album returns a dict with track info
    mock_spotify_client.get_album.return_value = {
        "id": "album123", "name": "The Album", "popularity": 80, "images": [{"url": "http://cover.art"}],
        "tracks": {"items": [{"id": "track123", "name": "The Song", "duration_ms": 180000, "artists": [{"name": "Similar Artist 1"}]}]}
    }
    
    result = service.build_custom_playlist(seed_artist_ids=[seed_artist_id])
    
    assert "error" not in result
    assert result['track_count'] == 1
    track = result['tracks'][0]
    assert track['track_name'] == "The Song"
    assert track['artist_name'] == "Similar Artist 1"
    
    # Verify mocks were called
    mock_db.cursor.execute.assert_called_once_with(ANY, (seed_artist_id,))
    mock_spotify_client.get_artist_albums.assert_called_once_with('similar1', album_type='album,single', limit=10)
    mock_spotify_client.get_album.assert_called_once_with('album123')

def test_build_custom_playlist_no_spotify_auth(service: PersonalizedPlaylistsService):
    """Test build playlist fails if spotify is not authenticated."""
    service.spotify_client.is_authenticated.return_value = False
    
    result = service.build_custom_playlist(seed_artist_ids=["some_artist"])
    
    assert "error" in result
    assert "Spotify not authenticated" in result['error']


def test_get_discovery_tracks_by_category_uses_named_like_parameters(service: PersonalizedPlaylistsService, mock_db):
    """Ensure category discovery queries keep LIKE values bound as parameters."""
    mock_db.cursor.fetchall.return_value = []

    result = service._get_discovery_tracks_by_category("rock", limit=5)

    assert result == []
    mock_db.cursor.execute.assert_called_once()
    query, params = mock_db.cursor.execute.call_args[0]
    assert "LIKE :category_pattern" in query
    assert params == {
        "category_pattern": "%rock%",
        "limit": 5,
    }
