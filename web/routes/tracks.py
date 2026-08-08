"""
Tracks API routes (web/routes/tracks.py).

All track endpoints use sync_id (canonical URN) as the routing key.
Responses include media_ids for UUID-based media telemetry lookups via /api/media/.
Physical file telemetry is NOT nested in track responses — use /api/media/<media_id>.
"""
from typing import List, Optional, Union, Any, Generic, TypeVar
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from pydantic import BaseModel

from database.music_database import get_database, Track, LocalMedia
from core.tiered_logger import get_logger
from core.database.repositories.track_repo import TrackRepository
from core.db.schemas import TrackSummarySchema, TrackResponseSchema

logger = get_logger("tracks_route")
router = APIRouter(prefix="/api/v1/core/tracks", tags=["Core: Tracks"])

# Physical-only fields that must never be PATCH'd through the track endpoint
_PHYSICAL_FIELDS = frozenset({
    "file_path", "file_format", "bitrate", "sample_rate",
    "bit_depth", "file_size_bytes", "inode", "mtime",
})

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    limit: Optional[int] = None
    offset: Optional[int] = None
    count: Optional[int] = None

@router.get(
    "/",
    response_model=Union[PaginatedResponse[TrackResponseSchema], PaginatedResponse[TrackSummarySchema]],
    response_model_exclude_unset=True
)
async def list_canonical_tracks(
    detail: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    ids: Optional[str] = Query(None)
):
    """List canonical tracks with pagination, optionally fetching details or batching ids."""
    try:
        from sqlalchemy.orm import selectinload
        db = get_database()
        with db.get_session() as session:
            query = session.query(Track).options(selectinload(Track.media))
            
            if ids:
                sync_ids = [s.strip() for s in ids.split(",") if s.strip()]
                if sync_ids:
                    query = query.filter(Track.sync_id.in_(sync_ids))
            
            tracks = query.order_by(Track.title).offset(offset).limit(limit).all()
            
            # To respect 'detail=False' with FastAPI's Union parsing, we must manually instantiate
            # the models here, because otherwise FastAPI's Union evaluator will just pick the first
            # schema that succeeds (TrackResponseSchema), ignoring the 'detail' flag.
            if detail:
                return PaginatedResponse[TrackResponseSchema](items=tracks, limit=limit, offset=offset, count=len(tracks))
            else:
                return PaginatedResponse[TrackSummarySchema](items=tracks, limit=limit, offset=offset, count=len(tracks))

    except Exception as e:
        logger.error(f"Error listing canonical tracks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list tracks")


@router.get(
    "/{sync_id}",
    response_model=Union[TrackResponseSchema, TrackSummarySchema],
    response_model_exclude_unset=True
)
async def get_canonical_track(sync_id: str, detail: bool = Query(False)):
    """
    Fetch a canonical track by sync_id.

    GET /api/v1/core/tracks/<sync_id>
    Returns logical metadata + media array if detail=true.
    """
    try:
        db = get_database()
        with db.get_session() as session:
            track = TrackRepository.get_track_by_sync_id(session, sync_id)
            if not track:
                raise HTTPException(status_code=404, detail="Track not found")
                
            return track
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching canonical track {sync_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch track")


@router.patch("/{sync_id}", response_model=TrackSummarySchema)
async def patch_canonical_track(sync_id: str, request: Request):
    """
    Partially update a track's logical metadata by sync_id.

    PATCH /api/tracks/<sync_id>
    Rejects any attempt to patch physical file properties.
    """
    try:
        payload = await request.json()
        if not payload:
            payload = {}
            
        rejected = [k for k in payload if k in _PHYSICAL_FIELDS]
        if rejected:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "Cannot PATCH physical file properties through track endpoint",
                    "rejected_fields": rejected,
                    "hint": "Use /api/media/<media_id> for physical telemetry updates.",
                }
            )

        db = get_database()
        with db.get_session() as session:
            track = TrackRepository.get_track_by_sync_id(session, sync_id)
            if not track:
                raise HTTPException(status_code=404, detail="Track not found")

            allowed = {"title", "track_number", "disc_number", "musicbrainz_id", "isrc", "global_rating"}
            for key, val in payload.items():
                if key in allowed and hasattr(track, key):
                    setattr(track, key, val)
            session.commit()
            session.refresh(track)
            
            return track
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error patching track {sync_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to patch track")


@router.delete("/{sync_id}")
async def delete_canonical_track(sync_id: str):
    """
    Delete a track and cascade-delete its associated LocalMedia records.

    DELETE /api/tracks/<sync_id>
    """
    try:
        db = get_database()
        with db.get_session() as session:
            track = TrackRepository.get_track_by_sync_id(session, sync_id)
            if not track:
                raise HTTPException(status_code=404, detail="Track not found")
            session.delete(track)
            session.commit()
            return {"deleted": True, "sync_id": sync_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting track {sync_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete track")


@router.get(
    "/search",
    response_model=Union[PaginatedResponse[TrackResponseSchema], PaginatedResponse[TrackSummarySchema]],
    response_model_exclude_unset=True
)
async def search_canonical_tracks(
    title: str = Query(...),
    artist: Optional[str] = Query(None),
    limit: int = Query(10, le=100),
    detail: bool = Query(False)
):
    """Fuzzy search canonical tracks by title and optional artist substring."""
    try:
        db = get_database()
        tracks = db.search_canonical_fuzzy(title=title, artist=artist, limit=limit)
        
        if detail:
            return PaginatedResponse[TrackResponseSchema](items=tracks, count=len(tracks))
        else:
            return PaginatedResponse[TrackSummarySchema](items=tracks, count=len(tracks))
            
    except Exception as e:
        logger.error(f"Error searching tracks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search tracks")