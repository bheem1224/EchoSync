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
import logging
from datetime import timedelta
from typing import Any, Callable, Optional, TypeVar, cast
from pathlib import Path
import hashlib

from time_utils import utc_now
from sqlalchemy import text
from database.music_database import MusicDatabase

logger = logging.getLogger(__name__)

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
            # Standard location
            # Note: This assumes relative path from this file
            # core/caching/provider_cache.py -> .../data/music_library.db
            db_path = Path(__file__).parent.parent.parent / "data" / "music_library.db"

        self.db_path = db_path
        self.db = MusicDatabase(db_path)
        self._ensure_table()

    def _ensure_table(self):
        """Ensure the cache table exists."""
        try:
            with self.db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS parsed_tracks (
                        raw_string TEXT PRIMARY KEY,
                        parsed_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ttl_expires_at TIMESTAMP
                    )
                """))
                conn.commit()
        except Exception as e:
            logger.error(f"Error ensuring cache table: {e}")

    def get(self, key: str, ttl_seconds: int = 3600) -> Optional[Any]:
        """
        Get value from cache if it exists and hasn't expired

        Args:
            key: Cache key
            ttl_seconds: Time-to-live in seconds

        Returns:
            Cached value or None if not found/expired
        """
        try:
            query = text("""
                SELECT parsed_json FROM parsed_tracks
                WHERE raw_string = :key
                AND (ttl_expires_at IS NULL OR ttl_expires_at > CURRENT_TIMESTAMP)
                LIMIT 1
            """)

            with self.db.engine.connect() as conn:
                result = conn.execute(query, {"key": key}).fetchone()

            if result:
                try:
                    return json.loads(result[0])
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Failed to decode cached value for key: {key}")
                    return None

            return None

        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """
        Store value in cache with TTL

        Args:
            key: Cache key
            value: Value to cache (should be JSON-serializable)
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize value to JSON
            json_value = json.dumps(value, default=str)

            # Calculate expiration time
            expires_at = utc_now() + timedelta(seconds=ttl_seconds)

            query = text("""
                INSERT OR REPLACE INTO parsed_tracks
                (raw_string, parsed_json, created_at, ttl_expires_at)
                VALUES (:key, :value, CURRENT_TIMESTAMP, :expires)
            """)

            with self.db.engine.connect() as conn:
                conn.execute(query, {
                    "key": key,
                    "value": json_value,
                    "expires": expires_at
                })
                conn.commit()
            return True

        except Exception as e:
            logger.error(f"Error storing in cache: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        try:
            query = text("DELETE FROM parsed_tracks WHERE raw_string = :key")
            with self.db.engine.connect() as conn:
                conn.execute(query, {"key": key})
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False

    def clear_expired(self) -> int:
        """
        Clear all expired entries

        Returns:
            Number of entries deleted
        """
        try:
            query = text("""
                DELETE FROM parsed_tracks
                WHERE ttl_expires_at IS NOT NULL
                AND ttl_expires_at <= CURRENT_TIMESTAMP
            """)
            with self.db.engine.connect() as conn:
                result = conn.execute(query)
                conn.commit()
                return result.rowcount
        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}")
            return 0

    def clear_all(self) -> bool:
        """
        Clear all cache entries

        Returns:
            True if successful
        """
        try:
            query = text("DELETE FROM parsed_tracks")
            with self.db.engine.connect() as conn:
                conn.execute(query)
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False


# Global cache instance
_cache_instance: Optional[ProviderCache] = None


def get_cache() -> ProviderCache:
    """Get or create global cache instance"""
    global _cache_instance
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
