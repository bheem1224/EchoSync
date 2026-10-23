"""Tests for AcoustID title pre-filter veto invalidation on high acoustic confidence,
MusicBrainz alias transliteration matching, and exact ISRC master ground truth elevation.
"""

from unittest.mock import MagicMock

import echosync_core
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest


def test_a_acoustid_high_confidence_transliteration_alias_wins(monkeypatch, tmp_path):
    """Test A: Lovely.flac (AcoustID 0.9995, 'ラヴリー' Billie Eilish) passes pre-filter
    despite foreign script and wins over The Eggnogs (2002) via MB alias matching and popularity.
    """
    audio_file = tmp_path / "Lovely.flac"
    audio_file.write_bytes(b"dummy audio for lovely")

    file_dur_ms = 200000

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Lovely",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_chromaprint = "A" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    # Candidate 1: Billie Eilish cataloged in Japanese script with alias "lovely"
    cand_billie = {
        "title": "ラヴリー",
        "artist": "Billie Eilish",
        "album": "Don't Smile at Me (Japanese Edition)",
        "duration_ms": file_dur_ms,
        "first_release_date": "2018-04-19",
        "aliases": [{"name": "lovely"}],
        "releases": [
            {"id": f"rel-be-{i}", "release_group": {"id": f"rg-be-{i % 6}", "primary_type": "Album"}}
            for i in range(30)
        ],
        "release_group": {"id": "rg-be-0", "title": "Lovely", "primary_type": "Album"},
    }

    # Candidate 2: The Eggnogs - obscure early 2002 single matching title "Lovely"
    cand_eggnogs = {
        "title": "Lovely",
        "artist": "The Eggnogs",
        "album": "Eggnog Season",
        "duration_ms": file_dur_ms,
        "first_release_date": "2002-12-01",
        "aliases": [],
        "releases": [
            {"id": "rel-eggnogs-1", "release_group": {"id": "rg-eggnogs-1", "primary_type": "Single"}}
        ],
        "release_group": {"id": "rg-eggnogs-1", "title": "Eggnog Season", "primary_type": "Single"},
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.side_effect = lambda mbid: (
        cand_billie if mbid == "mbid-billie-eilish"
        else cand_eggnogs if mbid == "mbid-eggnogs"
        else None
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "aid-lovely",
        "mbids": ["mbid-eggnogs", "mbid-billie-eilish"],
        "recordings": [
            {
                "id": "mbid-eggnogs",
                "title": "Lovely",
                "artist": "The Eggnogs",
                "score": 85,
                "duration": file_dur_ms / 1000.0,
            },
            {
                "id": "mbid-billie-eilish",
                "title": "ラヴリー",
                "artist": "Billie Eilish",
                "score": 99.95,
                "duration": file_dur_ms / 1000.0,
            },
        ],
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_lovely",
        file_path=audio_file,
        baseline_title="Lovely",
    )

    result = engine.resolve_track(req)

    # Billie Eilish must win over The Eggnogs
    assert result.musicbrainz_track_id == "mbid-billie-eilish"
    assert result.resolution_method == "acoustid"

    diagnostics = result.diagnostics or req._diagnostics
    stage3_diag = next((d for d in diagnostics if d.get("stage") == "Stage 3: AcoustID"), None)
    assert stage3_diag is not None
    candidates = stage3_diag.get("candidates") or []

    billie_diag = next(c for c in candidates if c.get("mbid") == "mbid-billie-eilish")
    eggnogs_diag = next(c for c in candidates if c.get("mbid") == "mbid-eggnogs")

    assert billie_diag.get("status") == "WINNER"
    assert eggnogs_diag.get("status") == "RUNNER_UP"
    # Ensure Billie Eilish was not dropped by pre-filter
    assert billie_diag.get("status") != "DROPPED_TITLE_PREFILTER"


def test_b_embedded_master_isrc_match_elevates_candidate(monkeypatch, tmp_path):
    """Test B: Embedded ISRC USUM71804190 awards Master ISRC match (+50.0)
    and wins candidate arbitration over competing candidates.
    """
    audio_file = tmp_path / "Lovely.flac"
    audio_file.write_bytes(b"dummy audio with embedded isrc")

    file_dur_ms = 200000
    isrc_universal = "USUM71804190"

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Lovely",
            "artist": "Billie Eilish",
            "isrc": isrc_universal,
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_chromaprint = "B" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    # Candidate 1: Canonical Billie Eilish recording with matching master ISRC
    cand_billie = {
        "title": "Lovely",
        "artist": "Billie Eilish & Khalid",
        "album": "13 Reasons Why (Season 2)",
        "duration_ms": file_dur_ms,
        "isrcs": [isrc_universal],
        "releases": [
            {"id": "rel-1", "release_group": {"id": "rg-1", "primary_type": "Album"}}
        ],
        "release_group": {"id": "rg-1", "title": "Lovely", "primary_type": "Album"},
    }

    # Candidate 2: Indie tribute cover with slightly higher raw AcoustID cluster score
    cand_cover = {
        "title": "Lovely",
        "artist": "Acoustic Tribute Band",
        "album": "Acoustic Hits",
        "duration_ms": file_dur_ms,
        "isrcs": ["QZME82012345"],
        "releases": [
            {"id": "rel-2", "release_group": {"id": "rg-2", "primary_type": "Album"}}
        ],
        "release_group": {"id": "rg-2", "title": "Acoustic Hits", "primary_type": "Album"},
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.side_effect = lambda mbid: (
        cand_billie if mbid == "mbid-billie-canonical"
        else cand_cover if mbid == "mbid-cover"
        else None
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "aid-isrc-test",
        "mbids": ["mbid-cover", "mbid-billie-canonical"],
        "recordings": [
            {
                "id": "mbid-cover",
                "title": "Lovely",
                "artist": "Acoustic Tribute Band",
                "score": 96,  # Higher initial AcoustID score
                "duration": file_dur_ms / 1000.0,
            },
            {
                "id": "mbid-billie-canonical",
                "title": "Lovely",
                "artist": "Billie Eilish",
                "score": 92,
                "duration": file_dur_ms / 1000.0,
            },
        ],
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_isrc",
        file_path=audio_file,
        baseline_title="Lovely",
        baseline_artist="Billie Eilish",
        baseline_isrc=isrc_universal,
    )

    result = engine.resolve_track(req)

    # Billie Eilish must win due to Master ISRC ground truth (+50.0 bonus)
    assert result.musicbrainz_track_id == "mbid-billie-canonical"
    assert result.resolution_method == "acoustid"

    diagnostics = result.diagnostics or req._diagnostics
    stage3_diag = next((d for d in diagnostics if d.get("stage") == "Stage 3: AcoustID"), None)
    assert stage3_diag is not None
    candidates = stage3_diag.get("candidates") or []

    billie_diag = next(c for c in candidates if c.get("mbid") == "mbid-billie-canonical")
    assert billie_diag.get("isrc_match") is True
    assert billie_diag.get("isrc_adjustment") == 50.0
    assert billie_diag.get("status") == "WINNER"
    assert 0.0 <= billie_diag.get("total_score") <= 100.0


def test_c_low_confidence_acoustid_drops_unrelated_title(monkeypatch, tmp_path):
    """Test C: Low-confidence AcoustID (< 0.90) drops an unrelated title
    (e.g. 'bury a friend' for Lovely.flac) at the Stage 3 pre-filter,
    preventing network egress to MusicBrainz for that candidate.
    """
    audio_file = tmp_path / "Lovely.flac"
    audio_file.write_bytes(b"dummy audio for prefilter drop")

    file_dur_ms = 200000

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Lovely",
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

    cand_lovely = {
        "title": "Lovely",
        "artist": "Billie Eilish",
        "album": "Don't Smile at Me",
        "duration_ms": file_dur_ms,
        "releases": [
            {"id": "rel-lov-1", "release_group": {"id": "rg-lov-1", "primary_type": "Album"}}
        ],
        "release_group": {"id": "rg-lov-1", "title": "Lovely", "primary_type": "Album"},
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.side_effect = lambda mbid: (
        cand_lovely if mbid == "mbid-lovely"
        else None
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "aid-drop-test",
        "mbids": ["mbid-bury-a-friend", "mbid-lovely"],
        "recordings": [
            {
                "id": "mbid-bury-a-friend",
                "title": "bury a friend",
                "artist": "Billie Eilish",
                "score": 75,  # Low confidence (< 90%)
                "duration": file_dur_ms / 1000.0,
            },
            {
                "id": "mbid-lovely",
                "title": "Lovely",
                "artist": "Billie Eilish",
                "score": 88,
                "duration": file_dur_ms / 1000.0,
            },
        ],
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_drop",
        file_path=audio_file,
        baseline_title="Lovely",
        baseline_artist="Billie Eilish",
    )

    result = engine.resolve_track(req)

    assert result.musicbrainz_track_id == "mbid-lovely"
    assert result.resolution_method == "acoustid"

    # MusicBrainz lookup must NOT have been called for 'bury a friend'
    mock_mb.get_metadata.assert_called_once_with("mbid-lovely")

    diagnostics = result.diagnostics or req._diagnostics
    stage3_diag = next((d for d in diagnostics if d.get("stage") == "Stage 3: AcoustID"), None)
    assert stage3_diag is not None
    candidates = stage3_diag.get("candidates") or []

    bury_diag = next((c for c in candidates if c.get("mbid") == "mbid-bury-a-friend"), None)
    assert bury_diag is not None
    assert bury_diag.get("status") == "DROPPED_TITLE_PREFILTER"
