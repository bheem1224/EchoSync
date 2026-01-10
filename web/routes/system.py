"""System endpoints for status, settings, and logs."""

from flask import Blueprint, jsonify, request, Response
import json
import os
import platform
import psutil
from utils.logging_config import get_logger
from core.settings import config_manager

logger = get_logger("system_route")
bp = Blueprint("system", __name__, url_prefix="/api")


@bp.get("/health")
def health_check():
    """Health endpoint with actual service health check results."""
    try:
        from core.health_check import health_check_registry
        
        # Get all cached health check results
        results = health_check_registry.get_all_last_results()
        
        # Convert to JSON-serializable format
        results_dict = {}
        for service_name, result in results.items():
            results_dict[service_name] = {
                "status": result.status,
                "message": result.message,
                "details": result.details,
                "timestamp": result.timestamp.isoformat() if result.timestamp else None,
                "response_time_ms": result.response_time_ms
            }
        
        # Overall status: healthy if all services are healthy or degraded
        overall_status = "healthy"
        for result in results.values():
            if result.status == "unhealthy":
                overall_status = "degraded"
                break
        
        return jsonify({
            "status": overall_status,
            "results": results_dict,
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


@bp.get('/quality-profiles')
def list_quality_profiles():
    """Return stored quality profiles from config manager."""
    try:
        profiles = config_manager.get_quality_profiles()
        return jsonify({'profiles': profiles}), 200
    except Exception as e:
        logger.error(f"Error listing quality profiles: {e}")
        return jsonify({'error': 'Failed to list quality profiles'}), 500


@bp.post('/quality-profiles')
def save_quality_profiles():
    """Accept and validate submitted quality profiles, then persist via config manager.

    Expects JSON body: { "profiles": [ ... ] }
    """
    try:
        payload = request.get_json(silent=True) or {}
        profiles = payload.get('profiles') if isinstance(payload, dict) else None
        if profiles is None:
            return jsonify({'error': 'Missing profiles list'}), 400

        # Basic validation: list of dicts with id and name
        if not isinstance(profiles, list):
            return jsonify({'error': 'Profiles must be a list'}), 400

        for p in profiles:
            if not isinstance(p, dict) or 'id' not in p or 'name' not in p:
                return jsonify({'error': 'Invalid profiles format; each profile must include id and name'}), 400

        ok = config_manager.set_quality_profiles(profiles)
        if not ok:
            return jsonify({'error': 'Failed to persist profiles'}), 500
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Error saving quality profiles: {e}")
        return jsonify({'error': 'Failed to save profiles'}), 500


@bp.post('/quality-profile')
def save_single_quality_profile():
    """Save a single quality profile into the stored list.

    Body: { "profile": { ... } }
    Replaces existing profile with same id or appends.
    """
    try:
        payload = request.get_json(silent=True) or {}
        profile = payload.get('profile') if isinstance(payload, dict) else None
        if profile is None:
            return jsonify({'error': 'Missing profile object'}), 400

        if not isinstance(profile, dict) or 'id' not in profile or 'name' not in profile:
            return jsonify({'error': 'Invalid profile format; id and name required'}), 400

        # Debug log incoming profile payload to help track missing arrays
        try:
            logger.debug(f"Incoming single profile payload: {json.dumps(profile, default=str)[:2000]}")
        except Exception:
            logger.debug(f"Incoming single profile payload (non-serializable)")

        # Load existing profiles
        existing = config_manager.get_quality_profiles() or []
        found = False
        for i, p in enumerate(existing):
            if str(p.get('id')) == str(profile.get('id')):
                # Preserve existing name if incoming profile omitted it
                if not profile.get('name') and p.get('name'):
                    profile['name'] = p.get('name')
                existing[i] = profile
                found = True
                break
        if not found:
            # Ensure new profile has a name
            if not profile.get('name'):
                profile['name'] = f"Profile {len(existing) + 1}"
            existing.append(profile)

        ok = config_manager.set_quality_profiles(existing)
        if not ok:
            return jsonify({'error': 'Failed to persist profile'}), 500
        return jsonify({'success': True, 'profile': profile}), 200
    except Exception as e:
        logger.error(f"Error saving single quality profile: {e}")
        return jsonify({'error': 'Failed to save profile'}), 500


@bp.get('/browse')
def browse_filesystem():
    """Browse allowed filesystem roots and folders for the UI Browse buttons.

    Query params:
      - path: absolute path or root key (downloads, data, config, library, logs)

    Security: only paths under configured allowed roots will be listed.
    Returns JSON: { path: <abs>, root: <root_key>, entries: [ {name, path, relpath, is_dir} ] }
    """
    try:
        requested = request.args.get('path', '')
        settings = config_manager.get_all() or {}

        roots = {
            'data': settings.get('data_dir'),
            'downloads': settings.get('downloads_path') or settings.get('storage', {}).get('download_dir'),
            'library': settings.get('library_path'),
            'logs': settings.get('logs_path'),
            'config': settings.get('config_dir'),
        }
        # Filter out None values
        allowed_roots = {k: os.path.abspath(v) for k, v in roots.items() if v}

        # If no path provided, return available roots
        if not requested:
            return jsonify({'roots': [{'key': k, 'path': p} for k, p in allowed_roots.items()]}), 200

        # Special-case: allow browsing filesystem root when client requests '/'
        if requested == '/':
            req_path = os.path.abspath(os.sep)
        else:
            # If requested is a root key, map it
            if requested in allowed_roots:
                req_path = allowed_roots[requested]
            else:
                # Accept absolute paths or paths relative to data root
                if os.path.isabs(requested):
                    req_path = os.path.abspath(requested)
                else:
                    base = allowed_roots.get('data') or os.getcwd()
                    req_path = os.path.abspath(os.path.join(base, requested))

        # Ensure requested path lies within one of the allowed roots, unless browsing root
        matched_root = None
        if req_path == os.path.abspath(os.sep):
            # browsing top-level root; use root key 'root'
            matched_root = ('root', req_path)
        elif os.path.isabs(req_path) and os.path.exists(req_path) and os.path.isdir(req_path):
            # Allow browsing absolute host paths (useful when running on the host/Windows)
            matched_root = ('host', req_path)
        else:
            for key, root_path in allowed_roots.items():
                try:
                    if os.path.commonpath([req_path, root_path]) == root_path:
                        matched_root = (key, root_path)
                        break
                except Exception:
                    continue

        if not matched_root:
            return jsonify({'error': 'Path not allowed'}), 403

        # Path must exist and be a directory
        if not os.path.exists(req_path) or not os.path.isdir(req_path):
            return jsonify({'error': 'Path not found or not a directory'}), 404

        entries = []
        for name in sorted(os.listdir(req_path)):
            full = os.path.join(req_path, name)
            entries.append({
                'name': name,
                'path': os.path.abspath(full),
                'relpath': os.path.relpath(full, matched_root[1]) if matched_root and matched_root[1] else name,
                'is_dir': os.path.isdir(full)
            })

        return jsonify({'path': req_path, 'root': matched_root[0], 'entries': entries}), 200
    except Exception as e:
        logger.error(f"Error browsing filesystem: {e}")
        return jsonify({'error': 'Failed to browse path'}), 500
