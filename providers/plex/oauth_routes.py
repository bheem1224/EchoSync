"""Plex OAuth routes for PIN-based authentication."""

import threading
import uuid
import time
from flask import Blueprint, request, jsonify
from utils.logging_config import get_logger

logger = get_logger("plex_oauth")

# Blueprint for Plex OAuth
oauth_bp = Blueprint('plex_oauth', __name__, url_prefix='/api/plex')

# OAuth session tracking
plex_oauth_sessions = {}  # Maps session_id to PIN login instance
plex_oauth_lock = threading.Lock()


@oauth_bp.post('/auth/start')
def start_oauth():
    """
    Start Plex OAuth flow using PIN-based authentication.
    Returns: {session_id, oauth_url, poll_url}
    """
    try:
        from plexapi.myplex import MyPlexPinLogin
        
        # Create a new OAuth PIN login session
        pin_login = MyPlexPinLogin(oauth=True)
        
        # Generate a unique session ID to track this OAuth flow
        session_id = str(uuid.uuid4())
        
        # Store the PIN login object for later polling
        with plex_oauth_lock:
            plex_oauth_sessions[session_id] = pin_login
        
        # Start the PIN login process (this gets the PIN from Plex API)
        # Timeout of 600 seconds (10 minutes) for user to authorize
        pin_login.run(timeout=600)
        
        # Get the OAuth URL (PIN code is populated after .run())
        oauth_url = pin_login.oauthUrl()
        
        logger.info(f"Plex OAuth session started: {session_id}")
        
        # Clean up old session after 15 minutes
        def cleanup_session():
            time.sleep(900)  # 15 minutes
            with plex_oauth_lock:
                if session_id in plex_oauth_sessions:
                    plex_oauth_sessions.pop(session_id, None)
                    logger.info(f"Plex OAuth session cleaned up: {session_id}")
        
        cleanup_thread = threading.Thread(target=cleanup_session, daemon=True)
        cleanup_thread.start()
        
        return jsonify({
            'session_id': session_id,
            'oauth_url': oauth_url,
            'poll_url': f'/api/plex/auth/poll/{session_id}'
        })
    except ImportError:
        logger.error("plexapi library not installed")
        return jsonify({'error': 'Plex library not available'}), 500
    except Exception as e:
        logger.error(f"Error starting Plex OAuth: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@oauth_bp.get('/auth/poll/<session_id>')
def poll_oauth(session_id: str):
    """
    Poll for Plex OAuth authorization completion.
    Returns: {completed, token?, error?}
    """
    try:
        with plex_oauth_lock:
            pin_login = plex_oauth_sessions.get(session_id)
        
        if not pin_login:
            return jsonify({'error': 'Session not found or expired'}), 404
        
        # Check if token is ready
        if getattr(pin_login, 'token', None):
            auth_token = pin_login.token
            
            # Store token (will be saved via settings API)
            # For now, just return it to the frontend
            
            # Clean up the session
            with plex_oauth_lock:
                plex_oauth_sessions.pop(session_id, None)
            
            logger.info(f"Plex OAuth completed for session: {session_id}")
            
            return jsonify({
                'completed': True,
                'token': auth_token
            })
        else:
            # Still waiting for user authorization
            return jsonify({
                'completed': False
            })
    
    except Exception as e:
        logger.error(f"Error polling Plex OAuth: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@oauth_bp.delete('/auth/cancel/<session_id>')
def cancel_oauth(session_id: str):
    """Cancel an ongoing OAuth session."""
    try:
        with plex_oauth_lock:
            pin_login = plex_oauth_sessions.pop(session_id, None)
            if pin_login:
                logger.info(f"Plex OAuth session cancelled: {session_id}")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error cancelling Plex OAuth: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
