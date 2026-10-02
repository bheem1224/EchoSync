import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from core.tiered_logger import get_logger
from database.music_database import LocalMedia, get_database
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


def get_db():
    db = get_database()
    with db.session_scope() as session:
        yield session


@router.get("/api/v1/core/stream/media/{media_id}")
@router.get("/api/v1/stream/media/{media_id}")
@router.get("/stream/media/{media_id}")
@router.get("/media/{media_id}")
def stream_media_by_id(media_id: str, db: Session = Depends(get_db)):
    clean_media_id = str(media_id or "").strip().split("?")[0]
    if not clean_media_id or clean_media_id.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Integer primary keys are not allowed. Provide a valid string NanoID media_id.",
        )

    media = db.query(LocalMedia).filter(LocalMedia.media_id == clean_media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media file not found")

    file_path = media.file_path
    if not file_path or not Path(file_path).exists():
        mapped = media_manager.get_track_stream(clean_media_id)
        if mapped and Path(mapped).exists():
            file_path = mapped
        else:
            raise HTTPException(status_code=404, detail="Media file not found on disk")

    ext = Path(file_path).suffix.lower()
    media_type = (
        getattr(media, "mime_type", None)
        or _AUDIO_MIMETYPES.get(ext)
        or mimetypes.guess_type(file_path)[0]
        or "audio/mpeg"
    )

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=Path(file_path).name,
    )


@router.get("/api/v1/core/stream/{track_id}")
@router.get("/api/v1/stream/{track_id}")
@router.get("/stream/{track_id}")
def stream_audio(track_id: str, request: Request, response: Response):
    """Stream audio track by integer ID, sync_id, or media_id with HTTP Range support.

    DEPRECATED: Integer-based streaming paths are deprecated. Use /api/v1/core/stream/media/{media_id}.
    """
    response_headers = {}
    if track_id.isdigit():
        response_headers["Deprecation"] = "true"
        response_headers["X-EchoSync-Warning"] = (
            "Integer-based streaming paths are deprecated. Use /api/v1/core/stream/media/{media_id}."
        )

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
            headers=response_headers if response_headers else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming track {track_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})
