"""Tidal provider routes."""
from flask import Blueprint, request, jsonify
from core.settings import config_manager
from core.account_manager import AccountManager
from core.tiered_logger import get_logger

logger = get_logger("tidal_routes")
bp = Blueprint("tidal_routes", __name__, url_prefix="/api/accounts/tidal")


@bp.get('')
def list_accounts():
    """List all Tidal accounts."""
    # short‑circuit if provider disabled
    from core.provider import ProviderRegistry
    if ProviderRegistry.is_provider_disabled('tidal'):
        # return empty result rather than error
        return jsonify({'accounts': [], 'redirect_uri': ''}), 200

    try:
        db_accounts = AccountManager.list_accounts('tidal')
        accounts = []
        
        for a in db_accounts:
            normalized = {
                'id': a.get('id'),
                'account_name': a.get('account_name') or a.get('name') or 'Unnamed',
                'display_name': a.get('display_name') or a.get('name') or 'Unnamed',
                'user_id': a.get('user_id'),
                'is_active': a.get('is_active', True),
                'is_authenticated': a.get('is_authenticated', False),
                'client_id': a.get('client_id'),
                'client_secret_configured': bool(a.get('client_secret'))
            }
            accounts.append(normalized)
        
        # Get global redirect URI
        redirect_uri = AccountManager.get_service_config('tidal', 'redirect_uri') or 'http://127.0.0.1:8000/api/tidal/callback'
        
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
        
        # Create account via ConfigManager helper
        new_account = {
            'name': account_name,
            'client_id': client_id,
            'client_secret': client_secret,
            'is_active': False,
            'is_authenticated': False
        }
        
        created = config_manager.add_tidal_account(new_account)
        
        logger.info(f"Created Tidal account {created.get('id')} with credentials")
        
        return jsonify({
            'account': {
                'id': created.get('id'),
                'account_name': created.get('name'),
                'display_name': created.get('name'),
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
        account = AccountManager.get_account('tidal', account_id)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        return jsonify({
            'account': {
                'id': account.get('id'),
                'account_name': account.get('name') or 'Unnamed',
                'display_name': account.get('name') or 'Unnamed',
                'user_id': account.get('user_id'),
                'is_active': account.get('is_active', True),
                'is_authenticated': account.get('is_authenticated', False),
                'client_id': account.get('client_id'),
                'client_secret': account.get('client_secret')  # Only returned on explicit GET
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
        account = AccountManager.get_account('tidal', account_id)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        payload = request.get_json(force=True) or {}
        updates = {}
        
        # Update account name if provided
        if payload.get('account_name'):
            updates['name'] = payload.get('account_name').strip()
        
        if 'client_id' in payload and payload.get('client_id'):
            updates['client_id'] = payload.get('client_id').strip()
            
        if 'client_secret' in payload and payload.get('client_secret'):
            updates['client_secret'] = payload.get('client_secret').strip()

        if updates:
            AccountManager.update_account('tidal', account_id, updates)
        
        # Return updated account
        updated_account = AccountManager.get_account('tidal', account_id)
        
        return jsonify({
            'account': {
                'id': updated_account.get('id'),
                'account_name': updated_account.get('name'),
                'display_name': updated_account.get('name'),
                'user_id': updated_account.get('user_id'),
                'is_active': updated_account.get('is_active', True),
                'is_authenticated': updated_account.get('is_authenticated', False),
                'client_id': updated_account.get('client_id'),
                'client_secret_configured': bool(updated_account.get('client_secret'))
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
        account = AccountManager.get_account('tidal', account_id)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        payload = request.get_json(force=True) or {}
        is_active = payload.get('is_active', True)
        
        AccountManager.update_account('tidal', account_id, {'is_active': is_active})
        
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
        # Currently ConfigManager doesn't support deleting accounts from list directly via simple API
        # We need to implement removal logic
        accounts = config_manager.get_tidal_accounts()
        new_accounts = [a for a in accounts if a.get('id') != account_id]
        
        if len(accounts) == len(new_accounts):
            return jsonify({'error': 'Account not found'}), 404

        config_manager.set('tidal_accounts', new_accounts)
        
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
        
        # Update global tidal config
        tidal_config = config_manager.get('tidal', {})
        tidal_config['redirect_uri'] = redirect_uri
        config_manager.set('tidal', tidal_config)
        
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
        account = AccountManager.get_account('tidal', account_id)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        client_id = account.get('client_id')
        client_secret = account.get('client_secret')
        
        return jsonify({
            'account': account,
            'client_id': client_id,
            'client_secret_present': bool(client_secret),
            'client_secret_length': len(client_secret) if client_secret else 0
        })
    except Exception as e:
        logger.error(f"Error debugging account: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
