from flask import Blueprint, jsonify, request
from core.file_handling.storage import get_storage_service
from core.tiered_logger import get_logger

logger = get_logger("accounts_route")
bp = Blueprint("accounts", __name__, url_prefix="/api/accounts")


@bp.post("/plex/sync_users")
def sync_plex_users():
    """Sync Plex admin and managed users into config.db and return the updated list."""
    try:
        from providers.plex.client import PlexClient

        client = PlexClient()
        client.import_managed_users()

        storage = get_storage_service()
        accounts = storage.list_accounts('plex')
        return jsonify({
            'service': 'plex',
            'accounts': accounts,
            'total': len(accounts),
            'success': True,
        }), 200
    except Exception as e:
        logger.error(f"Error syncing Plex users: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.get("/<service_name>")
def list_service_accounts(service_name):
    """List all accounts for a specific service."""
    try:
        storage = get_storage_service()
        accounts = storage.list_accounts(service_name)
        return jsonify({
            'service': service_name,
            'accounts': accounts,
            'total': len(accounts)
        }), 200
    except Exception as e:
        logger.error(f"Error listing accounts for {service_name}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.post("/<service_name>")
def create_account(service_name):
    """Create a new account for a service."""
    try:
        payload = request.get_json(silent=True) or {}
        account_name = payload.get('account_name')
        display_name = payload.get('display_name', account_name)
        
        if not account_name:
            return jsonify({'error': 'account_name is required'}), 400
        
        storage = get_storage_service()
        account_id = storage.ensure_account(
            service_name=service_name,
            account_name=account_name,
            display_name=display_name
        )
        
        if account_id:
            return jsonify({
                'success': True,
                'account_id': account_id,
                'account_name': account_name
            }), 201
        else:
            return jsonify({'error': 'Failed to create account'}), 500
    except Exception as e:
        logger.error(f"Error creating account for {service_name}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.put("/<service_name>/<int:account_id>/activate")
def activate_account(service_name, account_id):
    """Activate an account (toggle active status for multi-account support)."""
    try:
        payload = request.get_json(silent=True) or {}
        is_active = payload.get('is_active', True)
        
        storage = get_storage_service()
        success = storage.toggle_account_active(account_id, is_active)
        
        if success:
            return jsonify({'success': True, 'is_active': is_active}), 200
        else:
            return jsonify({'error': 'Failed to update account status'}), 500
    except Exception as e:
        logger.error(f"Error updating account {account_id} status for {service_name}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.delete("/<service_name>/<int:account_id>")
def delete_account(service_name, account_id):
    """Delete an account."""
    try:
        storage = get_storage_service()
        success = storage.delete_account(account_id)
        
        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Failed to delete account'}), 500
    except Exception as e:
        logger.error(f"Error deleting account {account_id} for {service_name}: {e}")
        return jsonify({'error': str(e)}), 500

@bp.put("/<service_name>/<int:account_id>/name")
def update_account_name(service_name, account_id):
    """Update account display name."""
    try:
        payload = request.get_json(silent=True) or {}
        new_name = payload.get('name')
        
        if not new_name:
            return jsonify({'error': 'name is required'}), 400
        
        storage = get_storage_service()
        success = storage.update_account_name(account_id, new_name)
        
        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Failed to update account name'}), 500
    except Exception as e:
        logger.error(f"Error updating account name for {account_id}: {e}")
        return jsonify({'error': str(e)}), 500
