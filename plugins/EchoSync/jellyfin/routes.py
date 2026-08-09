from core.nexus_framework.plugin_SDK import sdk
"""Jellyfin provider routes."""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from core.tiered_logger import get_logger

logger = get_logger("jellyfin_routes")

router = APIRouter()


@router.get('/settings')
def get_settings():
    """Get Jellyfin server settings (base_url, username, password status)."""
    from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
    if PluginRegistry.is_plugin_disabled('jellyfin'):
        return JSONResponse(content={'settings': {}}, status_code=200)
    try:
        base_url = sdk.config.get('jellyfin.base_url', '')
        username = sdk.config.get('jellyfin.username', '')
        password = sdk.config.get('jellyfin.password', '')
        
        # Check if this is the active media server
        active_media_server = sdk.config.get('active_media_server', 'plex')
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
                    'X-Emby-Authorization': 'MediaBrowser Client="Echosync", Device="Echosync", DeviceId="echosync-1", Version="1.0.0"'
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
        logger.error(f"Error getting Jellyfin settings: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.post('/settings')
async def save_settings(request: Request):
    """Save Jellyfin server settings."""
    from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
    if PluginRegistry.is_plugin_disabled('jellyfin'):
        return JSONResponse(content={'error': 'Jellyfin provider disabled'}, status_code=403)
    try:
        data = await request.json() or {}
        
        if 'base_url' in data:
            base_url = data['base_url'].strip()
            sdk.config.set('jellyfin.base_url', base_url)
            logger.info(f"Jellyfin base_url saved: {base_url}")
        
        if 'username' in data:
            username = data['username'].strip()
            sdk.config.set('jellyfin.username', username)
            logger.info(f"Jellyfin username saved: {username}")
        
        if 'password' in data:
            password = data['password'].strip()
            sdk.config.set('jellyfin.password', password)
            logger.info(f"Jellyfin password saved")
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Error saving Jellyfin settings: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.post('/activate')
def activate_server():
    """Set Jellyfin as the active media server."""
    try:
        sdk.config.set('active_media_server', 'jellyfin')
        logger.info("Jellyfin set as active media server")
        return JSONResponse(content={
            'success': True,
            'message': 'Jellyfin is now the active media server'
        })
    except Exception as e:
        logger.error(f"Error activating Jellyfin: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.post('/test-connection')
def test_connection():
    """Test connection to Jellyfin server."""
    try:
        base_url = sdk.config.get('jellyfin.base_url', '').strip()
        username = sdk.config.get('jellyfin.username', '').strip()
        password = sdk.config.get('jellyfin.password', '').strip()
        
        if not base_url:
            return JSONResponse(content={'error': 'Server URL is required'}, status_code=400)
        if not username or not password:
            return JSONResponse(content={'error': 'Username and password are required'}, status_code=400)
        
        import requests
        
        # Test authentication endpoint
        auth_url = f"{base_url.rstrip('/')}/Users/AuthenticateByName"
        headers = {
            'Content-Type': 'application/json',
            'X-Emby-Authorization': 'MediaBrowser Client="Echosync", Device="Echosync", DeviceId="echosync-1", Version="1.0.0"'
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
                    'X-Emby-Authorization': f'MediaBrowser Client="Echosync", Device="Echosync", DeviceId="echosync-1", Version="1.0.0", Token="{access_token}"'
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
            
            return JSONResponse(content={
                'connected': True,
                'version': version,
                'server_name': server_name,
                'user_id': user_id
            })
        elif response.status_code == 401:
            return JSONResponse(content={'connected': False, 'error': 'Invalid username or password'}, status_code=400)
        else:
            return JSONResponse(content={'connected': False, 'error': f'HTTP {response.status_code}'}, status_code=400)
            
    except ImportError:
        return JSONResponse(content={'error': 'requests library not available'}, status_code=500)
    except Exception as e:
        logger.error(f"Jellyfin connection test failed: {e}", exc_info=True)
        return JSONResponse(content={"connected": False, "error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Connection test failed"}, status_code=400)
