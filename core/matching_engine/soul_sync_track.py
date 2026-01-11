"""
SoulSyncTrack: The core data structure for music track representation in SoulSync.

This model unifies all metadata about a track across different providers, quality levels,
and matching contexts. It serves as the bridge between raw filenames, parsed candidates,
and matched results.
"""

import re
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
    Acts as a smart object that auto-cleans data on initialization.
    """
    # Required Fields
    raw_title: str
    artist_name: str
    album_title: str

    # Core Fields (Auto-Populated in __post_init__)
    title: str = field(init=False)
    edition: Optional[str] = None
    sort_title: Optional[str] = None
    display_title: str = field(init=False)

    # Artist/Album Metadata
    artist_sort_name: Optional[str] = None
    album_sort_title: Optional[str] = None
    album_type: Optional[str] = None
    album_release_group_id: Optional[str] = None

    # Track Metadata (Defaults to None for Sparse Updates)
    duration: Optional[int] = None  # Milliseconds
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    bitrate: Optional[int] = None
    file_path: Optional[str] = None
    file_format: Optional[str] = None
    release_year: Optional[int] = None
    added_at: Optional[datetime] = None

    # Technical Metadata
    sample_rate: Optional[int] = None
    bit_depth: Optional[int] = None
    file_size_bytes: Optional[int] = None

    # Identifiers
    musicbrainz_id: Optional[str] = None
    isrc: Optional[str] = None
    
    # Audio fingerprint for matching
    fingerprint: Optional[str] = None
    
    # Quality tags
    quality_tags: Optional[List[str]] = None
    
    # External Provider Links
    identifiers: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """
        Auto-clean and normalize data upon instantiation.
        """
        # 1. Populate display_title
        self.display_title = self.raw_title

        # 2. Regex Extraction for Edition
        edition_pattern = re.compile(
            r"(?:[\(\[]| - )\s*(.*?(?:Remix|Mix|Live|Demo|Remaster|Deluxe|Edit|Version|Acoustic|Instrumental|Bonus|Extended|Original).*?)(?:[\)\]]|$)",
            re.IGNORECASE
        )

        match = edition_pattern.search(self.raw_title)
        clean_title = self.raw_title

        if match:
            extracted_edition = match.group(1).strip()
            # Only set edition if not explicitly provided
            if self.edition is None:
                self.edition = extracted_edition

            # Remove the match from title
            start, end = match.span()
            clean_title = (self.raw_title[:start] + self.raw_title[end:]).strip()

        # 3. Balanced Quote Stripping
        clean_title = clean_title.strip()
        if len(clean_title) >= 2:
            if clean_title.startswith('"') and clean_title.endswith('"'):
                clean_title = clean_title[1:-1]
            elif clean_title.startswith("'") and clean_title.endswith("'"):
                clean_title = clean_title[1:-1]

        self.title = clean_title

        # 4. Sort Title Generation
        if self.sort_title is None:
            lower_title = self.title.lower()
            if lower_title.startswith("the "):
                self.sort_title = f"{self.title[4:]}, The"
            elif lower_title.startswith("a "):
                self.sort_title = f"{self.title[2:]}, A"
            elif lower_title.startswith("an "):
                self.sort_title = f"{self.title[3:]}, An"
            else:
                self.sort_title = self.title

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'title': self.title,
            'raw_title': self.raw_title,
            'display_title': self.display_title,
            'artist_name': self.artist_name,
            'album_title': self.album_title,
            'edition': self.edition,
            'sort_title': self.sort_title,
            'artist_sort_name': self.artist_sort_name,
            'album_sort_title': self.album_sort_title,
            'album_type': self.album_type,
            'album_release_group_id': self.album_release_group_id,
            'duration': self.duration,
            'track_number': self.track_number,
            'disc_number': self.disc_number,
            'bitrate': self.bitrate,
            'file_path': self.file_path,
            'file_format': self.file_format,
            'release_year': self.release_year,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'sample_rate': self.sample_rate,
            'bit_depth': self.bit_depth,
            'file_size_bytes': self.file_size_bytes,
            'musicbrainz_id': self.musicbrainz_id,
            'isrc': self.isrc,
            'fingerprint': self.fingerprint,
            'quality_tags': self.quality_tags,
            'identifiers': self.identifiers,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoulSyncTrack":
        """Create a SoulSyncTrack from a dictionary."""
        added_at = data.get('added_at')
        if added_at and isinstance(added_at, str):
            try:
                added_at = datetime.fromisoformat(added_at)
            except ValueError:
                pass

        # Handle backward compatibility where raw_title might be missing
        raw_title = data.get('raw_title', data.get('display_title', data.get('title', 'Unknown Title')))

        track = cls(
            raw_title=raw_title,
            artist_name=data.get('artist_name', 'Unknown Artist'),
            album_title=data.get('album_title', 'Unknown Album'),
            edition=data.get('edition'),
            sort_title=data.get('sort_title'),
            artist_sort_name=data.get('artist_sort_name'),
            album_sort_title=data.get('album_sort_title'),
            album_type=data.get('album_type'),
            album_release_group_id=data.get('album_release_group_id'),
            duration=data.get('duration'),
            track_number=data.get('track_number'),
            disc_number=data.get('disc_number'),
            bitrate=data.get('bitrate'),
            file_path=data.get('file_path'),
            file_format=data.get('file_format'),
            release_year=data.get('release_year'),
            added_at=added_at,
            sample_rate=data.get('sample_rate'),
            bit_depth=data.get('bit_depth'),
            file_size_bytes=data.get('file_size_bytes'),
            musicbrainz_id=data.get('musicbrainz_id'),
            isrc=data.get('isrc'),
            fingerprint=data.get('fingerprint'),
            quality_tags=data.get('quality_tags'),
            identifiers=data.get('identifiers', []),
        )
        return track
