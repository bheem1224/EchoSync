import re

with open('web/routes/plugins.py', 'r') as f:
    content = f.read()

# Add imports if they don't exist
if "import abort" not in content:
    content = content.replace("from flask import Blueprint, jsonify, request", "from flask import Blueprint, jsonify, request, abort, send_from_directory")

if "from werkzeug.utils import safe_join" not in content:
    content = content.replace("from core.settings import config_manager", "from core.settings import config_manager\nfrom werkzeug.utils import safe_join\nimport os")

route_code = """
@bp.route('/<plugin_id>/ui/<path:filename>', methods=['GET'])
def serve_plugin_ui(plugin_id, filename):
    plugins_dir = str(config_manager.get_plugins_dir())
    ui_dir = safe_join(plugins_dir, plugin_id, 'ui')

    if ui_dir is None or not os.path.exists(ui_dir):
        abort(404)

    return send_from_directory(ui_dir, filename)
"""

content = content + "\n" + route_code

with open('web/routes/plugins.py', 'w') as f:
    f.write(content)
