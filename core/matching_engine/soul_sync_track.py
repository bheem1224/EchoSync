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
    Track data container matching the SQLAlchemy database schema.
    Acts as a pending database row - no business logic.
    """
    # Core Fields (for lookup)
    title: str
    artist_name: str  # Used for artist lookup
    album_title: Optional[str] = None  # Used for album lookup
    edition: Optional[str] = None  # remaster, live, remix, deluxe, acoustic, etc.
    
    # Track Metadata
    duration: Optional[int] = None  # Milliseconds
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    bitrate: Optional[int] = None
    file_path: Optional[str] = None
    file_format: Optional[str] = None
    release_year: Optional[int] = None
    
    # Identifiers
    musicbrainz_id: Optional[str] = None
    isrc: Optional[str] = None  # International Standard Recording Code
    
    # Audio fingerprint for matching
    fingerprint: Optional[str] = None
    
    # Quality tags for tie-breaking
    quality_tags: Optional[List[str]] = None
    
    # External Provider Links (list of dicts for ExternalIdentifiers table)
    # Format: [{'provider_source': 'plex', 'provider_item_id': '123', 'raw_data': {...}}]
    identifiers: List[Dict[str, Any]] = field(default_factory=list)



    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'title': self.title,
            'artist_name': self.artist_name,
            'album_title': self.album_title,
                        'edition': self.edition,
            'duration': self.duration,
            'track_number': self.track_number,
            'disc_number': self.disc_number,
            'bitrate': self.bitrate,
            'file_path': self.file_path,
            'file_format': self.file_format,
            'release_year': self.release_year,
            'musicbrainz_id': self.musicbrainz_id,
                        'isrc': self.isrc,
                        'fingerprint': self.fingerprint,
                        'quality_tags': self.quality_tags,
            'identifiers': self.identifiers,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoulSyncTrack":
        """Create a SoulSyncTrack from a dictionary."""
        return cls(
            title=data['title'],
            artist_name=data['artist_name'],
            album_title=data.get('album_title'),
                        edition=data.get('edition'),
            duration=data.get('duration'),
            track_number=data.get('track_number'),
            disc_number=data.get('disc_number'),
            bitrate=data.get('bitrate'),
            file_path=data.get('file_path'),
            file_format=data.get('file_format'),
            release_year=data.get('release_year'),
            musicbrainz_id=data.get('musicbrainz_id'),
                        isrc=data.get('isrc'),
                        fingerprint=data.get('fingerprint'),
                        quality_tags=data.get('quality_tags'),
            identifiers=data.get('identifiers', []),
        )
