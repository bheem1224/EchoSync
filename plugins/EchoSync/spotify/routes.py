"""Spotify provider routes for FastAPI."""

import time

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from spotipy.oauth2 import SpotifyOAuth

from core.network_utils import get_lan_ip
from core.nexus_framework.plugin_SDK import sdk
from core.security import decrypt_string
from core.tiered_logger import get_logger

logger = get_logger("spotify_routes")
router = APIRouter()


def _get_redirect_uri() -> str:
    """Derive standardized OAuth redirect URI using sidecar port 5001."""
    lan_ip = get_lan_ip()
    return f"https://{lan_ip}:5001/api/oauth/callback/plugins/spotify"


# ── Settings ──────────────────────────────────────────────────────────────────


@router.get("/settings")
@router.get("settings")
def get_settings():
    """Get Spotify global settings and credentials."""
    try:
        client_id = ""
        client_secret = ""
        redirect_uri = ""
        try:
            client_id = sdk.config.get("client_id", "") or ""
            client_secret = sdk.secrets.get("client_secret", "") or ""
            redirect_uri = sdk.config.get("redirect_uri", "") or ""
        except Exception:
            pass

        # Fallback to SDK service_config if not yet in primary plugin sdk namespace
        if not client_id or not client_secret:
            for lookup_key in (2391116200, "Spotify", "EchoSync.Spotify", "spotify"):
                client_id = client_id or sdk.config.get_for_service(lookup_key, "client_id") or ""
                client_secret = client_secret or sdk.config.get_for_service(lookup_key, "client_secret") or ""
                redirect_uri = redirect_uri or sdk.config.get_for_service(lookup_key, "redirect_uri") or ""
                if client_id and client_secret:
                    break

        # Legacy storage fallback
        if not client_id or not client_secret or not redirect_uri:
            from services.storage_service import get_storage_service

            storage = get_storage_service()
            client_id = client_id or storage.get_service_config("spotify", "client_id") or ""
            raw_sec = storage.get_service_config("spotify", "client_secret")
            if raw_sec and not client_secret:
                client_secret = decrypt_string(raw_sec) if raw_sec.startswith("enc:") else raw_sec
            redirect_uri = redirect_uri or storage.get_service_config("spotify", "redirect_uri") or ""

        if not redirect_uri:
            redirect_uri = _get_redirect_uri()

        return JSONResponse(
            content={
                "settings": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                }
            }
        )
    except Exception as e:
        logger.error(f"Error getting Spotify settings: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to get Spotify settings"}, status_code=500)


@router.post("/settings")
@router.post("settings")
async def save_settings(request: Request):
    """Save Spotify global settings and credentials."""
    try:
        try:
            data = await request.json() or {}
        except Exception:
            data = {}
        client_id = (data.get("client_id") or "").strip()
        client_secret = (data.get("client_secret") or "").strip()
        redirect_uri = (data.get("redirect_uri") or "").strip() or _get_redirect_uri()

        if client_id:
            sdk.config.set("client_id", client_id)
        if client_secret:
            sdk.secrets.set("client_secret", client_secret)
        if redirect_uri:
            sdk.config.set("redirect_uri", redirect_uri)

        # Also mirror into canonical service_config via SDK
        for lookup_key in (2391116200, "Spotify", "EchoSync.Spotify"):
            if client_id:
                sdk.config.set_for_service(lookup_key, "client_id", client_id, is_sensitive=False)
            if client_secret:
                sdk.config.set_for_service(lookup_key, "client_secret", client_secret, is_sensitive=True)
            if redirect_uri:
                sdk.config.set_for_service(lookup_key, "redirect_uri", redirect_uri, is_sensitive=False)

        # Also mirror into storage for legacy callers
        from services.storage_service import get_storage_service

        storage = get_storage_service()
        storage.ensure_service(
            "spotify",
            service_type="streaming",
            description="Spotify music streaming service",
        )
        if client_id:
            storage.set_service_config("spotify", "client_id", client_id, is_sensitive=False)
        if client_secret:
            storage.set_service_config("spotify", "client_secret", client_secret, is_sensitive=True)
        if redirect_uri:
            storage.set_service_config("spotify", "redirect_uri", redirect_uri, is_sensitive=False)

        logger.info("Saved Spotify global credentials successfully.")
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error saving Spotify settings: {e}", exc_info=True)
        return JSONResponse(content={"error": f"Failed to save Spotify settings: {e}"}, status_code=500)


# ── Accounts ──────────────────────────────────────────────────────────────────


@router.get("/accounts")
def list_accounts():
    """List all Spotify accounts, preserving legacy database rows across service aliases."""
    try:
        seen_ids: set[int] = set()
        merged_rows: list[dict] = []

        def _collect(rows):
            for a in rows or []:
                aid = a.get("id")
                if aid is not None and aid in seen_ids:
                    continue
                if aid is not None:
                    seen_ids.add(int(aid))
                merged_rows.append(a)

        try:
            _collect(sdk.accounts.get_all())
        except Exception as sdk_err:
            logger.debug(f"sdk.accounts.get_all() fallback: {sdk_err}")

        try:
            from services.storage_service import get_storage_service

            _collect(get_storage_service().list_accounts("spotify"))
        except Exception as st_err:
            logger.debug(f"storage.list_accounts('spotify') fallback: {st_err}")

        accounts = []
        for a in merged_rows:
            accounts.append(
                {
                    "id": a.get("id"),
                    "account_name": a.get("account_name") or a.get("display_name") or "Unnamed Account",
                    "display_name": a.get("display_name") or a.get("account_name") or "Unnamed Account",
                    "user_id": a.get("user_id"),
                    "is_active": bool(a.get("is_active")),
                    "is_authenticated": bool(a.get("is_authenticated")),
                }
            )

        return JSONResponse(content={"accounts": accounts})
    except Exception as e:
        logger.error(f"Error listing Spotify accounts: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to list Spotify accounts"}, status_code=500)


@router.post("/accounts")
async def create_account(request: Request):
    """Create a new Spotify account slot."""
    try:
        try:
            data = await request.json() or {}
        except Exception:
            data = {}
        account_name = (data.get("account_name") or data.get("display_name") or "").strip()
        if not account_name:
            return JSONResponse(content={"error": "account_name is required"}, status_code=400)

        account_id = sdk.accounts.ensure_account(account_name=account_name, display_name=account_name)
        if not account_id:
            from services.storage_service import get_storage_service

            account_id = get_storage_service().ensure_account(
                "spotify", account_name=account_name, display_name=account_name
            )
        if not account_id:
            return JSONResponse(content={"error": "Failed to create account"}, status_code=500)

        return JSONResponse(
            content={
                "account": {
                    "id": account_id,
                    "account_name": account_name,
                    "display_name": account_name,
                    "is_active": False,
                    "is_authenticated": False,
                }
            },
            status_code=201,
        )
    except Exception as e:
        logger.error(f"Error creating Spotify account: {e}", exc_info=True)
        return JSONResponse(content={"error": f"Failed to create Spotify account: {e}"}, status_code=500)


@router.put("/accounts/{account_id}/activate")
@router.post("/accounts/{account_id}/activate")
async def activate_account(account_id: int, request: Request):
    """Toggle the active flag on a Spotify account."""
    try:
        data = await request.json() or {}
        is_active = bool(data.get("is_active", True))
        sdk.accounts.toggle_account_active(account_id, is_active)
        return JSONResponse(content={"success": True, "is_active": is_active})
    except Exception as e:
        logger.error(f"Error activating Spotify account {account_id}: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to activate Spotify account"}, status_code=500)


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int):
    """Delete a Spotify account and associated tokens."""
    try:
        sdk.accounts.delete_account(account_id)
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error deleting Spotify account {account_id}: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to delete Spotify account"}, status_code=500)


# ── OAuth ─────────────────────────────────────────────────────────────────────


@router.get("/auth")
def begin_auth(account_id: int | None = None):
    """Start OAuth flow for Spotify. Returns an auth URL to redirect the user to."""
    try:
        if not account_id:
            return JSONResponse(content={"error": "account_id parameter is required"}, status_code=400)

        client_id = sdk.config.get("client_id")
        client_secret = sdk.secrets.get("client_secret")

        if not client_id or not client_secret:
            for lookup_key in (2391116200, "Spotify", "EchoSync.Spotify"):
                client_id = client_id or sdk.config.get_for_service(lookup_key, "client_id")
                client_secret = client_secret or sdk.config.get_for_service(lookup_key, "client_secret")
                if client_id and client_secret:
                    break

        if not client_id or not client_secret:
            from services.storage_service import get_storage_service

            storage = get_storage_service()
            client_id = client_id or storage.get_service_config("spotify", "client_id")
            raw_sec = storage.get_service_config("spotify", "client_secret")
            if raw_sec:
                client_secret = decrypt_string(raw_sec) if raw_sec.startswith("enc:") else raw_sec

        if not client_id or not client_secret:
            return JSONResponse(
                content={"error": "Spotify client_id or client_secret not configured"},
                status_code=400,
            )

        def _on_spotify_tokens(tokens: dict):
            from core.task_manager.task_queue import job_queue

            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in", 3600)
            expires_at = int(time.time() + expires_in)
            token_scope = (
                tokens.get("scope")
                or "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email"
            )

            if not access_token:
                logger.error(f"No access token in Spotify token payload for account {account_id}")
                return

            with job_queue.db_write_lease(task_name=f"spotify_save_tokens_{account_id}"):
                sdk.accounts.save_token(
                    account_id=account_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    scope=token_scope,
                )
                sdk.accounts.mark_account_authenticated(account_id)
                sdk.accounts.toggle_account_active(account_id, True)
                logger.info(f"Spotify tokens persisted under db_write_lease for account {account_id}")

        session_handle = sdk.oauth.create_session(
            provider="spotify",
            auth_url="https://accounts.spotify.com/authorize",
            token_url="https://accounts.spotify.com/api/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes="user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email playlist-modify-public playlist-modify-private",
            use_pkce=False,
            account_id=account_id,
            on_token=_on_spotify_tokens,
            extra_auth_params={"show_dialog": "true"},
        )

        logger.info(f"Generated Spotify centralized auth session for account {account_id}")
        return JSONResponse(content={"auth_url": session_handle.auth_url}, status_code=200)
    except Exception as e:
        logger.error(f"Error creating Spotify auth URL: {e}", exc_info=True)
        return JSONResponse(
            content={"error": "Failed to initiate Spotify authentication"},
            status_code=500,
        )


@router.get("/callback")
def oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    """Handle Spotify OAuth callback and exchange code for tokens."""
    from core.nexus_framework.plugin_loader import PluginRegistry

    if PluginRegistry.is_plugin_disabled("spotify"):
        return JSONResponse(content={"error": "Spotify provider is disabled"}, status_code=403)
    try:
        if error:
            import html as html_escape

            desc = html_escape.escape(error_description or error or "Unknown error")
            logger.error(f"Spotify OAuth error: {desc}")
            html = f"<html><body style='font-family: Arial, sans-serif;'><h2>Spotify Authentication Failed</h2><p><strong>Error:</strong> {desc}</p><p>Please try again or check your Spotify app settings.</p></body></html>"
            return HTMLResponse(content=html, status_code=400)

        if not code:
            logger.error("OAuth callback missing code parameter")
            return JSONResponse(content={"error": "Missing authorization code"}, status_code=400)

        if not state:
            logger.error("OAuth callback missing state parameter (account id)")
            return JSONResponse(content={"error": "Missing state parameter (account ID)"}), 400

        try:
            account_id = int(state)
        except (ValueError, TypeError):
            account_id = None

        client_id = sdk.config.get("client_id")
        client_secret = sdk.secrets.get("client_secret")

        if not client_id or not client_secret:
            from services.storage_service import get_storage_service

            storage = get_storage_service()
            client_id = client_id or storage.get_service_config("spotify", "client_id")
            raw_sec = storage.get_service_config("spotify", "client_secret")
            if raw_sec:
                client_secret = decrypt_string(raw_sec) if raw_sec.startswith("enc:") else raw_sec

        if not client_id or not client_secret:
            return JSONResponse(
                content={"error": "Spotify client_id/client_secret not configured"},
                status_code=400,
            )

        from .client import CallbackBypassCacheHandler

        redirect_uri = _get_redirect_uri()
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email",
            cache_handler=CallbackBypassCacheHandler(),
        )

        try:
            token_info = auth_manager.get_access_token(code, as_dict=True)
        except TypeError:
            token_info = auth_manager.get_access_token(code)

        if not token_info:
            return JSONResponse(content={"error": "Failed to exchange code for token"}, status_code=400)

        access_token = token_info.get("access_token")
        refresh_token = token_info.get("refresh_token")
        expires_at = token_info.get("expires_at")
        scope = (
            token_info.get("scope")
            or "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email"
        )

        if not account_id:
            account_id = sdk.accounts.ensure_account(account_name=f"spotify_{int(time.time())}")

        from core.task_manager.task_queue import job_queue

        with job_queue.db_write_lease(task_name=f"spotify_cb_save_tokens_{account_id}"):
            sdk.accounts.save_token(
                account_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                scope=scope,
            )
            sdk.accounts.mark_account_authenticated(account_id)
            sdk.accounts.toggle_account_active(account_id, True)

        html = """
        <html>
        <body style='font-family: Arial, sans-serif; text-align: center; padding: 40px; background: #0f172a; color: #f8fafc;'>
            <h2 style='color: #10b981;'>Spotify Authentication Successful!</h2>
            <p>Your Spotify account has been linked. You can close this window now.</p>
            <script>
                if (window.opener) {
                    window.close();
                } else {
                    setTimeout(function() { window.location.href = '/settings/music-services'; }, 1500);
                }
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=200)

    except Exception as e:
        logger.error(f"Spotify callback error: {e}", exc_info=True)
        html = "<html><body style='font-family: Arial, sans-serif;'><h2>Spotify Authentication Failed</h2><p>An unexpected error occurred during Spotify authentication. Please try again.</p></body></html>"
        return HTMLResponse(content=html, status_code=500)


# Alias bp for backward compatibility
bp = router
