from flask import Blueprint, jsonify, request
from web.services.provider_registry import list_providers, get_providers_for_capability, get_provider
from core.tiered_logger import get_logger

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

@bp.get("/download-clients")
def list_download_clients():
    """List all providers flagged as download clients.
    
    Returns providers with supports_downloads=True capability.
    """
    try:
        from core.provider import ProviderRegistry, CAPABILITY_REGISTRY
        
        download_clients = []
        
        # Get all registered providers
        all_providers = ProviderRegistry.list_providers()
        
        for provider_name in all_providers:
            # Check if provider supports downloads
            if provider_name in CAPABILITY_REGISTRY:
                capabilities = CAPABILITY_REGISTRY[provider_name]
                if capabilities.supports_downloads:
                    # Get provider instance
                    provider_class = ProviderRegistry.get_provider_class(provider_name)
                    if provider_class:
                        download_clients.append({
                            'name': provider_name,
                            'display_name': provider_name.title(),
                            'supports_downloads': True,
                            'description': f'Download music via {provider_name.title()}'
                        })
        
        return jsonify(download_clients), 200
        
    except Exception as e:
        logger.error(f"Error listing download clients: {e}")
        return jsonify({'error': str(e)}), 500

@bp.get("/<provider_name>/playlists")
def get_provider_playlists(provider_name):
    """Fetch playlists from a specific provider."""
    try:
        # Get provider via registry
        from core.provider import ProviderRegistry
        
        provider_cls = ProviderRegistry.get_provider_class(provider_name)
        if not provider_cls:
            return jsonify({'error': f'Provider {provider_name} not found or not installed'}), 404
        
        # Instantiate provider
        try:
            plugin = ProviderRegistry.create_instance(provider_name)
        except ValueError as e:
            return jsonify({'error': f'Provider {provider_name} is disabled'}), 403
        
        if not plugin:
            return jsonify({'error': f'Provider {provider_name} instance not found'}), 404
        
        # For multi-account providers (Spotify, Tidal), try to use specific account if available
        multi_account_providers = ['spotify', 'tidal']
        if provider_name in multi_account_providers:
            try:
                from sdk.storage_service import get_storage_service
                storage = get_storage_service()

                accounts = storage.list_accounts(provider_name)
                if accounts and len(accounts) > 0:
                    # Use first account for now
                    account_id = accounts[0]['id']

                    if provider_name == 'spotify':
                        from providers.spotify.client import SpotifyClient
                        plugin = SpotifyClient(account_id=account_id)
                    elif provider_name == 'tidal':
                        from providers.tidal.client import TidalClient
                        plugin = TidalClient(account_id=str(account_id))
            except Exception as e:
                logger.warning(f"Error checking accounts for {provider_name}: {e}")
                # Fallback to default plugin instance

        # Check if configured (common for all providers)
        if hasattr(plugin, 'is_configured') and not plugin.is_configured():
            # If specifically not configured, return empty list (200) instead of error (400)
            # This allows the UI to render "No playlists" or handle empty state gracefully
            logger.info(f"Provider {provider_name} is not configured, returning empty list")
            return jsonify({
                'provider': provider_name,
                'items': [],
                'total': 0,
                'status': 'not_configured'
            }), 200
        
        # Check if it has a get_user_playlists method
        if not hasattr(plugin, 'get_user_playlists'):
            return jsonify({'error': f'Provider {provider_name} does not support playlists'}), 400
        
        logger.info(f"[ROUTE] Calling get_user_playlists on {provider_name} provider")
        playlists = plugin.get_user_playlists()
        logger.info(f"[ROUTE] get_user_playlists returned {len(playlists) if playlists else 0} playlists")
        logger.info(f"[ROUTE] Playlists type: {type(playlists)}, content: {playlists}")
        
        # Convert to serializable format if needed
        serialized = []
        for p in playlists:
            if hasattr(p, '__dict__'):
                serialized.append(p.__dict__)
            elif isinstance(p, dict):
                serialized.append(p)
            else:
                # Try to convert to dict for unknown types
                try:
                    serialized.append({'id': getattr(p, 'id', ''), 'name': getattr(p, 'name', str(p))})
                except:
                    serialized.append({'name': str(p)})
        
        logger.info(f"[ROUTE] Serialized {len(serialized)} playlists for response")
        response_data = {
            'provider': provider_name,
            'items': serialized,
            'total': len(serialized)
        }
        logger.info(f"[ROUTE] Response: {response_data}")
        return jsonify(response_data), 200
    except Exception as e:
        logger.error(f"Error fetching playlists for {provider_name}: {e}", exc_info=True)
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
        
        # Ensure service exists in config.db
        try:
            storage.ensure_service(provider_name)
        except Exception:
            return jsonify({'error': f'Provider {provider_name} not found'}), 404

        # Retrieve a known set of provider config keys (client_id, client_secret, redirect_uri)
        # Storage service returns decrypted values when present in config.db
        keys_of_interest = ['client_id', 'client_secret', 'redirect_uri']
        config = {}
        for key in keys_of_interest:
            config[key] = storage.get_service_config(provider_name, key)
        
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

        # SECURITY: Log only that we're updating, not the actual credentials
        logger.info(f"Updating settings for provider: {provider_name}")

        # Use the storage service so credentials are saved into the encrypted config.db
        from sdk.storage_service import get_storage_service
        storage = get_storage_service()

        try:
            # Ensure service exists in config.db
            storage.ensure_service(provider_name)

            # Default sensitive keys
            sensitive_keys = ['client_secret', 'access_token', 'refresh_token']

            all_ok = True
            for k, v in payload.items():
                is_sensitive = k in sensitive_keys
                ok = storage.set_service_config(provider_name, k, (v or '').strip() if isinstance(v, str) else v, is_sensitive=is_sensitive)
                if not ok:
                    all_ok = False

            if all_ok:
                logger.info(f"Successfully updated {provider_name} settings in config.db")
                return jsonify({'success': True, 'message': f'{provider_name} credentials saved securely'}), 200
            else:
                logger.warning(f"Failed to update one or more settings for {provider_name}")
                return jsonify({'error': 'Failed to update one or more settings'}), 500
        except Exception as e:
            logger.error(f"Error updating settings for {provider_name}: {e}")
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
            {'key': 'redirect_uri', 'label': 'Redirect URI', 'type': 'text', 'default': 'http://127.0.0.1:8008/api/spotify/callback'},
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
        from core.provider import get_provider_capabilities as fetch_capabilities
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
