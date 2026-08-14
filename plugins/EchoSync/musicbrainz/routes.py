"""MusicBrainz OAuth2 PKCE routes and account management.

Endpoints
---------
GET  /api/musicbrainz/accounts               — list accounts + credential / redirect status
POST /api/musicbrainz/accounts               — create a named account slot
DELETE /api/musicbrainz/accounts/<id>        — delete an account
PUT  /api/musicbrainz/accounts/<id>/activate — toggle active flag
GET  /api/musicbrainz/auth?account_id=N      — start PKCE OAuth2 flow
GET  /api/musicbrainz/callback               — handle OAuth2 callback & token exchange
"""
import base64
import hashlib
import json
import secrets
import time
import urllib.parse
import uuid

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from core.nexus_framework.plugin_SDK import sdk
from core.tiered_logger import get_logger
from services.storage_service import get_storage_service

logger = get_logger("musicbrainz_routes")
storage = get_storage_service()

router = APIRouter()

# Second blueprint for the settings-card config API
config_router = APIRouter()


@config_router.get("/config")
def get_config():
    """Return the current MusicBrainz settings-card configuration."""
    try:
        
        token = sdk.config.get('user_token')
        auto_contribute = sdk.config.get('auto_contribute')
        return JSONResponse(content={
            "token_configured": bool(token),
            "auto_contribute": auto_contribute == "true" if isinstance(auto_contribute, str) else bool(auto_contribute),
        }), 200
    except Exception as e:
        logger.error(f"Error reading MusicBrainz config: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@config_router.post("/config")
async def save_config(request: Request):
    """Persist MusicBrainz settings-card values (user token + auto-contribute flag)."""
    try:
        payload = await request.json() or {}

        if "user_token" in payload and payload["user_token"].strip():
            from core.security import encrypt_string
            sdk.config.set('user_token', encrypt_string(payload["user_token"].strip()))

        if "auto_contribute" in payload:
            sdk.config.set('auto_contribute', str(bool(payload["auto_contribute"])).lower())

        token = sdk.config.get('user_token')
        auto_contribute = sdk.config.get('auto_contribute')
        return JSONResponse(content={
            "success": True,
            "token_configured": bool(token),
            "auto_contribute": auto_contribute == "true" if isinstance(auto_contribute, str) else bool(auto_contribute)
        }), 200
    except Exception as e:
        logger.error(f"Error saving MusicBrainz config: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)

_AUTH_URL = "https://musicbrainz.org/oauth2/authorize"
_TOKEN_URL = "https://musicbrainz.org/oauth2/token"
_USERINFO_URL = "https://musicbrainz.org/oauth2/userinfo"
# Scopes used: profile/email for display name, submit_isrc for fingerprint contribution,
# tag/rating/collection for interactive editing features.
_SCOPES = "profile email submit_isrc tag rating collection"


# ── Account Management ────────────────────────────────────────────────────────

@router.get("/accounts")
def list_accounts():
    """List all MusicBrainz accounts with authentication status."""
    try:
        from core.nexus_framework.plugin_loader import PluginRegistry
        if PluginRegistry.is_plugin_disabled("musicbrainz"):
            return JSONResponse(content={"accounts": [], "redirect_uri": ""}, status_code=200)

        db_accounts = sdk.accounts.get_all()
        accounts = [
            {
                "id": a.get("id"),
                "account_name": a.get("account_name") or a.get("display_name") or "Unnamed",
                "display_name": a.get("display_name") or a.get("account_name") or "Unnamed",
                "user_id": a.get("user_id"),
                "is_active": a.get("is_active"),
                "is_authenticated": a.get("is_authenticated"),
            }
            for a in db_accounts
        ]

        from .client import MusicBrainzClient
        from core.network_utils import get_lan_ip
        redirect_uri = f"https://{get_lan_ip()}:5001/api/oauth/callback/musicbrainz"

        client_id = sdk.config.get('client_id')
        client_secret_configured = bool(sdk.config.get('client_secret'))

        return JSONResponse(content={
            "accounts": accounts,
            "redirect_uri": redirect_uri,
            "client_id_configured": bool(client_id),
            "client_secret_configured": client_secret_configured,
        }), 200
    except Exception as e:
        logger.error(f"Error listing MusicBrainz accounts: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.post("/accounts")
async def create_account(request: Request):
    """Create a new named MusicBrainz account slot.

    The account holds the OAuth tokens obtained via the auth flow.
    Body: { account_name (str) }
    """
    try:
        payload = await request.json() or {}
        account_name = (payload.get("account_name") or "").strip()
        if not account_name:
            return JSONResponse(content={"error": "account_name is required"}, status_code=400)

        account_id = sdk.accounts.ensure_account(
            account_name=account_name,
            display_name=account_name,
        )
        if not account_id:
            return JSONResponse(content={"error": "Failed to create account"}, status_code=500)

        return JSONResponse(content={
            "account": {
                "id": account_id,
                "account_name": account_name,
                "display_name": account_name,
                "is_active": False,
                "is_authenticated": False,
            }
        }), 201
    except Exception as e:
        logger.error(f"Error creating MusicBrainz account: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int):
    """Delete a MusicBrainz account and its stored tokens."""
    try:
        
        ok = sdk.accounts.delete_account(account_id)
        if ok:
            return JSONResponse(content={"success": True}, status_code=200)
        return JSONResponse(content={"error": "Account not found or deletion failed"}, status_code=404)
    except Exception as e:
        logger.error(f"Error deleting MusicBrainz account {account_id}: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.put("/accounts/{account_id}/activate")
async def activate_account(account_id: int, request: Request):
    """Toggle the active flag on a MusicBrainz account."""
    try:
        payload = await request.json() or {}
        is_active = bool(payload.get("is_active", True))
        
        ok = sdk.accounts.toggle_account_active(account_id, is_active)
        if ok:
            return JSONResponse(content={"success": True, "is_active": is_active}, status_code=200)
        return JSONResponse(content={"error": "Failed to update account status"}, status_code=500)
    except Exception as e:
        logger.error(f"Error toggling MusicBrainz account {account_id}: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


# ── OAuth2 PKCE Flow ──────────────────────────────────────────────────────────

@router.get("/auth")
async def begin_auth(request: Request):
    """Start an OAuth2 PKCE authorization code flow for a MusicBrainz account.

    Query params:
        account_id (int) — existing account ID to associate the tokens with.

    Returns:
        { auth_url: str } — redirect the browser here to proceed with MusicBrainz login.
    """
    try:
        raw_id = request.query_params.get("account_id")
        if not raw_id:
            return JSONResponse(content={"error": "account_id is required"}, status_code=400)
        account_id = int(raw_id)

        

        # Verify the account exists
        accounts = sdk.accounts.get_all()
        if not any(a.get("id") == account_id for a in accounts):
            return JSONResponse(content={"error": "Account not found"}, status_code=404)

        # Application credentials must be configured before an auth flow can start
        client_id = sdk.config.get('client_id')
        if not client_id:
            return JSONResponse(content={
                "error": (
                    "MusicBrainz client_id is not configured. "
                    "Register your application at https://musicbrainz.org/account/applications "
                    "then save the credentials on the Metadata settings page."
                )
            }), 400

        if not sdk.config.get('client_secret'):
            return JSONResponse(content={"error": "MusicBrainz client_secret is not configured."}, status_code=400)

        # Derive redirect URI from centralized PluginBase helper (OAuth sidecar)
        from .client import MusicBrainzClient
        from core.network_utils import get_lan_ip
        redirect_uri = f"https://{get_lan_ip()}:5001/api/oauth/callback/musicbrainz"

        # Generate PKCE verifier / challenge pair
        verifier = secrets.token_urlsafe(64)[:128]
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")

        pkce_id = str(uuid.uuid4())
        ok = storage.store_pkce_session(
            pkce_id=pkce_id,
            service="musicbrainz",
            account_id=account_id,
            code_verifier=verifier,
            code_challenge=challenge,
            redirect_uri=redirect_uri,
            client_id=client_id,
            ttl_seconds=600,
        )
        if not ok:
            return JSONResponse(content={"error": "Failed to store OAuth session"}, status_code=500)

        storage.cleanup_expired_pkce_sessions()

        state = base64.urlsafe_b64encode(
            json.dumps({"pkce_id": pkce_id}).encode()
        ).decode().rstrip("=")

        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": _SCOPES,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
        auth_url = f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"
        logger.info(f"Generated MusicBrainz auth URL for account {account_id}")
        return JSONResponse(content={"auth_url": auth_url}, status_code=200)

    except ValueError:
        return JSONResponse(content={"error": "Invalid account_id format"}, status_code=400)
    except Exception as e:
        logger.error(f"Error starting MusicBrainz OAuth: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.get("/callback")
async def oauth_callback(request: Request):
    """Handle the MusicBrainz OAuth2 callback and exchange the code for tokens."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        desc = request.query_params.get("error_description", error)
        logger.error(f"MusicBrainz OAuth error from provider: {desc}")
        return (
            f"""<html><body style='font-family:sans-serif;padding:24px;'>
            <h2>MusicBrainz Authentication Failed</h2>
            <p><strong>Error:</strong> {desc}</p>
            <p>Please close this window, check your application settings, and try again.</p>
            </body></html>""",
            400,
            {"Content-Type": "text/html"},
        )

    if not code or not state:
        logger.error("MusicBrainz callback missing code or state parameter")
        return JSONResponse(content={"error": "Missing authorization code or state"}, status_code=400)

    # Decode PKCE session ID from state
    try:
        padded = state + "=" * (-len(state) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        pkce_id = payload.get("pkce_id")
        if not pkce_id:
            raise ValueError("No pkce_id in state payload")
    except Exception as e:
        logger.error(f"Failed to decode OAuth state: {e}")
        return JSONResponse(content={"error": f"Invalid state parameter: {e}"}, status_code=400)

    
    pkce = storage.get_pkce_session(pkce_id)
    if not pkce:
        return JSONResponse(content={"error": "OAuth session not found or expired. Please start the flow again."}, status_code=400)

    account_id = pkce.get("account_id")
    verifier = pkce.get("code_verifier")
    redirect_uri = pkce.get("redirect_uri")
    client_id = pkce.get("client_id")

    if not all([account_id, verifier, redirect_uri, client_id]):
        return JSONResponse(content={"error": "Incomplete OAuth session data"}, status_code=400)

    account_id = int(account_id)  # narrow type: None already excluded by all() guard above

    from core.security import decrypt_string
    raw_secret = sdk.config.get('client_secret')
    if not raw_secret:
        return JSONResponse(content={"error": "client_secret not configured"}, status_code=400)
    client_secret = decrypt_string(raw_secret)

    # Exchange code for tokens using HTTP Basic auth (client_id:client_secret)
    from core.request_manager import RequestManager
    http = RequestManager("musicbrainz_oauth")
    creds_b64 = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    resp = http.post(
        _TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
        headers={"Authorization": f"Basic {creds_b64}"},
    )

    if resp.status_code != 200:
        logger.error(f"MusicBrainz token exchange failed: {resp.status_code} — {resp.text}")
        return JSONResponse(content={"error": f"Token exchange failed (HTTP {resp.status_code})"}, status_code=400)

    token = resp.json()
    access_token = token.get("access_token")
    refresh_token = token.get("refresh_token")
    expires_in = int(token.get("expires_in") or 3600)
    scope = token.get("scope") or _SCOPES
    expires_at = int(time.time() + expires_in - 60)

    if not access_token:
        return JSONResponse(content={"error": "No access_token in token response"}, status_code=400)

    from core.security import encrypt_string
    sdk.accounts.save_token(
        account_id=account_id, access_token=encrypt_string(access_token), refresh_token=encrypt_string(refresh_token) if refresh_token else None, expires_at=expires_at)
    sdk.accounts.mark_account_authenticated(account_id)
    storage.delete_pkce_session(pkce_id)

    # Enrich account with the authenticated MusicBrainz username
    try:
        profile_resp = http.get(
            _USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if profile_resp.status_code == 200:
            profile = profile_resp.json()
            username = profile.get("sub") or profile.get("name") or ""
            if username:
                sdk.accounts.update_account_name(account_id, username)
                storage.set_account_user_id(account_id, username)
    except Exception as e:
        logger.warning(f"Failed to fetch MusicBrainz user profile after auth: {e}")

    logger.info(f"MusicBrainz account {account_id} authenticated successfully")
    return (
        """<html><body style='font-family:sans-serif;padding:24px;text-align:center;'>
        <h2 style='color:#21ba45;'>&#10003; MusicBrainz Authenticated!</h2>
        <p>You may close this window and return to Echosync.</p>
        <script>setTimeout(function(){ window.close(); }, 2000);</script>
        </body></html>""",
        200,
        {"Content-Type": "text/html"},
    )

@router.get("/settings")
def get_settings():
    """Get MusicBrainz server settings (e.g. api_base_url)."""
    try:
        from core.nexus_framework.plugin_SDK import sdk
        api_base_url = sdk.config.get('api_base_url', 'https://musicbrainz.org/ws/2')
        return JSONResponse(content={"settings": {"api_base_url": api_base_url}}, status_code=200)
    except Exception as e:
        logger.error(f"Error reading MusicBrainz settings: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)

@router.post("/settings")
async def save_settings(request: Request):
    """Save MusicBrainz server settings."""
    try:
        from core.nexus_framework.plugin_SDK import sdk
        payload = await request.json() or {}
        settings = payload.get("settings", {})
        if "api_base_url" in settings:
            sdk.config.set('api_base_url', settings["api_base_url"].strip())
        return JSONResponse(content={"success": True}, status_code=200)
    except Exception as e:
        logger.error(f"Error saving MusicBrainz settings: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)

@router.get("/credentials")
def get_credentials():
    """Get MusicBrainz OAuth credentials status."""
    try:
        from core.nexus_framework.plugin_SDK import sdk
        client_id = sdk.config.get('client_id', '')
        client_secret = sdk.config.get('client_secret', '')
        return JSONResponse(content={"credentials": {"client_id": client_id, "has_secret": bool(client_secret)}}, status_code=200)
    except Exception as e:
        logger.error(f"Error reading MusicBrainz credentials: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)

@router.post("/credentials")
async def save_credentials(request: Request):
    """Save MusicBrainz OAuth credentials."""
    try:
        from core.nexus_framework.plugin_SDK import sdk
        from core.security import encrypt_string
        payload = await request.json() or {}
        creds = payload.get("credentials", {})
        if "client_id" in creds:
            sdk.config.set('client_id', creds["client_id"].strip())
        if "client_secret" in creds and creds["client_secret"].strip():
            sdk.config.set('client_secret', encrypt_string(creds["client_secret"].strip()))
        return JSONResponse(content={"success": True}, status_code=200)
    except Exception as e:
        logger.error(f"Error saving MusicBrainz credentials: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)
