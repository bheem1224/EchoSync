from flask import Blueprint, jsonify, request
from core.file_handling.storage import get_storage_service
from core.tiered_logger import get_logger

logger = get_logger("accounts_route")
bp = Blueprint("accounts", __name__, url_prefix="/api/accounts")

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

from web.auth import require_auth
@bp.post("/overrides")
@require_auth
def set_account_overrides():
    from core.settings import config_manager
    try:
        payload = request.get_json(silent=True) or {}
        managed_user_id = payload.get('managed_user_id')
        service_account_id = payload.get('service_account_id')
        action = payload.get('action') # "unfuse" | "refuse"

        if not managed_user_id or not service_account_id or action not in ("unfuse", "refuse"):
            return jsonify({'error': 'Missing or invalid parameters: managed_user_id, service_account_id, action'}), 400

        active_media_server = config_manager.get_active_media_server()
        if not active_media_server:
            return jsonify({'error': 'No active media server configured'}), 400

        provider_config = config_manager.get(active_media_server, {})
        account_map_override = provider_config.get("account_map_override", {})

        overrides = account_map_override.get(managed_user_id, [])

        if action == "unfuse":
            if service_account_id in overrides:
                overrides.remove(service_account_id)
        elif action == "refuse":
            if service_account_id not in overrides:
                overrides.append(service_account_id)

        account_map_override[managed_user_id] = overrides
        provider_config["account_map_override"] = account_map_override
        config_manager.set(active_media_server, provider_config)
        config_manager.save_settings(config_manager.get_settings())

        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Error setting account override: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
