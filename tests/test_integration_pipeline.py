"""
Integration tests for the complete SoulSync matching pipeline

Tests the end-to-end workflow:
Raw Filename → TrackParser → MatchService → WeightedMatchingEngine → PostProcessor

This validates that all components work together correctly.
"""

import pytest

pytestmark = pytest.mark.skip(reason="Integration tests depend on incomplete database matching engine")
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from core import (
    SoulSyncTrack,
    TrackParser,
    MatchService,
    MatchContext,
    get_match_service,
)
from core.post_processor import PostProcessor


class TestIntegrationPipeline:
    """Integration tests for complete matching and organizing pipeline"""

    def setup_method(self):
        """Setup for each test"""
        self.parser = TrackParser()
        self.match_service = MatchService()
        self.post_processor = PostProcessor(check_mutagen=False)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

    def teardown_method(self):
        """Cleanup after each test"""
        self.temp_dir.cleanup()

    def test_parse_then_match(self):
        """Test parsing raw filename then matching against candidates"""
        # Raw input (like from Slskd)
        raw_string = "The Weeknd - Blinding Lights (Chromatics Remix) [FLAC 24bit]"

        # Create candidate tracks (like from Spotify)
        candidates = [
            SoulSyncTrack(
                title="Blinding Lights",
                artist="The Weeknd",
                album="After Hours",
                duration_ms=200040,
                version="Original",
            ),
            SoulSyncTrack(
                title="Blinding Lights",
                artist="The Weeknd",
                album="After Hours",
                duration_ms=240000,
                version="Chromatics Remix",
                quality_tags=["FLAC", "24bit"],
            ),
            SoulSyncTrack(
                title="Different Song",
                artist="Different Artist",
                duration_ms=300000,
            ),
        ]

        # Step 1: Parse raw string
        parsed = self.parser.parse_filename(raw_string)
        assert parsed is not None
        assert "weeknd" in parsed.artist.lower() or "blinding" in parsed.title.lower()

        # Step 2: Find best match
        best_match = self.match_service.find_best_match(
            parsed, candidates, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert best_match is not None
        assert best_match.confidence_score > 70
        # The remix version should match well
        assert "chromatics" in best_match.candidate_track.version.lower()

    def test_full_pipeline_with_organization(self):
        """Test parsing, matching, and organizing a file"""
        # Create a source file
        source_dir = self.base_dir / "downloads"
        source_dir.mkdir()
        source_file = source_dir / "The_Weeknd_-_Blinding_Lights_FLAC.mp3"
        source_file.touch()

        # Raw string
        raw_string = "The Weeknd - Blinding Lights"

        # Candidate (simulating metadata lookup)
        candidate = SoulSyncTrack(
            title="Blinding Lights",
            artist="The Weeknd",
            album="After Hours",
            year=2019,
            duration_ms=200040,
        )

        # Step 1: Parse
        parsed = self.parser.parse_filename(raw_string)
        assert parsed is not None

        # Step 2: Match (against single candidate)
        match = self.match_service.compare_tracks(
            parsed, candidate, context=MatchContext.DOWNLOAD_SEARCH
        )
        assert match.confidence_score > 0

        # Step 3: Organize file
        org_dir = self.base_dir / "organized"
        pattern = "{Artist}/{Year} - {Album}/{Title}{ext}"

        result = self.post_processor.organize_file(
            source_file, candidate, pattern, org_dir
        )

        assert result.moved or result.destination_path.exists()
        # Should be organized under The Weeknd
        path_str = str(result.destination_path)
        assert "Weeknd" in path_str or "weeknd" in path_str.lower()

    def test_multiple_candidates_ranking(self):
        """Test ranking multiple candidates"""
        raw_string = "Calvin Harris - Summer (Disclosure Remix)"

        candidates = [
            SoulSyncTrack(
                title="Summer",
                artist="Calvin Harris",
                album="18 Months",
                duration_ms=180000,
            ),
            SoulSyncTrack(
                title="Summer",
                artist="Calvin Harris",
                album="18 Months",
                duration_ms=240000,
                version="Disclosure Remix",
            ),
            SoulSyncTrack(
                title="Summer",
                artist="Different Artist",
                duration_ms=200000,
            ),
        ]

        parsed = self.parser.parse_filename(raw_string)

        # Get top matches
        top_matches = self.match_service.find_top_matches(
            parsed, candidates, context=MatchContext.DOWNLOAD_SEARCH, top_n=2
        )

        assert len(top_matches) > 0
        # First result should be the best
        assert top_matches[0].rank == 1

    def test_compilation_detection_and_matching(self):
        """Test matching compilation tracks"""
        raw_string = "01. Billie Eilish - Bad Guy [from Various Artists Compilation]"

        candidate = SoulSyncTrack(
            title="Bad Guy",
            artist="Billie Eilish",
            album="When We All Fall Asleep, Where Do We Go?",
            track_number=1,
            is_compilation=False,  # The candidate is not a compilation
        )

        parsed = self.parser.parse_filename(raw_string)

        # Should still match even if compilation flag differs
        match = self.match_service.compare_tracks(
            parsed, candidate, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert match.confidence_score > 0

    def test_version_mismatch_penalty(self):
        """Test that version mismatches apply penalties"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            version="Original",
            duration_ms=180000,
        )

        # Remix version
        remix_candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            version="Remix",
            duration_ms=240000,
        )

        # Original version
        original_candidate = SoulSyncTrack(
            title="Song",
            artist="Artist",
            version="Original",
            duration_ms=180000,
        )

        remix_match = self.match_service.compare_tracks(source, remix_candidate)
        original_match = self.match_service.compare_tracks(source, original_candidate)

        # Original should score higher when source is original
        assert original_match.confidence_score > remix_match.confidence_score

    def test_profile_selection_affects_matching(self):
        """Test that different profiles affect match results"""
        source = SoulSyncTrack(
            title="Song Title",
            artist="Artist",
            duration_ms=180000,
        )

        candidate = SoulSyncTrack(
            title="Song Title",
            artist="Artist",
            duration_ms=192000,  # 12 seconds different
        )

        # EXACT_SYNC should be stricter
        exact_match = self.match_service.compare_tracks(
            source, candidate, context=MatchContext.EXACT_SYNC
        )

        # LIBRARY_IMPORT should be more tolerant
        import_match = self.match_service.compare_tracks(
            source, candidate, context=MatchContext.LIBRARY_IMPORT
        )

        # Both should find a match, but import might score higher
        assert import_match.confidence_score >= exact_match.confidence_score

    def test_end_to_end_with_caching(self):
        """Test that caching works end-to-end"""
        raw_string = "Artist - Track Title"

        # First call - should cache
        parsed1 = self.match_service.parse_filename(raw_string)

        # Second call - should use cache
        parsed2 = self.match_service.parse_filename(raw_string)

        # Both should return the same result
        assert parsed1 is not None
        assert parsed2 is not None
        assert parsed1.title == parsed2.title
        assert parsed1.artist == parsed2.artist

    def test_match_stats_generation(self):
        """Test generating match statistics"""
        source = SoulSyncTrack(
            title="Song",
            artist="Artist",
            duration_ms=180000,
        )

        candidates = [
            SoulSyncTrack(title="Song", artist="Artist", duration_ms=180000),
            SoulSyncTrack(title="Song", artist="Artist", duration_ms=181000),
            SoulSyncTrack(title="Different", artist="Other", duration_ms=300000),
        ]

        stats = self.match_service.get_match_stats(
            source, candidates, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert stats["total_candidates"] == 3
        assert stats["matches_found"] > 0
        assert "best_score" in stats
        assert "average_score" in stats

    def test_exact_sync_profile_strict_matching(self):
        """Test EXACT_SYNC profile for strict matching"""
        source = SoulSyncTrack(
            title="Exact Song Title",
            artist="Exact Artist Name",
            duration_ms=200000,
        )

        # Very similar candidate
        similar_candidate = SoulSyncTrack(
            title="Exact Song Title",
            artist="Exact Artist Name",
            duration_ms=201000,
        )

        # Different candidate
        different_candidate = SoulSyncTrack(
            title="Different Song",
            artist="Different Artist",
            duration_ms=250000,
        )

        similar_match = self.match_service.compare_tracks(
            source, similar_candidate, context=MatchContext.EXACT_SYNC
        )

        different_match = self.match_service.compare_tracks(
            source, different_candidate, context=MatchContext.EXACT_SYNC
        )

        # Similar should score much higher
        assert similar_match.confidence_score > different_match.confidence_score

    def test_download_search_profile_tolerant(self):
        """Test DOWNLOAD_SEARCH profile for tolerant matching"""
        source = SoulSyncTrack(
            title="Song Title",
            artist="Artist Name",
            duration_ms=180000,
        )

        # Similar but different candidate
        candidate = SoulSyncTrack(
            title="Song Title",
            artist="Artist Name",
            duration_ms=190000,  # 10 seconds different
            version="Extended Mix",
        )

        match = self.match_service.compare_tracks(
            source, candidate, context=MatchContext.DOWNLOAD_SEARCH
        )

        # Should still match well in DOWNLOAD_SEARCH
        assert match.confidence_score > 60

    def test_library_import_profile_fingerprint_first(self):
        """Test LIBRARY_IMPORT profile prioritizes fingerprinting"""
        source = SoulSyncTrack(
            title="Local File Name",
            artist="Local Artist",
            duration_ms=200000,
        )

        # Candidate from metadata provider
        candidate = SoulSyncTrack(
            title="Proper Song Title",
            artist="Proper Artist Name",
            album="Album",
            duration_ms=200000,  # Duration matches exactly
            year=2024,
        )

        match = self.match_service.compare_tracks(
            source, candidate, context=MatchContext.LIBRARY_IMPORT
        )

        # Should match due to duration alignment (fingerprint-like)
        assert match.confidence_score > 50


class TestIntegrationWithRealWorldExamples:
    """Integration tests with realistic SoulSeek/Tidal examples"""

    def setup_method(self):
        self.match_service = MatchService()

    def test_beatport_format_to_spotify(self):
        """Test matching Beatport filename to Spotify metadata"""
        raw = "Daft Punk - Homework - Da Funk (Chromatics Remix) [FLAC 24bit]"

        spotify_track = SoulSyncTrack(
            title="Da Funk",
            artist="Daft Punk",
            album="Homework",
            year=1997,
            duration_ms=355640,
        )

        parsed = self.match_service.parse_filename(raw)
        assert parsed is not None

        match = self.match_service.compare_tracks(
            parsed, spotify_track, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert match.confidence_score > 70

    def test_soulseek_format_to_tidal(self):
        """Test matching SoulSeek download to TIDAL metadata"""
        raw = "01 - The Weeknd - Blinding Lights (Radio Edit) [MP3 320kbps]"

        tidal_track = SoulSyncTrack(
            title="Blinding Lights",
            artist="The Weeknd",
            album="After Hours",
            track_number=1,
            duration_ms=200040,
        )

        parsed = self.match_service.parse_filename(raw)
        assert parsed is not None

        match = self.match_service.compare_tracks(
            parsed, tidal_track, context=MatchContext.DOWNLOAD_SEARCH
        )

        # Should match well despite "Radio Edit" not being in candidate
        assert match.confidence_score > 70


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
