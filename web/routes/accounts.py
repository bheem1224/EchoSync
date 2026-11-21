from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from core.security.passwords import validate_password_policy
from core.security.rbac import Principal
from core.tiered_logger import get_logger
from database.config_database import get_config_database
from services.storage_service import get_storage_service
from web.auth import require_auth, require_scope

logger = get_logger("accounts_route")
router = APIRouter(prefix="/api/v1/system/accounts", tags=["Accounts"])
users_auth_router = APIRouter(prefix="/api/v1/auth", tags=["Users & RBAC"])


class AccountResponse(BaseModel):
    service: str
    accounts: list[dict[str, Any]]
    total: int
    model_config = ConfigDict(from_attributes=True)


class CreateAccountRequest(BaseModel):
    account_name: str
    display_name: str | None = None


class CreateAccountResponse(BaseModel):
    success: bool
    account_id: int
    account_name: str
    model_config = ConfigDict(from_attributes=True)


class ActivateAccountRequest(BaseModel):
    is_active: bool = True


class ActivateAccountResponse(BaseModel):
    success: bool
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class GenericSuccessResponse(BaseModel):
    success: bool
    model_config = ConfigDict(from_attributes=True)


class UpdateAccountNameRequest(BaseModel):
    name: str


class AccountOverridesRequest(BaseModel):
    managed_user_id: str
    service_account_id: str
    action: str


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str | None = None
    roles: list[str] = Field(default_factory=lambda: ["member"])
    auth_provider: str = "local"


class AssignRolesRequest(BaseModel):
    roles: list[str] = Field(..., min_length=1)


class AssignManagedAccountRequest(BaseModel):
    server_plugin_id: int
    managed_account_id: str = Field(..., min_length=1)


class BindExternalAccountRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=64)
    external_account_id: str = Field(..., min_length=1, max_length=256)
    display_name: str | None = Field(default=None, max_length=256)
    category: str | None = Field(default=None, max_length=32)
    plugin_id: int | None = None


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8, max_length=512)


def _list_users_handler(_=Depends(require_scope("service:accounts:read"))):
    users = get_config_database().list_users()
    return {"users": users, "total": len(users)}


def _create_user_handler(payload: CreateUserRequest, _=Depends(require_scope("service:accounts:edit"))):
    db = get_config_database()
    if payload.auth_provider == "local":
        if payload.password is None:
            raise HTTPException(status_code=422, detail="Password is required for local users.")
        try:
            validate_password_policy(payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    try:
        user = db.create_user(
            username=payload.username,
            password=payload.password,
            auth_provider=payload.auth_provider,
            roles=payload.roles,
        )
        return {"success": True, "user": user}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _list_roles_handler(_=Depends(require_scope("service:accounts:read"))):
    roles = get_config_database().list_roles()
    return {"roles": roles, "total": len(roles)}


def _assign_user_roles_handler(
    user_id: str,
    payload: AssignRolesRequest,
    _=Depends(require_scope("service:accounts:edit")),
):
    db = get_config_database()
    if not db.assign_user_roles(user_id, payload.roles):
        raise HTTPException(status_code=404, detail="User not found.")
    user = db.get_user_by_id(user_id)
    return {"success": True, "user": user}


def _list_managed_accounts_handler(
    user_id: str,
    principal: Principal = Depends(require_auth),
):
    if principal.user_id == user_id:
        if not principal.has_scope("contract:accounts:read:own"):
            raise HTTPException(status_code=403, detail="Missing required capability scope: contract:accounts:read:own")
    elif not principal.has_scope("contract:accounts:read:any"):
        raise HTTPException(status_code=403, detail="Missing required capability scope: contract:accounts:read:any")

    assignments = get_config_database().get_user_managed_accounts(user_id)
    return {"user_id": user_id, "managed_accounts": assignments, "total": len(assignments)}


def _assign_managed_account_handler(
    user_id: str,
    payload: AssignManagedAccountRequest,
    _=Depends(require_scope("service:accounts:edit")),
):
    db = get_config_database()
    if not db.assign_managed_account(user_id, payload.server_plugin_id, payload.managed_account_id):
        raise HTTPException(status_code=404, detail="User not found.")
    assignments = db.get_user_managed_accounts(user_id)
    return {"success": True, "managed_accounts": assignments}


def _remove_managed_account_handler(
    user_id: str,
    server_plugin_id: int,
    managed_account_id: str,
    _=Depends(require_scope("service:accounts:edit")),
):
    get_config_database().remove_managed_account(user_id, server_plugin_id, managed_account_id)
    return {"success": True}


_STREAMING_PROVIDERS: frozenset[str] = frozenset({"spotify", "tidal", "listenbrainz", "apple_music", "deezer", "qobuz"})


def _list_external_accounts_handler(
    user_id: str,
    principal: Principal = Depends(require_auth),
):
    if principal.user_id == user_id:
        if not (principal.has_scope("contract:accounts:read:own") or principal.has_scope("service:accounts:read")):
            raise HTTPException(status_code=403, detail="Missing required capability scope: contract:accounts:read:own")
    elif not (principal.has_scope("contract:accounts:read:any") or principal.has_scope("service:accounts:read")):
        raise HTTPException(status_code=403, detail="Missing required capability scope: contract:accounts:read:any")

    accounts = get_config_database().get_user_external_accounts(user_id)
    return {"user_id": user_id, "external_accounts": accounts, "total": len(accounts)}


def _bind_external_account_handler(
    user_id: str,
    payload: BindExternalAccountRequest,
    principal: Principal = Depends(require_auth),
):
    db = get_config_database()
    clean_provider, resolved_cat, _ = db._resolve_provider_metadata(
        payload.provider, payload.category, payload.plugin_id
    )
    is_admin_edit = principal.has_scope("service:accounts:edit") or principal.has_scope("contract:accounts:edit:any")
    if not is_admin_edit:
        if principal.user_id != user_id or not principal.has_scope("contract:accounts:edit:own"):
            raise HTTPException(status_code=403, detail="Missing required capability scope: service:accounts:edit")
        if resolved_cat != "streaming" or clean_provider not in _STREAMING_PROVIDERS:
            raise HTTPException(
                status_code=403,
                detail="Members may only bind their own personal streaming accounts.",
            )

    if not db.bind_external_account(
        user_id=user_id,
        provider=clean_provider,
        external_account_id=payload.external_account_id,
        display_name=payload.display_name,
        category=resolved_cat,
        plugin_id=payload.plugin_id,
    ):
        raise HTTPException(status_code=404, detail="User not found or invalid external account.")
    accounts = db.get_user_external_accounts(user_id)
    return {"success": True, "external_accounts": accounts}


def _unbind_external_account_handler(
    user_id: str,
    provider: str,
    external_account_id: str,
    principal: Principal = Depends(require_auth),
):
    db = get_config_database()
    clean_provider, resolved_cat, _ = db._resolve_provider_metadata(provider)
    is_admin_edit = principal.has_scope("service:accounts:edit") or principal.has_scope("contract:accounts:edit:any")
    if not is_admin_edit:
        if principal.user_id != user_id or not principal.has_scope("contract:accounts:edit:own"):
            raise HTTPException(status_code=403, detail="Missing required capability scope: service:accounts:edit")
        if resolved_cat != "streaming":
            raise HTTPException(
                status_code=403,
                detail="Members may only unbind their own personal streaming accounts.",
            )

    db.unbind_external_account(user_id, clean_provider, external_account_id)
    accounts = db.get_user_external_accounts(user_id)
    return {"success": True, "external_accounts": accounts}


def _list_available_external_accounts_handler(principal: Principal = Depends(require_auth)):
    """Discover available streaming and media server accounts via SDK/storage without exposing secrets."""
    db = get_config_database()
    streaming: list[dict[str, Any]] = []
    media_server: list[dict[str, Any]] = []
    seen_streaming: set[tuple[str, str]] = set()
    seen_media: set[tuple[str, str]] = set()

    # 1. Query active media server plugins via agnostic SDK facade (discovers live Home / Managed Users)
    try:
        from core.nexus_framework.plugin_loader import PluginRegistry
        from core.nexus_framework.plugin_SDK import sdk

        media_pids = list(PluginRegistry.get_active_services_by_type("media_server") or [])
        for extra_pid in PluginRegistry.get_plugins_by_type("mediaserver", exclude_disabled=True) or []:
            if extra_pid not in media_pids:
                media_pids.append(extra_pid)

        for pid in media_pids:
            svc_name = (db.get_service_name(pid) or str(pid)).lower().replace("echosync.", "")
            for mu in sdk.plugins.list_provider_accounts(pid) or []:
                ext_id = str(mu.get("external_account_id") or "").strip()
                disp = str(mu.get("display_name") or ext_id).strip()
                prov = str(mu.get("provider") or svc_name).strip().lower()
                if ext_id and (prov, ext_id) not in seen_media:
                    seen_media.add((prov, ext_id))
                    media_server.append(
                        {
                            "provider": prov,
                            "external_account_id": ext_id,
                            "display_name": disp,
                            "is_managed": bool(mu.get("is_managed", False)),
                            "plugin_id": pid if isinstance(pid, int) else None,
                        }
                    )
    except Exception as exc:
        logger.warning(f"Media server SDK account discovery fallback: {exc}")

    # 2. Scan service accounts from config.db (preserves legacy Spotify/Tidal/Plex accounts)
    try:
        with db._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT a.id, a.account_name, a.display_name, a.user_id, a.is_active, a.is_authenticated,
                       s.name AS service_name, s.plugin_id, s.service_type
                FROM accounts a
                JOIN services s ON s.id = a.service_id
                ORDER BY s.name ASC, a.display_name ASC, a.account_name ASC
                """
            ).fetchall()
            for r in rows:
                svc_raw = str(r["service_name"] or "").lower().replace("echosync.", "").replace("echosync/", "")
                ext_id = str(r["account_name"] or r["user_id"] or r["id"])
                disp = str(r["display_name"] or r["account_name"] or ext_id)
                is_media = svc_raw in db._MEDIA_SERVER_PROVIDERS or r["service_type"] == "media_server"
                item = {
                    "provider": svc_raw,
                    "external_account_id": ext_id,
                    "display_name": disp,
                    "is_managed": False,
                    "account_db_id": r["id"],
                    "plugin_id": r["plugin_id"],
                    "is_authenticated": bool(r["is_authenticated"]),
                }
                if is_media:
                    key = (svc_raw, ext_id)
                    if key not in seen_media:
                        seen_media.add(key)
                        media_server.append(item)
                else:
                    key = (svc_raw, ext_id)
                    if key not in seen_streaming:
                        seen_streaming.add(key)
                        streaming.append(item)
    except Exception as exc:
        logger.debug(f"Available accounts DB scan fallback: {exc}")

    return {"streaming": streaming, "media_server": media_server}


def _list_family_profiles_handler(
    provider: str | None = None,
    principal: Principal = Depends(require_auth),
):
    """Return caller's own media profiles and family members' target media profiles (no secrets)."""
    can_family = (
        principal.has_scope("contract:media_profiles:read:family")
        or principal.has_scope("service:playlist_sync:share")
        or principal.has_scope("contract:accounts:read:any")
    )
    if not can_family and not principal.has_scope("contract:accounts:read:own"):
        raise HTTPException(
            status_code=403,
            detail="Missing required capability scope: contract:media_profiles:read:family",
        )

    db = get_config_database()
    all_bindings = db.list_all_external_accounts(category="media_server")
    clean_filter = provider.strip().lower().replace("echosync.", "") if provider else None

    my_profiles: list[dict[str, Any]] = []
    family_profiles: list[dict[str, Any]] = []
    for b in all_bindings:
        if clean_filter and b["provider"] != clean_filter:
            continue
        is_self = principal.user_id is not None and b["user_id"] == principal.user_id
        entry = {
            "user_id": b["user_id"],
            "username": b["username"],
            "provider": b["provider"],
            "external_account_id": b["external_account_id"],
            "display_name": b["display_name"],
            "is_self": is_self,
        }
        if is_self:
            my_profiles.append(entry)
        elif can_family:
            family_profiles.append(entry)

    return {
        "my_profiles": my_profiles,
        "family_profiles": family_profiles,
        "default_target_user_id": my_profiles[0]["external_account_id"] if my_profiles else None,
    }


def _reset_user_password_handler(
    user_id: str,
    payload: ResetPasswordRequest,
    _=Depends(require_scope("service:accounts:edit")),
):
    try:
        validate_password_policy(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if not get_config_database().reset_user_password(user_id, payload.password):
        raise HTTPException(status_code=404, detail="User not found.")
    return {"success": True}


def _delete_user_handler(
    user_id: str,
    principal: Principal = Depends(require_scope("service:accounts:edit")),
):
    if principal.user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own currently active account.")
    try:
        if not get_config_database().delete_user(user_id):
            raise HTTPException(status_code=404, detail="User not found.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"success": True}


for _acct_rtr in (router, users_auth_router):
    _acct_rtr.add_api_route("/users", _list_users_handler, methods=["GET"])
    _acct_rtr.add_api_route("/users", _create_user_handler, methods=["POST"], status_code=201)
    _acct_rtr.add_api_route("/users/{user_id}", _delete_user_handler, methods=["DELETE"])
    _acct_rtr.add_api_route("/users/{user_id}/password", _reset_user_password_handler, methods=["PUT", "POST"])
    _acct_rtr.add_api_route("/roles", _list_roles_handler, methods=["GET"])
    _acct_rtr.add_api_route("/users/{user_id}/roles", _assign_user_roles_handler, methods=["PUT", "POST"])
    _acct_rtr.add_api_route("/users/{user_id}/managed-accounts", _list_managed_accounts_handler, methods=["GET"])
    _acct_rtr.add_api_route("/users/{user_id}/managed-accounts", _assign_managed_account_handler, methods=["POST"], status_code=201)
    _acct_rtr.add_api_route(
        "/users/{user_id}/managed-accounts/{server_plugin_id}/{managed_account_id}",
        _remove_managed_account_handler,
        methods=["DELETE"],
    )
    _acct_rtr.add_api_route("/users/{user_id}/external-accounts", _list_external_accounts_handler, methods=["GET"])
    _acct_rtr.add_api_route(
        "/users/{user_id}/external-accounts", _bind_external_account_handler, methods=["POST"], status_code=201
    )
    _acct_rtr.add_api_route(
        "/users/{user_id}/external-accounts/{provider}/{external_account_id:path}",
        _unbind_external_account_handler,
        methods=["DELETE"],
    )
    _acct_rtr.add_api_route("/external-accounts/available", _list_available_external_accounts_handler, methods=["GET"])
    _acct_rtr.add_api_route("/family-profiles", _list_family_profiles_handler, methods=["GET"])


@router.post("/map", dependencies=[Depends(require_auth)])
def retired_map_accounts():
    """Retired legacy Music-to-Media-Server mapping endpoint."""
    raise HTTPException(
        status_code=410,
        detail="Retired: use /api/v1/auth/users/{user_id}/external-accounts to bind external accounts to EchoSync users.",
    )


@router.get("/{service_name}", response_model=AccountResponse)
def list_service_accounts(service_name: str):
    """List all accounts for a specific service."""
    try:
        storage = get_storage_service()
        accounts = storage.list_accounts(service_name)
        return AccountResponse(
            service=service_name, accounts=accounts, total=len(accounts)
        )
    except Exception as e:
        logger.error(f"Error listing accounts for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{service_name}", response_model=CreateAccountResponse, status_code=201)
def create_account(service_name: str, payload: CreateAccountRequest):
    """Create a new account for a service."""
    try:
        storage = get_storage_service()
        account_id = storage.ensure_account(
            service_name=service_name,
            account_name=payload.account_name,
            display_name=payload.display_name or payload.account_name,
        )

        if account_id:
            return CreateAccountResponse(
                success=True, account_id=account_id, account_name=payload.account_name
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create account")
    except Exception as e:
        logger.error(f"Error creating account for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{service_name}/{account_id}/activate", response_model=ActivateAccountResponse
)
def activate_account(
    service_name: str,
    account_id: int,
    payload: ActivateAccountRequest = Body(default=ActivateAccountRequest()),
):
    """Activate an account (toggle active status for multi-account support)."""
    try:
        storage = get_storage_service()
        success = storage.toggle_account_active(account_id, payload.is_active)

        if success:
            return ActivateAccountResponse(success=True, is_active=payload.is_active)
        else:
            raise HTTPException(
                status_code=500, detail="Failed to update account status"
            )
    except Exception as e:
        logger.error(
            f"Error updating account {account_id} status for {service_name}: {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{service_name}/{account_id}", response_model=GenericSuccessResponse)
def delete_account(service_name: str, account_id: int):
    """Delete an account."""
    try:
        storage = get_storage_service()
        success = storage.delete_account(account_id)

        if success:
            return GenericSuccessResponse(success=True)
        else:
            raise HTTPException(status_code=500, detail="Failed to delete account")
    except Exception as e:
        logger.error(f"Error deleting account {account_id} for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{service_name}/{account_id}/name", response_model=GenericSuccessResponse)
def update_account_name(
    service_name: str, account_id: int, payload: UpdateAccountNameRequest
):
    """Update account display name."""
    try:
        storage = get_storage_service()
        success = storage.update_account_name(account_id, payload.name)

        if success:
            return GenericSuccessResponse(success=True)
        else:
            raise HTTPException(status_code=500, detail="Failed to update account name")
    except Exception as e:
        logger.error(f"Error updating account name for {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/overrides",
    response_model=GenericSuccessResponse,
    dependencies=[Depends(require_auth)],
)
def set_account_overrides(payload: AccountOverridesRequest):
    from core.settings import config_manager

    try:
        if payload.action not in ("unfuse", "refuse"):
            raise HTTPException(status_code=400, detail="Invalid action parameter")

        from core.nexus_framework.plugin_loader import PluginRegistry

        active_servers = PluginRegistry.get_active_services_by_type("media_server")
        active_media_server = (
            active_servers[0].split(".")[-1] if active_servers else "plex"
        )
        if not active_media_server:
            raise HTTPException(
                status_code=400, detail="No active media server configured"
            )

        provider_config = config_manager.get(active_media_server, {})
        account_map_override = provider_config.get("account_map_override", {})

        overrides = account_map_override.get(payload.managed_user_id, [])

        if payload.action == "unfuse":
            if payload.service_account_id in overrides:
                overrides.remove(payload.service_account_id)
        elif payload.action == "refuse":
            if payload.service_account_id not in overrides:
                overrides.append(payload.service_account_id)

        account_map_override[payload.managed_user_id] = overrides
        provider_config["account_map_override"] = account_map_override
        config_manager.set(active_media_server, provider_config)
        config_manager.save_settings(config_manager.get_settings())

        return GenericSuccessResponse(success=True)
    except Exception as e:
        logger.error(f"Error setting account override: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
