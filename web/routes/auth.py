from flask import Blueprint, jsonify, request

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@bp.get("/status")
def auth_status():
    # TODO: reflect provider auth states (tokens live in config/db only)
    return jsonify({"authenticated": False, "providers": []}), 200

@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username")
    password = payload.get("password")

    try:
        from core.hook_manager import hook_manager
        plugin_auth = hook_manager.apply_filters('AUTHENTICATE_USER', None, username=username, password=password, payload=payload)
        if plugin_auth is not None and isinstance(plugin_auth, dict) and plugin_auth.get("authenticated") is True:
            # Plugin successfully authenticated
            return jsonify(plugin_auth), 200
    except Exception as e:
        import logging
        logging.getLogger("auth").error(f"Error in AUTHENTICATE_USER hook: {e}")

    try:
        from core.security import verify_user_credentials
        verify_user_credentials(username, password)
    except NotImplementedError as e:
        return jsonify({"error": str(e)}), 501
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500

    return jsonify({"error": "Unauthorized"}), 401
