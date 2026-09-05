import threading
import time
import urllib.parse
from collections.abc import Callable

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

    def wait(self, tokens: int = 1):
        """Block until tokens are available."""
        while True:
            with self._lock:
                now = time.time()
                elapsed = now - self.last_refill
                self.tokens = min(
                    self.capacity, self.tokens + elapsed * self.refill_rate
                )
                self.last_refill = now

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                # Calculate time to wait
                deficit = tokens - self.tokens
                wait_time = deficit / self.refill_rate

            if wait_time > 0:
                time.sleep(wait_time)


class GlobalRateLimiter:
    """A singleton managing token bucket rate limiters by domain."""

    _instance = None
    _init_lock = threading.Lock()

    def __new__(cls):
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.domains = {}
                cls._instance._domains_lock = threading.Lock()
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()

    def _get_domain(self, url: str) -> str:
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc
            if not domain:
                return "generic_fallback"
            return domain
        except Exception:
            return "generic_fallback"

    def wait_for_url(self, url: str, rps: float = 1.0):
        domain = self._get_domain(url)
        with self._domains_lock:
            if domain not in self.domains:
                # Capacity is set to 1.0 (burst size), refill_rate is rps
                self.domains[domain] = TokenBucketRateLimiter(
                    capacity=1.0, refill_rate=rps
                )
            bucket = self.domains[domain]

        bucket.wait(1)
