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
    
    Returns providers with supports_downloads=True capability,
    annotated with 'active' status.
    """
    try:
        from core.provider import ProviderRegistry
        from core.settings import config_manager
        
        active_client = config_manager.get_active_download_client()
        download_clients = []
        
        # Get all registered providers
        clients = ProviderRegistry.get_download_clients()
        
        for provider_name in clients:
            try:
                provider_class = ProviderRegistry.get_provider_class(provider_name)
                if provider_class:
                    download_clients.append({
                        'name': provider_name,
                        'display_name': provider_name.title(),
                        'supports_downloads': True,
                        'description': f'Download music via {provider_name.title()}',
                        'active': provider_name == active_client
                    })
            except Exception as e:
                logger.error(f"Error processing provider {provider_name} for download clients: {e}")
                continue
        
        return jsonify(download_clients), 200
        
    except Exception as e:
        logger.error(f"Error listing download clients: {e}")
        return jsonify({'error': str(e)}), 500

@bp.get("/download-clients/active")
def get_active_download_client():
    """Get the currently active download client."""
    try:
        from core.settings import config_manager
        active = config_manager.get_active_download_client()
        return jsonify({'active_client': active}), 200
    except Exception as e:
        logger.error(f"Error getting active download client: {e}")
        return jsonify({'error': str(e)}), 500

@bp.post("/download-clients/activate")
def set_active_download_client():
    """Set the active download client."""
    try:
        from core.settings import config_manager
        from core.provider import ProviderRegistry

        data = request.get_json(silent=True) or {}
        client_name = data.get('client')

        if not client_name:
            return jsonify({'error': 'Client name is required'}), 400

        # Validate client exists and is a download provider
        provider_class = ProviderRegistry.get_provider_class(client_name)
        if not provider_class:
            return jsonify({'error': f'Provider {client_name} not found'}), 404

        if not getattr(provider_class, 'supports_downloads', False):
             return jsonify({'error': f'Provider {client_name} does not support downloads'}), 400

        config_manager.set_active_download_client(client_name)
        logger.info(f"Active download client set to: {client_name}")

        return jsonify({
            'success': True,
            'active_client': client_name
        })
    except Exception as e:
        logger.error(f"Error setting active download client: {e}")
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
        
        # Check disabled state before instantiating
        if ProviderRegistry.is_provider_disabled(provider_name):
            return jsonify({'error': f'Provider {provider_name} is disabled'}), 403
        
        # Instantiate provider
        try:
            plugin = ProviderRegistry.create_instance(provider_name)
        except Exception as e:
            logger.error(f"Error instantiating provider {provider_name}: {e}")
            return jsonify({'error': f'Provider {provider_name} could not be initialized'}), 500
        
        if not plugin:
            return jsonify({'error': f'Provider {provider_name} instance not found'}), 404
        
        # For multi-account providers (Spotify, Tidal), loop through all accounts
        multi_account_providers = ['spotify', 'tidal']
        if provider_name in multi_account_providers:
            try:
                from core.storage import get_storage_service
                storage = get_storage_service()

                accounts = storage.list_accounts(provider_name)

                if not accounts:
                    # No accounts configured
                    logger.info(f"No accounts found for {provider_name}")
                    return jsonify({
                        'provider': provider_name,
                        'items': [],
                        'total': 0,
                        'status': 'not_configured'
                    }), 200

                all_playlists = []

                for account in accounts:
                    try:
                        account_id = account['id']
                        account_name = account.get('display_name') or account.get('account_name') or f"Account {account_id}"

                        if provider_name == 'spotify':
                            from providers.spotify.client import SpotifyClient
                            client = SpotifyClient(account_id=account_id)
                        elif provider_name == 'tidal':
                            from providers.tidal.client import TidalClient
                            client = TidalClient(account_id=str(account_id))
                        else:
                            continue

                        if hasattr(client, 'is_configured') and not client.is_configured():
                            continue

                        if hasattr(client, 'get_user_playlists'):
                            playlists = client.get_user_playlists()
                            for p in playlists:
                                # Convert to dict
                                if hasattr(p, '__dict__'):
                                    p_dict = p.__dict__.copy()
                                elif isinstance(p, dict):
                                    p_dict = p.copy()
                                else:
                                    continue

                                # Append account name to playlist name and keep id
                                original_name = p_dict.get('name', 'Unknown')
                                p_dict['name'] = f"{original_name} ({account_name})"
                                # record which account this playlist came from so clients can target it later
                                p_dict['account_id'] = account_id
                                all_playlists.append(p_dict)

                    except Exception as acc_err:
                        logger.warning(f"Error fetching playlists for account {account.get('id')}: {acc_err}")
                        continue

                return jsonify({
                    'provider': provider_name,
                    'items': all_playlists,
                    'total': len(all_playlists)
                }), 200

            except Exception as e:
                logger.error(f"Error handling multi-account logic for {provider_name}: {e}")
                return jsonify({'error': str(e)}), 500

        # Standard single-instance provider logic
        # Check if configured
        if hasattr(plugin, 'is_configured') and not plugin.is_configured():
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
        
        # Convert to serializable format
        serialized = []
        for p in playlists:
            if hasattr(p, '__dict__'):
                serialized.append(p.__dict__)
            elif isinstance(p, dict):
                serialized.append(p)
            else:
                try:
                    serialized.append({'id': getattr(p, 'id', ''), 'name': getattr(p, 'name', str(p))})
                except:
                    serialized.append({'name': str(p)})
        
        return jsonify({
            'provider': provider_name,
            'items': serialized,
            'total': len(serialized)
        }), 200
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
        from database.config_database import get_config_database
        config_db = get_config_database()
        
        # Ensure service exists in config.db
        try:
            service_id = config_db.get_or_create_service_id(provider_name)
        except Exception:
            return jsonify({'error': f'Provider {provider_name} not found'}), 404

        # Retrieve a known set of provider config keys
        # The new config_db automatically handles decryption
        keys_of_interest = ['client_id', 'client_secret', 'base_url', 'server_url', 'token', 'api_key', 'username', 'password', 'slskd_url']
        config = {}
        for key in keys_of_interest:
            val = config_db.get_service_config(service_id, key)
            if val is not None:
                config[key] = val
        
        # Dynamically inject immutable redirect URI for OAuth providers
        from core.network_utils import get_lan_ip
        lan_ip = get_lan_ip()
        config['redirect_uri'] = f"https://{lan_ip}:5001/api/oauth/callback/{provider_name}"

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

        # Use the config database directly
        from database.config_database import get_config_database
        config_db = get_config_database()

        try:
            # Ensure service exists in config.db
            service_id = config_db.get_or_create_service_id(provider_name)

            # Default sensitive keys
            sensitive_keys = ['client_secret', 'access_token', 'refresh_token', 'password', 'token', 'api_key']

            all_ok = True

            # Explicitly strip redirect_uri to prevent database persistence of dynamic urls
            if 'redirect_uri' in payload:
                del payload['redirect_uri']

            for k, v in payload.items():
                is_sensitive = k in sensitive_keys or any(s in k.lower() for s in ['secret', 'token', 'password', 'key'])
                ok = config_db.set_service_config(service_id, k, (v or '').strip() if isinstance(v, str) else v, is_sensitive=is_sensitive)
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
            {'key': 'slskd_url', 'label': 'slskd URL', 'type': 'text', 'default': 'http://localhost:5030'},
            {'key': 'api_key', 'label': 'API Key', 'type': 'password', 'sensitive': True},
        ],
        'slskd': [
            {'key': 'username', 'label': 'Username', 'type': 'text'},
            {'key': 'password', 'label': 'Password', 'type': 'password', 'sensitive': True},
            {'key': 'slskd_url', 'label': 'slskd URL', 'type': 'text', 'default': 'http://localhost:5030'},
            {'key': 'api_key', 'label': 'API Key', 'type': 'password', 'sensitive': True},
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

@bp.get("/<provider_name>/credentials")
def get_provider_credentials(provider_name):
    """Get credentials/configuration for a specific provider."""
    try:
        from database.config_database import get_config_database
        config_db = get_config_database()
        
        service_id = config_db.get_or_create_service_id(provider_name)
        # Fetch directly since config_manager might be deprecated for these
        # But we don't have a get_all_service_config endpoint natively, so we fetch keys of interest
        keys_of_interest = ['client_id', 'client_secret', 'base_url', 'server_url', 'token', 'api_key', 'username', 'password', 'slskd_url']
        credentials = {}
        for key in keys_of_interest:
            val = config_db.get_service_config(service_id, key)
            if val is not None:
                credentials[key] = val

        # Dynamically inject immutable redirect URI
        from core.network_utils import get_lan_ip
        lan_ip = get_lan_ip()
        credentials['redirect_uri'] = f"https://{lan_ip}:5001/api/oauth/callback/{provider_name}"
        
        return jsonify({
            'provider': provider_name,
            'credentials': credentials
        }), 200
    except Exception as e:
        logger.error(f"Error getting credentials for {provider_name}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.post("/<provider_name>/credentials")
def set_provider_credentials(provider_name):
    """Set credentials/configuration for a specific provider."""
    try:
        from database.config_database import get_config_database
        
        data = request.get_json(silent=True) or {}
        credentials = data.get('credentials', {})
        
        if not credentials:
            return jsonify({'error': 'No credentials provided'}), 400
        
        # Get or create service in config database
        config_db = get_config_database()
        service_id = config_db.get_or_create_service_id(provider_name)
        
        # Strip redirect_uri from payload
        if 'redirect_uri' in credentials:
            del credentials['redirect_uri']

        # Store each credential
        for key, value in credentials.items():
            # Mark sensitive keys (like api_key, token, password, secret) as sensitive
            is_sensitive = any(sensitive_word in key.lower() for sensitive_word in ['key', 'token', 'password', 'secret'])
            config_db.set_service_config(service_id, key, value, is_sensitive=is_sensitive)
        
        logger.info(f"Credentials saved for {provider_name}")
        
        return jsonify({
            'success': True,
            'provider': provider_name,
            'message': 'Credentials saved successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error setting credentials for {provider_name}: {e}")
        return jsonify({'error': str(e)}), 500
