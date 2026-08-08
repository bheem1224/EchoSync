"""
Media API routes (web/routes/media.py).

Serves physical file telemetry from the local_media table.
All lookups are keyed by media_id (NanoID), enforcing the 2-Model contract:
  - Tracks are identified by sync_id (logical identity)
  - Physical files are identified by media_id (physical telemetry)
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from web.auth import require_auth
from core.database.repositories.track_repo import TrackRepository
from database.music_database import get_database
from core.tiered_logger import get_logger

logger = get_logger("media_route")
router = APIRouter(prefix="/api/v1/core/media", tags=["Media"])


def _media_to_dict(m) -> dict:
    """Serialize a LocalMedia ORM object to a clean JSON-safe dict."""
    return {
        "media_id": m.media_id,
        "track_id": m.track_id,
        "file_path": m.file_path,
        "file_format": m.file_format,
        "bitrate": m.bitrate,
        "sample_rate": m.sample_rate,
        "bit_depth": m.bit_depth,
        "file_size_bytes": m.file_size_bytes,
        "inode": m.inode,
        "mtime": m.mtime,
        "added_at": m.added_at.isoformat() if m.added_at else None,
    }


@router.get("/{media_id}")
def get_media(media_id: str):
    """
    Fetch physical file telemetry for a single media file by its media_id (NanoID).

    GET /api/media/<media_id>
    Response: { media_id, track_id, file_path, file_format, bitrate, ... }
    """
    try:
        db = get_database()
        with db.get_session() as session:
            media = TrackRepository.get_media_by_media_id(session, media_id)
            if not media:
                raise HTTPException(status_code=404, detail={"error": "Media not found"})
            return _media_to_dict(media)
    except Exception as e:
        logger.error(f"Error fetching media {media_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Failed to fetch media"})


@router.get("/")
def get_media_bulk(request: Request):
    """
    Bulk fetch physical file telemetry for multiple media files.

    GET /api/media/?ids=abc,def,ghi
    Response: { items: [...], count: N }
    """
    ids_param = request.query_params.get("ids", "")
    if not ids_param:
        raise HTTPException(status_code=400, detail={"error": "Missing required 'ids' query parameter"})

    media_ids = [i.strip() for i in ids_param.split(",") if i.strip()]
    if not media_ids:
        raise HTTPException(status_code=400, detail={"error": "No valid media IDs provided"})

    try:
        db = get_database()
        results = []
        with db.get_session() as session:
            for media_id in media_ids:
                media = TrackRepository.get_media_by_media_id(session, media_id)
                if media:
                    results.append(_media_to_dict(media))
        return {"items": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error fetching bulk media: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Failed to fetch media"})


@router.get("/track/{sync_id}")
def get_media_for_track(sync_id: str):
    """
    Fetch all physical file telemetry for a track identified by sync_id.

    GET /api/media/track/<sync_id>
    Response: { items: [...], count: N }
    """
    try:
        db = get_database()
        with db.get_session() as session:
            track = TrackRepository.get_track_by_sync_id(session, sync_id)
            if not track:
                raise HTTPException(status_code=404, detail={"error": "Track not found"})
            media_list = TrackRepository.get_media_for_track(session, track.id)
            return jsonify({
                "sync_id": sync_id,
                "items": [_media_to_dict(m) for m in media_list],
                "count": len(media_list),
            })
    except Exception as e:
        logger.error(f"Error fetching media for track {sync_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Failed to fetch media for track"})
