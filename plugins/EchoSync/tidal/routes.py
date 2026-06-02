"""Tidal provider routes."""
import logging
from flask import Blueprint, request, jsonify
from core.tiered_logger import get_logger

logger = get_logger("tidal_routes")
bp = Blueprint("tidal_routes", __name__, url_prefix="/api/plugins/tidal")


@bp.get('')
def list_accounts():
    """List all Tidal accounts."""
    from core.nexus_framework.plugin_loader import PluginRegistry
    # Use the namespaced ID
    plugin_id = 'EchoSync/tidal'
    
    if PluginRegistry.is_plugin_disabled(plugin_id) or PluginRegistry.is_plugin_disabled('tidal'):
        return jsonify({'accounts': [], 'redirect_uri': ''}), 200

    try:
        from core.nexus_framework.plugin_loader import get_plugin
        plugin = get_plugin(plugin_id)
        if not plugin:
            return jsonify({'error': f'Plugin {plugin_id} not found'}), 404
            
        # Use the plugin's accounts SDK facade
        db_accounts = plugin.accounts.get_all()
        accounts = []
        
        for a in db_accounts:
            # Load per-account credentials via the accounts SDK
            # The account_metadata table has been removed, so we use global config instead
            client_id = plugin.config.get('client_id')
            client_secret_present = bool(plugin.secrets.get('client_secret'))
            
            normalized = {
                'id': a.get('id'),
                'account_name': a.get('account_name') or a.get('display_name') or 'Unnamed',
                'display_name': a.get('display_name') or a.get('account_name') or 'Unnamed',
                'user_id': a.get('user_id'),
                'is_active': a.get('is_active'),
                'is_authenticated': a.get('is_authenticated'),
                'client_id': client_id,
                'client_secret_configured': client_secret_present
            }
            accounts.append(normalized)
        
        # Get global redirect URI from config facade
        from core.network_utils import get_lan_ip
        redirect_uri = f"https://{get_lan_ip()}:5001/api/oauth/callback/plugins/tidal"
        
        return jsonify({
            'accounts': accounts,
            'redirect_uri': redirect_uri
        })
    except Exception as e:
        logger.error(f"Error getting Tidal accounts: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.post('')
def create_account():
    """
    Create a new Tidal account with per-account credentials.
    Body: { account_name, client_id, client_secret }
    """
    from core.nexus_framework.plugin_loader import PluginRegistry
    plugin_id = 'EchoSync/tidal'
    if PluginRegistry.is_plugin_disabled(plugin_id) or PluginRegistry.is_plugin_disabled('tidal'):
        return jsonify({'error': 'Tidal provider is disabled'}), 403
    try:
        payload = request.get_json(force=True) or {}
        account_name = (payload.get('account_name') or '').strip()
        client_id = (payload.get('client_id') or '').strip()
        client_secret = (payload.get('client_secret') or '').strip()
        
        if not account_name:
            return jsonify({'error': 'account_name is required'}), 400
        if not client_id or not client_secret:
            return jsonify({'error': 'client_id and client_secret are required'}), 400
        
        from core.nexus_framework.plugin_loader import get_plugin
        plugin = get_plugin(plugin_id)
        if not plugin:
            return jsonify({'error': 'Plugin instance not found'}), 500
        
        # Create account in encrypted config.db via SDK
        account_id = plugin.accounts.ensure_account(account_name=account_name, display_name=account_name)
        if not account_id:
            return jsonify({'error': 'Failed to create account'}), 500
        
        # Global credentials instead of per-account metadata
        
        # Also sync to global config if this is the first one
        plugin.config.set('client_id', client_id)
        plugin.secrets.set('client_secret', client_secret)
        
        logger.info(f"Created Tidal account {account_id} with credentials")
        
        return jsonify({
            'account': {
                'id': account_id,
                'account_name': account_name,
                'display_name': account_name,
                'is_active': False,
                'is_authenticated': False,
                'client_id': client_id,
                'client_secret_configured': True
            }
        }), 201
    except Exception as e:
        logger.error(f"Error creating Tidal account: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.get('/<int:account_id>')
def get_account(account_id):
    """Get a specific Tidal account with credentials."""
    from core.nexus_framework.plugin_loader import PluginRegistry
    plugin_id = 'EchoSync/tidal'
    if PluginRegistry.is_plugin_disabled(plugin_id) or PluginRegistry.is_plugin_disabled('tidal'):
        return jsonify({'error': 'Tidal provider is disabled'}), 403
    try:
        from core.nexus_framework.plugin_loader import get_plugin
        plugin = get_plugin(plugin_id)
        if not plugin:
            return jsonify({'error': 'Plugin not found'}), 404
            
        accounts = plugin.accounts.get_all()
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Load global credentials via SDK since account_metadata is removed
        client_id = plugin.config.get('client_id')
        client_secret = plugin.secrets.get('client_secret')
        
        return jsonify({
            'account': {
                'id': account.get('id'),
                'account_name': account.get('account_name') or account.get('display_name') or 'Unnamed',
                'display_name': account.get('display_name') or account.get('account_name') or 'Unnamed',
                'user_id': account.get('user_id'),
                'is_active': account.get('is_active'),
                'is_authenticated': account.get('is_authenticated'),
                'client_id': client_id,
                'client_secret': client_secret  # Only returned on explicit GET
            }
        })
    except Exception as e:
        logger.error(f"Error getting Tidal account: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.put('/<int:account_id>')
def update_account(account_id):
    """
    Update Tidal account name and/or credentials.
    Body: { account_name?, client_id?, client_secret? }
    """
    from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
    if PluginRegistry.is_plugin_disabled('tidal'):
        return jsonify({'error': 'Tidal provider is disabled'}), 403
    try:
        
        import zlib
        from core.nexus_framework.plugin_SDK import ProviderStorageBox
        sdk = ProviderStorageBox(plugin_id=zlib.crc32(b'echosync.tidal') & 0xFFFFFFFF)
        accounts = sdk.accounts.get_all()
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        payload = request.get_json(force=True) or {}
        
        # Update account name if provided
        if payload.get('account_name'):
            new_name = payload.get('account_name').strip()
            if new_name:
                sdk.accounts.update_account_name(account_id, new_name)
        
        # Update credentials if provided (non-empty)
        logger.info(f"UPDATE PAYLOAD for account {account_id}: client_id={'present' if payload.get('client_id') else 'missing'}, client_secret={'present' if payload.get('client_secret') else 'missing'}")
        
        from core.nexus_framework.plugin_loader import get_plugin
        plugin = get_plugin('EchoSync/tidal')
        
        if 'client_id' in payload and payload.get('client_id'):
            client_id_value = payload.get('client_id').strip()
            logger.info(f"Saving client_id globally: {client_id_value}")
            if plugin: plugin.config.set('client_id', client_id_value)
            
        if 'client_secret' in payload and payload.get('client_secret'):
            client_secret_value = payload.get('client_secret').strip()
            logger.info(f"Saving client_secret globally, length: {len(client_secret_value)}")
            if plugin: plugin.secrets.set('client_secret', client_secret_value)
        
        # Return updated account
        import zlib
        from core.nexus_framework.plugin_SDK import ProviderStorageBox
        sdk = ProviderStorageBox(plugin_id=zlib.crc32(b'echosync.tidal') & 0xFFFFFFFF)
        accounts = sdk.accounts.get_all()
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        return jsonify({
            'account': {
                'id': account.get('id'),
                'account_name': account.get('account_name') or account.get('display_name') or 'Unnamed',
                'display_name': account.get('display_name') or account.get('account_name') or 'Unnamed',
                'user_id': account.get('user_id'),
                'is_active': account.get('is_active'),
                'is_authenticated': account.get('is_authenticated'),
                'client_id': plugin.config.get('client_id') if plugin else None,
                'client_secret_configured': bool(plugin.secrets.get('client_secret')) if plugin else False
            }
        })
    except Exception as e:
        logger.error(f"Error updating Tidal account: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.put('/<int:account_id>/activate')
def activate_account(account_id):
    """Activate a Tidal account."""
    from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
    if PluginRegistry.is_plugin_disabled('tidal'):
        return jsonify({'error': 'Tidal provider is disabled'}), 403
    try:
        
        import zlib
        from core.nexus_framework.plugin_SDK import ProviderStorageBox
        sdk = ProviderStorageBox(plugin_id=zlib.crc32(b'echosync.tidal') & 0xFFFFFFFF)
        accounts = sdk.accounts.get_all()
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        payload = request.get_json(force=True) or {}
        is_active = payload.get('is_active', True)
        
        if is_active:
            sdk.accounts.toggle_account_active(account_id, True)
        else:
            sdk.accounts.toggle_account_active(account_id, False)
        
        return jsonify({'status': 'ok', 'is_active': is_active})
    except Exception as e:
        logger.error(f"Error activating Tidal account: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.delete('/<int:account_id>')
def delete_account(account_id):
    """Delete a Tidal account."""
    from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
    if PluginRegistry.is_plugin_disabled('tidal'):
        return jsonify({'error': 'Tidal provider is disabled'}), 403
    try:
        
        import zlib
        from core.nexus_framework.plugin_SDK import ProviderStorageBox
        sdk = ProviderStorageBox(plugin_id=zlib.crc32(b'echosync.tidal') & 0xFFFFFFFF)
        deleted = sdk.accounts.delete_account(account_id)
        
        if not deleted:
            return jsonify({'error': 'Account not found'}), 404
        
        # Clean up per-account credentials (not applicable anymore)
        pass
        
        logger.info(f"Deleted Tidal account {account_id}")
        return jsonify({'status': 'ok', 'message': 'Account deleted'})
    except Exception as e:
        logger.error(f"Error deleting Tidal account: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.post('/redirect-uri')
def set_redirect_uri():
    """
    Set global redirect URI for all Tidal accounts.
    Body: { redirect_uri }
    """
    try:
        payload = request.get_json(force=True) or {}
        redirect_uri = payload.get('redirect_uri', '').strip()
        
        if not redirect_uri:
            return jsonify({'error': 'redirect_uri is required'}), 400
        
        from core.nexus_framework.plugin_loader import get_plugin
        plugin = get_plugin('EchoSync/tidal')
        if not plugin:
            return jsonify({'error': 'Plugin not found'}), 404
            
        plugin.config.set('redirect_uri', redirect_uri)
        
        return jsonify({'status': 'ok', 'redirect_uri': redirect_uri})
    except Exception as e:
        logger.error(f"Error setting redirect URI: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


@bp.get('/<int:account_id>/debug')
def debug_account(account_id):
    """
    Debug endpoint to inspect what's stored for an account.
    """
    try:
        
        
        # Check if account exists
        import zlib
        from core.nexus_framework.plugin_SDK import ProviderStorageBox
        sdk = ProviderStorageBox(plugin_id=zlib.crc32(b'echosync.tidal') & 0xFFFFFFFF)
        accounts = sdk.accounts.get_all()
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        from core.nexus_framework.plugin_loader import get_plugin
        plugin = get_plugin('EchoSync/tidal')
        
        # Try to load global credentials
        client_id = plugin.config.get('client_id') if plugin else None
        client_secret = plugin.secrets.get('client_secret') if plugin else None
        
        raw_metadata = []
        # In a real compliant plugin, you'd only use storage methods.
        
        return jsonify({
            'account': account,
            'client_id': client_id,
            'client_secret_present': bool(client_secret),
            'client_secret_length': len(client_secret) if client_secret else 0,
            'raw_metadata_entries': len(raw_metadata),
            'raw_keys': [row[0] for row in raw_metadata]
        })
    except Exception as e:
        logger.error(f"Error debugging account: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500


# ---------------------------------------------------------------------------
# OAuth / Auth — consumed by TidalCard.svelte authenticate()
# ---------------------------------------------------------------------------

@bp.get('/auth')
def begin_auth():
    """Initiate Tidal OAuth device-code flow for the given account_id.
    Query params: account_id (required)
    Returns: { auth_url } to open in a new tab, or { device_code_url } for device flow.
    """
    from core.nexus_framework.plugin_loader import PluginRegistry
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            return jsonify({'error': 'account_id parameter is required'}), 400

        from core.nexus_framework.plugin_loader import get_plugin
        plugin = get_plugin('EchoSync/tidal')
        if not plugin:
            return jsonify({'error': 'Tidal plugin not loaded'}), 503

        client_id = plugin.config.get('client_id')
        if not client_id:
            return jsonify({'error': 'Tidal client_id not configured'}), 400

        # Build the TIDAL device-auth URL — browser opens this for user login
        # The plugin's own callback/polling handles the rest
        from core.network_utils import get_lan_ip
        redirect_uri = f"https://{get_lan_ip()}:5001/api/oauth/callback/plugins/tidal"
        auth_url = f"https://login.tidal.com/oauth2/authorization?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope=r_usr+w_usr"

        # Delegate to plugin client if it exposes a richer auth-start helper
        try:
            from .client import TidalClient
            tc = TidalClient(account_id=int(account_id))
            if hasattr(tc, 'get_auth_url'):
                auth_url = tc.get_auth_url()
        except Exception:
            pass  # fall back to the URL we built above

        logger.info(f"Generated Tidal auth URL for account {account_id}")
        return jsonify({'auth_url': auth_url}), 200
    except Exception as e:
        logger.error(f"Error generating Tidal auth URL: {e}", exc_info=True)
        return jsonify({"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}), 500
