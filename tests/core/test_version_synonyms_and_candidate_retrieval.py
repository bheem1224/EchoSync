#!/usr/bin/env python3
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.db.echo_sync_track import EchosyncTrack
from core.matching_engine.matching_engine import WeightedMatchingEngine, sanitize_title_for_comparison
from core.matching_engine.scoring_profile import ExactSyncProfile
from database.music_database import Base, Artist, Album, Track, LocalMedia
from services.playlists_api import get_library_candidates, normalize_title_for_search, normalize_artist_for_search
from web.routes.playlists import _cmp_titles


def test_version_synonyms_piano_acoustic():
    profile = ExactSyncProfile()
    engine = WeightedMatchingEngine(profile)

    source = EchosyncTrack(
        raw_title="Clocks",
        artist_name="Coldplay",
        album_title="A Rush of Blood to the Head",
        edition="Piano Version",
        duration=300000,
    )
    candidate_piano = EchosyncTrack(
        raw_title="Clocks",
        artist_name="Coldplay",
        album_title="A Rush of Blood to the Head",
        edition="Piano",
        duration=300000,
    )
    candidate_acoustic = EchosyncTrack(
        raw_title="Clocks",
        artist_name="Coldplay",
        album_title="A Rush of Blood to the Head",
        edition="Acoustic",
        duration=300000,
    )

    res_piano = engine.calculate_match(source, candidate_piano)
    assert res_piano.passed_version_check is True
    assert res_piano.confidence_score >= 90.0

    res_acoustic = engine.calculate_match(source, candidate_acoustic)
    assert res_acoustic.passed_version_check is True
    assert res_acoustic.confidence_score >= 90.0


def test_version_synonyms_radio_single_edit():
    profile = ExactSyncProfile()
    engine = WeightedMatchingEngine(profile)

    source = EchosyncTrack(
        raw_title="Don't You Worry Child",
        artist_name="Swedish House Mafia",
        album_title="Until Now",
        edition="Radio Edit",
        duration=212000,
    )
    candidate_radio_ver = EchosyncTrack(
        raw_title="Don't You Worry Child",
        artist_name="Swedish House Mafia",
        album_title="Until Now",
        edition="Radio Version",
        duration=212000,
    )
    candidate_single_ver = EchosyncTrack(
        raw_title="Don't You Worry Child",
        artist_name="Swedish House Mafia",
        album_title="Until Now",
        edition="Single Version",
        duration=212000,
    )

    res_radio = engine.calculate_match(source, candidate_radio_ver)
    assert res_radio.passed_version_check is True
    assert res_radio.confidence_score >= 90.0

    res_single = engine.calculate_match(source, candidate_single_ver)
    assert res_single.passed_version_check is True
    assert res_single.confidence_score >= 90.0


def test_remaster_edition_compatibility_with_original():
    profile = ExactSyncProfile()
    engine = WeightedMatchingEngine(profile)

    # Source has no edition (Original)
    source = EchosyncTrack(
        raw_title="Karma Police",
        artist_name="Radiohead",
        album_title="OK Computer",
        edition="",
        duration=264000,
    )
    # Candidate is 2013 Remaster with 500ms difference (within 3000ms)
    candidate_remaster = EchosyncTrack(
        raw_title="Karma Police",
        artist_name="Radiohead",
        album_title="OK Computer",
        edition="2013 Remaster",
        duration=264500,
    )

    res = engine.calculate_match(source, candidate_remaster)
    assert res.passed_version_check is True
    assert res.confidence_score >= 90.0

    # If duration delta exceeds 3000ms, it should not pass
    candidate_remaster_diff = EchosyncTrack(
        raw_title="Karma Police",
        artist_name="Radiohead",
        album_title="OK Computer",
        edition="2013 Remaster",
        duration=270000,
    )
    res_diff = engine.calculate_match(source, candidate_remaster_diff)
    assert res_diff.passed_version_check is False or res_diff.confidence_score < 90.0


def test_remaster_title_sanitization_tier2():
    profile = ExactSyncProfile()
    engine = WeightedMatchingEngine(profile)

    source = EchosyncTrack(
        raw_title="Karma Police",
        artist_name="Unknown Artist",
        album_title="OK Computer",
        duration=264000,
    )
    candidate = EchosyncTrack(
        raw_title="Karma Police - 2013 Remaster",
        artist_name="Radiohead",
        album_title="OK Computer",
        duration=264500,
    )

    res = engine.calculate_title_duration_match(source, candidate)
    assert res.confidence_score >= 90.0
    assert "Title exact match" in res.reasoning


def test_remix_subtype_equivalence_and_families():
    from core.matching_engine.matching_engine import evaluate_version_compatibility

    # Generic 'Remix' vs specific remix names
    assert evaluate_version_compatibility("Remix", "Seeb Remix")[0] is True
    assert evaluate_version_compatibility("Remix", "dotEXE remix")[0] is True
    assert evaluate_version_compatibility("Remix", "Mellen Gi & Tommee Profitt Remix")[0] is True
    assert evaluate_version_compatibility("Mellen Gi Remix", "Tommee Profitt Remix")[0] is True

    # Piano Version vs Piano
    assert evaluate_version_compatibility("Piano Version", "Piano")[0] is True
    assert evaluate_version_compatibility("Piano", "Acoustic")[0] is True

    # Year Remaster vs Remastered
    assert evaluate_version_compatibility("2013 Remaster", "Remastered")[0] is True


def test_tier2_title_sanitization_remix_inputs():
    profile = ExactSyncProfile()
    engine = WeightedMatchingEngine(profile)

    source = EchosyncTrack(
        raw_title="In the End - Mellen Gi Remix",
        artist_name="Unknown Artist",
        album_title="In the End",
        duration=218000,
    )
    candidate = EchosyncTrack(
        raw_title="In the End",
        artist_name="Linkin Park",
        album_title="Hybrid Theory",
        duration=218500,
    )

    res = engine.calculate_title_duration_match(source, candidate)
    assert res.confidence_score >= 90.0
    assert "Title exact match" in res.reasoning


def test_subtitle_descriptor_failsafe_tokens():
    # Descriptors like Sea Shanty, UEFA EURO 2024 Song, Soundtrack, From "...", etc.
    score_shanty = _cmp_titles("Wellerman", "Wellerman - Sea Shanty", context_score=0.95)
    assert score_shanty >= 0.90

    score_euro = _cmp_titles("Fire", "Fire - Official UEFA EURO 2024 Song", context_score=0.95)
    assert score_euro >= 0.90

    score_soundtrack = _cmp_titles("Theme", "Theme (Original Soundtrack Version)", context_score=0.95)
    assert score_soundtrack >= 0.90

    # Part indicators & edit descriptors
    score_pt2 = _cmp_titles("Title", "Title Pt II", context_score=0.95)
    assert score_pt2 >= 0.90

    score_part1 = _cmp_titles("Title", "Title Part 1", context_score=0.95)
    assert score_part1 >= 0.90

    score_vol1 = _cmp_titles("Title", "Title Vol 1", context_score=0.95)
    assert score_vol1 >= 0.90

    score_gabry = _cmp_titles("Blue (Da Ba Dee)", "Blue (Da Ba Dee) - Gabry Ponte Ice Pop Radio Edit", context_score=0.95)
    assert score_gabry >= 0.90


def test_get_library_candidates_multi_retention_and_various_artists():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create Various Artists compilation album
    va_artist = Artist(name="Various Artists", normalized_name="various artists")
    session.add(va_artist)
    session.flush()

    rixton = Artist(name="Rixton", normalized_name="rixton")
    session.add(rixton)
    session.flush()

    album = Album(title="Now That's What I Call Music", artist_id=va_artist.id)
    session.add(album)
    session.flush()

    # Track by Rixton inside VA album
    track_studio = Track(
        title="Me And My Broken Heart",
        normalized_title="me and my broken heart",
        artist_id=rixton.id,
        album_id=album.id,
        duration=193000,
        sync_id="sync_rixton_1",
    )
    # Remix version of the track
    track_remix = Track(
        title="Me And My Broken Heart (Remix)",
        normalized_title="me and my broken heart remix",
        artist_id=rixton.id,
        album_id=album.id,
        duration=285000,
        sync_id="sync_rixton_2",
    )
    session.add_all([track_studio, track_remix])
    session.commit()

    candidates = get_library_candidates(session, "Me And My Broken Heart", "Rixton")
    assert len(candidates) == 2
    assert {c.duration for c in candidates} == {193000, 285000}


def test_multi_token_artist_expansion_tier1_candidates():
    """Verify collaborative artist strings retrieve local tracks tagged with primary or collaborator artists."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Track 1: Jonas Blue (local artist) for "Jonas Blue feat. William Singe - Mama"
    jb_artist = Artist(name="Jonas Blue", normalized_name="jonas blue")
    session.add(jb_artist)
    session.flush()

    mama_track = Track(
        title="Mama",
        normalized_title="mama",
        artist_id=jb_artist.id,
        duration=184000,
        sync_id="sync_mama_1",
    )
    session.add(mama_track)
    session.flush()

    mama_media = LocalMedia(
        track_id=mama_track.id,
        file_path="/music/Jonas Blue/Mama.flac",
        file_format="flac",
        bitrate=1411,
    )
    session.add(mama_media)

    # Track 2: W&W for "W&W & AXMO - Heaven Is A Place On Earth"
    ww_artist = Artist(name="W&W", normalized_name="w&w")
    session.add(ww_artist)
    session.flush()

    heaven_track = Track(
        title="Heaven Is A Place On Earth",
        normalized_title="heaven is a place on earth",
        artist_id=ww_artist.id,
        duration=172000,
        sync_id="sync_heaven_1",
    )
    session.add(heaven_track)
    session.flush()

    heaven_media = LocalMedia(
        track_id=heaven_track.id,
        file_path="/music/W&W/Heaven.flac",
        file_format="flac",
        bitrate=1411,
    )
    session.add(heaven_media)
    session.commit()

    # Query with featured collaborator
    res_mama = get_library_candidates(session, "Mama", "Jonas Blue feat. William Singe")
    assert len(res_mama) == 1
    assert res_mama[0].id == mama_track.id
    assert len(res_mama[0].media_files) == 1
    assert res_mama[0].media_files[0].file_format == "flac"

    # Query with ampersand collaborator
    res_heaven = get_library_candidates(session, "Heaven Is A Place On Earth", "W&W & AXMO")
    assert len(res_heaven) == 1
    assert res_heaven[0].id == heaven_track.id
    assert len(res_heaven[0].media_files) == 1


def test_promotional_event_title_sanitization():
    """Verify promotional event descriptors and tournament anthems are stripped from titles."""
    from core.matching_engine.text_utils import normalize_title

    assert normalize_title("Fire - Official UEFA EURO 2024 Song") == "fire"
    assert normalize_title("Colors - Coca-Cola® Anthem, 2018 FIFA World CupTM") == "colors"
    assert normalize_title("Live It Up - Official Song 2018 FIFA World Cup (feat. Will Smith)") == "live it up"
    assert normalize_title("Theme - From the series Yellowstone") == "theme"


def test_edition_penalty_hierarchy_and_context_policies():
    """
    Verify edition penalty hierarchy and context-scoped policies:
    - Deluxe Edition penalty: -1.0 (download & sync)
    - Remaster penalty: -2.5 (sync only; strictly rejected on download when original requested)
    """
    from core.matching_engine.matching_engine import evaluate_version_compatibility

    # ── 1. Deluxe Edition fallback ──
    # Download context: Allowed with 1.0 penalty if delta <= 10000ms
    compat, pen, reason = evaluate_version_compatibility(None, "Deluxe Edition", context="download", duration_delta_ms=2000)
    assert compat is True
    assert pen == 1.0

    # Sync context: Allowed with 1.0 penalty
    compat, pen, reason = evaluate_version_compatibility(None, "Deluxe Edition", context="sync", duration_delta_ms=2000)
    assert compat is True
    assert pen == 1.0

    # Duration delta > 10,000ms: Rejected in both
    compat, pen, reason = evaluate_version_compatibility(None, "Deluxe Edition", context="download", duration_delta_ms=12000)
    assert compat is False

    # ── 2. Remastered fallback ──
    # Download context: Strictly REJECTED when original requested
    compat, pen, reason = evaluate_version_compatibility(None, "Remastered", context="download", duration_delta_ms=500)
    assert compat is False

    # Sync context: Allowed with 2.5 penalty when delta <= 5000ms
    compat, pen, reason = evaluate_version_compatibility(None, "Remastered", context="sync", duration_delta_ms=1500)
    assert compat is True
    assert pen == 2.5

    # Sync context: Rejected when delta > 5000ms
    compat, pen, reason = evaluate_version_compatibility(None, "Remastered", context="sync", duration_delta_ms=6000)
    assert compat is False


def test_matching_engine_context_scoped_scoring():
    """Verify WeightedMatchingEngine adheres to download vs sync context policies."""
    profile = ExactSyncProfile()
    engine = WeightedMatchingEngine(profile)

    source_orig = EchosyncTrack(
        raw_title="Heroes",
        artist_name="David Bowie",
        album_title="Heroes",
        duration=367000,
    )
    cand_deluxe = EchosyncTrack(
        raw_title="Heroes",
        artist_name="David Bowie",
        album_title="Heroes",
        edition="Deluxe Edition",
        duration=367500,
    )
    cand_remaster = EchosyncTrack(
        raw_title="Heroes",
        artist_name="David Bowie",
        album_title="Heroes",
        edition="2017 Remaster",
        duration=367500,
    )

    # In download mode: Deluxe passes with 1.0 penalty; Remaster is rejected
    res_dl_deluxe = engine.calculate_match(source_orig, cand_deluxe, context="download")
    assert res_dl_deluxe.passed_version_check is True
    assert res_dl_deluxe.edition_penalty_applied == 1.0

    res_dl_remaster = engine.calculate_match(source_orig, cand_remaster, context="download")
    assert res_dl_remaster.passed_version_check is False
    assert res_dl_remaster.confidence_score == 0.0

    # In sync mode: Deluxe passes with 1.0 penalty; Remaster passes with 2.5 penalty
    res_sync_deluxe = engine.calculate_match(source_orig, cand_deluxe, context="sync")
    assert res_sync_deluxe.passed_version_check is True
    assert res_sync_deluxe.edition_penalty_applied == 1.0

    res_sync_remaster = engine.calculate_match(source_orig, cand_remaster, context="sync")
    assert res_sync_remaster.passed_version_check is True
    assert res_sync_remaster.edition_penalty_applied == 2.5


def test_tier2_strict_2000ms_duration_gate():
    """Verify Tier 2 title-only fallback strictly enforces 2.0s duration ceiling."""
    profile = ExactSyncProfile()
    engine = WeightedMatchingEngine(profile)

    source = EchosyncTrack(
        raw_title="Midnight City",
        artist_name="M83",
        album_title="Hurry Up, We're Dreaming",
        duration=243000,
    )
    cand_pass = EchosyncTrack(
        raw_title="Midnight City",
        artist_name="Unknown Artist",
        album_title="Hurry Up, We're Dreaming",
        duration=244500,  # 1500ms diff <= 2000ms
    )
    cand_fail = EchosyncTrack(
        raw_title="Midnight City",
        artist_name="Unknown Artist",
        album_title="Hurry Up, We're Dreaming",
        duration=245500,  # 2500ms diff > 2000ms
    )

    res_pass = engine.calculate_title_duration_match(source, cand_pass)
    assert res_pass.confidence_score >= 90.0
    assert res_pass.passed_version_check is True

    res_fail = engine.calculate_title_duration_match(source, cand_fail)
    assert res_fail.confidence_score == 0.0
    assert "Duration outside tolerance" in res_fail.reasoning
