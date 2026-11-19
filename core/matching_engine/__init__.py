"""
Core matching engine module

Main components:
- EchosyncTrack: Central data model for track metadata
- QualityTag: Audio quality indicators
- TrackParser: Converts raw filenames to EchosyncTrack objects
- WeightedMatchingEngine: 5-step gating scoring algorithm
- ScoringProfile: Strategy pattern for different match contexts
- FingerprintMatcher: Audio fingerprinting for acoustic matching
"""

from ..db.echo_sync_track import EchosyncTrack, QualityTag
from .fingerprinting import FingerprintMatcher
from .matching_engine import MatchingEngine, MatchResult, WeightedMatchingEngine
from .scoring_profile import (
    PROFILE_DOWNLOAD_SEARCH,
    PROFILE_EXACT_SYNC,
    PROFILE_LIBRARY_IMPORT,
    ProfileFactory,
    ProfileType,
    ScoringProfile,
    ScoringWeights,
)
from .track_parser import ParseConfig, TrackParser, parse_file

__all__ = [
    # Data models
    "EchosyncTrack",
    "QualityTag",
    # Parsing
    "TrackParser",
    "ParseConfig",
    "parse_file",
    # Matching engine
    "WeightedMatchingEngine",
    "MatchingEngine",
    "MatchResult",
    # Scoring profiles
    "ScoringProfile",
    "ScoringWeights",
    "ProfileType",
    "ProfileFactory",
    "PROFILE_EXACT_SYNC",
    "PROFILE_DOWNLOAD_SEARCH",
    "PROFILE_LIBRARY_IMPORT",
    # Fingerprinting
    "FingerprintMatcher",
    # Trust Gate
    "sanitize_title_from_filename",
    "verify_title_trust_gate",
]

from .trust_gate import sanitize_title_from_filename, verify_title_trust_gate
