from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from core.tiered_logger import get_logger
from services.storage_service import get_storage_service
from web.auth import require_auth

logger = get_logger("accounts_route")
router = APIRouter(prefix="/api/v1/system/accounts", tags=["Accounts"])


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
