"""
MatchService - High-level API wrapper for unified track matching

This service integrates:
1. TrackParser for raw filename parsing
2. WeightedMatchingEngine for scoring
3. Caching layer for performance
4. Rate limiter/queue integration
5. Automatic profile selection based on context

Core methods:
- find_best_match(target, candidates, context) - Find best match from list
- compare_tracks(track_a, track_b, context) - Compare two specific tracks
- parse_and_match(raw_string, candidates, context) - End-to-end pipeline
"""

import logging
from typing import List, Optional, Dict, Tuple
from enum import Enum
from dataclasses import dataclass

from .soul_sync_track import SoulSyncTrack
from .track_parser import TrackParser
from .matching_engine import WeightedMatchingEngine, MatchResult
from .scoring_profile import ProfileFactory, ProfileType, ScoringProfile
from core.caching import provider_cache, get_cache

logger = logging.getLogger(__name__)


class MatchContext(Enum):
    """Context for match requests - determines profile selection"""
    EXACT_SYNC = "exact_sync"  # Watchlists, validation - strict
    DOWNLOAD_SEARCH = "download_search"  # SoulSeek, Tidal - tolerant
    LIBRARY_IMPORT = "library_import"  # Local files - fingerprint-first


@dataclass
class MatchcandiDate:
    """Represents a match candidate with result"""
    candidate_track: SoulSyncTrack
    confidence_score: float
    match_result: MatchResult
    rank: int = 0  # Rank in results (1 = best)


class MatchService:
    """
    High-level service for track matching with caching and rate limiting
    """

    def __init__(self):
        """Initialize MatchService"""
        self.parser = TrackParser()
        self.profile_factory = ProfileFactory()
        self.cache = get_cache()

    def find_best_match(
        self,
        target: SoulSyncTrack,
        candidates: List[SoulSyncTrack],
        context: MatchContext = MatchContext.DOWNLOAD_SEARCH,
    ) -> Optional[MatchcandiDate]:
        """
        Find the best matching track from a list of candidates

        Args:
            target: Target track to match
            candidates: List of candidate tracks to compare
            context: Matching context determining scoring profile

        Returns:
            MatchCandidate with best match, or None if no matches found
        """

        if not target or not candidates:
            logger.warning("find_best_match called with empty target or candidates")
            return None

        # Check if fingerprints are available (for LIBRARY_IMPORT fallback logic)
        has_fingerprints = bool(target.fingerprint) or any(bool(c.fingerprint) for c in candidates if c)

        # Select profile based on context and fingerprint availability
        profile = self._select_profile(context, has_fingerprints)

        # Score all candidates
        scored_candidates = []

        for candidate in candidates:
            if not candidate:
                continue

            # Get match result
            matcher = WeightedMatchingEngine(profile)
            result = matcher.calculate_match(target, candidate)

            if result.confidence_score > 0:
                scored_candidates.append(
                    MatchcandiDate(
                        candidate_track=candidate,
                        confidence_score=result.confidence_score,
                        match_result=result,
                    )
                )

        if not scored_candidates:
            logger.debug(f"No candidates matched target: {target.title}")
            return None

        # Sort by confidence score (descending)
        scored_candidates.sort(key=lambda x: x.confidence_score, reverse=True)

        # Add ranks
        for idx, candidate in enumerate(scored_candidates, 1):
            candidate.rank = idx

        # Return best match
        best_match = scored_candidates[0]
        logger.debug(
            f"Best match for '{target.title}': {best_match.candidate_track.title} "
            f"({best_match.confidence_score:.1f}%)"
        )

        return best_match

    def find_top_matches(
        self,
        target: SoulSyncTrack,
        candidates: List[SoulSyncTrack],
        context: MatchContext = MatchContext.DOWNLOAD_SEARCH,
        top_n: int = 5,
        min_confidence: float = 70.0,
    ) -> List[MatchcandiDate]:
        """
        Find top N matching tracks from a list of candidates

        Args:
            target: Target track to match
            candidates: List of candidate tracks
            context: Matching context
            top_n: Return top N matches
            min_confidence: Minimum confidence threshold

        Returns:
            List of top matching candidates, sorted by confidence (best first)
        """

        if not target or not candidates:
            return []

        # Check if fingerprints available
        has_fingerprints = bool(target.fingerprint) or any(bool(c.fingerprint) for c in candidates if c)

        # Select profile
        profile = self._select_profile(context, has_fingerprints)

        # Score all candidates
        scored_candidates = []

        for candidate in candidates:
            if not candidate:
                continue

            matcher = WeightedMatchingEngine(profile)
            result = matcher.calculate_match(target, candidate)

            if result.confidence_score >= min_confidence:
                scored_candidates.append(
                    MatchcandiDate(
                        candidate_track=candidate,
                        confidence_score=result.confidence_score,
                        match_result=result,
                    )
                )

        # Sort and add ranks
        scored_candidates.sort(key=lambda x: x.confidence_score, reverse=True)
        for idx, candidate in enumerate(scored_candidates[:top_n], 1):
            candidate.rank = idx

        return scored_candidates[:top_n]

    def compare_tracks(
        self,
        track_a: SoulSyncTrack,
        track_b: SoulSyncTrack,
        context: MatchContext = MatchContext.DOWNLOAD_SEARCH,
    ) -> MatchResult:
        """
        Compare two specific tracks

        Args:
            track_a: First track
            track_b: Second track
            context: Matching context

        Returns:
            MatchResult with detailed comparison
        """

        profile = self._select_profile(context)
        matcher = WeightedMatchingEngine(profile)
        return matcher.calculate_match(track_a, track_b)

    def parse_filename(self, raw_string: str) -> Optional[SoulSyncTrack]:
        """
        Parse a raw filename into SoulSyncTrack (cached)

        Args:
            raw_string: Raw filename or track description

        Returns:
            Parsed SoulSyncTrack or None
        """
        import hashlib
        key_str = f"parse|{raw_string}"
        cache_key = hashlib.md5(key_str.encode()).hexdigest()

        cached_data = self.cache.get(cache_key)
        if cached_data:
            try:
                # Ensure we return a SoulSyncTrack object, not a dict
                if isinstance(cached_data, dict):
                    return SoulSyncTrack.from_dict(cached_data)
            except Exception as e:
                logger.warning(f"Failed to deserialize cached track: {e}")

        result = self.parser.parse_filename(raw_string)
        if result:
            self.cache.set(cache_key, result.to_dict())

        return result

    def parse_and_match(
        self,
        raw_string: str,
        candidates: List[SoulSyncTrack],
        context: MatchContext = MatchContext.DOWNLOAD_SEARCH,
    ) -> Optional[MatchcandiDate]:
        """
        Parse a raw filename and find the best match

        This is the main entry point for the full pipeline:
        raw_string → TrackParser → WeightedMatchingEngine → best match

        Args:
            raw_string: Raw filename to parse
            candidates: List of candidate tracks
            context: Matching context

        Returns:
            Best match with MatchCandidate, or None
        """

        # Parse raw string
        parsed_track = self.parse_filename(raw_string)
        if not parsed_track:
            logger.warning(f"Failed to parse: {raw_string}")
            return None

        # Find best match
        best_match = self.find_best_match(parsed_track, candidates, context)

        if best_match:
            logger.info(
                f"Parsed and matched '{raw_string}' → "
                f"{best_match.candidate_track.title} ({best_match.confidence_score:.1f}%)"
            )

        return best_match

    def get_match_stats(
        self,
        target: SoulSyncTrack,
        candidates: List[SoulSyncTrack],
        context: MatchContext = MatchContext.DOWNLOAD_SEARCH,
    ) -> Dict:
        """
        Get detailed statistics about matching results

        Args:
            target: Target track
            candidates: Candidate tracks
            context: Matching context

        Returns:
            Dictionary with match statistics
        """

        if not candidates:
            return {"total_candidates": 0, "matches_found": 0}

        matches = self.find_top_matches(target, candidates, context, top_n=len(candidates))

        if not matches:
            return {
                "total_candidates": len(candidates),
                "matches_found": 0,
                "best_score": 0,
                "average_score": 0,
            }

        scores = [m.confidence_score for m in matches]

        # Calculate median
        median = 0.0
        if scores:
            mid = len(scores) // 2
            median = scores[mid] if len(scores) % 2 != 0 else (scores[mid-1] + scores[mid]) / 2

        return {
            "total_candidates": len(candidates),
            "matches_found": len(matches),
            "best_score": scores[0],
            "worst_match_score": scores[-1],
            "average_score": sum(scores) / len(scores),
            "median_score": median,
            "matches_above_80": len([s for s in scores if s >= 80]),
            "matches_above_90": len([s for s in scores if s >= 90]),
        }

    def _select_profile(self, context: MatchContext, has_fingerprint: bool = False) -> ScoringProfile:
        """
        Select scoring profile based on context and fingerprint availability

        Args:
            context: Matching context
            has_fingerprint: Whether target/candidates have fingerprints available

        Returns:
            Appropriate ScoringProfile

        Note: For LIBRARY_IMPORT without fingerprints, falls back to EXACT_SYNC (strict) logic
        instead of DOWNLOAD_SEARCH because a wrong metadata assignment is worse than no assignment.
        """
        # For LIBRARY_IMPORT: use fingerprint profile if fingerprints available, else fallback
        if context == MatchContext.LIBRARY_IMPORT:
            if has_fingerprint:
                # Use primary profile (fingerprint-first)
                return self.profile_factory.create(ProfileType.LIBRARY_IMPORT)
            else:
                # Fall back to DOWNLOAD_SEARCH profile (Profile 2)
                return self.profile_factory.create(ProfileType.DOWNLOAD_SEARCH)

        # For other contexts, use standard mapping
        profile_type_map = {
            MatchContext.EXACT_SYNC: ProfileType.EXACT_SYNC,
            MatchContext.DOWNLOAD_SEARCH: ProfileType.DOWNLOAD_SEARCH,
        }

        profile_type = profile_type_map.get(context, ProfileType.DOWNLOAD_SEARCH)
        return self.profile_factory.create(profile_type)

    def get_cache_info(self) -> Dict:
        """Get information about cache usage"""
        return {
            "cache_enabled": True,
            "cache_implementation": "music_library.db (parsed_tracks table)",
            "cache_operations_available": ["get", "set", "delete", "clear_all", "clear_expired"],
        }


# Global MatchService instance
_match_service: Optional[MatchService] = None


def get_match_service() -> MatchService:
    """Get or create global MatchService instance"""
    global _match_service
    if _match_service is None:
        _match_service = MatchService()
    return _match_service


def find_best_match(
    target: SoulSyncTrack,
    candidates: List[SoulSyncTrack],
    context: MatchContext = MatchContext.DOWNLOAD_SEARCH,
) -> Optional[MatchcandiDate]:
    """Convenience function using global MatchService"""
    service = get_match_service()
    return service.find_best_match(target, candidates, context)


def parse_and_match(
    raw_string: str,
    candidates: List[SoulSyncTrack],
    context: MatchContext = MatchContext.DOWNLOAD_SEARCH,
) -> Optional[MatchcandiDate]:
    """Convenience function using global MatchService"""
    service = get_match_service()
    return service.parse_and_match(raw_string, candidates, context)
