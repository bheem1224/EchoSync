"""Tests for script-tolerant CJK AcoustID pre-filtering, feature extraction query expansion,
and parenthetical album qualifier amnesty during playlist sync.

Test A: Lovely.flac with ISRC USUM71804190 does not drop candidate ラヴリー (Billie Eilish)
        in _resolve_acoustid and selects Billie Eilish over The Eggnogs.
Test B: Query Without You (feat. Usher) matches local track Without You by David Guetta & Usher.
Test C: Query i like the way you kiss me (2:22) matches local track on album
        i like the way you kiss me (burnt) with confidence >= 90%.
"""

from unittest.mock import MagicMock
import echosync_core
import pytest

from core.db.echo_sync_track import EchosyncTrack
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import ExactSyncProfile
from core.matching_engine.track_parser import TrackParser
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest


def test_cjk_isrc_acoustid_prefilter_lovely_billie_eilish(monkeypatch, tmp_path):
    """Test A: Lovely.flac with ISRC USUM71804190 preserves Japanese candidate ラヴリー

    (Billie Eilish) in AcoustID candidate pre-filter and selects Billie Eilish over The Eggnogs.
    """
    audio_file = tmp_path / "Lovely.flac"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 200000

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Lovely",
            "artist": "Billie Eilish",
            "duration_ms": file_dur_ms,
            "channels": 2,
            "isrc": "USUM71804190",
        },
    )

    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: ("C" * 60, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-lovely-test",
        "score": 0.96,
        "recordings": [
            {
                "id": "mbid-billie-lovely",
                "title": "ラヴリー",
                "artist": "Billie Eilish & Khalid",
                "duration": file_dur_ms / 1000.0,
                "score": 0.96,
                "isrcs": ["USUM71804190"],
                "aliases": [{"name": "Lovely"}],
            },
            {
                "id": "mbid-eggnogs-lovely",
                "title": "Lovely",
                "artist": "The Eggnogs",
                "duration": file_dur_ms / 1000.0,
                "score": 0.93,
                "isrcs": ["USXYZ9876543"],
            },
        ],
        "mbids": ["mbid-billie-lovely", "mbid-eggnogs-lovely"],
    }

    mock_mb = MagicMock()

    def mock_get_metadata(mbid):
        if mbid == "mbid-billie-lovely":
            return {
                "title": "ラヴリー",
                "artist": "Billie Eilish & Khalid",
                "album": "Lovely",
                "duration_ms": file_dur_ms,
                "release_id": "rel-billie",
                "release_group": {"primary_type": "Single"},
                "isrcs": ["USUM71804190"],
                "aliases": [{"name": "Lovely"}],
            }
        else:
            return {
                "title": "Lovely",
                "artist": "The Eggnogs",
                "album": "Eggnog Season",
                "duration_ms": file_dur_ms,
                "release_id": "rel-eggnogs",
                "release_group": {"primary_type": "Album"},
                "isrcs": ["USXYZ9876543"],
            }

    mock_mb.get_metadata.side_effect = mock_get_metadata

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_lovely_1",
        file_path=audio_file,
        baseline_title="Lovely",
        baseline_artist="Billie Eilish",
        baseline_isrc="USUM71804190",
    )

    result = engine.resolve_track(req)

    assert result is not None
    assert result.musicbrainz_track_id == "mbid-billie-lovely"
    assert "Billie Eilish" in result.artist
    assert result.musicbrainz_track_id != "mbid-eggnogs-lovely"


def test_feature_extraction_and_junction_query_without_you():
    """Test B: Query 'Without You (feat. Usher)' matches local track 'Without You' by 'David Guetta & Usher'."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="Without You (feat. Usher)",
        artist_name="David Guetta",
        duration=208000,
    )
    candidate = EchosyncTrack(
        raw_title="Without You",
        artist_name="David Guetta & Usher",
        duration=208000,
    )

    result = engine.calculate_match(source, candidate, context="sync")

    assert result.confidence_score >= 85.0
    assert result.passed_version_check is True
    assert result.title_score >= 0.95
    assert result.artist_score >= 0.90


def test_album_parenthetical_qualifier_amnesty_artemas():
    """Test C: Query 'i like the way you kiss me' (2:22) matches local track on album

    'i like the way you kiss me (burnt)' with confidence >= 90%.
    """
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="i like the way you kiss me",
        artist_name="Artemas",
        album_title="i like the way you kiss me",
        duration=142000,
    )
    candidate = EchosyncTrack(
        raw_title="i like the way you kiss me",
        artist_name="Artemas",
        album_title="i like the way you kiss me (burnt)",
        edition="burnt",
        duration=142000,
    )

    result = engine.calculate_match(source, candidate, context="sync")

    assert result.confidence_score >= 90.0
    assert result.passed_version_check is True
    assert result.passed_edition_check is True
    assert result.version_penalty_applied == 0.0
    assert result.edition_penalty_applied == 0.0


def test_track_parser_extract_featured_from_title():
    """Verify TrackParser feature extraction helper functions."""
    clean_t, featured = TrackParser.extract_featured_from_title("Without You (feat. Usher)")
    assert clean_t == "Without You"
    assert featured == ["Usher"]

    clean_t2, featured2 = TrackParser.parse_query_title("Song Name (with Artist A & Artist B)")
    assert clean_t2 == "Song Name"
    assert "Artist A" in featured2
    assert "Artist B" in featured2

