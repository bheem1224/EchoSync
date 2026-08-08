
import re
_ATTRIBUTION_PATTERN = re.compile(
    r"[\(\[]\s*(?:feat\.?|ft\.?|featuring|with)\s+[^()\[\]]*?[\)\]]|\s+(?:feat\.?|ft\.?|featuring|with)\s+.*$",
    re.IGNORECASE
)

_VERSION_KEYWORDS_PATTERN = re.compile(
    r"\b(?:Remix|Mix|Live|Demo|Remaster|Deluxe|Edit|Version|Acoustic|Instrumental|Bonus|Extended|Original)\b",
    re.IGNORECASE
)

_EDITION_CLEANUP_RE = re.compile(r'[\)\]]\s*$')

"""
EchosyncTrack: The core data structure for music track representation in Echosync.

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
class EchosyncMedia:
    """Represents a specific physical audio file on a local or remote server."""
    file_path: Optional[str] = None  # Optional: may be None for remote/streaming media
    media_id: Optional[str] = None   # NanoID — assigned on DB insert if not provided
    file_format: Optional[str] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    bit_depth: Optional[int] = None
    channels: Optional[int] = None
    file_size_bytes: Optional[int] = None
    inode: Optional[int] = None
    mtime: Optional[float] = None
    added_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'media_id': self.media_id,
            'file_path': self.file_path,
            'file_format': self.file_format,
            'bitrate': self.bitrate,
            'sample_rate': self.sample_rate,
            'bit_depth': self.bit_depth,
            'channels': self.channels,
            'file_size_bytes': self.file_size_bytes,
            'inode': self.inode,
            'mtime': self.mtime,
            'added_at': self.added_at.isoformat() if self.added_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EchosyncMedia":
        added_at = data.get('added_at')
        if added_at and isinstance(added_at, str):
            try:
                added_at = datetime.fromisoformat(added_at)
            except ValueError:
                pass
        return cls(
            file_path=data.get('file_path'),
            media_id=data.get('media_id'),
            file_format=data.get('file_format'),
            bitrate=data.get('bitrate'),
            sample_rate=data.get('sample_rate'),
            bit_depth=data.get('bit_depth'),
            channels=data.get('channels'),
            file_size_bytes=data.get('file_size_bytes'),
            inode=data.get('inode'),
            mtime=data.get('mtime'),
            added_at=added_at
        )


@dataclass
class EchosyncTrack:
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
    artist_id: Optional[int] = None
    album_id: Optional[int] = None
    artist_sort_name: Optional[str] = None
    album_artist: Optional[str] = None
    album_sort_title: Optional[str] = None
    album_type: Optional[str] = None
    album_release_group_id: Optional[str] = None

    # Track Metadata (Defaults to None for Sparse Updates)
    duration: Optional[int] = None  # Milliseconds
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    release_year: Optional[int] = None
    version: Optional[str] = None  # e.g., "Remix", "Live", "Extended"
    added_at: Optional[datetime] = None
    
    # Physical Media Files (1:N relationship)
    media: List[EchosyncMedia] = field(default_factory=list)

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

    # Plugin-private scratch space — populated by pre_normalize_title hooks.
    # Excluded from equality / repr so it doesn't affect matching identity checks.
    plugin_context: Dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    # External Provider Links
    identifiers: Dict[str, Any] = field(default_factory=dict)
    
    # Opaque conceptual anchor (NanoID)
    sync_id: Optional[str] = None

    def __post_init__(self):

        """
        Auto-clean and normalize data upon instantiation.
        """
        # Path-detection validation warning
        for field_name, value in [
            ("artist", self.artist_name),
            ("album_artist", self.album_artist),
            ("title", self.raw_title),
            ("album_title", self.album_title)
        ]:
            if value:
                val_str = str(value).strip()
                is_suspicious = False
                if "\\" in val_str or re.match(r'^[a-zA-Z]:[/\\]', val_str):
                    is_suspicious = True
                elif val_str.startswith("/") or val_str.endswith("/"):
                    is_suspicious = True
                elif re.search(r'\.(mp3|flac|m4a|aac|wav|ogg|wma|opus|aiff|alac)$', val_str, re.IGNORECASE):
                    is_suspicious = True
                elif "/" in val_str:
                    for m in re.finditer(r'/', val_str):
                        idx = m.start()
                        before = val_str[idx - 1] if idx > 0 else ''
                        after = val_str[idx + 1] if idx < len(val_str) - 1 else ''
                        if not ((before.isalnum() or before.isspace()) and (after.isalnum() or after.isspace())):
                            is_suspicious = True
                            break

                if is_suspicious:
                    from core.tiered_logger import get_logger
                    get_logger("core.models").warning(
                        f"[core.models] - Suspicious metadata detected: Field '{field_name}' contains a file path ('{value}')."
                    )

        # 0b. Fire pre_normalize_title hook so plugins (e.g. CJK Language Pack) can
        #     extract contextual signals (e.g. drama / series names inside CJK brackets)
        #     into plugin_context BEFORE the subsequent cleaning strips those brackets.
        from core.hook_manager import hook_manager as _hm
        _hm.apply_filters('pre_normalize_title', self.raw_title, plugin_context=self.plugin_context)

        # 0. Handle legacy identifiers (List[Dict]) -> Dict[str, str]
        if isinstance(self.identifiers, list):
            new_identifiers = {}
            for item in self.identifiers:
                # Assuming old format: {'plugin_source': 'plex_guid', 'plugin_item_id': '123'}
                key = item.get('plugin_source')
                val = item.get('plugin_item_id') or item.get('id')
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

        # Validate ISRC format if present
        if self.isrc:
            isrc_clean = str(self.isrc).strip().upper().replace("-", "")
            if re.match(r"^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$", isrc_clean):
                self.isrc = isrc_clean
            else:
                self.isrc = None

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
        # Find all matches of version keywords
        all_matches = list(_VERSION_KEYWORDS_PATTERN.finditer(self.raw_title))
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
                edition_text = _EDITION_CLEANUP_RE.sub('', edition_text).strip()
                
                # Only set edition if not explicitly provided
                if self.edition is None and edition_text:
                    self.edition = edition_text
                
                # Clean title is everything before the delimiter
                clean_title = self.raw_title[:delimiter_pos].strip()

        # 3. Strip Featured Artist Attribution
        # Remove (feat. ...), [feat. ...], or trailing "feat. ..." after all other info is extracted
        clean_title = _ATTRIBUTION_PATTERN.sub("", clean_title).strip()

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

        # 6. Deterministic sync_id Assignment if None
        if not self.sync_id:
            title_norm = (self.title or self.raw_title or "").strip().lower()
            artist_norm = (self.artist_name or "").strip().lower()
            if title_norm and artist_norm:
                self.sync_id = f"ss:track:meta:{title_norm}:{artist_norm}"

    @property
    def artist(self) -> str:
        return self.artist_name

    @property
    def album(self) -> str:
        return self.album_title

    @property
    def year(self) -> Optional[int]:
        return self.release_year

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage or API transport."""
        media_list = [m.to_dict() for m in self.media]
        media_ids = [m.media_id for m in self.media if m.media_id]
        return {
            'sync_id': self.sync_id,
            'title': self.title,
            'raw_title': self.raw_title,
            'display_title': self.display_title,
            'artist': self.artist_name,
            'album_artist': self.album_artist,
            'album_title': self.album_title,
            'edition': self.edition,
            'sort_title': self.sort_title,
            'artist_sort_name': self.artist_sort_name,
            'album_sort_title': self.album_sort_title,
            'album_type': self.album_type,
            'album_release_group_id': self.album_release_group_id,
            'duration_ms': self.duration,
            'track_number': self.track_number,
            'disc_number': self.disc_number,
            'release_year': self.release_year,
            'version': self.version,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            # 2-Model: media_ids for UUID-based API lookups; media for full telemetry
            'media_ids': media_ids,
            'media': media_list,
            'mbid': self.musicbrainz_id,
            'isrc': self.isrc,
            'acoustid': self.acoustid_id,
            'mb_release_id': self.mb_release_id,
            'original_release_date': self.original_release_date.isoformat() if self.original_release_date else None,
            'fingerprint': self.fingerprint,
            'quality_tags': self.quality_tags,
            'is_compilation': self.is_compilation,
            'identifiers': self.identifiers,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EchosyncTrack":
        """Create a EchosyncTrack from a dictionary."""
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

        # Compatibility: accept duration_ms (canonical) or legacy duration key.
        duration_value = data.get('duration_ms')
        if duration_value is None:
            duration_value = data.get('duration')

        isrc_value = data.get('isrc')
        if isrc_value is None and isinstance(identifiers, dict):
            isrc_value = identifiers.get('isrc')

        # 2-Model: Parse full EchosyncMedia dicts if present; fallback to stub EchosyncMedia(media_id=mid) if only media_ids array is provided
        raw_media_list = data.get('media', [])
        if raw_media_list:
            media_list = [EchosyncMedia.from_dict(m) for m in raw_media_list]
        elif data.get('media_ids'):
            media_list = [EchosyncMedia(media_id=str(mid)) for mid in data.get('media_ids', []) if mid]
        else:
            media_list = []

        track = cls(
            sync_id=data.get('sync_id'),
            raw_title=raw_title,
            artist_name=data.get('artist') or data.get('artist_name', 'Unknown Artist'),
            album_artist=data.get('album_artist'),
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
            release_year=data.get('release_year'),
            version=data.get('version'),
            added_at=added_at,
            media=media_list,
            musicbrainz_id=data.get('mbid') or data.get('musicbrainz_id'),
            isrc=isrc_value,
            acoustid_id=data.get('acoustid') or data.get('acoustid_id'),
            mb_release_id=data.get('mb_release_id'),
            original_release_date=original_release_date,
            fingerprint=data.get('fingerprint'),
            quality_tags=data.get('quality_tags'),
            is_compilation=data.get('is_compilation'),
            identifiers=identifiers,
        )
        return track
