"""
Core matching system module

Main components:
- SoulSyncTrack: Central data model for track metadata
- TrackParser: Converts raw filenames to SoulSyncTrack objects
- WeightedMatchingEngine: 5-step gating scoring algorithm
- ScoringProfile: Strategy pattern for different match contexts
- @provider_cache: Decorator for caching provider queries
"""

from .matching_engine import (
    SoulSyncTrack,
    QualityTag,
    TrackParser,
    ParseConfig,
    WeightedMatchingEngine,
    MatchResult,
    ScoringProfile,
    ScoringWeights,
    ProfileType,
    ProfileFactory,
    PROFILE_EXACT_SYNC,
    PROFILE_DOWNLOAD_SEARCH,
    PROFILE_LIBRARY_IMPORT,
)
from .caching import (
    provider_cache,
    ProviderCache,
    get_cache,
    clear_cache,
    cleanup_expired_cache,
)
from .post_processor import (
    PostProcessor,
    AudioFormat,
    TagWriteResult,
    FileOrganizeResult,
    get_post_processor,
)
from .auto_importer import (
    AutoImporter,
    get_auto_importer,
    start_auto_import,
    stop_auto_import,
)
from .matching_engine import (
    FingerprintMatcher,
)

__all__ = [
    # Data models
    'SoulSyncTrack',
    'QualityTag',
    # Parsing
    'TrackParser',
    'ParseConfig',
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
    # Caching
    'provider_cache',
    'ProviderCache',
    'get_cache',
    'clear_cache',
    'cleanup_expired_cache',
    # Post-processing
    'PostProcessor',
    'AudioFormat',
    'TagWriteResult',
    'FileOrganizeResult',
    'get_post_processor',
    # Auto-import service
    'AutoImporter',
    'get_auto_importer',
    'start_auto_import',
    'stop_auto_import',
    # Fingerprinting
    'FingerprintMatcher',
]
