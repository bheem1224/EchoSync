"""Spotify provider routes."""

from flask import Blueprint, request, jsonify, redirect
from core.tiered_logger import get_logger

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time

logger = get_logger("spotify_routes")
bp = Blueprint("spotify_routes", __name__, url_prefix="/api/plugins/spotify")


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
                sdk.config.set('client_id', client_id)
                sdk.secrets.set('client_secret', client_secret)
                if redirect_uri:
                    sdk.config.set('redirect_uri', redirect_uri)
            except Exception as e:
                logger.warning(f"Failed to seed Spotify service config into settings database: {e}")

    except Exception:
        # Don't block auth on normalization failures
        pass


@bp.get('/settings')
def get_settings():
    """Retrieve Spotify plugin settings."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        client_id = sdk.config.get('client_id', '')
        client_secret = sdk.secrets.get('client_secret', '')
        redirect_uri = sdk.config.get('redirect_uri', '')

        # Fallback to local if not set
        if not redirect_uri:
            from core.nexus_framework.plugin_loader import PluginRegistry
            from .client import SpotifyClient
            sp_client = PluginRegistry.create_instance('spotify') or SpotifyClient(account_id=0)
            redirect_uri = sp_client.get_oauth_redirect_uri()

        return jsonify({
            'settings': {
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri
            }
        }), 200
    except Exception as e:
        logger.error(f"Failed to get Spotify settings: {e}")
        return jsonify({'error': str(e)}), 500

@bp.post('/settings')
def save_settings():
    """Save Spotify plugin settings securely using the SDK."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        data = request.get_json() or {}
        client_id = data.get('client_id', '').strip()
        client_secret = data.get('client_secret', '').strip()
        redirect_uri = data.get('redirect_uri', '').strip()

        if client_id:
            sdk.config.set('client_id', client_id)
        if client_secret:
            sdk.secrets.set('client_secret', client_secret)
        if redirect_uri:
            sdk.config.set('redirect_uri', redirect_uri)

        logger.info("Spotify credentials saved securely via SDK")
        return jsonify({'success': True, 'message': 'Spotify credentials saved securely'}), 200
    except Exception as e:
        logger.error(f"Failed to save Spotify settings: {e}")
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Account management — consumed by SpotifyCard.svelte
# ---------------------------------------------------------------------------

@bp.get('/accounts')
def list_accounts():
    """Return all Spotify accounts."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        accounts = sdk.accounts.get_all()
        return jsonify({'accounts': accounts}), 200
    except Exception as e:
        logger.error(f"Failed to list Spotify accounts: {e}")
        return jsonify({'error': str(e)}), 500


@bp.post('/accounts')
def create_account():
    """Create a new Spotify account entry."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        data = request.get_json() or {}
        account_name = (data.get('account_name') or '').strip()
        display_name = (data.get('display_name') or account_name).strip()
        if not account_name:
            return jsonify({'error': 'account_name is required'}), 400
        account_id = sdk.accounts.ensure_account(account_name=account_name, display_name=display_name)
        if not account_id:
            return jsonify({'error': 'Failed to create account'}), 500
        return jsonify({'account': {'id': account_id, 'account_name': account_name,
                                    'display_name': display_name, 'is_active': False,
                                    'is_authenticated': False}}), 201
    except Exception as e:
        logger.error(f"Failed to create Spotify account: {e}")
        return jsonify({'error': str(e)}), 500


@bp.put('/accounts/<int:account_id>/activate')
def activate_account(account_id):
    """Toggle active state for a Spotify account."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        data = request.get_json() or {}
        is_active = bool(data.get('is_active', True))
        sdk.accounts.toggle_account_active(account_id, is_active)
        return jsonify({'success': True, 'is_active': is_active}), 200
    except Exception as e:
        logger.error(f"Failed to toggle Spotify account {account_id}: {e}")
        return jsonify({'error': str(e)}), 500


@bp.delete('/accounts/<int:account_id>')
def delete_account(account_id):
    """Delete a Spotify account and its tokens."""
    from core.nexus_framework.plugin_SDK import sdk
    try:
        sdk.accounts.delete_account(account_id)
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Failed to delete Spotify account {account_id}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.get('/auth')
def begin_auth():
    """Start OAuth flow for Spotify. Returns an auth URL to redirect the user to.
    Query params: account_id (required)
    """
    from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
    from .client import SpotifyClient
    if PluginRegistry.is_plugin_disabled('spotify'):
        return jsonify({'error': 'Spotify provider is disabled'}), 403
    try:
        account_id = request.args.get('account_id')
        
        # account_id is required for proper state management
        if not account_id:
            return jsonify({'error': 'account_id parameter is required'}), 400
        
        # Read client credentials from storage (service config)
        from core.nexus_framework.plugin_SDK import sdk

        from core.security import decrypt_string
        client_id = sdk.config.get('client_id')
        client_secret = sdk.secrets.get('client_secret')

        # We now use the sidecar's redirect URI systematically, ignoring what is in config
        from core.network_utils import get_lan_ip
        redirect_uri = f"https://{get_lan_ip()}:5001/api/oauth/callback/plugins/spotify"

        # Seed into storage if we have app credentials
        if client_id and client_secret:
            _normalize_and_seed_credentials(sdk, client_id, client_secret, redirect_uri)

        if not client_id or not client_secret:
            return jsonify({'error': 'Spotify client_id or client_secret not configured'}), 400

        scope = "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email playlist-modify-public playlist-modify-private"
        # Use account_id as state so callback knows which account to save tokens under
        state = str(account_id)

        from .client import CallbackBypassCacheHandler
        sp_oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=decrypt_string(client_secret),
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            show_dialog=True,
            cache_handler=CallbackBypassCacheHandler()
        )
        auth_url = sp_oauth.get_authorize_url()
        logger.info(f"Generated Spotify authorize URL for account {account_id} with redirect_uri {redirect_uri}")
        return jsonify({'auth_url': auth_url}), 200
    except Exception as e:
        logger.error(f"Error creating Spotify auth URL: {e}")
        return jsonify({'error': str(e)}), 500


@bp.get('/callback')
def oauth_callback():
    """Handle Spotify OAuth callback and exchange code for tokens.
    Expects query params: code, state
    """
    from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
    if PluginRegistry.is_plugin_disabled('spotify'):
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

        from core.nexus_framework.plugin_SDK import sdk

        from core.security import decrypt_string
        client_id = sdk.config.get('client_id')
        client_secret = sdk.secrets.get('client_secret')
        from core.network_utils import get_lan_ip
        redirect_uri = f"https://{get_lan_ip()}:5001/api/oauth/callback/plugins/spotify"
        # Fallback to legacy config.json and seed storage if needed
        if not client_id or not client_secret:
            try:
                spotify_conf = ServiceRegistry.get_sdk("spotify").config.get_all()
                client_id = client_id or spotify_conf.get('client_id')
                client_secret = client_secret or spotify_conf.get('client_secret')
                _normalize_and_seed_credentials(sdk, client_id, client_secret, redirect_uri)
            except Exception:
                pass

        if not client_id or not client_secret:
            return jsonify({"error": "Spotify client_id/client_secret not configured"}), 400

        # Use ConfigCacheHandler so tokens are persisted via StorageService
        from .client import CallbackBypassCacheHandler
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=decrypt_string(client_secret),
            redirect_uri=redirect_uri,
            scope="user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email",
            cache_handler=CallbackBypassCacheHandler()
        )

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
            account_id = sdk.accounts.ensure_account(account_name=f"spotify_{int(time.time())}")

        # Persist tokens and mark authenticated
        try:
            sdk.accounts.save_token(account_id, access_token, refresh_token, expires_at)
            sdk.accounts.mark_account_authenticated(account_id)
        except Exception as e:
            logger.error(f"Failed to persist tokens to settings database: {e}")

        # Optionally activate the account
        try:
            sdk.accounts.toggle_account_active(account_id, True)
        except Exception:
            pass

        # Redirect back to the web UI settings.
        from core.settings import config_manager
        ui_base = config_manager.get('webui.base_url')
        if ui_base:
            ui_redirect = ui_base.rstrip('/') + '/settings/music-services'
        else:
            # Use the actual request host and scheme to construct redirect
            scheme = request.scheme
            host = request.host
            ui_redirect = f'{scheme}://{host}/settings/music-services'
        return redirect(ui_redirect)
    except Exception as e:
        logger.error(f"Spotify callback error: {e}", exc_info=True)
        error_html = f"""<html><body style='font-family: Arial, sans-serif;'><h2>Spotify Authentication Failed</h2><p>{str(e)}</p></body></html>"""
        return error_html, 500, {"Content-Type": "text/html"}
