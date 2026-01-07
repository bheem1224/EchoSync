"""
Core matching engine module

Main components:
- SoulSyncTrack: Central data model for track metadata
- QualityTag: Audio quality indicators
- TrackParser: Converts raw filenames to SoulSyncTrack objects
- WeightedMatchingEngine: 5-step gating scoring algorithm
- ScoringProfile: Strategy pattern for different match contexts
- MatchService: High-level API integrating all components
- FingerprintMatcher: Audio fingerprinting for acoustic matching
"""

from .soul_sync_track import SoulSyncTrack, QualityTag
from .track_parser import TrackParser, ParseConfig, parse_file
from .matching_engine import WeightedMatchingEngine, MatchResult
from .scoring_profile import (
    ScoringProfile,
    ScoringWeights,
    ProfileType,
    ProfileFactory,
    PROFILE_EXACT_SYNC,
    PROFILE_DOWNLOAD_SEARCH,
    PROFILE_LIBRARY_IMPORT,
)
from .match_service import (
    MatchService,
    MatchContext,
    get_match_service,
    find_best_match,
    parse_and_match,
)
from .fingerprinting import FingerprintMatcher

__all__ = [
    # Data models
    'SoulSyncTrack',
    'QualityTag',
    
    # Parsing
    'TrackParser',
    'ParseConfig',
    'parse_file',
    
    # Matching engine
    'WeightedMatchingEngine',
    'MatchResult',
    
    # Scoring profiles
    'ScoringProfile',
    'ScoringWeights',
    'ProfileType',
    'ProfileFactory',
    'PROFILE_EXACT_SYNC',
    'PROFILE_DOWNLOAD_SEARCH',
    'PROFILE_LIBRARY_IMPORT',
    
    # Match service
    'MatchService',
    'MatchContext',
    'get_match_service',
    'find_best_match',
    'parse_and_match',
    
    # Fingerprinting
    'FingerprintMatcher',
]
