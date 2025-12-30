from flask import Blueprint, jsonify

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@bp.get("/status")
def auth_status():
    # TODO: reflect provider auth states (tokens live in config/db only)
    return jsonify({"authenticated": False, "providers": []}), 200
