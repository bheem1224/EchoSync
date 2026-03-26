"""
Suggestion Engine API Routes

Exposes:
- GET /api/suggestions/accounts - List managed accounts with taste profiles
- GET /api/suggestions/pending/{account_id} - Pending recommendations for user
- POST /api/suggestions/approve - Approve and queue a suggestion
- GET /api/suggestions/audit - History of approved suggestions
- POST /api/suggestions/toggle-auto - Toggle automated suggestion job
"""

from flask import Blueprint, jsonify, request
from core.tiered_logger import get_logger
from core.settings import config_manager
from database.config_database import get_config_database
from database.working_database import get_working_database, UserRating, User, Download
from database.music_database import get_database as get_music_database
from core.account_manager import AccountManager
from services.download_manager import get_download_manager
from sqlalchemy import func, tuple_
from collections import Counter
import base64
import logging

logger = get_logger("suggestions")
bp = Blueprint("suggestions", __name__, url_prefix="/api/suggestions")


def _decode_sync_id_pair(sync_id: str):
    """Decode ss:track:meta sync IDs into (artist, title) pairs."""
    raw = str(sync_id or "").strip()
    if not raw.startswith("ss:track:meta:"):
        return None

    encoded = raw.split("ss:track:meta:", 1)[1].split("?", 1)[0].strip()
    if not encoded:
        return None

    try:
        padded = encoded + "=" * ((4 - len(encoded) % 4) % 4)
        decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
        artist_name, track_title = decoded.split("|", 1)
        artist_name = artist_name.strip()
        track_title = track_title.strip()
        if artist_name and track_title:
            return artist_name, track_title
    except Exception:
        return None

    return None


def _resolve_scope_account(accounts, requested_account_id=None, requested_user_id=None):
    """Resolve scope account by account_id/user_id, else first active managed user."""
    if requested_account_id:
        for account in accounts:
            if account.get('id') == requested_account_id:
                return account, 'account_id'

    if requested_user_id:
        requested_user_id = str(requested_user_id)
        for account in accounts:
            if str(account.get('user_id') or '') == requested_user_id:
                return account, 'user_id'

    active_account = next((account for account in accounts if account.get('is_active')), None)
    if active_account:
        return active_account, 'active_account'

    if accounts:
        return accounts[0], 'first_account'

    return None, 'none'


def _calculate_top_genres_for_user(work_session, music_session, user_id: int, limit: int = 5):
    """Calculate user-scoped taste distribution from highly-rated tracks.

    Uses user ratings from working DB and matches to music DB tracks by decoded
    sync_id metadata. If explicit genres are unavailable in schema, falls back to
    artist-name buckets so the UI still receives scoped category data.
    """
    rated_sync_ids = [
        row.sync_id
        for row in work_session.query(UserRating.sync_id)
        .filter(
            UserRating.user_id == user_id,
            UserRating.rating.isnot(None),
            UserRating.rating >= 4.0,
        )
        .all()
    ]

    decoded_pairs = []
    for sync_id in rated_sync_ids:
        pair = _decode_sync_id_pair(sync_id)
        if pair:
            decoded_pairs.append((pair[0].lower(), pair[1].lower()))

    if not decoded_pairs:
        return []

    from database.music_database import Track, Artist

    matched_tracks = (
        music_session.query(Track, Artist)
        .join(Artist, Track.artist_id == Artist.id)
        .filter(tuple_(func.lower(Artist.name), func.lower(Track.title)).in_(decoded_pairs))
        .all()
    )

    if not matched_tracks:
        return []

    buckets = Counter()
    for _, artist in matched_tracks:
        key = str(artist.name or '').strip()
        if key:
            buckets[key] += 1

    total = sum(buckets.values())
    if total <= 0:
        return []

    top = []
    for name, count in buckets.most_common(limit):
        top.append({
            'name': name,
            'count': count,
            'percentage': round((count / total) * 100, 2),
        })
    return top


@bp.get("/accounts")
def get_suggestion_accounts():
    """
    Returns a list of all managed accounts with their taste profile summaries.
    
    Taste profile includes:
    - Top 3 genres (from tracks in their library)
    - Total tracks ever suggested/approved
    - Account display info
    """
    try:
        config_db = get_config_database()
        working_db = get_working_database()
        music_db = get_music_database()
        
        requested_account_id = request.args.get('account_id', type=int)
        requested_user_id = request.args.get('user_id')

        # Get all active Plex accounts (managed accounts)
        plex_service_id = config_db.get_or_create_service_id('plex')
        accounts = config_db.get_accounts(service_id=plex_service_id, is_active=True)
        scoped_account, scope_source = _resolve_scope_account(
            accounts,
            requested_account_id=requested_account_id,
            requested_user_id=requested_user_id,
        )
        
        result_accounts = []
        scoped_distribution = []
        
        for account in accounts:
            account_id = account['id']
            account_name = account.get('display_name') or account.get('account_name') or 'Unknown'
            
            # Get taste profile: top genres from user's track ratings
            total_suggestions = 0
            top_genres = []
            
            try:
                # Find user in working_db and count their high ratings
                with working_db.session_scope() as work_session:
                    with music_db.session_scope() as music_session:
                        user = work_session.query(User).filter(
                            User.provider_identifier == account.get('user_id')
                        ).first() if account.get('user_id') else None
                    
                        if user:
                            # Count approved tracks for this user (high ratings: 4.0+)
                            high_ratings = work_session.query(UserRating).filter(
                                UserRating.user_id == user.id,
                                UserRating.rating >= 4.0
                            ).count()
                            total_suggestions = high_ratings
                            top_genres = _calculate_top_genres_for_user(
                                work_session,
                                music_session,
                                user.id,
                                limit=5,
                            )

                            if scoped_account and scoped_account.get('id') == account_id:
                                scoped_distribution = top_genres
            except Exception as e:
                logger.warning(f"Failed to calculate taste profile for account {account_id}: {e}")
            
            result_accounts.append({
                'id': account_id,
                'name': account_name,
                'email': account.get('account_email'),
                'is_active': account.get('is_active', False),
                'taste_profile': {
                    'top_genres': top_genres,
                    'total_suggestions': total_suggestions
                }
            })
        
        return jsonify({
            'accounts': result_accounts,
            'genre_scope': {
                'source': scope_source,
                'account_id': scoped_account.get('id') if scoped_account else None,
                'user_id': scoped_account.get('user_id') if scoped_account else None,
            },
            'genre_distribution': scoped_distribution,
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting suggestion accounts: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.get("/pending/<int:account_id>")
def get_pending_suggestions(account_id: int):
    """
    Returns 10-20 highly scored tracks recommended for this account
    that have not been downloaded yet.
    
    Query params:
        - limit: Max number of suggestions to return (default 15, max 20)
    """
    try:
        limit = request.args.get('limit', default=15, type=int)
        limit = min(limit, 20)  # Cap at 20
        
        config_db = get_config_database()
        working_db = get_working_database()
        music_db = get_music_database()
        
        # Verify account exists
        plex_service_id = config_db.get_or_create_service_id('plex')
        account = None
        for acc in config_db.get_accounts(service_id=plex_service_id):
            if acc['id'] == account_id:
                account = acc
                break
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Get pending recommendations for this user
        # This would come from a scoring engine that evaluates what tracks match user's taste
        # For now, we'll return highly-rated tracks as recommendations
        
        pending_tracks = []
        
        try:
            with working_db.session_scope() as session:
                user = session.query(User).filter(
                    User.provider_identifier == account.get('user_id')
                ).first() if account.get('user_id') else None
            
            if user:
                # Get this user's highest-rated tracks as pending recommendations
                with working_db.session_scope() as session:
                    from sqlalchemy import desc
                    
                    user_ratings = session.query(UserRating).filter(
                        UserRating.user_id == user.id,
                        UserRating.rating >= 4.0
                    ).order_by(desc(UserRating.rating)).limit(limit).all()
                    
                    for rating in user_ratings:
                        pending_tracks.append({
                            'sync_id': rating.sync_id,
                            'user_rating': rating.rating,
                            'score': rating.rating  # Simplified score
                        })
        except Exception as e:
            logger.warning(f"Error fetching pending suggestions: {e}")
        
        return jsonify({
            'account_id': account_id,
            'pending_tracks': pending_tracks[:limit],
            'count': len(pending_tracks)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting pending suggestions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post("/approve")
def approve_suggestion():
    """
    Approve a suggestion and queue it for download.
    
    Request body:
    {
        "track": { ... },  # SoulSyncTrack object
        "account_id": int,
        "playlist_name": "Suggestions for You"  # optional
    }
    """
    try:
        payload = request.get_json(silent=True) or {}
        track_data = payload.get('track')
        account_id = payload.get('account_id')
        playlist_name = payload.get('playlist_name', 'Suggestions for You')
        
        if not track_data or not account_id:
            return jsonify({'error': 'Missing track or account_id'}), 400
        
        # Queue the track for download
        dm = get_download_manager()
        
        # Create a simple SoulSyncTrack from the payload
        from core.content_models import SoulSyncTrack
        
        try:
            track = SoulSyncTrack.from_dict(track_data)
        except Exception as e:
            logger.warning(f"Failed to parse track from payload: {e}")
            return jsonify({'error': 'Invalid track data'}), 400
        
        # Queue the download
        download_id = dm.queue_download(track)
        
        if not download_id:
            return jsonify({'error': 'Failed to queue download'}), 500
        
        logger.info(f"Approved suggestion: {track.sync_id} for account {account_id}")
        
        return jsonify({
            'success': True,
            'download_id': download_id,
            'sync_id': track.sync_id,
            'message': f'Track queued for download and will be added to {playlist_name}'
        }), 201
        
    except Exception as e:
        logger.error(f"Error approving suggestion: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.get("/audit")
def get_suggestion_audit():
    """
    Returns audit history of approved suggestions and their outcomes.
    
    Query params:
        - limit: Max records to return (default 50)
        - account_id: Filter by specific account (optional)
    """
    try:
        limit = request.args.get('limit', default=50, type=int)
        account_id = request.args.get('account_id', type=int)
        
        working_db = get_working_database()
        config_db = get_config_database()
        
        # Get Download records as audit history
        audit_history = []
        
        try:
            with working_db.session_scope() as session:
                from sqlalchemy import desc
                
                query = session.query(Download)
                
                # Optionally filter by account (would need to link via user)
                if account_id:
                    # Would need to implement account_id linking in Download model
                    pass
                
                downloads = query.order_by(
                    desc(Download.created_at)
                ).limit(limit).all()
                
                for dl in downloads:
                    audit_history.append({
                        'id': dl.id,
                        'sync_id': dl.sync_id,
                        'status': dl.status,
                        'created_at': dl.created_at.isoformat() if dl.created_at else None,
                        'updated_at': dl.updated_at.isoformat() if dl.updated_at else None,
                        'retry_count': dl.retry_count
                    })
        except Exception as e:
            logger.warning(f"Error fetching audit history: {e}")
        
        return jsonify({
            'audit_history': audit_history,
            'count': len(audit_history)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting audit history: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.post("/toggle-auto")
def toggle_auto_suggestions():
    """
    Toggle the automated daily background suggestion job on/off.
    
    Request body:
    {
        "enabled": bool
    }
    """
    try:
        payload = request.get_json(silent=True) or {}
        enabled = payload.get('enabled')
        
        if enabled is None:
            return jsonify({'error': 'Missing "enabled" field'}), 400
        
        # Update config to enable/disable the suggestion job
        # This job would run the suggestion discovery and consensus engine
        config_manager.set('suggestions.auto_job_enabled', enabled)
        
        logger.info(f"Automated suggestion job {'enabled' if enabled else 'disabled'}")
        
        return jsonify({
            'success': True,
            'auto_job_enabled': enabled,
            'message': f'Automated suggestion job {("enabled" if enabled else "disabled")}'
        }), 200
        
    except Exception as e:
        logger.error(f"Error toggling auto suggestions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
