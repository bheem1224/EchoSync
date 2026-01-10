from flask import Blueprint, jsonify
from core.provider_registry import ProviderRegistry
from utils.logging_config import get_logger

logger = get_logger("plugins_route")
bp = Blueprint("plugins", __name__, url_prefix="/api/plugins")

@bp.get("/")
def list_plugins():
    """List all registered providers/plugins."""
    try:
        providers = ProviderRegistry.list_providers()
        provider_info = []
        for name in providers:
            cls = ProviderRegistry.get_provider_class(name)
            if cls:
                provider_info.append({
                    'name': name,
                    'category': getattr(cls, 'category', 'provider'),
                    'disabled': ProviderRegistry.is_provider_disabled(name)
                })
        return jsonify({
            'providers': provider_info,
            'total': len(provider_info)
        })
    except Exception as e:
        logger.error(f"Error listing providers: {e}")
        return jsonify({'error': 'Failed to list providers'}), 500

@bp.get("/by-type/<provider_type>")
def get_plugins_by_type(provider_type: str):
    """Get providers filtered by type (e.g., downloader, mediaserver, syncservice)."""
    try:
        providers = ProviderRegistry.get_providers_by_type(provider_type)
        provider_info = []
        for name in providers:
            cls = ProviderRegistry.get_provider_class(name)
            if cls:
                provider_info.append({
                    'name': name,
                    'category': getattr(cls, 'category', 'provider'),
                    'disabled': ProviderRegistry.is_provider_disabled(name)
                })
        return jsonify({
            'type': provider_type,
            'providers': provider_info,
            'total': len(provider_info)
        })
    except ValueError as e:
        logger.error(f"Invalid provider type: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting providers by type: {e}")
        return jsonify({'error': 'Failed to get providers'}), 500

@bp.post("/disable/<provider_name>")
def disable_provider(provider_name: str):
    """Disable a provider/plugin."""
    try:
        if ProviderRegistry.disable_provider(provider_name):
            # Also persist to config
            from core.settings import config_manager
            config_manager.disable_provider(provider_name)
            return jsonify({'status': 'success', 'message': f'Provider {provider_name} disabled. Restart required.'}), 200
        else:
            return jsonify({'error': f'Provider {provider_name} not found'}), 404
    except Exception as e:
        logger.error(f"Error disabling provider: {e}")
        return jsonify({'error': 'Failed to disable provider'}), 500

@bp.post("/enable/<provider_name>")
def enable_provider(provider_name: str):
    """Enable a previously disabled provider/plugin."""
    try:
        if ProviderRegistry.enable_provider(provider_name):
            # Also persist to config
            from core.settings import config_manager
            config_manager.enable_provider(provider_name)
            return jsonify({'status': 'success', 'message': f'Provider {provider_name} enabled. Restart required.'}), 200
        else:
            return jsonify({'error': f'Provider {provider_name} not found'}), 404
    except Exception as e:
        logger.error(f"Error enabling provider: {e}")
        return jsonify({'error': 'Failed to enable provider'}), 500

@bp.get("/disabled")
def get_disabled_providers():
    """Get list of disabled providers."""
    try:
        disabled = ProviderRegistry.get_disabled_providers()
        return jsonify({'disabled_providers': disabled, 'total': len(disabled)}), 200
    except Exception as e:
        logger.error(f"Error getting disabled providers: {e}")
        return jsonify({'error': 'Failed to fetch disabled providers'}), 500