"""Tidal OAuth routes - handles PKCE-based OAuth flow for Tidal accounts."""
from flask import Blueprint, request, jsonify, redirect
from core.settings import config_manager
from core.account_manager import AccountManager
from core.tiered_logger import get_logger
from core.request_manager import RequestManager
import json
import base64
import uuid
import urllib.parse
import time
import requests

logger = get_logger("tidal_oauth")
bp = Blueprint("tidal_oauth", __name__, url_prefix="/api/tidal")

# Temporary in-memory store for PKCE sessions since we removed storage_service
# In a real distributed system this should be in Redis or DB
# Structure: { pkce_id: { ...data... } }
_pkce_sessions = {}

@bp.route('/auth', methods=['GET'])
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

        # Verify account exists
        accounts = AccountManager.list_accounts('tidal')
        account = next((a for a in accounts if a.get('id') == account_id), None)
        if not account:
            return jsonify({'error': 'Account not found'}), 404

        # Load per-account credentials
        client_id = account.get('client_id')
        client_secret = account.get('client_secret')
        
        # Debug logging
        logger.info(f"Tidal auth for account {account_id}: client_id={'present' if client_id else 'MISSING'}, client_secret={'present' if client_secret else 'MISSING'}")
        
        # Global redirect URI
        redirect_uri = AccountManager.get_service_config('tidal', 'redirect_uri') or 'http://127.0.0.1:8000/api/tidal/callback'
        
        if not client_id or not client_secret:
            logger.error(f"Tidal account {account_id} exists but credentials missing")
            return jsonify({'error': 'Account missing client_id or client_secret. Please edit the account to configure credentials.'}), 400

        # Generate PKCE values
        # We need to implement manual PKCE generation since we can't import TidalClient easily without circular dependency
        # or we just import it locally
        from providers.tidal.client import TidalClient
        # Create temp client just for PKCE generation
        temp_client = TidalClient(account_id=str(account_id))
        verifier, challenge = temp_client.generate_pkce()

        # Create unique PKCE session and store in memory
        pkce_id = str(uuid.uuid4())
        
        _pkce_sessions[pkce_id] = {
            'service': 'tidal',
            'account_id': account_id,
            'code_verifier': verifier,
            'code_challenge': challenge,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'expires_at': time.time() + 600  # 10 minutes
        }

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
        logger.error(f"Error creating Tidal auth URL: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/callback', methods=['GET'])
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

        # Retrieve PKCE entry
        pkce_entry = _pkce_sessions.get(pkce_id)
        
        if not pkce_entry or pkce_entry.get('expires_at', 0) < time.time():
            logger.error(f"No valid PKCE entry found for id={pkce_id[:8]}...")
            return jsonify({"error": "PKCE session not found or expired"}), 400

        account_id = pkce_entry.get('account_id')
        code_verifier = pkce_entry.get('code_verifier')
        redirect_uri = pkce_entry.get('redirect_uri')
        client_id = pkce_entry.get('client_id')

        if not all([account_id, code_verifier, redirect_uri, client_id]):
            return jsonify({"error": "Incomplete PKCE session data"}), 400

        # Load client_secret from account config
        account = AccountManager.get_account('tidal', account_id)
        if not account:
            return jsonify({"error": "Account not found"}), 400

        client_secret = account.get('client_secret')
        if not client_secret:
            return jsonify({"error": "Account missing client_secret"}), 400

        # Exchange authorization code for tokens using direct requests
        # We don't use RequestManager here to avoid circular dependencies or complex setup
        # for a simple one-off auth request.
        
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'code_verifier': code_verifier
        }
        
        # Basic auth with client_id:client_secret is required by Tidal
        auth = (client_id, client_secret)

        logger.info(f"Exchanging code for tokens (account {account_id})")
        response = requests.post('https://auth.tidal.com/v1/oauth2/token', data=token_data, auth=auth)
        
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
            token_update = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_at': expires_at,
                'scope': scope,
                'is_authenticated': True
            }
            AccountManager.save_account_token('tidal', account_id, token_update)
            logger.info(f"Tokens saved for Tidal account {account_id}")
        except Exception as e:
            logger.error(f"Failed to persist tokens: {e}")

        # Clean up one-time PKCE session
        if pkce_id in _pkce_sessions:
            del _pkce_sessions[pkce_id]

        # Redirect back to UI
        # Assuming UI runs on standard port or served by same host
        ui_redirect = '/settings/music-services'
            
        return redirect(ui_redirect)

    except Exception as e:
        logger.error(f"Tidal callback error: {e}", exc_info=True)
        error_html = f"""<html><body style='font-family: Arial, sans-serif;'>
            <h2>Tidal Authentication Failed</h2>
            <p>{str(e)}</p>
        </body></html>"""
        return error_html, 500, {"Content-Type": "text/html"}
