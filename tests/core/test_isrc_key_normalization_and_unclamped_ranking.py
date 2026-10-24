"""Tests for MusicBrainz live key normalization (isrc-list, release-list)
and unclamped multi-factor candidate ranking in Stage 3 AcoustID resolution.
"""

from unittest.mock import MagicMock

import echosync_core
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest


def test_live_mb_key_normalization_and_isrc_award(monkeypatch, tmp_path):
    """Test that live MusicBrainz keys ('isrc-list', 'release-list') are properly normalized,
    release group count is computed, and authoritative embedded ISRC awards +25.0 even when
    text tags are untrusted.
    """
    audio_file = tmp_path / "track_untrusted_stream.flac"
    audio_file.write_bytes(b"dummy audio for live mb normalization")

    file_dur_ms = 180000
    isrc_universal = "USUM71804190"

    # Untrusted tags: file has generic/mismatched text tags, but authoritative embedded ISRC
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Track 01",
            "artist": "Unknown Artist",
            "isrc": isrc_universal,
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

    # Candidate with live MusicBrainz response format: 'isrc-list' and 'release-list'
    cand_canonical = {
        "title": "Lovely",
        "artist": "Billie Eilish",
        "album": "Don't Smile at Me",
        "duration_ms": file_dur_ms,
        "isrc-list": [{"isrc": isrc_universal}],
        "release-list": [
            {
                "id": f"rel-{i}",
                "title": f"Release {i}",
                "release-group": {"id": f"rg-{i % 5}", "primary-type": "Album"},
            }
            for i in range(25)
        ],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.side_effect = lambda mbid: (
        cand_canonical if mbid == "mbid-billie-live" else None
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "aid-live-norm",
        "mbids": ["mbid-billie-live"],
        "recordings": [
            {
                "id": "mbid-billie-live",
                "title": "Lovely",
                "artist": "Billie Eilish",
                "score": 99.9,
                "duration": file_dur_ms / 1000.0,
            },
        ],
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    # Filename stem gives baseline hint, but tag artist is contaminated and untrusted
    req = ResolutionRequest(
        media_id="media_norm_test",
        file_path=audio_file,
        baseline_title="Lovely",
        baseline_artist="Unknown Artist",
        baseline_isrc=isrc_universal,
        untrusted_tags=True,
    )

    result = engine.resolve_track(req)

    assert result is not None
    assert result.musicbrainz_track_id == "mbid-billie-live"
    assert result.resolution_method == "acoustid"

    # Check candidate diagnostics
    diagnostics = result.diagnostics or req._diagnostics
    stage3_diag = next((d for d in diagnostics if d.get("stage") == "Stage 3: AcoustID"), None)
    assert stage3_diag is not None
    candidates = stage3_diag.get("candidates") or []
    assert len(candidates) == 1

    cand_diag = candidates[0]
    assert cand_diag.get("status") == "WINNER"
    # Key normalization checks
    assert cand_diag.get("isrc_match") is True
    # In untrusted mode, authoritative ISRC grants +25.0
    assert cand_diag.get("isrc_adjustment") == 25.0
    # Release count and release group count extracted from release-list
    assert cand_diag.get("release_count") == 25
    assert cand_diag.get("release_group_count") >= 25
    assert cand_diag.get("canonical_weight") == 10.0
    # Popularity bonus > 0 from continuous log10
    assert cand_diag.get("popularity_bonus") > 4.0
    # Raw score must be unclamped (> 100.0), total_score clamped to 100.0
    assert cand_diag.get("raw_score") > 120.0
    assert cand_diag.get("total_score") == 100.0
    assert stage3_diag.get("details", {}).get("score") == 100.0


def test_unclamped_multi_factor_ranking_breaks_tie(monkeypatch, tmp_path):
    """Test that unclamped raw scores and multi-factor ranking break 3-way score ties:
    Candidate with matching master ISRC and 25 releases defeats competing candidates
    even when basic scores would have clamped to 99.9 or 100.0.
    """
    audio_file = tmp_path / "Lovely.flac"
    audio_file.write_bytes(b"dummy audio for tie breaking")

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

    dummy_chromaprint = "E" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    # Candidate 1: Canonical Billie Eilish recording (matching ISRC, 30 releases)
    cand_billie = {
        "title": "Lovely",
        "artist": "Billie Eilish",
        "album": "Don't Smile at Me",
        "duration_ms": file_dur_ms,
        "first_release_date": "2018-04-19",
        "isrc-list": [{"isrc": isrc_universal}],
        "release-list": [
            {"id": f"rel-b-{i}", "release-group": {"id": f"rg-b-{i % 5}", "primary-type": "Album"}}
            for i in range(30)
        ],
    }

    # Candidate 2: The Eggnogs (earlier year 2002, perfect AcoustID cluster, 1 release, wrong ISRC)
    cand_eggnogs = {
        "title": "Lovely",
        "artist": "The Eggnogs",
        "album": "Eggnog Season",
        "duration_ms": file_dur_ms,
        "first_release_date": "2002-12-01",
        "isrc-list": [{"isrc": "USXX10200001"}],
        "release-list": [
            {"id": "rel-e-1", "release-group": {"id": "rg-e-1", "primary-type": "Single"}}
        ],
    }

    # Candidate 3: Obscure Cover (matching duration, 2 releases, wrong ISRC)
    cand_cover = {
        "title": "Lovely",
        "artist": "Tribute Band",
        "album": "Acoustic Hits",
        "duration_ms": file_dur_ms,
        "first_release_date": "2019-01-01",
        "isrc-list": [{"isrc": "QZ1234567890"}],
        "release-list": [
            {"id": "rel-c-1", "release-group": {"id": "rg-c-1", "primary-type": "Album"}},
            {"id": "rel-c-2", "release-group": {"id": "rg-c-1", "primary-type": "Album"}},
        ],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.side_effect = lambda mbid: (
        cand_eggnogs if mbid == "mbid-eggnogs"
        else cand_billie if mbid == "mbid-billie"
        else cand_cover if mbid == "mbid-cover"
        else None
    )

    mock_acoustid = MagicMock()
    # List eggnogs first in recordings to test stable max() does NOT default to first
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "aid-tie-break",
        "mbids": ["mbid-eggnogs", "mbid-billie", "mbid-cover"],
        "recordings": [
            {
                "id": "mbid-eggnogs",
                "title": "Lovely",
                "artist": "The Eggnogs",
                "score": 99.95,
                "duration": file_dur_ms / 1000.0,
            },
            {
                "id": "mbid-billie",
                "title": "Lovely",
                "artist": "Billie Eilish",
                "score": 99.95,
                "duration": file_dur_ms / 1000.0,
            },
            {
                "id": "mbid-cover",
                "title": "Lovely",
                "artist": "Tribute Band",
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
        media_id="media_tie_break",
        file_path=audio_file,
        baseline_title="Lovely",
        baseline_artist="Billie Eilish",
        baseline_isrc=isrc_universal,
    )

    result = engine.resolve_track(req)

    # Billie Eilish must win arbitration due to raw score, master ISRC match, and release group stature
    assert result is not None
    assert result.musicbrainz_track_id == "mbid-billie"
    assert result.resolution_method == "acoustid"

    diagnostics = result.diagnostics or req._diagnostics
    stage3_diag = next((d for d in diagnostics if d.get("stage") == "Stage 3: AcoustID"), None)
    assert stage3_diag is not None
    candidates = stage3_diag.get("candidates") or []

    billie_diag = next(c for c in candidates if c.get("mbid") == "mbid-billie")
    eggnogs_diag = next(c for c in candidates if c.get("mbid") == "mbid-eggnogs")

    assert billie_diag.get("status") == "WINNER"
    assert eggnogs_diag.get("status") == "RUNNER_UP"
    # Billie raw score > Eggnogs raw score
    assert billie_diag.get("raw_score") > eggnogs_diag.get("raw_score")
    # Both display total_score clamped to <= 100.0
    assert billie_diag.get("total_score") == 100.0
    assert stage3_diag.get("details", {}).get("score") == 100.0
