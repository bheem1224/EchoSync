import pytest
from services.playlists_api import resolve_duplicate_matches
from core.matching_engine.matching_engine import WeightedMatchingEngine, get_version_family
from core.matching_engine.scoring_profile import ExactSyncProfile
from core.db.echo_sync_track import EchosyncTrack


def test_resolve_duplicate_matches_winner_take_all_and_relegation():
    """Test that when multiple source tracks claim the same local track ID, the highest score wins."""
    all_tracks = [
        {
            "title": "Rewrite The Stars",
            "artist": "James Arthur & Anne-Marie",
            "matched_track_id": 8149,
            "match_score": 95.0,
            "library_match": "Found",
            "target_identifier": "plex://123",
            "candidate_matches": [
                {"id": 8149, "score": 95.0, "target_identifier": "plex://123"}
            ],
        },
        {
            "title": "Rewrite The Stars",
            "artist": "Zac Efron & Zendaya",
            "matched_track_id": 8149,
            "match_score": 75.0,
            "library_match": "Found (score: 75%)",
            "target_identifier": "plex://123",
            "candidate_matches": [
                {"id": 8149, "score": 75.0, "target_identifier": "plex://123"}
            ],
        },
    ]

    resolved = resolve_duplicate_matches(all_tracks)

    # James Arthur entry should win
    assert resolved[0]["matched_track_id"] == 8149
    assert resolved[0]["match_score"] == 95.0
    assert resolved[0]["library_match"] == "Found"

    # Zac Efron entry should lose and be marked unmatched
    assert resolved[1]["matched_track_id"] is None
    assert resolved[1]["library_match"] == "Not Found"
    assert resolved[1]["target_identifier"] is None
    assert resolved[1]["target_exists"] is False
    assert "Collision" in resolved[1].get("rejection_reason", "")
    assert "James Arthur" in resolved[1].get("rejection_reason", "")


def test_resolve_duplicate_matches_fallback_to_second_candidate():
    """Test that a loser in a collision falls back to its next best candidate if available."""
    all_tracks = [
        {
            "title": "Song A",
            "artist": "Artist 1",
            "matched_track_id": 100,
            "match_score": 92.0,
            "library_match": "Found",
            "target_identifier": "plex://100",
            "candidate_matches": [
                {"id": 100, "score": 92.0, "target_identifier": "plex://100"}
            ],
        },
        {
            "title": "Song A",
            "artist": "Artist 2",
            "matched_track_id": 100,
            "match_score": 85.0,
            "library_match": "Found",
            "target_identifier": "plex://100",
            "candidate_matches": [
                {"id": 100, "score": 85.0, "target_identifier": "plex://100"},
                {"id": 101, "score": 78.0, "target_identifier": "plex://101"},
            ],
        },
    ]

    resolved = resolve_duplicate_matches(all_tracks)

    # Artist 1 wins 100
    assert resolved[0]["matched_track_id"] == 100
    assert resolved[0]["match_score"] == 92.0

    # Artist 2 falls back to 101
    assert resolved[1]["matched_track_id"] == 101
    assert resolved[1]["match_score"] == 78.0
    assert resolved[1]["target_identifier"] == "plex://101"
    assert resolved[1]["library_match"] == "Found (score: 78%)"


def test_matching_engine_rejects_cover_versions_across_artist_boundaries():
    """Verify that distinct recognized artists (covers) score 0.0 and do not trigger Rescue B."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="Rewrite The Stars",
        artist_name="James Arthur & Anne-Marie",
        album_title="The Greatest Showman: Reimagined",
        duration=217000,
    )
    candidate = EchosyncTrack(
        raw_title="Rewrite The Stars",
        artist_name="Zac Efron & Zendaya",
        album_title="The Greatest Showman",
        duration=217000,
    )

    result = engine.calculate_match(source, candidate)

    # Must be completely rejected with 0.0 confidence
    assert result.confidence_score == 0.0
    assert result.fuzzy_text_score < 0.70


def test_matching_engine_accepts_same_artist_and_collaborator_variations():
    """Verify that matching primary artists or legitimate collaborator subsets match confidently."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="Mama",
        artist_name="Jonas Blue feat. William Singe",
        album_title="Blue",
        duration=184000,
    )
    candidate = EchosyncTrack(
        raw_title="Mama",
        artist_name="Jonas Blue, William Singe",
        album_title="Blue",
        duration=184000,
    )

    result = engine.calculate_match(source, candidate)
    assert result.confidence_score >= 85.0


def test_version_family_extraction_karaoke_and_sea_shanty():
    """Verify get_version_family extracts karaoke and sea shanty qualifiers."""
    assert get_version_family("Karaoke Version") == "karaoke"
    assert get_version_family("Sea Shanty") == "sea_shanty"
    assert get_version_family("Wellerman (Sea Shanty)") == "sea_shanty"
    assert get_version_family("Acoustic Version") == "piano"  # grouped under acoustic/piano
