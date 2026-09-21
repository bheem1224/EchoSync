"""Unit and regression tests for unified duration decay evaluation and MatchingEngine duration tolerance wiring."""

import pytest

from core.db.echo_sync_track import EchosyncTrack
from core.matching_engine.matching_engine import (
    WeightedMatchingEngine,
    calculate_duration_score,
)
from core.matching_engine.scoring_profile import (
    ExactSyncProfile,
    LibraryImportProfile,
)
from core.metadata.engine import compute_dynamic_duration_threshold
from core.metadata.scoring import (
    calculate_acoustid_duration_weight,
    calculate_bounded_duration_weight,
)


def test_calculate_bounded_duration_weight_unit():
    """Verify bounded duration weight: 1.0 up to base, smooth quadratic decay to max, 0.0 beyond."""
    base = 2.0
    max_sec = 5.0

    # Below or at base threshold
    assert calculate_bounded_duration_weight(0.0, base, max_sec) == 1.0
    assert calculate_bounded_duration_weight(1.0, base, max_sec) == 1.0
    assert calculate_bounded_duration_weight(2.0, base, max_sec) == 1.0
    assert calculate_bounded_duration_weight(-1.5, base, max_sec) == 1.0

    # At or above max threshold
    assert calculate_bounded_duration_weight(5.0, base, max_sec) == 0.0
    assert calculate_bounded_duration_weight(5.5, base, max_sec) == 0.0
    assert calculate_bounded_duration_weight(10.0, base, max_sec) == 0.0

    # Invalid thresholds: max_sec <= base
    assert calculate_bounded_duration_weight(1.5, 3.0, 3.0) == 0.0
    assert calculate_bounded_duration_weight(1.5, 4.0, 2.0) == 0.0

    # Intermediate quadratic decay:
    # Midpoint at delta = 3.5: ratio = (3.5 - 2.0) / (5.0 - 2.0) = 1.5 / 3.0 = 0.5
    # score = 1.0 - (0.5)^2 = 0.75
    assert pytest.approx(calculate_bounded_duration_weight(3.5, base, max_sec), 0.001) == 0.75


def test_calculate_acoustid_duration_weight_dynamic_lerp_retains_weight():
    """Verify candidate with delta=3.72s and similarity >= 0.95 retains > 0.60 weight and does NOT receive 0.0."""
    similarity = 0.96  # >= 0.95 -> dynamic threshold = 5.0s
    max_thresh = compute_dynamic_duration_threshold(similarity)
    assert max_thresh == 5.0

    delta = 3.72
    weight = calculate_acoustid_duration_weight(delta, max_sec=max_thresh)

    # In old code: delta > 2.0 hard-dropped to 0.0
    # In unified code: ratio = (3.72 - 2.0) / (5.0 - 2.0) = 0.5733 -> 1 - 0.5733^2 = 0.6713
    assert weight > 0.60
    assert weight != 0.0
    assert pytest.approx(weight, 0.01) == 0.67

    # Backward compatibility: default max_sec=2.0 still drops delta=3.72 to 0.0
    assert calculate_acoustid_duration_weight(delta, max_sec=2.0) == 0.0

    # Backward compatibility: 1.0s delta with max_sec=2.0 yields 0.75
    assert calculate_acoustid_duration_weight(200.0, 201.0, max_sec=2.0) == 0.75


def test_matching_engine_honors_duration_tolerance_from_profile():
    """Verify MatchingEngine._calculate_duration_match derives limits from profile duration_tolerance_ms."""
    # LibraryImportProfile sets duration_tolerance_ms = 8000ms
    engine_lib = WeightedMatchingEngine(LibraryImportProfile())
    source = EchosyncTrack(raw_title="Track A", artist_name="Artist", duration=200000)
    # Delta = 7000ms (within 8000ms base tolerance)
    candidate_within = EchosyncTrack(raw_title="Track A", artist_name="Artist", duration=207000)

    score_lib = engine_lib._calculate_duration_match(source, candidate_within)
    assert score_lib == 1.0

    # ExactSyncProfile has duration_tolerance_ms = 3000ms -> delta 7000ms must be 0.0
    engine_sync = WeightedMatchingEngine(ExactSyncProfile())
    score_sync = engine_sync._calculate_duration_match(source, candidate_within)
    assert score_sync == 0.0


def test_matching_engine_honors_tolerance_override_ms():
    """Verify MatchingEngine.calculate_match honors tolerance_override_ms=90000 for extended versions."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="Extended Dance Mix",
        artist_name="Daft Punk",
        duration=240000,  # 4m 00s
    )
    candidate = EchosyncTrack(
        raw_title="Extended Dance Mix",
        artist_name="Daft Punk",
        duration=300000,  # 5m 00s (delta = 60,000ms = 60s)
    )

    # Without override: 60s delta fails duration completely
    res_no_override = engine.calculate_match(source, candidate)
    assert res_no_override.duration_match_score == 0.0

    # With Tier A 90s override (90000ms): 60s delta is within 90s base tolerance
    res_override = engine.calculate_match(source, candidate, tolerance_override_ms=90000)
    assert res_override.duration_match_score == 1.0
    assert res_override.confidence_score >= 90.0


def test_calculate_title_duration_match_honors_tolerance_override():
    """Verify calculate_title_duration_match honors tolerance_override_ms."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="One More Time",
        duration=320000,
    )
    candidate = EchosyncTrack(
        raw_title="One More Time",
        duration=335000,  # delta = 15,000ms
    )

    # Without override: strict=True (2000/3000ms) drops 15s delta to 0.0
    res_strict = engine.calculate_title_duration_match(source, candidate)
    assert res_strict.duration_match_score == 0.0

    # With override=15000ms: delta is right at base tolerance -> score == 1.0
    res_over = engine.calculate_title_duration_match(source, candidate, tolerance_override_ms=15000)
    assert res_over.duration_match_score == 1.0
    assert res_over.confidence_score >= 90.0


def test_calculate_duration_score_dynamic_parameters():
    """Verify calculate_duration_score handles explicit t_base_ms and t_limit_ms."""
    # Custom 10s base, 15s limit
    assert calculate_duration_score(5000, t_base_ms=10000, t_limit_ms=15000) == 1.0
    assert calculate_duration_score(10000, t_base_ms=10000, t_limit_ms=15000) == 1.0
    assert calculate_duration_score(15000, t_base_ms=10000, t_limit_ms=15000) == 0.0
    assert calculate_duration_score(20000, t_base_ms=10000, t_limit_ms=15000) == 0.0

    # Auto limit: base 10000ms -> limit max(11000, 12500) = 12500ms
    assert calculate_duration_score(10000, t_base_ms=10000) == 1.0
    assert calculate_duration_score(12500, t_base_ms=10000) == 0.0

