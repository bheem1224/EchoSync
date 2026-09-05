#!/usr/bin/env python3

"""
Echosync Database Module

This module provides database functionality for storing and managing
music library metadata from Plex. It includes:

- SQLite database management for artists, albums, and tracks
- Singleton database access pattern
- Data models for database entities
- Search and query capabilities

Usage:
    from database import get_database

    db = get_database()
    stats = db.get_statistics()
"""

from .engine import ensure_writer, execute_write, execute_write_sql
from .music_database import (
    Album,
    Artist,
    AudioFingerprint,
    Base,
    ExternalIdentifier,
    MusicDatabase,
    Track,
    close_database,
    get_database,
)


def _canonicalize_path(p: str) -> str:
    import os

    return os.path.normpath(os.path.abspath(str(p)))


__all__ = [
    "Album",
    "Artist",
    "AudioFingerprint",
    "Base",
    "ExternalIdentifier",
    "MusicDatabase",
    "Track",
    "_canonicalize_path",
    "close_database",
    "ensure_writer",
    "execute_write",
    "execute_write_sql",
    "get_database",
]

__version__ = "1.0.0"
