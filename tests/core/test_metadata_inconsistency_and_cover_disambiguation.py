"""Tests for embedded metadata inconsistency detection and cover disambiguation in AcoustID resolution."""

import logging
from unittest.mock import MagicMock
import pytest
import echosync_core
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest
from core.metadata.scoring import compute_cover_penalty, score_acoustid_candidate


def test_compute_cover_penalty_logic():
    """Unit tests for compute_cover_penalty helper."""
    cover_cand = {
        "title": "Try",
        "artist": "Jun Sung Ahn",
        "album": "Violin Covers Vol 1",
        "release_group": {"title": "Violin Covers Vol 1", "primary_type": "Album"},
    }
    orig_cand = {
        "title": "Try",
        "artist": "P!nk",
        "album": "The Truth About Love",
        "release_group": {"title": "The Truth About Love", "primary_type": "Album"},
    }

    # Decisive acoustic difference (> 0.08) preserves genuine cover without penalty
    assert compute_cover_penalty(cover_cand, delta_sim=0.15) == 0.0
    assert compute_cover_penalty(cover_cand, delta_sim=0.09) == 0.0

    # Acoustic tie (|delta_sim| <= 0.08) penalizes cover collection album (-25.0)
    assert compute_cover_penalty(cover_cand, delta_sim=0.05) == -25.0
    assert compute_cover_penalty(cover_cand, delta_sim=0.0) == -25.0
    assert compute_cover_penalty(cover_cand, delta_sim=-0.05) == -25.0

    # Negative delta_sim (< -0.08) also penalizes cover collection
    assert compute_cover_penalty(cover_cand, delta_sim=-0.12) == -25.0

    # Original studio release is never penalized regardless of delta_sim
    assert compute_cover_penalty(orig_cand, delta_sim=0.02) == 0.0
    assert compute_cover_penalty(orig_cand, delta_sim=-0.05) == 0.0


def test_inconsistency_detection_demotes_untrusted_tags(monkeypatch, tmp_path, caplog):
    """Case A: A file with conflicting embedded tags (tag says Jun Sung Ahn,

    but embedded MBID points to P!nk).
    Verifies:
    1. Warning is logged: Embedded metadata contradiction detected
    2. untrusted_tags is set to True
    3. AcoustID resolution resolves P!nk without dropping her in Step B or penalizing matcher score.
    """
    audio_file = tmp_path / "pink_try_contaminated_tag.mp3"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 247000

    # Embedded tags contradict: Artist is "Jun Sung Ahn", but MBID is P!nk's track
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Try",
            "artist": "Jun Sung Ahn",
            "musicbrainz_id": "mbid-pink-try",
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

    cand_pink = {
        "title": "Try",
        "artist": "P!nk",
        "album": "The Truth About Love",
        "duration_ms": file_dur_ms,
        "release_id": "rel-pink-album",
        "release_group": {"title": "The Truth About Love", "primary_type": "Album"},
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.side_effect = lambda mbid: cand_pink if mbid == "mbid-pink-try" else None

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-pink-999",
        "mbids": ["mbid-pink-try"],
        "recordings": [
            {
                "id": "mbid-pink-try",
                "title": "Try",
                "artist": "P!nk",
                "score": 98,
                "duration": file_dur_ms / 1000.0,
            }
        ],
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_case_a",
        file_path=audio_file,
        baseline_title="Try",
        baseline_artist="Jun Sung Ahn",
    )

    with caplog.at_level(logging.WARNING):
        result = engine.resolve_track(req)

    # 1. Contradiction warning logged
    assert any(
        "Embedded metadata contradiction detected: tag artist 'Jun Sung Ahn' contradicts MBID artist 'P!nk'" in record.message
        for record in caplog.records
    )

    # 2. untrusted_tags flagged on request
    assert req.untrusted_tags is True
    assert req.is_untrusted_legacy_tags is True

    # 3. AcoustID selected P!nk without dropping her in Step B
    assert result.musicbrainz_track_id == "mbid-pink-try"
    assert result.artist == "P!nk"
    assert result.title == "Try"
    assert result.album == "The Truth About Love"
    assert result.resolution_method == "acoustid"


def test_true_cover_selected_when_acoustic_similarity_decisively_higher(monkeypatch, tmp_path):
    """Case B: An actual cover recording whose acoustic similarity is decisively

    higher than the original (delta_sim > 0.08).
    Verifies no cover penalty is applied and the cover is selected.
    """
    audio_file = tmp_path / "jun_sung_ahn_try_violin_cover.mp3"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 245000

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Try",
            "artist": "Jun Sung Ahn",
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

    cand_cover = {
        "title": "Try",
        "artist": "Jun Sung Ahn",
        "album": "Violin Covers",
        "duration_ms": file_dur_ms,
        "release_id": "rel-cover-1",
        "release_group": {"title": "Violin Covers", "primary_type": "Album"},
    }

    cand_original = {
        "title": "Try",
        "artist": "P!nk",
        "album": "The Truth About Love",
        "duration_ms": file_dur_ms,
        "release_id": "rel-orig-1",
        "release_group": {"title": "The Truth About Love", "primary_type": "Album"},
    }

    mock_mb = MagicMock()

    def mock_get_meta(mbid):
        if mbid == "mbid-cover":
            return cand_cover
        elif mbid == "mbid-original":
            return cand_original
        return None

    mock_mb.get_metadata.side_effect = mock_get_meta

    mock_acoustid = MagicMock()
    # Cover acoustic score = 0.96, Original acoustic score = 0.80 -> delta_sim = 0.16 > 0.08
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-cover-123",
        "mbids": ["mbid-cover", "mbid-original"],
        "recordings": [
            {
                "id": "mbid-cover",
                "title": "Try",
                "artist": "Jun Sung Ahn",
                "score": 96,
                "duration": file_dur_ms / 1000.0,
            },
            {
                "id": "mbid-original",
                "title": "Try",
                "artist": "P!nk",
                "score": 80,
                "duration": file_dur_ms / 1000.0,
            },
        ],
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_case_b",
        file_path=audio_file,
        baseline_title="Try",
        baseline_artist="Jun Sung Ahn",
    )

    result = engine.resolve_track(req)

    # Cover won decisively based on audio fingerprint similarity without being penalized
    assert result.musicbrainz_track_id == "mbid-cover"
    assert result.artist == "Jun Sung Ahn"
    assert result.album == "Violin Covers"


def test_original_selected_over_cover_when_acoustically_tied(monkeypatch, tmp_path):
    """Case C: An original recording where acoustic similarity is virtually tied

    (|delta_sim| <= 0.08) with a cover collection album.
    Verifies cover penalty (-25.0) is applied to the cover, allowing the original
    recording to win.
    """
    audio_file = tmp_path / "pink_try_original_tied.mp3"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 247000

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Try",
            "artist": "P!nk",
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

    # Candidate 1: Obscure Cover Album with slightly closer duration or 1% higher score
    cand_cover = {
        "title": "Try",
        "artist": "Acoustic Tribute Band",
        "album": "Greatest Hits Acoustic Covers",
        "duration_ms": file_dur_ms,
        "release_id": "rel-cover-coll",
        "release_group": {"title": "Greatest Hits Acoustic Covers", "primary_type": "Album"},
    }

    # Candidate 2: Canonical Original Studio Album
    cand_original = {
        "title": "Try",
        "artist": "P!nk",
        "album": "The Truth About Love",
        "duration_ms": file_dur_ms,
        "release_id": "rel-pink-orig",
        "release_group": {"title": "The Truth About Love", "primary_type": "Album"},
    }

    mock_mb = MagicMock()

    def mock_get_meta(mbid):
        if mbid == "mbid-cover-coll":
            return cand_cover
        elif mbid == "mbid-pink-orig":
            return cand_original
        return None

    mock_mb.get_metadata.side_effect = mock_get_meta

    mock_acoustid = MagicMock()
    # Cover acoustic score = 0.94, Original acoustic score = 0.93 -> delta_sim = 0.01 <= 0.08
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-tied-456",
        "mbids": ["mbid-cover-coll", "mbid-pink-orig"],
        "recordings": [
            {
                "id": "mbid-cover-coll",
                "title": "Try",
                "artist": "Acoustic Tribute Band",
                "score": 94,
                "duration": file_dur_ms / 1000.0,
            },
            {
                "id": "mbid-pink-orig",
                "title": "Try",
                "artist": "P!nk",
                "score": 93,
                "duration": file_dur_ms / 1000.0,
            },
        ],
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_case_c",
        file_path=audio_file,
        baseline_title="Try",
        baseline_artist="P!nk",
    )

    result = engine.resolve_track(req)

    # Original studio release won because cover received -25.0 penalty under acoustic tie
    assert result.musicbrainz_track_id == "mbid-pink-orig"
    assert result.artist == "P!nk"
    assert result.album == "The Truth About Love"

