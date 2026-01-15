"""
Rate Limiter Module for SoulSync

This module provides a generic rate limiter and a decorator for rate-limiting function calls.
"""

import time
import asyncio
from typing import Callable, Optional

# Global dictionary to track last call times for the decorator
_last_call = {}

def rate_limited(key: str, min_interval_sec: float) -> Callable:
    """
    Decorator to rate limit a function call based on a key and interval.

    Args:
        key: A unique identifier for the rate limit bucket.
        min_interval_sec: Minimum time in seconds between calls.

    Returns:
        A dictionary {"rate_limited": True} if limited, otherwise the function result.
    """
    def decorator(fn):
        def wrapper(*args, **kwargs):
            now = time.time()
            prev = _last_call.get(key, 0)
            if now - prev < min_interval_sec:
                # skip/deny for now; production should return 429 or handle retry
                return {"rate_limited": True}
            _last_call[key] = now
            return fn(*args, **kwargs)
        return wrapper
    return decorator

class RateLimiter:
    """
    A generic token-bucket style rate limiter (window-based).
    """
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.timestamps = []

    async def wait(self):
        """Wait if necessary to respect rate limiting."""
        self._clean_old_timestamps()
        if len(self.timestamps) >= self.max_requests:
            oldest_timestamp = self.timestamps[0]
            wait_time = oldest_timestamp + self.window_seconds - time.time()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self._clean_old_timestamps()
        self.timestamps.append(time.time())

    def _clean_old_timestamps(self):
        """Remove timestamps older than the rate limit window."""
        cutoff_time = time.time() - self.window_seconds
        self.timestamps = [ts for ts in self.timestamps if ts > cutoff_time]

    def get_status(self) -> dict:
        """Get current rate limiting status."""
        self._clean_old_timestamps()
        return {
            'requests_in_window': len(self.timestamps),
            'max_requests': self.max_requests,
            'window_seconds': self.window_seconds,
            'remaining_requests': max(0, self.max_requests - len(self.timestamps))
        }
