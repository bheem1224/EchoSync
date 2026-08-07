import subprocess
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file, Response, stream_with_context
from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("local_server_routes")
bp = Blueprint("local_server", __name__, url_prefix="/api/local_server")

# Formats that modern browsers can decode natively — served directly with Accept-Ranges.
_NATIVE_FORMATS = {'.mp3', '.flac', '.wav', '.m4a', '.ogg'}

# Formats that require server-side transcoding before the browser can play them.
_TRANSCODE_FORMATS = {'.dsf', '.dff', '.ape', '.wma'}


@bp.get("/stream")
def stream_audio():
    """Stream audio file from the local library.

    Native formats (FLAC, MP3, WAV, M4A, OGG) are served directly via
    send_file which enables Accept-Ranges byte-range delivery.

    Exotic formats (DSF, DFF, APE, WMA) are transcoded on-the-fly to a FLAC
    stream via FFmpeg so the frontend player remains lightweight and never
    needs to handle exotic codec decoding itself.
    """
    path_param = request.args.get("path")

    if not path_param:
        return jsonify({"error": "Missing 'path' query parameter"}), 400

    _lib = config_manager.get('storage.library_dir') or config_manager.get('library_dir')
    library_dir = Path(_lib) if _lib else None

    if not library_dir:
        return jsonify({"error": "Library directory is not configured"}), 500

    try:
        requested_path = Path(path_param).resolve()
        library_root = library_dir.resolve()

        # Verify that the requested path falls within the library root.
        # This prevents directory traversal attacks (e.g., path=../../etc/passwd).
        if not requested_path.is_relative_to(library_root):
            logger.warning(f"Security violation: Attempted to access file outside library path: {requested_path}")
            return jsonify({"error": "Security violation: Access denied"}), 403

        if not requested_path.exists():
            return jsonify({"error": "File not found"}), 404

        if not requested_path.is_file():
            return jsonify({"error": "Requested path is not a file"}), 400

        ext = requested_path.suffix.lower()

        # --- Native formats: direct byte-range delivery ---
        if ext in _NATIVE_FORMATS:
            return send_file(requested_path, conditional=True)

        # --- Exotic formats: server-side FFmpeg transcode to FLAC stream ---
        if ext in _TRANSCODE_FORMATS:
            logger.info(f"Transcoding {ext} → FLAC for {requested_path.name}")

            import os
            safe_path = os.path.normpath(str(requested_path.resolve()))
            ffmpeg_cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", safe_path,
                "-c:a", "flac", "-f", "flac", "pipe:1",
            ]

            def generate():
                proc = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=False,
                )
                reg_id = None
                try:
                    from core.task_manager.supervisor import supervisor
                    from core.task_manager.models import ProcessOwner, OwnerType
                    owner_info = ProcessOwner(
                        owner_id="local_server.stream",
                        owner_type=OwnerType.CORE,
                        pid=proc.pid,
                        task_name="ffmpeg_transcode",
                        metadata={"cmd": ffmpeg_cmd, "path": safe_path}
                    )
                    reg_id = supervisor.register_process(owner_info)
                except Exception as reg_err:
                    logger.warning(f"Could not register FFmpeg transcode process with supervisor: {reg_err}")

                try:
                    while True:
                        chunk = proc.stdout.read(65536)
                        if not chunk:
                            break
                        yield chunk
                finally:
                    if reg_id:
                        try:
                            supervisor.unregister_process(reg_id)
                        except Exception:
                            pass
                    proc.stdout.close()
                    proc.wait()
                    if proc.returncode not in (0, None):
                        stderr_out = proc.stderr.read().decode(errors="replace")
                        logger.error(
                            f"FFmpeg exited {proc.returncode} transcoding "
                            f"{requested_path.name}: {stderr_out}"
                        )
                    proc.stderr.close()

            return Response(
                stream_with_context(generate()),
                mimetype="audio/flac",
                headers={
                    "Content-Disposition": f'inline; filename="{requested_path.stem}.flac"',
                },
            )

        # Unknown/unsupported format — serve as-is and let the client decide.
        return send_file(requested_path, conditional=True)

    except Exception as e:
        logger.error(f"Error streaming local file {path_param}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred while processing the request"}), 500
