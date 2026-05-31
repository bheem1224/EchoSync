from flask import Blueprint, jsonify, request
from core.nexus_framework.plugin_SDK import sdk
from core.tiered_logger import get_logger

logger = get_logger("acoustid_routes")

# Blueprint for the AcoustID settings-card config API
config_bp = Blueprint("acoustid_config", __name__, url_prefix="/api/plugins/acoustid")

@config_bp.get("/config")
def get_config():
    """Return the current AcoustID settings-card configuration."""
    try:
        
        # The legacy key was stored under service 'acoustid' as 'api_key'
        api_key = sdk.config.get('api_key')
        auto_contribute = sdk.config.get('auto_contribute')
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
        
        storage.ensure_service("acoustid", service_type="metadata")

        if "api_key" in payload and payload["api_key"].strip():
            from core.security import encrypt_string
            sdk.config.set('api_key', encrypt_string(payload["api_key"].strip()))

        if "auto_contribute" in payload:
            sdk.config.set('auto_contribute', str(bool(payload["auto_contribute"])).lower())

        api_key = sdk.config.get('api_key')
        auto_contribute = sdk.config.get('auto_contribute')
        return jsonify({
            "success": True, 
            "api_key_configured": bool(api_key),
            "auto_contribute": auto_contribute == "true" if isinstance(auto_contribute, str) else bool(auto_contribute)
        }), 200
    except Exception as e:
        logger.error(f"Error saving AcoustID config: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
