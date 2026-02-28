"""Tidal OAuth routes - handles PKCE-based OAuth flow for Tidal accounts."""
from flask import Blueprint, request, jsonify, redirect
from core.storage import get_storage_service
from core.tiered_logger import get_logger
import json
import base64
import uuid
import urllib.parse
import time

logger = get_logger("tidal_oauth")
bp = Blueprint("tidal_oauth", __name__, url_prefix="/api/tidal")


@bp.get('/auth')
def begin_auth():
    """
    Start OAuth flow for Tidal with PKCE.
    Query params: account_id (required)
    
    Tidal uses per-account credentials, so account_id is mandatory.
    Returns an auth URL with PKCE challenge.
    """
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            return jsonify({'error': 'account_id is required'}), 400

        account_id = int(account_id)
        storage = get_storage_service()

        # Verify account exists
        accounts = storage.list_accounts('tidal')
        account = next((a for a in accounts if a.get('id') == account_id), None)
        if not account:
            return jsonify({'error': 'Account not found'}), 404

        # Load per-account credentials from storage
        # Tidal requires per-account client_id and client_secret
        client_id = storage.get_account_config(account_id, 'client_id')
        client_secret = storage.get_account_config(account_id, 'client_secret')
        
        # Debug logging
        logger.info(f"Tidal auth for account {account_id}: client_id={'present' if client_id else 'MISSING'}, client_secret={'present' if client_secret else 'MISSING'}")
        
        # Global redirect URI (shared across all Tidal accounts)
        redirect_uri = storage.get_service_config('tidal', 'redirect_uri') or 'http://127.0.0.1:8000/api/tidal/callback'
        
        if not client_id or not client_secret:
            # Try to fetch account to see if it exists
            accounts = storage.list_accounts('tidal')
            account_exists = any(a.get('id') == account_id for a in accounts)
            logger.error(f"Tidal account {account_id} exists: {account_exists}, but credentials missing")
            return jsonify({'error': 'Account missing client_id or client_secret. Please edit the account to configure credentials.'}), 400

        # Generate PKCE values
        from providers.tidal.client import TidalClient
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
            return jsonify({'error': 'Failed to store PKCE session'}), 500

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
        return jsonify({'auth_url': auth_url}), 200

    except ValueError:
        return jsonify({'error': 'Invalid account_id format'}), 400
    except Exception as e:
        logger.exception(f"Action failed for tidal begin_auth: {e}")
        return jsonify({'error': str(e)}), 500


@bp.get('/callback')
def oauth_callback():
    """
    Handle Tidal OAuth callback and exchange code for tokens using PKCE.
    Expects query params: code, state
    """
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')

        # Handle user-denied or provider errors
        if error:
            error_description = request.args.get('error_description', error)
            logger.error(f"Tidal OAuth error: {error_description}")
            html = f"""<html><body style='font-family: Arial, sans-serif;'>
                <h2>Tidal Authentication Failed</h2>
                <p><strong>Error:</strong> {error_description}</p>
                <p>Please try again or check your Tidal app settings.</p>
            </body></html>"""
            return html, 400, {"Content-Type": "text/html"}

        if not code or not state:
            logger.error("OAuth callback missing code or state parameter")
            return jsonify({"error": "Missing authorization code or state"}), 400

        # Decode state to get PKCE session ID
        try:
            padded_state = state + '=' * (-len(state) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded_state.encode('utf-8')).decode('utf-8'))
            pkce_id = payload.get('pkce_id')
            
            if not pkce_id:
                raise ValueError("State payload missing pkce_id")
                
        except Exception as e:
            logger.error(f"Failed to decode state: {e}")
            return jsonify({"error": f"Invalid state parameter: {e}"}), 400

        # Retrieve PKCE entry from config.db
        storage = get_storage_service()
        pkce_entry = storage.get_pkce_session(pkce_id)
        
        if not pkce_entry:
            logger.error(f"No PKCE entry found for id={pkce_id[:8]}...")
            return jsonify({"error": "PKCE session not found or expired"}), 400

        account_id = pkce_entry.get('account_id')
        code_verifier = pkce_entry.get('code_verifier')
        redirect_uri = pkce_entry.get('redirect_uri')
        client_id = pkce_entry.get('client_id')

        if not all([account_id, code_verifier, redirect_uri, client_id]):
            return jsonify({"error": "Incomplete PKCE session data"}), 400

        # Load client_secret from account config
        client_secret = storage.get_account_config(account_id, 'client_secret')
        if not client_secret:
            return jsonify({"error": "Account missing client_secret"}), 400

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
            return jsonify({"error": "Failed to exchange code for token"}), 400

        token_info = response.json()
        access_token = token_info.get('access_token')
        refresh_token = token_info.get('refresh_token')
        expires_in = token_info.get('expires_in', 3600)
        expires_at = int(time.time() + expires_in - 60)
        scope = token_info.get('scope') or 'user.read playlists.read'

        if not access_token:
            return jsonify({"error": "No access token in response"}), 400

        # Persist tokens to storage
        try:
            storage.save_account_token(account_id, access_token, refresh_token, 'Bearer', expires_at, scope)
            storage.mark_account_authenticated(account_id)
            logger.info(f"Tokens saved for Tidal account {account_id}")
        except Exception as e:
            logger.error(f"Failed to persist tokens: {e}")

        # Clean up one-time PKCE session
        storage.delete_pkce_session(pkce_id)

        # Redirect back to UI
        ui_base = storage.get_service_config('webui', 'base_url')
        if ui_base:
            ui_redirect = ui_base.rstrip('/') + '/settings/music-services'
        else:
            ui_redirect = 'http://localhost:5173/settings/music-services'
            
        return redirect(ui_redirect)

    except Exception as e:
        logger.exception(f"Action failed for tidal callback: {e}")
        error_html = f"""<html><body style='font-family: Arial, sans-serif;'>
            <h2>Tidal Authentication Failed</h2>
            <p>{str(e)}</p>
        </body></html>"""
        return error_html, 500, {"Content-Type": "text/html"}
