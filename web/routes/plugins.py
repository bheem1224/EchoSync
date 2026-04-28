from web.auth import require_auth
import json
from flask import Blueprint, jsonify, request, abort, send_from_directory
from core.settings import config_manager
from werkzeug.utils import safe_join
import os
from core.plugin_loader import get_all_plugins
from core.plugin_store import plugin_store

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
        return jsonify({"error": str(e)}), 500

@bp.route('/install', methods=['POST'])
@require_auth
def install_plugin():
    data = request.json or {}
    plugin_info = data.get('plugin')
    channel = data.get('channel', 'stable')
    
    if not plugin_info:
        return jsonify({"error": "Plugin info required"}), 400

    success = plugin_store.download_plugin(plugin_info, channel=channel)
    if success:
        from core.state import system_state
        system_state.restart_pending = True
        return jsonify({"success": True})
    else:
        return jsonify({"error": f"Failed to install plugin on channel {channel}"}), 500


@bp.route('/<plugin_id>/ui/<path:filename>', methods=['GET'])
@require_auth
def serve_plugin_ui(plugin_id, filename):
    plugins_dir = str(config_manager.get_plugins_dir())
    ui_dir = safe_join(plugins_dir, plugin_id, 'ui')

    if ui_dir is None or not os.path.exists(ui_dir):
        abort(404)

    return send_from_directory(ui_dir, filename)

@bp.route('/<plugin_id>/static/<path:filename>', methods=['GET'])
@require_auth
def serve_plugin_static(plugin_id, filename):
    plugins_dir = str(config_manager.get_plugins_dir())
    static_dir = safe_join(plugins_dir, plugin_id, 'static')

    if static_dir is None or not os.path.exists(static_dir):
        abort(404)

    return send_from_directory(static_dir, filename)
