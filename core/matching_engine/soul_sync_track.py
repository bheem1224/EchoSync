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
from datetime import datetime, date


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


# STANDARD IDENTIFIER KEYS
# Providers MUST use these exact keys in the 'identifiers' dict:
# - 'musicbrainz_recording_id'  (Track ID)
# - 'musicbrainz_artist_id'     (Artist ID)
# - 'musicbrainz_release_id'    (Album/Release ID)
# - 'isrc'                      (International Standard Recording Code)
# - 'upc'                       (Universal Product Code / Barcode)
# - 'acoustid_id'               (AcoustID UUID)
# - 'plex_guid'                 (Plex GUID)
# - 'spotify_id'                (Spotify ID)

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
    version: Optional[str] = None  # e.g., "Remix", "Live", "Extended"
    added_at: Optional[datetime] = None

    # Technical Metadata
    sample_rate: Optional[int] = None
    bit_depth: Optional[int] = None
    file_size_bytes: Optional[int] = None

    # Identifiers
    musicbrainz_id: Optional[str] = None
    isrc: Optional[str] = None
    
    # New Identifiers
    acoustid_id: Optional[str] = None
    mb_release_id: Optional[str] = None
    original_release_date: Optional[date] = None

    # Audio fingerprint for matching
    fingerprint: Optional[str] = None
    
    # Quality tags and flags
    quality_tags: Optional[List[str]] = None
    is_compilation: Optional[bool] = None
    

    # External Provider Links
    identifiers: Dict[str, Any] = field(default_factory=dict)



    @property
    def sync_id(self) -> str:
        import base64
        import urllib.parse

        # Base identity: ss:track:meta:{base64(lowercase_artist|lowercase_title)}
        # Ensure we safely access artist_name instead of artists[0] since artists doesn't exist on SoulSyncTrack
        artist = self.artist_name.lower() if getattr(self, "artist_name", None) else "unknown"
        title = self.title.lower() if getattr(self, "title", None) else "unknown"
        payload = f"{artist}|{title}"

        encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        base_sync_id = f"ss:track:meta:{encoded}"

        # Append available attributes as query parameters
        params = {}
        if self.duration:
            params['dur'] = str(self.duration)
        if self.isrc:
            params['isrc'] = self.isrc
        if self.musicbrainz_id:
            params['mbid'] = self.musicbrainz_id

        # Get external_id if any identifier is present
        ext_id = None
        if self.identifiers:
            # Prefer some specific ones if multiple, but we can just grab the first available value
            # Since identifiers is a dict, we can grab the first value
            # Let's check for specific ones first: spotify_id, plex_guid, etc.
            if 'spotify_id' in self.identifiers:
                ext_id = self.identifiers['spotify_id']
            elif 'plex_guid' in self.identifiers:
                ext_id = self.identifiers['plex_guid']
            elif 'musicbrainz_recording_id' in self.identifiers and not self.musicbrainz_id:
                 params['mbid'] = self.identifiers['musicbrainz_recording_id']
            elif len(self.identifiers) > 0:
                 # Just take the first value
                 ext_id = list(self.identifiers.values())[0]

        if ext_id:
            params['ext'] = ext_id

        if params:
            query_string = urllib.parse.urlencode(params)
            return f"{base_sync_id}?{query_string}"

        return base_sync_id

    def __post_init__(self):

        """
        Auto-clean and normalize data upon instantiation.
        """
        # 0. Handle legacy identifiers (List[Dict]) -> Dict[str, str]
        if isinstance(self.identifiers, list):
            new_identifiers = {}
            for item in self.identifiers:
                # Assuming old format: {'provider_source': 'plex_guid', 'provider_item_id': '123'}
                key = item.get('provider_source')
                val = item.get('provider_item_id') or item.get('id')
                if key and val:
                    new_identifiers[key] = str(val)
            self.identifiers = new_identifiers

        # 1. Populate display_title
        self.display_title = self.raw_title

        # 1.5 Handle date parsing for original_release_date
        if isinstance(self.original_release_date, str):
            try:
                # Attempt to parse ISO format string to date object
                self.original_release_date = date.fromisoformat(self.original_release_date)
            except ValueError:
                pass

        # 1.6 Sync top-level fields with identifiers

        # 1. mb_release_id
        if self.mb_release_id:
            if isinstance(self.identifiers, dict):
                self.identifiers['musicbrainz_release_id'] = self.mb_release_id
        elif isinstance(self.identifiers, dict) and 'musicbrainz_release_id' in self.identifiers:
            self.mb_release_id = self.identifiers['musicbrainz_release_id']

        # 2. acoustid_id
        if self.acoustid_id:
            if isinstance(self.identifiers, dict):
                self.identifiers['acoustid_id'] = self.acoustid_id
        elif isinstance(self.identifiers, dict) and 'acoustid_id' in self.identifiers:
            self.acoustid_id = self.identifiers['acoustid_id']

        # 2. Regex Extraction for Edition
        # Extract edition/version info from title (e.g., "2005 Remaster", "Live at X", etc.)
        # Strategy: Find the LAST occurrence of version keywords, then work backwards to find delimiter
        # This handles: "Sweet Dreams (Are Made of This) - 2005 Remaster" → edition="2005 Remaster"
        version_keywords = r"(?:Remix|Mix|Live|Demo|Remaster|Deluxe|Edit|Version|Acoustic|Instrumental|Bonus|Extended|Original)"
        
        # Find all matches of version keywords
        all_matches = list(re.finditer(rf"\b{version_keywords}\b", self.raw_title, re.IGNORECASE))
        clean_title = self.raw_title
        
        if all_matches:
            # Use the LAST match (rightmost)
            last_match = all_matches[-1]
            keyword_pos = last_match.start()
            
            # Look backwards from keyword to find the delimiter (dash, bracket, paren)
            prefix = self.raw_title[:keyword_pos]
            
            # Find the LAST delimiter before the keyword
            last_dash = prefix.rfind(' - ')
            last_paren = prefix.rfind('(')
            last_bracket = prefix.rfind('[')
            
            # Use the rightmost delimiter
            delimiter_pos = max(last_dash, last_paren, last_bracket)
            
            if delimiter_pos >= 0:
                # Extract from delimiter to end
                if last_dash == delimiter_pos:
                    edition_start = delimiter_pos + 3  # Skip " - "
                else:
                    edition_start = delimiter_pos + 1  # Skip '(' or '['
                
                edition_text = self.raw_title[edition_start:].strip()
                
                # Remove trailing closing brackets/parens if present
                edition_text = re.sub(r'[\)\]]\s*$', '', edition_text).strip()
                
                # Only set edition if not explicitly provided
                if self.edition is None and edition_text:
                    self.edition = edition_text
                
                # Clean title is everything before the delimiter
                clean_title = self.raw_title[:delimiter_pos].strip()

        # 3. Strip Featured Artist Attribution
        # Remove (feat. ...), [feat. ...], or trailing "feat. ..." after all other info is extracted
        attribution_pattern = re.compile(
            r"[\(\[]\s*(?:feat\.?|ft\.?|featuring|with)\s+.*?[\]\)]|\s+(?:feat\.?|ft\.?|featuring|with)\s+.*$",
            re.IGNORECASE
        )
        clean_title = attribution_pattern.sub("", clean_title).strip()

        # 4. Balanced Quote Stripping
        clean_title = clean_title.strip()
        if len(clean_title) >= 2:
            if clean_title.startswith('"') and clean_title.endswith('"'):
                clean_title = clean_title[1:-1]
            elif clean_title.startswith("'") and clean_title.endswith("'"):
                clean_title = clean_title[1:-1]

        self.title = clean_title

        # 5. Sort Title Generation
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
            'sync_id': self.sync_id,
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
            'version': self.version,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'sample_rate': self.sample_rate,
            'bit_depth': self.bit_depth,
            'file_size_bytes': self.file_size_bytes,
            'musicbrainz_id': self.musicbrainz_id,
            'isrc': self.isrc,
            'acoustid_id': self.acoustid_id,
            'mb_release_id': self.mb_release_id,
            'original_release_date': self.original_release_date.isoformat() if self.original_release_date else None,
            'fingerprint': self.fingerprint,
            'quality_tags': self.quality_tags,
            'is_compilation': self.is_compilation,
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

        # Handle original_release_date extraction (string to date conversion happens in __post_init__ or here)
        original_release_date = data.get('original_release_date')

        # Handle backward compatibility where raw_title might be missing
        raw_title = data.get('raw_title', data.get('display_title', data.get('title', 'Unknown Title')))

        # Handle identifiers: Ensure it's passed.
        identifiers = data.get('identifiers', {})
        if isinstance(identifiers, list):
             identifiers = {}

        # Compatibility: accept either duration or duration_ms and hydrate ISRC from identifiers.
        duration_value = data.get('duration')
        if duration_value is None:
            duration_value = data.get('duration_ms')

        isrc_value = data.get('isrc')
        if isrc_value is None and isinstance(identifiers, dict):
            isrc_value = identifiers.get('isrc')

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
            duration=duration_value,
            track_number=data.get('track_number'),
            disc_number=data.get('disc_number'),
            bitrate=data.get('bitrate'),
            file_path=data.get('file_path'),
            file_format=data.get('file_format'),
            release_year=data.get('release_year'),
            version=data.get('version'),
            added_at=added_at,
            sample_rate=data.get('sample_rate'),
            bit_depth=data.get('bit_depth'),
            file_size_bytes=data.get('file_size_bytes'),
            musicbrainz_id=data.get('musicbrainz_id'),
            isrc=isrc_value,
            acoustid_id=data.get('acoustid_id'),
            mb_release_id=data.get('mb_release_id'),
            original_release_date=original_release_date,
            fingerprint=data.get('fingerprint'),
            quality_tags=data.get('quality_tags'),
            is_compilation=data.get('is_compilation'),
            identifiers=identifiers,
        )
        return track
