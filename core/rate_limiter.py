"""
Rate Limiter Module for Echosync

This module provides a generic rate limiter and a decorator for rate-limiting function calls.
"""

import time
import asyncio
import threading
from typing import Callable, Optional

# Global dictionary to track last call times for the decorator
_last_call = {}
_last_call_lock = threading.Lock()

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
            with _last_call_lock:
                prev = _last_call.get(key, 0)
                if now - prev < min_interval_sec:
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
        while True:
            self._clean_old_timestamps()
            if len(self.timestamps) < self.max_requests:
                break
            oldest_timestamp = self.timestamps[0]
            wait_time = oldest_timestamp + self.window_seconds - time.time()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            # Re-check after sleep: another coroutine may have consumed a slot
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


class TokenBucketRateLimiter:
    """A standard thread-safe token bucket rate limiter for API requests."""
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.time()
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
