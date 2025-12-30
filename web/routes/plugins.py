from flask import Blueprint, jsonify
from plugins.plugin_system import plugin_registry, PluginType, PluginScope
from utils.logging_config import get_logger

logger = get_logger("plugins_route")
bp = Blueprint("plugins", __name__, url_prefix="/api/plugins")

@bp.get("/")
def list_plugins():
    """List all registered plugins with their declarations."""
    try:
        return jsonify({
            'plugins': plugin_registry.list_all_dict(),
            'total': len(plugin_registry.list_all())
        })
    except Exception as e:
        logger.error(f"Error listing plugins: {e}")
        return jsonify({'error': 'Failed to list plugins'}), 500

@bp.get("/by-type/<plugin_type>")
def get_plugins_by_type(plugin_type: str):
    """Get plugins filtered by type (e.g., playlist_service, library_manager)."""
    try:
        ptype = PluginType(plugin_type)
        plugins = plugin_registry.get_plugins_by_type(ptype)
        return jsonify({
            'type': plugin_type,
            'plugins': [p.to_dict() for p in plugins],
            'total': len(plugins)
        })
    except ValueError:
        return jsonify({'error': f'Unknown plugin type: {plugin_type}'}), 404
    except Exception as e:
        logger.error(f"Error filtering plugins by type: {e}")
        return jsonify({'error': 'Failed to filter plugins'}), 500

@bp.get("/by-scope/<scope>")
def get_plugins_by_scope(scope: str):
    """Get plugins filtered by scope (library, sync, search, download, playback, utility)."""
    try:
        pscope = PluginScope(scope)
        plugins = plugin_registry.get_plugins_by_scope(pscope)
        return jsonify({
            'scope': scope,
            'plugins': [p.to_dict() for p in plugins],
            'total': len(plugins)
        })
    except ValueError:
        return jsonify({'error': f'Unknown scope: {scope}'}), 404
    except Exception as e:
        logger.error(f"Error filtering plugins by scope: {e}")
        return jsonify({'error': 'Failed to filter plugins'}), 500

@bp.get("/capability/<capability>")
def get_capability_providers(capability: str):
    """Get plugins that provide a specific capability, sorted by priority."""
    try:
        providers = plugin_registry.get_providers_for_capability(capability)
        return jsonify({
            'capability': capability,
            'providers': [p.to_dict() for p in providers],
            'primary': providers[0].to_dict() if providers else None,
            'total': len(providers)
        })
    except Exception as e:
        logger.error(f"Error getting capability providers: {e}")
        return jsonify({'error': 'Failed to fetch providers'}), 500

@bp.get("/field/<field_name>")
def get_field_providers(field_name: str):
    """Get plugins that can populate a Track field, sorted by priority."""
    try:
        providers = plugin_registry.get_providers_for_field(field_name)
        return jsonify({
            'field': field_name,
            'providers': [p.to_dict() for p in providers],
            'primary': providers[0].to_dict() if providers else None,
            'total': len(providers)
        })
    except Exception as e:
        logger.error(f"Error getting field providers: {e}")
        return jsonify({'error': 'Failed to fetch providers'}), 500