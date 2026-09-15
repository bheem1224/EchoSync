"""OAuth models and session structures for centralized OAuth sidecar."""

from __future__ import annotations

import concurrent.futures
import dataclasses
import time
from collections.abc import Callable
from typing import Any


def validate_plugin_id_int(plugin_id: Any) -> int:
    """Strictly validate that plugin_id is an unsigned 32-bit integer."""
    if not isinstance(plugin_id, int) or isinstance(plugin_id, bool):
        raise TypeError(f"Plugin ID must be an integer, got {type(plugin_id).__name__} ({plugin_id!r})")
    if not (0 <= plugin_id <= 0xFFFFFFFF):
        raise ValueError(f"Plugin ID must be an unsigned 32-bit integer (0 <= id <= 4294967295), got {plugin_id}")
    return plugin_id


@dataclasses.dataclass
class OAuthSession:
    """Internal session state held by the centralized OAuth sidecar."""

    session_id: str
    plugin_id: int
    provider: str
    auth_url: str
    token_url: str
    client_id: str
    redirect_uri: str
    account_id: int | None = None
    client_secret: str | None = None
    code_verifier: str | None = None
    code_challenge: str | None = None
    scopes: str | list[str] | None = None
    on_token: Callable[[dict[str, Any]], None] | None = None
    on_error: Callable[[str], None] | None = None
    future: concurrent.futures.Future = dataclasses.field(default_factory=concurrent.futures.Future)
    created_at: float = dataclasses.field(default_factory=time.time)
    ttl_seconds: int = 600

    def __post_init__(self):
        self.plugin_id = validate_plugin_id_int(self.plugin_id)

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds


@dataclasses.dataclass
class OAuthSessionHandle:
    """Public handle returned to calling plugins/routes."""

    session_id: str
    auth_url: str
    future: concurrent.futures.Future

    def wait_for_tokens(self, timeout: float = 300.0) -> dict[str, Any]:
        """Block and wait for the centralized sidecar to resolve tokens in-memory."""
        return self.future.result(timeout=timeout)
