from core.nexus_framework.plugin_SDK import PluginStorageBox
"""Plex provider routes."""

import threading
import uuid
import logging
from flask import Blueprint, request, jsonify
from core.tiered_logger import get_logger


logger = get_logger("plex_routes")

# Create a single blueprint for all Plex routes
bp = Blueprint('plex_routes', __name__, url_prefix='/api/plex')

# --- Settings Logic (from web/routes/plex_settings.py) ---

@bp.get('/settings')
def get_settings():
    """Get Plex server settings (base_url, token status)."""
    from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
    if PluginRegistry.is_plugin_disabled('plex'):
        return jsonify({'settings': {}}), 200
    try:
        base_url = PluginStorageBox().config.get('plex.base_url', '')
        server_name = PluginStorageBox().config.get('plex.server_name', '')
        
        # Retrieve token from Singleton Account
        sdk = PluginStorageBox()
        from core.security import decrypt_string
        
        accounts = sdk.accounts.get_all()

        token = ''
        if accounts:
            account_id = accounts[0].get('id')
            token_data = sdk.accounts.get_token(account_id)
            if token_data and token_data.get('access_token'):
                token = decrypt_string(token_data.get('access_token'))

        # Check if this is the active media server
        active_media_server = PluginStorageBox().config.get('active_media_server', 'plex')
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
        path_mappings_raw = PluginStorageBox().config.get('plex.path_mappings', '[]')
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
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.post('/settings')
def save_settings():
    """Save Plex server settings."""
    try:
        from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
        data = request.get_json(force=True) or {}
        
        if 'base_url' in data:
            base_url = data['base_url'].strip()
            PluginStorageBox().config.set('plex.base_url', base_url)
            logger.info(f"Plex base_url saved: {base_url}")
        
        if 'server_name' in data:
            server_name = data['server_name'].strip()
            PluginStorageBox().config.set('plex.server_name', server_name)
            logger.info(f"Plex server_name saved: {server_name}")
        
        if 'token' in data:
            # We don't save tokens to config_manager anymore. We save them to account_tokens
            token = data['token'].strip()
            sdk = PluginStorageBox()
            from core.security import encrypt_string
            from .client import PlexClient
            import time
            

            accounts = sdk.accounts.get_all()
            if accounts:
                account_id = accounts[0].get('id')
            else:
                account_id = sdk.accounts.ensure_account(account_name=f"plex_user_{int(time.time())}")

            sdk.accounts.save_token(
                account_id=account_id, access_token=encrypt_string(token), refresh_token=None, expires_at=None)
            logger.info(f"Plex token saved to SQLite account {account_id}")

            try:
                PlexClient(account_id=account_id).import_managed_users()
            except Exception as e:
                logger.warning(f"Failed to import Plex managed users after saving settings: {e}")
        
        if 'path_mappings' in data:
            import json
            path_mappings = data['path_mappings']
            PluginStorageBox().config.set('plex.path_mappings', json.dumps(path_mappings))
            logger.info(f"Plex path_mappings saved: {len(path_mappings)} mappings")

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error saving Plex settings: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.post('/activate')
def activate_server():
    """Set Plex as the active media server."""
    try:
        PluginStorageBox().config.set('active_media_server', 'plex')
        logger.info("Plex set as active media server")
        return jsonify({
            'success': True,
            'message': 'Plex is now the active media server'
        })
    except Exception as e:
        logger.error(f"Error activating Plex: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.post('/test-connection')
def test_connection():
    """Test connection to Plex server."""
    try:
        payload = request.get_json(silent=True) or {}

        base_url = str(
            payload.get('base_url')
            or PluginStorageBox().config.get('plex.base_url', '')
        ).strip()

        sdk = PluginStorageBox()
        from core.security import decrypt_string

        
        accounts = sdk.accounts.get_all()

        token = ''
        if accounts:
            account_id = accounts[0].get('id')
            token_data = sdk.accounts.get_token(account_id)
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
        return jsonify({"connected": False, "error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Connection test failed"}), 400

@bp.post('/auto-map-paths')
def auto_map_paths():
    """Auto-generate remote to local path mappings by comparing synced tracks."""
    try:
        from core.nexus_framework.plugin_loader import PluginStorageBox
        sdk = PluginStorageBox()
        from core.security import decrypt_string
        
        base_url = str(sdk.config.get('plex.base_url', '')).strip()
        accounts = sdk.accounts.get_all()
        token = ''
        if accounts:
            account_id = accounts[0].get('id')
            token_data = sdk.accounts.get_token(account_id)
            if token_data and token_data.get('access_token'):
                token = decrypt_string(token_data.get('access_token'))
                
        if not base_url or not token:
            return jsonify({'error': 'Plex is not configured or authenticated.'}), 400
            
        from plexapi.server import PlexServer
        server = PlexServer(base_url, token, timeout=10)
        
        from database.music_database import ExternalIdentifier, Track
        mappings_derived = []
        
        with sdk.db.session_scope() as session:
            # Query up to 15 distinct tracks that have a plex external identifier
            ext_ids = session.query(ExternalIdentifier).filter(
                ExternalIdentifier.plugin_source == 'plex'
            ).limit(15).all()
            
            if not ext_ids:
                return jsonify({'error': 'No tracks synced with Plex found in the local database. Try importing a playlist or library first.'}), 400
                
            for ext in ext_ids:
                local_track = session.query(Track).filter_by(id=ext.track_id).first()
                if not local_track or not local_track.file_path:
                    continue
                    
                # Get remote track
                try:
                    plex_track = server.fetchItem(int(ext.plugin_item_id))
                    if not hasattr(plex_track, 'media') or not plex_track.media or not hasattr(plex_track.media[0], 'parts') or not plex_track.media[0].parts:
                        continue
                    remote_file = getattr(plex_track.media[0].parts[0], 'file', None)
                    if not remote_file:
                        continue
                        
                    # Derive mapping
                    remote = remote_file.replace('\\', '/')
                    local = local_track.file_path.replace('\\', '/')
                    
                    remote_parts = remote.split('/')
                    local_parts = local.split('/')
                    
                    common_len = 0
                    while common_len < len(remote_parts) and common_len < len(local_parts):
                        if remote_parts[-(common_len + 1)] == local_parts[-(common_len + 1)]:
                            common_len += 1
                        else:
                            break
                            
                    if common_len == 0:
                        continue
                        
                    remote_prefix = '/'.join(remote_parts[:-common_len])
                    local_prefix = '/'.join(local_parts[:-common_len])
                    
                    if remote.startswith('/') and not remote_prefix.startswith('/'):
                        remote_prefix = '/' + remote_prefix
                    if local.startswith('/') and not local_prefix.startswith('/'):
                        local_prefix = '/' + local_prefix
                    if not remote_prefix and remote.startswith('/'): remote_prefix = '/'
                    if not local_prefix and local.startswith('/'): local_prefix = '/'
                    
                    mapping = {"remote": remote_prefix, "local": local_prefix}
                    if mapping not in mappings_derived:
                        mappings_derived.append(mapping)
                        
                    if len(mappings_derived) >= 1:
                        # We just want one identical mapping. If we find more than 1 distinct, we'll error out.
                        pass
                except Exception as e:
                    logger.debug(f"Failed to fetch plex track {ext.plugin_item_id} during auto-map: {e}")
                    
        if not mappings_derived:
            return jsonify({'error': 'Could not derive path mapping. No matching file structures found between Plex and local DB.'}), 400
            
        if len(mappings_derived) > 1:
            return jsonify({'error': 'Found conflicting path mappings among tracks. Manual configuration required.'}), 400
            
        import json
        sdk.config.set('plex.path_mappings', json.dumps(mappings_derived))
        logger.info(f"Auto-generated Plex path mapping: {mappings_derived}")
        
        return jsonify({
            'success': True,
            'mappings': mappings_derived
        })
        
    except Exception as e:
        logger.error(f"Error auto-mapping paths: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


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
        origin = request.headers.get('Origin')
        forward_url = f"{origin}/settings/music-services" if origin else "http://127.0.0.1:5173/settings/music-services"
        oauth_url = pin_login.oauthUrl(forward_url)

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
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


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
                'X-Plex-Client-Identifier': pin_login._headers().get('X-Plex-Client-Identifier', 'Echosync')
            }
            # Explicitly request the PIN status from Plex
            resp = requests.get(f"https://plex.tv/api/v2/pins/{pin_login._id}", headers=headers, timeout=5)
            resp_data = resp.json()
            logger.debug(f"Plex PIN status response: {resp_data}")

            if resp_data.get('authToken'):
                is_logged_in = True
                auth_token = resp_data.get('authToken')
        except requests.exceptions.RequestException as e:
            # Network-level failure (DNS, timeout, connection refused). Return 503 so the
            # frontend applies backoff rather than hammering a potentially unreachable endpoint.
            logger.warning(f"Plex PIN API unreachable: {e}")
            return jsonify({'completed': False, 'error': 'Plex authorization service temporarily unavailable'}), 503
        except Exception as e:
            logger.debug(f"Plex poll API check failed: {e}")

        if is_logged_in and auth_token:
            sdk = PluginStorageBox()
            from core.security import encrypt_string
            from .client import PlexClient
            

            # Plex follows a Singleton Account Pattern. Look for an existing account first.
            accounts = sdk.accounts.get_all()

            if accounts:
                # Upsert existing account
                account_id = accounts[0].get('id')
                account_name = accounts[0].get('account_name', 'Default Plex Server')
                logger.info(f"Plex Singleton: Found existing account {account_id}, updating token.")
            else:
                # Fallback to fetching user details if we create a new one
                account_name = sdk.config.get('base_url') or sdk.config.get('server_url') or "Default Plex Server"
                try:
                    from plexapi.myplex import MyPlexAccount
                    myplex_acc = MyPlexAccount(token=auth_token)
                    account_name = myplex_acc.username or myplex_acc.email or account_name
                except Exception as e:
                    logger.warning(f"Failed to fetch Plex username: {e}")

                # Ensure the new singleton account exists
                account_id = sdk.accounts.ensure_account(account_name=account_name)
                logger.info(f"Plex Singleton: Created new account {account_id} ({account_name}).")

            # Encrypt and save token to account_tokens
            try:
                sdk.accounts.save_token(
                    account_id=account_id, access_token=encrypt_string(auth_token), refresh_token=None, expires_at=None)
                sdk.accounts.mark_account_authenticated(account_id)
                sdk.accounts.toggle_account_active(account_id, True)
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
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


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
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500

from web.auth import require_auth

@bp.post("/sync_users")
@require_auth
def sync_plex_users():
    """Sync Plex admin and managed users into settings database and return the updated list."""
    try:
        from .client import PlexClient
        sdk = PluginStorageBox()

        client = PlexClient()
        client.import_managed_users()

        
        accounts = sdk.accounts.get_all()
        return jsonify({
            'service': 'plex',
            'accounts': accounts,
            'total': len(accounts),
            'success': True,
        }), 200
    except Exception as e:
        logger.error(f"Error syncing Plex users: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500
