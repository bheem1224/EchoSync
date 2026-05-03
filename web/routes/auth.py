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
            import uuid
            from core.security import generate_auth_token
            csrf_token = str(uuid.uuid4())
            token = generate_auth_token(username or plugin_auth.get("user", "unknown"), csrf_token)
            
            resp = jsonify(plugin_auth)
            resp.set_cookie('echo_auth', token, httponly=True, secure=False, samesite='Strict')
            resp.set_cookie('echo_csrf', csrf_token, httponly=False, secure=False, samesite='Strict')
            return resp
    except Exception as e:
        import logging
        logging.getLogger("auth").error(f"Error in AUTHENTICATE_USER hook: {e}")

    try:
        from core.security import verify_user_credentials, generate_auth_token
        verify_user_credentials(username, password)
        
        import uuid
        csrf_token = str(uuid.uuid4())
        token = generate_auth_token(username, csrf_token)
        
        resp = jsonify({"authenticated": True, "user": username})
        resp.set_cookie('echo_auth', token, httponly=True, secure=False, samesite='Strict')
        resp.set_cookie('echo_csrf', csrf_token, httponly=False, secure=False, samesite='Strict')
        return resp
    except NotImplementedError as e:
        return jsonify({"error": str(e)}), 501
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500

    return jsonify({"error": "Unauthorized"}), 401
