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

from flask import Blueprint, jsonify, request

from core.file_handling.storage import get_storage_service
from core.tiered_logger import get_logger

logger = get_logger("musicbrainz_routes")

bp = Blueprint("musicbrainz_routes", __name__, url_prefix="/api/musicbrainz")

_AUTH_URL = "https://musicbrainz.org/oauth2/authorize"
_TOKEN_URL = "https://musicbrainz.org/oauth2/token"
_USERINFO_URL = "https://musicbrainz.org/oauth2/userinfo"
# Scopes used: profile/email for display name, submit_isrc for fingerprint contribution,
# tag/rating/collection for interactive editing features.
_SCOPES = "profile email submit_isrc tag rating collection"


# ── Account Management ────────────────────────────────────────────────────────

@bp.get("/accounts")
def list_accounts():
    """List all MusicBrainz accounts with authentication status."""
    try:
        from core.provider import ProviderRegistry
        if ProviderRegistry.is_provider_disabled("musicbrainz"):
            return jsonify({"accounts": [], "redirect_uri": ""}), 200

        storage = get_storage_service()
        storage.ensure_service(
            "musicbrainz",
            display_name="MusicBrainz",
            service_type="metadata",
            description="Open music encyclopedia providing comprehensive metadata",
        )

        db_accounts = storage.list_accounts("musicbrainz")
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

        from plugins.musicbrainz.client import MusicBrainzClient
        redirect_uri = MusicBrainzClient().get_oauth_redirect_uri()

        client_id = storage.get_service_config("musicbrainz", "client_id")
        client_secret_configured = bool(storage.get_service_config("musicbrainz", "client_secret"))

        return jsonify({
            "accounts": accounts,
            "redirect_uri": redirect_uri,
            "client_id_configured": bool(client_id),
            "client_secret_configured": client_secret_configured,
        }), 200
    except Exception as e:
        logger.error(f"Error listing MusicBrainz accounts: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.post("/accounts")
def create_account():
    """Create a new named MusicBrainz account slot.

    The account holds the OAuth tokens obtained via the auth flow.
    Body: { account_name (str) }
    """
    try:
        payload = request.get_json(force=True) or {}
        account_name = (payload.get("account_name") or "").strip()
        if not account_name:
            return jsonify({"error": "account_name is required"}), 400

        storage = get_storage_service()
        storage.ensure_service("musicbrainz", display_name="MusicBrainz", service_type="metadata")

        account_id = storage.ensure_account(
            "musicbrainz",
            account_name=account_name,
            display_name=account_name,
        )
        if not account_id:
            return jsonify({"error": "Failed to create account"}), 500

        return jsonify({
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
        return jsonify({"error": str(e)}), 500


@bp.delete("/accounts/<int:account_id>")
def delete_account(account_id: int):
    """Delete a MusicBrainz account and its stored tokens."""
    try:
        storage = get_storage_service()
        ok = storage.delete_account(account_id)
        if ok:
            return jsonify({"success": True}), 200
        return jsonify({"error": "Account not found or deletion failed"}), 404
    except Exception as e:
        logger.error(f"Error deleting MusicBrainz account {account_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.put("/accounts/<int:account_id>/activate")
def activate_account(account_id: int):
    """Toggle the active flag on a MusicBrainz account."""
    try:
        payload = request.get_json(force=True) or {}
        is_active = bool(payload.get("is_active", True))
        storage = get_storage_service()
        ok = storage.toggle_account_active(account_id, is_active)
        if ok:
            return jsonify({"success": True, "is_active": is_active}), 200
        return jsonify({"error": "Failed to update account status"}), 500
    except Exception as e:
        logger.error(f"Error toggling MusicBrainz account {account_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ── OAuth2 PKCE Flow ──────────────────────────────────────────────────────────

@bp.get("/auth")
def begin_auth():
    """Start an OAuth2 PKCE authorization code flow for a MusicBrainz account.

    Query params:
        account_id (int) — existing account ID to associate the tokens with.

    Returns:
        { auth_url: str } — redirect the browser here to proceed with MusicBrainz login.
    """
    try:
        raw_id = request.args.get("account_id")
        if not raw_id:
            return jsonify({"error": "account_id is required"}), 400
        account_id = int(raw_id)

        storage = get_storage_service()

        # Verify the account exists
        accounts = storage.list_accounts("musicbrainz")
        if not any(a.get("id") == account_id for a in accounts):
            return jsonify({"error": "Account not found"}), 404

        # Application credentials must be configured before an auth flow can start
        client_id = storage.get_service_config("musicbrainz", "client_id")
        if not client_id:
            return jsonify({
                "error": (
                    "MusicBrainz client_id is not configured. "
                    "Register your application at https://musicbrainz.org/account/applications "
                    "then save the credentials on the Metadata settings page."
                )
            }), 400

        if not storage.get_service_config("musicbrainz", "client_secret"):
            return jsonify({"error": "MusicBrainz client_secret is not configured."}), 400

        # Derive redirect URI from centralized ProviderBase helper (OAuth sidecar)
        from plugins.musicbrainz.client import MusicBrainzClient
        redirect_uri = MusicBrainzClient().get_oauth_redirect_uri()

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
            return jsonify({"error": "Failed to store OAuth session"}), 500

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
        return jsonify({"auth_url": auth_url}), 200

    except ValueError:
        return jsonify({"error": "Invalid account_id format"}), 400
    except Exception as e:
        logger.error(f"Error starting MusicBrainz OAuth: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.get("/callback")
def oauth_callback():
    """Handle the MusicBrainz OAuth2 callback and exchange the code for tokens."""
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        desc = request.args.get("error_description", error)
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
        return jsonify({"error": "Missing authorization code or state"}), 400

    # Decode PKCE session ID from state
    try:
        padded = state + "=" * (-len(state) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        pkce_id = payload.get("pkce_id")
        if not pkce_id:
            raise ValueError("No pkce_id in state payload")
    except Exception as e:
        logger.error(f"Failed to decode OAuth state: {e}")
        return jsonify({"error": f"Invalid state parameter: {e}"}), 400

    storage = get_storage_service()
    pkce = storage.get_pkce_session(pkce_id)
    if not pkce:
        return jsonify({"error": "OAuth session not found or expired. Please start the flow again."}), 400

    account_id = pkce.get("account_id")
    verifier = pkce.get("code_verifier")
    redirect_uri = pkce.get("redirect_uri")
    client_id = pkce.get("client_id")

    if not all([account_id, verifier, redirect_uri, client_id]):
        return jsonify({"error": "Incomplete OAuth session data"}), 400

    account_id = int(account_id)  # narrow type: None already excluded by all() guard above

    from core.security import decrypt_string
    raw_secret = storage.get_service_config("musicbrainz", "client_secret")
    if not raw_secret:
        return jsonify({"error": "client_secret not configured"}), 400
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
        return jsonify({"error": f"Token exchange failed (HTTP {resp.status_code})"}), 400

    token = resp.json()
    access_token = token.get("access_token")
    refresh_token = token.get("refresh_token")
    expires_in = int(token.get("expires_in") or 3600)
    scope = token.get("scope") or _SCOPES
    expires_at = int(time.time() + expires_in - 60)

    if not access_token:
        return jsonify({"error": "No access_token in token response"}), 400

    from core.security import encrypt_string
    storage.save_account_token(
        account_id=account_id,
        access_token=encrypt_string(access_token),
        refresh_token=encrypt_string(refresh_token) if refresh_token else None,
        token_type="Bearer",
        expires_at=expires_at,
        scope=scope,
    )
    storage.mark_account_authenticated(account_id)
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
                storage.upsert_account(
                    service_name="musicbrainz",
                    account_id=account_id,
                    display_name=username,
                    user_id=username,
                )
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
