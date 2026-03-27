"""
Caching layer for provider queries and metadata lookups

This module provides:
1. @provider_cache decorator for caching function results with TTL
2. Database-backed cache using music_library.db
3. Automatic TTL expiration handling
4. Cache invalidation methods
"""

import functools
import json
import os
from core.tiered_logger import get_logger
import threading
from datetime import timedelta
from typing import Any, Callable, Optional, TypeVar, cast
from pathlib import Path
import hashlib

from time_utils import utc_now
from database.music_database import MusicDatabase, ParsedTrack

logger = get_logger(__name__)

# Type variable for generic decorator
F = TypeVar('F', bound=Callable[..., Any])


class ProviderCache:
    """Cache manager for provider queries using database backend"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize cache manager

        Args:
            db_path: Path to music_library.db (defaults to standard location)
        """
        if db_path is None:
            data_dir = os.getenv("SOULSYNC_DATA_DIR")
            base = Path(data_dir) if data_dir else Path("data")
            db_path = base / "music_library.db"

        self.db_path = db_path
        self.db = MusicDatabase(db_path)
        # ParsedTrack is part of Base; create_all() is idempotent.
        self.db.create_all()

    def get(self, key: str, ttl_seconds: int = 3600) -> Optional[Any]:
        """
        Get value from cache if it exists and hasn't expired.
        """
        try:
            now = utc_now()
            with self.db.session_scope() as session:
                row = (
                    session.query(ParsedTrack)
                    .filter(
                        ParsedTrack.raw_string == key,
                        (ParsedTrack.ttl_expires_at == None)  # noqa: E711
                        | (ParsedTrack.ttl_expires_at > now),
                    )
                    .first()
                )
            if row is None:
                return None
            try:
                return json.loads(row.parsed_json)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to decode cached value for key: {key}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """
        Store value in cache with TTL.
        """
        try:
            json_value = json.dumps(value, default=str)
            expires_at = utc_now() + timedelta(seconds=ttl_seconds)
            with self.db.session_scope() as session:
                row = session.query(ParsedTrack).filter(ParsedTrack.raw_string == key).first()
                if row is None:
                    row = ParsedTrack(
                        raw_string=key,
                        parsed_json=json_value,
                        ttl_expires_at=expires_at,
                    )
                    session.add(row)
                else:
                    row.parsed_json = json_value
                    row.ttl_expires_at = expires_at
            return True
        except Exception as e:
            logger.error(f"Error storing in cache: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        """
        try:
            with self.db.session_scope() as session:
                session.query(ParsedTrack).filter(ParsedTrack.raw_string == key).delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False

    def clear_expired(self) -> int:
        """
        Clear all expired entries.
        """
        try:
            now = utc_now()
            with self.db.session_scope() as session:
                count = (
                    session.query(ParsedTrack)
                    .filter(
                        ParsedTrack.ttl_expires_at != None,  # noqa: E711
                        ParsedTrack.ttl_expires_at <= now,
                    )
                    .delete()
                )
            return count
        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}")
            return 0

    def clear_all(self) -> bool:
        """
        Clear all cache entries.
        """
        try:
            with self.db.session_scope() as session:
                session.query(ParsedTrack).delete()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False


# Global cache instance
_cache_instance: Optional[ProviderCache] = None
_cache_lock = threading.Lock()


def get_cache() -> ProviderCache:
    """Get or create global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = ProviderCache()
    return _cache_instance


def provider_cache(ttl_seconds: int = 3600, key_prefix: str = ""):
    """
    Decorator for caching provider query results

    Args:
        ttl_seconds: Time-to-live for cache entries (default 1 hour)
        key_prefix: Optional prefix for cache keys to avoid collisions

    Example:
        @provider_cache(ttl_seconds=7200)
        def get_track_metadata(track_id: str) -> dict:
            # ... expensive metadata lookup ...
            return metadata

        # First call queries the provider
        result = get_track_metadata("spotify:123")

        # Second call returns cached result
        result = get_track_metadata("spotify:123")
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cache = get_cache()

            # Generate cache key from function name, args, and kwargs
            key_parts = [func.__module__, func.__name__, key_prefix]

            # Include args and kwargs in key (serialize to string)
            try:
                args_str = json.dumps(args, default=str)
                kwargs_str = json.dumps(kwargs, default=str, sort_keys=True)
                key_parts.append(args_str)
                key_parts.append(kwargs_str)
            except Exception:
                # Fallback: use repr if JSON fails
                key_parts.append(repr(args))
                key_parts.append(repr(kwargs))

            # Create hash of key to avoid overly long cache keys
            key_str = "|".join(key_parts)
            cache_key = hashlib.md5(key_str.encode()).hexdigest()

            # Try to get from cache
            cached_result = cache.get(cache_key, ttl_seconds)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # Not in cache - call function
            logger.debug(f"Cache miss for {func.__name__}, calling function")
            result = func(*args, **kwargs)

            # Store in cache
            if result is not None:
                cache.set(cache_key, result, ttl_seconds)

            return result

        return cast(F, wrapper)

    return decorator


def invalidate_cache_for(pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern

    Args:
        pattern: SQL LIKE pattern for cache keys

    Returns:
        Number of entries deleted
    """
    cache = get_cache()
    try:
        query = text("DELETE FROM parsed_tracks WHERE raw_string LIKE :pattern")
        with cache.db.engine.connect() as conn:
            result = conn.execute(query, {"pattern": pattern})
            conn.commit()
            logger.info(f"Invalidated cache entries matching: {pattern}")
            return result.rowcount
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return 0


def clear_cache() -> bool:
    """Clear all cache entries"""
    cache = get_cache()
    return cache.clear_all()


def cleanup_expired_cache() -> int:
    """Clean up expired cache entries"""
    cache = get_cache()
    return cache.clear_expired()
