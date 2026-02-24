"""Jellyfin provider routes."""

from flask import Blueprint, request, jsonify
from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("jellyfin_routes")

bp = Blueprint('jellyfin_routes', __name__, url_prefix='/api/jellyfin')


@bp.get('/settings')
def get_settings():
    """Get Jellyfin server settings (base_url, username, password status)."""
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('jellyfin'):
        return jsonify({'settings': {}}), 200
    try:
        base_url = config_manager.get('jellyfin.base_url', '')
        username = config_manager.get('jellyfin.username', '')
        password = config_manager.get('jellyfin.password', '')
        
        # Check if this is the active media server
        active_media_server = config_manager.get('active_media_server', 'plex')
        is_active = (active_media_server == 'jellyfin')
        
        # Check connection status
        connected = False
        if base_url and username and password:
            try:
                import requests
                # Test authentication with Jellyfin API
                auth_url = f"{base_url.rstrip('/')}/Users/AuthenticateByName"
                headers = {
                    'Content-Type': 'application/json',
                    'X-Emby-Authorization': 'MediaBrowser Client="SoulSync", Device="SoulSync", DeviceId="soulsync-1", Version="1.0.0"'
                }
                auth_data = {
                    'Username': username,
                    'Pw': password
                }
                response = requests.post(auth_url, json=auth_data, headers=headers, timeout=5)
                if response.status_code == 200:
                    connected = True
            except Exception as e:
                logger.debug(f"Jellyfin connection check failed: {e}")
        
        # Get path mappings
        import json
        path_mappings_str = config_manager.get('jellyfin.path_mappings', '[]')
        try:
            path_mappings = json.loads(path_mappings_str)
        except:
            path_mappings = []
        
        return jsonify({
            'settings': {
                'base_url': base_url,
                'username': username,
                'has_password': bool(password),
                'connected': connected,
                'is_active': is_active,
                'path_mappings': path_mappings
            }
        })
    except Exception as e:
        logger.error(f"Error getting Jellyfin settings: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post('/settings')
def save_settings():
    """Save Jellyfin server settings."""
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('jellyfin'):
        return jsonify({'error': 'Jellyfin provider disabled'}), 403
    try:
        data = request.get_json(force=True) or {}
        
        if 'base_url' in data:
            base_url = data['base_url'].strip()
            config_manager.set('jellyfin.base_url', base_url)
            logger.info(f"Jellyfin base_url saved: {base_url}")
        
        if 'username' in data:
            username = data['username'].strip()
            config_manager.set('jellyfin.username', username)
            logger.info(f"Jellyfin username saved: {username}")
        
        if 'password' in data:
            password = data['password'].strip()
            config_manager.set('jellyfin.password', password)
            logger.info(f"Jellyfin password saved")
        
        if 'path_mappings' in data:
            import json
            path_mappings = data['path_mappings']
            config_manager.set('jellyfin.path_mappings', json.dumps(path_mappings))
            logger.info(f"Jellyfin path_mappings saved: {len(path_mappings)} mappings")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error saving Jellyfin settings: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post('/activate')
def activate_server():
    """Set Jellyfin as the active media server."""
    try:
        config_manager.set('active_media_server', 'jellyfin')
        logger.info("Jellyfin set as active media server")
        return jsonify({
            'success': True,
            'message': 'Jellyfin is now the active media server'
        })
    except Exception as e:
        logger.error(f"Error activating Jellyfin: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post('/test-connection')
def test_connection():
    """Test connection to Jellyfin server."""
    try:
        base_url = config_manager.get('jellyfin.base_url', '').strip()
        username = config_manager.get('jellyfin.username', '').strip()
        password = config_manager.get('jellyfin.password', '').strip()
        
        if not base_url:
            return jsonify({'error': 'Server URL is required'}), 400
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        import requests
        
        # Test authentication endpoint
        auth_url = f"{base_url.rstrip('/')}/Users/AuthenticateByName"
        headers = {
            'Content-Type': 'application/json',
            'X-Emby-Authorization': 'MediaBrowser Client="SoulSync", Device="SoulSync", DeviceId="soulsync-1", Version="1.0.0"'
        }
        auth_data = {
            'Username': username,
            'Pw': password
        }
        
        response = requests.post(auth_url, json=auth_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            server_name = data.get('ServerId', 'Jellyfin Server')
            user_id = data.get('User', {}).get('Id', '')
            
            # Get server info
            try:
                access_token = data.get('AccessToken', '')
                info_url = f"{base_url.rstrip('/')}/System/Info"
                info_headers = {
                    'X-Emby-Authorization': f'MediaBrowser Client="SoulSync", Device="SoulSync", DeviceId="soulsync-1", Version="1.0.0", Token="{access_token}"'
                }
                info_response = requests.get(info_url, headers=info_headers, timeout=5)
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    version = info_data.get('Version', 'unknown')
                    server_name = info_data.get('ServerName', server_name)
                else:
                    version = 'unknown'
            except Exception as e:
                logger.debug(f"Failed to get server info: {e}")
                version = 'unknown'
            
            logger.info(f"Jellyfin connection successful: {server_name} version {version}")
            
            return jsonify({
                'connected': True,
                'version': version,
                'server_name': server_name,
                'user_id': user_id
            })
        elif response.status_code == 401:
            return jsonify({'connected': False, 'error': 'Invalid username or password'}), 400
        else:
            return jsonify({'connected': False, 'error': f'HTTP {response.status_code}'}), 400
            
    except ImportError:
        return jsonify({'error': 'requests library not available'}), 500
    except Exception as e:
        logger.error(f"Jellyfin connection test failed: {e}", exc_info=True)
        return jsonify({'connected': False, 'error': str(e)}), 400
