"""System endpoints for status, settings, and logs."""

from flask import Blueprint, jsonify, request, Response
import json
import platform
import psutil
from utils.logging_config import get_logger
from config.settings import config_manager

logger = get_logger("system_route")
bp = Blueprint("system", __name__, url_prefix="/api")


@bp.get("/health")
def health_check():
    """Health endpoint expected by Svelte UI (/api/health)."""
    try:
        return jsonify({
            "status": "healthy",
            "results": {},
            "timestamp": None,
        }), 200
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify({"status": "error", "results": {}}), 500


@bp.get("/status")
def system_status():
    """System health check and service status."""
    try:
        return jsonify({
            "status": "online",
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "uptime": None,  # TODO: track app start time
        }), 200
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({"error": "Failed to get status"}), 500


@bp.get("/stats")
def system_stats():
    """System resource usage statistics."""
    try:
        mem = psutil.virtual_memory()
        return jsonify({
            "memory": {
                "total": mem.total,
                "available": mem.available,
                "percent": mem.percent,
            },
            "cpu_percent": psutil.cpu_percent(interval=0.1),
        }), 200
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return jsonify({"error": "Failed to get stats"}), 500


@bp.get("/settings")
def get_settings():
    """Get current application settings (Svelte expects settings/schema/version)."""
    try:
        data = config_manager.get_all() if hasattr(config_manager, "get_all") else {}
        return jsonify({
            "settings": data,
            "schema": None,
            "version": None,
        }), 200
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({"error": "Failed to get settings"}), 500


@bp.post("/settings")
def update_settings():
    """Update application settings (partial update)."""
    try:
        payload = request.get_json(silent=True) or {}
        for key, value in payload.items():
            config_manager.set(key, value)
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({"error": "Failed to update settings"}), 500


@bp.get("/logs")
def get_logs():
    """Retrieve recent application logs."""
    try:
        # TODO: implement log retrieval from logging system
        return jsonify({"logs": []}), 200
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({"error": "Failed to get logs"}), 500


@bp.get("/activity/feed")
def activity_feed():
    """Activity feed for dashboard."""
    return jsonify({"items": []}), 200


@bp.get("/activity/toasts")
def activity_toasts():
    """Toast notifications."""
    return jsonify({"toasts": []}), 200


@bp.get("/downloads/status")
def downloads_status():
    """Download queue status."""
    return jsonify({
        "active": [],
        "queued": [],
        "completed": [],
        "failed": []
    }), 200


@bp.get("/quality-profile")
def quality_profile():
    """Audio quality preferences."""
    return jsonify({
        "min_bitrate": 320,
        "preferred_format": "FLAC",
        "fallback_format": "MP3"
    }), 200
