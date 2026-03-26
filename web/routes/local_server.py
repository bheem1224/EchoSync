from pathlib import Path
from flask import Blueprint, request, jsonify, send_file
from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("local_server_routes")
bp = Blueprint("local_server", __name__, url_prefix="/api/local_server")

@bp.get("/stream")
def stream_audio():
    """Stream audio file from the local library."""
    path_param = request.args.get("path")

    if not path_param:
        return jsonify({"error": "Missing 'path' query parameter"}), 400

    library_dir = config_manager.get_library_dir()

    if not library_dir:
        return jsonify({"error": "Library directory is not configured"}), 500

    try:
        requested_path = Path(path_param).resolve()
        library_root = library_dir.resolve()

        # Verify that the requested path falls within the library root
        # This prevents directory traversal attacks (e.g., path=../../etc/passwd)
        if not requested_path.is_relative_to(library_root):
            logger.warning(f"Security violation: Attempted to access file outside library path: {requested_path}")
            return jsonify({"error": "Security violation: Access denied"}), 403

        if not requested_path.exists():
            return jsonify({"error": "File not found"}), 404

        if not requested_path.is_file():
            return jsonify({"error": "Requested path is not a file"}), 400

        # Stream the file safely using Accept-Ranges: bytes
        return send_file(requested_path, conditional=True)

    except Exception as e:
        logger.error(f"Error streaming local file {path_param}: {e}", exc_info=True)
        return jsonify({"error": f"Internal server error: {e}"}), 500
