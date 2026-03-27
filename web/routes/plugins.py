from flask import Blueprint, jsonify
import json

from core.provider import ProviderRegistry
from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("plugins_route")
bp = Blueprint("plugins", __name__, url_prefix="/api/plugins")

@bp.get("/")
def list_plugins():
    """List installed community plugins and plugin-category registry entries."""
    try:
        plugin_info = []
        seen_names = set()

        plugins_dir = config_manager.get_plugins_dir()
        if plugins_dir.exists():
            for plugin_dir in sorted(plugins_dir.iterdir(), key=lambda p: p.name.lower()):
                if not plugin_dir.is_dir():
                    continue
                manifest_path = plugin_dir / "manifest.json"
                if not manifest_path.exists():
                    continue
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except Exception:
                    manifest = {}

                plugin_name = manifest.get("name") or plugin_dir.name
                plugin_info.append({
                    'id': plugin_dir.name,
                    'name': plugin_name,
                    'display_name': plugin_name,
                    'category': 'plugin',
                    'version': manifest.get('version'),
                    'disabled': False,
                    'is_configured': True,
                })
                seen_names.add(plugin_dir.name)
                seen_names.add(str(plugin_name).lower())

        providers = ProviderRegistry.list_providers()
        for name in providers:
            cls = ProviderRegistry.get_provider_class(name)
            if not cls:
                continue

            category = getattr(cls, 'category', 'provider')
            if category != 'plugin':
                continue

            if name in seen_names or name.lower() in seen_names:
                continue

            plugin_info.append({
                'id': name,
                'name': name,
                'display_name': name.title(),
                'category': 'plugin',
                'disabled': ProviderRegistry.is_provider_disabled(name),
                'is_configured': True,
            })

        return jsonify({
            'plugins': plugin_info,
            'total': len(plugin_info)
        })
    except Exception as e:
        logger.error(f"Error listing plugins: {e}")
        return jsonify({'error': 'Failed to list plugins'}), 500

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