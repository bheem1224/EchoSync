from core.nexus_framework.plugin_SDK import sdk
"""Navidrome provider routes."""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from core.tiered_logger import get_logger

logger = get_logger("navidrome_routes")

router = APIRouter()


@router.get('/settings')
def get_settings():
    """Get Navidrome server settings (base_url, username, password status)."""
    from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
    if PluginRegistry.is_plugin_disabled('navidrome'):
        return JSONResponse(content={'settings': {}}, status_code=200)
    try:
        base_url = sdk.config.get('navidrome.base_url', '')
        username = sdk.config.get('navidrome.username', '')
        password = sdk.config.get('navidrome.password', '')
        
        # Check if this is the active media server
        active_media_server = sdk.config.get('active_media_server', 'plex')
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
                    'c': 'Echosync',
                    'f': 'json'
                }
                response = requests.get(auth_url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('subsonic-response', {}).get('status') == 'ok':
                        connected = True
            except Exception as e:
                logger.debug(f"Navidrome connection check failed: {e}")
        
        return JSONResponse(content={
            'settings': {
                'base_url': base_url,
                'username': username,
                'has_password': bool(password),
                'connected': connected,
                'is_active': is_active
            }
        })
    except Exception as e:
        logger.error(f"Error getting Navidrome settings: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to get Navidrome settings"}, status_code=500)


@router.post('/settings')
async def save_settings(request: Request):
    """Save Navidrome server settings."""
    from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
    if PluginRegistry.is_plugin_disabled('navidrome'):
        return JSONResponse(content={'error': 'Navidrome provider disabled'}, status_code=403)
    try:
        data = await request.json() or {}
        
        if 'base_url' in data:
            base_url = data['base_url'].strip()
            sdk.config.set('navidrome.base_url', base_url)
            logger.info(f"Navidrome base_url saved: {base_url}")
        
        if 'username' in data:
            username = data['username'].strip()
            sdk.config.set('navidrome.username', username)
            logger.info(f"Navidrome username saved: {username}")
        
        if 'password' in data:
            password = data['password'].strip()
            sdk.config.set('navidrome.password', password)
            logger.info(f"Navidrome password saved")
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error saving Navidrome settings: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to save Navidrome settings"}, status_code=500)


@router.post('/activate')
def activate_server():
    """Set Navidrome as the active media server."""
    try:
        sdk.config.set('active_media_server', 'navidrome')
        logger.info("Navidrome set as active media server")
        return JSONResponse(content={
            'success': True,
            'message': 'Navidrome is now the active media server'
        })
    except Exception as e:
        logger.error(f"Error activating Navidrome: {e}", exc_info=True)
        return JSONResponse(content={"error": "Failed to activate Navidrome server"}, status_code=500)


@router.post('/test-connection')
def test_connection():
    """Test connection to Navidrome server."""
    try:
        base_url = sdk.config.get('navidrome.base_url', '').strip()
        username = sdk.config.get('navidrome.username', '').strip()
        password = sdk.config.get('navidrome.password', '').strip()
        
        if not base_url:
            return JSONResponse(content={'error': 'Server URL is required'}, status_code=400)
        if not username or not password:
            return JSONResponse(content={'error': 'Username and password are required'}, status_code=400)
        
        import requests
        
        # Test ping endpoint
        auth_url = f"{base_url.rstrip('/')}/rest/ping.view"
        params = {
            'u': username,
            'p': password,
            'v': '1.16.1',
            'c': 'Echosync',
            'f': 'json'
        }
        
        response = requests.get(auth_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            subsonic_response = data.get('subsonic-response', {})
            
            if subsonic_response.get('status') == 'ok':
                version = subsonic_response.get('version', 'unknown')
                logger.info(f"Navidrome connection successful: version {version}")
                
                return JSONResponse(content={
                    'connected': True,
                    'version': version,
                    'server_type': subsonic_response.get('type', 'navidrome')
                })
            else:
                error_msg = subsonic_response.get('error', {}).get('message', 'Authentication failed')
                return JSONResponse(content={'connected': False, 'error': error_msg}, status_code=400)
        else:
            return JSONResponse(content={'connected': False, 'error': f'HTTP {response.status_code}'}, status_code=400)
            
    except ImportError:
        return JSONResponse(content={'error': 'requests library not available'}, status_code=500)
    except Exception as e:
        logger.error(f"Navidrome connection test failed: {e}", exc_info=True)
        return JSONResponse(content={"connected": False, "error": "Connection test failed"}, status_code=400)
