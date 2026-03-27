"""Tidal provider routes."""
from flask import Blueprint, request, jsonify
from core.file_handling.storage import get_storage_service
from core.tiered_logger import get_logger

logger = get_logger("tidal_routes")
bp = Blueprint("tidal_routes", __name__)


@bp.get('')
def list_accounts():
    """List all Tidal accounts."""
    # short‑circuit if provider disabled
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('tidal'):
        # return empty result rather than error
        return jsonify({'accounts': [], 'redirect_uri': ''}), 200

    try:
        storage = get_storage_service()
        storage.ensure_service('tidal', display_name='Tidal', service_type='streaming', description='Tidal music streaming service')
        
        db_accounts = storage.list_accounts('tidal')
        accounts = []
        
        for a in db_accounts:
            # Load per-account credentials
            client_id = storage.get_account_config(a.get('id', 0), 'client_id')
            client_secret_present = bool(storage.get_account_config(a.get('id', 0), 'client_secret'))
            
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
        
        # Get global redirect URI
        redirect_uri = storage.get_service_config('tidal', 'redirect_uri') or 'http://127.0.0.1:8000/api/tidal/callback'
        
        return jsonify({
            'accounts': accounts,
            'redirect_uri': redirect_uri
        })
    except Exception as e:
        logger.error(f"Error getting Tidal accounts: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post('')
def create_account():
    """
    Create a new Tidal account with per-account credentials.
    Body: { account_name, client_id, client_secret }
    """
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('tidal'):
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
        
        storage = get_storage_service()
        storage.ensure_service('tidal', display_name='Tidal', service_type='streaming', description='Tidal music streaming service')
        
        # Create account in encrypted config.db
        account_id = storage.ensure_account('tidal', account_name=account_name, display_name=account_name)
        if not account_id:
            return jsonify({'error': 'Failed to create account'}), 500
        
        # Store per-account credentials
        storage.set_account_config(account_id, 'client_id', client_id, is_sensitive=False)
        storage.set_account_config(account_id, 'client_secret', client_secret, is_sensitive=True)
        
        # Store client_id and client_secret in service_config
        storage.ensure_service('tidal', display_name='Tidal', service_type='streaming', description='Tidal music streaming service')
        storage.set_service_config('tidal', 'client_id', client_id, is_sensitive=False)
        storage.set_service_config('tidal', 'client_secret', client_secret, is_sensitive=True)
        
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
        return jsonify({'error': str(e)}), 500


@bp.get('/<int:account_id>')
def get_account(account_id):
    """Get a specific Tidal account with credentials."""
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('tidal'):
        return jsonify({'error': 'Tidal provider is disabled'}), 403
    try:
        storage = get_storage_service()
        accounts = storage.list_accounts('tidal')
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Load per-account credentials
        client_id = storage.get_account_config(account_id, 'client_id')
        client_secret = storage.get_account_config(account_id, 'client_secret')
        
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
        return jsonify({'error': str(e)}), 500


@bp.put('/<int:account_id>')
def update_account(account_id):
    """
    Update Tidal account name and/or credentials.
    Body: { account_name?, client_id?, client_secret? }
    """
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('tidal'):
        return jsonify({'error': 'Tidal provider is disabled'}), 403
    try:
        storage = get_storage_service()
        accounts = storage.list_accounts('tidal')
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        payload = request.get_json(force=True) or {}
        
        # Update account name if provided
        if payload.get('account_name'):
            new_name = payload.get('account_name').strip()
            if new_name:
                storage.update_account_name(account_id, new_name)
        
        # Update credentials if provided (non-empty)
        logger.info(f"UPDATE PAYLOAD for account {account_id}: client_id={'present' if payload.get('client_id') else 'missing'}, client_secret={'present' if payload.get('client_secret') else 'missing'}, secret_length={len(payload.get('client_secret', ''))}")
        
        if 'client_id' in payload and payload.get('client_id'):
            client_id_value = payload.get('client_id').strip()
            logger.info(f"Saving client_id for account {account_id}: {client_id_value}")
            result = storage.set_account_config(account_id, 'client_id', client_id_value, is_sensitive=False)
            logger.info(f"Save client_id result: {result}")
            
        if 'client_secret' in payload and payload.get('client_secret'):
            client_secret_value = payload.get('client_secret').strip()
            logger.info(f"Saving client_secret for account {account_id}, length: {len(client_secret_value)}")
            result = storage.set_account_config(account_id, 'client_secret', client_secret_value, is_sensitive=True)
            logger.info(f"Save client_secret result: {result}")
            # Verify it was saved
            verify_secret = storage.get_account_config(account_id, 'client_secret')
            logger.info(f"VERIFICATION READ: client_secret length after save: {len(verify_secret) if verify_secret else 0}")
        
        # Return updated account
        accounts = storage.list_accounts('tidal')
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        return jsonify({
            'account': {
                'id': account.get('id'),
                'account_name': account.get('account_name') or account.get('display_name') or 'Unnamed',
                'display_name': account.get('display_name') or account.get('account_name') or 'Unnamed',
                'user_id': account.get('user_id'),
                'is_active': account.get('is_active'),
                'is_authenticated': account.get('is_authenticated'),
                'client_id': storage.get_account_config(account_id, 'client_id'),
                'client_secret_configured': bool(storage.get_account_config(account_id, 'client_secret'))
            }
        })
    except Exception as e:
        logger.error(f"Error updating Tidal account: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.put('/<int:account_id>/activate')
def activate_account(account_id):
    """Activate a Tidal account."""
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('tidal'):
        return jsonify({'error': 'Tidal provider is disabled'}), 403
    try:
        storage = get_storage_service()
        accounts = storage.list_accounts('tidal')
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        payload = request.get_json(force=True) or {}
        is_active = payload.get('is_active', True)
        
        if is_active:
            storage.toggle_account_active(account_id, True)
        else:
            storage.toggle_account_active(account_id, False)
        
        return jsonify({'status': 'ok', 'is_active': is_active})
    except Exception as e:
        logger.error(f"Error activating Tidal account: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.delete('/<int:account_id>')
def delete_account(account_id):
    """Delete a Tidal account."""
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('tidal'):
        return jsonify({'error': 'Tidal provider is disabled'}), 403
    try:
        storage = get_storage_service()
        deleted = storage.delete_account(account_id)
        
        if not deleted:
            return jsonify({'error': 'Account not found'}), 404
        
        # Clean up per-account credentials
        try:
            storage.delete_account_config(account_id, 'client_id')
            storage.delete_account_config(account_id, 'client_secret')
        except Exception:
            pass
        
        logger.info(f"Deleted Tidal account {account_id}")
        return jsonify({'status': 'ok', 'message': 'Account deleted'})
    except Exception as e:
        logger.error(f"Error deleting Tidal account: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


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
        
        storage = get_storage_service()
        storage.ensure_service('tidal', display_name='Tidal', service_type='streaming', description='Tidal music streaming service')
        storage.set_service_config('tidal', 'redirect_uri', redirect_uri, is_sensitive=False)
        
        return jsonify({'status': 'ok', 'redirect_uri': redirect_uri})
    except Exception as e:
        logger.error(f"Error setting redirect URI: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.get('/<int:account_id>/debug')
def debug_account(account_id):
    """
    Debug endpoint to inspect what's stored for an account.
    """
    try:
        storage = get_storage_service()
        
        # Check if account exists
        accounts = storage.list_accounts('tidal')
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Try to load credentials
        client_id = storage.get_account_config(account_id, 'client_id')
        client_secret = storage.get_account_config(account_id, 'client_secret')
        
        # Check if values exist in raw DB
        from database.config_database import get_config_database
        cfg_db = get_config_database()
        with cfg_db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT metadata_key, metadata_value FROM account_metadata WHERE account_id = ?", (account_id,))
            raw_metadata = c.fetchall()
        
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
        return jsonify({'error': str(e)}), 500
