"""
Core matching system module

Main components:
- EchosyncTrack: Central data model for track metadata
- TrackParser: Converts raw filenames to EchosyncTrack objects
- WeightedMatchingEngine: 5-step gating scoring algorithm
- ScoringProfile: Strategy pattern for different match contexts
- @plugin_cache: Decorator for caching plugin queries
"""


# ── Late Imports to break circular dependencies ──
# We move these to the bottom so that core.settings (and others) can import 
# from the core package without triggering a full load of the matching engine 
# before config_manager is instantiated.

from .db.echo_sync_track import (
    EchosyncTrack,
    EchosyncMedia,
    QualityTag,
)
from .matching_engine import (
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
    plugin_cache,
    PluginCache,
    get_cache,
    clear_cache,
    cleanup_expired_cache,
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
    'EchosyncTrack',
    'EchosyncMedia',
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
    'plugin_cache',
    'PluginCache',
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
