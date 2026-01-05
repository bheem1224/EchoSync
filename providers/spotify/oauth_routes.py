from flask import Blueprint, request, jsonify, redirect
from sdk.storage_service import get_storage_service
from utils.logging_config import get_logger
from config.settings import config_manager
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time

logger = get_logger("spotify_oauth")
bp = Blueprint("spotify_oauth", __name__, url_prefix="/api/spotify")


def _normalize_and_seed_credentials(storage, client_id, client_secret, redirect_uri):
    """Normalize legacy redirect URIs and seed credentials into the encrypted config DB."""
    try:
        # Normalize old localhost:8888 callback URIs to our Flask callback
        if redirect_uri and (
            "127.0.0.1:8888/callback" in redirect_uri or
            "localhost:8888/callback" in redirect_uri or
            redirect_uri.rstrip('/').endswith(":8888/callback")
        ):
            redirect_uri = "http://127.0.0.1:8008/api/spotify/callback"

        # Seed into storage if we have app credentials
        if client_id and client_secret:
            try:
                storage.ensure_service('spotify', display_name='Spotify', service_type='streaming', description='Spotify music streaming service')
                storage.set_service_config('spotify', 'client_id', client_id, is_sensitive=False)
                storage.set_service_config('spotify', 'client_secret', client_secret, is_sensitive=True)
                if redirect_uri:
                    storage.set_service_config('spotify', 'redirect_uri', redirect_uri, is_sensitive=False)
            except Exception as e:
                logger.warning(f"Failed to seed Spotify service config into config.db: {e}")

    except Exception:
        # Don't block auth on normalization failures
        pass


@bp.get('/auth')
def begin_auth():
    """Start OAuth flow for Spotify. Returns an auth URL to redirect the user to.
    Query params: account_id (optional)
    """
    try:
        account_id = request.args.get('account_id')
        storage = get_storage_service()

        # Read client credentials from storage (service config)
        client_id = storage.get_service_config('spotify', 'client_id')
        client_secret = storage.get_service_config('spotify', 'client_secret')
        redirect_uri = storage.get_service_config('spotify', 'redirect_uri') or None

        # Fallback to legacy config.json via config_manager and seed into storage
        if not client_id or not client_secret or not redirect_uri:
            try:
                spotify_conf = config_manager.get_spotify_config()
                client_id = client_id or spotify_conf.get('client_id')
                client_secret = client_secret or spotify_conf.get('client_secret')
                redirect_uri = redirect_uri or spotify_conf.get('redirect_uri') or None
                _normalize_and_seed_credentials(storage, client_id, client_secret, redirect_uri)
            except Exception:
                pass

        if not client_id or not client_secret or not redirect_uri:
            return jsonify({'error': 'Spotify client_id, client_secret, or redirect_uri not configured'}), 400

        scope = "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email"
        # Use account_id as state so callback knows which account to save tokens under
        state = account_id or ''
        sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope, state=state, show_dialog=True)
        auth_url = sp_oauth.get_authorize_url()
        logger.info(f"Generated Spotify authorize URL (truncated): {auth_url[:120]}")
        return jsonify({'auth_url': auth_url}), 200
    except Exception as e:
        logger.error(f"Error creating Spotify auth URL: {e}")
        return jsonify({'error': str(e)}), 500


@bp.get('/callback')
def oauth_callback():
    """Handle Spotify OAuth callback and exchange code for tokens.
    Expects query params: code, state
    """
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

        storage = get_storage_service()

        client_id = storage.get_service_config('spotify', 'client_id')
        client_secret = storage.get_service_config('spotify', 'client_secret')
        redirect_uri = storage.get_service_config('spotify', 'redirect_uri') or None

        # Fallback to legacy config.json and seed storage if needed
        if not client_id or not client_secret or not redirect_uri:
            try:
                spotify_conf = config_manager.get_spotify_config()
                client_id = client_id or spotify_conf.get('client_id')
                client_secret = client_secret or spotify_conf.get('client_secret')
                redirect_uri = redirect_uri or spotify_conf.get('redirect_uri') or None
                _normalize_and_seed_credentials(storage, client_id, client_secret, redirect_uri)
            except Exception:
                pass

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
            account_id = storage.ensure_account('spotify', account_name=f"spotify_{int(time.time())}")

        # Persist tokens and mark authenticated
        try:
            storage.save_account_token(account_id, access_token, refresh_token, 'Bearer', expires_at, scope)
            storage.mark_account_authenticated(account_id)
        except Exception as e:
            logger.error(f"Failed to persist tokens to config.db: {e}")

        # Optionally activate the account
        try:
            storage.toggle_account_active(account_id, True)
        except Exception:
            pass

        # Redirect back to the web UI settings.
        # If a `webui.base_url` is configured in storage, use that as the base.
        # Otherwise default to the local dev frontend URL so the browser returns
        # to the Svelte app instead of the Flask backend (which would 404).
        ui_base = storage.get_service_config('webui', 'base_url')
        if ui_base:
            ui_redirect = ui_base.rstrip('/') + '/settings/music-services'
        else:
            ui_redirect = 'http://localhost:5173/settings/music-services'
        return redirect(ui_redirect)
    except Exception as e:
        logger.error(f"Spotify callback error: {e}", exc_info=True)
        error_html = f"""<html><body style='font-family: Arial, sans-serif;'><h2>Spotify Authentication Failed</h2><p>{str(e)}</p></body></html>"""
        return error_html, 500, {"Content-Type": "text/html"}
from flask import Blueprint, request, jsonify, redirect
from sdk.storage_service import get_storage_service
from utils.logging_config import get_logger
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time

logger = get_logger("spotify_oauth")
bp = Blueprint("spotify_oauth", __name__, url_prefix="/api/spotify")


@bp.get('/auth')
def begin_auth():
    """Start OAuth flow for Spotify. Returns an auth URL to redirect the user to.
    Query params: account_id (optional)
    """
    try:
        account_id = request.args.get('account_id')
        storage = get_storage_service()
        # Read client credentials from storage (service config)
        client_id = storage.get_service_config('spotify', 'client_id')
        client_secret = storage.get_service_config('spotify', 'client_secret')
        redirect_uri = storage.get_service_config('spotify', 'redirect_uri') or None
        if not client_id or not client_secret or not redirect_uri:
            return jsonify({'error': 'Spotify client_id, client_secret, or redirect_uri not configured'}), 400

        scope = "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email"
        # Use account_id as state so callback knows which account to save tokens under
        state = account_id or ''
        sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope, state=state)
        auth_url = sp_oauth.get_authorize_url(state=state)
        return jsonify({'auth_url': auth_url}), 200
    except Exception as e:
        logger.error(f"Error creating Spotify auth URL: {e}")
        return jsonify({'error': str(e)}), 500


@bp.get('/callback')
def oauth_callback():
    """Handle Spotify OAuth callback and exchange code for tokens.
    Expects query params: code, state
    """
    try:
        code = request.args.get('code')
        state = request.args.get('state')  # account_id
        storage = get_storage_service()
        client_id = storage.get_service_config('spotify', 'client_id')
        client_secret = storage.get_service_config('spotify', 'client_secret')
        redirect_uri = storage.get_service_config('spotify', 'redirect_uri') or None
        if not client_id or not client_secret or not redirect_uri:
            return "Missing Spotify client configuration", 400

        sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
        token_info = sp_oauth.get_access_token(code)
        if not token_info:
            logger.error('Failed to obtain token from Spotify')
            return "Authentication failed", 400

        # token_info may be dict with access_token, refresh_token, expires_at, scope
        access_token = token_info.get('access_token')
        refresh_token = token_info.get('refresh_token')
        expires_at = token_info.get('expires_at')
        scope = token_info.get('scope')

        # If state contains account_id, save tokens for that account; otherwise, create a new account
        account_id = int(state) if state and state.isdigit() else None
        if not account_id:
            # create a new account entry
            account_id = storage.ensure_account('spotify', account_name=f"spotify_{int(time.time())}")

        # Persist tokens
        storage.save_account_token(account_id, access_token, refresh_token, 'Bearer', expires_at, scope)
        storage.mark_account_authenticated(account_id)

        # Optionally activate the account by default
        try:
            storage.toggle_account_active(account_id, True)
        except Exception:
            pass

        # Redirect back to the web UI settings.
        ui_base = storage.get_service_config('webui', 'base_url')
        if ui_base:
            ui_redirect = ui_base.rstrip('/') + '/settings/music-services'
        else:
            ui_redirect = 'http://localhost:5173/settings/music-services'
        return redirect(ui_redirect)
    except Exception as e:
        logger.error(f"Error in Spotify OAuth callback: {e}")
        return f"OAuth callback error: {e}", 500
