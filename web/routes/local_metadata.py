"""
REST API routes for the Local Metadata provider.

Purpose: acts as SoulSync's outward-facing API translator so external apps
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

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import contains_eager

from database.music_database import Album, Artist, Track, get_database
from core.tiered_logger import get_logger

logger = get_logger("local_metadata")

bp = Blueprint("local_metadata", __name__, url_prefix="/api/external")

_DEFAULT_PER_PAGE = 50
_MAX_PER_PAGE = 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_page_params() -> tuple:
    """Parse and clamp ``?page=`` / ``?per_page=`` query parameters."""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = min(
            _MAX_PER_PAGE,
            max(1, int(request.args.get("per_page", _DEFAULT_PER_PAGE))),
        )
    except (TypeError, ValueError):
        per_page = _DEFAULT_PER_PAGE
    return page, per_page


def _track_to_dict(track: Track) -> dict:
    """Serialise a Track ORM row to the standard external-API payload.

    The ``stream_url`` field is *required by specification*: it gives
    external clients a ready-to-use URL so they can begin playback without
    any additional lookup.
    """
    return {
        "id":             track.id,
        "title":          track.title,
        "artist":         track.artist.name if track.artist else None,
        "artist_id":      track.artist_id,
        "album":          track.album.title if track.album else None,
        "album_id":       track.album_id,
        "duration":       track.duration,           # milliseconds
        "track_number":   track.track_number,
        "disc_number":    track.disc_number,
        "bitrate":        track.bitrate,
        "file_format":    track.file_format,
        "isrc":           track.isrc,
        "musicbrainz_id": track.musicbrainz_id,
        # CRITICAL: direct stream URL so external apps can play immediately
        "stream_url":     f"/api/library/stream/{track.id}",
    }


# ---------------------------------------------------------------------------
# Tracks
# ---------------------------------------------------------------------------

@bp.get("/library/tracks")
def list_tracks():
    """Paginated list of tracks in the local library.

    Query params:
        page      (int, default 1)
        per_page  (int, default 50, max 200)
        artist_id (int, optional) — filter to a specific artist
        album_id  (int, optional) — filter to a specific album
        q         (str, optional) — title substring search

    Response envelope::

        {
          "page": 1,
          "per_page": 50,
          "total": 1234,
          "total_pages": 25,
          "items": [ { ...track, "stream_url": "/api/library/stream/7" }, ... ]
        }
    """
    page, per_page = _parse_page_params()
    artist_id = request.args.get("artist_id", type=int)
    album_id  = request.args.get("album_id",  type=int)
    q         = request.args.get("q", "").strip()

    db = get_database()
    with db.session_scope() as session:
        # contains_eager populates track.artist and track.album in-memory from
        # the join rows, so the relationships are accessible after session close.
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
            query = query.filter(Track.title.ilike(f"%{q}%"))

        query = query.order_by(
            Artist.name,
            Album.title,
            Track.disc_number,
            Track.track_number,
        )

        total = query.count()
        rows  = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "page":        page,
            "per_page":    per_page,
            "total":       total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
            "items":       [_track_to_dict(t) for t in rows],
        })


@bp.get("/library/tracks/<int:track_id>")
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
            return jsonify({"error": "Track not found"}), 404
        return jsonify(_track_to_dict(track))


# ---------------------------------------------------------------------------
# Artists
# ---------------------------------------------------------------------------

@bp.get("/library/artists")
def list_artists():
    """Paginated list of artists in the local library.

    Query params:
        page     (int, default 1)
        per_page (int, default 50, max 200)
        q        (str, optional) — name substring search
    """
    page, per_page = _parse_page_params()
    q = request.args.get("q", "").strip()

    db = get_database()
    with db.session_scope() as session:
        query = session.query(Artist)
        if q:
            query = query.filter(Artist.name.ilike(f"%{q}%"))
        query = query.order_by(Artist.name)

        total = query.count()
        rows  = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
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
        })


# ---------------------------------------------------------------------------
# Albums
# ---------------------------------------------------------------------------

@bp.get("/library/albums")
def list_albums():
    """Paginated list of albums in the local library.

    Query params:
        page      (int, default 1)
        per_page  (int, default 50, max 200)
        artist_id (int, optional) — filter to a specific artist
        q         (str, optional) — title substring search
    """
    page, per_page = _parse_page_params()
    artist_id = request.args.get("artist_id", type=int)
    q         = request.args.get("q", "").strip()

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
            query = query.filter(Album.title.ilike(f"%{q}%"))
        query = query.order_by(Artist.name, Album.title)

        total = query.count()
        rows  = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "page":        page,
            "per_page":    per_page,
            "total":       total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
            "items": [
                {
                    "id":              al.id,
                    "title":           al.title,
                    "artist_id":       al.artist_id,
                    "artist":          al.artist.name if al.artist else None,
                    "cover_image_url": al.cover_image_url,
                    "year":            al.release_date.year if al.release_date else None,
                    "album_type":      al.album_type,
                }
                for al in rows
            ],
        })
