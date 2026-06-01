from web.auth import require_auth
from flask import Blueprint, jsonify, request
from web.services.plugin_registry import list_plugins, get_plugins_for_capability, get_plugin
from core.tiered_logger import get_logger

logger = get_logger("plugins_config_route")
bp = Blueprint("plugins_config", __name__)


def _normalize_sensitive_value_for_ui(key, value):
    """Ensure sensitive values returned to UI are plaintext (or empty on failure)."""
    if value is None:
        return value
    sensitive = {'client_secret', 'access_token', 'refresh_token', 'password', 'token', 'api_key'}
    if key in sensitive and isinstance(value, str) and value.startswith('enc:'):
        from core.security import decrypt_string
        decrypted = decrypt_string(value)
        if isinstance(decrypted, str) and decrypted.startswith('enc:'):
            return ''
        return decrypted
    return value


def _normalize_sensitive_value_for_save(key, value):
    """If UI posted an encrypted blob for a sensitive field, decrypt before re-saving."""
    sensitive = {'client_secret', 'access_token', 'refresh_token', 'password', 'token', 'api_key'}
    if key in sensitive and isinstance(value, str) and value.startswith('enc:'):
        from core.security import decrypt_string
        decrypted = decrypt_string(value)
        if isinstance(decrypted, str) and not decrypted.startswith('enc:'):
            return decrypted
    return value


def _resolve_plugin_name(plugin_id: str) -> str:
    """Normalize plugin identifiers from route paths to canonical plugin IDs."""
    plugin_name = str(plugin_id or '').strip()
    if not plugin_name:
        return plugin_name

    try:
        from core.nexus_framework.plugin_loader import get_all_plugins
        normalized = plugin_name.lower()
        for p in get_all_plugins():
            p_id = str(p.get('id', '')).strip()
            p_name = str(p.get('name', '')).strip()
            if not p_id and not p_name:
                continue
            if (normalized == p_id.lower() or
                normalized == p_name.lower() or
                p_id.lower().endswith(f".{normalized}") or
                p_name.lower().endswith(f".{normalized}")):
                return p_id
    except Exception as e:
        logger.debug(f"Unable to resolve plugin provider '{plugin_name}' to canonical plugin ID: {e}")

    return plugin_name


def _build_active_plex_user_map():
    """Build a display-name to Plex user_id map from active config.db accounts."""
    try:
        from database.config_database import get_config_database

        config_db = get_config_database()
        plex_service_id = config_db.get_or_create_service_id('plex')
        accounts = config_db.get_accounts(service_id=plex_service_id, is_active=True)

        mapping = {}
        for account in accounts:
            user_id = account.get('user_id')
            if not user_id:
                continue

            for key in (account.get('display_name'), account.get('account_name')):
                normalized = (key or '').strip().lower()
                if normalized:
                    mapping[normalized] = str(user_id)
        return mapping
    except Exception as e:
        logger.warning(f"Failed to build Plex user map for provider playlists: {e}")
        return {}


def _match_plex_user_for_account(plex_user_map: dict, account_name: str):
    """Return the Plex user_id for a source account name.

    Tries exact match first, then substring: Plex 'Simi' contained in 'Simi\\'s Spotify'.
    """
    normalized = (account_name or '').strip().lower()
    if not normalized:
        return None
    if normalized in plex_user_map:
        return plex_user_map[normalized]
    for plex_name, uid in plex_user_map.items():
        if plex_name and plex_name in normalized:
            return uid
    return None

@bp.get("")
@bp.get("/")
def list_all_plugins():
    """List all available plugins with their metadata and capabilities.

    Returns a plain array so the Svelte web UI (baseURL=/api) can map it
    directly.
    """
    try:
        plugins_list = list_plugins()
        return jsonify(plugins_list), 200
    except Exception as e:
        logger.error(f"Error listing plugins: {e}")
        return jsonify({'error': str(e)}), 500

@bp.get("/download-clients")
def list_download_clients():
    """List all providers flagged as download clients.
    
    Returns providers with supports_downloads=True capability,
    annotated with 'active' status.
    """
    try:
        from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
        from core.settings import config_manager
        
        from core.nexus_framework.plugin_loader import PluginRegistry
        active_downloads = PluginRegistry.get_active_services_by_type('download')
        active_client = active_downloads[0].split('.')[-1] if active_downloads else None
        download_clients = []
        
        # Get all registered plugins
        clients = PluginRegistry.get_download_clients()
        
        for plugin_name in clients:
            try:
                plugin_class = PluginRegistry.get_plugin_class(plugin_name)
                if plugin_class:
                    download_clients.append({
                        'name': plugin_name,
                        'display_name': plugin_name.title(),
                        'supports_downloads': True,
                        'description': f'Download music via {plugin_name.title()}',
                        'active': plugin_name == active_client
                    })
            except Exception as e:
                logger.error(f"Error processing plugin {plugin_name} for download clients: {e}")
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
        from core.nexus_framework.plugin_loader import PluginRegistry
        active_downloads = PluginRegistry.get_active_services_by_type('download')
        active = active_downloads[0].split('.')[-1] if active_downloads else None
        return jsonify({'active_client': active}), 200
    except Exception as e:
        logger.error(f"Error getting active download client: {e}")
        return jsonify({'error': str(e)}), 500

@bp.post("/download-clients/activate")
@require_auth
def set_active_download_client():
    """Set the active download client."""
    try:
        from core.settings import config_manager
        from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry

        data = request.get_json(silent=True) or {}
        client_name = data.get('client')

        if not client_name:
            return jsonify({'error': 'Client name is required'}), 400

        # Validate client exists and is a download plugin
        plugin_class = PluginRegistry.get_plugin_class(client_name)
        if not plugin_class:
            return jsonify({'error': f'Plugin {client_name} not found'}), 404

        if not getattr(plugin_class, 'supports_downloads', False):
             return jsonify({'error': f'Plugin {client_name} does not support downloads'}), 400

        config_manager.set_active_download_client(client_name)
        logger.info(f"Active download client set to: {client_name}")

        return jsonify({
            'success': True,
            'active_client': client_name
        })
    except Exception as e:
        logger.error(f"Error setting active download client: {e}")
        return jsonify({'error': str(e)}), 500

@bp.post("/<plugin_id>/toggle")
@require_auth
def toggle_plugin(plugin_id):
    """Toggle a plugin's enabled/disabled status.
    
    Updates both persistent config and in-memory registry state.
    """
    try:
        from core.settings import config_manager
        from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
        
        data = request.get_json(silent=True) or {}
        # If enabled is provided in payload, use it, otherwise flip current state
        enabled = data.get('enabled')
        
        current_disabled = config_manager.get_disabled_plugins()
        # Use full ID (plugin_id) to distinguish between core and community plugins
        is_currently_disabled = plugin_id.lower() in [d.lower() for d in current_disabled]
        
        if enabled is None:
            new_enabled = is_currently_disabled
        else:
            new_enabled = enabled
            
        if new_enabled:
            # Enable: remove from disabled list
            new_disabled = [d for d in current_disabled if d.lower() != plugin_id.lower()]
            PluginRegistry.enable_plugin(plugin_id)
        else:
            # Disable: add to disabled list
            if not is_currently_disabled:
                new_disabled = current_disabled + [plugin_id]
            else:
                new_disabled = current_disabled
            PluginRegistry.disable_plugin(plugin_id)
            
        config_manager.set_disabled_plugins(new_disabled)
        
        return jsonify({
            'success': True,
            'enabled': new_enabled,
            'plugin': plugin_id,
            'restart_required': True
        }), 200
    except Exception as e:
        logger.error(f"Error toggling plugin {plugin_id}: {e}")
        return jsonify({'error': str(e)}), 500


@bp.post("/<plugin_id>/rollback")
@require_auth
def rollback_plugin(plugin_id):
    """Roll back a plugin to its previous stable version and state."""
    try:
        from core.nexus_framework.plugin_store import plugin_store
        
        # plugin_id might be a full ID or just a folder name. 
        # PluginStore needs the plugin_id.
        success = plugin_store.rollback_plugin(plugin_id)
        
        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Rollback failed or no snapshot found'}), 400
    except Exception as e:
        logger.error(f"Error rolling back plugin {plugin_id}: {e}")
        return jsonify({'error': str(e)}), 500


@bp.get("/<plugin_id>/playlists")
def get_plugin_playlists(plugin_id):
    """Fetch playlists from a specific plugin."""
    try:
        # Get plugin via registry
        from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
        
        plugin_cls = PluginRegistry.get_plugin_class(plugin_id)
        if not plugin_cls:
            return jsonify({'error': f'Plugin {plugin_id} not found or not installed'}), 404
        
        # Check disabled state before instantiating
        if PluginRegistry.is_plugin_disabled(plugin_id):
            return jsonify({'error': f'Plugin {plugin_id} is disabled'}), 403
        
        # Instantiate plugin
        try:
            plugin = PluginRegistry.create_instance(plugin_id)
        except Exception as e:
            logger.error(f"Error instantiating plugin {plugin_id}: {e}")
            return jsonify({'error': f'Plugin {plugin_id} could not be initialized'}), 500
        
        if not plugin:
            return jsonify({'error': f'Plugin {plugin_id} instance not found'}), 404
        
        # For multi-account plugins (Spotify, Tidal), loop through all accounts
        multi_account_plugins = ['spotify', 'tidal']
        if plugin_id in multi_account_plugins:
            try:
                from core.file_handling.storage import get_storage_service
                storage = get_storage_service()
                plex_user_map = _build_active_plex_user_map()

                accounts = storage.list_accounts(plugin_id)

                if not accounts:
                    # No accounts configured
                    logger.info(f"No accounts found for {plugin_id}")
                    return jsonify({
                        'plugin': plugin_id,
                        'items': [],
                        'total': 0,
                        'status': 'not_configured'
                    }), 200

                all_playlists = []

                for account in accounts:
                    try:
                        account_id = account['id']
                        account_name = account.get('display_name') or account.get('account_name') or f"Account {account_id}"

                        if plugin_id == 'spotify':
                            from plugins.EchoSync.spotify.client import SpotifyClient
                            client = SpotifyClient(account_id=account_id)
                        elif plugin_id == 'tidal':
                            from plugins.EchoSync.tidal.client import TidalClient
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

                                # Keep the original name for the UI string
                                original_name = p_dict.get('name', 'Unknown')
                                p_dict['name'] = original_name
                                # pass account name as a separate field to render in subtle UI
                                p_dict['source_account_name'] = account_name
                                mapped_user_id = _match_plex_user_for_account(plex_user_map, account_name)
                                if mapped_user_id:
                                    p_dict['target_user_id'] = mapped_user_id
                                # record which account this playlist came from so clients can target it later
                                p_dict['account_id'] = account_id
                                all_playlists.append(p_dict)

                    except Exception as acc_err:
                        logger.warning(f"Error fetching playlists for account {account.get('id')}: {acc_err}")
                        continue

                return jsonify({
                    'plugin': plugin_id,
                    'items': all_playlists,
                    'total': len(all_playlists)
                }), 200

            except Exception as e:
                logger.error(f"Error handling multi-account logic for {plugin_id}: {e}")
                return jsonify({'error': str(e)}), 500

        # Standard single-instance plugin logic
        # Check if configured
        if hasattr(plugin, 'is_configured') and not plugin.is_configured():
            logger.info(f"Plugin {plugin_id} is not configured, returning empty list")
            return jsonify({
                'plugin': plugin_id,
                'items': [],
                'total': 0,
                'status': 'not_configured'
            }), 200
        
        # Check if it has a get_user_playlists method
        if not hasattr(plugin, 'get_user_playlists'):
            return jsonify({'error': f'Plugin {plugin_id} does not support playlists'}), 400
        
        logger.info(f"[ROUTE] Calling get_user_playlists on {plugin_id} plugin")
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
            'plugin': plugin_id,
            'items': serialized,
            'total': len(serialized)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching playlists for {plugin_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.get("/<plugin_id>/settings")
def get_plugin_settings(plugin_id):
    """Get settings and schema for a specific plugin.
    
    Returns decrypted credentials for display (show/hide password button in UI).
    The storage service handles decryption automatically via config.db.
    """
    try:
        from database.config_database import get_config_database
        config_db = get_config_database()
        
        # Ensure service exists in config.db
        normalized_plugin_id = _resolve_plugin_name(plugin_id)
        try:
            service_id = config_db.get_or_create_service_id(normalized_plugin_id)
            if not service_id:
                return jsonify({'error': f'Plugin {plugin_id} not found'}), 404
        except Exception:
            return jsonify({'error': f'Plugin {plugin_id} not found'}), 404

        # Retrieve a known set of plugin config keys
        # The new config_db automatically handles decryption
        keys_of_interest = ['client_id', 'client_secret', 'base_url', 'server_url', 'token', 'api_key', 'username', 'password', 'slskd_url']
        config = {}
        for key in keys_of_interest:
            val = config_db.get_service_config(service_id, key)
            if val is not None:
                config[key] = _normalize_sensitive_value_for_ui(key, val)
        
        # Dynamically inject immutable redirect URI for OAuth plugins
        from core.network_utils import get_lan_ip
        lan_ip = get_lan_ip()
        callback_id = normalized_plugin_id.split('.')[-1].lower()
        config['redirect_uri'] = f"https://{lan_ip}:5001/api/oauth/callback/plugins/{callback_id}"
        
        # Mock schema for dynamic UI generation (should eventually come from plugin class)
        schema = _get_mock_schema(plugin_id)
        return jsonify({
            'plugin': plugin_id,
            'settings': config,
            'schema': schema
        }), 200
    except Exception as e:
        logger.error(f"Error getting settings for {plugin_id}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.post("/<plugin_id>/settings")
@require_auth
def update_plugin_settings(plugin_id):
    """Update settings for a specific plugin.
    
    SECURITY:
    - Credentials are encrypted by config_manager before storage
    - Payload is never logged (would expose secrets)
    - Must be called over HTTPS in production
    """
    try:
        payload = request.get_json(silent=True) or {}

        # SECURITY: Log only that we're updating, not the actual credentials
        logger.info(f"Updating settings for plugin: {plugin_id}")

        # Use the config database directly
        from database.config_database import get_config_database
        config_db = get_config_database()

        normalized_plugin_id = _resolve_plugin_name(plugin_id)
        try:
            # Ensure service exists in config.db
            service_id = config_db.get_or_create_service_id(normalized_plugin_id)
            if not service_id:
                return jsonify({'error': f'Plugin {plugin_id} not found'}), 404

            # Default sensitive keys
            sensitive_keys = ['client_secret', 'access_token', 'refresh_token', 'password', 'token', 'api_key']

            all_ok = True

            # Explicitly strip redirect_uri to prevent database persistence of dynamic urls
            if 'redirect_uri' in payload:
                del payload['redirect_uri']

            for k, v in payload.items():
                is_sensitive = k in sensitive_keys or any(s in k.lower() for s in ['secret', 'token', 'password', 'key'])
                value = (v or '').strip() if isinstance(v, str) else v
                if is_sensitive:
                    value = _normalize_sensitive_value_for_save(k, value)
                ok = config_db.set_service_config(service_id, k, value, is_sensitive=is_sensitive)
                if not ok:
                    all_ok = False

            if all_ok:
                logger.info(f"Successfully updated {plugin_id} settings in config.db")
                return jsonify({'success': True, 'message': f'{plugin_id} credentials saved securely'}), 200
            else:
                logger.warning(f"Failed to update one or more settings for {plugin_id}")
                return jsonify({'error': 'Failed to update one or more settings'}), 500
        except Exception as e:
            logger.error(f"Error updating settings for {plugin_id}: {e}")
            return jsonify({'error': 'Failed to update settings'}), 500
    except Exception as e:
        # SECURITY: Log error but not the payload
        logger.error(f"Error updating settings for {plugin_id}: {type(e).__name__}")
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
        from core.nexus_framework.plugin_loader import get_plugin_capabilities as fetch_capabilities
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
def list_plugins_route():
    """Full plugin metadata for diagnostics."""
    try:
        plugins = list_plugins()
        return jsonify({
            'plugins': [p.to_dict() for p in plugins],
            'total': len(plugins)
        }), 200
    except Exception as e:
        logger.error(f"Error listing plugins: {e}")
        return jsonify({'error': str(e)}), 500

@bp.get("/by-capability/<capability>")
def get_plugins_by_capability(capability):
    """Get plugins that support a specific capability."""
    try:
        plugins = get_plugins_for_capability(capability)
        return jsonify({
            'capability': capability,
            'plugins': [p.to_dict() for p in plugins],
            'total': len(plugins)
        }), 200
    except Exception as e:
        logger.error(f"Error getting plugins for capability {capability}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.get("/<plugin_id>")
def get_plugin_details(plugin_id):
    """Get full details for a specific plugin."""
    try:
        plugin = get_plugin(plugin_id)
        if not plugin:
            return jsonify({'error': f'Plugin {plugin_id} not found'}), 404
        
        plugin_dict = plugin.to_dict() if hasattr(plugin, 'to_dict') else plugin
        plugin_dict = _enrich_provider_capabilities(plugin_dict, plugin_id)
        
        return jsonify(plugin_dict), 200
    except Exception as e:
        logger.error(f"Error getting plugin details for {plugin_id}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.get("/<plugin_id>/credentials")
def get_plugin_credentials(plugin_id):
    """Get credentials/configuration for a specific plugin."""
    try:
        from database.config_database import get_config_database
        config_db = get_config_database()
        normalized_plugin_id = _resolve_plugin_name(plugin_id)
        service_id = config_db.get_or_create_service_id(normalized_plugin_id)
        if not service_id:
            return jsonify({'error': f'Plugin {plugin_id} not found'}), 404

        # Fetch directly since config_manager might be deprecated for these
        # But we don't have a get_all_service_config endpoint natively, so we fetch keys of interest
        keys_of_interest = ['client_id', 'client_secret', 'base_url', 'server_url', 'token', 'api_key', 'username', 'password', 'slskd_url']
        credentials = {}
        for key in keys_of_interest:
            val = config_db.get_service_config(service_id, key)
            if val is not None:
                credentials[key] = _normalize_sensitive_value_for_ui(key, val)

        # Dynamically inject immutable redirect URI
        from core.network_utils import get_lan_ip
        lan_ip = get_lan_ip()
        callback_id = normalized_plugin_id.split('.')[-1].lower()
        credentials['redirect_uri'] = f"https://{lan_ip}:5001/api/oauth/callback/plugins/{callback_id}"
        
        return jsonify({
            'plugin': plugin_id,
            'credentials': credentials
        }), 200
    except Exception as e:
        logger.error(f"Error getting credentials for {plugin_id}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.post("/<plugin_id>/credentials")
@require_auth
def set_plugin_credentials(plugin_id):
    """Set credentials/configuration for a specific plugin."""
    try:
        from database.config_database import get_config_database
        
        data = request.get_json(silent=True) or {}
        credentials = data.get('credentials', {})
        
        if not credentials:
            return jsonify({'error': 'No credentials provided'}), 400
        
        # Get or create service in config database
        config_db = get_config_database()
        normalized_plugin_id = _resolve_plugin_name(plugin_id)
        service_id = config_db.get_or_create_service_id(normalized_plugin_id)
        if not service_id:
            return jsonify({'error': f'Plugin {plugin_id} not found'}), 404
        
        # Strip redirect_uri from payload
        if 'redirect_uri' in credentials:
            del credentials['redirect_uri']

        # Store each credential
        for key, value in credentials.items():
            # Mark sensitive keys (like api_key, token, password, secret) as sensitive
            is_sensitive = any(sensitive_word in key.lower() for sensitive_word in ['key', 'token', 'password', 'secret'])
            if is_sensitive:
                value = _normalize_sensitive_value_for_save(key, value)
            config_db.set_service_config(service_id, key, value, is_sensitive=is_sensitive)
        
        logger.info(f"Credentials saved for {plugin_id}")
        
        return jsonify({
            'success': True,
            'plugin': plugin_id,
            'message': 'Credentials saved successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error setting credentials for {plugin_id}: {e}")
        return jsonify({'error': str(e)}), 500
