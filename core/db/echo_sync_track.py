"""Compatibility re-export module for canonical immutable DTOs in `core.models`."""

from core.models import (
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
