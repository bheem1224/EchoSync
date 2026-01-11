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
from datetime import datetime, timezone


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
    display_title: str  # Original full title
    artist_name: str  # Used for artist lookup
    album_title: Optional[str] = None  # Used for album lookup
    edition: Optional[str] = None  # remaster, live, remix, deluxe, acoustic, etc.
    sort_title: Optional[str] = None
    
    # Artist/Album Metadata
    artist_sort_name: Optional[str] = None
    album_sort_title: Optional[str] = None
    album_type: Optional[str] = None
    album_release_group_id: Optional[str] = None

    # Track Metadata
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

        return cls(
            title=data['title'],
            display_title=data.get('display_title', data['title']),
            artist_name=data['artist_name'],
            album_title=data.get('album_title'),
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

    @staticmethod
    def from_plex(data: Dict[str, Any]) -> "SoulSyncTrack":
        """
        Factory method to create a SoulSyncTrack from a Plex API response.
        Handles data cleaning, regex extraction, and normalization.
        """
        raw_title = data.get('title', '')

        # 1. Edition Extraction
        edition = None
        clean_title = raw_title

        # Regex pattern for Edition extraction
        # Targets: (Live), [Remix], - Remaster, etc.
        edition_pattern = re.compile(
            r"(?:[\(\[]| - )\s*(.*?(?:Remix|Mix|Live|Demo|Remaster|Deluxe|Edit|Version|Acoustic|Instrumental|Bonus|Extended).*?)(?:[\)\]]|$)",
            re.IGNORECASE
        )

        match = edition_pattern.search(raw_title)
        if match:
            edition = match.group(1).strip()
            # Remove the *entire match* from raw_title to generate clean_title
            # We replace the matched string with nothing, then clean up
            start, end = match.span()
            clean_title = (raw_title[:start] + raw_title[end:]).strip()

        # 2. Title Sanitization (Balanced Quote Check)
        clean_title = clean_title.strip()
        if len(clean_title) >= 2:
            if clean_title.startswith('"') and clean_title.endswith('"'):
                clean_title = clean_title[1:-1]
            if clean_title.startswith("'") and clean_title.endswith("'"):
                clean_title = clean_title[1:-1]

        # 3. Sort Title
        sort_title = data.get('titleSort')
        if not sort_title:
            # Fallback: Article Mover
            lower_title = clean_title.lower()
            if lower_title.startswith("the "):
                sort_title = f"{clean_title[4:]}, The"
            elif lower_title.startswith("a "):
                sort_title = f"{clean_title[2:]}, A"
            elif lower_title.startswith("an "):
                sort_title = f"{clean_title[3:]}, An"
            else:
                sort_title = clean_title

        # 4. Tech Metadata Extraction
        sample_rate = None
        bit_depth = None
        file_size_bytes = None
        bitrate = None
        file_format = None
        file_path = None

        media_items = data.get('Media', [])
        if media_items:
            media = media_items[0]
            # Container/Format
            file_format = media.get('container')
            bitrate = media.get('bitrate')

            parts = media.get('Part', [])
            if parts:
                part = parts[0]
                file_path = part.get('file')
                file_size_bytes = part.get('size')

                # Check streams for detailed audio info
                streams = part.get('Stream', [])
                for stream in streams:
                    # streamType 2 is typically audio
                    if stream.get('streamType') == 2 or stream.get('codec'):
                        # Prefer the selected/default stream, or just the first one found
                        sample_rate = stream.get('samplingRate')
                        bit_depth = stream.get('bitDepth')
                        if stream.get('bitrate'):
                            bitrate = stream.get('bitrate')
                        break

        # 5. Timestamps
        added_at = None
        if 'addedAt' in data:
            try:
                added_at = datetime.fromtimestamp(int(data['addedAt']), tz=timezone.utc)
            except (ValueError, TypeError):
                pass

        if not added_at:
            added_at = datetime.now(timezone.utc)

        # 6. Identifiers
        identifiers = []
        if data.get('ratingKey'):
             identifiers.append({
                 'provider_source': 'plex',
                 'provider_item_id': str(data['ratingKey']),
                 'raw_data': data
             })

        # 7. Construct Object
        return SoulSyncTrack(
            title=clean_title,
            display_title=raw_title,
            artist_name=data.get('grandparentTitle') or data.get('parentTitle') or "Unknown Artist", # Fallback logic
            album_title=data.get('parentTitle'),
            edition=edition,
            sort_title=sort_title,
            artist_sort_name=data.get('grandparentSortTitle'),
            album_sort_title=data.get('parentSortTitle'),
            # album_type and release_group_id not available in standard Plex track JSON usually, left None

            duration=data.get('duration'),
            track_number=data.get('index'),
            disc_number=data.get('parentIndex'),
            bitrate=bitrate,
            file_path=file_path,
            file_format=file_format,
            release_year=data.get('year'), # Plex often has 'year' at top level or parentYear

            added_at=added_at,
            sample_rate=sample_rate,
            bit_depth=bit_depth,
            file_size_bytes=file_size_bytes,

            identifiers=identifiers
        )
