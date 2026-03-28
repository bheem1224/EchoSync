import json
from flask import Blueprint, jsonify, request
from core.settings import config_manager
from core.plugin_loader import get_all_plugins

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
        config_manager.set_disabled_providers(disabled_list)

    active_matching_engine = data.get('active_matching_engine')
    if active_matching_engine is not None:
        config_manager.set('settings.active_matching_engine', active_matching_engine)

    return jsonify({"success": True})
