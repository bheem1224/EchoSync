from __future__ import annotations
import time
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable

import requests
from requests import Response

from sdk.storage_service import get_storage_service


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_backoff: float = 0.5  # seconds
    max_backoff: float = 8.0   # seconds
    jitter: float = 0.25       # +/- 25%


@dataclass
class RateLimitConfig:
    # Requests per second allowed; None means unlimited (provider handles it)
    requests_per_second: Optional[float] = None


class HttpError(Exception):
    def __init__(self, message: str, status: Optional[int] = None, response: Optional[Response] = None):
        super().__init__(message)
        self.status = status
        self.response = response


class HttpClient:
    """HTTP client with provider-configurable rate-limiting and retries.

    Rate limits and retry settings are looked up per provider via StorageService
    service config (e.g. service_config keys under `<provider>.rate_limit.*`).
    """

    def __init__(self, provider: str, session_factory: Optional[Callable[[], requests.Session]] = None,
                 retry: Optional[RetryConfig] = None, rate: Optional[RateLimitConfig] = None):
        self.provider = provider
        self._session = (session_factory() if session_factory else requests.Session())
        self.retry = retry or RetryConfig()
        self.rate = rate or self._load_rate_limit_from_config()
        self._last_call_ts: float = 0.0

    def _load_rate_limit_from_config(self) -> RateLimitConfig:
        storage = get_storage_service()
        # Try provider-specific rate config; keep it optional
        rps = storage.get_service_config(self.provider, 'rate_limit.requests_per_second')
        try:
            return RateLimitConfig(requests_per_second=float(rps)) if rps is not None else RateLimitConfig()
        except (TypeError, ValueError):
            return RateLimitConfig()

    def _apply_rate_limit(self):
        if not self.rate.requests_per_second or self.rate.requests_per_second <= 0:
            return
        min_interval = 1.0 / self.rate.requests_per_second
        now = time.time()
        delta = now - self._last_call_ts
        if delta < min_interval:
            time.sleep(min_interval - delta)
        self._last_call_ts = time.time()

    def _should_retry(self, resp: Optional[Response], exc: Optional[Exception], attempt: int) -> bool:
        if attempt >= self.retry.max_retries:
            return False
        if exc is not None:
            return True  # network/timeout/etc.
        if resp is None:
            return False
        # Retry on 429 and 5xx
        if resp.status_code == 429 or 500 <= resp.status_code < 600:
            return True
        return False

    def _backoff_sleep(self, attempt: int):
        back = min(self.retry.base_backoff * (2 ** (attempt - 1)), self.retry.max_backoff)
        jitter_factor = 1 + random.uniform(-self.retry.jitter, self.retry.jitter)
        time.sleep(back * jitter_factor)

    def request(self, method: str, url: str, **kwargs) -> Response:
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
        return self.request('GET', url, **kwargs)

    def post(self, url: str, **kwargs) -> Response:
        return self.request('POST', url, **kwargs)

    def put(self, url: str, **kwargs) -> Response:
        return self.request('PUT', url, **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        return self.request('DELETE', url, **kwargs)
