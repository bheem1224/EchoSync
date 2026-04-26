from flask import Blueprint, jsonify, request
from core.file_handling.storage import get_storage_service
from core.tiered_logger import get_logger

logger = get_logger("acoustid_routes")

# Blueprint for the AcoustID settings-card config API
config_bp = Blueprint("acoustid_config", __name__, url_prefix="/api/plugins/acoustid")

@config_bp.get("/config")
def get_config():
    """Return the current AcoustID settings-card configuration."""
    try:
        storage = get_storage_service()
        # The legacy key was stored under service 'acoustid' as 'api_key'
        api_key = storage.get_service_config("acoustid", "api_key")
        auto_contribute = storage.get_service_config("acoustid", "auto_contribute")
        return jsonify({
            "api_key_configured": bool(api_key),
            "auto_contribute": auto_contribute == "true" if isinstance(auto_contribute, str) else bool(auto_contribute),
        }), 200
    except Exception as e:
        logger.error(f"Error reading AcoustID config: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@config_bp.post("/config")
def save_config():
    """Persist AcoustID settings-card values (API key + auto-contribute)."""
    try:
        payload = request.get_json(force=True) or {}
        storage = get_storage_service()
        storage.ensure_service("acoustid", display_name="AcoustID", service_type="metadata")

        if "api_key" in payload and payload["api_key"].strip():
            from core.security import encrypt_string
            storage.set_service_config("acoustid", "api_key", encrypt_string(payload["api_key"].strip()))

        if "auto_contribute" in payload:
            storage.set_service_config("acoustid", "auto_contribute", str(bool(payload["auto_contribute"])).lower())

        api_key = storage.get_service_config("acoustid", "api_key")
        auto_contribute = storage.get_service_config("acoustid", "auto_contribute")
        return jsonify({
            "success": True, 
            "api_key_configured": bool(api_key),
            "auto_contribute": auto_contribute == "true" if isinstance(auto_contribute, str) else bool(auto_contribute)
        }), 200
    except Exception as e:
        logger.error(f"Error saving AcoustID config: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
