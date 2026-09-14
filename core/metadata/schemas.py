"""Canonical models for EchoSync metadata resolution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

ResolutionMethod = Literal["local_cache", "acoustid", "isrc", "text_waterfall", "embedded_mbid"]


@dataclass
class EntityAliasProposal:
    """Proposal for an entity alias (transliteration, translation, or romanization)."""

    entity_type: Literal["artist", "track_artist", "track", "album"]
    value: str  # The localized, romanized, or sort string
    language: str  # ISO 639-1 / 639-2: e.g. "ja", "ko", "zh", "ru"
    script: str  # ISO 15924: e.g. "Jpan", "Hang", "Hani", "Cyrl", "Latn"
    alias_type: Literal["transliteration", "translation", "official_romanization", "sort_name"]
    entity_id: str | int | None = None  # Target database ID or MBID

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AliasResolutionContext:
    """Context passed to the resolve_entity_aliases plugin hook."""

    sync_id: str
    media_id: str
    title: str  # Native script
    artist: str  # Native script
    album: str | None = None  # Native script
    musicbrainz_track_id: str | None = None
    artist_mbids: list[str] = field(default_factory=list)
    track_artist_ids: list[int] = field(default_factory=list)


@dataclass
class ResolutionRequest:
    """Input contract for resolving track metadata."""

    media_id: str
    file_path: Path
    sync_id: str | None = None
    baseline_title: str | None = None
    baseline_artist: str | None = None
    baseline_album: str | None = None
    baseline_isrc: str | None = None
    chromaprint: str | None = None
    duration: float | None = None
    duration_ms: int | None = None
    ignore_embedded_mbid: bool = False
    ignore_cache: bool = False


@dataclass
class ResolutionResult:
    """Canonical output contract for resolved metadata."""

    media_id: str
    title: str  # Original native script preserved
    artist: str  # Original native script preserved
    confidence_score: float
    resolution_method: ResolutionMethod
    duration_ms: int = 0  # Extracted from physical audio stream
    sync_id: str | None = None
    album: str | None = None  # Original native script preserved
    year: int | None = None
    track_number: int | None = None
    disc_number: int | None = None
    musicbrainz_track_id: str | None = None
    musicbrainz_release_id: str | None = None
    acoustid_id: str | None = None
    chromaprint: str | None = None
    isrc: str | None = None
    extra_metadata: dict[str, Any] | None = None
    musicbrainz_artist_id: str | None = None
    track_artist_ids: list[int] = field(default_factory=list)
    alias_proposals: list[EntityAliasProposal] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if resolution achieved a valid MusicBrainz recording match with confidence."""
        return bool(self.musicbrainz_track_id and self.confidence_score > 0.0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary matching legacy identify_file metadata format."""
        mbid = self.musicbrainz_track_id
        res = {
            "sync_id": self.sync_id,
            "media_id": self.media_id,
            "title": self.title,
            "raw_title": self.title,
            "display_title": self.title,
            "artist": self.artist,
            "artist_name": self.artist,
            "album": self.album,
            "album_title": self.album,
            "year": self.year,
            "release_year": self.year,
            "date": str(self.year) if self.year is not None else None,
            "track_number": self.track_number,
            "disc_number": self.disc_number,
            "musicbrainz_track_id": mbid,
            "musicbrainz_id": mbid,
            "recording_id": mbid,
            "musicbrainz_release_id": self.musicbrainz_release_id,
            "release_id": self.musicbrainz_release_id,
            "acoustid_id": self.acoustid_id,
            "chromaprint": self.chromaprint,
            "duration_ms": self.duration_ms,
            "duration": (self.duration_ms / 1000.0) if self.duration_ms else None,
            "isrc": self.isrc,
            "confidence_score": self.confidence_score,
            "resolution_method": self.resolution_method,
        }
        if self.extra_metadata:
            res.update(self.extra_metadata)
        return res
