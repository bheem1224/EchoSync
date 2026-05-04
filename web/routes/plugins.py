from web.auth import require_auth
import json
from flask import Blueprint, jsonify, request, abort, send_from_directory
from core.settings import config_manager
from werkzeug.utils import safe_join
import os
from pathlib import Path
from core.plugin_loader import get_all_plugins
from core.plugin_store import plugin_store
from core.tiered_logger import get_logger

logger = get_logger("plugins_route")
bp = Blueprint('plugins', __name__, url_prefix='/api/system/plugins')

@bp.route('', methods=['GET'])
@require_auth
def list_plugins():
    plugins = get_all_plugins()
    return jsonify({'plugins': plugins})

@bp.route('/ui-manifest', methods=['GET'])
@require_auth
def get_ui_manifest():
    """Return active plugin UI manifests.

    Manifest shape per plugin
    ─────────────────────────
    {
      "id":         "spotify",          // folder_name
      "api_base":   "/api/plugins/spotify",
      "components": {                   // category → { element_tag, bundle_url }
        "music_service": {
          "element_tag": "echosync-spotify-card",
          "bundle_url":  "/api/system/plugins/spotify/ui/bundle.js"
        }
      },
      "assets": {                       // legacy flat asset map (preserved)
        "js": "/api/system/plugins/spotify/ui/bundle.js"
      },
      "views": [                        // plugin-declared dashboard views
        {
          "id":        "spotify_analytics",
          "title":     "Spotify Stats",
          "icon":      "mdi-spotify",
          "yaml_path": "/api/plugins/spotify/static/dashboard.yaml"
        }
      ]
    }
    """
    plugins = get_all_plugins()
    ui_plugins = []

    for plugin in plugins:
        if not plugin.get('enabled', False):
            continue

        ui_manifest = plugin.get('ui_manifest')
        if not ui_manifest:
            continue

        folder_name = plugin.get('folder_name')
        if not folder_name:
            folder_name = plugin.get('id', '').replace('plugin.', '').replace('core.', '')

        # ── Normalize components ──────────────────────────────────────
        # Old shape: { "dashboard_card": "tag-name" }
        # New shape: { "category": { "element_tag": "tag-name", "bundle_url": "..." } }
        raw_components = ui_manifest.get('components', {})
        raw_assets     = ui_manifest.get('assets', {})

        # Derive the canonical bundle URL from assets (fallback: legacy js key)
        def _default_bundle_url(folder):
            return f'/api/system/plugins/{folder}/static/bundle.js'

        bundle_url = (
            raw_assets.get('js')
            or raw_assets.get('bundle.js')
            or raw_assets.get('main')
            or _default_bundle_url(folder_name)
        )

        normalized_components = {}
        for category, value in raw_components.items():
            if isinstance(value, str):
                # Legacy: value is just the element tag name
                normalized_components[category] = {
                    'element_tag': value,
                    'bundle_url':  bundle_url,
                }
            elif isinstance(value, dict):
                # New schema: already a structured object
                normalized_components[category] = {
                    'element_tag': value.get('element_tag', ''),
                    'bundle_url':  value.get('bundle_url', bundle_url),
                }

        # ── Normalize views ───────────────────────────────────────────
        raw_views = ui_manifest.get('views', [])
        normalized_views = []
        for view in raw_views:
            if not isinstance(view, dict):
                continue
            normalized_views.append({
                'id':        view.get('id', ''),
                'title':     view.get('title', ''),
                'icon':      view.get('icon', None),
                'yaml_path': view.get('yaml_path', ''),
            })

        ui_plugins.append({
            'id':         folder_name,
            'api_base':   f'/api/plugins/{folder_name}',
            'components': normalized_components,
            'assets':     raw_assets,
            'views':      normalized_views,
        })

    return jsonify({'plugins': ui_plugins})


@bp.route('/config', methods=['POST'])
@require_auth
def update_plugin_config():
    data = request.json or {}

    disabled_list = data.get('disabled_providers')
    if disabled_list is not None:
        # C2: strict type validation — must be a flat list of strings.
        if not isinstance(disabled_list, list) or not all(
            isinstance(x, str) for x in disabled_list
        ):
            return jsonify(
                {"error": "disabled_providers must be a list of strings"}
            ), 400
        config_manager.set_disabled_providers(disabled_list)

    active_matching_engine = data.get('active_matching_engine')
    if active_matching_engine is not None:
        if not isinstance(active_matching_engine, str):
            return jsonify(
                {"error": "active_matching_engine must be a string"}
            ), 400
        config_manager.set('settings.active_matching_engine', active_matching_engine)

    return jsonify({"success": True})


@bp.route('/repos', methods=['GET'])
@require_auth
def get_repos():
    repos = plugin_store.get_repositories()
    return jsonify({"repos": repos})

@bp.route('/repos', methods=['POST'])
@require_auth
def add_repo():
    data = request.json or {}
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL required"}), 400
    success = plugin_store.add_repository(url)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Failed to add repository"}), 500

@bp.route('/repos', methods=['DELETE'])
@require_auth
def remove_repo():
    data = request.json or {}
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL required"}), 400
    success = plugin_store.remove_repository(url)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Failed to remove repository"}), 500

@bp.route('/store', methods=['GET'])
@require_auth
def get_plugin_store():
    try:
        plugins = plugin_store.get_all_store_plugins()
        return jsonify({'plugins': plugins})
    except Exception as e:
        logger.error(f"Error fetching plugin store: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/install', methods=['POST'])
@require_auth
def install_plugin():
    data = request.json or {}
    plugin_info = data.get('plugin')
    channel = data.get('channel') or (plugin_info.get('channel') if plugin_info else 'stable')
    if channel == 'release': channel = 'stable' # Normalize internal naming
    
    if not plugin_info:
        return jsonify({"error": "Plugin info required"}), 400

    success = plugin_store.download_plugin(plugin_info, channel=channel)
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"error": f"Failed to install plugin on channel {channel}"}), 500



@bp.route('/<plugin_id>/toggle', methods=['POST'])
@require_auth
def toggle_plugin(plugin_id):
    """
    Safely toggle a plugin's enabled status by updating the disabled_providers list.
    """
    data = request.json or {}
    enabled = data.get('enabled')

    if enabled is None:
        return jsonify({"error": "Missing 'enabled' boolean in payload"}), 400

    from core.settings import config_manager

    # plugin_id usually comes in as "plugin.name" or just "name"
    # To be safe, we strip prefixes to get the raw name, then we can disable both forms if needed,
    # but the settings manager usually stores the exact ID passed. Let's use the exact ID.
    if enabled:
        config_manager.enable_provider(plugin_id)
    else:
        config_manager.disable_provider(plugin_id)

    config_manager.save_settings(config_manager.get_settings())

    # Hot-Reload if enabled, otherwise restart pending
    try:
        from core.plugin_loader import PluginLoader
        app_root = Path(__file__).parent.parent.parent
        loader = PluginLoader(app_root)
        loader.reload_plugin(plugin_id)
        logger.info(f"Hot-reloaded plugin {plugin_id} after toggle")
    except Exception as e:
        logger.warning(f"Hot-reload failed for {plugin_id}, marking restart pending: {e}")
        from core.state import system_state
        system_state.restart_pending = True

    return jsonify({"success": True})

@bp.route('/<plugin_id>/ui/<path:filename>', methods=['GET'])
@require_auth
def serve_plugin_ui(plugin_id, filename):
    # Strip prefixes if present
    clean_id = plugin_id.replace('core.', '').replace('plugin.', '')
    plugins_dir = config_manager.get_plugins_dir()
    app_root = Path(__file__).parent.parent.parent
    
    logger.debug(f"[UISearch] Request for {plugin_id}/{filename} (Cleaned ID: {clean_id})")
    
    # Possible base directories for plugins
    base_dirs = [
        str(plugins_dir),
        str(app_root / "plugins"),
    ]

    ui_dir = None
    for base in base_dirs:
        # Check standard folder
        path = os.path.abspath(os.path.join(base, clean_id, 'ui'))
        if os.path.exists(path):
            ui_dir = path
            break
        
        # Check beta folder
        path = os.path.abspath(os.path.join(base, clean_id, 'beta', 'ui'))
        if os.path.exists(path):
            ui_dir = path
            break

    if not ui_dir:
        logger.error(f"Plugin UI folder NOT FOUND for {plugin_id}. Searched in: {base_dirs}")
        abort(404)

    # Security check
    file_path = os.path.abspath(os.path.join(ui_dir, filename))
    if not file_path.startswith(ui_dir):
        logger.warning(f"Security: Blocked UI traversal attempt for {plugin_id}: {filename}")
        abort(403)

    if not os.path.exists(file_path):
        logger.error(f"Plugin UI file NOT FOUND: {file_path}")
        abort(404)

    return send_from_directory(ui_dir, filename)

@bp.route('/<plugin_id>/static/<path:filename>', methods=['GET'])
@require_auth
def serve_plugin_static(plugin_id, filename):
    """
    Serve static assets (JS bundles, CSS, etc.) for a plugin.
    Checks community plugins, beta channel, and core plugins.
    """
    # Strip prefixes if present
    clean_id = plugin_id.replace('core.', '').replace('plugin.', '')
    plugins_dir = config_manager.get_plugins_dir()
    app_root = Path(__file__).parent.parent.parent
    
    logger.debug(f"[AssetSearch] Request for {plugin_id}/{filename} (Cleaned ID: {clean_id})")
    
    # Possible base directories for plugins
    base_dirs = [
        str(plugins_dir),
        str(app_root / "plugins"),
        str(app_root / "providers"),
    ]

    static_dir = None
    for base in base_dirs:
        # Check standard static folder
        path = os.path.abspath(os.path.join(base, clean_id, 'static'))
        if os.path.exists(path):
            static_dir = path
            break
        
        # Check beta folder static folder
        path = os.path.abspath(os.path.join(base, clean_id, 'beta', 'static'))
        if os.path.exists(path):
            static_dir = path
            break

    if not static_dir:
        logger.error(f"Plugin asset folder NOT FOUND for {plugin_id}. Searched in: {base_dirs}")
        abort(404)

    # Security check: Ensure we are not serving files outside the plugin static folder
    # filename is already sanitized by Flask/Werkzeug to some extent
    file_path = os.path.abspath(os.path.join(static_dir, filename))
    if not file_path.startswith(static_dir):
        logger.warning(f"Security: Blocked traversal attempt for {plugin_id}: {filename}")
        abort(403)

    if not os.path.exists(file_path):
        logger.error(f"Plugin asset file NOT FOUND: {file_path}")
        abort(404)

    logger.info(f"Serving plugin asset: {file_path}")
    return send_from_directory(static_dir, filename)
