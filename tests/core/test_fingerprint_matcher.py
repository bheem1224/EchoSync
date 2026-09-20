"""
Unit tests for native chromaprint fingerprint matching and comparison via echosync_core.
Verifies that FingerprintMatcher operates entirely on native Rust FFI without relying
on acoustid.compare (which does not exist in pyacoustid).
"""

import echosync_core
from core.matching_engine.fingerprinting import FingerprintMatcher


# Sample valid chromaprint strings (base64 compressed)
SAMPLE_FP_1 = (
    "AQAAf0mSpEkSRVEUB0mSB0mSBEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeS"
    "JEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeS"
)
SAMPLE_FP_2 = (
    "AQAAf0mSpEkSRVEUB0mSB0mSBEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeS"
    "JEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeSJEeS"
)


def test_native_echosync_core_has_compare_chromaprints():
    """Verify echosync_core exports the compare_chromaprints pyfunction."""
    assert hasattr(echosync_core, "compare_chromaprints")
    assert callable(echosync_core.compare_chromaprints)


def test_echosync_core_compare_chromaprints_identical():
    """Native Rust comparison of identical fingerprints returns 1.0."""
    score = echosync_core.compare_chromaprints(SAMPLE_FP_1, SAMPLE_FP_1)
    assert abs(score - 1.0) < 1e-6


def test_echosync_core_compare_chromaprints_empty_or_invalid():
    """Native Rust comparison with empty or invalid input safely returns 0.0."""
    assert echosync_core.compare_chromaprints("", SAMPLE_FP_1) == 0.0
    assert echosync_core.compare_chromaprints(SAMPLE_FP_1, "") == 0.0
    assert echosync_core.compare_chromaprints("", "") == 0.0
    assert echosync_core.compare_chromaprints("invalid_base64!@#$", SAMPLE_FP_1) == 0.0


def test_fingerprint_matcher_identical_confidence_and_match():
    """FingerprintMatcher correctly evaluates identical fingerprints with 1.0 confidence."""
    score = FingerprintMatcher.get_confidence_score(SAMPLE_FP_1, SAMPLE_FP_2)
    assert abs(score - 1.0) < 1e-6
    assert FingerprintMatcher.fingerprints_match(SAMPLE_FP_1, SAMPLE_FP_2) is True


def test_fingerprint_matcher_empty_and_none_handling():
    """FingerprintMatcher safely returns 0.0 and False for None or empty inputs without exceptions."""
    assert FingerprintMatcher.get_confidence_score(None, SAMPLE_FP_1) == 0.0
    assert FingerprintMatcher.get_confidence_score(SAMPLE_FP_1, None) == 0.0
    assert FingerprintMatcher.get_confidence_score(None, None) == 0.0
    assert FingerprintMatcher.get_confidence_score("", SAMPLE_FP_1) == 0.0

    assert FingerprintMatcher.fingerprints_match(None, SAMPLE_FP_1) is False
    assert FingerprintMatcher.fingerprints_match(SAMPLE_FP_1, None) is False
    assert FingerprintMatcher.fingerprints_match(None, None) is False
    assert FingerprintMatcher.fingerprints_match("", SAMPLE_FP_1) is False


def test_fingerprint_matcher_no_acoustid_compare_attribute_error():
    """Verify that calling get_confidence_score does not raise AttributeError for acoustid.compare."""
    # Even if pyacoustid is installed, it has no compare method.
    # FingerprintMatcher should cleanly invoke native Rust FFI and never raise.
    score = FingerprintMatcher.get_confidence_score(SAMPLE_FP_1, SAMPLE_FP_1)
    assert score == 1.0

