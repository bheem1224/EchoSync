from flask import Blueprint, jsonify, request
from database.music_database import get_database
from core.models import Track
from utils.logging_config import get_logger

logger = get_logger("tracks_route")
bp = Blueprint("tracks", __name__, url_prefix="/api/tracks")

@bp.get("/")
def list_canonical_tracks():
    """List canonical tracks with pagination."""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        db = get_database()
        tracks = db.list_canonical_tracks(limit=limit, offset=offset)
        return jsonify({
            'items': [t.to_dict() for t in tracks],
            'limit': limit,
            'offset': offset,
            'count': len(tracks)
        })
    except Exception as e:
        logger.error(f"Error listing canonical tracks: {e}")
        return jsonify({'error': 'Failed to list tracks'}), 500

@bp.get("/<track_id>")
def get_canonical_track(track_id: str):
    """Fetch a canonical track by ID."""
    try:
        db = get_database()
        track = db.get_canonical_track(track_id)
        if not track:
            return jsonify({'error': 'Track not found'}), 404
        return jsonify(track.to_dict())
    except Exception as e:
        logger.error(f"Error fetching canonical track {track_id}: {e}")
        return jsonify({'error': 'Failed to fetch track'}), 500

@bp.post("/")
def upsert_canonical_track():
    """Create or update a canonical track from JSON payload."""
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({'error': 'Missing JSON payload'}), 400
        # Build Track and upsert
        track = Track.from_dict(payload)
        db = get_database()
        db.upsert_canonical_track(track)
        return jsonify(track.to_dict())
    except Exception as e:
        logger.error(f"Error upserting canonical track: {e}")
        return jsonify({'error': 'Failed to upsert track'}), 500

@bp.delete("/<track_id>")
def delete_canonical_track(track_id: str):
    """Delete a canonical track by ID."""
    try:
        db = get_database()
        deleted = db.delete_canonical_track(track_id)
        if not deleted:
            return jsonify({'error': 'Track not found'}), 404
        return jsonify({'deleted': True, 'track_id': track_id})
    except Exception as e:
        logger.error(f"Error deleting canonical track {track_id}: {e}")
        return jsonify({'error': 'Failed to delete track'}), 500

@bp.get("/search")
def search_canonical_tracks():
    """Fuzzy search canonical tracks by title and optional artist substring."""
    try:
        title = request.args.get('title')
        artist = request.args.get('artist')
        limit = int(request.args.get('limit', 10))
        if not title:
            return jsonify({'error': 'Missing title parameter'}), 400
        db = get_database()
        tracks = db.search_canonical_fuzzy(title=title, artist=artist, limit=limit)
        return jsonify({
            'query': {'title': title, 'artist': artist, 'limit': limit},
            'items': [t.to_dict() for t in tracks],
            'count': len(tracks)
        })
    except Exception as e:
        logger.error(f"Error searching canonical tracks: {e}")
        return jsonify({'error': 'Failed to search tracks'}), 500

@bp.get("/ids")
def search_canonical_by_ids():
    """Search canonical tracks by global identifiers (ISRC, MBID, AcoustID)."""
    try:
        isrc = request.args.get('isrc')
        mbid = request.args.get('mbid')  # alias for musicbrainz_recording_id
        acoustid = request.args.get('acoustid')
        db = get_database()
        tracks = db.search_canonical_by_ids(
            isrc=isrc,
            musicbrainz_recording_id=mbid,
            acoustid=acoustid,
        )
        return jsonify({
            'query': {'isrc': isrc, 'mbid': mbid, 'acoustid': acoustid},
            'items': [t.to_dict() for t in tracks],
            'count': len(tracks)
        })
    except Exception as e:
        logger.error(f"Error searching canonical tracks by IDs: {e}")
        return jsonify({'error': 'Failed to search tracks by IDs'}), 500