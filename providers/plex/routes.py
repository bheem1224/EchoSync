"""Plex provider routes."""

import threading
import uuid
import time
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
        base_url = config_manager.get('plex.base_url', '')
        token = config_manager.get('plex.token', '')
        server_name = config_manager.get('plex.server_name', '')
        
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
        path_mappings_str = config_manager.get('plex.path_mappings', '[]')
        try:
            path_mappings = json.loads(path_mappings_str)
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
        
        if 'base_url' in data:
            base_url = data['base_url'].strip()
            config_manager.set('plex.base_url', base_url)
            logger.info(f"Plex base_url saved: {base_url}")
        
        if 'server_name' in data:
            server_name = data['server_name'].strip()
            config_manager.set('plex.server_name', server_name)
            logger.info(f"Plex server_name saved: {server_name}")
        
        if 'token' in data:
            token = data['token'].strip()
            config_manager.set('plex.token', token)
            logger.info(f"Plex token saved")
        
        if 'path_mappings' in data:
            import json
            path_mappings = data['path_mappings']
            config_manager.set('plex.path_mappings', json.dumps(path_mappings))
            logger.info(f"Plex path_mappings saved: {len(path_mappings)} mappings")
        
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
        base_url = config_manager.get('plex.base_url', '').strip()
        token = config_manager.get('plex.token', '').strip()
        
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

        # Timeout of 600 seconds (10 minutes)
        pin_login.run(timeout=600)
        oauth_url = pin_login.oauthUrl()

        logger.info(f"Plex OAuth session started: {session_id}")

        def cleanup_session():
            time.sleep(900)  # 15 minutes
            with plex_oauth_lock:
                if session_id in plex_oauth_sessions:
                    plex_oauth_sessions.pop(session_id, None)
                    logger.info(f"Plex OAuth session cleaned up: {session_id}")

        cleanup_thread = threading.Thread(target=cleanup_session, daemon=True)
        cleanup_thread.start()

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

        # Call checkLogin to actively poll Plex. It returns True when authenticated.
        is_logged_in = False
        try:
            is_logged_in = pin_login.checkLogin()
        except Exception as check_e:
            logger.debug(f"Plex poll checkLogin still waiting: {check_e}")

        if is_logged_in and getattr(pin_login, 'token', None):
            auth_token = pin_login.token

            # Fetch user details to name the account properly
            from plexapi.myplex import MyPlexAccount
            account_name = f"plex_user_{int(time.time())}"
            try:
                myplex_acc = MyPlexAccount(token=auth_token)
                account_name = myplex_acc.username or myplex_acc.email or account_name
            except Exception as e:
                logger.warning(f"Failed to fetch Plex username: {e}")

            from core.storage import get_storage_service
            from core.security import encrypt_string
            storage = get_storage_service()

            # Ensure the account exists in SQLite accounts table
            account_id = storage.ensure_account('plex', account_name=account_name)

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
