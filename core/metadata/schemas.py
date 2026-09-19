"""Canonical models for EchoSync metadata resolution."""

from __future__ import annotations

import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from core.db.echo_sync_track import EchosyncTrack, EchosyncMedia

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
    prefer_studio_album: bool = True
    track: EchosyncTrack | None = None


class ResolutionResult(EchosyncTrack):
    """Deprecated: EchosyncTrack is the universal canonical transport model.

    ResolutionResult is maintained for backward compatibility.
    """

    def __init__(
        self,
        media_id: str = "",
        title: str = "",
        artist: str = "",
        confidence_score: float = 0.0,
        resolution_method: str = "text_waterfall",
        duration_ms: int = 0,
        sync_id: str | None = None,
        album: str | None = None,
        year: int | None = None,
        track_number: int | None = None,
        disc_number: int | None = None,
        musicbrainz_track_id: str | None = None,
        musicbrainz_release_id: str | None = None,
        acoustid_id: str | None = None,
        chromaprint: str | None = None,
        isrc: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
        musicbrainz_artist_id: str | None = None,
        track_artist_ids: list[int] | None = None,
        alias_proposals: list[Any] | None = None,
        **kwargs: Any,
    ):
        warnings.warn(
            "ResolutionResult is deprecated; use EchosyncTrack as the canonical model.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            raw_title=title or kwargs.get("raw_title", ""),
            artist_name=artist or kwargs.get("artist_name", ""),
            album_title=album or kwargs.get("album_title", "") or "",
            sync_id=sync_id,
            duration=duration_ms or kwargs.get("duration", 0),
            track_number=track_number,
            disc_number=disc_number,
            release_year=year,
            musicbrainz_id=musicbrainz_track_id or kwargs.get("musicbrainz_id"),
            mb_release_id=musicbrainz_release_id or kwargs.get("mb_release_id"),
            acoustid_id=acoustid_id,
            fingerprint=chromaprint or kwargs.get("fingerprint"),
            isrc=isrc,
            confidence_score=confidence_score,
            resolution_method=resolution_method,
            alias_proposals=alias_proposals or [],
            extra_metadata=extra_metadata or {},
            media=[EchosyncMedia(media_id=media_id)] if media_id else [],
        )
