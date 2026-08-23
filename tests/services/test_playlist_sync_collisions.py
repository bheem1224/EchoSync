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


def test_extended_mix_duration_amnesty():
    """Verify that extended/club tags with <=2000ms duration delta receive duration amnesty, while >2000ms or non-extended fail."""
    from core.matching_engine.matching_engine import evaluate_version_compatibility

    # Case 1: Candidate is erroneously tagged Extended Mix, but duration delta is 1000ms <= 2000ms -> Passes
    is_compat, penalty, reason = evaluate_version_compatibility(
        source_version=None,
        candidate_version="Extended Mix",
        duration_delta_ms=1000,
    )
    assert is_compat is True
    assert penalty == 0.0
    assert "Duration amnesty" in reason

    # Case 2: Candidate is tagged Extended Mix with duration delta 6000ms > 2000ms -> Fails
    is_compat, penalty, reason = evaluate_version_compatibility(
        source_version=None,
        candidate_version="Extended Mix",
        duration_delta_ms=6000,
    )
    assert is_compat is False
    assert "Version mismatch" in reason

    # Case 3: Candidate is tagged Live with duration delta 1000ms <= 2000ms -> Fails (non-extended not amnestied)
    is_compat, penalty, reason = evaluate_version_compatibility(
        source_version=None,
        candidate_version="Live",
        duration_delta_ms=1000,
    )
    assert is_compat is False
    assert "Version mismatch" in reason


def test_remixer_safe_semantic_equivalence():
    """Verify generic remix matches specific remixes, while conflicting specific remixers fail."""
    from core.matching_engine.matching_engine import evaluate_version_compatibility

    # Generic vs Specific: "Remix" vs "Mellen Gi Remix" -> Passes
    is_compat, penalty, reason = evaluate_version_compatibility(
        source_version="Remix",
        candidate_version="Mellen Gi Remix",
    )
    assert is_compat is True
    assert penalty == 0.0
    assert "Generic semantic remix match" in reason

    # Specific vs Generic: "Steve Aoki Remix" vs "Remix" -> Passes
    is_compat, penalty, reason = evaluate_version_compatibility(
        source_version="Steve Aoki Remix",
        candidate_version="Remix",
    )
    assert is_compat is True
    assert penalty == 0.0
    assert "Generic semantic remix match" in reason

    # Compatible Specific: "Steve Aoki Remix" vs "Steve Aoki Extended Remix" -> Passes
    is_compat, penalty, reason = evaluate_version_compatibility(
        source_version="Steve Aoki Remix",
        candidate_version="Steve Aoki Extended Remix",
    )
    assert is_compat is True
    assert "Compatible specific remixers" in reason

    # Contradicting Specific: "Seeb Remix" vs "Mellen Gi Remix" -> Fails
    is_compat, penalty, reason = evaluate_version_compatibility(
        source_version="Seeb Remix",
        candidate_version="Mellen Gi Remix",
    )
    assert is_compat is False
    assert penalty == 70.0
    assert "Contradicting specific remixers" in reason


def test_tier2_unknown_artist_title_recovery():
    """Verify Unknown Artist files with encapsulated 'Artist - Title' in title receive full artist confidence in Tier 2."""
    from services.playlists_api import evaluate_tier2_candidate, check_title_recovery

    # Verify helper directly
    assert check_title_recovery(
        source_artist="BTS",
        source_title="Dynamite",
        candidate_artist="Unknown Artist",
        candidate_title="BTS - Dynamite",
    ) is True

    assert check_title_recovery(
        source_artist="BTS",
        source_title="Dynamite",
        candidate_artist="Different Artist",
        candidate_title="BTS - Dynamite",
    ) is False

    # Verify end-to-end evaluation
    engine = WeightedMatchingEngine(ExactSyncProfile())
    source = EchosyncTrack(
        raw_title="Dynamite",
        artist_name="BTS",
        album_title="Dynamite (DayTime Version)",
        duration=199000,
    )
    candidate = EchosyncTrack(
        raw_title="BTS - Dynamite",
        artist_name="Unknown Artist",
        album_title="",
        duration=199500,
    )

    result = evaluate_tier2_candidate(engine, source, candidate, artist_score=0.0)
    assert result.passed_version_check is True
    assert result.confidence_score >= 90.0


def test_unicode_multi_artist_splitting():
    """Verify that Unicode multiplication/cross (× / \\u00d7) and ' x ' split into separate artist records."""
    from core.matching_engine.text_utils import split_artists

    tokens1 = split_artists("Selena Gomez × Marshmello")
    assert tokens1 == ["Selena Gomez", "Marshmello"]

    tokens2 = split_artists("Marshmello \u00d7 Selena Gomez")
    assert tokens2 == ["Marshmello", "Selena Gomez"]

    tokens3 = split_artists("Selena Gomez x Marshmello")
    assert tokens3 == ["Selena Gomez", "Marshmello"]


def test_extended_mix_duration_amnesty_with_delta():
    """Verify that a studio length file tagged as extended receives duration amnesty when delta <= 2000ms."""
    engine = WeightedMatchingEngine(ExactSyncProfile())
    source = EchosyncTrack(
        raw_title="Happier",
        artist_name="Marshmello",
        album_title="Happier",
        duration=214285,  # 3:34
    )
    candidate = EchosyncTrack(
        raw_title="Happier",
        artist_name="Marshmello",
        album_title="Happier",
        duration=215000,  # 3:35 (delta = 715ms <= 2000ms)
        edition="Extended Mix",
    )

    result = engine.calculate_match(source, candidate)
    assert result.passed_version_check is True
    assert result.confidence_score >= 90.0
    assert "Duration amnesty" in result.reasoning


def test_remixer_token_collaborator_credit():
    """Verify that a remixer token named inside edition is credited as a collaborator for remix queries."""
    engine = WeightedMatchingEngine(ExactSyncProfile())
    source = EchosyncTrack(
        raw_title="In the End",
        artist_name="Tommee Profitt",
        album_title="In the End (Mellen Gi & Tommee Profitt Remix)",
        duration=218000,
        edition="Remix",
    )
    candidate = EchosyncTrack(
        raw_title="In the End",
        artist_name="Linkin Park",
        album_title="In the End",
        duration=218500,
        edition="Mellen Gi & Tommee Profitt Remix",
    )

    result = engine.calculate_match(source, candidate)
    assert result.passed_version_check is True
    assert result.confidence_score >= 85.0


def test_encapsulated_artist_title_recovery():
    """Verify 'Taio Cruz - Dynamite' with Unknown Artist resolves to 'Dynamite' by 'Taio Cruz'."""
    from services.playlists_api import evaluate_tier2_candidate

    engine = WeightedMatchingEngine(ExactSyncProfile())
    source = EchosyncTrack(
        raw_title="Dynamite",
        artist_name="Taio Cruz",
        album_title="Rokstarr",
        duration=203000,
    )
    candidate = EchosyncTrack(
        raw_title="Taio Cruz - Dynamite",
        artist_name="Unknown Artist",
        album_title="",
        duration=203500,
    )

    result = evaluate_tier2_candidate(engine, source, candidate, artist_score=0.0)
    assert result.passed_version_check is True
    assert result.confidence_score >= 90.0
    assert candidate.artist_name == "Taio Cruz"
    assert candidate.title == "Dynamite"


def test_scan_modes_execution(tmp_path, monkeypatch):
    """Verify scan_mode parameter execution across incremental, force_rescan, and full_rebuild modes."""
    from services.library_sync_service import LibrarySyncService
    from core.settings import config_manager
    from database.music_database import MusicDatabase

    # Setup dummy directory and test database
    lib_dir = tmp_path / "music"
    lib_dir.mkdir(parents=True)
    db_file = tmp_path / "test_scan_modes.db"
    from database.music_database import Base
    db = MusicDatabase(str(db_file))
    Base.metadata.create_all(db.engine)

    orig_get = config_manager.get
    monkeypatch.setattr(config_manager, "get", lambda k: str(lib_dir) if "library_dir" in k else orig_get(k))

    service = LibrarySyncService(database_path=str(db_file))
    # Test all 3 modes can execute without exception
    service.sync_library(scan_mode="incremental")
    service.sync_library(scan_mode="force_rescan")
    service.sync_library(scan_mode="full_rebuild")


def test_unicode_cross_artist_splitting():
    """Verify split_artists handles Unicode cross/multiplication variants and Ha characters."""
    from core.matching_engine.text_utils import split_artists

    # Mathematical multiplication cross (U+00D7: ×)
    res1 = split_artists("Marshmello × Anne-Marie")
    assert res1 == ["Marshmello", "Anne-Marie"]

    # Fullwidth / heavy cross variants (U+2715: ✕, U+2716: ✖)
    res2 = split_artists("Galantis ✕ Ship Wrek")
    assert res2 == ["Galantis", "Ship Wrek"]

    res3 = split_artists("KSHMR ✖ Stefy De Cicco")
    assert res3 == ["KSHMR", "Stefy De Cicco"]

    # Cyrillic small letter ha (U+0445: х)
    res4 = split_artists("Alan Walker \u0445 Ava Max")
    assert res4 == ["Alan Walker", "Ava Max"]


def test_ingestion_remixer_extraction_to_junction(tmp_path):
    """Verify ingestion pipeline extracts remixer entities and attaches role='remixer' to track_artists."""
    from database.music_database import MusicDatabase, Base, Track, Artist, TrackArtist
    from core.database.repositories.track_repo import TrackRepository
    from core.db.echo_sync_track import EchosyncTrack, EchosyncMedia

    db_file = tmp_path / "test_remixer_junction.db"
    db = MusicDatabase(str(db_file))
    Base.metadata.create_all(db.engine)

    with db.session_factory() as session:
        track = EchosyncTrack(
            raw_title="In the End (Mellen Gi & Tommee Profitt Remix)",
            artist_name="Linkin Park",
            album_title="Hybrid Theory",
            edition="Mellen Gi & Tommee Profitt Remix",
            duration=218000,
            media=[
                EchosyncMedia(
                    file_path=str(tmp_path / "in_the_end_remix.flac"),
                    file_format="FLAC",
                )
            ],
        )
        TrackRepository.resolve_artists_and_albums(session, [track])
        TrackRepository.bulk_upsert_tracks(session, [track])
        session.commit()

        # Verify track record
        db_track = session.query(Track).first()
        assert db_track is not None
        assert db_track.edition == "Remix"

        # Verify primary artist
        primary_artist = session.query(Artist).filter_by(name="Linkin Park").first()
        assert primary_artist is not None
        assert db_track.artist_id == primary_artist.id

        # Verify remixer artists in junction table
        mellen = session.query(Artist).filter_by(name="Mellen Gi").first()
        tommee = session.query(Artist).filter_by(name="Tommee Profitt").first()
        assert mellen is not None
        assert tommee is not None

        remixer_links = (
            session.query(TrackArtist)
            .filter_by(track_id=db_track.id, role="remixer")
            .all()
        )
        remixer_artist_ids = {link.artist_id for link in remixer_links}
        assert mellen.id in remixer_artist_ids
        assert tommee.id in remixer_artist_ids


def test_unidentifiable_file_ejection_and_cascade_purge(tmp_path, monkeypatch):
    """Verify unidentifiable media files are ejected to download directory and cascade purged from DB."""
    import echosync_core
    from services.library_sync_service import LibrarySyncService
    from database.music_database import MusicDatabase, Base, Track, Artist, Album, LocalMedia
    from core.database.repositories.track_repo import TrackRepository
    from core.db.echo_sync_track import EchosyncTrack, EchosyncMedia
    from core.settings import config_manager

    lib_dir = tmp_path / "music"
    lib_dir.mkdir(parents=True)
    dl_dir = tmp_path / "downloads"
    dl_dir.mkdir(parents=True)
    db_file = tmp_path / "test_ejection.db"

    db = MusicDatabase(str(db_file))
    Base.metadata.create_all(db.engine)

    # 1. Create a dummy untagged wav file in library
    bad_file = lib_dir / "corrupted_untagged.wav"
    bad_file.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")

    # 2. Mock echosync_core.extract_metadata to return empty title/artist
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda path: {
            "title": "",
            "raw_title": "",
            "artist_name": "Unknown Artist",
            "artist": "Unknown Artist",
            "album_title": "",
            "duration": 5000,
            "file_path": str(path),
        }
    )

    orig_get = config_manager.get
    monkeypatch.setattr(
        config_manager,
        "get",
        lambda k: str(lib_dir) if "library_dir" in k else (str(dl_dir) if "download_dir" in k else orig_get(k))
    )

    # Seed the DB with a record pointing to bad_file to test cascade purge
    with db.session_factory() as session:
        track = EchosyncTrack(
            raw_title="Unknown Title",
            artist_name="Unknown Artist",
            album_title="",
            duration=5000,
            media=[
                EchosyncMedia(
                    file_path=str(bad_file),
                    file_format="WAV",
                )
            ],
        )
        TrackRepository.resolve_artists_and_albums(session, [track])
        TrackRepository.bulk_upsert_tracks(session, [track])
        session.commit()

        assert session.query(LocalMedia).count() == 1
        assert session.query(Track).count() == 1

    # Run library sync
    service = LibrarySyncService(database_path=str(db_file))
    service.sync_library(scan_mode="force_rescan")

    # File should no longer be in library directory
    assert not bad_file.exists()
    # File should have moved to downloads directory
    ejected_file = dl_dir / "corrupted_untagged.wav"
    assert ejected_file.exists()

    # DB state should be cleanly cascade-purged
    with db.session_factory() as session:
        assert session.query(LocalMedia).count() == 0
        assert session.query(Track).count() == 0


def test_acoustid_duration_integer_rounding():
    """Verify that floating point durations (e.g. 384.44, 179.4) are normalized to rounded integers."""
    from plugins.EchoSync.acoustid.client import AcoustIDProvider
    from web.routes.metadata_review import _normalize_duration_seconds, _coerce_int
    from pathlib import Path

    # 1. Test _coerce_int with float strings and floats
    assert _coerce_int("384.44") == 384
    assert _coerce_int(179.4) == 179
    assert _coerce_int("179.6") == 180
    assert _coerce_int(240000) == 240000

    # 2. Test _normalize_duration_seconds with ms and float durations
    meta_sec = {"duration": "179.4"}
    assert _normalize_duration_seconds(meta_sec, Path("dummy.mp3")) == 179

    meta_ms = {"duration_ms": 179600}
    assert _normalize_duration_seconds(meta_ms, Path("dummy.mp3")) == 180

    meta_high_sec = {"duration": 180000}
    assert _normalize_duration_seconds(meta_high_sec, Path("dummy.mp3")) == 180

    # 3. Test AcoustIDProvider payload generation
    provider = AcoustIDProvider()
    class DummyHTTP:
        def post(self, url, data):
            self.last_data = data
            class DummyResp:
                status_code = 200
                def json(self):
                    return {"status": "ok", "results": []}
            return DummyResp()

    dummy_http = DummyHTTP()
    provider.http = dummy_http
    provider.config = {"api_key": "test_key"}

    # Pass float duration 384.44
    provider.resolve_fingerprint_details("dummy_fingerprint", 384.44)
    assert dummy_http.last_data["duration"] == 384
    assert isinstance(dummy_http.last_data["duration"], int)


def test_filename_hyphen_parsing():
    """Verify that '04 - A Drawing-Down of Blinds.wav' parses title without corrupting internal hyphens."""
    from core.matching_engine.track_parser import TrackParser
    from services.auto_importer import parse_fallback_filename
    from pathlib import Path

    raw_filename = "04 - A Drawing-Down of Blinds.wav"

    # Test auto_importer fallback helper
    artist_hint, title_hint = parse_fallback_filename(Path(raw_filename))
    assert artist_hint is None
    assert title_hint == "A Drawing-Down of Blinds"

    # Test TrackParser on raw filename
    parser = TrackParser()
    track = parser.parse_filename(raw_filename)
    assert track is not None
    assert track.title == "A Drawing-Down of Blinds"

    # Test Artist - Title with internal hyphens
    track_with_artist = parser.parse_filename("01 - The Artist - A Drawing-Down of Blinds.flac")
    assert track_with_artist is not None
    assert track_with_artist.artist_name.lower() == "the artist"
    assert track_with_artist.title == "A Drawing-Down of Blinds"


def test_review_approval_suppresses_watcher(tmp_path, monkeypatch):
    """Verify that review approval suppresses watcher events during destination move."""
    from services.library_watcher import suppress_path, is_path_suppressed

    dest_file = tmp_path / "library" / "Artist" / "Album" / "Track.mp3"
    dest_path_str = str(dest_file)

    assert is_path_suppressed(dest_path_str) is False

    with suppress_path(dest_path_str):
        assert is_path_suppressed(dest_path_str) is True

    assert is_path_suppressed(dest_path_str) is False




