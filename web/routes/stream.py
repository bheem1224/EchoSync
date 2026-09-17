import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from core.tiered_logger import get_logger
from services.media_manager import MediaManagerService

logger = get_logger("stream")
router = APIRouter(tags=["Streaming"])
media_manager = MediaManagerService()

_AUDIO_MIMETYPES = {
    ".flac": "audio/flac",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".wav": "audio/wav",
    ".ape": "audio/ape",
    ".dsf": "audio/x-dsf",
    ".dff": "audio/x-dff",
    ".alac": "audio/alac",
}


@router.get("/api/v1/stream/{track_id}")
@router.get("/stream/{track_id}")
def stream_audio(track_id: str, request: Request):
    """Stream audio track by integer ID, sync_id, or media_id with HTTP Range support."""
    try:
        file_path = media_manager.get_track_stream(track_id)
        if not file_path or not Path(file_path).exists():
            raise HTTPException(status_code=404, detail={"error": "Track not found or file missing"})

        ext = Path(file_path).suffix.lower()
        media_type = _AUDIO_MIMETYPES.get(ext) or mimetypes.guess_type(file_path)[0] or "audio/mpeg"

        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=Path(file_path).name,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming track {track_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})
