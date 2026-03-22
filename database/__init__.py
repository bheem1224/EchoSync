#!/usr/bin/env python3

"""
SoulSync Database Module

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

from .music_database import (
    MusicDatabase,
    Base,
    Artist,
    Album,
    Track,
    ExternalIdentifier,
    AudioFingerprint,
    get_database,
    close_database
)

from .bulk_operations import LibraryManager

from .engine import (
    execute_write,
    execute_write_sql,
    ensure_writer
)

__all__ = [
    'MusicDatabase',
    'Base',
    'Artist',
    'Album',
    'Track',
    'ExternalIdentifier',
    'AudioFingerprint',
    'LibraryManager',
    'get_database',
    'close_database',
    'execute_write',
    'execute_write_sql',
    'ensure_writer'
]

__version__ = '1.0.0'
