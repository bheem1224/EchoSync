"""
SDK HTTP Client - DEPRECATED STUB

This module is a stub for backward compatibility only.
All code should use core.request_manager.RequestManager instead.

This stub redirects imports to the new request_manager module.
"""

from typing import Optional
import warnings

# Import from the new location and re-export for backward compatibility
from core.request_manager import (
    RequestManager,
    RetryConfig,
    RateLimitConfig,
    HttpError
)

warnings.warn(
    "sdk.http_client is deprecated. Use core.request_manager.RequestManager instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    'RequestManager',
    'RetryConfig',
    'RateLimitConfig',
    'HttpError',
    'HttpClient'
]


# Alias for backward compatibility
class HttpClient(RequestManager):
    """
    Deprecated alias for RequestManager.
    
    Use RequestManager from core.request_manager instead.
    """
    def __init__(self, provider: str, retry: Optional[RetryConfig] = None, rate: Optional[RateLimitConfig] = None):
        """Initialize HTTP client (now just RequestManager)."""
        warnings.warn(
            "HttpClient is deprecated. Use core.request_manager.RequestManager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # Call parent __init__ with correct parameters
        super().__init__(provider=provider, retry=retry, rate=rate)
