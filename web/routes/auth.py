"""Authentication, First-Boot Setup, OIDC PKCE, and API Key Management Routes."""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from core.security.oidc import oidc_manager
from core.security.passwords import PASSWORD_RECOMMENDED_LENGTH, validate_password_policy
from core.security.rbac import Principal
from core.security.tokens import create_access_token
from core.tiered_logger import get_logger
from database.config_database import get_config_database
from web.auth import get_optional_principal, require_authenticated

logger = get_logger("auth_route")

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
legacy_router = APIRouter(prefix="/api/v1/system/auth", tags=["Auth (Legacy)"])


class AuthStatusResponse(BaseModel):
    setup_required: bool
    oidc_enabled: bool
    authenticated: bool
    user: dict[str, Any] | None = None
    providers: list[str]
    password_recommended_length: int = PASSWORD_RECOMMENDED_LENGTH


class SetupRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    scopes: list[str] = Field(default_factory=list)
    expires_at: int | None = None


def _issue_session_cookies(response: Response, user: dict[str, Any]) -> tuple[str, str]:
    csrf = secrets.token_urlsafe(24)
    token = create_access_token(
        user_id=user.get("id"),
        username=user.get("username", ""),
        roles=user.get("roles") or (),
        auth_provider=user.get("auth_provider") or "local",
        csrf=csrf,
    )
    response.set_cookie(
        key="echo_auth",
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return token, csrf


def auth_status(request: Request) -> AuthStatusResponse:
    db = get_config_database()
    setup_required = db.is_setup_required()
    oidc_enabled = oidc_manager.is_enabled()
    providers = ["local"]
    if oidc_enabled:
        providers.append("oidc")

    principal = get_optional_principal(request)
    user_payload = None
    authenticated = False
    if principal is not None and principal.user_id is not None:
        authenticated = True
        user_payload = {
            "id": principal.user_id,
            "username": principal.username,
            "roles": list(principal.roles),
            "scopes": sorted(principal.scopes),
            "principal_type": principal.principal_type,
            "auth_provider": principal.auth_provider,
        }

    return AuthStatusResponse(
        setup_required=setup_required,
        oidc_enabled=oidc_enabled,
        authenticated=authenticated,
        user=user_payload,
        providers=providers,
    )


def first_boot_setup(payload: SetupRequest, response: Response) -> dict[str, Any]:
    db = get_config_database()
    if not db.is_setup_required():
        raise HTTPException(status_code=409, detail="Initial admin account already exists.")

    try:
        validate_password_policy(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        admin_user = db.create_user(
            username=payload.username,
            password=payload.password,
            auth_provider="local",
            roles=["admin"],
        )
    except Exception as exc:
        logger.error("First-boot setup failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))

    token, csrf = _issue_session_cookies(response, admin_user)
    return {
        "success": True,
        "user": admin_user,
        "access_token": token,
        "csrf_token": csrf,
    }


def login(payload: LoginRequest, response: Response) -> dict[str, Any]:
    db = get_config_database()
    user = db.authenticate_local_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token, csrf = _issue_session_cookies(response, user)
    return {
        "success": True,
        "user": user,
        "access_token": token,
        "csrf_token": csrf,
    }


def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(key="echo_auth", path="/")
    response.delete_cookie(key="csrf_token", path="/")
    return {"success": True}


def get_current_user_info(principal: Principal = Depends(require_authenticated)) -> dict[str, Any]:
    return {
        "user": {
            "id": principal.user_id,
            "username": principal.username,
            "roles": list(principal.roles),
            "scopes": sorted(principal.scopes),
            "principal_type": principal.principal_type,
            "auth_provider": principal.auth_provider,
        }
    }


def oidc_login(
    redirect_uri: str | None = Query(None),
    mode: str = Query("redirect"),
):
    if not oidc_manager.is_enabled():
        raise HTTPException(status_code=400, detail="OIDC authentication is not configured.")
    try:
        auth_url, state = oidc_manager.start_login(redirect_uri=redirect_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if mode == "json":
        return {"authorization_url": auth_url, "state": state}
    return RedirectResponse(url=auth_url, status_code=302)


def oidc_callback(code: str = Query(...), state: str = Query(...)):
    if not oidc_manager.is_enabled():
        raise HTTPException(status_code=400, detail="OIDC authentication is not configured.")
    try:
        user = oidc_manager.complete_callback(code=code, state=state)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    resp = JSONResponse({"success": True, "user": user})
    token, csrf = _issue_session_cookies(resp, user)
    resp.body = JSONResponse(
        {"success": True, "user": user, "access_token": token, "csrf_token": csrf}
    ).body
    resp.headers["content-length"] = str(len(resp.body))
    return resp


def create_api_key_route(
    payload: CreateApiKeyRequest,
    principal: Principal = Depends(require_authenticated),
) -> dict[str, Any]:
    requested_scopes = list(dict.fromkeys(s.strip() for s in payload.scopes if s.strip()))
    if not requested_scopes:
        requested_scopes = sorted(principal.scopes) if principal.scopes else []

    if "*" not in principal.scopes:
        for req_scope in requested_scopes:
            if not principal.has_scope(req_scope):
                raise HTTPException(
                    status_code=403,
                    detail=f"Cannot grant API key scope '{req_scope}' outside caller permissions.",
                )

    db = get_config_database()
    assert principal.user_id is not None
    key_record = db.create_api_key(
        user_id=principal.user_id,
        name=payload.name,
        scopes=requested_scopes,
        expires_at=payload.expires_at,
    )
    return {"success": True, **key_record}


def list_api_keys_route(
    user_id: str | None = Query(None),
    principal: Principal = Depends(require_authenticated),
) -> dict[str, Any]:
    db = get_config_database()
    is_admin = principal.has_scope("*")
    target_user_id = user_id if (is_admin and user_id) else (None if is_admin and user_id is None else principal.user_id)
    if not is_admin and user_id and user_id != principal.user_id:
        raise HTTPException(status_code=403, detail="Cannot list API keys for another user.")
    keys = db.list_api_keys(user_id=target_user_id)
    return {"api_keys": keys, "total": len(keys)}


def delete_api_key_route(
    key_id: str,
    principal: Principal = Depends(require_authenticated),
) -> dict[str, bool]:
    db = get_config_database()
    is_admin = principal.has_scope("*")
    revoked = db.revoke_api_key(key_id, user_id=None if is_admin else principal.user_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found or already revoked.")
    return {"success": True}


for _rtr in (router, legacy_router):
    _rtr.add_api_route("/status", auth_status, methods=["GET"], response_model=AuthStatusResponse)
    _rtr.add_api_route("/setup", first_boot_setup, methods=["POST"], status_code=201)
    _rtr.add_api_route("/login", login, methods=["POST"])
    _rtr.add_api_route("/logout", logout, methods=["POST"])
    _rtr.add_api_route("/me", get_current_user_info, methods=["GET"])
    _rtr.add_api_route("/oidc/login", oidc_login, methods=["GET"])
    _rtr.add_api_route("/oidc/callback", oidc_callback, methods=["GET"])
    _rtr.add_api_route("/api-keys", create_api_key_route, methods=["POST"], status_code=201)
    _rtr.add_api_route("/api-keys", list_api_keys_route, methods=["GET"])
    _rtr.add_api_route("/api-keys/{key_id}", delete_api_key_route, methods=["DELETE"])
