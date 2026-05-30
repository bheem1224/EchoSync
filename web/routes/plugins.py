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
from contextlib import contextmanager
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from database.models import Service

logger = get_logger("plugins_route")
bp = Blueprint('plugins', __name__, url_prefix='/api/system/plugins')


@contextmanager
def config_db_connection():
    from database.config_database import get_config_database
    db = get_config_database()
    conn = db._get_connection()
    try:
        yield conn
    finally:
        conn.close()


def resolve_case_insensitive_path(path: Path) -> Path:
    if path.exists():
        return path
    parts = path.parts
    if not parts:
        return path
    current = Path(parts[0])
    for part in parts[1:]:
        if (current / part).exists():
            current = current / part
        else:
            found = False
            if current.is_dir():
                try:
                    for child in current.iterdir():
                        if child.name.lower() == part.lower():
                            current = child
                            found = True
                            break
                except Exception:
                    pass
            if not found:
                current = current / part
    return current

@bp.route('', methods=['GET'])
@require_auth
def list_plugins():
    plugins = get_all_plugins()
    return jsonify({'plugins': plugins})

@bp.route('/ui-manifest', methods=['GET'])
@require_auth
def get_ui_manifest():
    """Return active plugin UI manifests.

    .. deprecated::
        Use ``GET /api/ui/registry`` instead.  This endpoint now reads from the
        central ``ui_components`` table and emits an ``X-Deprecated`` header.

    Manifest shape per plugin (backward-compatible)
    ─────────────────────────────────────────────────
    {
      "id":         "spotify",
      "api_base":   "/api/plugins/spotify",
      "components": { "category": { "element_tag", "bundle_url" } },
      "assets":     {},
      "views":      []
    }
    """
    from web.routes.ui_registry import _query_ui_registry
    from flask import make_response

    registry = _query_ui_registry()

    # Reshape DB-backed registry into the legacy per-plugin format the old
    # frontend expects: list of plugin objects with components/views.
    plugin_map: dict = {}  # plugin_id -> assembled dict

    for type_key, components in registry.items():
        # Reverse the pluralisation (cards → card)
        category = type_key.rstrip("s") if type_key.endswith("s") and type_key != "settings" else type_key

        for comp in components:
            pid = comp.get("plugin_id")
            if pid is None:
                continue

            pname = comp.get("plugin_name") or str(pid)

            if pid not in plugin_map:
                plugin_map[pid] = {
                    "id": pname,
                    "plugin_id": pid,
                    "api_base": f"/api/plugins/{pname}",
                    "components": {},
                    "assets": {},
                    "views": [],
                }

            entry = plugin_map[pid]

            if category == "view":
                entry["views"].append({
                    "id": comp["tag_name"].replace("es-view-", ""),
                    "title": comp["tag_name"],
                    "icon": None,
                    "yaml_path": comp["entry"],
                })
            else:
                entry["assets"]["js"] = comp["entry"]
                entry["components"][category] = {
                    "element_tag": comp["tag_name"],
                    "bundle_url": comp["entry"],
                }

    ui_plugins = list(plugin_map.values())

    resp = make_response(jsonify({"plugins": ui_plugins}))
    resp.headers["X-Deprecated"] = "Use /api/ui/registry instead"
    return resp



@bp.route('/config', methods=['POST'])
@require_auth
def update_plugin_config():
    data = request.json or {}

    disabled_list = data.get('disabled_plugins') or data.get('disabled_providers')
    if disabled_list is not None:
        # C2: strict type validation — must be a flat list of strings.
        if not isinstance(disabled_list, list) or not all(
            isinstance(x, str) for x in disabled_list
        ):
            return jsonify(
                {"error": "disabled_plugins must be a list of strings"}
            ), 400
        config_manager.set_disabled_plugins(disabled_list)

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
            with config_db_connection() as conn:
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
            with config_db_connection() as conn:
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
            with config_db_connection() as conn:
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
            with config_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT plugin_id FROM services WHERE id=? OR plugin_id=?", (plugin_id_int, plugin_id_int))
                row = c.fetchone()
                if row:
                    db_plugin_id = row['plugin_id']
                    c.execute("UPDATE services SET beta_opt_in=? WHERE plugin_id=?", (db_val, db_plugin_id))
                    conn.commit()
                    
        if not db_plugin_id:
            return jsonify({"error": f"Plugin {plugin_id} not found"}), 404
            
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

    from database.config_database import get_config_database
    db = get_config_database()

    # Attempt to resolve the service ID first
    service_id = db.get_service_id(plugin_id_raw)
    if not service_id and author and plugin_name:
        service_id = db.get_service_id(f"{author}.{plugin_name}")

    if service_id:
        with config_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT plugin_id FROM services WHERE id=?", (service_id,))
            row = c.fetchone()
            if row and row['plugin_id'] is not None:
                plugin_id = int(row['plugin_id'])
            else:
                plugin_id = service_id
    else:
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
        config_manager.enable_plugin(plugin_id)
    else:
        config_manager.disable_plugin(plugin_id)

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

@bp.route('/<plugin_id>/<path:filename>', methods=['GET'])
@require_auth
def serve_plugin_asset(plugin_id, filename):
    """
    Serve static assets (JS bundles, CSS, UI files, etc.) for a plugin.
    Uses the database's absolute_install_path and appends the requested path.
    """
    logger.info(f"[serve_plugin_asset] Request received for plugin_id={plugin_id}, filename={filename}")
    install_path = None
    try:
        with config_db_connection() as conn:
            c = conn.cursor()
            if str(plugin_id).isdigit():
                pid_int = int(plugin_id)
                c.execute("SELECT absolute_install_path FROM services WHERE plugin_id = ? OR id = ?", (pid_int, pid_int))
            else:
                c.execute("SELECT absolute_install_path FROM services WHERE LOWER(name) = ?", (str(plugin_id).lower(),))

            row = c.fetchone()
            if row and row[0]:
                install_path = row[0]
            else:
                # Fallback for complex namespace mismatches
                from database.config_database import get_config_database
                db = get_config_database()
                service_id = db.get_service_id(plugin_id)
                if service_id:
                    c.execute("SELECT absolute_install_path FROM services WHERE id = ?", (service_id,))
                    row = c.fetchone()
                    if row and row[0]:
                        install_path = row[0]
    except Exception as e:
        logger.error(f"Error querying service {plugin_id}: {e}", exc_info=True)

    logger.info(f"[serve_plugin_asset] Retrieve absolute_install_path={install_path} for plugin_id={plugin_id}")

    if install_path:
        resolved_install = Path(install_path).resolve()
        resolved_install = resolve_case_insensitive_path(resolved_install)

        from werkzeug.security import safe_join
        safe_path = safe_join(str(resolved_install), filename)

        if safe_path:
            file_path = Path(safe_path)
            if file_path.exists():
                logger.info(f"Serving plugin asset: {file_path}")
                return send_from_directory(str(file_path.parent), file_path.name)

        logger.warning(f"Security: Blocked traversal attempt or file missing for {plugin_id}: {filename}")
        abort(403)

    logger.error(f"Plugin asset folder NOT FOUND for {plugin_id}")
    abort(404)
