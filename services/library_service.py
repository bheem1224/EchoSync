"""Centralized Library Service for managing library statistics, adapters, and reactive cache invalidation."""

import copy
from pathlib import Path
import threading
import time
from typing import Any

from core.settings import config_manager
from core.task_manager.task_queue import db_read_lease
from core.tiered_logger import get_logger
from database.music_database import get_database

logger = get_logger("library_service")

_cache_lock = threading.Lock()
_cached_stats: dict[str, Any] | None = None
_cached_stats_timestamp: float = 0.0
STATS_CACHE_TTL: float = 300.0  # 5 minutes


def _get_database_size_mb() -> float:
    """Get the size of the Echosync music database in MB."""
    try:
        db_path = (
            config_manager.get("media_database_path") or Path(__file__).parent.parent / "config" / "media_library.db"
        )
        if isinstance(db_path, str):
            db_path = Path(db_path)
        if db_path.exists():
            size_bytes = db_path.stat().st_size
            return round(size_bytes / (1024 * 1024), 2)
    except Exception as e:
        logger.warning(f"Could not get database size: {e}")
    return 0.0


def invalidate_stats_cache() -> None:
    """Invalidate the in-memory database library statistics cache."""
    global _cached_stats, _cached_stats_timestamp
    with _cache_lock:
        _cached_stats = None
        _cached_stats_timestamp = 0.0
    logger.debug("Library database stats cache invalidated.")


def get_database_stats(force_refresh: bool = False) -> dict[str, Any]:
    """Fetch library statistics with in-memory TTL caching and db_read_lease."""
    global _cached_stats, _cached_stats_timestamp
    now = time.time()
    with _cache_lock:
        if not force_refresh and _cached_stats is not None and (now - _cached_stats_timestamp < STATS_CACHE_TTL):
            return copy.deepcopy(_cached_stats)

    with db_read_lease("get_database_stats"):
        db_tracks = 0
        db_artists = 0
        db_albums = 0
        db_size_mb = _get_database_size_mb()

        try:
            db = get_database()
            logger.debug("Fetching fresh database stats from database...")
            db_artists = db.count_artists()
            db_albums = db.count_albums()
            db_tracks = db.count_tracks()

            logger.debug(f"Database stats retrieved: {db_tracks} tracks, {db_artists} artists, {db_albums} albums")
        except Exception as e:
            logger.error(f"Error getting database stats: {e}", exc_info=True)

        stats = {
            "synced_tracks": db_tracks,
            "synced_artists": db_artists,
            "synced_albums": db_albums,
            "total_tracks": db_tracks,
            "total_artists": db_artists,
            "total_albums": db_albums,
            "database_size_mb": db_size_mb,
        }

        with _cache_lock:
            _cached_stats = stats
            _cached_stats_timestamp = time.time()

        return copy.deepcopy(stats)


class LibraryAdapter:
    """Library adapter for summarizing library servers and canonical tracks."""

    def overview(self, force_refresh: bool = False) -> dict[str, Any]:
        """Summarize available library servers and canonical tracks.

        Returns:
            dict: servers, stats, tracks, artists, albums
        """
        stats = get_database_stats(force_refresh=force_refresh)
        db_tracks = stats.get("total_tracks", 0)
        db_artists = stats.get("total_artists", 0)
        db_albums = stats.get("total_albums", 0)

        active_server = config_manager.get("active_media_server", "plex")

        servers = [
            {
                "name": active_server,
                "type": "media_server",
                "metadata_richness": "standard",
                "track_count": db_tracks,
                "artist_count": db_artists,
                "album_count": db_albums,
                "is_active": True,
            }
        ]

        return {
            "servers": servers,
            "stats": stats,
            "tracks": [],
            "artists": [],
            "albums": [],
        }


def _handle_event_invalidation(payload: dict, **kwargs) -> None:
    """Reactively invalidate stats cache on library, sync, or media ingestion events."""
    event_name = str(payload.get("event") or "").lower()
    mutation_keywords = (
        "library",
        "track",
        "album",
        "artist",
        "database",
        "sync",
        "import",
        "ingest",
        "scan",
    )
    if any(kw in event_name for kw in mutation_keywords):
        invalidate_stats_cache()


try:
    from core.event_bus import event_bus

    event_bus.subscribe("*", _handle_event_invalidation)
except Exception as exc:
    logger.debug(f"Could not subscribe to event_bus for library stats invalidation: {exc}")
