"""
Scoring Profile Strategy Classes - Define scoring weights and penalties for different contexts

This module contains ScoringProfile classes that define how tracks are matched in different scenarios:
- EXACT_SYNC: Strict matching for exact track identification (high text match requirement)
- DOWNLOAD_SEARCH: Tolerant matching for finding downloads (accepts approximate matches)
- LIBRARY_IMPORT: Maximum weight on fingerprint/duration for library organization

Profiles can be customized by modifying the matching_profiles section in config.json
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ProfileType(Enum):
    """Available scoring profiles"""
    EXACT_SYNC = "exact_sync"
    DOWNLOAD_SEARCH = "download_search"
    LIBRARY_IMPORT = "library_import"


@dataclass
class ScoringWeights:
    """Container for all scoring weights and penalties"""

    # Text matching weights (0.0 - 1.0 scale, higher = more important)
    text_weight: float = 0.4  # How important is text match?

    # Duration matching weight
    duration_weight: float = 0.2  # How important is duration match?

    # Fingerprint/global ID weight (ISRC, MusicBrainz, AcousticID, etc.)
    fingerprint_weight: float = 0.3  # How important are global IDs?

    # Quality bonus (applied when quality is significantly better)
    quality_bonus: float = 0.05  # Bonus points for better quality

    # Penalties (subtracted from score)
    version_mismatch_penalty: float = 15.0  # Penalty if versions don't match (0-100 scale)
    edition_mismatch_penalty: float = 10.0  # Penalty if editions don't match (track_total, album type differ)
    duration_tolerance_ms: int = 3000  # Allow 3 second difference in duration
    fuzzy_match_threshold: float = 0.85  # Fuzzy match must be >= this to pass gating

    # Minimum confidence thresholds
    min_confidence_to_accept: float = 70.0  # Minimum score to consider a match valid
    text_match_fallback: float = 0.80  # Fallback text fuzzy match if no fingerprints available

    # Weights validation
    def validate(self) -> bool:
        """Validate that weights sum properly"""
        # Note: weights don't need to sum to 1.0 since we normalize in the matching engine
        return all([
            0.0 <= self.text_weight <= 1.0,
            0.0 <= self.duration_weight <= 1.0,
            0.0 <= self.fingerprint_weight <= 1.0,
            0.0 <= self.quality_bonus <= 1.0,
            self.version_mismatch_penalty >= 0,
            self.edition_mismatch_penalty >= 0,
        ])

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'text_weight': self.text_weight,
            'duration_weight': self.duration_weight,
            'fingerprint_weight': self.fingerprint_weight,
            'quality_bonus': self.quality_bonus,
            'version_mismatch_penalty': self.version_mismatch_penalty,
            'edition_mismatch_penalty': self.edition_mismatch_penalty,
            'duration_tolerance_ms': self.duration_tolerance_ms,
            'fuzzy_match_threshold': self.fuzzy_match_threshold,
            'min_confidence_to_accept': self.min_confidence_to_accept,
            'text_match_fallback': self.text_match_fallback,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ScoringWeights':
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ScoringProfile(ABC):
    """Abstract base class for scoring profiles"""

    profile_type: ProfileType
    description: str
    weights: ScoringWeights

    @abstractmethod
    def get_weights(self) -> ScoringWeights:
        """Get the weights for this profile"""
        pass

    @abstractmethod
    def describe(self) -> str:
        """Get a human-readable description of this profile"""
        pass

    def validate_weights(self) -> bool:
        """Validate that weights are properly configured"""
        return self.weights.validate()


class ExactSyncProfile(ScoringProfile):
    """
    EXACT_SYNC Profile - For matching structured API responses (Spotify → Tidal/Plex)

    Use when: Matching tracks between streaming services or against local metadata
    Priority: Title (35%) + Artist (35%) > Duration (20%) > Album (10%)
    Philosophy: High precision, avoid false positives, structured metadata comparison

    Characteristics:
    - Title: 35% (must be very close)
    - Artist: 35% (must be exact)
    - Duration: 20% (allow ~3s variance for different masters)
    - Album: 10% (low - compilations often have same track)
    - NO fingerprint weight (metadata-only matching)
    - ISRC match = instant 100% (if available)
    - Minimum confidence threshold: 85%
    """

    profile_type = ProfileType.EXACT_SYNC

    def __init__(self):
        self.description = "Exact track identification for structured metadata (Spotify/Tidal/Plex)"
        self.weights = ScoringWeights(
            text_weight=0.70,  # Combined title (35%) + artist (35%) = 70%
            duration_weight=0.20,  # 20% - allow ~3s variance
            fingerprint_weight=0.0,  # NO fingerprint for metadata matching
            quality_bonus=0.05,  # 5% bonus for quality
            version_mismatch_penalty=50.0,  # -50 for version mismatch (Remix vs Original)
            edition_mismatch_penalty=15.0,  # -15 for edition mismatch
            duration_tolerance_ms=3000,  # Allow 3 second difference
            fuzzy_match_threshold=0.90,  # High fuzzy threshold for text
            min_confidence_to_accept=85.0,  # High confidence required
            text_match_fallback=0.92,
        )

    def get_weights(self) -> ScoringWeights:
        return self.weights

    def describe(self) -> str:
        return (
            "EXACT_SYNC - High precision metadata matching for structured API responses. "
            "Title (35%) + Artist (35%) + Duration (20%) + Album (10%). "
            "ISRC match = instant 100%. No fingerprinting. "
            f"Min confidence: {self.weights.min_confidence_to_accept}%"
        )


class DownloadSearchProfile(ScoringProfile):
    """
    DOWNLOAD_SEARCH Profile - For matching against messy P2P filenames (Slskd)

    Use when: Searching for downloads on P2P networks with ugly filenames
    Priority: Title (40%) > Artist (30%) > Duration (20%) > Album (10%)
    Philosophy: Flexible text matching, duration as BS detector, quality bonus for exact format match

    Characteristics:
    - Title: 40% (filename usually contains title but with junk)
    - Artist: 30% (critical, but feat. artists may be at end)
    - Duration: 20% (BS detector - if >5s off, likely fake/wrong mix)
    - Album: 10% (low - filenames often omit album)
    - Quality bonus: 5-10% (FLAC search + FLAC file = bonus)
    - Version penalty: -50 (Original vs Remix = kill score)
    - Duration tolerance: 5s
    - Minimum confidence: 70%
    """

    profile_type = ProfileType.DOWNLOAD_SEARCH

    def __init__(self):
        self.description = "Tolerant matching for P2P downloads with messy filenames"
        self.weights = ScoringWeights(
            text_weight=0.70,  # Combined title (40%) + artist (30%) = 70%
            duration_weight=0.20,  # 20% - BS detector (>5s = likely wrong)
            fingerprint_weight=0.0,  # No fingerprint for search
            quality_bonus=0.10,  # 5-10% bonus if format matches request
            version_mismatch_penalty=50.0,  # -50 for version mismatch (kill score)
            edition_mismatch_penalty=10.0,  # -10 for edition issues
            duration_tolerance_ms=5000,  # Allow 5 second difference (BS threshold)
            fuzzy_match_threshold=0.80,  # More lenient for messy filenames
            min_confidence_to_accept=70.0,  # Accept decent matches
            text_match_fallback=0.75,
        )

    def get_weights(self) -> ScoringWeights:
        return self.weights

    def describe(self) -> str:
        return (
            "DOWNLOAD_SEARCH - Flexible matching for P2P networks with messy filenames. "
            "Title (40%) + Artist (30%) + Duration (20%) + Album (10%). "
            "Quality bonus: +5-10%. Version penalty: -50. "
            f"Min confidence: {self.weights.min_confidence_to_accept}%"
        )


class LibraryImportProfile(ScoringProfile):
    """
    LIBRARY_IMPORT Profile - For identifying local files via fingerprinting (Picard style)

    Use when: Scanning local files that might have no tags but have audio data
    Priority: Fingerprint (60%) > Duration (30%) > Meta Tags (10%)
    Philosophy: Identification via audio fingerprinting, don't trust existing tags

    Characteristics:
    - Fingerprint: 60% (chromaprint match = mostly done)
    - Duration: 30% (confirms fingerprint isn't false positive)
    - Meta Tags: 10% (existing tags trusted least - user might have bad tags)
    - Track count penalty: -20 (wrong release if track totals don't match)
    - Very high fingerprint weight
    - Minimum confidence: 65%
    """

    profile_type = ProfileType.LIBRARY_IMPORT

    def __init__(self):
        self.description = "Fingerprint-first identification for local files (Picard style)"
        self.weights = ScoringWeights(
            text_weight=0.10,  # 10% - existing tags trusted least
            duration_weight=0.30,  # 30% - confirms fingerprint
            fingerprint_weight=0.60,  # 60% - chromaprint is primary
            quality_bonus=0.02,  # Minimal quality bonus
            version_mismatch_penalty=5.0,  # Very lenient - just organizing
            edition_mismatch_penalty=3.0,  # Very lenient
            duration_tolerance_ms=8000,  # Very generous (8 sec for codec differences)
            fuzzy_match_threshold=0.75,  # Lenient threshold
            min_confidence_to_accept=65.0,  # Accept lower-confidence matches
            text_match_fallback=0.80,
        )

    def get_weights(self) -> ScoringWeights:
        return self.weights

    def describe(self) -> str:
        return (
            "LIBRARY_IMPORT - Fingerprint-first matching for local file identification. "
            "Fingerprint (60%) + Duration (30%) + Meta Tags (10%). "
            "Track count penalty: -20 for wrong release. "
            "Suitable for organizing existing library and associating with metadata. "
            f"Min confidence: {self.weights.min_confidence_to_accept}%"
        )


class ConfigurableProfile(ScoringProfile):
    """Custom profile loaded from config.json"""

    def __init__(self, name: str, weights: ScoringWeights, description: str = ""):
        self.profile_type = ProfileType.LIBRARY_IMPORT  # Default
        self.name = name
        self.description = description
        self.weights = weights

    def get_weights(self) -> ScoringWeights:
        return self.weights

    def describe(self) -> str:
        return self.description or f"Custom profile: {self.name}"

    @classmethod
    def from_config(cls, name: str, config_data: Dict) -> 'ConfigurableProfile':
        """Create profile from config dictionary"""
        # Extract weights
        weights_dict = {k: v for k, v in config_data.items() 
                       if k in ScoringWeights.__dataclass_fields__}
        weights = ScoringWeights.from_dict(weights_dict)

        description = config_data.get("description", "")
        
        profile = cls(name, weights, description)
        return profile


class ProfileFactory:
    """Factory for creating scoring profiles"""

    _profiles = {
        ProfileType.EXACT_SYNC: ExactSyncProfile,
        ProfileType.DOWNLOAD_SEARCH: DownloadSearchProfile,
        ProfileType.LIBRARY_IMPORT: LibraryImportProfile,
    }
    
    _config_profiles: Optional[Dict] = None  # Cached config profiles

    @classmethod
    def _load_config_profiles(cls) -> Dict:
        """Load matching profiles from config.json"""
        if cls._config_profiles is not None:
            return cls._config_profiles or {}

        try:
            # Try to find config.json
            config_paths = [
                Path("config/config.json"),
                Path("./config.json"),
            ]
            
            for config_path in config_paths:
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        cls._config_profiles = config.get("matching_profiles", {})
                        return cls._config_profiles or {}
            
            logger.debug("config.json not found, using built-in profiles")
            cls._config_profiles = {}
            return cls._config_profiles
        except Exception as e:
            logger.warning(f"Failed to load config profiles: {e}")
            cls._config_profiles = {}
            return cls._config_profiles

    @classmethod
    def create(cls, profile_type: ProfileType) -> ScoringProfile:
        """Create a scoring profile by type"""
        if profile_type not in cls._profiles:
            raise ValueError(f"Unknown profile type: {profile_type}")
        
        # Try to load from config first
        config_profiles = cls._load_config_profiles()
        profile_name = profile_type.value.upper()
        
        if profile_name in config_profiles:
            config_data = config_profiles[profile_name]
            return ConfigurableProfile.from_config(profile_name, config_data)
        
        # Fall back to built-in profile
        return cls._profiles[profile_type]()

    @classmethod
    def create_from_name(cls, name: str) -> ScoringProfile:
        """Create a profile from string name"""
        try:
            profile_type = ProfileType(name.lower())
            return cls.create(profile_type)
        except ValueError:
            raise ValueError(f"Unknown profile name: {name}")

    @classmethod
    def list_profiles(cls) -> list[str]:
        """List all available profile names"""
        return [pt.value for pt in ProfileType]

    @classmethod
    def get_default_profile(cls) -> ScoringProfile:
        """Get the default profile (DOWNLOAD_SEARCH)"""
        return cls.create(ProfileType.DOWNLOAD_SEARCH)


# Pre-instantiated profiles for convenience
PROFILE_EXACT_SYNC = ExactSyncProfile()
PROFILE_DOWNLOAD_SEARCH = DownloadSearchProfile()
PROFILE_LIBRARY_IMPORT = LibraryImportProfile()
