"""
Tracks API routes (web/routes/tracks.py).

All track endpoints use sync_id (canonical URN) as the routing key.
Responses include media_ids for UUID-based media telemetry lookups via /api/media/.
Physical file telemetry is NOT nested in track responses — use /api/media/<media_id>.
"""
from flask import Blueprint, jsonify, request
from database.music_database import get_database, Track, LocalMedia
from core.tiered_logger import get_logger
from core.database.repositories.track_repo import TrackRepository

logger = get_logger("tracks_route")
bp = Blueprint("tracks", __name__, url_prefix="/api/tracks")

# Physical-only fields that must never be PATCH'd through the track endpoint
_PHYSICAL_FIELDS = frozenset({
    "file_path", "file_format", "bitrate", "sample_rate",
    "bit_depth", "file_size_bytes", "inode", "mtime",
})


def _track_to_dict(track: Track) -> dict:
    """Serialize a Track ORM object to a clean JSON-safe dict with media_ids."""
    media_ids = [m.media_id for m in (track.media_files or []) if m.media_id]
    return {
        "sync_id": track.sync_id,
        "title": track.title,
        "normalized_title": track.normalized_title,
        "sort_title": track.sort_title,
        "edition": track.edition,
        "duration": track.duration,
        "track_number": track.track_number,
        "disc_number": track.disc_number,
        "musicbrainz_id": track.musicbrainz_id,
        "isrc": track.isrc,
        "artist_id": track.artist_id,
        "album_id": track.album_id,
        "added_at": track.added_at.isoformat() if track.added_at else None,
        "metadata_status": track.metadata_status,
        "global_rating": track.global_rating,
        # 2-Model: only expose UUIDs — use /api/media/ for full telemetry
        "media_ids": media_ids,
        "media_count": len(media_ids),
    }


@bp.get("/")
def list_canonical_tracks():
    """List canonical tracks with pagination."""
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 500))
        offset = max(0, int(request.args.get("offset", 0)))
        db = get_database()
        with db.get_session() as session:
            tracks = (
                session.query(Track)
                .order_by(Track.title)
                .offset(offset)
                .limit(limit)
                .all()
            )
            return jsonify({
                "items": [_track_to_dict(t) for t in tracks],
                "limit": limit,
                "offset": offset,
                "count": len(tracks),
            })
    except Exception as e:
        logger.error(f"Error listing canonical tracks: {e}", exc_info=True)
        return jsonify({"error": "Failed to list tracks"}), 500


@bp.get("/<sync_id>")
def get_canonical_track(sync_id: str):
    """
    Fetch a canonical track by sync_id.

    GET /api/tracks/<sync_id>
    Returns logical metadata + media_ids array.
    """
    try:
        db = get_database()
        with db.get_session() as session:
            track = TrackRepository.get_track_by_sync_id(session, sync_id)
            if not track:
                return jsonify({"error": "Track not found"}), 404
            return jsonify(_track_to_dict(track))
    except Exception as e:
        logger.error(f"Error fetching canonical track {sync_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch track"}), 500


@bp.patch("/<sync_id>")
def patch_canonical_track(sync_id: str):
    """
    Partially update a track's logical metadata by sync_id.

    PATCH /api/tracks/<sync_id>
    Rejects any attempt to patch physical file properties.
    """
    try:
        payload = request.get_json(force=True) or {}
        rejected = [k for k in payload if k in _PHYSICAL_FIELDS]
        if rejected:
            return jsonify({
                "error": "Cannot PATCH physical file properties through track endpoint",
                "rejected_fields": rejected,
                "hint": "Use /api/media/<media_id> for physical telemetry updates.",
            }), 400

        db = get_database()
        with db.get_session() as session:
            track = TrackRepository.get_track_by_sync_id(session, sync_id)
            if not track:
                return jsonify({"error": "Track not found"}), 404

            allowed = {"title", "track_number", "disc_number", "musicbrainz_id", "isrc", "global_rating"}
            for key, val in payload.items():
                if key in allowed and hasattr(track, key):
                    setattr(track, key, val)
            session.commit()
            session.refresh(track)
            return jsonify(_track_to_dict(track))
    except Exception as e:
        logger.error(f"Error patching track {sync_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to patch track"}), 500


@bp.delete("/<sync_id>")
def delete_canonical_track(sync_id: str):
    """
    Delete a track and cascade-delete its associated LocalMedia records.

    DELETE /api/tracks/<sync_id>
    """
    try:
        db = get_database()
        with db.get_session() as session:
            track = TrackRepository.get_track_by_sync_id(session, sync_id)
            if not track:
                return jsonify({"error": "Track not found"}), 404
            session.delete(track)
            session.commit()
            return jsonify({"deleted": True, "sync_id": sync_id})
    except Exception as e:
        logger.error(f"Error deleting track {sync_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete track"}), 500


@bp.get("/search")
def search_canonical_tracks():
    """Fuzzy search canonical tracks by title and optional artist substring."""
    try:
        title = request.args.get("title")
        artist = request.args.get("artist")
        limit = min(int(request.args.get("limit", 10)), 100)
        if not title:
            return jsonify({"error": "Missing title parameter"}), 400
        db = get_database()
        tracks = db.search_canonical_fuzzy(title=title, artist=artist, limit=limit)
        return jsonify({
            "items": [_track_to_dict(t) for t in tracks],
            "count": len(tracks),
        })
    except Exception as e:
        logger.error(f"Error searching tracks: {e}", exc_info=True)
        return jsonify({"error": "Failed to search tracks"}), 500