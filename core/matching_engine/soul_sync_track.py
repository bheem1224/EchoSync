"""
SoulSyncTrack: The core data structure for music track representation in SoulSync.

This model unifies all metadata about a track across different providers, quality levels,
and matching contexts. It serves as the bridge between raw filenames, parsed candidates,
and matched results.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class QualityTag(str, Enum):
    """Supported audio quality indicators"""
    FLAC_24BIT = "FLAC 24bit"
    FLAC_16BIT = "FLAC 16bit"
    MP3_320 = "MP3 320kbps"
    MP3_256 = "MP3 256kbps"
    MP3_192 = "MP3 192kbps"
    MP3_128 = "MP3 128kbps"
    AAC = "AAC"
    OGG = "OGG Vorbis"
    WMA = "WMA"
    ALAC = "ALAC"
    OPUS = "Opus"
    UNKNOWN = "Unknown"


@dataclass
class SoulSyncTrack:
    """
    Unified track representation for matching, parsing, and organization.
    
    REQUIRED FIELDS (for provider contribution):
    - title: Track title (REQUIRED)
    - artist: Primary artist (REQUIRED)
    - source: Where this track came from (REQUIRED for traceability)
    - album: Album name (STRONGLY RECOMMENDED)
    
    OPTIONAL FIELDS (providers should populate as much as possible):
    All other fields are optional. If a provider cannot provide a field,
    it defaults to None and the system continues functioning normally.
    
    CRITICAL FIELDS FOR ENHANCED MATCHING:
    - version: Remix, Live, Acoustic, etc. (SEPARATED from title)
    - duration_ms: Used for tie-breaking and validation
    - isrc: International Standard Recording Code (instant match if both have)
    - musicbrainz_id: For high-accuracy matching
    - is_compilation: Flag that disables album artist penalties
    - track_total: For edition/release detection (original vs remaster)
    - disc_number, total_discs: For multi-disc album handling
    
    QUALITY/FILE FIELDS:
    - quality_tags: List of detected quality indicators (FLAC, 320kbps, etc.)
    - file_format: Container format (mp3, flac, m4a, etc.)
    - file_path: Provider-specific path to the file (e.g., /music/track.mp3)
    - bitrate: Bitrate in kbps (for MP3)
    - sample_rate: Sample rate in Hz (e.g., 44100, 48000)
    - bit_depth: Bit depth (e.g., 16, 24)
    
    EXTERNAL IDENTIFIERS:
    - external_ids: Dict mapping provider names to provider-specific IDs
      Example: { 'spotify': 'spotify:track:...', 'mbid': '...', 'acousticid': '...' }
    
    PLUGIN/ENRICHMENT DATA:
    - extra_metadata: Dict for plugin data (BPM, mood, lyrics, etc.)
    """
    
    # REQUIRED FIELDS
    title: str
    artist: str  # Primary artist (featured artists in separate field)
    
    # STRONGLY RECOMMENDED
    album: Optional[str] = None
    year: Optional[int] = None
    duration_ms: Optional[int] = None  # Track duration in milliseconds
    
    # Version info (CRITICAL: separated from title)
    version: Optional[str] = None  # e.g., "Remix", "Live", "Acoustic", "Radio Edit"
    
    # Album/Release info
    is_compilation: bool = False  # "Various Artists" or compilation compilation flag
    disc_number: Optional[int] = None  # Disc number in multi-disc album
    total_discs: Optional[int] = None  # Total discs in album
    track_number: Optional[int] = None  # Track position within disc
    track_total: Optional[int] = None  # CRITICAL: Total tracks in album/release (for edition detection)
    
    # Featured/collaboration info
    featured_artists: List[str] = field(default_factory=list)
    
    # Quality indicators
    quality_tags: List[str] = field(default_factory=list)  # e.g., ["FLAC", "24bit", "44.1kHz"]
    file_format: Optional[str] = None  # e.g., "mp3", "flac", "m4a", "ogg"
    file_path: Optional[str] = None  # e.g., "/music/track.mp3" (provider-specific path)
    bitrate: Optional[int] = None  # Bitrate in kbps (for MP3)
    sample_rate: Optional[int] = None  # Sample rate in Hz (44100, 48000, etc.)
    bit_depth: Optional[int] = None  # Bit depth (16, 24, etc.)
    file_size: Optional[int] = None  # File size in bytes
    
    # External identifiers (for linking across providers)
    external_ids: Dict[str, str] = field(default_factory=dict)
    # Example: { 'spotify': 'spotify:track:...', 'mbid': '...', 'acousticid': '...' }
    
    # Audio fingerprint (Chromaprint for high-accuracy matching)
    fingerprint: Optional[str] = None  # Chromaprint fingerprint string
    fingerprint_confidence: Optional[float] = None  # Confidence of fingerprint generation (0-1)
    
    # Plugin/enrichment data
    extra_metadata: Dict[str, Any] = field(default_factory=dict)
    # Example: { 'bpm': 120, 'mood': 'energetic', 'lyrics': '...', 'genres': ['pop', 'dance'] }
    
    # Metadata about the track object itself
    source: Optional[str] = None  # Where this track came from (e.g., "spotify", "plex", "slskd", "filename")
    parsed_at: Optional[datetime] = None  # When this track was parsed/created
    confidence: Optional[float] = None  # Confidence score (0.0-1.0) from matching engine
    
    # Direct ISRC field for instant matching (International Standard Recording Code)
    isrc: Optional[str] = None  # e.g., "USRC12345678"
    musicbrainz_id: Optional[str] = None  # MusicBrainz Recording ID
    musicbrainz_album_id: Optional[str] = None  # MusicBrainz Album ID
    musicbrainz_artist_id: Optional[str] = None  # MusicBrainz Artist ID
    
    def validate(self) -> bool:
        """Validate that track has minimum required fields"""
        return bool(self.title and self.artist)
    
    def get_quality_score(self) -> float:
        """
        Calculate a simple quality score based on quality tags.
        Used for tie-breaking in matching.
        
        Returns: float 0.0-1.0
        """
        quality_weights = {
            "FLAC 24bit": 1.0,
            "FLAC 16bit": 0.95,
            "FLAC": 0.95,
            "24bit": 0.05,  # Bonus, not standalone
            "MP3 320kbps": 0.7,
            "320kbps": 0.7,
            "MP3 256kbps": 0.6,
            "256kbps": 0.6,
            "MP3 192kbps": 0.5,
            "192kbps": 0.5,
            "MP3 128kbps": 0.3,
            "128kbps": 0.3,
            "AAC": 0.6,
            "OGG Vorbis": 0.65,
            "ALAC": 0.9,
            "Opus": 0.75,
        }
        
        if not self.quality_tags:
            return 0.5  # Unknown quality defaults to middle
        
        # Find highest quality score from tags
        score = 0.0
        for tag in self.quality_tags:
            score = max(score, quality_weights.get(tag, 0.3))
        
        return min(1.0, score)
    
    def is_version_match(self, other: "SoulSyncTrack") -> bool:
        """
        Check if two tracks have matching version info.
        
        CRITICAL for matching: Original vs Remix must be distinguished.
        """
        # Both original (no version tag)
        if not self.version and not other.version:
            return True
        
        # Version mismatch (one is original, one is remixed)
        if bool(self.version) != bool(other.version):
            return False
        
        # Both have versions - do they match?
        if self.version and other.version:
            return self.version.lower() == other.version.lower()
        
        return True
    
    def is_edition_match(self, other: "SoulSyncTrack", tolerance: float = 0.1) -> bool:
        """
        Check if two tracks are from the same release/edition.
        
        CRITICAL for matching: Detects if candidate is from a remaster/bonus edition.
        
        Args:
            other: Track to compare against
            tolerance: Allow track count difference up to this percentage (default 10%)
        
        Returns: True if editions match (or close enough), False if clearly different editions
        """
        if not self.track_total or not other.track_total:
            return True  # Can't determine, assume match
        
        # Calculate percentage difference
        diff = abs(self.track_total - other.track_total)
        max_total = max(self.track_total, other.track_total)
        pct_diff = diff / max_total if max_total > 0 else 0.0
        
        return pct_diff <= tolerance
    
    def __repr__(self) -> str:
        """Human-readable representation"""
        version_str = f" [{self.version}]" if self.version else ""
        quality_str = f" ({', '.join(self.quality_tags)})" if self.quality_tags else ""
        return f"SoulSyncTrack({self.artist} - {self.title}{version_str}{quality_str})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'year': self.year,
            'duration_ms': self.duration_ms,
            'version': self.version,
            'is_compilation': self.is_compilation,
            'disc_number': self.disc_number,
            'total_discs': self.total_discs,
            'track_number': self.track_number,
            'track_total': self.track_total,
            'featured_artists': self.featured_artists,
            'quality_tags': self.quality_tags,
            'file_format': self.file_format,
            'bitrate': self.bitrate,
            'sample_rate': self.sample_rate,
            'bit_depth': self.bit_depth,
            'file_size': self.file_size,
            'external_ids': self.external_ids,
            'extra_metadata': self.extra_metadata,
            'source': self.source,
            'confidence': self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoulSyncTrack":
        """Create from dictionary (for deserialization)"""
        return cls(**data)
