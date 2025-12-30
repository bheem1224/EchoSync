from flask import Blueprint, jsonify, request
from web.services.sync_service import SyncAdapter

bp = Blueprint("playlists", __name__, url_prefix="/api/playlists")

@bp.get("/")
def list_playlists():
    # Placeholder: surface playlists via provider adapters (future)
    return jsonify({"items": [], "total": 0}), 200

@bp.post("/sync")
def trigger_sync():
    payload = request.get_json(silent=True) or {}
    adapter = SyncAdapter()
    result = adapter.trigger_sync(payload)
    status = 202 if result.get("accepted") else 400
    return jsonify(result), status
