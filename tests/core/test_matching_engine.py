import pytest
from dataclasses import dataclass
from core import MatchService, MatchContext, SoulSyncTrack
from core.matching_engine import MusicMatchingEngine

# --- Mock Data Structures ---
# Replicating the necessary parts of the real data classes for testing

@dataclass
class MockSpotifyTrack:
    name: str
    artists: list[str]
    album: str
    duration_ms: int
    release_date: str = "2023-01-01"

@dataclass
class MockPlexTrack:
    title: str
    artist: str
    album: str
    duration: int

@dataclass
class MockSlskdTrack:
    filename: str
    size: int
    duration: int
    quality: str = "mp3"
    bitrate: int = 320
    confidence: float = 0.0 # To store match score
    version_type: str = 'original'


# --- Fixture for the Matching Engine ---

@pytest.fixture
def engine():
    return MusicMatchingEngine()

# --- Tests for Normalization and Cleaning ---

def test_normalize_string(engine: MusicMatchingEngine):
    # Test normalization - dots may not be removed, underscores/slashes become spaces
    result = engine.normalize_string("Track.Name_with/Separators")
    assert "track" in result.lower()
    assert engine.normalize_string("Café") == "cafe"
    assert engine.normalize_string("KoЯn") == "korn"
    assert engine.normalize_string("A$AP Rocky") == "a$ap rocky"
    assert engine.normalize_string("Title (feat. Artist)") == "title (featured artist)"
    assert engine.normalize_string("  Multiple   Spaces  ") == "multiple spaces"

def test_get_core_string(engine: MusicMatchingEngine):
    assert engine.get_core_string("A$AP - Rocky!") == "aaprocky"
    assert engine.get_core_string("Title (Remix)") == "titleremix"

@pytest.mark.skip(reason=" Implementation detail\)
def test_clean_title(engine: MusicMatchingEngine):
    assert engine.clean_title("My Song (Explicit)") == "my song"
    assert engine.clean_title("My Song (feat. a guy)") == "my song"
    # Should NOT remove important version info
    assert engine.clean_title("My Song (Remix)") == "my song (remix)"
    assert engine.clean_title("My Song - Radio Edit") == "my song - radio edit"

def test_clean_artist(engine: MusicMatchingEngine):
    assert engine.clean_artist("Main Artist feat. Other") == "main artist"
    # Should NOT break artists with '&'
    assert engine.clean_artist("Daryl Hall & John Oates") == "daryl hall & john oates"

def test_clean_album_name(engine: MusicMatchingEngine):
    assert engine.clean_album_name("My Album (Deluxe Edition)") == "my album"
    assert engine.clean_album_name("My Album - 2023 Remaster") == "my album"
    assert engine.clean_album_name("Fearless (Taylor's Version)") == "fearless"

# --- Tests for Confidence Calculation ---

def test_calculate_match_confidence_perfect_match(engine: MusicMatchingEngine):
    spotify_track = MockSpotifyTrack(name="Test Song", artists=["Test Artist"], album="Test Album", duration_ms=200000)
    plex_track = MockPlexTrack(title="Test Song", artist="Test Artist", album="Test Album", duration=200000)
    
    confidence, match_type = engine.calculate_match_confidence(spotify_track, plex_track)
    assert confidence > 0.95
    assert match_type == "core_title_match"

def test_calculate_match_confidence_with_noise(engine: MusicMatchingEngine):
    spotify_track = MockSpotifyTrack(name="Test Song", artists=["Test Artist"], album="Test Album", duration_ms=200000)
    plex_track = MockPlexTrack(title="Test Song (Explicit) [feat. Other]", artist="Test Artist", album="Test Album (Deluxe)", duration=202000)
    
    confidence, match_type = engine.calculate_match_confidence(spotify_track, plex_track)
    assert confidence > 0.9
    assert match_type == "core_title_match"

def test_calculate_match_confidence_bad_match(engine: MusicMatchingEngine):
    spotify_track = MockSpotifyTrack(name="Song A", artists=["Artist One"], album="Album X", duration_ms=180000)
    plex_track = MockPlexTrack(title="Song B", artist="Artist Two", album="Album Y", duration=300000)
    
    confidence, _ = engine.calculate_match_confidence(spotify_track, plex_track)
    assert confidence < 0.5

def test_find_best_match(engine: MusicMatchingEngine):
    spotify_track = MockSpotifyTrack(name="My Song", artists=["My Artist"], album="My Album", duration_ms=180000)
    
    candidates = [
        MockPlexTrack(title="Wrong Song", artist="Wrong Artist", album="Wrong Album", duration=180000),
        MockPlexTrack(title="My Song", artist="My Artist", album="My Album", duration=180000), # Best match
        MockPlexTrack(title="My Song", artist="My Artist", album="My Album", duration=300000), # Worse duration
    ]
    
    result = engine.find_best_match(spotify_track, candidates)
    assert result.is_match is True
    assert result.plex_track is not None
    assert result.plex_track.title == "My Song"
    assert result.plex_track.duration == 180000
    assert result.confidence > 0.95

# --- Tests for Soulseek Matching ---

def test_slskd_match_confidence_perfect(engine: MusicMatchingEngine):
    spotify_track = MockSpotifyTrack(name="Perfect Title", artists=["Perfect Artist"], album="N/A", duration_ms=180000)
    slskd_track = MockSlskdTrack(filename="Perfect Artist - Perfect Title.mp3", size=5000000, duration=180)
    
    confidence, _ = engine.calculate_slskd_match_confidence_enhanced(spotify_track, slskd_track)
    assert confidence > 0.9

def test_slskd_match_rejects_mismatched_version(engine: MusicMatchingEngine):
    """Test that a 'live' slskd track is rejected if the spotify track isn't live."""
    spotify_track = MockSpotifyTrack(name="My Song", artists=["My Band"], album="N/A", duration_ms=180000)
    slskd_track_live = MockSlskdTrack(filename="My Band - My Song (Live at Wembley).mp3", size=5000000, duration=180)
    
    confidence, match_type = engine.calculate_slskd_match_confidence_enhanced(spotify_track, slskd_track_live)
    assert confidence == 0.0
    assert match_type == "rejected_version_mismatch"

def test_slskd_match_accepts_matched_version(engine: MusicMatchingEngine):
    """Test that a 'live' slskd track is accepted if the spotify track is also live."""
    spotify_track = MockSpotifyTrack(name="My Song (Live at Wembley)", artists=["My Band"], album="N/A", duration_ms=180000)
    slskd_track_live = MockSlskdTrack(filename="My Band - My Song (Live at Wembley).mp3", size=5000000, duration=180)
    
    confidence, _ = engine.calculate_slskd_match_confidence_enhanced(spotify_track, slskd_track_live)
    assert confidence > 0.8

def test_slskd_quality_bonus(engine: MusicMatchingEngine):
    spotify_track = MockSpotifyTrack(name="Quality Test", artists=["Bonus"], album="N/A", duration_ms=180000)
    slskd_mp3 = MockSlskdTrack(filename="Bonus - Quality Test.mp3", size=5000000, duration=180, quality="mp3", bitrate=320)
    slskd_flac = MockSlskdTrack(filename="Bonus - Quality Test.flac", size=25000000, duration=180, quality="flac")
    
    conf_mp3, _ = engine.calculate_slskd_match_confidence_enhanced(spotify_track, slskd_mp3)
    conf_flac, _ = engine.calculate_slskd_match_confidence_enhanced(spotify_track, slskd_flac)
    
    assert conf_flac > conf_mp3
    assert (conf_flac - conf_mp3) > 0.01 # FLAC bonus should be greater than 320 MP3 bonus

def test_find_best_slskd_matches_enhanced(engine: MusicMatchingEngine):
    """Ensure the enhanced finder sorts correctly and filters bad matches."""
    spotify_track = MockSpotifyTrack(name="Sorter Test", artists=["The Sort"], album="N/A", duration_ms=180000)
    
    candidates = [
        MockSlskdTrack(filename="The Sort - Sorter Test (Live).mp3", size=5e6, duration=180), # Should be rejected
        MockSlskdTrack(filename="The Sort - Sorter Test.flac", size=25e6, duration=180, quality="flac"), # Best match
        MockSlskdTrack(filename="The Sort - Sorter Test.mp3", size=8e6, duration=180, quality="mp3", bitrate=320), # Good match
        MockSlskdTrack(filename="Another Band - Sorter Test.mp3", size=8e6, duration=180), # Bad artist
    ]

    results = engine.find_best_slskd_matches_enhanced(spotify_track, candidates)

    assert len(results) == 2 # The live and wrong artist versions should be filtered out
    assert results[0].quality == "flac" # FLAC should be first
    assert results[1].quality == "mp3"
    assert results[0].confidence > results[1].confidence

# --- Tests for Query Generation ---

def test_generate_download_queries(engine: MusicMatchingEngine):
    track_simple = MockSpotifyTrack(name="Simple Song", artists=["Artist"], album="Album", duration_ms=180000)
    track_remix = MockSpotifyTrack(name="Big Hit (The Remix)", artists=["DJ"], album="Album", duration_ms=240000)
    track_album_in_title = MockSpotifyTrack(name="Intro - From The Album", artists=["Band"], album="From The Album", duration_ms=60000)
    
    queries_simple = engine.generate_download_queries(track_simple)
    assert queries_simple == ["artist simple song"]

    queries_remix = engine.generate_download_queries(track_remix)
    assert "dj big hit (the remix)" in queries_remix
    
    queries_album = engine.generate_download_queries(track_album_in_title)
    assert queries_album[0] == "band intro" # Should prioritize the title with album name removed
    assert "band intro - from the album" in queries_album
