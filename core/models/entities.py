"""Passive, immutable domain DTOs for EchoSync tracks, albums, artists, credits, and physical media."""

from __future__ import annotations

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


SUBSTITUTABLE_VERSION_TYPES: frozenset[str] = frozenset(
    {"original", "deluxe", "anniversary", "remaster", "soundtrack"}
)

DISTINCT_VERSION_TYPES: frozenset[str] = frozenset(
    {"remix", "acoustic", "instrumental", "live", "parody", "extended"}
)


def classify_version_type(version: str | None = None, edition: str | None = None) -> str:
    """Classify version/edition descriptors into canonical substitutable or distinct version_type."""
    combined = f"{version or ''} {edition or ''}".strip().lower()
    if not combined:
        return "original"

    for token in ("remix", "rmx", "rework", "vip", "bootleg", "mashup"):
        if token in combined:
            return "remix"
    if "instrumental" in combined or "karaoke" in combined or "off vocal" in combined:
        return "instrumental"
    if "acoustic" in combined or "unplugged" in combined:
        return "acoustic"
    if "live" in combined or "concert" in combined:
        return "live"
    if "parody" in combined:
        return "parody"
    if "extended" in combined or "maxi" in combined:
        return "extended"

    if "remaster" in combined:
        return "remaster"
    if "deluxe" in combined:
        return "deluxe"
    if "anniversary" in combined:
        return "anniversary"
    if "soundtrack" in combined or " ost" in f" {combined}":
        return "soundtrack"

    if combined in DISTINCT_VERSION_TYPES or combined in SUBSTITUTABLE_VERSION_TYPES:
        return combined
    return "original"


def _coerce_duration_ms(raw_duration_ms: Any = None, raw_duration: Any = None) -> int | None:
    """Normalize duration inputs into integer milliseconds, converting legacy float seconds."""
    if raw_duration_ms is not None:
        try:
            if isinstance(raw_duration_ms, float) and raw_duration_ms < 1000.0:
                return int(round(raw_duration_ms))
            return int(round(float(raw_duration_ms)))
        except (TypeError, ValueError):
            return None

    if raw_duration is not None:
        try:
            if isinstance(raw_duration, float):
                if raw_duration < 10000.0:
                    return int(round(raw_duration * 1000.0))
                return int(round(raw_duration))
            return int(raw_duration)
        except (TypeError, ValueError):
            return None

    return None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


@dataclass(frozen=True)
class ArtistCredit:
    """Immutable artist credit entry with role, position, and optional identifiers."""

    name: str
    role: str = "primary"
    position: int = 0
    mbid: str | None = None
    sort_name: str | None = None
    artist_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "position": self.position,
            "mbid": self.mbid,
            "sort_name": self.sort_name,
            "artist_id": self.artist_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtistCredit:
        return cls(
            name=str(data.get("name") or ""),
            role=str(data.get("role") or "primary"),
            position=int(data.get("position") or 0),
            mbid=data.get("mbid") or data.get("musicbrainz_id"),
            sort_name=data.get("sort_name"),
            artist_id=data.get("artist_id"),
        )


@dataclass(frozen=True)
class EchosyncArtist:
    """Immutable canonical artist domain DTO."""

    name: str
    normalized_name: str = ""
    sort_name: str | None = None
    musicbrainz_id: str | None = None
    artist_id: int | None = None
    image_url: str | None = None
    parent_artist_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "normalized_name": self.normalized_name,
            "sort_name": self.sort_name,
            "musicbrainz_id": self.musicbrainz_id,
            "artist_id": self.artist_id,
            "image_url": self.image_url,
            "parent_artist_id": self.parent_artist_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EchosyncArtist:
        return cls(
            name=str(data.get("name") or ""),
            normalized_name=str(data.get("normalized_name") or ""),
            sort_name=data.get("sort_name"),
            musicbrainz_id=data.get("musicbrainz_id") or data.get("mbid"),
            artist_id=data.get("artist_id") or data.get("id"),
            image_url=data.get("image_url"),
            parent_artist_id=data.get("parent_artist_id"),
        )

    @classmethod
    def from_orm(cls, artist: Any) -> EchosyncArtist:
        return cls(
            name=getattr(artist, "name", "") or "",
            normalized_name=getattr(artist, "normalized_name", "") or "",
            sort_name=getattr(artist, "sort_name", None),
            musicbrainz_id=getattr(artist, "musicbrainz_id", None),
            artist_id=getattr(artist, "id", None),
            image_url=getattr(artist, "image_url", None),
            parent_artist_id=getattr(artist, "parent_artist_id", None),
        )


@dataclass(frozen=True)
class EchosyncAlbum:
    """Immutable canonical album domain DTO."""

    title: str
    normalized_title: str = ""
    artist_name: str = ""
    artist_id: int | None = None
    album_id: int | None = None
    release_date: date | None = None
    original_release_date: date | None = None
    release_group_id: str | None = None
    mb_release_id: str | None = None
    album_type: str | None = None
    cover_image_url: str | None = None
    artists: tuple[ArtistCredit, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "normalized_title": self.normalized_title,
            "artist_name": self.artist_name,
            "artist_id": self.artist_id,
            "album_id": self.album_id,
            "release_date": self.release_date.isoformat() if self.release_date else None,
            "original_release_date": (
                self.original_release_date.isoformat() if self.original_release_date else None
            ),
            "release_group_id": self.release_group_id,
            "mb_release_id": self.mb_release_id,
            "album_type": self.album_type,
            "cover_image_url": self.cover_image_url,
            "artists": [c.to_dict() for c in self.artists],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EchosyncAlbum:
        raw_credits = data.get("artists") or ()
        credits = tuple(
            c if isinstance(c, ArtistCredit) else ArtistCredit.from_dict(c) for c in raw_credits
        )
        return cls(
            title=str(data.get("title") or ""),
            normalized_title=str(data.get("normalized_title") or ""),
            artist_name=str(data.get("artist_name") or data.get("artist") or ""),
            artist_id=data.get("artist_id"),
            album_id=data.get("album_id") or data.get("id"),
            release_date=_parse_date(data.get("release_date")),
            original_release_date=_parse_date(data.get("original_release_date")),
            release_group_id=data.get("release_group_id"),
            mb_release_id=data.get("mb_release_id"),
            album_type=data.get("album_type"),
            cover_image_url=data.get("cover_image_url"),
            artists=credits,
        )

    @classmethod
    def from_orm(cls, album: Any) -> EchosyncAlbum:
        artist_obj = getattr(album, "artist", None)
        credits = tuple(
            ArtistCredit(
                name=assoc.artist.name,
                role=getattr(assoc, "role", "primary") or "primary",
                position=int(getattr(assoc, "position", 0) or 0),
                mbid=getattr(assoc.artist, "musicbrainz_id", None),
                sort_name=getattr(assoc.artist, "sort_name", None),
                artist_id=getattr(assoc, "artist_id", None),
            )
            for assoc in (getattr(album, "artist_associations", None) or ())
            if getattr(assoc, "artist", None) is not None
        )
        return cls(
            title=getattr(album, "title", "") or "",
            normalized_title=getattr(album, "normalized_title", "") or "",
            artist_name=getattr(artist_obj, "name", "") or "",
            artist_id=getattr(album, "artist_id", None),
            album_id=getattr(album, "id", None),
            release_date=_parse_date(getattr(album, "release_date", None)),
            original_release_date=_parse_date(getattr(album, "original_release_date", None)),
            release_group_id=getattr(album, "release_group_id", None),
            mb_release_id=getattr(album, "mb_release_id", None),
            album_type=getattr(album, "album_type", None),
            cover_image_url=getattr(album, "cover_image_url", None),
            artists=credits,
        )


@dataclass(frozen=True)
class EchosyncMedia:
    """Immutable DTO representing a physical audio file on disk or remote storage."""

    file_path: str | None = None
    media_id: str | None = None
    file_format: str | None = None
    bitrate: int | None = None
    sample_rate: int | None = None
    bit_depth: int | None = None
    channels: int | None = None
    duration_ms: int | None = None
    file_size_bytes: int | None = None
    inode: int | None = None
    mtime: float | None = None
    added_at: datetime | None = None

    @property
    def format(self) -> str | None:
        return self.file_format

    def to_dict(self) -> dict[str, Any]:
        return {
            "media_id": self.media_id,
            "file_path": self.file_path,
            "file_format": self.file_format,
            "bitrate": self.bitrate,
            "sample_rate": self.sample_rate,
            "bit_depth": self.bit_depth,
            "channels": self.channels,
            "duration_ms": self.duration_ms,
            "file_size_bytes": self.file_size_bytes,
            "inode": self.inode,
            "mtime": self.mtime,
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EchosyncMedia:
        return cls(
            file_path=data.get("file_path"),
            media_id=data.get("media_id"),
            file_format=data.get("file_format") or data.get("format"),
            bitrate=data.get("bitrate"),
            sample_rate=data.get("sample_rate"),
            bit_depth=data.get("bit_depth"),
            channels=data.get("channels"),
            duration_ms=_coerce_duration_ms(data.get("duration_ms"), data.get("duration")),
            file_size_bytes=data.get("file_size_bytes"),
            inode=data.get("inode"),
            mtime=data.get("mtime"),
            added_at=_parse_datetime(data.get("added_at")),
        )


@dataclass(frozen=True)
class EchosyncTrack:
    """Passive, immutable canonical domain DTO for EchoSync tracks."""

    raw_title: str = ""
    artist_name: str = ""
    album_title: str = ""

    title: str = ""
    edition: str | None = None
    version_type: str = "original"
    sort_title: str | None = None
    display_title: str = ""

    artist_id: int | None = None
    album_id: int | None = None
    artist_sort_name: str | None = None
    album_artist: str | None = None
    album_sort_title: str | None = None
    album_type: str | None = None
    album_release_group_id: str | None = None

    duration_ms: int | None = None
    track_number: int | None = None
    disc_number: int | None = None
    release_year: int | None = None
    version: str | None = None
    added_at: datetime | None = None

    primary_artists: list[str] = field(default_factory=list)
    featured_artists: list[str] = field(default_factory=list)
    remixers: list[str] = field(default_factory=list)

    media: list[EchosyncMedia] = field(default_factory=list)

    musicbrainz_id: str | None = None
    isrc: str | None = None
    acoustid_id: str | None = None
    mb_release_id: str | None = None
    original_release_date: date | None = None
    fingerprint: str | None = None

    quality_tags: list[str] | None = None
    is_compilation: bool | None = None
    custom_tags: dict[str, str] = field(default_factory=dict)
    plugin_context: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)
    identifiers: dict[str, Any] = field(default_factory=dict)
    sync_id: str | None = None

    confidence_score: float = 0.0
    resolution_method: str | None = None
    alias_proposals: list[Any] = field(default_factory=list)
    extra_metadata: dict[str, Any] = field(default_factory=dict)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    @property
    def artist(self) -> str:
        return self.artist_name

    @property
    def album(self) -> str:
        return self.album_title

    @property
    def year(self) -> int | None:
        return self.release_year

    @property
    def local_media(self) -> list[EchosyncMedia]:
        return list(self.media)

    @property
    def file_path(self) -> str | None:
        return self.media[0].file_path if self.media else None

    @property
    def musicbrainz_track_id(self) -> str | None:
        return self.musicbrainz_id

    @property
    def musicbrainz_release_id(self) -> str | None:
        return self.mb_release_id

    @property
    def chromaprint(self) -> str | None:
        return self.fingerprint

    @property
    def media_id(self) -> str | None:
        return self.media[0].media_id if self.media else None

    @property
    def success(self) -> bool:
        return bool(self.musicbrainz_id and self.confidence_score > 0.0)

    @property
    def resolution_stage(self) -> str:
        stage_map = {
            "signature_verified": "Stage 0: Signature Verified",
            "embedded_mbid": "Fast-Path: Embedded MBID",
            "local_cache": "Stage 2: Local Cache",
            "acoustid": "Stage 3: AcoustID",
            "isrc": "Stage 4: ISRC",
            "text_waterfall": "Stage 5: Text Waterfall",
            "embedded_mbid_fallback": "Fallback: Embedded MBID",
        }
        if self.resolution_method in stage_map:
            return stage_map[self.resolution_method]
        if self.resolution_method and self.resolution_method.startswith("signature_verified_merged_with_"):
            sub = self.resolution_method.replace("signature_verified_merged_with_", "")
            sub_name = stage_map.get(sub, sub)
            return f"Stage 0 (Merged with {sub_name})"
        if not self.confidence_score or self.confidence_score <= 0.0:
            return "Unresolved (Manual Review Needed)"
        return self.resolution_method or "Unresolved"

    def get(self, key: str, default: Any = None) -> Any:
        effective_title = self.title or self.raw_title
        effective_display = self.display_title or effective_title
        key_map = {
            "artist": self.artist_name,
            "artist_name": self.artist_name,
            "album": self.album_title,
            "album_title": self.album_title,
            "title": effective_title,
            "raw_title": self.raw_title,
            "display_title": effective_display,
            "duration_ms": self.duration_ms,
            "duration": self.duration_ms,
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
            "version_type": self.version_type,
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
        effective_title = self.title or self.raw_title
        effective_display = self.display_title or effective_title
        media_list = [m.to_dict() for m in self.media]
        media_ids = [m.media_id for m in self.media if m.media_id]
        return {
            "sync_id": self.sync_id,
            "title": effective_title,
            "raw_title": self.raw_title,
            "display_title": effective_display,
            "artist": self.artist_name,
            "artist_name": self.artist_name,
            "album_artist": self.album_artist,
            "album_title": self.album_title,
            "edition": self.edition,
            "version_type": self.version_type,
            "sort_title": self.sort_title,
            "artist_sort_name": self.artist_sort_name,
            "album_sort_title": self.album_sort_title,
            "album_type": self.album_type,
            "album_release_group_id": self.album_release_group_id,
            "duration_ms": self.duration_ms,
            "track_number": self.track_number,
            "disc_number": self.disc_number,
            "release_year": self.release_year,
            "version": self.version,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "media_ids": media_ids,
            "media": media_list,
            "mbid": self.musicbrainz_id,
            "musicbrainz_id": self.musicbrainz_id,
            "musicbrainz_track_id": self.musicbrainz_id,
            "isrc": self.isrc,
            "acoustid": self.acoustid_id,
            "acoustid_id": self.acoustid_id,
            "mb_release_id": self.mb_release_id,
            "musicbrainz_release_id": self.mb_release_id,
            "album": self.album_title,
            "year": self.release_year,
            "original_release_date": (
                self.original_release_date.isoformat() if self.original_release_date else None
            ),
            "fingerprint": self.fingerprint,
            "chromaprint": self.fingerprint,
            "quality_tags": self.quality_tags,
            "is_compilation": self.is_compilation,
            "primary_artists": list(self.primary_artists),
            "featured_artists": list(self.featured_artists),
            "remixers": list(self.remixers),
            "identifiers": dict(self.identifiers),
            "custom_tags": dict(self.custom_tags),
            "confidence_score": self.confidence_score,
            "resolution_method": self.resolution_method,
            "extra_metadata": dict(self.extra_metadata),
            "diagnostics": list(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EchosyncTrack:
        identifiers = data.get("identifiers") or {}
        if isinstance(identifiers, list):
            normalized_ids: dict[str, Any] = {}
            for item in identifiers:
                if isinstance(item, dict):
                    key = item.get("plugin_source")
                    val = item.get("plugin_item_id") or item.get("id")
                    if key and val:
                        normalized_ids[str(key)] = str(val)
            identifiers = normalized_ids
        elif not isinstance(identifiers, dict):
            identifiers = {}

        raw_title = str(data.get("raw_title") or data.get("title") or "")
        title = str(data.get("title") or raw_title)
        display_title = str(data.get("display_title") or raw_title or title)

        duration_ms = _coerce_duration_ms(data.get("duration_ms"), data.get("duration"))
        isrc_value = data.get("isrc")
        if isrc_value is None:
            isrc_value = identifiers.get("isrc")

        raw_media_list = data.get("media") or []
        if raw_media_list:
            media_list = [
                m if isinstance(m, EchosyncMedia) else EchosyncMedia.from_dict(m) for m in raw_media_list
            ]
        elif data.get("media_ids"):
            media_list = [EchosyncMedia(media_id=str(mid)) for mid in data.get("media_ids", []) if mid]
        else:
            media_list = []

        edition = data.get("edition")
        version = data.get("version")
        version_type = data.get("version_type") or classify_version_type(version, edition)

        return cls(
            sync_id=data.get("sync_id"),
            raw_title=raw_title,
            title=title,
            display_title=display_title,
            artist_name=str(data.get("artist") or data.get("artist_name") or "Unknown Artist"),
            album_artist=data.get("album_artist"),
            album_title=str(data.get("album_title") or data.get("album") or "Unknown Album"),
            edition=edition,
            version_type=version_type,
            sort_title=data.get("sort_title"),
            artist_sort_name=data.get("artist_sort_name"),
            album_sort_title=data.get("album_sort_title"),
            album_type=data.get("album_type"),
            album_release_group_id=data.get("album_release_group_id"),
            duration_ms=duration_ms,
            track_number=data.get("track_number"),
            disc_number=data.get("disc_number"),
            release_year=data.get("release_year") or data.get("year"),
            version=version,
            added_at=_parse_datetime(data.get("added_at")),
            primary_artists=list(data.get("primary_artists") or []),
            featured_artists=list(data.get("featured_artists") or []),
            remixers=list(data.get("remixers") or []),
            media=media_list,
            musicbrainz_id=data.get("mbid") or data.get("musicbrainz_id") or data.get("musicbrainz_track_id"),
            isrc=isrc_value,
            acoustid_id=data.get("acoustid") or data.get("acoustid_id"),
            mb_release_id=data.get("mb_release_id") or data.get("musicbrainz_release_id"),
            original_release_date=_parse_date(data.get("original_release_date")),
            fingerprint=data.get("fingerprint") or data.get("chromaprint"),
            quality_tags=data.get("quality_tags"),
            is_compilation=data.get("is_compilation"),
            custom_tags=dict(data.get("custom_tags") or {}),
            identifiers=dict(identifiers),
            confidence_score=float(data.get("confidence_score", 0.0) or 0.0),
            resolution_method=data.get("resolution_method"),
            alias_proposals=list(data.get("alias_proposals") or []),
            extra_metadata=dict(data.get("extra_metadata") or {}),
            diagnostics=list(data.get("diagnostics") or []),
        )

    @classmethod
    def from_orm(cls, track: Any, preloaded_fingerprint: str | None = None) -> EchosyncTrack:
        track_dur = getattr(track, "duration", None)
        media_list: list[EchosyncMedia] = []
        if hasattr(track, "media_files") and track.media_files:
            for lm in track.media_files:
                media_dur = getattr(lm, "duration_ms", None)
                media_list.append(
                    EchosyncMedia(
                        media_id=getattr(lm, "media_id", None),
                        file_path=getattr(lm, "file_path", None),
                        file_format=getattr(lm, "file_format", None),
                        bitrate=getattr(lm, "bitrate", None),
                        sample_rate=getattr(lm, "sample_rate", None),
                        bit_depth=getattr(lm, "bit_depth", None),
                        channels=getattr(lm, "channels", None),
                        duration_ms=media_dur if media_dur is not None else track_dur,
                        file_size_bytes=getattr(lm, "file_size_bytes", None),
                        inode=getattr(lm, "inode", None),
                        mtime=getattr(lm, "mtime", None),
                        added_at=getattr(lm, "added_at", None),
                    )
                )

        artist_name = track.artist.name if getattr(track, "artist", None) else "Unknown Artist"
        album_title = track.album.title if getattr(track, "album", None) else "Unknown Album"
        title_str = getattr(track, "title", "") or ""
        edition = getattr(track, "edition", None)
        version_type = getattr(track, "version_type", None) or classify_version_type(edition=edition)

        primary: list[str] = []
        featured: list[str] = []
        remixers: list[str] = []
        for assoc in getattr(track, "artist_associations", None) or ():
            a_obj = getattr(assoc, "artist", None)
            if a_obj and getattr(a_obj, "name", None):
                role = (getattr(assoc, "role", "primary") or "primary").lower()
                if role == "featured":
                    featured.append(a_obj.name)
                elif role == "remixer":
                    remixers.append(a_obj.name)
                else:
                    primary.append(a_obj.name)
        if not primary and artist_name and not artist_name.strip().lower().startswith("unknown"):
            primary = [artist_name]

        return cls(
            sync_id=getattr(track, "sync_id", None),
            raw_title=title_str,
            title=title_str,
            display_title=title_str,
            artist_name=artist_name,
            album_artist=getattr(track, "album_artist", None),
            album_title=album_title,
            edition=edition,
            version_type=version_type,
            sort_title=getattr(track, "sort_title", None),
            duration_ms=track_dur,
            track_number=getattr(track, "track_number", None),
            disc_number=getattr(track, "disc_number", None),
            added_at=getattr(track, "added_at", None),
            primary_artists=primary,
            featured_artists=featured,
            remixers=remixers,
            media=media_list,
            musicbrainz_id=getattr(track, "musicbrainz_id", None),
            isrc=getattr(track, "isrc", None),
            fingerprint=preloaded_fingerprint,
        )
