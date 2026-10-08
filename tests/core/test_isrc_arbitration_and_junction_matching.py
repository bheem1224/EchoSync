"""Tests for Phase 1 & Phase 2 EchoSync Candidate Arbitration Blueprint:
1. ISRC Registrant classification & major-label vs aggregator candidate arbitration.
2. Continuous logarithmic popularity bonus scaling.
3. MatchingEngine junction table querying & remixer role matching across track_artists.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import echosync_core
from core.db.echo_sync_track import EchosyncTrack
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.matching_engine import MatchingEngine, WeightedMatchingEngine
from core.matching_engine.scoring_profile import ExactSyncProfile
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.isrc_registry import calculate_isrc_penalty_or_bonus, classify_isrc
from core.metadata.schemas import ResolutionRequest
from core.metadata.scoring import calculate_popularity_bonus
from database.music_database import Artist, Base, Track, TrackArtist


def test_classify_isrc_registries():
    """Verify ISRC classification distinguishes major labels from digital aggregators."""
    # Major labels
    umg = classify_isrc("USUM71814888")
    assert umg["is_valid"] is True
    assert umg["is_major_label"] is True
    assert umg["is_aggregator"] is False
    assert umg["country_code"] == "US"
    assert umg["registrant_code"] == "UM7"
    assert umg["prefix"] == "USUM7"

    sony = classify_isrc("USSM11700681")
    assert sony["is_major_label"] is True
    assert sony["is_aggregator"] is False

    wmg = classify_isrc("USAT21301234")
    assert wmg["is_major_label"] is True
    assert wmg["is_aggregator"] is False

    # Digital aggregators
    distrokid = classify_isrc("QZME82012345")
    assert distrokid["is_valid"] is True
    assert distrokid["is_major_label"] is False
    assert distrokid["is_aggregator"] is True
    assert distrokid["country_code"] == "QZ"

    tunecore = classify_isrc("TCACG1912345")
    assert tunecore["is_aggregator"] is True


def test_isrc_penalty_and_bonus_calculations():
    """Verify ISRC arbitration rules: exact match (+25), matching prefix (+10), aggregator penalty (-50)."""
    # 1. Exact match bonus
    assert calculate_isrc_penalty_or_bonus("USUM71814888", ["USUM71814888"]) == 25.0

    # 2. Matching label prefix bonus (different recording on same label)
    assert calculate_isrc_penalty_or_bonus("USUM71814888", ["USUM71899999"]) == 10.0

    # 3. Major label file vs digital aggregator candidate -> -50.0 disqualification
    assert calculate_isrc_penalty_or_bonus("USUM71814888", ["QZME82012345"]) == -50.0

    # 4. Unknown/neutral candidate -> 0.0
    assert calculate_isrc_penalty_or_bonus("USUM71814888", ["GBAYE1234567"]) == 0.0
    assert calculate_isrc_penalty_or_bonus(None, ["USUM71814888"]) == 0.0


def test_a_isrc_arbitration_demotes_aggregator_candidate(monkeypatch, tmp_path):
    """Test A: File tagged with USUM71814888 (Post Malone) correctly demotes or disqualifies
    an AcoustID candidate tagged with aggregator prefix QZ (Rick Jayson).
    """
    audio_file = tmp_path / "sunflower.mp3"
    audio_file.write_bytes(b"dummy sunflower audio data")

    file_dur_ms = 158000

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Sunflower",
            "artist": "Post Malone",
            "isrc": "USUM71814888",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_chromaprint = "C" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    cand_rick_jayson = {
        "title": "Sunflower",
        "artist": "Rick Jayson",
        "album": "Acoustic Tributes",
        "duration_ms": file_dur_ms,
        "isrcs": ["QZME82012345"],
        "releases": [
            {"id": "rel-rick-1", "release_group": {"id": "rg-rick-1", "primary_type": "Single"}}
        ],
        "release_group": {"id": "rg-rick-1", "title": "Acoustic Tributes", "primary_type": "Single"},
    }

    cand_post_malone = {
        "title": "Sunflower",
        "artist": "Post Malone & Swae Lee",
        "album": "Spider-Man: Into the Spider-Verse",
        "duration_ms": file_dur_ms,
        "isrcs": ["USUM71814888"],
        "releases": [
            {"id": f"rel-post-{i}", "release_group": {"id": f"rg-post-{i % 5}", "primary_type": "Album"}}
            for i in range(30)
        ],
        "release_group": {"id": "rg-post-0", "title": "Spider-Man", "primary_type": "Album"},
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.side_effect = lambda mbid: (
        cand_rick_jayson if mbid == "mbid-rick-jayson"
        else cand_post_malone if mbid == "mbid-post-malone"
        else None
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "aid-sunflower",
        "mbids": ["mbid-rick-jayson", "mbid-post-malone"],
        "recordings": [
            {
                "id": "mbid-rick-jayson",
                "title": "Sunflower",
                "artist": "Rick Jayson",
                "score": 97,  # Raw AcoustID payload puts indie cover first
                "duration": file_dur_ms / 1000.0,
            },
            {
                "id": "mbid-post-malone",
                "title": "Sunflower",
                "artist": "Post Malone",
                "score": 95,
                "duration": file_dur_ms / 1000.0,
            },
        ],
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_isrc_arbitration",
        file_path=audio_file,
        baseline_title="Sunflower",
        baseline_artist="Post Malone",
        baseline_isrc="USUM71814888",
    )

    result = engine.resolve_track(req)

    # Post Malone must win despite lower initial AcoustID score due to ISRC disqualification of aggregator
    assert result.musicbrainz_track_id == "mbid-post-malone"
    assert result.resolution_method == "acoustid"

    diagnostics = result.diagnostics or req._diagnostics
    stage3_diag = next((d for d in diagnostics if d.get("stage") == "Stage 3: AcoustID"), None)
    assert stage3_diag is not None
    candidates = stage3_diag.get("candidates") or []

    rick_diag = next(c for c in candidates if c.get("mbid") == "mbid-rick-jayson")
    post_diag = next(c for c in candidates if c.get("mbid") == "mbid-post-malone")

    assert rick_diag.get("isrc_adjustment") == -50.0
    assert rick_diag.get("status") == "RUNNER_UP"
    assert post_diag.get("isrc_adjustment") == 25.0
    assert post_diag.get("status") == "WINNER"


def test_b_logarithmic_popularity_outscores_tribute_single(monkeypatch, tmp_path):
    """Test B: Candidate scoring with 200 release groups outscores a tribute single with 5 release groups."""
    # 1. Formula check: continuous logarithmic scaling min(10.0, 3.0 * log10(R + 1))
    pop_200 = calculate_popularity_bonus(200)
    pop_5 = calculate_popularity_bonus(5)
    assert pop_200 > pop_5
    assert 6.8 < pop_200 < 7.1
    assert 2.2 < pop_5 < 2.5

    # 2. Stage 3 candidate arbitration resolution test
    audio_file = tmp_path / "shallow.mp3"
    audio_file.write_bytes(b"dummy shallow audio data")

    file_dur_ms = 215000

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Shallow",
            "artist": "Lady Gaga",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_chromaprint = "D" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    # Tribute candidate with 5 release groups
    cand_tribute = {
        "title": "Shallow",
        "artist": "Acoustic Tribute Band",
        "album": "Movie Hits Tribute",
        "duration_ms": file_dur_ms,
        "releases": [
            {"id": f"rel-trib-{i}", "release_group": {"id": f"rg-trib-{i}", "primary_type": "Single"}}
            for i in range(5)
        ],
        "release_group": {"id": "rg-trib-0", "title": "Movie Hits Tribute", "primary_type": "Single"},
    }

    # Original candidate with 200 release groups
    cand_original = {
        "title": "Shallow",
        "artist": "Lady Gaga & Bradley Cooper",
        "album": "A Star Is Born Soundtrack",
        "duration_ms": file_dur_ms,
        "releases": [
            {"id": f"rel-orig-{i}", "release_group": {"id": f"rg-orig-{i}", "primary_type": "Album"}}
            for i in range(200)
        ],
        "release_group": {"id": "rg-orig-0", "title": "A Star Is Born", "primary_type": "Album"},
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.side_effect = lambda mbid: (
        cand_tribute if mbid == "mbid-tribute"
        else cand_original if mbid == "mbid-original"
        else None
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "aid-shallow",
        "mbids": ["mbid-tribute", "mbid-original"],
        "recordings": [
            {
                "id": "mbid-tribute",
                "title": "Shallow",
                "artist": "Acoustic Tribute Band",
                "score": 96,
                "duration": file_dur_ms / 1000.0,
            },
            {
                "id": "mbid-original",
                "title": "Shallow",
                "artist": "Lady Gaga",
                "score": 95,
                "duration": file_dur_ms / 1000.0,
            },
        ],
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_popularity",
        file_path=audio_file,
        baseline_title="Shallow",
        baseline_artist="Lady Gaga",
    )

    result = engine.resolve_track(req)

    assert result.musicbrainz_track_id == "mbid-original"
    assert result.artist == "Lady Gaga & Bradley Cooper"

    diagnostics = result.diagnostics or req._diagnostics
    stage3_diag = next((d for d in diagnostics if d.get("stage") == "Stage 3: AcoustID"), None)
    candidates = stage3_diag.get("candidates") or []

    orig_diag = next(c for c in candidates if c.get("mbid") == "mbid-original")
    trib_diag = next(c for c in candidates if c.get("mbid") == "mbid-tribute")

    assert orig_diag["popularity_bonus"] > trib_diag["popularity_bonus"]
    assert orig_diag["status"] == "WINNER"
    assert trib_diag["status"] == "RUNNER_UP"


def test_c_matching_engine_junction_matching_and_remixer_bonus():
    """Test C: MatchingEngine.calculate_match successfully identifies a track when queried
    with an artist whose role is remixer in track_artists.
    """
    engine = MatchingEngine(ExactSyncProfile())

    primary_artist = Artist(id=1, name="Mike Posner", normalized_name="mike posner")
    remixer_artist = Artist(id=2, name="Seeb", normalized_name="seeb")

    track = Track(
        id=10,
        title="I Took a Pill in Ibiza",
        artist=primary_artist,
        artist_id=1,
        duration=195000,
    )
    track.artist_associations = [
        TrackArtist(track_id=10, artist_id=1, role="primary", artist=primary_artist),
        TrackArtist(track_id=10, artist_id=2, role="remixer", artist=remixer_artist),
    ]

    # Query track specifies the remixer as the query artist
    query_track = EchosyncTrack(
        raw_title="I Took a Pill in Ibiza",
        artist_name="Seeb",
        duration=195000,
    )

    result = engine.calculate_match(query_track, track)

    # Must successfully match with high confidence score (>= 80%)
    assert result.confidence_score >= 80.0
    assert result.passed_version_check is True
    assert any("track_artists" in r for r in result.reasoning.split(" | "))
    assert any("remixer" in r for r in result.reasoning.split(" | "))


def test_c_matching_engine_query_candidates_by_artist_junction():
    """Verify MatchingEngine.query_candidates_by_artist queries across track_artists junction."""
    # Set up in-memory SQLite database
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)
    SessionMaker = sessionmaker(bind=db_engine)
    session = SessionMaker()

    primary_artist = Artist(id=1, name="Calvin Harris", normalized_name="calvin harris")
    featured_artist = Artist(id=2, name="Dua Lipa", normalized_name="dua lipa")
    remixer_artist = Artist(id=3, name="MK", normalized_name="mk")
    session.add_all([primary_artist, featured_artist, remixer_artist])
    session.flush()

    track = Track(
        id=20,
        title="One Kiss",
        artist_id=primary_artist.id,
        duration=214000,
        sync_id="test_sync_one_kiss",
    )
    session.add(track)
    session.flush()

    ta_primary = TrackArtist(track_id=track.id, artist_id=primary_artist.id, role="primary")
    ta_featured = TrackArtist(track_id=track.id, artist_id=featured_artist.id, role="featured")
    ta_remixer = TrackArtist(track_id=track.id, artist_id=remixer_artist.id, role="remixer")
    session.add_all([ta_primary, ta_featured, ta_remixer])
    session.commit()

    # Query by primary artist
    res_primary = MatchingEngine.query_candidates_by_artist(session, "Calvin Harris")
    assert len(res_primary) == 1
    assert res_primary[0].id == track.id

    # Query by featured artist across track_artists junction
    res_featured = MatchingEngine.query_candidates_by_artist(session, "Dua Lipa")
    assert len(res_featured) == 1
    assert res_featured[0].id == track.id

    # Query by remixer across track_artists junction
    res_remixer = MatchingEngine.query_candidates_by_artist(session, "MK")
    assert len(res_remixer) == 1
    assert res_remixer[0].id == track.id

    # Query for non-existent artist returns empty
    res_none = MatchingEngine.query_candidates_by_artist(session, "Unknown DJ")
    assert len(res_none) == 0

    session.close()

