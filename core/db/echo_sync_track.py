"""
EchosyncTrack: The core data structure for music track representation in Echosync.

This model unifies all metadata about a track across different providers, quality levels,
and matching contexts. It serves as the bridge between raw filenames, parsed candidates,
and matched results.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


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

    file_path: str | None = None  # Optional: may be None for remote/streaming media
    media_id: str | None = None  # NanoID — assigned on DB insert if not provided
    file_format: str | None = None
    bitrate: int | None = None
    sample_rate: int | None = None
    bit_depth: int | None = None
    channels: int | None = None
    file_size_bytes: int | None = None
    inode: int | None = None
    mtime: float | None = None
    added_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "media_id": self.media_id,
            "file_path": self.file_path,
            "file_format": self.file_format,
            "bitrate": self.bitrate,
            "sample_rate": self.sample_rate,
            "bit_depth": self.bit_depth,
            "channels": self.channels,
            "file_size_bytes": self.file_size_bytes,
            "inode": self.inode,
            "mtime": self.mtime,
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EchosyncMedia":
        added_at = data.get("added_at")
        if added_at and isinstance(added_at, str):
            try:
                added_at = datetime.fromisoformat(added_at)
            except ValueError:
                pass
        return cls(
            file_path=data.get("file_path"),
            media_id=data.get("media_id"),
            file_format=data.get("file_format"),
            bitrate=data.get("bitrate"),
            sample_rate=data.get("sample_rate"),
            bit_depth=data.get("bit_depth"),
            channels=data.get("channels"),
            file_size_bytes=data.get("file_size_bytes"),
            inode=data.get("inode"),
            mtime=data.get("mtime"),
            added_at=added_at,
        )


@dataclass
class EchosyncTrack:
    """
    Track data container matching the SQLAlchemy database schema.
    Acts as a smart object that auto-cleans data on initialization.
    """

    # Required Fields
    raw_title: str = ""
    artist_name: str = ""
    album_title: str = ""

    # Core Fields (Auto-Populated in __post_init__)
    title: str = field(init=False)
    edition: str | None = None
    sort_title: str | None = None
    display_title: str = field(init=False)

    # Artist/Album Metadata
    artist_id: int | None = None
    album_id: int | None = None
    artist_sort_name: str | None = None
    album_artist: str | None = None
    album_sort_title: str | None = None
    album_type: str | None = None
    album_release_group_id: str | None = None

    # Track Metadata (Defaults to None for Sparse Updates)
    duration: int | None = None  # Milliseconds
    track_number: int | None = None
    disc_number: int | None = None
    release_year: int | None = None
    version: str | None = None  # e.g., "Remix", "Live", "Extended"
    added_at: datetime | None = None

    # Artist Roles
    primary_artists: list[str] = field(default_factory=list)
    featured_artists: list[str] = field(default_factory=list)
    remixers: list[str] = field(default_factory=list)

    # Physical Media Files (1:N relationship)
    media: list[EchosyncMedia] = field(default_factory=list)

    # Identifiers
    musicbrainz_id: str | None = None
    isrc: str | None = None

    # New Identifiers
    acoustid_id: str | None = None
    mb_release_id: str | None = None
    original_release_date: date | None = None

    # Audio fingerprint for matching
    fingerprint: str | None = None

    # Quality tags and flags
    quality_tags: list[str] | None = None
    is_compilation: bool | None = None

    # Custom track tags (used for passing provenance like COMPILATION_SOURCE)
    custom_tags: dict[str, str] = field(default_factory=dict)

    # Plugin-private scratch space — populated by pre_normalize_title hooks.
    # Excluded from equality / repr so it doesn't affect matching identity checks.
    plugin_context: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    # External Provider Links
    identifiers: dict[str, Any] = field(default_factory=dict)

    # Opaque conceptual anchor (NanoID)
    sync_id: str | None = None

    # Resolution metadata
    confidence_score: float = 0.0
    resolution_method: str | None = None
    alias_proposals: list[Any] = field(default_factory=list)
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """
        Auto-clean and normalize data upon instantiation.
        """
        # Path-detection validation warning
        for field_name, value in [
            ("artist", self.artist_name),
            ("album_artist", self.album_artist),
            ("title", self.raw_title),
            ("album_title", self.album_title),
        ]:
            if value:
                val_str = str(value).strip()
                is_suspicious = False
                # Genuine absolute or relative file paths (e.g. /data/music/..., C:\music\..., ./music/...)
                if (
                    re.match(
                        r"^(?:[a-zA-Z]:[/\\]|/(?:data|mnt|app|home|var|tmp|music|storage|media|usr|opt|etc)/|\.{1,2}[/\\])",
                        val_str,
                    )
                    or re.search(
                        r"[/\\][^/\\]+\.(mp3|flac|m4a|aac|wav|ogg|wma|opus|aiff|alac)$",
                        val_str,
                        re.IGNORECASE,
                    )
                    or re.search(
                        r"\.(mp3|flac|m4a|aac|wav|ogg|wma|opus|aiff|alac)$",
                        val_str,
                        re.IGNORECASE,
                    )
                    and ("/" in val_str or "\\" in val_str)
                ):
                    is_suspicious = True

                if is_suspicious:
                    from core.tiered_logger import get_logger

                    get_logger("core.models").warning(
                        f"[core.models] - Suspicious metadata detected: Field '{field_name}' contains a file path ('{value}')."
                    )

        # 0b. Fire pre_normalize_title hook so plugins (e.g. CJK Language Pack) can
        #     extract contextual signals (e.g. drama / series names inside CJK brackets)
        #     into plugin_context BEFORE the subsequent cleaning strips those brackets.
        from core.hook_manager import hook_manager as _hm

        _hm.apply_filters("pre_normalize_title", self.raw_title, plugin_context=self.plugin_context)

        # 0. Handle legacy identifiers (List[Dict]) -> Dict[str, str]
        if isinstance(self.identifiers, list):
            new_identifiers = {}
            for item in self.identifiers:
                # Assuming old format: {'plugin_source': 'plex_guid', 'plugin_item_id': '123'}
                key = item.get("plugin_source")
                val = item.get("plugin_item_id") or item.get("id")
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
                self.identifiers["musicbrainz_release_id"] = self.mb_release_id
        elif isinstance(self.identifiers, dict) and "musicbrainz_release_id" in self.identifiers:
            self.mb_release_id = self.identifiers["musicbrainz_release_id"]

        # 2. acoustid_id
        if self.acoustid_id:
            if isinstance(self.identifiers, dict):
                self.identifiers["acoustid_id"] = self.acoustid_id
        elif isinstance(self.identifiers, dict) and "acoustid_id" in self.identifiers:
            self.acoustid_id = self.identifiers["acoustid_id"]

        from core.matching_engine.track_parser import extract_version_descriptors, decompose_artists

        # 2. Title & Version normalization
        clean_title = self.raw_title
        if clean_title:
            clean_title, ext_version, ext_edition = extract_version_descriptors(clean_title)
            if ext_edition and not self.edition:
                self.edition = ext_edition
            if ext_version and not self.version:
                self.version = ext_version

        # 2b. Album Title & Version normalization (cleanse edition from release names e.g. "Dusk Till Dawn (radio edit)")
        if self.album_title:
            clean_album, alb_version, alb_edition = extract_version_descriptors(self.album_title)
            if clean_album:
                self.album_title = clean_album
            if not self.edition and (alb_edition or alb_version):
                if clean_title and clean_album and clean_title.strip().lower() == clean_album.strip().lower():
                    self.edition = alb_edition or alb_version
                    if not self.version and alb_version:
                        self.version = alb_version

        # 3. Artist decomposition
        if self.artist_name and not self.primary_artists:
            roles = decompose_artists(self.artist_name)
            self.primary_artists = roles.get("primary") or [self.artist_name]
            self.featured_artists = roles.get("featured") or []
            self.remixers = roles.get("remixer") or []

        # 4. Balanced Quote Stripping
        clean_title = clean_title.strip()
        if len(clean_title) >= 2 and (
            (clean_title.startswith('"') and clean_title.endswith('"'))
            or (clean_title.startswith("'") and clean_title.endswith("'"))
        ):
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

        # 6. Unique NanoID sync_id Assignment if None or empty
        if not self.sync_id:
            from database.music_database import generate_nanoid

            self.sync_id = generate_nanoid()

    @property
    def artist(self) -> str:
        return self.artist_name

    @artist.setter
    def artist(self, val: str) -> None:
        self.artist_name = val

    @property
    def album(self) -> str:
        return self.album_title

    @property
    def year(self) -> int | None:
        return self.release_year

    @property
    def file_path(self) -> str | None:
        """Return the physical file path of the primary associated media file, if present."""
        return self.media[0].file_path if self.media else None

    @property
    def musicbrainz_track_id(self) -> str | None:
        return self.musicbrainz_id

    @musicbrainz_track_id.setter
    def musicbrainz_track_id(self, val: str | None) -> None:
        self.musicbrainz_id = val

    @property
    def musicbrainz_release_id(self) -> str | None:
        return self.mb_release_id

    @musicbrainz_release_id.setter
    def musicbrainz_release_id(self, val: str | None) -> None:
        self.mb_release_id = val

    @property
    def chromaprint(self) -> str | None:
        return self.fingerprint

    @chromaprint.setter
    def chromaprint(self, val: str | None) -> None:
        self.fingerprint = val

    @property
    def duration_ms(self) -> int | None:
        return self.duration

    @duration_ms.setter
    def duration_ms(self, val: int | None) -> None:
        self.duration = val

    @property
    def media_id(self) -> str | None:
        return self.media[0].media_id if self.media else None

    @media_id.setter
    def media_id(self, val: str | None) -> None:
        if self.media:
            self.media[0].media_id = val
        elif val:
            self.media.append(EchosyncMedia(media_id=val))

    @property
    def success(self) -> bool:
        return bool(self.musicbrainz_id and self.confidence_score > 0.0)

    def get(self, key: str, default: Any = None) -> Any:
        key_map = {
            "artist": self.artist_name,
            "artist_name": self.artist_name,
            "album": self.album_title,
            "album_title": self.album_title,
            "title": getattr(self, "title", None) or self.raw_title,
            "raw_title": self.raw_title,
            "display_title": getattr(self, "display_title", None) or self.raw_title,
            "duration": self.duration,
            "duration_ms": self.duration,
            "chromaprint": self.fingerprint,
            "fingerprint": self.fingerprint,
            "musicbrainz_id": self.musicbrainz_id,
            "musicbrainz_track_id": self.musicbrainz_id,
            "mbid": self.musicbrainz_id,
            "recording_id": self.musicbrainz_id,
            "musicbrainz_release_id": self.mb_release_id,
            "mb_release_id": self.mb_release_id,
            "release_id": self.mb_release_id,
            "year": self.release_year,
            "release_year": self.release_year,
            "date": str(self.release_year) if self.release_year else None,
            "confidence_score": self.confidence_score,
            "resolution_method": self.resolution_method,
            "sync_id": self.sync_id,
            "media_id": self.media_id,
            "acoustid_id": self.acoustid_id,
            "isrc": self.isrc,
            "track_number": self.track_number,
            "disc_number": self.disc_number,
            "version": self.version,
            "edition": self.edition,
        }
        if key in key_map and key_map[key] is not None:
            return key_map[key]
        if hasattr(self, key):
            val = getattr(self, key)
            if val is not None:
                return val
        if self.custom_tags and key in self.custom_tags:
            return self.custom_tags[key]
        if self.identifiers and key in self.identifiers:
            return self.identifiers[key]
        if self.extra_metadata and key in self.extra_metadata:
            return self.extra_metadata[key]
        return default

    def __getitem__(self, key: str) -> Any:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage or API transport."""
        media_list = [m.to_dict() for m in self.media]
        media_ids = [m.media_id for m in self.media if m.media_id]
        return {
            "sync_id": self.sync_id,
            "title": self.title,
            "raw_title": self.raw_title,
            "display_title": self.display_title,
            "artist": self.artist_name,
            "album_artist": self.album_artist,
            "album_title": self.album_title,
            "edition": self.edition,
            "sort_title": self.sort_title,
            "artist_sort_name": self.artist_sort_name,
            "album_sort_title": self.album_sort_title,
            "album_type": self.album_type,
            "album_release_group_id": self.album_release_group_id,
            "duration_ms": self.duration,
            "track_number": self.track_number,
            "disc_number": self.disc_number,
            "release_year": self.release_year,
            "version": self.version,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            # 2-Model: media_ids for UUID-based API lookups; media for full telemetry
            "media_ids": media_ids,
            "media": media_list,
            "mbid": self.musicbrainz_id,
            "musicbrainz_id": self.musicbrainz_id,
            "isrc": self.isrc,
            "acoustid": self.acoustid_id,
            "acoustid_id": self.acoustid_id,
            "mb_release_id": self.mb_release_id,
            "original_release_date": self.original_release_date.isoformat() if self.original_release_date else None,
            "fingerprint": self.fingerprint,
            "chromaprint": self.fingerprint,
            "quality_tags": self.quality_tags,
            "is_compilation": self.is_compilation,
            "identifiers": self.identifiers,
            "confidence_score": self.confidence_score,
            "resolution_method": self.resolution_method,
            "recording_id": self.musicbrainz_id,
            "musicbrainz_track_id": self.musicbrainz_id,
            "musicbrainz_release_id": self.mb_release_id,
            "duration": (self.duration / 1000.0) if self.duration else None,
            "date": str(self.release_year) if self.release_year else None,
            "artist_name": self.artist_name,
            "album": self.album_title,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EchosyncTrack":
        """Create a EchosyncTrack from a dictionary."""
        added_at = data.get("added_at")
        if added_at and isinstance(added_at, str):
            try:
                added_at = datetime.fromisoformat(added_at)
            except ValueError:
                pass

        # Handle original_release_date extraction (string to date conversion happens in __post_init__ or here)
        original_release_date = data.get("original_release_date")

        # Handle backward compatibility where raw_title might be missing
        raw_title = data.get("raw_title", data.get("display_title", data.get("title", "Unknown Title")))

        # Handle identifiers: Ensure it's passed.
        identifiers = data.get("identifiers", {})
        if isinstance(identifiers, list):
            identifiers = {}

        # Compatibility: accept duration_ms (canonical) or legacy duration key.
        duration_value = data.get("duration_ms")
        if duration_value is None:
            duration_value = data.get("duration")

        isrc_value = data.get("isrc")
        if isrc_value is None and isinstance(identifiers, dict):
            isrc_value = identifiers.get("isrc")

        # 2-Model: Parse full EchosyncMedia dicts if present; fallback to stub EchosyncMedia(media_id=mid) if only media_ids array is provided
        raw_media_list = data.get("media", [])
        if raw_media_list:
            media_list = [EchosyncMedia.from_dict(m) for m in raw_media_list]
        elif data.get("media_ids"):
            media_list = [EchosyncMedia(media_id=str(mid)) for mid in data.get("media_ids", []) if mid]
        else:
            media_list = []

        track = cls(
            sync_id=data.get("sync_id"),
            raw_title=raw_title,
            artist_name=data.get("artist") or data.get("artist_name", "Unknown Artist"),
            album_artist=data.get("album_artist"),
            album_title=data.get("album_title", "Unknown Album"),
            edition=data.get("edition"),
            sort_title=data.get("sort_title"),
            artist_sort_name=data.get("artist_sort_name"),
            album_sort_title=data.get("album_sort_title"),
            album_type=data.get("album_type"),
            album_release_group_id=data.get("album_release_group_id"),
            duration=duration_value,
            track_number=data.get("track_number"),
            disc_number=data.get("disc_number"),
            release_year=data.get("release_year"),
            version=data.get("version"),
            added_at=added_at,
            media=media_list,
            musicbrainz_id=data.get("mbid") or data.get("musicbrainz_id"),
            isrc=isrc_value,
            acoustid_id=data.get("acoustid") or data.get("acoustid_id"),
            mb_release_id=data.get("mb_release_id"),
            original_release_date=original_release_date,
            fingerprint=data.get("fingerprint"),
            quality_tags=data.get("quality_tags"),
            is_compilation=data.get("is_compilation"),
            identifiers=identifiers,
            confidence_score=data.get("confidence_score", 0.0),
            resolution_method=data.get("resolution_method"),
        )
        return track

    @classmethod
    def from_orm(cls, track: Any, preloaded_fingerprint: str | None = None) -> "EchosyncTrack":
        """
        Construct a full EchosyncTrack domain model from a SQLAlchemy Track ORM entity,
        including nested EchosyncMedia objects for all associated LocalMedia rows.
        """
        media_list: list[EchosyncMedia] = []
        if hasattr(track, "media_files") and track.media_files:
            for lm in track.media_files:
                media_list.append(
                    EchosyncMedia(
                        media_id=getattr(lm, "media_id", None),
                        file_path=getattr(lm, "file_path", None),
                        file_format=getattr(lm, "file_format", None),
                        bitrate=getattr(lm, "bitrate", None),
                        sample_rate=getattr(lm, "sample_rate", None),
                        bit_depth=getattr(lm, "bit_depth", None),
                        channels=getattr(lm, "channels", None),
                        file_size_bytes=getattr(lm, "file_size_bytes", None),
                        inode=getattr(lm, "inode", None),
                        mtime=getattr(lm, "mtime", None),
                        added_at=getattr(lm, "added_at", None),
                    )
                )

        artist_name = track.artist.name if getattr(track, "artist", None) else "Unknown Artist"
        album_title = track.album.title if getattr(track, "album", None) else "Unknown Album"

        acoustid_id = None
        chromaprint = preloaded_fingerprint

        return cls(
            sync_id=getattr(track, "sync_id", None),
            raw_title=getattr(track, "title", "") or "",
            artist_name=artist_name,
            album_artist=getattr(track, "album_artist", None),
            album_title=album_title,
            edition=getattr(track, "edition", None),
            sort_title=getattr(track, "sort_title", None),
            duration=getattr(track, "duration", None),
            track_number=getattr(track, "track_number", None),
            disc_number=getattr(track, "disc_number", None),
            added_at=getattr(track, "added_at", None),
            media=media_list,
            musicbrainz_id=getattr(track, "musicbrainz_id", None),
            isrc=getattr(track, "isrc", None),
            acoustid_id=acoustid_id,
            fingerprint=chromaprint,
        )


def _get_artist_name(self) -> str:
    if getattr(self, "primary_artists", None):
        res = " & ".join(self.primary_artists)
        if getattr(self, "featured_artists", None):
            res += " ft. " + " & ".join(self.featured_artists)
        return res
    return self.__dict__.get("artist_name", "Unknown Artist")


def _set_artist_name(self, val: str):
    self.__dict__["artist_name"] = val
    if val:
        try:
            from core.matching_engine.track_parser import decompose_artists

            roles = decompose_artists(str(val))
            self.primary_artists = roles.get("primary") or [str(val).strip()]
            self.featured_artists = roles.get("featured") or []
            self.remixers = roles.get("remixer") or []
        except Exception:
            self.primary_artists = [str(val).strip()]
            self.featured_artists = []
            self.remixers = []
    else:
        self.primary_artists = []
        self.featured_artists = []
        self.remixers = []


EchosyncTrack.artist_name = property(_get_artist_name, _set_artist_name)
