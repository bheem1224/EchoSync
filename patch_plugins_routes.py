import re

with open('web/routes/plugins.py', 'r') as f:
    content = f.read()

toggle_code = """
@bp.route('/<plugin_id>/toggle', methods=['POST'])
@require_auth
def toggle_plugin(plugin_id):
    \"\"\"
    Safely toggle a plugin's enabled status by updating the disabled_providers list.
    \"\"\"
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

    # Mark restart pending
    from core.state import system_state
    system_state.restart_pending = True

    return jsonify({"success": True})
"""

# Insert before serve_plugin_ui
content = content.replace("@bp.route('/<plugin_id>/ui/<path:filename>', methods=['GET'])", toggle_code + "\n@bp.route('/<plugin_id>/ui/<path:filename>', methods=['GET'])")

with open('web/routes/plugins.py', 'w') as f:
    f.write(content)
