"""Provider-agnostic OIDC PKCE S256, JWKS verification, and JIT provisioning."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import threading
import time
import urllib.parse
from typing import Any

import httpx

from core.security.tokens import verify_jwt_jwks


def generate_pkce_pair() -> tuple[str, str]:
    """Generate a cryptographic `(code_verifier, code_challenge)` PKCE S256 pair."""
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


class OIDCManager:
    """Stateless-config OIDC login + callback verifier with ephemeral PKCE challenge cache."""

    def __init__(self, state_ttl_seconds: int = 600) -> None:
        self._state_ttl_seconds = state_ttl_seconds
        self._lock = threading.Lock()
        self._pending_states: dict[str, dict[str, Any]] = {}
        self._discovery_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def get_config(self) -> dict[str, Any]:
        """Resolve OIDC configuration from config_manager and environment variables."""
        from core.settings import config_manager

        enabled = bool(config_manager.get("security.oidc.enabled", False)) or (
            os.getenv("ECHOSYNC_OIDC_ENABLED", "").strip().lower() in ("1", "true", "yes")
        )
        issuer_url = (
            os.getenv("ECHOSYNC_OIDC_ISSUER_URL") or config_manager.get("security.oidc.issuer_url") or ""
        ).rstrip("/")
        client_id = os.getenv("ECHOSYNC_OIDC_CLIENT_ID") or config_manager.get("security.oidc.client_id") or ""
        client_secret = (
            os.getenv("ECHOSYNC_OIDC_CLIENT_SECRET") or config_manager.get("security.oidc.client_secret") or ""
        )
        redirect_uri = (
            os.getenv("ECHOSYNC_OIDC_REDIRECT_URI") or config_manager.get("security.oidc.redirect_uri") or ""
        )
        scopes = os.getenv("ECHOSYNC_OIDC_SCOPES") or config_manager.get(
            "security.oidc.scopes", "openid profile email"
        )
        groups_claim = os.getenv("ECHOSYNC_OIDC_GROUPS_CLAIM") or config_manager.get(
            "security.oidc.groups_claim", "groups"
        )
        username_claim = os.getenv("ECHOSYNC_OIDC_USERNAME_CLAIM") or config_manager.get(
            "security.oidc.username_claim", "preferred_username"
        )
        group_role_map = config_manager.get("security.oidc.group_role_map", {}) or {}
        return {
            "enabled": bool(enabled and issuer_url and client_id),
            "issuer_url": issuer_url,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "groups_claim": groups_claim,
            "username_claim": username_claim,
            "group_role_map": group_role_map,
            "authorization_endpoint": config_manager.get("security.oidc.authorization_endpoint") or "",
            "token_endpoint": config_manager.get("security.oidc.token_endpoint") or "",
            "jwks_uri": config_manager.get("security.oidc.jwks_uri") or "",
        }

    def is_enabled(self) -> bool:
        return bool(self.get_config()["enabled"])

    def fetch_discovery(self, issuer_url: str, *, discovery_override: dict[str, Any] | None = None) -> dict[str, Any]:
        if discovery_override is not None:
            return discovery_override
        now = time.time()
        cached = self._discovery_cache.get(issuer_url)
        if cached and cached[0] > now:
            return cached[1]
        url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
        doc = resp.json()
        self._discovery_cache[issuer_url] = (now + 300, doc)
        return doc

    def fetch_jwks(self, jwks_uri: str, *, jwks_override: dict[str, Any] | None = None) -> dict[str, Any]:
        if jwks_override is not None:
            return jwks_override
        now = time.time()
        cached = self._jwks_cache.get(jwks_uri)
        if cached and cached[0] > now:
            return cached[1]
        resp = httpx.get(jwks_uri, timeout=10.0)
        resp.raise_for_status()
        doc = resp.json()
        self._jwks_cache[jwks_uri] = (now + 300, doc)
        return doc

    def start_login(
        self,
        *,
        redirect_uri: str | None = None,
        discovery_override: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Build an OIDC PKCE authorization redirect URL and persist single-use state."""
        cfg = self.get_config()
        if not cfg["enabled"]:
            raise ValueError("OIDC authentication is not configured or enabled.")

        auth_endpoint = cfg["authorization_endpoint"]
        if not auth_endpoint:
            discovery = self.fetch_discovery(cfg["issuer_url"], discovery_override=discovery_override)
            auth_endpoint = discovery["authorization_endpoint"]

        effective_redirect = redirect_uri or cfg["redirect_uri"]
        if not effective_redirect:
            raise ValueError("OIDC redirect_uri is required.")

        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier, challenge = generate_pkce_pair()

        now = time.time()
        with self._lock:
            expired_keys = [k for k, v in self._pending_states.items() if v["expires_at"] <= now]
            for k in expired_keys:
                self._pending_states.pop(k, None)
            self._pending_states[state] = {
                "code_verifier": verifier,
                "nonce": nonce,
                "redirect_uri": effective_redirect,
                "expires_at": now + self._state_ttl_seconds,
            }

        params = {
            "response_type": "code",
            "client_id": cfg["client_id"],
            "redirect_uri": effective_redirect,
            "scope": cfg["scopes"],
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return f"{auth_endpoint}?{urllib.parse.urlencode(params)}", state

    def complete_callback(
        self,
        *,
        code: str,
        state: str,
        discovery_override: dict[str, Any] | None = None,
        jwks_override: dict[str, Any] | None = None,
        token_response_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Exchange authorization code with PKCE verifier, verify ID token, and JIT provision user."""
        cfg = self.get_config()
        if not cfg["enabled"]:
            raise ValueError("OIDC authentication is not configured or enabled.")

        with self._lock:
            state_entry = self._pending_states.pop(state, None)

        if not state_entry or state_entry["expires_at"] <= time.time():
            raise ValueError("Invalid or expired OIDC state.")

        discovery = (
            discovery_override
            if discovery_override is not None
            else (
                {
                    "token_endpoint": cfg["token_endpoint"],
                    "jwks_uri": cfg["jwks_uri"],
                    "issuer": cfg["issuer_url"],
                }
                if cfg["token_endpoint"] and cfg["jwks_uri"]
                else self.fetch_discovery(cfg["issuer_url"])
            )
        )

        if token_response_override is not None:
            token_data = token_response_override
        else:
            form_payload = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": state_entry["redirect_uri"],
                "client_id": cfg["client_id"],
                "code_verifier": state_entry["code_verifier"],
            }
            if cfg["client_secret"]:
                form_payload["client_secret"] = cfg["client_secret"]
            token_resp = httpx.post(discovery["token_endpoint"], data=form_payload, timeout=15.0)
            token_resp.raise_for_status()
            token_data = token_resp.json()

        id_token = token_data.get("id_token")
        if not id_token:
            raise ValueError("OIDC token endpoint response omitted id_token.")

        jwks = self.fetch_jwks(discovery.get("jwks_uri", ""), jwks_override=jwks_override)
        issuer = discovery.get("issuer") or cfg["issuer_url"]
        claims = verify_jwt_jwks(
            id_token,
            jwks,
            audience=cfg["client_id"],
            issuer=issuer,
        )

        if claims.get("nonce") != state_entry["nonce"]:
            raise ValueError("ID token nonce mismatch.")

        sub = str(claims.get("sub") or "").strip()
        if not sub:
            raise ValueError("ID token missing 'sub' claim.")

        username_claim = cfg["username_claim"]
        raw_username = (
            claims.get(username_claim)
            or claims.get("preferred_username")
            or claims.get("email")
            or sub
        )
        username = str(raw_username).strip()

        groups_claim = cfg["groups_claim"]
        raw_groups = claims.get(groups_claim) or []
        if isinstance(raw_groups, str):
            groups = [g.strip() for g in raw_groups.split(",") if g.strip()]
        elif isinstance(raw_groups, list):
            groups = [str(g).strip() for g in raw_groups if g]
        else:
            groups = []

        role_map = cfg["group_role_map"] or {}
        mapped_roles: list[str] = []
        for grp in groups:
            role_target = role_map.get(grp)
            if isinstance(role_target, str) and role_target.strip():
                mapped_roles.append(role_target.strip())
            elif isinstance(role_target, list):
                mapped_roles.extend(str(r).strip() for r in role_target if r)

        if not mapped_roles:
            mapped_roles = ["member"]

        from database.config_database import get_config_database

        return get_config_database().provision_or_link_oidc_user(
            oidc_subject=sub,
            username=username,
            role_names=list(dict.fromkeys(mapped_roles)),
        )


oidc_manager = OIDCManager()
