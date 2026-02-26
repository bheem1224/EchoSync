"""Spotify provider routes."""

from flask import Blueprint, request, jsonify, redirect
from core.tiered_logger import get_logger
from core.settings import config_manager
from core.account_manager import AccountManager
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time

logger = get_logger("spotify_routes")
bp = Blueprint("spotify_routes", __name__, url_prefix="/api/spotify")


def _normalize_and_seed_credentials(storage, client_id, client_secret, redirect_uri):
    """Normalize legacy redirect URIs and seed credentials into the encrypted config DB."""
    # Stubbed - logic moved to core/settings.py or initialization if needed
    pass


@bp.get('/auth')
def begin_auth():
    """Start OAuth flow for Spotify. Returns an auth URL to redirect the user to.
    Query params: account_id (required)
    """
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('spotify'):
        return jsonify({'error': 'Spotify provider is disabled'}), 403
    try:
        account_id = request.args.get('account_id')
        
        # account_id is required for proper state management
        if not account_id:
            return jsonify({'error': 'account_id parameter is required'}), 400
        
        # Read client credentials
        client_id = AccountManager.get_service_config('spotify', 'client_id')
        client_secret = AccountManager.get_service_config('spotify', 'client_secret')
        redirect_uri = AccountManager.get_service_config('spotify', 'redirect_uri') or None

        if not client_id or not client_secret or not redirect_uri:
            return jsonify({'error': 'Spotify client_id, client_secret, or redirect_uri not configured'}), 400

        scope = "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email"
        # Use account_id as state so callback knows which account to save tokens under
        state = str(account_id)
        sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope, state=state, show_dialog=True)
        auth_url = sp_oauth.get_authorize_url()
        logger.info(f"Generated Spotify authorize URL for account {account_id}")
        return jsonify({'auth_url': auth_url}), 200
    except Exception as e:
        logger.error(f"Error creating Spotify auth URL: {e}")
        return jsonify({'error': str(e)}), 500


@bp.get('/callback')
def oauth_callback():
    """Handle Spotify OAuth callback and exchange code for tokens.
    Expects query params: code, state
    """
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('spotify'):
        return jsonify({'error': 'Spotify provider is disabled'}), 403
    try:
        code = request.args.get('code')
        state = request.args.get('state')  # account_id
        error = request.args.get('error')

        # Handle user-denied or provider errors
        if error:
            error_description = request.args.get('error_description', error)
            logger.error(f"Spotify OAuth error: {error_description}")
            html = f"""<html><body style='font-family: Arial, sans-serif;'><h2>Spotify Authentication Failed</h2><p><strong>Error:</strong> {error_description}</p><p>Please try again or check your Spotify app settings.</p></body></html>"""
            return html, 400, {"Content-Type": "text/html"}

        if not code:
            logger.error("OAuth callback missing code parameter")
            return jsonify({"error": "Missing authorization code"}), 400

        if not state:
            logger.error("OAuth callback missing state parameter (account id)")
            return jsonify({"error": "Missing state parameter (account ID)"}), 400

        # Parse account_id from state
        try:
            account_id = int(state)
        except (ValueError, TypeError):
            account_id = None

        client_id = AccountManager.get_service_config('spotify', 'client_id')
        client_secret = AccountManager.get_service_config('spotify', 'client_secret')
        redirect_uri = AccountManager.get_service_config('spotify', 'redirect_uri') or None

        if not client_id or not client_secret:
            return jsonify({"error": "Spotify client_id/client_secret not configured"}), 400

        # Use ConfigCacheHandler so tokens are persisted via StorageService
        from providers.spotify.client import ConfigCacheHandler
        auth_manager = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope="user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email", cache_handler=ConfigCacheHandler(account_id))

        # Exchange code for tokens
        try:
            token_info = auth_manager.get_access_token(code, as_dict=True)
        except TypeError:
            # Older spotipy versions may use different signature
            token_info = auth_manager.get_access_token(code)

        if not token_info:
            return jsonify({"error": "Failed to exchange code for token"}), 400

        access_token = token_info.get('access_token')
        refresh_token = token_info.get('refresh_token')
        expires_at = token_info.get('expires_at')
        scope = token_info.get('scope') or "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email"

        # If no account_id passed, create a new account entry
        if not account_id:
            new_acc = config_manager.add_spotify_account({'name': f"spotify_{int(time.time())}"})
            account_id = new_acc.get('id')

        # Persist tokens and mark authenticated
        try:
            token_update = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_at': expires_at,
                'scope': scope,
                'is_authenticated': True
            }
            AccountManager.save_account_token('spotify', account_id, token_update)
        except Exception as e:
            logger.error(f"Failed to persist tokens to config.db: {e}")

        # Optionally activate the account
        try:
            AccountManager.update_account('spotify', account_id, {'is_active': True})
        except Exception:
            pass

        # Redirect back to the web UI settings.
        # If a `webui.base_url` is configured in storage, use that as the base.
        # Otherwise default to the local dev frontend URL so the browser returns
        # to the Svelte app instead of the Flask backend (which would 404).
        ui_base = AccountManager.get_service_config('webui', 'base_url')
        if ui_base:
            ui_redirect = ui_base.rstrip('/') + '/settings/music-services'
        else:
            ui_redirect = 'http://localhost:5173/settings/music-services'
        return redirect(ui_redirect)
    except Exception as e:
        logger.error(f"Spotify callback error: {e}", exc_info=True)
        error_html = f"""<html><body style='font-family: Arial, sans-serif;'><h2>Spotify Authentication Failed</h2><p>{str(e)}</p></body></html>"""
        return error_html, 500, {"Content-Type": "text/html"}
