"""Media server selection API."""

from flask import Blueprint, request, jsonify
from config.settings import config_manager
from utils.logging_config import get_logger

logger = get_logger("media_server")

bp = Blueprint('media_server', __name__, url_prefix='/api/media-server')


@bp.get('/active')
def get_active_server():
    """Get the currently active media server."""
    try:
        active_server = config_manager.get('active_media_server', 'plex')
        return jsonify({
            'active_server': active_server
        })
    except Exception as e:
        logger.error(f"Error getting active media server: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post('/activate')
def set_active_server():
    """Set the active media server."""
    try:
        data = request.get_json(force=True) or {}
        server_name = data.get('server')
        
        if not server_name:
            return jsonify({'error': 'Server name is required'}), 400
        
        # Validate server name
        valid_servers = ['plex', 'jellyfin', 'navidrome']
        if server_name not in valid_servers:
            return jsonify({'error': f'Invalid server. Must be one of: {", ".join(valid_servers)}'}), 400
        
        config_manager.set('active_media_server', server_name)
        logger.info(f"Active media server set to: {server_name}")
        
        return jsonify({
            'success': True,
            'active_server': server_name
        })
    except Exception as e:
        logger.error(f"Error setting active media server: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
