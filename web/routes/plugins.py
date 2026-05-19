from web.auth import require_auth
import json
from flask import Blueprint, jsonify, request, abort, send_from_directory
from core.settings import config_manager
from werkzeug.utils import safe_join
import os
from pathlib import Path
from core.nexus_framework.plugin_loader import get_all_plugins
from core.nexus_framework.plugin_store import plugin_store
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

        # Fix Bug 1: Ensure we use the correct folder_name (Nexus schema aware)
        folder_name = plugin.get('folder_name') or plugin.get('id', '').replace('plugin.', '').replace('core.', '')

        # Physical verification: only include plugins where UI assets actually exist on disk
        abs_path = plugin.get('abs_path')
        if abs_path:
            bundle_file = Path(abs_path) / 'static' / 'bundle.js'
            if not bundle_file.exists():
                logger.warning(f"Plugin {plugin.get('id')} advertised UI but static/bundle.js is missing at {bundle_file}. Skipping.")
                continue

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
                # Ensure we override broken/generic bundle_urls with our verified one if needed
                m_bundle = value.get('bundle_url')
                if m_bundle and '/static/bundle.js' in m_bundle and '/' not in m_bundle.replace('/api/system/plugins/', '').split('/static/')[0]:
                     m_bundle = bundle_url

                normalized_components[category] = {
                    'element_tag': value.get('element_tag', ''),
                    'bundle_url':  m_bundle or bundle_url,
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

        # Nexus Framework: api_base MUST use slashes for URI routing
        uri_path = folder_name.replace('.', '/')
        ui_plugins.append({
            'id':         folder_name,
            'plugin_id':  plugin.get('id'),
            'api_base':   f'/api/plugins/{uri_path}',
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
    from core.nexus_framework.plugin_store import PrivilegeEscalationError
    data = request.json or {}
    plugin_info = data.get('plugin')
    channel = data.get('channel') or (plugin_info.get('channel') if plugin_info else 'stable')
    if channel == 'release': channel = 'stable'
    force_consent = request.args.get('force_consent') == 'true'
    
    if not plugin_info:
        return jsonify({"error": "Plugin info required"}), 400

    try:
        success = plugin_store.install_plugin(plugin_info, channel=channel, force_consent=force_consent)
        if success:
            return jsonify({"success": True})
        return jsonify({"error": f"Failed to install plugin on channel {channel}"}), 500
    except PrivilegeEscalationError as e:
        return jsonify({"requires_consent": True, "escalations": e.escalations, "message": "This update requires elevated permissions."}), 403
    except Exception as e:
        logger.error(f"Install error: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route('/update', methods=['POST'])
@require_auth
def update_plugin():
    from core.nexus_framework.plugin_store import PrivilegeEscalationError
    data = request.json or {}
    plugin_info = data.get('plugin')
    force_consent = request.args.get('force_consent') == 'true'
    
    if not plugin_info:
        return jsonify({"error": "Plugin info required"}), 400

    try:
        from database.config_database import get_config_database
        db = get_config_database()
        plugin_name = plugin_info.get("id") or plugin_info.get("name")
        
        # 1. Resolve to CRC32 integer plugin_id using get_service_id
        plugin_id_int = db.get_service_id(plugin_name)
        if not plugin_id_int:
            try:
                plugin_id_int = int(plugin_info.get("plugin_id") or plugin_info.get("id"))
            except (ValueError, TypeError):
                pass
                
        # 2. Retrieve the plugin_id column from the database
        db_plugin_id = None
        if plugin_id_int is not None:
            with db._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT plugin_id FROM services WHERE id=? OR plugin_id=?", (plugin_id_int, plugin_id_int))
                row = c.fetchone()
                if row:
                    db_plugin_id = row['plugin_id']
                    
        if not db_plugin_id:
            return jsonify({"error": f"Plugin {plugin_name} not found in database registry."}), 404

        success = plugin_store.update_plugin(db_plugin_id, force_consent=force_consent)
        if success:
            return jsonify({"success": True})
        return jsonify({"error": f"Failed to update plugin {plugin_name}"}), 500
    except PrivilegeEscalationError as e:
        return jsonify({"requires_consent": True, "escalations": e.escalations, "message": "This update requires elevated permissions."}), 403
    except Exception as e:
        logger.error(f"Update error: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route('/rollback', methods=['POST'])
@require_auth
def rollback_plugin():
    data = request.json or {}
    plugin_info = data.get('plugin')
    
    if not plugin_info:
        return jsonify({"error": "Plugin info required"}), 400

    try:
        from database.config_database import get_config_database
        db = get_config_database()
        plugin_name = plugin_info.get("id") or plugin_info.get("name")
        
        # 1. Resolve to CRC32 integer plugin_id using get_service_id
        plugin_id_int = db.get_service_id(plugin_name)
        if not plugin_id_int:
            try:
                plugin_id_int = int(plugin_info.get("plugin_id") or plugin_info.get("id"))
            except (ValueError, TypeError):
                pass
                
        # 2. Retrieve the plugin_id column from the database
        db_plugin_id = None
        if plugin_id_int is not None:
            with db._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT plugin_id FROM services WHERE id=? OR plugin_id=?", (plugin_id_int, plugin_id_int))
                row = c.fetchone()
                if row:
                    db_plugin_id = row['plugin_id']
                    
        if not db_plugin_id:
            return jsonify({"error": f"Plugin {plugin_name} not found in database registry."}), 404

        success = plugin_store.rollback_plugin(db_plugin_id)
        if success:
            return jsonify({"success": True})
        return jsonify({"error": "Failed to rollback plugin"}), 500
    except Exception as e:
        logger.error(f"Rollback error: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route('/<plugin_id>/rollback', methods=['POST'])
@require_auth
def rollback_plugin_direct(plugin_id):
    try:
        from database.config_database import get_config_database
        db = get_config_database()
        
        # Resolve to CRC32 integer plugin_id using get_service_id
        plugin_id_int = db.get_service_id(plugin_id)
        if not plugin_id_int:
            try:
                plugin_id_int = int(plugin_id)
            except (ValueError, TypeError):
                pass
                
        db_plugin_id = None
        if plugin_id_int is not None:
            with db._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT plugin_id FROM services WHERE id=? OR plugin_id=?", (plugin_id_int, plugin_id_int))
                row = c.fetchone()
                if row:
                    db_plugin_id = row['plugin_id']
                    
        if not db_plugin_id:
            return jsonify({"error": f"Plugin {plugin_id} not found"}), 404
            
        success = plugin_store.rollback_plugin(db_plugin_id)
        if success:
            return jsonify({"success": True})
        return jsonify({"error": "Failed to rollback plugin"}), 500
    except Exception as e:
        logger.error(f"Rollback error for {plugin_id}: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route('/<plugin_id>/beta-opt', methods=['POST'])
@require_auth
def set_plugin_beta_opt(plugin_id):
    data = request.json or {}
    val = data.get('beta_opt_in')
    
    db_val = None
    if val is not None:
        db_val = 1 if bool(val) else 0
        
    try:
        from database.config_database import get_config_database
        db = get_config_database()
        
        # Resolve to CRC32 integer plugin_id using get_service_id
        plugin_id_int = db.get_service_id(plugin_id)
        if not plugin_id_int:
            try:
                plugin_id_int = int(plugin_id)
            except (ValueError, TypeError):
                pass
                
        db_plugin_id = None
        if plugin_id_int is not None:
            with db._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT plugin_id FROM services WHERE id=? OR plugin_id=?", (plugin_id_int, plugin_id_int))
                row = c.fetchone()
                if row:
                    db_plugin_id = row['plugin_id']
                    
        if not db_plugin_id:
            return jsonify({"error": f"Plugin {plugin_id} not found"}), 404
            
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE services SET beta_opt_in=? WHERE plugin_id=?", (db_val, db_plugin_id))
            conn.commit()
            
        try:
            from core.nexus_framework.plugin_loader import PluginLoader
            app_root = Path(__file__).parent.parent.parent
            loader = PluginLoader(app_root)
            loader.reload_plugin(db_plugin_id)
            logger.info(f"Hot-reloaded plugin {db_plugin_id} after beta-opt change")
        except Exception as re:
            logger.warning(f"Failed to hot-reload plugin {db_plugin_id} after beta-opt change: {re}")
            
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error setting beta opt for {plugin_id}: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route('/uninstall', methods=['POST'])
@require_auth
def uninstall_plugin_route():
    import binascii
    data = request.json or {}
    plugin_id_raw = data.get('id')
    plugin_name = data.get('name')
    author = data.get('author')

    if not plugin_id_raw and not (plugin_name and author):
        return jsonify({"error": "Plugin ID required"}), 400

    if isinstance(plugin_id_raw, int):
        plugin_id = plugin_id_raw
    elif author and plugin_name:
        plugin_id = binascii.crc32(f"{author}.{plugin_name}".lower().encode('utf-8')) & 0xFFFFFFFF
    else:
        plugin_id = binascii.crc32(str(plugin_id_raw).lower().encode('utf-8')) & 0xFFFFFFFF


    try:
        success = plugin_store.uninstall_plugin(plugin_id)
        if success:
            return jsonify({"success": True})
        return jsonify({"error": "Failed to uninstall plugin"}), 500
    except Exception as e:
        logger.error(f"Uninstall error: {e}")
        return jsonify({"error": str(e)}), 500


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

    # Hot-Reload if enabled
    try:
        from core.nexus_framework.plugin_loader import PluginLoader
        from database.config_database import get_config_database
        db = get_config_database()
        
        # Resolve to integer ID
        int_id = db.get_service_id(plugin_id)
        if int_id:
            app_root = Path(__file__).parent.parent.parent
            loader = PluginLoader(app_root)
            loader.reload_plugin(int_id)
            logger.info(f"Hot-reloaded plugin {plugin_id} (int: {int_id}) after toggle")
        else:
            logger.warning(f"Could not resolve {plugin_id} to an integer ID for hot-reload")
    except Exception as e:
        logger.warning(f"Hot-reload failed for {plugin_id}, marking restart pending: {e}")
        from core.state import system_state
        system_state.restart_pending = True

    return jsonify({"success": True})

@bp.route('/<plugin_id>/ui/<path:filename>', methods=['GET'])
@require_auth
def serve_plugin_ui(plugin_id, filename):
    # Strip prefixes if present
    clean_id = plugin_id.replace('core.', '').replace('plugin.', '').replace('.', '/')
    plugins_dir = config_manager.get_plugins_dir()
    app_root = Path(__file__).parent.parent.parent
    
    logger.debug(f"[UISearch] Request for {plugin_id}/{filename} (Cleaned ID: {clean_id})")
    
    # Canonical base directory for plugins
    base_dirs = [str(plugins_dir)]

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
    clean_id = plugin_id.replace('core.', '').replace('plugin.', '').replace('.', '/')
    plugins_dir = config_manager.get_plugins_dir()
    app_root = Path(__file__).parent.parent.parent
    
    logger.debug(f"[AssetSearch] Request for {plugin_id}/{filename} (Cleaned ID: {clean_id})")
    
    # Canonical base directory for plugins
    base_dirs = [str(plugins_dir)]

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
