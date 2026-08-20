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


def test_subtitle_descriptor_failsafe_tokens():
    # Descriptors like Sea Shanty, UEFA EURO 2024 Song, Soundtrack, From "...", etc.
    score_shanty = _cmp_titles("Wellerman", "Wellerman - Sea Shanty", context_score=0.95)
    assert score_shanty >= 0.90

    score_euro = _cmp_titles("Fire", "Fire - Official UEFA EURO 2024 Song", context_score=0.95)
    assert score_euro >= 0.90

    score_soundtrack = _cmp_titles("Theme", "Theme (Original Soundtrack Version)", context_score=0.95)
    assert score_soundtrack >= 0.90


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
