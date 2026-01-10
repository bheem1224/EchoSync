"""
SoulSyncTrack: The core data structure for music track representation in SoulSync.

This model unifies all metadata about a track across different providers, quality levels,
and matching contexts. It serves as the bridge between raw filenames, parsed candidates,
and matched results.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


class DownloadStatus(Enum):
    MISSING = "missing"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    VERIFIED = "verified"
    FAILED = "failed"


class QualityTag(Enum):
    FLAC_24BIT = "FLAC 24-bit"
    FLAC_16BIT = "FLAC 16-bit"
    MP3_320KBPS = "MP3 320kbps"
    MP3_256KBPS = "MP3 256kbps"
    MP3_192KBPS = "MP3 192kbps"
    AAC = "AAC"
    ALAC = "ALAC"
    OGG_VORBIS = "OGG Vorbis"
    OPUS = "Opus"


@dataclass
class SoulSyncTrack:
    """
    Unified track representation for matching, storage, and enrichment.
    Assumes data is standardized by providers.
    """
    # Core Fields
    title: str
    artist: str
    album: Optional[str] = None
    duration_ms: Optional[int] = None

    # Matching Identifiers
    isrc: Optional[str] = None
    musicbrainz_id: Optional[str] = None

    # Additional Identifiers
    track_id: Optional[str] = None
    musicbrainz_album_id: Optional[str] = None

    # Download and File Info
    download_status: DownloadStatus = DownloadStatus.MISSING
    file_path: Optional[str] = None
    file_format: Optional[str] = None
    bitrate: Optional[int] = None

    # Metadata
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    release_year: Optional[int] = None
    genres: List[str] = field(default_factory=list)

    # Confidence Score
    confidence_score: float = 0.0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def enrich(self, **kwargs) -> None:
        """Progressively enrich track fields."""
        for key, value in kwargs.items():
            if value is not None and hasattr(self, key):
                current = getattr(self, key)
                if current is None or (isinstance(current, list) and not current):
                    setattr(self, key, value)
        self.updated_at = datetime.now()
        self._calculate_confidence()

    def _calculate_confidence(self) -> None:
        """Calculate confidence score based on field completeness."""
        score = 0.0
        total_weight = 0.0
        field_weights = {
            'title': 0.25,
            'artist': 0.25,
            'album': 0.15,
            'duration_ms': 0.10,
            'isrc': 0.10,
            'file_path': 0.15 if self.download_status == DownloadStatus.VERIFIED else 0.0
        }
        for field, weight in field_weights.items():
            if getattr(self, field):
                score += weight
            total_weight += weight
        self.confidence_score = min(score / total_weight if total_weight > 0 else 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'duration_ms': self.duration_ms,
            'isrc': self.isrc,
            'musicbrainz_id': self.musicbrainz_id,
            'download_status': self.download_status.value,
            'file_path': self.file_path,
            'file_format': self.file_format,
            'bitrate': self.bitrate,
            'track_number': self.track_number,
            'disc_number': self.disc_number,
            'release_year': self.release_year,
            'genres': self.genres,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoulSyncTrack":
        """Create a SoulSyncTrack from a dictionary."""
        return cls(
            title=data['title'],
            artist=data['artist'],
            album=data.get('album'),
            duration_ms=data.get('duration_ms'),
            isrc=data.get('isrc'),
            musicbrainz_id=data.get('musicbrainz_id'),
            download_status=DownloadStatus(data.get('download_status', 'missing')),
            file_path=data.get('file_path'),
            file_format=data.get('file_format'),
            bitrate=data.get('bitrate'),
            track_number=data.get('track_number'),
            disc_number=data.get('disc_number'),
            release_year=data.get('release_year'),
            genres=data.get('genres', []),
            confidence_score=data.get('confidence_score', 0.0),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )
