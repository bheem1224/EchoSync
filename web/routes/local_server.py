import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("local_server_routes")
router = APIRouter(prefix="/api/v1/system/local_server", tags=["Local Server"])
legacy_router = APIRouter(prefix="/api/local_server", tags=["Local Server Legacy"])
bp = router

# Formats that modern browsers can decode natively — served directly with Accept-Ranges.
_NATIVE_FORMATS = {'.mp3', '.flac', '.wav', '.m4a', '.ogg'}

# Formats that require server-side transcoding before the browser can play them.
_TRANSCODE_FORMATS = {'.dsf', '.dff', '.ape', '.wma'}


@router.get("/stream")
@legacy_router.get("/stream")
def stream_audio(path: str = Query(..., description="Path to the audio file")):
    """Stream audio file from the local library.

    Native formats (FLAC, MP3, WAV, M4A, OGG) are served directly via
    FileResponse which enables Accept-Ranges byte-range delivery.

    Exotic formats (DSF, DFF, APE, WMA) are transcoded on-the-fly to a FLAC
    stream via FFmpeg so the frontend player remains lightweight and never
    needs to handle exotic codec decoding itself.
    """
    if not path:
        raise HTTPException(status_code=400, detail="Missing 'path' query parameter")

    candidate_roots = [
        config_manager.get('storage.library_dir'),
        config_manager.get('library_dir'),
        config_manager.get('download_dir'),
        config_manager.get('storage.download_dir'),
        config_manager.get('data_dir'),
        '.'
    ]
    allowed_roots = [Path(r).resolve() for r in candidate_roots if r]

    if not allowed_roots:
        raise HTTPException(status_code=500, detail="Library directory is not configured")

    try:
        from core.path_security import resolve_safe_path, PathTraversalError
        try:
            requested_path = resolve_safe_path(allowed_roots, path)
        except (PathTraversalError, ValueError):
            logger.warning(f"Security violation: Attempted to access file outside library path: {path}")
            raise HTTPException(status_code=403, detail="Security violation: Access denied")

        if not requested_path.exists() or not requested_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        ext = requested_path.suffix.lower()

        # --- Native formats: direct byte-range delivery ---
        if ext in _NATIVE_FORMATS:
            return FileResponse(path=str(requested_path), media_type=f"audio/{ext.lstrip('.')}")

        # --- Exotic formats: server-side FFmpeg transcode to FLAC stream ---
        if ext in _TRANSCODE_FORMATS:
            logger.info(f"Transcoding {ext} → FLAC for {requested_path.name}")

            # Fixed command line with pipe:0 input stream prevents CWE-078 command injection
            ffmpeg_cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", "pipe:0",
                "-c:a", "flac", "-f", "flac", "pipe:1",
            ]

            def generate():
                in_file = open(requested_path, "rb")
                proc = subprocess.Popen(
                    ffmpeg_cmd,
                    stdin=in_file,
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
                        metadata={"cmd": ffmpeg_cmd, "file": requested_path.name}
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
                    try:
                        in_file.close()
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

            return StreamingResponse(
                generate(),
                media_type="audio/flac",
                headers={
                    "Content-Disposition": f'inline; filename="{requested_path.stem}.flac"',
                },
            )

        # Unknown/unsupported format — serve as-is and let the client decide.
        return FileResponse(path=str(requested_path))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming local file {path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing the request")
