"""
Canonical data models for SoulSync.

The Track model is the single source of truth used by ALL providers.
Providers never own data - they only create stubs, enrich fields, or attach references.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import base64
import uuid
from datetime import datetime
import re

from time_utils import parse_utc_datetime, utc_isoformat, utc_now


class DownloadStatus(Enum):
    """Track download lifecycle states"""
    MISSING = "missing"           # Not yet downloaded
    QUEUED = "queued"             # In download queue
    DOWNLOADING = "downloading"   # Active download
    COMPLETE = "complete"         # Downloaded but not verified
    VERIFIED = "verified"         # Downloaded and verified
    FAILED = "failed"             # Download failed


class ProviderType(Enum):
    """Provider types for track references"""
    SPOTIFY = "spotify"
    TIDAL = "tidal"
    YOUTUBE = "youtube"
    PLEX = "plex"
    JELLYFIN = "jellyfin"
    NAVIDROME = "navidrome"
    SOULSEEK = "soulseek"
    MUSICBRAINZ = "musicbrainz"
    ACOUSTID = "acoustid"


@dataclass
class ProviderRef:
    """Reference to a track in a specific provider"""
    provider: ProviderType
    provider_id: str                    # Provider's native ID
    provider_url: Optional[str] = None  # Direct URL if available
    metadata: Dict[str, Any] = field(default_factory=dict)  # Provider-specific extras
    last_updated: datetime = field(default_factory=utc_now)

    def validate(self) -> None:
        """Validate the provider reference fields."""
        if not self.provider_id:
            raise ValueError("Provider ID cannot be empty.")
        if self.provider_url and not re.match(r'^https?://', self.provider_url):
            raise ValueError("Provider URL must start with http:// or https://.")


@dataclass
class SoulSyncTrack:
    """
    Canonical Track model - single source of truth for all providers.
    
    Design principles:
    - All fields except track_id are optional (progressive enrichment)
    - Providers attach references via provider_refs
    - confidence_score tracks data quality (0.0 = stub, 1.0 = fully verified)
    - No provider owns this data - all work through music_database
    """
    
    # === Core Identity ===
    track_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # === Basic Metadata (progressively enriched) ===
    title: Optional[str] = None
    artists: List[str] = field(default_factory=list)  # Ordered list
    album: Optional[str] = None
    duration_ms: Optional[int] = None
    
    # === Global Identifiers (for matching) ===
    isrc: Optional[str] = None                          # International Standard Recording Code
    musicbrainz_recording_id: Optional[str] = None      # MusicBrainz recording MBID
    acoustid: Optional[str] = None                      # AcoustID fingerprint
    
    # === Provider References ===
    provider_refs: Dict[str, ProviderRef] = field(default_factory=dict)  # Key: provider name
    
    # === Download Management ===
    download_status: DownloadStatus = DownloadStatus.MISSING
    file_path: Optional[str] = None                     # Local file path if downloaded
    file_format: Optional[str] = None                   # e.g., "flac", "mp3"
    bitrate: Optional[int] = None                       # Bits per second
    
    # === Quality & Confidence ===
    confidence_score: float = 0.0                       # 0.0 (stub) to 1.0 (verified)
    
    # === Extended Metadata (optional enrichment) ===
    album_artist: Optional[str] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    release_year: Optional[int] = None
    genres: List[str] = field(default_factory=list)
    total_discs: Optional[int] = None
    track_total: Optional[int] = None
    version: Optional[str] = None
    is_compilation: Optional[bool] = None
    quality_tags: Optional[List[str]] = None
    sample_rate: Optional[int] = None
    bit_depth: Optional[int] = None
    file_size: Optional[int] = None
    featured_artists: Optional[List[str]] = None
    fingerprint: Optional[str] = None
    fingerprint_confidence: Optional[float] = None
    
    # === System Fields ===
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def sync_id(self) -> str:
        """
        Return the stable URN used by working database tables.
        
        Format: ss:track:meta:{base64(lowercase_artist|lowercase_title)}?dur={duration_ms}&mbid={mbid}
        
        The base identity is always the metadata hash. Query parameters are optional and only included
        if the corresponding fields have values. Database queries MUST strip everything after '?' before lookup.
        """
        from urllib.parse import urlencode
        
        # Core identity: always use base64 metadata hash
        primary_artist = (self.artists[0] if self.artists else "").strip().lower()
        track_title = (self.title or "").strip().lower()
        payload = f"{primary_artist}|{track_title}"
        encoded_payload = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        base_id = f"ss:track:meta:{encoded_payload}"
        
        # Build query parameters from available external attributes
        params = {}
        if self.duration_ms is not None:
            params["dur"] = self.duration_ms
        if self.musicbrainz_recording_id is not None:
            params["mbid"] = self.musicbrainz_recording_id
        
        # Only append query string if params exist
        if params:
            query_string = urlencode(params)
            return f"{base_id}?{query_string}"
        
        return base_id
    
    def add_provider_ref(self, provider: ProviderType, provider_id: str, 
                        provider_url: Optional[str] = None, 
                        metadata: Optional[Dict[str, Any]] = None) -> None:
        """Attach a provider reference to this track"""
        self.provider_refs[provider.value] = ProviderRef(
            provider=provider,
            provider_id=provider_id,
            provider_url=provider_url,
            metadata=metadata or {}
        )
        self.updated_at = utc_now()
    
    def get_provider_ref(self, provider: ProviderType) -> Optional[ProviderRef]:
        """Get reference for a specific provider"""
        return self.provider_refs.get(provider.value)
    
    def has_provider_ref(self, provider: ProviderType) -> bool:
        """Check if track has reference for a provider"""
        return provider.value in self.provider_refs
    
    def enrich(self, **kwargs) -> None:
        """
        Progressively enrich track fields.
        Only updates non-None values, never overwrites existing data.
        Updates confidence_score based on completeness.
        """
        for key, value in kwargs.items():
            if value is not None and hasattr(self, key):
                current = getattr(self, key)
                # Only update if current is None or empty list
                if current is None or (isinstance(current, list) and len(current) == 0):
                    setattr(self, key, value)

        self.updated_at = utc_now()
        self._calculate_confidence()
    
    def _calculate_confidence(self) -> None:
        """Calculate confidence score based on field completeness."""
        score = 0.0
        total_weight = 0.0

        # Core fields (higher weight)
        field_weights = {
            'title': 0.25,
            'artists': 0.20,
            'album': 0.15,
            'duration_ms': 0.10,
            'isrc': 0.10,
            'musicbrainz_recording_id': 0.08,
            'file_path': 0.12 if self.download_status == DownloadStatus.VERIFIED else 0.0
        }

        for field, weight in field_weights.items():
            if getattr(self, field):
                score += weight
            total_weight += weight

        self.confidence_score = min(score / total_weight if total_weight > 0 else 0.0, 1.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'track_id': self.track_id,
            'title': self.title,
            'artists': self.artists,
            'album': self.album,
            'duration_ms': self.duration_ms,
            'isrc': self.isrc,
            'musicbrainz_recording_id': self.musicbrainz_recording_id,
            'acoustid': self.acoustid,
            'provider_refs': {k: {
                'provider': v.provider.value,
                'provider_id': v.provider_id,
                'provider_url': v.provider_url,
                'metadata': v.metadata,
                'last_updated': utc_isoformat(v.last_updated)
            } for k, v in self.provider_refs.items()},
            'download_status': self.download_status.value,
            'file_path': self.file_path,
            'file_format': self.file_format,
            'bitrate': self.bitrate,
            'confidence_score': round(self.confidence_score, 2),  # Round for consistency
            'album_artist': self.album_artist,
            'track_number': self.track_number,
            'disc_number': self.disc_number,
            'release_year': self.release_year,
            'genres': self.genres,
            'total_discs': self.total_discs,
            'track_total': self.track_total,
            'version': self.version,
            'is_compilation': self.is_compilation,
            'quality_tags': self.quality_tags,
            'sample_rate': self.sample_rate,
            'bit_depth': self.bit_depth,
            'file_size': self.file_size,
            'featured_artists': self.featured_artists,
            'fingerprint': self.fingerprint,
            'fingerprint_confidence': self.fingerprint_confidence,
            'created_at': utc_isoformat(self.created_at),
            'updated_at': utc_isoformat(self.updated_at)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SoulSyncTrack':
        """Create Track from dictionary (database retrieval)."""
        # Parse provider_refs
        provider_refs = {}
        for key, ref_data in data.get('provider_refs', {}).items():
            provider_refs[key] = ProviderRef(
                provider=ProviderType(ref_data['provider']),
                provider_id=ref_data['provider_id'],
                provider_url=ref_data.get('provider_url'),
                metadata=ref_data.get('metadata', {}),
                last_updated=parse_utc_datetime(ref_data.get('last_updated')) or utc_now()
            )
        
        track = cls(
            track_id=data.get('track_id', str(uuid.uuid4())),
            title=data.get('title'),
            artists=data.get('artists', []),
            album=data.get('album'),
            duration_ms=data.get('duration_ms'),
            isrc=data.get('isrc'),
            musicbrainz_recording_id=data.get('musicbrainz_recording_id'),
            acoustid=data.get('acoustid'),
            provider_refs=provider_refs,
            download_status=DownloadStatus(data.get('download_status', 'missing')),
            file_path=data.get('file_path'),
            file_format=data.get('file_format'),
            bitrate=data.get('bitrate'),
            confidence_score=data.get('confidence_score', 0.0),
            album_artist=data.get('album_artist'),
            track_number=data.get('track_number'),
            disc_number=data.get('disc_number'),
            release_year=data.get('release_year'),
            genres=data.get('genres', []),
            total_discs=data.get('total_discs'),
            track_total=data.get('track_total'),
            version=data.get('version'),
            is_compilation=data.get('is_compilation'),
            quality_tags=data.get('quality_tags'),
            sample_rate=data.get('sample_rate'),
            bit_depth=data.get('bit_depth'),
            file_size=data.get('file_size'),
            featured_artists=data.get('featured_artists'),
            fingerprint=data.get('fingerprint'),
            fingerprint_confidence=data.get('fingerprint_confidence'),
            created_at=parse_utc_datetime(data.get('created_at')) or utc_now(),
            updated_at=parse_utc_datetime(data.get('updated_at')) or utc_now()
        )
        return track
    
    def __repr__(self) -> str:
        artist_str = ", ".join(self.artists) if self.artists else "Unknown"
        return f"Track('{self.title or 'Unknown'}' by {artist_str}, confidence={self.confidence_score:.2f})"


@dataclass
class Track:
    """
    Placeholder for the Track class.
    This should be implemented with the actual logic or replaced with SoulSyncTrack.
    """
    track_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
