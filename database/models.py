#!/usr/bin/env python3

"""Compatibility re-export module for ORM models.

Alembic and external tooling can import from database.models while the
canonical implementations live in database.music_database.
"""

from .music_database import (
    Base,
    Artist,
    Album,
    Track,
    ArtistAlias,
    TrackAlias,
    ExternalIdentifier,
    AudioFingerprint,
    TrackAudioFeatures,
)

__all__ = [
    "Base",
    "Artist",
    "Album",
    "Track",
    "ArtistAlias",
    "TrackAlias",
    "ExternalIdentifier",
    "AudioFingerprint",
    "TrackAudioFeatures",
]
