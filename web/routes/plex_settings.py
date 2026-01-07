"""Plex server settings API."""

from flask import Blueprint, request, jsonify
from config.settings import config_manager
from utils.logging_config import get_logger

logger = get_logger("plex_settings")

bp = Blueprint('plex_settings', __name__, url_prefix='/api/plex')


@bp.get('/settings')
def get_settings():
    """Get Plex server settings (base_url, token status)."""
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
        
        return jsonify({
            'settings': {
                'base_url': base_url,
                'server_name': server_name,
                'has_token': bool(token),
                'connected': connected,
                'is_active': is_active
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
