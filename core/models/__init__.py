"""Canonical passive immutable domain DTO models package."""

from core.models.entities import (
    DISTINCT_VERSION_TYPES,
    SUBSTITUTABLE_VERSION_TYPES,
    ArtistCredit,
    DownloadStatus,
    EchosyncAlbum,
    EchosyncArtist,
    EchosyncMedia,
    EchosyncTrack,
    QualityTag,
    classify_version_type,
)

__all__ = [
    "ArtistCredit",
    "DISTINCT_VERSION_TYPES",
    "DownloadStatus",
    "EchosyncAlbum",
    "EchosyncArtist",
    "EchosyncMedia",
    "EchosyncTrack",
    "QualityTag",
    "SUBSTITUTABLE_VERSION_TYPES",
    "classify_version_type",
]
