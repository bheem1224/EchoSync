"""Two-tier capability RBAC, frozen Principal model, and manifest verification helpers."""

from __future__ import annotations

import base64
import contextlib
import contextvars
import hashlib
import hmac
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key

ADMIN_ROLE_PERMISSIONS: tuple[str, ...] = ("*",)

MEMBER_ROLE_PERMISSIONS: tuple[str, ...] = (
    "contract:tracks:read",
    "contract:albums:read",
    "contract:artists:read",
    "contract:playlists:read:own",
    "contract:playlists:edit:own",
    "contract:accounts:read:own",
    "contract:accounts:edit:own",
    "contract:media_profiles:read:family",
    "service:library:read",
    "service:playlist_sync:edit",
    "service:playlist_sync:share",
    "service:requests:enrich",
    "service:requests:auto_approve",
    "service:suggestions:read",
    "service:suggestions:enrich",
)

SYSTEM_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "admin": ADMIN_ROLE_PERMISSIONS,
    "member": MEMBER_ROLE_PERMISSIONS,
}


@dataclass(frozen=True)
class Principal:
    """Immutable authenticated security context for requests, API keys, plugins, and tasks."""

    user_id: str | None
    username: str
    principal_type: Literal["user", "api_key", "plugin", "system"]
    roles: tuple[str, ...] = ()
    scopes: frozenset[str] = frozenset()
    plugin_id: int | None = None
    auth_provider: str = "local"

    def has_scope(self, scope: str) -> bool:
        """Check whether this principal holds the requested capability scope."""
        clean_scope = scope.strip()
        if not clean_scope:
            return False

        # Plugins may never hold direct account secrets capability; must use OAuth sidecar.
        if self.principal_type == "plugin" and clean_scope.startswith("contract:accounts:secrets"):
            return False

        if "*" in self.scopes:
            return True

        if clean_scope in self.scopes:
            return True

        if clean_scope.endswith(":own"):
            any_variant = f"{clean_scope[:-4]}:any"
            if any_variant in self.scopes:
                return True

        for granted in self.scopes:
            if granted.endswith(":*") and clean_scope.startswith(granted[:-1]):
                return True

        return False

    def require(self, scope: str) -> None:
        """Enforce capability scope membership or raise PermissionError."""
        if not self.has_scope(scope):
            raise PermissionError(f"Missing required capability scope: {scope}")


_current_principal_var: contextvars.ContextVar[Principal | None] = contextvars.ContextVar(
    "echosync_current_principal",
    default=None,
)


def get_current_principal() -> Principal | None:
    """Return the active Principal bound to the current execution context, if any."""
    return _current_principal_var.get()


def set_current_principal(principal: Principal | None):
    """Bind a Principal to the current contextvar and return its reset token."""
    return _current_principal_var.set(principal)


@contextlib.contextmanager
def principal_scope(principal: Principal | None) -> Iterator[Principal | None]:
    """Context manager scoping an active Principal cleanly."""
    token = _current_principal_var.set(principal)
    try:
        yield principal
    finally:
        _current_principal_var.reset(token)


def enforce_contract_scope(principal: Principal | None, scope: str) -> None:
    """Enforce contract-tier RBAC when an explicit or context-bound Principal is active."""
    effective = principal if principal is not None else _current_principal_var.get()
    if effective is not None:
        effective.require(scope)


def _canonical_manifest_payload(manifest: dict[str, Any]) -> bytes:
    unsigned = {
        k: v
        for k, v in manifest.items()
        if k not in ("signature", "manifest_signature", "verified_source")
    }
    return json.dumps(unsigned, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _load_trusted_verify_key() -> Ed25519PublicKey | None:
    raw_key = os.getenv("ECHOSYNC_PLUGIN_VERIFY_KEY")
    if not raw_key:
        try:
            from core.settings import config_manager

            raw_key = config_manager.get("security.plugin_verify_public_key")
        except Exception:
            raw_key = None

    if not raw_key or not isinstance(raw_key, str):
        return None

    stripped = raw_key.strip()
    try:
        if stripped.startswith("-----BEGIN"):
            loaded = load_pem_public_key(stripped.encode("utf-8"))
            if isinstance(loaded, Ed25519PublicKey):
                return loaded
            return None
        key_bytes = base64.b64decode(stripped)
        if len(key_bytes) == 32:
            return Ed25519PublicKey.from_public_bytes(key_bytes)
    except Exception:
        return None
    return None


def verify_manifest_signature(manifest: dict[str, Any]) -> bool:
    """Cryptographically verify a plugin manifest signature if a trusted key is configured."""
    if not isinstance(manifest, dict):
        return False

    sig_b64 = manifest.get("manifest_signature") or manifest.get("signature")
    if not isinstance(sig_b64, str) or not sig_b64.strip():
        return False

    payload = _canonical_manifest_payload(manifest)
    pub_key = _load_trusted_verify_key()
    if pub_key is not None:
        try:
            sig_bytes = base64.b64decode(sig_b64.strip())
            pub_key.verify(sig_bytes, payload)
            return True
        except (InvalidSignature, ValueError):
            return False

    hmac_secret = os.getenv("ECHOSYNC_PLUGIN_SIGNING_SECRET")
    if hmac_secret:
        try:
            expected = hmac.new(hmac_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, sig_b64.strip().lower())
        except Exception:
            return False

    return False


def is_privileged_or_verified(manifest: dict[str, Any], *, trusted_core_path: bool = False) -> bool:
    """Determine verified/trusted plugin status strictly from cryptographic signature or core path.

    Self-asserted JSON fields such as `"verified_source": "official"` or `"privileged": true`
    are never trusted to grant verified bypass status.
    """
    if trusted_core_path:
        return True
    if not isinstance(manifest, dict):
        return False
    return verify_manifest_signature(manifest)
