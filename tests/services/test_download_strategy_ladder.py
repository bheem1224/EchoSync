"""
Unit and integration tests for search strategy ladder, provider capability dispatching,
and multi-tier quality pre-filtering.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.db.echo_sync_track import EchosyncTrack
from core.enums import Capability
from core.matching_engine.text_utils import split_artist_collaborators, sanitize_query_for_wire
from plugins.EchoSync.slskd.client import SlskdProvider, _is_raw_file_eligible
from services.download_manager import (
    DownloadManager,
    SearchStrategyIntent,
    _provider_supports_capability,
)


class TestArtistDecompositionAndSanitization:
    """Test multi-artist decomposition and wire query sanitization."""

    def test_split_artist_collaborators_various_delimiters(self):
        primary, collabs = split_artist_collaborators("W&W x AXMO feat. Sonja")
        assert primary == "W&W"
        assert collabs == ["AXMO", "Sonja"]

        primary, collabs = split_artist_collaborators("Armin van Buuren & Brennan Heart ft. Andreas Moe")
        assert primary == "Armin van Buuren"
        assert collabs == ["Brennan Heart", "Andreas Moe"]

        primary, collabs = split_artist_collaborators("Calvin Harris with Ellie Goulding")
        assert primary == "Calvin Harris"
        assert collabs == ["Ellie Goulding"]

        primary, collabs = split_artist_collaborators("Single Artist")
        assert primary == "Single Artist"
        assert collabs == []

        primary, collabs = split_artist_collaborators(None)
        assert primary == ""
        assert collabs == []

    def test_sanitize_query_for_wire(self):
        assert sanitize_query_for_wire("W&W") == "W W"
        assert sanitize_query_for_wire("AC/DC") == "AC DC"
        assert sanitize_query_for_wire("Song (Original Mix) [2024]") == "Song Original Mix 2024"
        assert sanitize_query_for_wire("Artist & Collaborator / Remix!") == "Artist Collaborator Remix"


class TestSearchStrategyLadder:
    """Test 7-step strategy ladder generation."""

    def test_generate_search_strategies_ladder(self):
        manager = object.__new__(DownloadManager)
        track = EchosyncTrack(
            raw_title="Rave Love (Extended Mix)",
            artist_name="W&W x AXMO feat. Sonja",
            album_title="Rave Love EP",
            duration=180000,
            isrc="USUM71703881",
        )

        strategies = manager._generate_search_strategies(track, base_duration_tolerance_ms=5000)

        # 1. ISRC Lookup
        assert strategies[0].name == "isrc"
        assert strategies[0].required_capability == Capability.FETCH_BY_ISRC
        assert strategies[0].wire_query == "USUM71703881"

        # 2. Strict Artist + Title (Universal)
        assert strategies[1].name == "artist+title"
        assert strategies[1].required_capability is None
        assert "W W" in strategies[1].wire_query
        assert "rave love" in strategies[1].wire_query.lower()

        # 3. Broad Artist + Filter Title (Pre-Filter)
        assert strategies[2].name == "artist+broad+filter"
        assert strategies[2].required_capability == Capability.CLIENT_PREFILTER
        assert strategies[2].wire_query == "W W"
        assert strategies[2].filter_expression == "rave love"

        # 4. Title + Filter Artist (Pre-Filter)
        assert strategies[3].name == "title+filter_artist"
        assert strategies[3].required_capability == Capability.CLIENT_PREFILTER

        # 5. Collaborators + Filter Title (Pre-Filter)
        collab_strats = [s for s in strategies if s.name == "collab+filter_title"]
        assert len(collab_strats) == 2  # AXMO and Sonja
        assert collab_strats[0].wire_query == "AXMO"
        assert collab_strats[1].wire_query == "Sonja"

        # 6. Strict Album + Title (Universal)
        album_strat = next(s for s in strategies if s.name == "album+title")
        assert album_strat.required_capability is None
        assert "rave love" in album_strat.wire_query.lower()

        # 7. Title + Strict Duration Window (Universal)
        duration_strat = next(s for s in strategies if s.name == "title+strict-duration")
        assert duration_strat.required_capability is None
        assert duration_strat.duration_tolerance_ms == 2500  # 50% of 5000ms


class TestCapabilityDispatching:
    """Test provider capability filtering."""

    def test_provider_capability_filtering(self):
        # Provider with NO client pre-filtering and NO ISRC
        basic_provider = MagicMock()
        basic_provider.name = "BasicMock"
        basic_provider.capabilities = MagicMock()
        basic_provider.capabilities.to_enum_list.return_value = []
        basic_provider.supports_pre_filtering = False
        basic_provider.supports_isrc = False

        assert not _provider_supports_capability(basic_provider, Capability.CLIENT_PREFILTER)
        assert not _provider_supports_capability(basic_provider, Capability.FETCH_BY_ISRC)
        assert _provider_supports_capability(basic_provider, None)

        # Provider WITH pre-filtering
        prefilter_provider = MagicMock()
        prefilter_provider.name = "SlskdMock"
        prefilter_provider.capabilities = MagicMock()
        prefilter_provider.capabilities.to_enum_list.return_value = [Capability.CLIENT_PREFILTER]
        prefilter_provider.supports_pre_filtering = True

        assert _provider_supports_capability(prefilter_provider, Capability.CLIENT_PREFILTER)
        assert not _provider_supports_capability(prefilter_provider, Capability.FETCH_BY_ISRC)


class TestZeroAllocationStreamPreFiltering:
    """Test zero-allocation raw file validation."""

    def test_is_raw_file_eligible_drops_locked_and_duration_outliers(self):
        # Locked file
        locked_file = {"filename": "track.flac", "isLocked": True, "length": 180}
        assert not _is_raw_file_eligible(locked_file, basic_filters={"target_duration_ms": 180000})

        # Duration outlier (> 5000ms tolerance)
        outlier_file = {"filename": "track.flac", "isLocked": False, "length": 250}
        assert not _is_raw_file_eligible(
            outlier_file,
            basic_filters={"target_duration_ms": 180000, "duration_tolerance_ms": 5000}
        )

        # Valid duration match
        valid_file = {"filename": "track.flac", "isLocked": False, "length": 182}
        assert _is_raw_file_eligible(
            valid_file,
            basic_filters={"target_duration_ms": 180000, "duration_tolerance_ms": 5000}
        )

    def test_is_raw_file_eligible_multi_tier_quality_profile(self):
        quality_profile = {
            "formats": [
                {
                    "type": "flac",
                    "min_size_mb": 15,
                    "max_size_mb": 100,
                    "bit_depths": [16, 24],
                    "sample_rates": ["44.1", "48", "96", "192"],
                }
            ],
            "advanced_filters": {
                "fake_flac_min_bytes_per_second": 70000,
                "fake_flac_min_kbps": 500,
            }
        }

        # 1. Undersized FLAC (< 15MB)
        small_flac = {
            "filename": "Artist - Track.flac",
            "size": 10 * 1024 * 1024,
            "length": 180,
            "bitDepth": 16,
            "sampleRate": 44100,
        }
        assert not _is_raw_file_eligible(small_flac, quality_profile=quality_profile)

        # 2. Oversized FLAC (> 100MB)
        huge_flac = {
            "filename": "Artist - Track.flac",
            "size": 120 * 1024 * 1024,
            "length": 180,
            "bitDepth": 24,
            "sampleRate": 96000,
        }
        assert not _is_raw_file_eligible(huge_flac, quality_profile=quality_profile)

        # 3. Valid 24-bit 96kHz FLAC (45MB)
        valid_flac = {
            "filename": "Artist - Track.flac",
            "size": 45 * 1024 * 1024,
            "length": 180,
            "bitDepth": 24,
            "sampleRate": 96000,
        }
        assert _is_raw_file_eligible(valid_flac, quality_profile=quality_profile)

    def test_process_search_responses_zero_allocation(self):
        provider = object.__new__(SlskdProvider)
        responses_data = [
            {
                "username": "peerA",
                "freeUploadSlots": 2,
                "uploadSpeed": 200000,
                "files": [
                    {
                        "filename": "Music/W&W/Track.mp3",
                        "size": 5 * 1024 * 1024,
                        "length": 180,
                        "bitRate": 320,
                    },
                    {
                        "filename": "Music/W&W/Track (fake).flac",
                        "size": 2 * 1024 * 1024,
                        "length": 180,
                        "bitRate": 800,
                    },
                    {
                        "filename": "Music/W&W/Track [24bit 96kHz].flac",
                        "size": 50 * 1024 * 1024,
                        "length": 180,
                        "bitDepth": 24,
                        "sampleRate": 96000,
                    },
                ],
            }
        ]

        quality_profile = {
            "formats": [
                {
                    "type": "flac",
                    "min_size_mb": 20,
                    "max_size_mb": 100,
                    "bit_depths": [24],
                    "sample_rates": ["96"],
                }
            ],
            "advanced_filters": {
                "fake_flac_min_bytes_per_second": 70000,
                "fake_flac_min_kbps": 500,
            }
        }

        results = provider._process_search_responses(
            responses_data,
            quality_profile=quality_profile,
            basic_filters={"allowed_extensions": ["flac"], "target_duration_ms": 180000, "duration_tolerance_ms": 5000}
        )

        assert len(results) == 1
        assert results[0].bit_depth == 24
        assert results[0].sample_rate == 96000
        assert results[0].username == "peerA"


class TestRawScorePreservation:
    """Verify candidate evaluation uses pure raw matching engine scores without artificial strategy weighting."""

    def test_raw_score_preservation_across_strategies(self):
        from core.matching_engine.matching_engine import WeightedMatchingEngine, MatchResult
        from core.matching_engine.scoring_profile import PROFILE_DOWNLOAD_SEARCH

        # Target track and Candidate track
        target = EchosyncTrack(
            raw_title="One More Time",
            artist_name="Daft Punk",
            album_title="Discovery",
            duration=320000,
        )
        candidate = EchosyncTrack(
            raw_title="One More Time",
            artist_name="Daft Punk",
            album_title="Discovery",
            duration=320000,
        )

        engine = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)
        match_result = engine.calculate_match(target, candidate)
        raw_score = match_result.confidence_score

        # Ensure raw score is high and completely unaltered by discovery strategies
        assert raw_score >= 90.0
        # No artificial multipliers downgrade candidate scores
        for strat in ["isrc", "strict_metadata", "fuzzy_artist_title", "loose_title_duration", "title+strict-duration"]:
            candidate.identifiers["discovery_strategy"] = strat
            # Candidate score evaluated directly from matching engine remains raw
            evaluated_score = engine.calculate_match(target, candidate).confidence_score
            assert evaluated_score == raw_score
