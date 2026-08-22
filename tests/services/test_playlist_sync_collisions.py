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


def test_wellerman_sea_shanty_version_equivalence():
    """Verify that 'Wellerman - Sea Shanty' matches canonical 'Wellerman' via subtitle descriptor equivalence."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="Wellerman - Sea Shanty",
        artist_name="Nathan Evans",
        album_title="Wellerman",
        duration=155000,
        edition="Sea Shanty",
    )
    candidate = EchosyncTrack(
        raw_title="Wellerman",
        artist_name="Nathan Evans",
        album_title="Wellerman",
        duration=155000,
    )

    result = engine.calculate_match(source, candidate)
    assert result.passed_version_check is True
    assert result.confidence_score >= 85.0
    assert "Subtitle descriptor equivalence" in result.reasoning or result.version_penalty_applied == 0.0


def test_tier2_escalation_blocked_on_distinct_artist_cover():
    """Verify check_cover_rejection blocks Tier 2 escalation for distinct artist covers."""
    from services.playlists_api import check_cover_rejection

    candidate_diagnostics = [
        {
            "candidate": {
                "title": "Rewrite The Stars",
                "artist": "Zac Efron & Zendaya",
                "duration": 217000,
            },
            "result": {
                "score": 0.0,
                "passed_version": True,
                "passed_edition": True,
                "fuzzy_text": 0.50,
                "duration_score": 1.0,
                "quality_bonus": 0.0,
                "version_penalty": 0.0,
                "edition_penalty": 0.0,
            },
            "reasoning": "Artist boundary mismatch: 'James Arthur & Anne-Marie' vs 'Zac Efron & Zendaya' are distinct artists (score: 0.0)",
        }
    ]

    is_cover_rejected = check_cover_rejection(
        source_title="Rewrite The Stars",
        source_artist="James Arthur & Anne-Marie",
        candidate_diagnostics=candidate_diagnostics,
    )
    assert is_cover_rejected is True


def test_girls_like_you_cardi_b_version_matches_library_cut():
    """Verify that 'Girls Like You - Cardi B Version' (3:55) matches local 'Girls Like You' (feat. Cardi B, 3:55)."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="Girls Like You - Cardi B Version",
        artist_name="Maroon 5",
        album_title="Girls Like You",
        duration=235545,  # 3:55
        edition="Cardi B Version",
    )
    candidate = EchosyncTrack(
        raw_title="Girls Like You",
        artist_name="Maroon 5 feat. Cardi B",
        album_title="Girls Like You",
        duration=235545,  # 3:55
    )

    result = engine.calculate_match(source, candidate)
    assert result.passed_version_check is True
    assert result.confidence_score >= 85.0


def test_single_version_studio_release_equivalence():
    """Verify that 'All The Things She Said' matches 'All The Things She Said (Single Version)' when durations align."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="All The Things She Said",
        artist_name="t.A.T.u.",
        album_title="200 km/h in the Wrong Lane",
        duration=214440,
    )
    candidate = EchosyncTrack(
        raw_title="All The Things She Said",
        artist_name="t.A.T.u.",
        album_title="200 km/h in the Wrong Lane",
        duration=214440,
        edition="Single Version",
    )

    result = engine.calculate_match(source, candidate)
    assert result.passed_version_check is True
    assert result.confidence_score >= 85.0


def test_tribute_band_substring_rejection():
    """Verify that 'Maroon 5' vs 'The Maroon 5 Tribute Band' does not receive containment boost and fails matching."""
    from core.matching_engine.text_utils import _cmp_artists
    engine = WeightedMatchingEngine(ExactSyncProfile())

    art_score = _cmp_artists("Maroon 5", "The Maroon 5 Tribute Band")
    assert art_score < 0.50

    source = EchosyncTrack(
        raw_title="Sugar",
        artist_name="Maroon 5",
        album_title="V",
        duration=235000,
    )
    candidate = EchosyncTrack(
        raw_title="Sugar",
        artist_name="The Maroon 5 Tribute Band",
        album_title="Tribute to Maroon 5",
        duration=235000,
    )

    result = engine.calculate_match(source, candidate)
    assert result.confidence_score == 0.0


def test_compilation_soundtrack_performer_resolution():
    """Verify that 'This Is Me' by 'Keala Settle' matches a track on a 'Various Artists' soundtrack album."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="This Is Me",
        artist_name="Keala Settle",
        album_title="The Greatest Showman (Original Motion Picture Soundtrack)",
        duration=234000,
    )
    candidate = EchosyncTrack(
        raw_title="This Is Me",
        artist_name="Various Artists",
        album_title="The Greatest Showman (Original Motion Picture Soundtrack)",
        album_artist="Various Artists",
        duration=234000,
    )

    result = engine.calculate_match(source, candidate)
    assert result.passed_version_check is True
    assert result.confidence_score >= 85.0


def test_recursive_stacked_parenthetical_decomposition():
    """Verify that complex stacked parentheticals decompose cleanly into title, collaborators, soundtrack, and version."""
    from core.matching_engine.text_utils import decompose_complex_title

    raw = 'Rewrite The Stars (feat. Anne-Marie) [From "The Greatest Showman: Reimagined"] (Radio Edit)'
    parsed = decompose_complex_title(raw)

    assert parsed["clean_title"] == "Rewrite The Stars"
    assert "Anne-Marie" in parsed["collaborators"]
    assert "The Greatest Showman: Reimagined" in parsed["soundtrack"]
    assert parsed["version"] == "Radio Edit"


def test_whitespace_normalization_collapsing():
    """Verify that consecutive whitespace in titles collapses to single space."""
    from core.matching_engine.text_utils import normalize_title

    norm = normalize_title("Wavin'  Flag")
    assert norm == "wavin' flag"


def test_franchise_publisher_soundtrack_matching():
    """Verify that 'Legends Never Die' by 'League of Legends' matches 'Against the Current'."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="Legends Never Die",
        artist_name="League of Legends",
        album_title="Legends Never Die",
        duration=235000,
    )
    candidate = EchosyncTrack(
        raw_title="Legends Never Die",
        artist_name="Against the Current",
        album_title="Legends Never Die",
        duration=235000,
    )

    result = engine.calculate_match(source, candidate)
    assert result.passed_version_check is True
    assert result.confidence_score >= 85.0


def test_clean_studio_track_edition_isolation():
    """Verify that a studio track in an album folder does not inherit album edition tokens."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    # Studio candidate from a Deluxe album folder: track title is clean
    candidate = EchosyncTrack(
        raw_title="In the End",
        artist_name="Linkin Park",
        album_title="Hybrid Theory (Deluxe Edition)",
        duration=217312,  # 3:37
    )
    # Verify Track.edition is None (not polluted by album edition)
    assert candidate.edition is None

    source = EchosyncTrack(
        raw_title="In the End",
        artist_name="Linkin Park",
        album_title="Hybrid Theory",
        duration=216880,  # 3:36
    )

    result = engine.calculate_match(source, candidate)
    assert result.passed_version_check is True
    assert result.confidence_score >= 85.0


def test_tier2_evaluates_only_new_candidates():
    """Verify that Tier 2 skips candidates already evaluated and rejected in Tier 1."""
    from services.playlists_api import filter_unevaluated_candidates

    evaluated_candidate_ids = {101}
    tier2_raw_candidates = [
        (101, "Sweater Weather (Remix)", 240000, "Remix", "The Neighbourhood", 1, None, "Album A"),
        (102, "Sweater Weather", 240000, None, "The Neighbourhood", 1, None, "I Love You."),
    ]

    tier2_candidates = filter_unevaluated_candidates(tier2_raw_candidates, evaluated_candidate_ids)
    assert len(tier2_candidates) == 1
    assert tier2_candidates[0][0] == 102


def test_tier2_scores_artist_bonus_on_new_candidate():
    """Verify a candidate found in Tier 2 with the correct artist receives full match confidence."""
    from services.playlists_api import evaluate_tier2_candidate

    engine = WeightedMatchingEngine(ExactSyncProfile())
    source = EchosyncTrack(
        raw_title="Sweater Weather",
        artist_name="The Neighbourhood",
        album_title="I Love You.",
        duration=240000,
    )
    candidate = EchosyncTrack(
        raw_title="Sweater Weather",
        artist_name="The Neighbourhood",
        album_title="I Love You.",
        duration=240500,
    )

    result = evaluate_tier2_candidate(engine, source, candidate, artist_score=1.0)
    assert result.passed_version_check is True
    assert result.confidence_score >= 90.0

