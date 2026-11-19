"""FastAPI (and legacy Flask plugin proxy) authentication & RBAC dependencies."""

from __future__ import annotations

import functools
from typing import Any

from fastapi import Depends, HTTPException, Request

from core.security.rbac import SYSTEM_ROLE_PERMISSIONS, Principal
from core.security.tokens import verify_auth_token
from database.config_database import get_config_database


def _build_principal_from_user_dict(
    user: dict[str, Any],
    *,
    principal_type: str = "user",
    override_scopes: list[str] | tuple[str, ...] | None = None,
) -> Principal:
    roles = tuple(user.get("roles") or ())
    if override_scopes is not None:
        scopes = frozenset(str(s) for s in override_scopes if s)
    else:
        raw_scopes = set(user.get("scopes") or ())
        for role_name in roles:
            raw_scopes.update(SYSTEM_ROLE_PERMISSIONS.get(role_name, ()))
        scopes = frozenset(raw_scopes)
    return Principal(
        user_id=user.get("id"),
        username=user.get("username") or "",
        principal_type=principal_type,  # type: ignore[arg-type]
        roles=roles,
        scopes=scopes,
        auth_provider=user.get("auth_provider") or "local",
    )


def _resolve_principal_from_headers_and_cookies(
    *,
    auth_header: str | None,
    x_api_key: str | None,
    cookie_token: str | None,
    csrf_header: str | None = None,
) -> tuple[Principal | None, bool]:
    """Resolve an authenticated Principal from HTTP credentials.

    Returns `(principal, credentials_present)`.
    Raises HTTPException(401) if credentials were supplied but invalid/revoked/expired.
    """
    db = get_config_database()

    # 1. Explicit X-API-Key header
    if x_api_key:
        verified = db.verify_api_key(x_api_key.strip())
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid or expired API key.")
        user, key_scopes = verified
        return _build_principal_from_user_dict(user, principal_type="api_key", override_scopes=key_scopes), True

    # 2. Authorization: Bearer <jwt_or_api_key>
    if auth_header:
        parts = auth_header.strip().split(None, 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Malformed Authorization header.")
        token = parts[1].strip()
        if token.startswith("es_"):
            verified = db.verify_api_key(token)
            if not verified:
                raise HTTPException(status_code=401, detail="Invalid or expired API key.")
            user, key_scopes = verified
            return _build_principal_from_user_dict(user, principal_type="api_key", override_scopes=key_scopes), True

        claims = verify_auth_token(token)
        if not claims:
            raise HTTPException(status_code=401, detail="Invalid or expired bearer token.")
        return _principal_from_claims(db, claims), True

    # 3. HttpOnly echo_auth session cookie
    if cookie_token:
        claims = verify_auth_token(cookie_token)
        if not claims:
            raise HTTPException(status_code=401, detail="Invalid or expired session cookie.")
        if csrf_header is not None and claims.get("csrf") and csrf_header != claims.get("csrf"):
            raise HTTPException(status_code=403, detail="CSRF token mismatch.")
        return _principal_from_claims(db, claims), True

    return None, False


def _principal_from_claims(db, claims: dict[str, Any]) -> Principal:
    sub = claims.get("sub")
    username = claims.get("user") or ""
    user = db.get_user_by_id(sub) if sub else None
    if user is None and username:
        user = db.get_user_by_username(username)

    if user is not None:
        if not user.get("is_active", True):
            raise HTTPException(status_code=401, detail="User account is disabled.")
        return _build_principal_from_user_dict(user, principal_type="user")

    if db.has_any_users():
        raise HTTPException(status_code=401, detail="User no longer exists.")

    # Legacy/stateless token minted when no users table entries exist
    token_roles = tuple(claims.get("roles") or ("admin",))
    scopes: set[str] = set()
    for role_name in token_roles:
        scopes.update(SYSTEM_ROLE_PERMISSIONS.get(role_name, ()))
    return Principal(
        user_id=sub,
        username=str(username or sub or "system"),
        principal_type="user",
        roles=token_roles,
        scopes=frozenset(scopes),
        auth_provider=str(claims.get("auth_provider") or "local"),
    )


def get_optional_principal(request: Request) -> Principal | None:
    """Resolve authenticated Principal if present and valid; return None if absent or invalid."""
    cached = getattr(request.state, "principal", None)
    if isinstance(cached, Principal) and cached.user_id is not None:
        return cached
    try:
        principal, has_creds = _resolve_principal_from_headers_and_cookies(
            auth_header=request.headers.get("Authorization"),
            x_api_key=request.headers.get("X-API-Key"),
            cookie_token=request.cookies.get("echo_auth"),
            csrf_header=request.headers.get("X-CSRF-Token"),
        )
        if has_creds and principal is not None:
            request.state.principal = principal
            return principal
    except HTTPException:
        return None
    return None


def _fastapi_require_auth(request: Request) -> Principal:
    principal, has_creds = _resolve_principal_from_headers_and_cookies(
        auth_header=request.headers.get("Authorization"),
        x_api_key=request.headers.get("X-API-Key"),
        cookie_token=request.cookies.get("echo_auth"),
        csrf_header=request.headers.get("X-CSRF-Token"),
    )
    if has_creds and principal is not None:
        request.state.principal = principal
        return principal

    db = get_config_database()
    if db.has_any_users():
        raise HTTPException(status_code=401, detail="Authentication required.")

    # Pre-setup / bootstrap state (0 users exist in config.db): permit initial configuration
    # and legacy pre-setup route tests cleanly as an ephemeral system principal.
    pre_setup_principal = Principal(
        user_id=None,
        username="setup",
        principal_type="system",
        roles=("admin",),
        scopes=frozenset({"*"}),
        auth_provider="system",
    )
    request.state.principal = pre_setup_principal
    return pre_setup_principal


def require_auth(request: Request):
    """FastAPI dependency returning an authenticated Principal (also compatible as Flask decorator)."""
    if callable(request) and not isinstance(request, Request):
        func = request

        @functools.wraps(func)
        def _flask_wrapper(*args, **kwargs):
            from flask import abort, g, request as flask_request

            try:
                principal, has_creds = _resolve_principal_from_headers_and_cookies(
                    auth_header=flask_request.headers.get("Authorization"),
                    x_api_key=flask_request.headers.get("X-API-Key"),
                    cookie_token=flask_request.cookies.get("echo_auth"),
                    csrf_header=flask_request.headers.get("X-CSRF-Token"),
                )
            except HTTPException as exc:
                abort(exc.status_code, description=exc.detail)
                return None

            if not has_creds or principal is None:
                if get_config_database().has_any_users():
                    abort(401, description="Authentication required.")
                    return None
                principal = Principal(
                    user_id=None,
                    username="setup",
                    principal_type="system",
                    roles=("admin",),
                    scopes=frozenset({"*"}),
                    auth_provider="system",
                )
            g.principal = principal
            return func(*args, **kwargs)

        return _flask_wrapper

    return _fastapi_require_auth(request)


def require_authenticated(principal: Principal = Depends(require_auth)) -> Principal:
    """Strict FastAPI dependency requiring a concrete authenticated user or API key (never pre-setup)."""
    if principal.user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return principal


def require_scope(scope: str):
    """FastAPI service-tier RBAC dependency enforcing `Principal.has_scope(scope)`."""

    def _scope_dependency(principal: Any = Depends(require_auth)) -> Principal:
        if isinstance(principal, Principal):
            resolved = principal
        elif isinstance(principal, dict):
            raw_scopes = principal.get("scopes")
            roles = tuple(principal.get("roles") or (("admin",) if raw_scopes is None else ()))
            if raw_scopes is not None:
                scopes = frozenset(str(s) for s in raw_scopes)
            else:
                acc_scopes: set[str] = set()
                for r in roles:
                    acc_scopes.update(SYSTEM_ROLE_PERMISSIONS.get(r, ()))
                scopes = frozenset(acc_scopes)
            resolved = Principal(
                user_id=principal.get("id") or principal.get("user_id"),
                username=str(principal.get("user") or principal.get("username") or "test"),
                principal_type="system",
                roles=roles,
                scopes=scopes,
            )
        elif principal is True:
            resolved = Principal(
                user_id=None,
                username="override",
                principal_type="system",
                roles=("admin",),
                scopes=frozenset({"*"}),
            )
        else:
            raise HTTPException(status_code=401, detail="Authentication required.")

        if not resolved.has_scope(scope):
            raise HTTPException(status_code=403, detail=f"Missing required capability scope: {scope}")
        return resolved

    return _scope_dependency
