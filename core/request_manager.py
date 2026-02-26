"""
Core Request Manager: Centralized HTTP client with rate limiting and retry logic.

All providers and plugins MUST use this HTTP client for external requests.
This ensures:
- Consistent rate limiting across all providers
- Unified retry and backoff behavior
- Centralized configuration management
- Prevention of thundering herd problems
"""

from __future__ import annotations
import time
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable

import requests
from requests import Response

from core.settings import config_manager


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_backoff: float = 0.5  # seconds
    max_backoff: float = 8.0   # seconds
    jitter: float = 0.25       # +/- 25%


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    # Requests per second allowed; None means unlimited (provider handles it)
    requests_per_second: Optional[float] = None
    # Token bucket capacity (burst size) - Not currently used but good for future
    burst: int = 1


class HttpError(Exception):
    """Exception raised for HTTP errors."""
    def __init__(self, message: str, status: Optional[int] = None, response: Optional[Response] = None):
        super().__init__(message)
        self.status = status
        self.response = response


class RequestManager:
    """
    Central HTTP client with provider-configurable rate-limiting and retries.

    Rate limits and retry settings are looked up per provider via StorageService
    service config (e.g. service_config keys under `<provider>.rate_limit.*`).
    
    Usage by providers:
        In ProviderBase subclass:
        response = self.http.get(url)
        response = self.http.post(url, json=data)
    """

    def __init__(self, provider: str, session_factory: Optional[Callable[[], requests.Session]] = None,
                 retry: Optional[RetryConfig] = None, rate: Optional[RateLimitConfig] = None):
        """
        Initialize RequestManager for a specific provider.
        
        Args:
            provider: Provider name (used for config lookup)
            session_factory: Optional factory to create custom requests.Session
            retry: Optional RetryConfig; if None, loaded from storage config
            rate: Optional RateLimitConfig; if None, loaded from storage config
        """
        self.provider = provider
        self._session = (session_factory() if session_factory else requests.Session())
        self.retry = retry or RetryConfig()
        self.rate = rate or self._load_rate_limit_from_config()
        self._last_call_ts: float = 0.0

    def _load_rate_limit_from_config(self) -> RateLimitConfig:
        """Load rate limit configuration from config_manager."""
        # Try provider-specific rate config; keep it optional
        creds = config_manager.get_service_credentials(self.provider)
        rps = creds.get('rate_limit.requests_per_second') if creds else None
        try:
            return RateLimitConfig(requests_per_second=float(rps)) if rps is not None else RateLimitConfig()
        except (TypeError, ValueError):
            return RateLimitConfig()

    def _apply_rate_limit(self):
        """Apply rate limiting before making a request."""
        if not self.rate.requests_per_second or self.rate.requests_per_second <= 0:
            return
        min_interval = 1.0 / self.rate.requests_per_second
        now = time.time()
        delta = now - self._last_call_ts
        if delta < min_interval:
            time.sleep(min_interval - delta)
        self._last_call_ts = time.time()

    def _should_retry(self, resp: Optional[Response], exc: Optional[Exception], attempt: int) -> bool:
        """Determine if a request should be retried."""
        if attempt >= self.retry.max_retries:
            return False
        if exc is not None:
            return True  # network/timeout/etc.
        if resp is None:
            return False
        # Retry on 429 (Too Many Requests) and 5xx (Server Errors)
        if resp.status_code == 429 or 500 <= resp.status_code < 600:
            return True
        return False

    def _backoff_sleep(self, attempt: int):
        """Apply exponential backoff with jitter."""
        back = min(self.retry.base_backoff * (2 ** (attempt - 1)), self.retry.max_backoff)
        jitter_factor = 1 + random.uniform(-self.retry.jitter, self.retry.jitter)
        time.sleep(back * jitter_factor)

    def request(self, method: str, url: str, **kwargs) -> Response:
        """
        Make an HTTP request with automatic retries and rate limiting.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: URL to request
            **kwargs: Additional arguments to pass to requests.Session.request()
            
        Returns:
            Response object
            
        Raises:
            HttpError: If the request fails after all retries
        """
        attempt = 0
        last_exc: Optional[Exception] = None
        last_resp: Optional[Response] = None
        
        while True:
            attempt += 1
            try:
                self._apply_rate_limit()
                resp = self._session.request(method, url, timeout=kwargs.pop('timeout', 15), **kwargs)
                if not self._should_retry(resp, None, attempt):
                    if resp.status_code >= 400:
                        raise HttpError(f"HTTP {resp.status_code} for {url}", status=resp.status_code, response=resp)
                    return resp
                last_resp = resp
            except Exception as e:
                last_exc = e
                if not self._should_retry(None, e, attempt):
                    if isinstance(e, HttpError):
                        raise e
                    raise HttpError(f"HTTP error for {url}: {e}")
            
            self._backoff_sleep(attempt)

    def get(self, url: str, **kwargs) -> Response:
        """Make a GET request."""
        return self.request('GET', url, **kwargs)

    def post(self, url: str, **kwargs) -> Response:
        """Make a POST request."""
        return self.request('POST', url, **kwargs)

    def put(self, url: str, **kwargs) -> Response:
        """Make a PUT request."""
        return self.request('PUT', url, **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        """Make a DELETE request."""
        return self.request('DELETE', url, **kwargs)

    def patch(self, url: str, **kwargs) -> Response:
        """Make a PATCH request."""
        return self.request('PATCH', url, **kwargs)
