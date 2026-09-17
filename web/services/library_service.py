"""Compatibility shim re-exporting library service symbols from services.library_service."""

from services.library_service import (
    LibraryAdapter,
    _get_database_size_mb,
    get_database_stats,
    invalidate_stats_cache,
    logger,
)

__all__ = [
    "LibraryAdapter",
    "_get_database_size_mb",
    "get_database_stats",
    "invalidate_stats_cache",
    "logger",
]
