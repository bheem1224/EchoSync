"""Navidrome provider routes."""

from flask import Blueprint, request, jsonify
from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("navidrome_routes")

bp = Blueprint('navidrome_routes', __name__, url_prefix='/api/navidrome')


@bp.get('/settings')
def get_settings():
    """Get Navidrome server settings (base_url, username, password status)."""
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('navidrome'):
        return jsonify({'settings': {}}), 200
    try:
        base_url = config_manager.get('navidrome.base_url', '')
        username = config_manager.get('navidrome.username', '')
        password = config_manager.get('navidrome.password', '')
        
        # Check if this is the active media server
        active_media_server = config_manager.get('active_media_server', 'plex')
        is_active = (active_media_server == 'navidrome')
        
        # Check connection status
        connected = False
        if base_url and username and password:
            try:
                import requests
                # Test authentication with Navidrome API
                auth_url = f"{base_url.rstrip('/')}/rest/ping.view"
                params = {
                    'u': username,
                    'p': password,
                    'v': '1.16.1',
                    'c': 'SoulSync',
                    'f': 'json'
                }
                response = requests.get(auth_url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('subsonic-response', {}).get('status') == 'ok':
                        connected = True
            except Exception as e:
                logger.debug(f"Navidrome connection check failed: {e}")
        
        # Get path mappings
        import json
        path_mappings_str = config_manager.get('navidrome.path_mappings', '[]')
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
        logger.error(f"Error getting Navidrome settings: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post('/settings')
def save_settings():
    """Save Navidrome server settings."""
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('navidrome'):
        return jsonify({'error': 'Navidrome provider disabled'}), 403
    try:
        data = request.get_json(force=True) or {}
        
        if 'base_url' in data:
            base_url = data['base_url'].strip()
            config_manager.set('navidrome.base_url', base_url)
            logger.info(f"Navidrome base_url saved: {base_url}")
        
        if 'username' in data:
            username = data['username'].strip()
            config_manager.set('navidrome.username', username)
            logger.info(f"Navidrome username saved: {username}")
        
        if 'password' in data:
            password = data['password'].strip()
            config_manager.set('navidrome.password', password)
            logger.info(f"Navidrome password saved")
        
        if 'path_mappings' in data:
            import json
            path_mappings = data['path_mappings']
            config_manager.set('navidrome.path_mappings', json.dumps(path_mappings))
            logger.info(f"Navidrome path_mappings saved: {len(path_mappings)} mappings")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error saving Navidrome settings: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post('/activate')
def activate_server():
    """Set Navidrome as the active media server."""
    try:
        config_manager.set('active_media_server', 'navidrome')
        logger.info("Navidrome set as active media server")
        return jsonify({
            'success': True,
            'message': 'Navidrome is now the active media server'
        })
    except Exception as e:
        logger.error(f"Error activating Navidrome: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post('/test-connection')
def test_connection():
    """Test connection to Navidrome server."""
    try:
        base_url = config_manager.get('navidrome.base_url', '').strip()
        username = config_manager.get('navidrome.username', '').strip()
        password = config_manager.get('navidrome.password', '').strip()
        
        if not base_url:
            return jsonify({'error': 'Server URL is required'}), 400
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        import requests
        
        # Test ping endpoint
        auth_url = f"{base_url.rstrip('/')}/rest/ping.view"
        params = {
            'u': username,
            'p': password,
            'v': '1.16.1',
            'c': 'SoulSync',
            'f': 'json'
        }
        
        response = requests.get(auth_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            subsonic_response = data.get('subsonic-response', {})
            
            if subsonic_response.get('status') == 'ok':
                version = subsonic_response.get('version', 'unknown')
                logger.info(f"Navidrome connection successful: version {version}")
                
                return jsonify({
                    'connected': True,
                    'version': version,
                    'server_type': subsonic_response.get('type', 'navidrome')
                })
            else:
                error_msg = subsonic_response.get('error', {}).get('message', 'Authentication failed')
                return jsonify({'connected': False, 'error': error_msg}), 400
        else:
            return jsonify({'connected': False, 'error': f'HTTP {response.status_code}'}), 400
            
    except ImportError:
        return jsonify({'error': 'requests library not available'}), 500
    except Exception as e:
        logger.error(f"Navidrome connection test failed: {e}", exc_info=True)
        return jsonify({'connected': False, 'error': str(e)}), 400
