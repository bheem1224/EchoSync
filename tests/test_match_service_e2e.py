"""
End-to-end tests for MatchService API
Tests the high-level MatchService interface
"""

import pytest
from unittest.mock import Mock

from core import (
    SoulSyncTrack,
    MatchService,
    MatchContext,
    get_match_service,
)


class TestMatchServiceBasic:
    """Basic MatchService functionality tests"""

    def setup_method(self):
        """Setup for each test"""
        self.service = MatchService()

    def test_find_best_match_basic(self):
        """Test finding the best match from candidates"""
        source = SoulSyncTrack(
            raw_title="Song Title",
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        candidates = [
            SoulSyncTrack(
                raw_title="Different Song",
                artist_name="Different",
                album_title="",
                duration=200000,
            ),
            SoulSyncTrack(
                raw_title="Song Title",
                artist_name="Artist",
                album_title="",
                duration=180000,
            ),
            SoulSyncTrack(
                raw_title="Another Song",
                artist_name="Another",
                album_title="",
                duration=220000,
            ),
        ]

        best = self.service.find_best_match(
            source, candidates, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert best is not None
        assert best.candidate_track.title == "Song Title"
        assert best.confidence_score > 80

    def test_find_best_match_empty_candidates(self):
        """Test handling empty candidate list"""
        source = SoulSyncTrack(raw_title="Song", artist_name="Artist", album_title="", duration=180000)
        candidates = []

        best = self.service.find_best_match(
            source, candidates, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert best is None

    def test_find_top_matches(self):
        """Test finding top N matches"""
        source = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        candidates = [
            SoulSyncTrack(
                raw_title="Song",
                artist_name="Artist",
                album_title="",
                duration=180000,
            ),
            SoulSyncTrack(
                raw_title="Song",
                artist_name="Artist",
                album_title="",
                duration=181000,
            ),
            SoulSyncTrack(
                raw_title="Song",
                artist_name="Artist",
                album_title="",
                duration=182000,
            ),
            SoulSyncTrack(
                raw_title="Different",
                artist_name="Other",
                album_title="",
                duration=300000,
            ),
        ]

        top_3 = self.service.find_top_matches(
            source, candidates, top_n=3, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert len(top_3) <= 3
        if len(top_3) > 1:
            assert top_3[0].confidence_score >= top_3[1].confidence_score

    def test_find_top_matches_with_min_confidence(self):
        """Test top matches with minimum confidence threshold"""
        source = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        candidates = [
            SoulSyncTrack(
                raw_title="Song",
                artist_name="Artist",
                album_title="",
                duration=180000,
            ),
            SoulSyncTrack(
                raw_title="Different",
                artist_name="Other",
                album_title="",
                duration=300000,
            ),
        ]

        matches = self.service.find_top_matches(
            source, candidates, min_confidence=80, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert len(matches) >= 1
        for match in matches:
            assert match.confidence_score >= 80

    def test_compare_tracks(self):
        """Test comparing two tracks directly"""
        track_a = SoulSyncTrack(
            raw_title="Song A",
            artist_name="Artist A",
            album_title="",
            duration=180000,
        )

        track_b = SoulSyncTrack(
            raw_title="Song A",
            artist_name="Artist A",
            album_title="",
            duration=180000,
        )

        result = self.service.compare_tracks(
            track_a, track_b, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert result.confidence_score >= 90
        assert result.reasoning is not None

    def test_parse_filename(self):
        """Test parsing a filename"""
        raw = "Artist - Song Title (Remix) [FLAC 24bit]"

        parsed = self.service.parse_filename(raw)

        assert parsed is not None
        assert parsed.title is not None
        assert parsed.artist_name is not None

    def test_parse_and_match(self):
        """Test parsing and matching in one call"""
        raw = "Artist - Song Title"

        candidates = [
            SoulSyncTrack(
                raw_title="Song Title",
                artist_name="Artist",
                album_title="",
                duration=180000,
            ),
            SoulSyncTrack(
                raw_title="Different",
                artist_name="Other",
                album_title="",
                duration=200000,
            ),
        ]

        best = self.service.parse_and_match(
            raw, candidates, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert best is not None
        assert best.confidence_score > 70

    def test_get_match_stats(self):
        """Test getting match statistics"""
        source = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        candidates = [
            SoulSyncTrack(
                raw_title="Song",
                artist_name="Artist",
                album_title="",
                duration=180000,
            ),
            SoulSyncTrack(
                raw_title="Song",
                artist_name="Artist",
                album_title="",
                duration=181000,
            ),
            SoulSyncTrack(
                raw_title="Different",
                artist_name="Other",
                album_title="",
                duration=300000,
            ),
        ]

        stats = self.service.get_match_stats(
            source, candidates, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert stats["total_candidates"] == 3
        assert stats["matches_found"] > 0
        assert "best_score" in stats
        assert "average_score" in stats
        assert "median_score" in stats
        assert stats["best_score"] > 0


class TestMatchServiceContexts:
    """Test MatchService with different contexts"""

    def setup_method(self):
        self.service = MatchService()

    def test_context_exact_sync(self):
        """Test EXACT_SYNC context (strict matching)"""
        source = SoulSyncTrack(
            raw_title="Exact Title",
            artist_name="Exact Artist",
            album_title="Exact Album",
            duration=180000,
        )

        perfect_match = SoulSyncTrack(
            raw_title="Exact Title",
            artist_name="Exact Artist",
            album_title="Exact Album",
            duration=180000,
        )

        close_match = SoulSyncTrack(
            raw_title="Exact Title",
            artist_name="Exact Artist",
            album_title="Exact Album",
            duration=185000,
        )

        perfect_score = self.service.compare_tracks(
            source, perfect_match, context=MatchContext.EXACT_SYNC
        ).confidence_score

        close_score = self.service.compare_tracks(
            source, close_match, context=MatchContext.EXACT_SYNC
        ).confidence_score

        assert perfect_score > close_score

    def test_context_download_search(self):
        """Test DOWNLOAD_SEARCH context (tolerant matching)"""
        source = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        candidate_with_remix = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="Album",
            edition="Remix",
            duration=240000,
        )

        match = self.service.compare_tracks(
            source, candidate_with_remix, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert match.confidence_score > 50

    def test_context_library_import(self):
        """Test LIBRARY_IMPORT context (fuzzy matching)"""
        source = SoulSyncTrack(
            raw_title="My Song (Local)",
            artist_name="The Artist",
            album_title="",
            duration=200000,
        )

        metadata = SoulSyncTrack(
            raw_title="My Song",
            artist_name="The Artist",
            album_title="Album",
            duration=200000,
        )

        match = self.service.compare_tracks(
            source, metadata, context=MatchContext.LIBRARY_IMPORT
        )

        assert match.confidence_score > 50


class TestMatchServiceEdgeCases:
    """Test MatchService edge cases"""

    def setup_method(self):
        self.service = MatchService()

    def test_unicode_in_tracks(self):
        """Test handling unicode characters"""
        source = SoulSyncTrack(
            raw_title="Song with Ñoño",
            artist_name="Artístico",
            album_title="",
            duration=180000,
        )

        candidate = SoulSyncTrack(
            raw_title="Song with Ñoño",
            artist_name="Artístico",
            album_title="",
            duration=180000,
        )

        match = self.service.compare_tracks(source, candidate)

        assert match.confidence_score >= 90

    def test_very_long_titles(self):
        """Test handling very long track titles"""
        long_title = "A" * 500

        source = SoulSyncTrack(
            raw_title=long_title,
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        candidate = SoulSyncTrack(
            raw_title=long_title,
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        match = self.service.compare_tracks(source, candidate)

        assert match.confidence_score >= 90

    def test_missing_optional_fields(self):
        """Test tracks with missing optional fields"""
        source = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        candidate = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            duration=180000,
            album_title="Album",
            release_year=2024,
            edition="Original",
        )

        match = self.service.compare_tracks(
            source, candidate, context=MatchContext.LIBRARY_IMPORT
        )

        assert match.confidence_score > 70

    def test_zero_duration_handling(self):
        """Test handling tracks with zero duration"""
        source = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="",
            duration=0,
        )

        candidate = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        match = self.service.compare_tracks(
            source, candidate, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert match is not None

    def test_single_word_titles(self):
        """Test single-word track titles"""
        source = SoulSyncTrack(raw_title="Thriller", artist_name="Artist", album_title="", duration=180000)
        candidate = SoulSyncTrack(raw_title="Thriller", artist_name="Artist", album_title="", duration=180000)

        match = self.service.compare_tracks(source, candidate)

        assert match.confidence_score >= 90

    def test_numbers_in_titles(self):
        """Test track titles with numbers"""
        source = SoulSyncTrack(
            raw_title="Song 123 (Remix 2.0)",
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        candidate = SoulSyncTrack(
            raw_title="Song 123",
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        match = self.service.compare_tracks(
            source, candidate, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert match.confidence_score > 70


class TestMatchServiceGlobalFunctions:
    """Test global convenience functions"""

    def test_get_match_service_singleton(self):
        """Test that get_match_service returns a singleton"""
        service1 = get_match_service()
        service2 = get_match_service()

        assert service1 is service2

    def test_global_find_best_match(self):
        """Test global find_best_match function"""
        from core import find_best_match

        source = SoulSyncTrack(raw_title="Song", artist_name="Artist", album_title="", duration=180000)

        candidates = [
            SoulSyncTrack(raw_title="Song", artist_name="Artist", album_title="", duration=180000),
            SoulSyncTrack(raw_title="Different", artist_name="Other", album_title="", duration=200000),
        ]

        best = find_best_match(
            source, candidates, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert best is not None
        assert best.confidence_score > 80

    def test_global_parse_and_match(self):
        """Test global parse_and_match function"""
        from core import parse_and_match

        raw = "Artist - Song Title"

        candidates = [
            SoulSyncTrack(raw_title="Song Title", artist_name="Artist", album_title="", duration=180000),
        ]

        best = parse_and_match(
            raw, candidates, context=MatchContext.DOWNLOAD_SEARCH
        )

        assert best is not None


class TestMatchServiceCaching:
    """Test caching behavior in MatchService"""

    def setup_method(self):
        self.service = MatchService()

    def test_parse_filename_caching(self):
        """Test that parse_filename results are cached"""
        raw = "Artist - Song Title"

        parsed1 = self.service.parse_filename(raw)
        parsed2 = self.service.parse_filename(raw)

        assert parsed1 is not None
        assert parsed2 is not None
        assert parsed1.title == parsed2.title
        assert parsed1.artist_name == parsed2.artist_name


class TestMatchServicePerformance:
    """Test MatchService performance characteristics"""

    def setup_method(self):
        self.service = MatchService()

    def test_large_candidate_list(self):
        """Test matching against large candidate list"""
        source = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        candidates = [
            SoulSyncTrack(
                raw_title=f"Song {i}",
                artist_name=f"Artist {i}",
                album_title="",
                duration=180000 + i * 1000,
            )
            for i in range(100)
        ]
        candidates[50] = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        import time

        start = time.time()
        best = self.service.find_best_match(
            source, candidates, context=MatchContext.DOWNLOAD_SEARCH
        )
        elapsed = time.time() - start

        assert best is not None
        assert best.confidence_score > 80
        assert elapsed < 5.0

    def test_top_n_matches_performance(self):
        """Test performance of finding top N matches"""
        source = SoulSyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="",
            duration=180000,
        )

        candidates = [
            SoulSyncTrack(
                raw_title="Song",
                artist_name="Artist",
                album_title="",
                duration=180000 + i * 100,
            )
            for i in range(50)
        ]

        import time

        start = time.time()
        top_10 = self.service.find_top_matches(
            source, candidates, top_n=10, context=MatchContext.DOWNLOAD_SEARCH
        )
        elapsed = time.time() - start

        assert len(top_10) <= 10
        assert elapsed < 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
