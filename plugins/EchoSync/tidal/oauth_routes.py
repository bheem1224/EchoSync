"""Tidal OAuth routes - handles PKCE-based OAuth flow for Tidal accounts."""
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from core.nexus_framework.plugin_SDK import sdk
from services.storage_service import get_storage_service
from core.tiered_logger import get_logger
import json
import base64
import uuid
import urllib.parse
import time

logger = get_logger("tidal_oauth")
storage = get_storage_service()
router = APIRouter(prefix="/api/tidal")


@router.get('/auth')
def begin_auth(request: Request):
    """
    Start OAuth flow for Tidal with PKCE.
    Query params: account_id (required)
    
    Tidal uses per-account credentials, so account_id is mandatory.
    Returns an auth URL with PKCE challenge.
    """
    try:
        account_id = request.query_params.get('account_id')
        if not account_id:
            return JSONResponse(content={'error': 'account_id is required'}, status_code=400)

        account_id = int(account_id)
        

        # Verify account exists
        accounts = sdk.accounts.get_all()
        account = next((a for a in accounts if a.get('id') == account_id), None)
        if not account:
            return JSONResponse(content={'error': 'Account not found'}, status_code=404)

        # Load per-account credentials from storage
        # Tidal requires per-account client_id and client_secret
        client_id = storage.get_account_config(account_id, 'client_id')
        client_secret = storage.get_account_config(account_id, 'client_secret')
        
        # Debug logging
        logger.info(f"Tidal auth for account {account_id}: client_id={'present' if client_id else 'MISSING'}, client_secret={'present' if client_secret else 'MISSING'}")
        
        # Global redirect URI (shared across all Tidal accounts)
        from core.network_utils import get_lan_ip
        redirect_uri = f"https://{get_lan_ip()}:5001/api/oauth/callback/plugins/tidal"
        
        if not client_id or not client_secret:
            # Try to fetch account to see if it exists
            accounts = sdk.accounts.get_all()
            account_exists = any(a.get('id') == account_id for a in accounts)
            logger.error(f"Tidal account {account_id} exists: {account_exists}, but credentials missing")
            return JSONResponse(content={'error': 'Account missing client_id or client_secret. Please edit the account to configure credentials.'}, status_code=400)

        # Generate PKCE values
        from .client import TidalClient
        temp_client = TidalClient(account_id=str(account_id))
        verifier, challenge = temp_client.generate_pkce()

        # Create unique PKCE session and store in config.db
        pkce_id = str(uuid.uuid4())
        success = storage.store_pkce_session(
            pkce_id=pkce_id,
            service='tidal',
            account_id=account_id,
            code_verifier=verifier,
            code_challenge=challenge,
            redirect_uri=redirect_uri,
            client_id=client_id,
            ttl_seconds=600  # 10 minutes
        )
        
        if not success:
            return JSONResponse(content={'error': 'Failed to store PKCE session'}, status_code=500)

        # Cleanup expired PKCE sessions
        storage.cleanup_expired_pkce_sessions()

        # Build state containing only pkce_id
        state_payload = {'pkce_id': pkce_id}
        state_bytes = json.dumps(state_payload).encode('utf-8')
        state = base64.urlsafe_b64encode(state_bytes).decode('utf-8').rstrip('=')

        # Build authorization URL
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': 'user.read playlists.read',
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
            'state': state,
        }
        
        auth_url = f"https://login.tidal.com/authorize?{urllib.parse.urlencode(params)}"
        
        logger.info(f"Generated Tidal auth URL for account {account_id}")
        return JSONResponse(content={'auth_url': auth_url}, status_code=200)

    except ValueError:
        return JSONResponse(content={'error': 'Invalid account_id format'}, status_code=400)
    except Exception as e:
        logger.error(f"Error creating Tidal auth URL: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.get('/callback')
def oauth_callback(request: Request):
    """
    Handle Tidal OAuth callback and exchange code for tokens using PKCE.
    Expects query params: code, state
    """
    try:
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')

        # Handle user-denied or provider errors
        if error:
            error_description = request.query_params.get('error_description', error)
            logger.error(f"Tidal OAuth error: {error_description}")
            html = f"""<html><body style='font-family: Arial, sans-serif;'>
                <h2>Tidal Authentication Failed</h2>
                <p><strong>Error:</strong> {error_description}</p>
                <p>Please try again or check your Tidal app settings.</p>
            </body></html>"""
            return HTMLResponse(content=html, status_code=400)

        if not code or not state:
            logger.error("OAuth callback missing code or state parameter")
            return JSONResponse(content={"error": "Missing authorization code or state"}, status_code=400)

        # Decode state to get PKCE session ID
        try:
            padded_state = state + '=' * (-len(state) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded_state.encode('utf-8')).decode('utf-8'))
            pkce_id = payload.get('pkce_id')
            
            if not pkce_id:
                raise ValueError("State payload missing pkce_id")
                
        except Exception as e:
            logger.error(f"Failed to decode state: {e}")
            return JSONResponse(content={"error": f"Invalid state parameter: {e}"}, status_code=400)

        # Retrieve PKCE entry from config.db
        
        pkce_entry = storage.get_pkce_session(pkce_id)
        
        if not pkce_entry:
            logger.error(f"No PKCE entry found for id={pkce_id[:8]}...")
            return JSONResponse(content={"error": "PKCE session not found or expired"}, status_code=400)

        account_id = pkce_entry.get('account_id')
        code_verifier = pkce_entry.get('code_verifier')
        redirect_uri = pkce_entry.get('redirect_uri')
        client_id = pkce_entry.get('client_id')

        if not all([account_id, code_verifier, redirect_uri, client_id]):
            return JSONResponse(content={"error": "Incomplete PKCE session data"}, status_code=400)

        # Load client_secret from account config
        from core.security import decrypt_string
        client_secret = storage.get_account_config(account_id, 'client_secret')
        if not client_secret:
            return JSONResponse(content={"error": "Account missing client_secret"}, status_code=400)
        client_secret = decrypt_string(client_secret)

        # Exchange authorization code for tokens
        from sdk.http_client import HttpClient
        http_client = HttpClient(provider='tidal')
        
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'code_verifier': code_verifier
        }
        
        logger.info(f"Exchanging code for tokens (account {account_id})")
        response = http_client.post('https://auth.tidal.com/v1/oauth2/token', data=token_data)
        
        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            return JSONResponse(content={"error": "Failed to exchange code for token"}, status_code=400)

        token_info = response.json()
        access_token = token_info.get('access_token')
        refresh_token = token_info.get('refresh_token')
        expires_in = token_info.get('expires_in', 3600)
        expires_at = int(time.time() + expires_in - 60)
        scope = token_info.get('scope') or 'user.read playlists.read'

        if not access_token:
            return JSONResponse(content={"error": "No access token in response"}, status_code=400)

        from core.security import encrypt_string
        # Persist tokens to storage
        try:
            sdk.accounts.save_token(
                account_id, encrypt_string(access_token), encrypt_string(refresh_token) if refresh_token else None, expires_at)
            sdk.accounts.mark_account_authenticated(account_id)
            logger.info(f"Tokens saved for Tidal account {account_id}")
        except Exception as e:
            logger.error(f"Failed to persist tokens: {e}")

        # Clean up one-time PKCE session
        storage.delete_pkce_session(pkce_id)

        # Redirect back to UI
        ui_base = sdk.config.get('base_url')
        if ui_base:
            ui_redirect = ui_base.rstrip('/') + '/settings/music-services'
        else:
            # Use actual request host instead of hardcoded localhost
            scheme = request.url.scheme
            host = request.url.netloc
            ui_redirect = f'{scheme}://{host}/settings/music-services'
            
        return RedirectResponse(url=ui_redirect)

    except Exception as e:
        logger.error(f"Tidal callback error: {e}", exc_info=True)
        error_html = f"""<html><body style='font-family: Arial, sans-serif;'>
            <h2>Tidal Authentication Failed</h2>
            <p>{str(e)}</p>
        </body></html>"""
        return HTMLResponse(content=error_html, status_code=500)
