"""Spotify provider routes for FastAPI."""

import time
import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from spotipy.oauth2 import SpotifyOAuth

from core.tiered_logger import get_logger
from core.nexus_framework.plugin_SDK import sdk
from core.network_utils import get_lan_ip
from core.security import decrypt_string, encrypt_string

logger = get_logger("spotify_routes")
router = APIRouter()


def _get_redirect_uri() -> str:
    """Derive standardized OAuth redirect URI using sidecar port 5001."""
    lan_ip = get_lan_ip()
    return f"https://{lan_ip}:5001/api/oauth/callback/plugins/spotify"


# ── Settings ──────────────────────────────────────────────────────────────────

@router.get('/settings')
@router.get('settings')
def get_settings():
    """Get Spotify global settings and credentials."""
    try:
        client_id = ''
        client_secret = ''
        try:
            client_id = sdk.config.get('client_id', '') or ''
            client_secret = sdk.secrets.get('client_secret', '') or ''
        except Exception:
            pass

        redirect_uri = _get_redirect_uri()

        # Fallback to database service_config if not yet in plugin sdk namespace
        if not client_id or not client_secret:
            from database.config_database import get_config_database
            db = get_config_database()
            svc_id = db.get_service_id(2391116200) or db.get_service_id('Spotify') or db.get_service_id('EchoSync.Spotify')
            if svc_id:
                client_id = client_id or db.get_service_config(svc_id, 'client_id') or ''
                client_secret = client_secret or db.get_service_config(svc_id, 'client_secret') or ''

        # Legacy storage fallback
        if not client_id or not client_secret:
            from core.file_handling.storage import get_storage_service
            storage = get_storage_service()
            client_id = client_id or storage.get_service_config('spotify', 'client_id') or ''
            raw_sec = storage.get_service_config('spotify', 'client_secret')
            if raw_sec:
                client_secret = decrypt_string(raw_sec) if raw_sec.startswith('enc:') else raw_sec

        return JSONResponse(content={
            'settings': {
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri
            }
        })
    except Exception as e:
        logger.error(f"Error getting Spotify settings: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to get Spotify settings"}, status_code=500)


@router.post('/settings')
@router.post('settings')
async def save_settings(request: Request):
    """Save Spotify global settings and credentials."""
    try:
        data = await request.json() or {}
        client_id = (data.get('client_id') or '').strip()
        client_secret = (data.get('client_secret') or '').strip()
        redirect_uri = (data.get('redirect_uri') or '').strip() or _get_redirect_uri()

        if client_id:
            sdk.config.set('client_id', client_id)
        if client_secret:
            sdk.secrets.set('client_secret', client_secret)
        if redirect_uri:
            sdk.config.set('redirect_uri', redirect_uri)

        # Also mirror into database service_config
        from database.config_database import get_config_database
        db = get_config_database()
        svc_id = db.get_service_id(2391116200) or db.get_service_id('Spotify') or db.get_service_id('EchoSync.Spotify')
        if svc_id:
            if client_id:
                db.set_service_config(svc_id, 'client_id', client_id, is_sensitive=False)
            if client_secret:
                db.set_service_config(svc_id, 'client_secret', client_secret, is_sensitive=True)
            if redirect_uri:
                db.set_service_config(svc_id, 'redirect_uri', redirect_uri, is_sensitive=False)

        # Also mirror into storage for legacy callers
        from core.file_handling.storage import get_storage_service
        storage = get_storage_service()
        storage.ensure_service('spotify', service_type='streaming', description='Spotify music streaming service')
        if client_id:
            storage.set_service_config('spotify', 'client_id', client_id, is_sensitive=False)
        if client_secret:
            storage.set_service_config('spotify', 'client_secret', client_secret, is_sensitive=True)
        if redirect_uri:
            storage.set_service_config('spotify', 'redirect_uri', redirect_uri, is_sensitive=False)

        logger.info("Saved Spotify global credentials successfully.")
        return JSONResponse(content={'success': True})
    except Exception as e:
        logger.error(f"Error saving Spotify settings: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to save Spotify settings"}, status_code=500)


# ── Accounts ──────────────────────────────────────────────────────────────────

@router.get('/accounts')
def list_accounts():
    """List all Spotify accounts."""
    try:
        db_accounts = sdk.accounts.get_all()
        accounts = []
        for a in db_accounts:
            accounts.append({
                'id': a.get('id'),
                'account_name': a.get('account_name') or a.get('display_name') or 'Unnamed Account',
                'display_name': a.get('display_name') or a.get('account_name') or 'Unnamed Account',
                'user_id': a.get('user_id'),
                'is_active': bool(a.get('is_active')),
                'is_authenticated': bool(a.get('is_authenticated')),
            })

        return JSONResponse(content={'accounts': accounts})
    except Exception as e:
        logger.error(f"Error listing Spotify accounts: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to list Spotify accounts"}, status_code=500)


@router.post('/accounts')
async def create_account(request: Request):
    """Create a new Spotify account slot."""
    try:
        data = await request.json() or {}
        account_name = (data.get('account_name') or data.get('display_name') or '').strip()
        if not account_name:
            return JSONResponse(content={'error': 'account_name is required'}, status_code=400)

        account_id = sdk.accounts.ensure_account(account_name=account_name, display_name=account_name)
        if not account_id:
            return JSONResponse(content={'error': 'Failed to create account'}, status_code=500)

        return JSONResponse(content={
            'account': {
                'id': account_id,
                'account_name': account_name,
                'display_name': account_name,
                'is_active': False,
                'is_authenticated': False,
            }
        }, status_code=201)
    except Exception as e:
        logger.error(f"Error creating Spotify account: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to create Spotify account"}, status_code=500)


@router.put('/accounts/{account_id}/activate')
@router.post('/accounts/{account_id}/activate')
async def activate_account(account_id: int, request: Request):
    """Toggle the active flag on a Spotify account."""
    try:
        data = await request.json() or {}
        is_active = bool(data.get('is_active', True))
        sdk.accounts.toggle_account_active(account_id, is_active)
        return JSONResponse(content={'success': True, 'is_active': is_active})
    except Exception as e:
        logger.error(f"Error activating Spotify account {account_id}: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to activate Spotify account"}, status_code=500)


@router.delete('/accounts/{account_id}')
def delete_account(account_id: int):
    """Delete a Spotify account and associated tokens."""
    try:
        sdk.accounts.delete_account(account_id)
        return JSONResponse(content={'success': True})
    except Exception as e:
        logger.error(f"Error deleting Spotify account {account_id}: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to delete Spotify account"}, status_code=500)


# ── OAuth ─────────────────────────────────────────────────────────────────────

@router.get('/auth')
def begin_auth(account_id: Optional[int] = None):
    """Start OAuth flow for Spotify. Returns an auth URL to redirect the user to."""
    try:
        if not account_id:
            return JSONResponse(content={'error': 'account_id parameter is required'}, status_code=400)

        client_id = sdk.config.get('client_id')
        client_secret = sdk.secrets.get('client_secret')
        redirect_uri = _get_redirect_uri()

        if not client_id or not client_secret:
            from database.config_database import get_config_database
            db = get_config_database()
            svc_id = db.get_service_id(2391116200) or db.get_service_id('Spotify') or db.get_service_id('EchoSync.Spotify')
            if svc_id:
                client_id = client_id or db.get_service_config(svc_id, 'client_id')
                client_secret = client_secret or db.get_service_config(svc_id, 'client_secret')

        if not client_id or not client_secret:
            from core.file_handling.storage import get_storage_service
            storage = get_storage_service()
            client_id = client_id or storage.get_service_config('spotify', 'client_id')
            raw_sec = storage.get_service_config('spotify', 'client_secret')
            if raw_sec:
                client_secret = decrypt_string(raw_sec) if raw_sec.startswith('enc:') else raw_sec

        if not client_id or not client_secret:
            return JSONResponse(content={'error': 'Spotify client_id or client_secret not configured'}, status_code=400)

        scope = "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email playlist-modify-public playlist-modify-private"
        state = str(account_id)

        from .client import CallbackBypassCacheHandler
        sp_oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            show_dialog=True,
            cache_handler=CallbackBypassCacheHandler()
        )
        auth_url = sp_oauth.get_authorize_url()
        logger.info(f"Generated Spotify authorize URL for account {account_id} with redirect_uri {redirect_uri}")
        return JSONResponse(content={'auth_url': auth_url}, status_code=200)
    except Exception as e:
        logger.error(f"Error creating Spotify auth URL: {e}", exc_info=True)
        return JSONResponse(content={'error': "Failed to initiate Spotify authentication"}, status_code=500)


@router.get('/callback')
def oauth_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None, error_description: Optional[str] = None):
    """Handle Spotify OAuth callback and exchange code for tokens."""
    from core.nexus_framework.plugin_loader import PluginRegistry
    if PluginRegistry.is_plugin_disabled('spotify'):
        return JSONResponse(content={'error': 'Spotify provider is disabled'}, status_code=403)
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

        client_id = sdk.config.get('client_id')
        client_secret = sdk.secrets.get('client_secret')
        redirect_uri = _get_redirect_uri()

        if not client_id or not client_secret:
            from core.file_handling.storage import get_storage_service
            storage = get_storage_service()
            client_id = client_id or storage.get_service_config('spotify', 'client_id')
            raw_sec = storage.get_service_config('spotify', 'client_secret')
            if raw_sec:
                client_secret = decrypt_string(raw_sec) if raw_sec.startswith('enc:') else raw_sec

        if not client_id or not client_secret:
            return JSONResponse(content={"error": "Spotify client_id/client_secret not configured"}, status_code=400)

        from .client import CallbackBypassCacheHandler
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email",
            cache_handler=CallbackBypassCacheHandler()
        )

        try:
            token_info = auth_manager.get_access_token(code, as_dict=True)
        except TypeError:
            token_info = auth_manager.get_access_token(code)

        if not token_info:
            return JSONResponse(content={"error": "Failed to exchange code for token"}, status_code=400)

        access_token = token_info.get('access_token')
        refresh_token = token_info.get('refresh_token')
        expires_at = token_info.get('expires_at')
        scope = token_info.get('scope') or "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email"

        if not account_id:
            account_id = sdk.accounts.ensure_account(account_name=f"spotify_{int(time.time())}")

        sdk.accounts.save_token(account_id, access_token=access_token, refresh_token=refresh_token, expires_at=expires_at, scope=scope)
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
