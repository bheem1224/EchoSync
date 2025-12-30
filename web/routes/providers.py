from flask import Blueprint, jsonify, request
from web.services.provider_registry import list_providers, get_providers_for_capability, get_provider
from plugins.adapter_registry import AdapterRegistry
from utils.logging_config import get_logger

logger = get_logger("providers_route")
bp = Blueprint("providers", __name__, url_prefix="/api/providers")

@bp.get("")
@bp.get("/")
def list_all_providers():
    """List all available providers with their metadata and capabilities.

    Returns a plain array so the Svelte web UI (baseURL=/api) can map it
    directly.
    """
    try:
        providers_list = list_providers()
        return jsonify(providers_list), 200
    except Exception as e:
        logger.error(f"Error listing providers: {e}")
        return jsonify({'error': str(e)}), 500

@bp.get("/<provider_name>/playlists")
def get_provider_playlists(provider_name):
    """Fetch playlists from a specific provider."""
    try:
        # Get provider via registry
        from plugins.plugin_system import plugin_registry
        
        plugin = plugin_registry.get_plugin(provider_name)
        if not plugin:
            return jsonify({'error': f'Provider {provider_name} not found or not installed'}), 404
        
        # Instantiate client if it has a get_user_playlists method
        if not hasattr(plugin, 'get_user_playlists'):
            return jsonify({'error': f'Provider {provider_name} does not support playlists'}), 400
        
        playlists = plugin.get_user_playlists()
        
        # Convert to serializable format if needed
        serialized = []
        for p in playlists:
            if hasattr(p, '__dict__'):
                serialized.append(p.__dict__)
            else:
                serialized.append(p)
                
        return jsonify({
            'provider': provider_name,
            'items': serialized,
            'total': len(serialized)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching playlists for {provider_name}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.get("/<provider_name>/settings")
def get_provider_settings(provider_name):
    """Get settings and schema for a specific provider.
    
    Returns decrypted credentials for display (show/hide password button in UI).
    The storage service handles decryption automatically via config.db.
    """
    try:
        from sdk.storage_service import get_storage_service
        storage = get_storage_service()
        
        # Ensure service exists
        try:
            storage.ensure_service(provider_name)
        except Exception:
            return jsonify({'error': f'Provider {provider_name} not found'}), 404
        
        # Get all config keys for this provider
        # Storage service automatically decrypts sensitive values
        from database.music_database import get_database
        db = get_database()
        
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM services WHERE name = ?", (provider_name,))
            row = c.fetchone()
            if not row:
                return jsonify({'error': f'Provider {provider_name} not found'}), 404
            service_id = row[0]
            
            # Get config via storage service (handles decryption)
            c.execute("SELECT config_key FROM service_config WHERE service_id = ?", (service_id,))
            keys = [row['config_key'] for row in c.fetchall()]
            
            # Retrieve each value (storage service decrypts automatically)
            config = {}
            for key in keys:
                value = storage.get_service_config(provider_name, key)
                config[key] = value  # Already decrypted by storage service
        
        # Mock schema for dynamic UI generation (should eventually come from provider class)
        schema = _get_mock_schema(provider_name)
        
        return jsonify({
            'provider': provider_name,
            'settings': config,
            'schema': schema
        }), 200
    except Exception as e:
        logger.error(f"Error getting settings for {provider_name}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.post("/<provider_name>/settings")
def update_provider_settings(provider_name):
    """Update settings for a specific provider.
    
    SECURITY:
    - Credentials are encrypted by config_manager before storage
    - Payload is never logged (would expose secrets)
    - Must be called over HTTPS in production
    """
    try:
        payload = request.get_json(silent=True) or {}
        from config.settings import config_manager
        
        # SECURITY: Log only that we're updating, not the actual credentials
        logger.info(f"Updating settings for provider: {provider_name}")
        
        # Use config_manager to set credentials
        # This handles encryption and database storage automatically
        success = config_manager.set_service_credentials(provider_name, payload)
        
        if success:
            # SECURITY: Return only success, not echoing back the data
            logger.info(f"Successfully updated {provider_name} settings")
            return jsonify({'success': True, 'message': f'{provider_name} credentials saved securely'}), 200
        else:
            logger.warning(f"Failed to update settings for {provider_name}")
            return jsonify({'error': 'Failed to update settings'}), 500
    except Exception as e:
        # SECURITY: Log error but not the payload
        logger.error(f"Error updating settings for {provider_name}: {type(e).__name__}")
        return jsonify({'error': 'Failed to update settings'}), 500

def _get_mock_schema(provider_name):
    """Temporary mock schema until providers declare their own."""
    schemas = {
        'spotify': [
            {'key': 'client_id', 'label': 'Client ID', 'type': 'text', 'sensitive': True},
            {'key': 'client_secret', 'label': 'Client Secret', 'type': 'password', 'sensitive': True},
            {'key': 'redirect_uri', 'label': 'Redirect URI', 'type': 'text', 'default': 'http://localhost:8888/callback'},
        ],
        'plex': [
            {'key': 'server_url', 'label': 'Server URL', 'type': 'text', 'default': 'http://localhost:32400'},
            {'key': 'token', 'label': 'X-Plex-Token', 'type': 'password', 'sensitive': True},
        ],
        'soulseek': [
            {'key': 'username', 'label': 'Username', 'type': 'text'},
            {'key': 'password', 'label': 'Password', 'type': 'password', 'sensitive': True},
            {'key': 'server_url', 'label': 'slskd URL', 'type': 'text', 'default': 'http://localhost:5030'},
        ]
    }
    return schemas.get(provider_name, [])

def _enrich_provider_capabilities(provider_dict, provider_name=None):
    """Enrich a provider dict with capability metadata.
    
    Args:
        provider_dict: The provider dictionary to enrich
        provider_name: Optional provider name override (defaults to dict's name/id)
    
    Used by tests to verify capability enrichment logic.
    Returns the provider dict with added capability fields.
    """
    try:
        from core.provider_capabilities import get_provider_capabilities as fetch_capabilities
        name = provider_name or provider_dict.get('name') or provider_dict.get('id')
        
        caps = fetch_capabilities(name)
        provider_dict['metadata_richness'] = caps.metadata.name if hasattr(caps, 'metadata') else 'MEDIUM'
        provider_dict['supports_streaming'] = caps.supports_streaming if hasattr(caps, 'supports_streaming') else False
        provider_dict['supports_downloads'] = caps.supports_downloads if hasattr(caps, 'supports_downloads') else False
        provider_dict['supports_cover_art'] = caps.supports_cover_art if hasattr(caps, 'supports_cover_art') else False
        provider_dict['supports_library_scan'] = caps.supports_library_scan if hasattr(caps, 'supports_library_scan') else False
        provider_dict['playlist_support'] = caps.supports_playlists.name if hasattr(caps, 'supports_playlists') and caps.supports_playlists else 'NONE'
        
        if hasattr(caps, 'search'):
            provider_dict['search_capabilities'] = {
                'tracks': caps.search.tracks if hasattr(caps.search, 'tracks') else False,
                'artists': caps.search.artists if hasattr(caps.search, 'artists') else False,
                'albums': caps.search.albums if hasattr(caps.search, 'albums') else False,
                'playlists': caps.search.playlists if hasattr(caps.search, 'playlists') else False,
            }
    except KeyError:
        # Provider not in capability registry, use defaults
        provider_dict['metadata_richness'] = 'MEDIUM'
        provider_dict['supports_streaming'] = False
        provider_dict['supports_downloads'] = False
        provider_dict['supports_cover_art'] = False
        provider_dict['supports_library_scan'] = False
        provider_dict['playlist_support'] = 'NONE'
        provider_dict['search_capabilities'] = {
            'tracks': False, 'artists': False, 'albums': False, 'playlists': False
        }
    except Exception:
        # If something goes wrong, just return the provider as-is
        pass
    
    return provider_dict

@bp.get("/full")
def list_providers_route():
    """Full provider metadata for diagnostics (legacy shape)."""
    try:
        providers = list_providers()
        return jsonify({
            'plugins': [p.to_dict() for p in providers],
            'total': len(providers)
        }), 200
    except Exception as e:
        logger.error(f"Error listing providers: {e}")
        return jsonify({'error': str(e)}), 500

@bp.get("/by-capability/<capability>")
def get_providers_by_capability(capability):
    """Get providers that support a specific capability."""
    try:
        providers = get_providers_for_capability(capability)
        return jsonify({
            'capability': capability,
            'providers': [p.to_dict() for p in providers],
            'total': len(providers)
        }), 200
    except Exception as e:
        logger.error(f"Error getting providers for capability {capability}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.get("/<provider_name>")
def get_provider_details(provider_name):
    """Get full details for a specific provider."""
    try:
        provider = get_provider(provider_name)
        if not provider:
            return jsonify({'error': f'Provider {provider_name} not found'}), 404
        
        provider_dict = provider.to_dict()
        provider_dict = _enrich_provider_capabilities(provider_dict, provider_name)
        
        return jsonify(provider_dict), 200
    except Exception as e:
        logger.error(f"Error getting provider details for {provider_name}: {e}")
        return jsonify({'error': str(e)}), 500
