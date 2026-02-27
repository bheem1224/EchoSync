"""Spotify provider routes."""

from flask import Blueprint, request, jsonify, redirect
from core.tiered_logger import get_logger
from core.settings import config_manager
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time

logger = get_logger("spotify_routes")
bp = Blueprint("spotify_routes", __name__, url_prefix="/api/spotify")


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
        
        # Read client credentials from storage (service config)
        from core.storage import get_storage_service
        storage = get_storage_service()

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
    from providers.spotify.client import process_oauth_callback

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

        # process token and get relative redirect path
        ui_redirect_path = process_oauth_callback(code, state, error)

        # construct full URL if the path was relative
        if ui_redirect_path.startswith('/'):
            from core.storage import get_storage_service
            storage = get_storage_service()
            ui_base = storage.get_service_config('webui', 'base_url')
            if ui_base:
                ui_redirect = ui_base.rstrip('/') + ui_redirect_path
            else:
                host_ip = request.host.split(':')[0]
                ui_redirect = f'http://{host_ip}:5000{ui_redirect_path}'
        else:
            ui_redirect = ui_redirect_path

        return redirect(ui_redirect)
    except Exception as e:
        logger.error(f"Spotify callback error: {e}", exc_info=True)
        error_html = f"""<html><body style='font-family: Arial, sans-serif;'><h2>Spotify Authentication Failed</h2><p>{str(e)}</p></body></html>"""
        return error_html, 500, {"Content-Type": "text/html"}
