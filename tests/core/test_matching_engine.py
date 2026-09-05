from core.db.echo_sync_track import EchosyncTrack
from core.matching_engine.matching_engine import (
    WeightedMatchingEngine,
    calculate_duration_score,
)
from core.matching_engine.scoring_profile import ExactSyncProfile


def test_polynomial_duration_penalty_decay_standard_mode():
    """Verify standard mode polynomial decay (T=5000, Limit=6000, k=6)."""
    assert calculate_duration_score(0, strict=False) == 1.0
    assert calculate_duration_score(5000, strict=False) == 1.0

    # 5050ms has negligible decay (k=6 buffer) -> score > 0.99
    score_5050 = calculate_duration_score(5050, strict=False)
    assert score_5050 > 0.99
    assert score_5050 < 1.0

    # Intermediate point (e.g. 5500ms -> (0.5)**6 = 0.015625 -> ~0.984)
    assert calculate_duration_score(5500, strict=False) > 0.98

    # Hard limit at 6000ms and beyond is 0.0
    assert calculate_duration_score(6000, strict=False) == 0.0
    assert calculate_duration_score(6001, strict=False) == 0.0
    assert calculate_duration_score(7000, strict=False) == 0.0


def test_polynomial_duration_penalty_decay_strict_mode():
    """Verify strict mode polynomial decay (T=2000, Limit=3000, k=6)."""
    assert calculate_duration_score(0, strict=True) == 1.0
    assert calculate_duration_score(2000, strict=True) == 1.0

    # 2050ms has negligible decay -> score > 0.99
    score_2050 = calculate_duration_score(2050, strict=True)
    assert score_2050 > 0.99
    assert score_2050 < 1.0

    # Hard limit at 3000ms and beyond is 0.0
    assert calculate_duration_score(3000, strict=True) == 0.0
    assert calculate_duration_score(3001, strict=True) == 0.0
    assert calculate_duration_score(4000, strict=True) == 0.0


def test_strict_remaster_rejection_for_original_queries():
    """Verify original track query strictly rejects candidates tagged with Remaster."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="Karma Police",
        artist_name="Radiohead",
        album_title="OK Computer",
        duration=264000,
    )
    candidate_remaster1 = EchosyncTrack(
        raw_title="Karma Police",
        artist_name="Radiohead",
        album_title="OK Computer",
        edition="2013 Remaster",
        duration=264000,
    )
    candidate_remaster2 = EchosyncTrack(
        raw_title="Karma Police",
        artist_name="Radiohead",
        album_title="OK Computer",
        edition="Remastered",
        duration=264000,
    )

    res1 = engine.calculate_match(source, candidate_remaster1, context="sync")
    assert res1.passed_version_check is False
    assert res1.confidence_score == 0.0

    res2 = engine.calculate_match(source, candidate_remaster2, context="download")
    assert res2.passed_version_check is False
    assert res2.confidence_score == 0.0


def test_deluxe_isolation_to_tier3_fallback():
    """Verify Deluxe edition fails in standard/sync tiers but matches in tier3_fallback."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source = EchosyncTrack(
        raw_title="Viva La Vida",
        artist_name="Coldplay",
        album_title="Viva La Vida",
        duration=242000,
    )
    candidate_deluxe = EchosyncTrack(
        raw_title="Viva La Vida",
        artist_name="Coldplay",
        album_title="Viva La Vida (Deluxe Edition)",
        edition="Deluxe",
        duration=242000,
    )

    # Standard context ("sync" / "standard"): strictly rejected
    res_std = engine.calculate_match(source, candidate_deluxe, context="sync")
    assert res_std.passed_version_check is False
    assert res_std.confidence_score == 0.0

    # Tier 3 fallback context: permitted within 10000ms duration delta
    res_t3 = engine.calculate_match(source, candidate_deluxe, context="tier3_fallback")
    assert res_t3.passed_version_check is True
    assert res_t3.confidence_score >= 85.0

    # If duration exceeds 10000ms in Tier 3, it is rejected
    candidate_deluxe_long = EchosyncTrack(
        raw_title="Viva La Vida",
        artist_name="Coldplay",
        album_title="Viva La Vida (Deluxe Edition)",
        edition="Deluxe",
        duration=255000,  # 13000ms delta > 10000ms
    )
    res_t3_long = engine.calculate_match(
        source, candidate_deluxe_long, context="tier3_fallback"
    )
    assert res_t3_long.passed_version_check is False
    assert res_t3_long.confidence_score == 0.0


def test_non_destructive_album_bonus():
    """Verify matching album grants +2.0 bonus and mismatched/missing album has zero deduction."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source_base = EchosyncTrack(
        raw_title="Fix You",
        artist_name="Coldplay",
        album_title="X&Y",
        duration=295000,
    )
    candidate_matching_album = EchosyncTrack(
        raw_title="Fix You",
        artist_name="Coldplay",
        album_title="X&Y",
        duration=295000,
    )
    candidate_different_album = EchosyncTrack(
        raw_title="Fix You",
        artist_name="Coldplay",
        album_title="Greatest Hits",
        duration=295000,
    )
    candidate_no_album = EchosyncTrack(
        raw_title="Fix You",
        artist_name="Coldplay",
        album_title="",
        duration=295000,
    )

    res_match = engine.calculate_match(source_base, candidate_matching_album)
    res_diff = engine.calculate_match(source_base, candidate_different_album)
    res_none = engine.calculate_match(source_base, candidate_no_album)

    # Base match without album is high confidence
    assert res_diff.confidence_score >= 85.0
    assert res_none.confidence_score >= 85.0

    # Different album has same score as no album (zero deduction for mismatch/missing)
    assert abs(res_diff.confidence_score - res_none.confidence_score) < 0.1

    # Matching album gets the +2.0 boost (clamped to 100.0)
    assert res_match.confidence_score >= res_diff.confidence_score
    assert any(
        "Non-destructive album bonus" in r for r in res_match.reasoning.split(" | ")
    )
