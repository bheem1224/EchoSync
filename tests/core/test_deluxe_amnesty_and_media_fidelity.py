"""
Tests for Deluxe/Container Edition Compatibility Amnesty and Physical Media Fidelity Scoring.

Verifies:
- Test A: Candidate with edition 'Deluxe Edition' matching clean source has
          passed_version_check = True and version_penalty = 0.0.
- Test B: Candidate with edition 'Extended Mix' does NOT receive the exemption
          and is evaluated under version mismatch rules.
- Test C: Candidate with local_media containing a FLAC file (bitrate=1080)
          receives the fidelity bonus over a 128kbps MP3 candidate of the same track.
- Test D: Low-bitrate Deluxe edition does not receive arbitrary text bonuses
          over a higher-bitrate original edition.
"""

import pytest
from core.db.echo_sync_track import EchosyncMedia, EchosyncTrack
from core.matching_engine.matching_engine import (
    WeightedMatchingEngine,
    evaluate_version_compatibility,
)
from core.matching_engine.scoring_profile import DownloadSearchProfile, ExactSyncProfile


def test_deluxe_edition_amnesty_clean_source():
    """
    Test A: Candidate with edition 'Deluxe Edition' matching clean source
    has passed_version_check = True and version_penalty = 0.0.
    """
    source = EchosyncTrack(
        raw_title="Fix You",
        artist_name="Coldplay",
        album_title="X&Y",
        duration=295000,
    )
    candidate = EchosyncTrack(
        raw_title="Fix You",
        artist_name="Coldplay",
        album_title="X&Y",
        edition="Deluxe Edition",
        duration=295000,
    )

    # 1. Direct evaluate_version_compatibility verification
    is_compat, penalty, reason = evaluate_version_compatibility(
        source.edition,
        candidate.edition,
        context="sync",
        duration_delta_ms=0,
    )
    assert is_compat is True
    assert penalty == 0.0
    assert "Studio container qualifier amnesty" in reason or "Original" in reason

    # 2. Engine calculate_match verification
    engine = WeightedMatchingEngine(ExactSyncProfile())
    result = engine.calculate_match(source, candidate, context="sync")

    assert result.passed_version_check is True
    assert result.version_penalty_applied == 0.0
    assert result.confidence_score >= 95.0


def test_extended_mix_excluded_from_amnesty():
    """
    Test B: Candidate with edition 'Extended Mix' does NOT receive the exemption
    and is evaluated under version mismatch rules.
    """
    source = EchosyncTrack(
        raw_title="Midnight City",
        artist_name="M83",
        album_title="Hurry Up, We're Dreaming",
        duration=243000,
    )
    # Extended mix with significant duration difference (e.g. 60s longer)
    candidate = EchosyncTrack(
        raw_title="Midnight City",
        artist_name="M83",
        album_title="Hurry Up, We're Dreaming",
        edition="Extended Mix",
        duration=303000,  # +60s duration
    )

    # 1. Direct evaluate_version_compatibility verification
    is_compat, penalty, reason = evaluate_version_compatibility(
        source.edition,
        candidate.edition,
        context="sync",
        duration_delta_ms=60000,
    )
    assert is_compat is False
    assert "extended" in reason.lower() or "mismatch" in reason.lower()

    # 2. Engine calculate_match verification
    engine = WeightedMatchingEngine(ExactSyncProfile())
    result = engine.calculate_match(source, candidate, context="sync")

    assert result.passed_version_check is False
    assert result.confidence_score == 0.0


def test_fidelity_bonus_flac_over_mp3():
    """
    Test C: Candidate with local_media containing a FLAC file (bitrate=1080)
    receives the fidelity bonus over a 128kbps MP3 candidate of the same track.
    """
    source = EchosyncTrack(
        raw_title="Blinding Lights",
        artist_name="The Weeknd",
        album_title="After Hours",
        duration=200000,
    )

    cand_flac = EchosyncTrack(
        raw_title="Blinding Lights",
        artist_name="The Weeknd",
        album_title="After Hours",
        duration=200000,
    )
    cand_flac.local_media = [
        EchosyncMedia(
            file_path="/music/The Weeknd/Blinding Lights.flac",
            file_format="flac",
            bitrate=1080,
            sample_rate=44100,
            bit_depth=16,
        )
    ]

    cand_mp3 = EchosyncTrack(
        raw_title="Blinding Lights",
        artist_name="The Weeknd",
        album_title="After Hours",
        duration=200000,
    )
    cand_mp3.local_media = [
        EchosyncMedia(
            file_path="/music/The Weeknd/Blinding Lights.mp3",
            file_format="mp3",
            bitrate=128,
            sample_rate=44100,
            bit_depth=16,
        )
    ]

    engine = WeightedMatchingEngine(ExactSyncProfile())
    res_flac = engine.calculate_match(source, cand_flac, context="sync")
    res_mp3 = engine.calculate_match(source, cand_mp3, context="sync")

    assert res_flac.passed_version_check is True
    assert res_mp3.passed_version_check is True

    # FLAC candidate receives lossless fidelity bonus (+3.0)
    # MP3 128k receives 0.0 fidelity bonus
    assert res_flac.quality_bonus_applied == 3.0
    assert res_mp3.quality_bonus_applied == 0.0
    assert res_flac.confidence_score > res_mp3.confidence_score
    assert round(res_flac.confidence_score - res_mp3.confidence_score, 1) == 3.0


def test_low_bitrate_deluxe_does_not_beat_high_bitrate_original():
    """
    Test D: Low-bitrate Deluxe edition does not receive arbitrary text bonuses
    over a higher-bitrate original edition.
    """
    source = EchosyncTrack(
        raw_title="Hotel California",
        artist_name="Eagles",
        album_title="Hotel California",
        duration=390000,
    )

    # Deluxe Edition rip in low-bitrate MP3 128k
    cand_deluxe_low = EchosyncTrack(
        raw_title="Hotel California",
        artist_name="Eagles",
        album_title="Hotel California (Deluxe Edition)",
        edition="Deluxe Edition",
        duration=390000,
    )
    cand_deluxe_low.local_media = [
        EchosyncMedia(
            file_path="/music/Eagles/Hotel California Deluxe.mp3",
            file_format="mp3",
            bitrate=128,
        )
    ]

    # Standard original release in 320k MP3
    cand_orig_high = EchosyncTrack(
        raw_title="Hotel California",
        artist_name="Eagles",
        album_title="Hotel California",
        duration=390000,
    )
    cand_orig_high.local_media = [
        EchosyncMedia(
            file_path="/music/Eagles/Hotel California.mp3",
            file_format="mp3",
            bitrate=320,
        )
    ]

    engine = WeightedMatchingEngine(ExactSyncProfile())
    res_deluxe = engine.calculate_match(source, cand_deluxe_low, context="sync")
    res_orig = engine.calculate_match(source, cand_orig_high, context="sync")

    # High bitrate original gets 1.5 bitrate fidelity bonus, while 128k deluxe gets 0.0
    # No arbitrary +2.0 or other text bonus awarded to the Deluxe candidate
    assert res_orig.confidence_score > res_deluxe.confidence_score
    assert res_deluxe.quality_bonus_applied == 0.0
    assert res_orig.quality_bonus_applied == 1.5
