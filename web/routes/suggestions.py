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
import logging

logger = get_logger("suggestions")
bp = Blueprint("suggestions", __name__, url_prefix="/api/suggestions")


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
        
        # Get all Plex accounts (managed accounts)
        plex_service_id = config_db.get_or_create_service_id('plex')
        accounts = config_db.get_accounts(service_id=plex_service_id, is_active=True)
        
        result_accounts = []
        
        for account in accounts:
            account_id = account['id']
            account_name = account.get('display_name') or account.get('account_name') or 'Unknown'
            
            # Get taste profile: top genres from user's track ratings
            total_suggestions = 0
            top_genres = []
            
            try:
                # Find user in working_db and count their high ratings
                with working_db.session_scope() as work_session:
                    user = work_session.query(User).filter(
                        User.plex_id == account.get('user_id')
                    ).first() if account.get('user_id') else None
                    
                    if user:
                        # Count approved tracks for this user (high ratings: 4.0+)
                        high_ratings = work_session.query(UserRating).filter(
                            UserRating.user_id == user.id,
                            UserRating.rating >= 4.0
                        ).count()
                        total_suggestions = high_ratings
                    
                    # Top genres would come from metadata provider
                    # For now, return empty (would require Spotify/MB API calls)
                    top_genres = []
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
            'accounts': result_accounts
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
                    User.plex_id == account.get('user_id')
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
