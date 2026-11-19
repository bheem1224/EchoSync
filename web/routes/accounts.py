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


for _acct_rtr in (router, users_auth_router):
    _acct_rtr.add_api_route("/users", _list_users_handler, methods=["GET"])
    _acct_rtr.add_api_route("/users", _create_user_handler, methods=["POST"], status_code=201)
    _acct_rtr.add_api_route("/roles", _list_roles_handler, methods=["GET"])
    _acct_rtr.add_api_route("/users/{user_id}/roles", _assign_user_roles_handler, methods=["PUT", "POST"])
    _acct_rtr.add_api_route("/users/{user_id}/managed-accounts", _list_managed_accounts_handler, methods=["GET"])
    _acct_rtr.add_api_route("/users/{user_id}/managed-accounts", _assign_managed_account_handler, methods=["POST"], status_code=201)
    _acct_rtr.add_api_route(
        "/users/{user_id}/managed-accounts/{server_plugin_id}/{managed_account_id}",
        _remove_managed_account_handler,
        methods=["DELETE"],
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
