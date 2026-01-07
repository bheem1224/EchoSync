"""
Comprehensive tests for WeightedMatchingEngine scoring logic

Tests cover:
- 5-step gating logic (version, edition, text, duration, quality)
- Score normalization (0-100 range)
- Penalty application
- Different scoring profiles
- Edge cases and boundary conditions
"""

import pytest
from core.matching_engine import WeightedMatchingEngine, MatchResult
from core.matching_engine import SoulSyncTrack, QualityTag
from core.matching_engine import (
    PROFILE_EXACT_SYNC,
    PROFILE_DOWNLOAD_SEARCH,
    PROFILE_LIBRARY_IMPORT,
)


class TestWeightedMatchingEngineBasic:
    """Basic matching tests"""

    def setup_method(self):
        """Setup engine with default profile"""
        self.engine = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)

    def test_exact_match(self):
        """Test matching identical tracks"""
        source = SoulSyncTrack(
            title="Blinding Lights",
            artist="The Weeknd",
            duration_ms=200040,
        )
        candidate = SoulSyncTrack(
            title="Blinding Lights",
            artist="The Weeknd",
            duration_ms=200040,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result is not None
        assert result.confidence_score > 80  # Should be very high

    def test_similar_match(self):
        """Test matching similar tracks"""
        source = SoulSyncTrack(
            title="Blinding Lights",
            artist="The Weeknd",
            duration_ms=200000,
        )
        candidate = SoulSyncTrack(
            title="Blinding Lights",
            artist="The Weeknd",
            duration_ms=201000,  # 1 second different
        )

        result = self.engine.calculate_match(source, candidate)
        assert result is not None
        assert 70 < result.confidence_score < 100

    def test_different_tracks(self):
        """Test matching completely different tracks"""
        source = SoulSyncTrack(
            title="Song A",
            artist="Artist A",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song B",
            artist="Artist B",
            duration_ms=300000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result is not None
        assert result.confidence_score < 50  # Should be low

    def test_score_in_valid_range(self):
        """Test that scores are always 0-100"""
        source = SoulSyncTrack(title="Song", artist="Artist", duration_ms=180000)
        candidate = SoulSyncTrack(title="Different", artist="Other", duration_ms=200000)

        result = self.engine.calculate_match(source, candidate)
        assert 0 <= result.confidence_score <= 100


class TestWeightedMatchingEngineVersionCheck:
    """Tests for version matching (Step 1 of gating)"""

    def setup_method(self):
        self.engine = WeightedMatchingEngine(PROFILE_EXACT_SYNC)

    def test_exact_version_match(self):
        """Test exact version match"""
        source = SoulSyncTrack(
            title="Summer",
            artist="Calvin Harris",
            version="Chromatics Remix",
            duration_ms=300000,
        )
        candidate = SoulSyncTrack(
            title="Summer",
            artist="Calvin Harris",
            version="Chromatics Remix",
            duration_ms=300000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result.passed_version_check is True
        assert "Version match" in result.reasoning

    def test_version_mismatch_original_vs_remix(self):
        """Test mismatch between original and remix"""
        source = SoulSyncTrack(
            title="Original",
            artist="Artist",
            version="Original",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Original",
            artist="Artist",
            version="Remix",
            duration_ms=240000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result.passed_version_check is False
        assert result.version_penalty_applied > 0

    def test_no_version_vs_version(self):
        """Test matching track with version to one without"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            version=None,
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            version="Remix",
            duration_ms=240000,
        )

        result = self.engine.calculate_match(source, candidate)
        # Should be lenient when source has no version
        assert result.passed_version_check is True

    def test_similar_version_keywords(self):
        """Test versions with similar keywords"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            version="Extended Mix",
            duration_ms=300000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            version="Extended Version",
            duration_ms=300000,
        )

        result = self.engine.calculate_match(source, candidate)
        # Should match because both have 'extended'
        assert result.passed_version_check is True


class TestWeightedMatchingEngineEditionCheck:
    """Tests for edition matching (Step 2 of gating)"""

    def setup_method(self):
        self.engine = WeightedMatchingEngine(PROFILE_EXACT_SYNC)

    def test_matching_track_totals(self):
        """Test tracks with matching track totals"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            album="Album",
            track_total=12,
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            album="Album",
            track_total=12,
            duration_ms=180000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result.passed_edition_check is True

    def test_mismatched_track_totals(self):
        """Test tracks with different track totals"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            album="Album",
            track_total=12,
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            album="Album",
            track_total=16,  # Deluxe edition
            duration_ms=180000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result.passed_edition_check is False
        assert result.edition_penalty_applied > 0

    def test_no_track_total_info(self):
        """Test when track_total is not available"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result.passed_edition_check is True


class TestWeightedMatchingEngineFuzzyText:
    """Tests for fuzzy text matching (Step 3 of gating)"""

    def setup_method(self):
        self.engine = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)

    def test_exact_title_match(self):
        """Test exact title match"""
        source = SoulSyncTrack(
            title="Blinding Lights",
            artist="The Weeknd",
            duration_ms=200000,
        )
        candidate = SoulSyncTrack(
            title="Blinding Lights",
            artist="The Weeknd",
            duration_ms=200000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result.fuzzy_text_score > 0.95

    def test_title_with_typo(self):
        """Test title with minor typo"""
        source = SoulSyncTrack(
            title="Blinding Lights",
            artist="The Weeknd",
            duration_ms=200000,
        )
        candidate = SoulSyncTrack(
            title="Blinding Lites",  # Typo
            artist="The Weeknd",
            duration_ms=200000,
        )

        result = self.engine.calculate_match(source, candidate)
        # Should still be fairly high
        assert result.fuzzy_text_score > 0.80

    def test_case_insensitive_match(self):
        """Test case-insensitive matching"""
        source = SoulSyncTrack(
            title="BLINDING LIGHTS",
            artist="THE WEEKND",
            duration_ms=200000,
        )
        candidate = SoulSyncTrack(
            title="blinding lights",
            artist="the weeknd",
            duration_ms=200000,
        )

        result = self.engine.calculate_match(source, candidate)
        # Should be high despite case difference
        assert result.fuzzy_text_score > 0.90

    def test_below_fuzzy_threshold_fails(self):
        """Test that very low fuzzy match fails gating"""
        source = SoulSyncTrack(
            title="Completely Different Song",
            artist="Artist A",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Totally Unrelated Track",
            artist="Artist B",
            duration_ms=200000,
        )

        result = self.engine.calculate_match(source, candidate)
        # Should fail fuzzy threshold
        assert result.confidence_score == 0.0


class TestWeightedMatchingEngineDuration:
    """Tests for duration matching (Step 4 of gating)"""

    def setup_method(self):
        self.engine = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)

    def test_exact_duration_match(self):
        """Test exact duration match"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result.duration_match_score == 1.0

    def test_duration_within_tolerance(self):
        """Test duration within tolerance window"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=182000,  # 2 seconds difference
        )

        result = self.engine.calculate_match(source, candidate)
        # Should be within tolerance (default 5 seconds for DOWNLOAD_SEARCH)
        assert result.duration_match_score > 0.9

    def test_duration_outside_tolerance(self):
        """Test duration outside tolerance window"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=200000,  # 20 seconds different
        )

        result = self.engine.calculate_match(source, candidate)
        # Should be outside tolerance, score drops
        assert result.duration_match_score < 0.5

    def test_missing_duration_info(self):
        """Test when duration is not available"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=None,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )

        result = self.engine.calculate_match(source, candidate)
        # Should assume match when info is missing
        assert result.duration_match_score == 1.0


class TestWeightedMatchingEngineQuality:
    """Tests for quality tie-breaker (Step 5 of gating)"""

    def setup_method(self):
        self.engine = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)

    def test_quality_bonus_applied(self):
        """Test quality bonus is applied"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
            quality_tags=[QualityTag.FLAC_24BIT.value],
        )

        result = self.engine.calculate_match(source, candidate)
        assert result.quality_bonus_applied > 0

    def test_no_quality_bonus_without_tags(self):
        """Test no quality bonus when candidate has no quality tags"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
            quality_tags=[],
        )

        result = self.engine.calculate_match(source, candidate)
        assert result.quality_bonus_applied == 0


class TestWeightedMatchingEngineProfiles:
    """Tests for different scoring profiles"""

    def test_exact_sync_stricter_than_download_search(self):
        """Test that EXACT_SYNC is stricter than DOWNLOAD_SEARCH"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=190000,  # 10 seconds different
        )

        exact_engine = WeightedMatchingEngine(PROFILE_EXACT_SYNC)
        download_engine = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)

        exact_result = exact_engine.calculate_match(source, candidate)
        download_result = download_engine.calculate_match(source, candidate)

        # DOWNLOAD_SEARCH should be more lenient
        assert download_result.confidence_score >= exact_result.confidence_score

    def test_library_import_tolerant(self):
        """Test LIBRARY_IMPORT profile is tolerant"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            version="Remaster",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            version="Original",
            duration_ms=188000,  # 8 seconds different
        )

        import_engine = WeightedMatchingEngine(PROFILE_LIBRARY_IMPORT)
        result = import_engine.calculate_match(source, candidate)

        # Should be more tolerant
        assert result.confidence_score > 60


class TestWeightedMatchingEngineEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def setup_method(self):
        self.engine = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)

    def test_empty_artist_title(self):
        """Test matching with empty fields"""
        source = SoulSyncTrack(
            title="",
            artist="",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result is not None
        assert 0 <= result.confidence_score <= 100

    def test_very_long_title(self):
        """Test matching with very long titles"""
        long_title = "A" * 300
        source = SoulSyncTrack(
            title=long_title,
            artist="Artist",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title=long_title,
            artist="Artist",
            duration_ms=180000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result is not None

    def test_unicode_characters(self):
        """Test matching with unicode characters"""
        source = SoulSyncTrack(
            title="Björk - Jóga",
            artist="Björk",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Björk - Jóga",
            artist="Björk",
            duration_ms=180000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result.confidence_score > 80

    def test_special_characters(self):
        """Test matching with special characters"""
        source = SoulSyncTrack(
            title="Song & Dance!",
            artist="Artist (Real Name)",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song & Dance!",
            artist="Artist (Real Name)",
            duration_ms=180000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert result is not None


class TestWeightedMatchingEngineReasoning:
    """Tests for detailed reasoning in MatchResult"""

    def setup_method(self):
        self.engine = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)

    def test_reasoning_includes_version_info(self):
        """Test that reasoning includes version information"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            version="Remix",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            version="Original",
            duration_ms=180000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert "Version" in result.reasoning or "version" in result.reasoning.lower()

    def test_reasoning_includes_duration_info(self):
        """Test that reasoning includes duration information"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=200000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert "Duration" in result.reasoning or "duration" in result.reasoning.lower()

    def test_reasoning_includes_final_score(self):
        """Test that reasoning includes final score"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )
        candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )

        result = self.engine.calculate_match(source, candidate)
        assert "FINAL SCORE" in result.reasoning


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
