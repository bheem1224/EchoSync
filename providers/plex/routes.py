"""Plex provider routes."""

import threading
import uuid
from flask import Blueprint, request, jsonify
from core.tiered_logger import get_logger
from core.settings import config_manager

logger = get_logger("plex_routes")

# Create a single blueprint for all Plex routes
bp = Blueprint('plex_routes', __name__, url_prefix='/api/plex')

# --- Settings Logic (from web/routes/plex_settings.py) ---

@bp.get('/settings')
def get_settings():
    """Get Plex server settings (base_url, token status)."""
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('plex'):
        return jsonify({'settings': {}}), 200
    try:
        # Load Hybrid Configuration
        plex_config = config_manager.get('plex', {})
        base_url = plex_config.get('base_url') or config_manager.get('plex.base_url', '')
        server_name = plex_config.get('server_name') or config_manager.get('plex.server_name', '')
        
        # Retrieve token from Singleton Account
        from core.storage import get_storage_service
        from core.security import decrypt_string
        storage = get_storage_service()
        accounts = storage.list_accounts('plex')

        token = ''
        if accounts:
            account_id = accounts[0].get('id')
            token_data = storage.get_account_token(account_id)
            if token_data and token_data.get('access_token'):
                token = decrypt_string(token_data.get('access_token'))

        # Check if this is the active media server
        active_media_server = config_manager.get('active_media_server', 'plex')
        is_active = (active_media_server == 'plex')
        
        # Check connection status
        connected = False
        if base_url and token:
            try:
                from plexapi.server import PlexServer
                server = PlexServer(base_url, token, timeout=5)
                # If we can get server identity, we're connected
                _ = server.machineIdentifier
                connected = True
            except Exception as e:
                logger.debug(f"Plex connection check failed: {e}")
        
        # Get path mappings
        import json
        path_mappings_raw = plex_config.get('path_mappings') or config_manager.get('plex.path_mappings', '[]')
        try:
            path_mappings = json.loads(path_mappings_raw) if isinstance(path_mappings_raw, str) else path_mappings_raw
        except:
            path_mappings = []
        
        return jsonify({
            'settings': {
                'base_url': base_url,
                'server_name': server_name,
                'has_token': bool(token),
                'connected': connected,
                'is_active': is_active,
                'path_mappings': path_mappings
            }
        })
    except Exception as e:
        logger.error(f"Error getting Plex settings: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post('/settings')
def save_settings():
    """Save Plex server settings."""
    try:
        data = request.get_json(force=True) or {}
        plex_config = config_manager.get('plex', {})
        
        if 'base_url' in data:
            base_url = data['base_url'].strip()
            plex_config['base_url'] = base_url
            config_manager.set('plex.base_url', base_url) # Legacy fallback
            logger.info(f"Plex base_url saved: {base_url}")
        
        if 'server_name' in data:
            server_name = data['server_name'].strip()
            plex_config['server_name'] = server_name
            config_manager.set('plex.server_name', server_name) # Legacy fallback
            logger.info(f"Plex server_name saved: {server_name}")
        
        if 'token' in data:
            # We don't save tokens to config_manager anymore. We save them to account_tokens
            token = data['token'].strip()
            from core.storage import get_storage_service
            from core.security import encrypt_string
            from providers.plex.client import PlexClient
            import time
            storage = get_storage_service()

            accounts = storage.list_accounts('plex')
            if accounts:
                account_id = accounts[0].get('id')
            else:
                account_id = storage.ensure_account('plex', account_name=f"plex_user_{int(time.time())}")

            storage.save_account_token(
                account_id=account_id,
                access_token=encrypt_string(token),
                refresh_token=None,
                token_type='Bearer'
            )
            storage.mark_account_authenticated(account_id)
            storage.toggle_account_active(account_id, True)
            logger.info(f"Plex token saved to SQLite account {account_id}")

            try:
                PlexClient(account_id=account_id).import_managed_users()
            except Exception as e:
                logger.warning(f"Failed to import Plex managed users after saving settings: {e}")
        
        if 'path_mappings' in data:
            import json
            path_mappings = data['path_mappings']
            plex_config['path_mappings'] = path_mappings
            config_manager.set('plex.path_mappings', json.dumps(path_mappings)) # Legacy fallback
            logger.info(f"Plex path_mappings saved: {len(path_mappings)} mappings")

        config_manager.set('plex', plex_config)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error saving Plex settings: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post('/activate')
def activate_server():
    """Set Plex as the active media server."""
    try:
        config_manager.set('active_media_server', 'plex')
        logger.info("Plex set as active media server")
        return jsonify({
            'success': True,
            'message': 'Plex is now the active media server'
        })
    except Exception as e:
        logger.error(f"Error activating Plex: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post('/test-connection')
def test_connection():
    """Test connection to Plex server."""
    try:
        payload = request.get_json(silent=True) or {}

        plex_config = config_manager.get('plex', {})
        base_url = str(
            payload.get('base_url')
            or plex_config.get('base_url')
            or config_manager.get('plex.base_url', '')
        ).strip()

        from core.storage import get_storage_service
        from core.security import decrypt_string

        storage = get_storage_service()
        accounts = storage.list_accounts('plex')

        token = ''
        if accounts:
            account_id = accounts[0].get('id')
            token_data = storage.get_account_token(account_id)
            if token_data and token_data.get('access_token'):
                token = decrypt_string(token_data.get('access_token'))
        
        if not base_url:
            return jsonify({'error': 'Server URL is required'}), 400
        if not token:
            return jsonify({'error': 'Authentication token is required. Please log in first.'}), 400
        
        from plexapi.server import PlexServer
        server = PlexServer(base_url, token, timeout=10)
        
        # Get server info
        machine_id = server.machineIdentifier
        friendly_name = server.friendlyName
        version = server.version
        
        logger.info(f"Plex connection successful: {friendly_name} ({version})")
        
        return jsonify({
            'connected': True,
            'server_name': friendly_name,
            'version': version,
            'machine_id': machine_id
        })
    except ImportError:
        return jsonify({'error': 'Plex library not available'}), 500
    except Exception as e:
        logger.error(f"Plex connection test failed: {e}", exc_info=True)
        return jsonify({'connected': False, 'error': str(e)}), 400

# --- OAuth Logic (from providers/plex/oauth_routes.py) ---

plex_oauth_sessions = {}
plex_oauth_lock = threading.Lock()

@bp.post('/auth/start')
def start_oauth():
    """
    Start Plex OAuth flow using PIN-based authentication.
    Returns: {session_id, oauth_url, poll_url}
    """
    try:
        from plexapi.myplex import MyPlexPinLogin

        pin_login = MyPlexPinLogin(oauth=True)
        session_id = str(uuid.uuid4())

        with plex_oauth_lock:
            plex_oauth_sessions[session_id] = pin_login

        # We don't want to use pin_login.run() because it blocks the thread
        # and starts an internal polling loop. Instead we initialize the code
        # and let the frontend do the polling.
        pin_login._getCode()

        # We need a dummy forward URL to satisfy OAuth, even though Plex uses PINs
        oauth_url = pin_login.oauthUrl('http://127.0.0.1:5173/settings/music-services')

        logger.info(f"Plex OAuth session started: {session_id} with pin id: {pin_login._id}")

        # Register a one-shot cleanup job with the central scheduler so the session
        # is expired after 15 minutes without spawning a raw background thread.
        _session_id = session_id  # capture for closure
        def _cleanup_oauth_session():
            with plex_oauth_lock:
                if _session_id in plex_oauth_sessions:
                    plex_oauth_sessions.pop(_session_id, None)
                    logger.info(f"Plex OAuth session cleaned up: {_session_id}")

        from core.job_queue import job_queue
        job_queue.register_job(
            name=f"plex_oauth_cleanup_{session_id}",
            func=_cleanup_oauth_session,
            interval_seconds=None,  # one-shot
            start_after=900.0,      # 15 minutes
            enabled=True,
            tags=["plex", "oauth", "cleanup"],
        )

        return jsonify({
            'session_id': session_id,
            'oauth_url': oauth_url,
            'poll_url': f'/api/plex/auth/poll/{session_id}'
        })
    except ImportError:
        logger.error("plexapi library not installed")
        return jsonify({'error': 'Plex library not available'}), 500
    except Exception as e:
        logger.error(f"Error starting Plex OAuth: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.get('/auth/poll/<session_id>')
def poll_oauth(session_id: str):
    """
    Poll for Plex OAuth authorization completion.
    Returns: {completed, token?, error?}
    """
    try:
        with plex_oauth_lock:
            pin_login = plex_oauth_sessions.get(session_id)

        if not pin_login:
            return jsonify({'error': 'Session not found or expired'}), 404

        # We manually query the Plex PIN API to check if the user authorized it.
        # `pin_login._checkLogin()` handles this cleanly without starting a background thread.
        import requests
        is_logged_in = False
        auth_token = None

        try:
            headers = {
                'Accept': 'application/json',
                'X-Plex-Client-Identifier': pin_login._headers().get('X-Plex-Client-Identifier', 'SoulSync')
            }
            # Explicitly request the PIN status from Plex
            resp = requests.get(f"https://plex.tv/api/v2/pins/{pin_login._id}", headers=headers, timeout=5)
            resp_data = resp.json()
            logger.debug(f"Plex PIN status response: {resp_data}")

            if resp_data.get('authToken'):
                is_logged_in = True
                auth_token = resp_data.get('authToken')
        except Exception as e:
            logger.debug(f"Plex poll API check failed: {e}")

        if is_logged_in and auth_token:
            from core.storage import get_storage_service
            from core.security import encrypt_string
            from providers.plex.client import PlexClient
            storage = get_storage_service()

            # Plex follows a Singleton Account Pattern. Look for an existing account first.
            accounts = storage.list_accounts('plex')

            if accounts:
                # Upsert existing account
                account_id = accounts[0].get('id')
                account_name = accounts[0].get('account_name', 'Default Plex Server')
                logger.info(f"Plex Singleton: Found existing account {account_id}, updating token.")
            else:
                # Fallback to fetching user details if we create a new one
                account_name = storage.get_service_config('plex', 'base_url') or storage.get_service_config('plex', 'server_url') or "Default Plex Server"
                try:
                    from plexapi.myplex import MyPlexAccount
                    myplex_acc = MyPlexAccount(token=auth_token)
                    account_name = myplex_acc.username or myplex_acc.email or account_name
                except Exception as e:
                    logger.warning(f"Failed to fetch Plex username: {e}")

                # Ensure the new singleton account exists
                account_id = storage.ensure_account('plex', account_name=account_name)
                logger.info(f"Plex Singleton: Created new account {account_id} ({account_name}).")

            # Encrypt and save token to account_tokens
            try:
                storage.save_account_token(
                    account_id=account_id,
                    access_token=encrypt_string(auth_token),
                    refresh_token=None,  # Plex tokens do not use standard OAuth refresh tokens
                    token_type='Bearer',
                    expires_at=None,
                    scope=None
                )
                storage.mark_account_authenticated(account_id)
                storage.toggle_account_active(account_id, True)
                logger.info(f"Plex OAuth completed and token securely saved for account: {account_name}")
                try:
                    PlexClient(account_id=account_id).import_managed_users()
                except Exception as import_err:
                    logger.warning(f"Failed to import Plex managed users after OAuth: {import_err}")
            except Exception as e:
                logger.error(f"Failed to securely save Plex token: {e}")
                return jsonify({'error': 'Failed to securely save token'}), 500

            with plex_oauth_lock:
                plex_oauth_sessions.pop(session_id, None)

            return jsonify({
                'completed': True,
                'token': auth_token  # For backwards compatibility in UI until UI is updated
            })
        else:
            return jsonify({
                'completed': False
            })

    except Exception as e:
        logger.error(f"Error polling Plex OAuth: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.delete('/auth/cancel/<session_id>')
def cancel_oauth(session_id: str):
    """Cancel an ongoing OAuth session."""
    try:
        with plex_oauth_lock:
            pin_login = plex_oauth_sessions.pop(session_id, None)
            if pin_login:
                logger.info(f"Plex OAuth session cancelled: {session_id}")

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error cancelling Plex OAuth: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
