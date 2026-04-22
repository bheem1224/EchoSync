import os
from flask import Blueprint, jsonify, request
from web.auth import require_auth
from core.tiered_logger import get_logger
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

logger = get_logger("dashboard_route")
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/system/dashboard")

DASHBOARD_FILE = os.path.join("config", "webui", "dashboard.yaml")
DEFAULT_DASHBOARD_CONTENT = """# EchoSync Dashboard Configuration
# You can manually edit this file or use the UI editor.
views:
  - title: Home
    icon: mdi:home
    cards:
      - type: spotify-dashboard-card
      - type: plex-dashboard-card
"""

def _ensure_file():
    if not os.path.exists(DASHBOARD_FILE):
        os.makedirs(os.path.dirname(DASHBOARD_FILE), exist_ok=True)
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(DEFAULT_DASHBOARD_CONTENT)

@dashboard_bp.get("/")
@require_auth
def get_dashboard():
    """Reads dashboard.yaml and returns the parsed structure as standard JSON."""
    _ensure_file()

    yaml = YAML()
    try:
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            data = yaml.load(f)

        if data is None:
            data = {}

    except YAMLError as e:
        return jsonify({"error": "YAML Syntax Error", "details": str(e)}), 400
    except Exception as e:
        logger.error(f"Error reading dashboard.yaml: {e}")
        return jsonify({"error": "Failed to read dashboard configuration"}), 500

    return jsonify(data), 200

@dashboard_bp.post("/")
@require_auth
def update_dashboard():
    """Accepts a JSON payload, converts it, and writes it back to dashboard.yaml preserving comments."""
    payload = request.get_json()
    if payload is None:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    _ensure_file()

    yaml = YAML()
    yaml.preserve_quotes = True

    try:
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            data = yaml.load(f)

        if data is None:
            data = payload
        elif isinstance(data, dict) and isinstance(payload, dict):
            # Update root level keys, removing ones not in payload
            for key in list(data.keys()):
                if key not in payload:
                    del data[key]
            for key, value in payload.items():
                data[key] = value
        else:
            data = payload

        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        return jsonify({"success": True}), 200
    except YAMLError as e:
        return jsonify({"error": "YAML Syntax Error while writing", "details": str(e)}), 400
    except Exception as e:
        logger.error(f"Error writing dashboard.yaml: {e}")
        return jsonify({"error": "Failed to write dashboard configuration"}), 500
