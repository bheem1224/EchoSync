import json
from flask import Blueprint, jsonify, request
from core.settings import config_manager
from core.plugin_loader import get_all_plugins
from core.plugin_store import plugin_store

bp = Blueprint('plugins', __name__, url_prefix='/api/system/plugins')

@bp.route('', methods=['GET'])
def list_plugins():
    plugins = get_all_plugins()
    return jsonify({'plugins': plugins})

@bp.route('/config', methods=['POST'])
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


def get_plugin_store():
    try:
        plugins = plugin_store.get_all_store_plugins()
        return jsonify({'plugins': plugins})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/store', methods=['GET'])
def get_plugin_store():
    try:
        plugins = plugin_store.get_all_store_plugins()
        return jsonify({'plugins': plugins})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/install', methods=['POST'])
def install_plugin():
    data = request.json or {}
    plugin_info = data.get('plugin')
    if not plugin_info:
        return jsonify({"error": "Plugin info required"}), 400

    success = plugin_store.download_plugin(plugin_info)
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Failed to install plugin"}), 500
