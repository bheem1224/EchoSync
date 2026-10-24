"""Unit and regression tests for acoustic-modulated dynamic duration bounds and engine bridging."""

import pytest
from unittest.mock import MagicMock

from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import ExactSyncProfile
from core.metadata.engine import (
    MetadataResolutionEngine,
    compute_dynamic_duration_bounds,
    compute_dynamic_duration_threshold,
)
from core.metadata.scoring import (
    calculate_acoustid_duration_weight,
    score_acoustid_candidate,
)


def test_compute_dynamic_duration_bounds_high_similarity():
    """Test A: compute_dynamic_duration_bounds(0.95) returns (3.5, 5.0)."""
    assert compute_dynamic_duration_bounds(0.95) == (3.5, 5.0)
    assert compute_dynamic_duration_bounds(0.99) == (3.5, 5.0)
    assert compute_dynamic_duration_bounds(1.0) == (3.5, 5.0)
    # 0-100 scale normalization
    assert compute_dynamic_duration_bounds(95.0) == (3.5, 5.0)
    assert compute_dynamic_duration_bounds(99.0) == (3.5, 5.0)


def test_compute_dynamic_duration_bounds_low_similarity():
    """Test B: compute_dynamic_duration_bounds(0.80) returns (2.0, 2.0)."""
    assert compute_dynamic_duration_bounds(0.80) == (2.0, 2.0)
    assert compute_dynamic_duration_bounds(0.50) == (2.0, 2.0)
    assert compute_dynamic_duration_bounds(0.0) == (2.0, 2.0)
    # 0-100 scale normalization
    assert compute_dynamic_duration_bounds(80.0) == (2.0, 2.0)
    assert compute_dynamic_duration_bounds(50.0) == (2.0, 2.0)


def test_compute_dynamic_duration_bounds_interpolation():
    """Verify linear interpolation between 0.80 and 0.95."""
    # Midpoint at 0.875:
    # progress = (0.875 - 0.80) / 0.15 = 0.5
    # base = 2.0 + 0.5 * 1.5 = 2.75
    # limit = 2.0 + 0.5 * 3.0 = 3.5
    assert compute_dynamic_duration_bounds(0.875) == (2.75, 3.5)

    # At 0.85: progress = (0.85 - 0.80) / 0.15 = 1/3
    # base = 2.0 + (1/3 * 1.5) = 2.5
    # limit = 2.0 + (1/3 * 3.0) = 3.0
    assert compute_dynamic_duration_bounds(0.85) == (2.5, 3.0)


def test_billie_eilish_duration_delta_retains_full_weight():
    """Test C: File with 202.485s and candidate with 200.186s (delta = 2.299s) with sim_score = 0.85 yields dur_weight == 1.0."""
    file_dur = 202.485
    cand_dur = 200.186
    delta_sec = abs(file_dur - cand_dur)
    assert pytest.approx(delta_sec, 0.001) == 2.299

    sim_score = 0.85
    base_sec, limit_sec = compute_dynamic_duration_bounds(sim_score)
    assert base_sec == 2.5
    assert limit_sec == 3.0
    assert delta_sec <= base_sec

    dur_weight = calculate_acoustid_duration_weight(
        file_dur,
        cand_dur,
        base_sec=base_sec,
        max_sec=limit_sec,
    )
    assert dur_weight == 1.0


def test_score_acoustid_candidate_with_sim_score_prevents_rejection():
    """Verify score_acoustid_candidate honors sim_score dynamic bounds."""
    matcher = WeightedMatchingEngine(ExactSyncProfile())
    candidate = {
        "title": "Lovely",
        "artist": "Billie Eilish",
        "album": "Don't Smile at Me",
        "duration_ms": 200186,  # 200.186s
        "release_group": {"primary_type": "Album"},
    }
    file_duration_ms = 202485  # 202.485s -> delta = 2.299s

    # Without sim_score: delta = 2.299s > max_sec=2.0s triggers hard duration gate (score = 0.0)
    score_default = score_acoustid_candidate(
        matcher=matcher,
        candidate=candidate,
        baseline_title="Lovely",
        file_duration_ms=file_duration_ms,
        baseline_artist="Billie Eilish",
        baseline_album="Don't Smile at Me",
    )
    assert score_default == 0.0

    # With sim_score = 0.85: base_sec = 2.5s, limit_sec = 3.0s -> delta 2.299s <= 2.5s -> dur_weight = 1.0
    score_with_sim = score_acoustid_candidate(
        matcher=matcher,
        candidate=candidate,
        baseline_title="Lovely",
        file_duration_ms=file_duration_ms,
        baseline_artist="Billie Eilish",
        baseline_album="Don't Smile at Me",
        sim_score=0.85,
    )
    assert score_with_sim > 80.0


def test_metadata_resolution_engine_score_candidate_forwards_sim_score():
    """Verify MetadataResolutionEngine.score_candidate forwards sim_score to score_acoustid_candidate."""
    engine = MetadataResolutionEngine()
    candidate = {
        "title": "Lovely",
        "artist": "Billie Eilish",
        "album": "Don't Smile at Me",
        "duration_ms": 200186,
        "score": 0.85,
        "release_group": {"primary_type": "Album"},
    }
    file_duration_ms = 202485

    score = engine.score_candidate(
        candidate=candidate,
        baseline_title="Lovely",
        file_duration_ms=file_duration_ms,
        baseline_artist="Billie Eilish",
        baseline_album="Don't Smile at Me",
    )
    assert score > 80.0
