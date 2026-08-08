"""
REST API routes for the Local Metadata provider.

Purpose: acts as Echosync's outward-facing API translator so external apps
(e.g. native players, third-party tools) can connect to and query the local
music library without direct database access.

All endpoints:
  • Return standardised, paginated JSON envelopes
  • Include ``stream_url`` in every track payload so external clients can
    begin playback immediately without a second lookup
  • Query the MusicDatabase directly (single source of truth)

Base URL prefix: /api/external
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import contains_eager
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

from database.music_database import Album, Artist, Track, get_database
from core.tiered_logger import get_logger

logger = get_logger("local_metadata")

router = APIRouter(prefix="/api/v1/system/local_metadata", tags=["Local Metadata"])

_DEFAULT_PER_PAGE = 50
_MAX_PER_PAGE = 200

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ExternalTrack(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: Optional[str] = None
    artist: Optional[str] = None
    artist_id: Optional[int] = None
    album: Optional[str] = None
    album_id: Optional[int] = None
    duration: Optional[int] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    bitrate: Optional[int] = None
    file_format: Optional[str] = None
    isrc: Optional[str] = None
    musicbrainz_id: Optional[str] = None
    stream_url: str

class ExternalTrackList(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    items: List[ExternalTrack]

class ExternalArtist(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: Optional[str] = None
    sort_name: Optional[str] = None
    image_url: Optional[str] = None

class ExternalArtistList(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    items: List[ExternalArtist]

class ExternalAlbum(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: Optional[str] = None
    artist_id: Optional[int] = None
    artist: Optional[str] = None
    cover_image_url: Optional[str] = None
    year: Optional[int] = None
    album_type: Optional[str] = None

class ExternalAlbumList(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    items: List[ExternalAlbum]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _track_to_dict(track: Track) -> dict:
    """Serialise a Track ORM row to the standard external-API payload.

    The ``stream_url`` field is *required by specification*: it gives
    external clients a ready-to-use URL so they can begin playback without
    any additional lookup.
    """
    first_media = track.media[0] if getattr(track, "media", None) else None
    return {
        "id":             track.id,
        "title":          track.title,
        "artist":         track.artist.name if getattr(track, "artist", None) else None,
        "artist_id":      track.artist_id,
        "album":          track.album.title if getattr(track, "album", None) else None,
        "album_id":       track.album_id,
        "duration":       track.duration,           # milliseconds
        "track_number":   track.track_number,
        "disc_number":    track.disc_number,
        "bitrate":        first_media.bitrate if first_media else getattr(track, "bitrate", None),
        "file_format":    first_media.file_format if first_media else getattr(track, "file_format", None),
        "isrc":           track.isrc,
        "musicbrainz_id": track.musicbrainz_id,
        # CRITICAL: direct stream URL so external apps can play immediately
        "stream_url":     f"/api/library/stream/{track.id}",
    }


# ---------------------------------------------------------------------------
# Tracks
# ---------------------------------------------------------------------------

@router.get("/library/tracks", response_model=ExternalTrackList)
def list_tracks(
    page: int = Query(1, ge=1),
    per_page: int = Query(_DEFAULT_PER_PAGE, ge=1, le=_MAX_PER_PAGE),
    artist_id: Optional[int] = None,
    album_id: Optional[int] = None,
    q: Optional[str] = None
):
    """Paginated list of tracks in the local library."""
    db = get_database()
    with db.session_scope() as session:
        query = (
            session.query(Track)
            .join(Artist, Track.artist_id == Artist.id)
            .outerjoin(Album, Track.album_id == Album.id)
            .options(
                contains_eager(Track.artist),
                contains_eager(Track.album),
            )
        )

        if artist_id is not None:
            query = query.filter(Track.artist_id == artist_id)
        if album_id is not None:
            query = query.filter(Track.album_id == album_id)
        if q:
            query = query.filter(Track.title.ilike(f"%{q.strip()}%"))

        query = query.order_by(
            Artist.name,
            Album.title,
            Track.disc_number,
            Track.track_number,
        )

        total = query.count()
        rows  = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "page":        page,
            "per_page":    per_page,
            "total":       total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
            "items":       [_track_to_dict(t) for t in rows],
        }


@router.get("/library/tracks/{track_id}", response_model=ExternalTrack)
def get_track(track_id: int):
    """Return a single track by ID, including ``stream_url``.

    Returns 404 if the track is not found in the local library.
    """
    db = get_database()
    with db.session_scope() as session:
        track = (
            session.query(Track)
            .join(Artist, Track.artist_id == Artist.id)
            .outerjoin(Album, Track.album_id == Album.id)
            .options(
                contains_eager(Track.artist),
                contains_eager(Track.album),
            )
            .filter(Track.id == track_id)
            .first()
        )
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        return _track_to_dict(track)


# ---------------------------------------------------------------------------
# Artists
# ---------------------------------------------------------------------------

@router.get("/library/artists", response_model=ExternalArtistList)
def list_artists(
    page: int = Query(1, ge=1),
    per_page: int = Query(_DEFAULT_PER_PAGE, ge=1, le=_MAX_PER_PAGE),
    q: Optional[str] = None
):
    """Paginated list of artists in the local library."""
    db = get_database()
    with db.session_scope() as session:
        query = session.query(Artist)
        if q:
            query = query.filter(Artist.name.ilike(f"%{q.strip()}%"))
        query = query.order_by(Artist.name)

        total = query.count()
        rows  = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "page":        page,
            "per_page":    per_page,
            "total":       total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
            "items": [
                {
                    "id":        a.id,
                    "name":      a.name,
                    "sort_name": a.sort_name,
                    "image_url": a.image_url,
                }
                for a in rows
            ],
        }


# ---------------------------------------------------------------------------
# Albums
# ---------------------------------------------------------------------------

@router.get("/library/albums", response_model=ExternalAlbumList)
def list_albums(
    page: int = Query(1, ge=1),
    per_page: int = Query(_DEFAULT_PER_PAGE, ge=1, le=_MAX_PER_PAGE),
    artist_id: Optional[int] = None,
    q: Optional[str] = None
):
    """Paginated list of albums in the local library."""
    db = get_database()
    with db.session_scope() as session:
        query = (
            session.query(Album)
            .join(Artist, Album.artist_id == Artist.id)
            .options(contains_eager(Album.artist))
        )
        if artist_id is not None:
            query = query.filter(Album.artist_id == artist_id)
        if q:
            query = query.filter(Album.title.ilike(f"%{q.strip()}%"))
        query = query.order_by(Artist.name, Album.title)

        total = query.count()
        rows  = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "page":        page,
            "per_page":    per_page,
            "total":       total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
            "items": [
                {
                    "id":              al.id,
                    "title":           al.title,
                    "artist_id":       al.artist_id,
                    "artist":          al.artist.name if getattr(al, "artist", None) else None,
                    "cover_image_url": al.cover_image_url,
                    "year":            al.release_date.year if getattr(al, "release_date", None) else None,
                    "album_type":      al.album_type,
                }
                for al in rows
            ],
        }
