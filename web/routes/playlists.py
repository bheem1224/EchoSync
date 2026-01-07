from flask import Blueprint, jsonify, request
from web.services.sync_service import SyncAdapter
from core.personalized_playlists import get_personalized_playlists_service
from database.music_database import MusicDatabase
from utils.logging_config import get_logger
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import ScoringProfile
from core.matching_engine.soul_sync_track import SoulSyncTrack

logger = get_logger("playlists_api")
bp = Blueprint("playlists", __name__, url_prefix="/api/playlists")

@bp.get("/")
def list_playlists():
    # Placeholder: surface playlists via provider adapters (future)
    return jsonify({"items": [], "total": 0}), 200

@bp.post("/analyze")
def analyze_playlists():
    """Analyze playlists: fetch real tracks from source provider and check against database using WeightedMatchingEngine."""
    payload = request.get_json(silent=True) or {}
    source = payload.get("source")
    target = payload.get("target")
    playlists = payload.get("playlists") or []
    quality_profile = payload.get("quality_profile", "Auto")

    if not source:
        return jsonify({"error": "source provider required"}), 400
    
    if not playlists:
        return jsonify({"error": "playlists list required"}), 400

    try:
        from core.provider_registry import ProviderRegistry
        from database.music_database import MusicDatabase
        
        # Get source provider instance
        try:
            # For multi-account providers (Spotify, Tidal), get the first account
            if source in ['spotify', 'tidal']:
                from sdk.storage_service import get_storage_service
                storage = get_storage_service()
                accounts = storage.list_accounts(source)
                
                if not accounts or len(accounts) == 0:
                    return jsonify({"error": f"No {source.title()} accounts configured. Please add an account in Settings."}), 400
                
                account_id = accounts[0]['id']
                
                if source == 'spotify':
                    from providers.spotify.client import SpotifyClient
                    source_provider = SpotifyClient(account_id=account_id)
                elif source == 'tidal':
                    from providers.tidal.client import TidalClient
                    source_provider = TidalClient(account_id=str(account_id))
            else:
                source_provider = ProviderRegistry.create_instance(source)
        except ValueError as e:
            return jsonify({"error": f"Provider {source} is disabled or not available"}), 400
        
        # Check if provider has playlist support
        if not hasattr(source_provider, 'get_playlist_tracks'):
            return jsonify({"error": f"Provider {source} does not support playlist fetching"}), 400
        
        # Initialize database for track lookups
        db = MusicDatabase()
        
        # Initialize matching engine with EXACT_SYNC profile
        # Use EXACT_SYNC because we need high-confidence text/duration matching
        # without relying on fingerprints (Spotify metadata vs Plex metadata comparison)
        from core.matching_engine.scoring_profile import ExactSyncProfile
        profile = ExactSyncProfile()
        matching_engine = WeightedMatchingEngine(profile)
        
        all_tracks = []
        found_count = 0
        missing_count = 0
        
        # Process each playlist
        for playlist_info in playlists:
            playlist_id = playlist_info.get("id")
            playlist_name = playlist_info.get("name", "Unknown Playlist")
            
            if not playlist_id:
                logger.warning(f"Skipping playlist without id: {playlist_name}")
                continue
            
            try:
                # Fetch actual tracks from provider - now returns List[SoulSyncTrack]
                logger.info(f"Fetching tracks for playlist: {playlist_name} (id: {playlist_id})")
                source_tracks = source_provider.get_playlist_tracks(playlist_id)
                
                # Check each track against database using matching engine
                for source_track in source_tracks:
                    # source_track is now SoulSyncTrack from provider (Spotify, Plex, etc.)
                    track_title = source_track.title
                    track_artist = source_track.artist
                    track_album = source_track.album or ''
                    track_duration = source_track.duration_ms
                    track_isrc = source_track.isrc
                    
                    # Search database for matching tracks
                    library_match = "Not Found"
                    best_score = 0
                    try:
                        # Get all candidates from database with similar title/artist
                        conn = db._get_connection()
                        cursor = conn.cursor()
                        
                        # Quick text search for candidates (artist + title), include ISRC
                        cursor.execute("""
                            SELECT t.id, t.title, t.duration, a.name as artist_name, a.id as artist_id, t.isrc
                            FROM tracks t
                            JOIN artists a ON t.artist_id = a.id
                            WHERE LOWER(a.name) LIKE LOWER(?)
                            OR LOWER(t.title) LIKE LOWER(?)
                            LIMIT 20
                        """, (f"%{track_artist}%", f"%{track_title}%"))
                        
                        candidates = cursor.fetchall()
                        conn.close()
                        
                        # Score each candidate using matching engine
                        best_match = None
                        for candidate_row in candidates:
                            candidate_track = SoulSyncTrack(
                                title=candidate_row[1],
                                artist=candidate_row[3],
                                duration_ms=candidate_row[2] if candidate_row[2] else 0,
                                isrc=candidate_row[5] if len(candidate_row) > 5 else None
                            )
                            
                            # Calculate match score
                            result = matching_engine.calculate_match(source_track, candidate_track)
                            
                            logger.debug(f"Match score for '{track_title}' vs '{candidate_track.title}': {result.confidence_score}")
                            
                            if result.confidence_score > best_score:
                                best_score = result.confidence_score
                                best_match = (candidate_row[0], result)
                        
                        # Determine result based on best score
                        if best_score >= 85:  # High confidence threshold
                            library_match = "Found"
                            found_count += 1
                        elif best_score >= 70:  # Fuzzy match threshold
                            library_match = f"Found (score: {int(best_score)}%)"
                            found_count += 1
                        else:
                            library_match = "Not Found"
                            missing_count += 1
                        
                        if best_match:
                            logger.info(f"Matched '{track_title}' with database track (score: {best_score:.0f}%)")
                            
                    except Exception as e:
                        logger.error(f"Error searching for track '{track_title}' by '{track_artist}': {e}", exc_info=True)
                        missing_count += 1
                    
                    # Format duration
                    duration_str = "–"
                    if track_duration:
                        mins = track_duration // 60000
                        secs = (track_duration % 60000) // 1000
                        duration_str = f"{mins}:{secs:02d}"
                    
                    all_tracks.append({
                        "playlist": playlist_name,
                        "title": track_title,
                        "artist": track_artist,
                        "album": track_album,
                        "duration": duration_str,
                        "library_match": library_match,
                        "download_status": "-"
                    })
                    
            except Exception as e:
                logger.error(f"Error fetching tracks for playlist {playlist_name}: {e}", exc_info=True)
                # Add error placeholder
                all_tracks.append({
                    "playlist": playlist_name,
                    "title": f"Error: {str(e)}",
                    "artist": "–",
                    "album": "–",
                    "duration": "–",
                    "library_match": "Error",
                    "download_status": "-"
                })
        
        total_tracks = len(all_tracks)
        
        return jsonify({
            "summary": {
                "total_tracks": total_tracks,
                "found_in_library": found_count,
                "missing_tracks": missing_count,
                "downloaded": 0,
                "quality_profile": quality_profile
            },
            "tracks": all_tracks
        }), 200
        
    except Exception as e:
        logger.error(f"Error analyzing playlists: {e}", exc_info=True)
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@bp.post("/sync")
def trigger_sync():
    payload = request.get_json(silent=True) or {}
    adapter = SyncAdapter()
    result = adapter.trigger_sync(payload)
    # Echo requested download + quality so UI can display
    result.update({
        "download_missing": bool(payload.get("download_missing")),
        "quality_profile": payload.get("quality_profile")
    })
    status = 202 if result.get("accepted") else 400
    return jsonify(result), status


# ========================================
# PERSONALIZED PLAYLISTS ENDPOINTS
# ========================================

@bp.get("/genres")
def get_available_genres():
    """Get list of available genres from discovery pool"""
    try:
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        genres = service.get_available_genres()
        return jsonify({
            "genres": genres,
            "total": len(genres)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching genres: {e}")
        return jsonify({"error": "Failed to fetch genres"}), 500


@bp.get("/genre/<genre_name>")
def get_genre_playlist(genre_name):
    """Get playlist for a specific genre"""
    try:
        limit = request.args.get("limit", 50, type=int)
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_genre_playlist(genre_name, limit=limit)
        return jsonify({
            "genre": genre_name,
            "tracks": tracks,
            "total": len(tracks)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching genre playlist for {genre_name}: {e}")
        return jsonify({"error": "Failed to fetch genre playlist"}), 500


@bp.get("/decade/<int:decade>")
def get_decade_playlist(decade):
    """Get playlist for a specific decade"""
    try:
        limit = request.args.get("limit", 100, type=int)
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_decade_playlist(decade, limit=limit)
        return jsonify({
            "decade": decade,
            "tracks": tracks,
            "total": len(tracks)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching decade playlist for {decade}s: {e}")
        return jsonify({"error": "Failed to fetch decade playlist"}), 500


@bp.get("/popular-picks")
def get_popular_picks():
    """Get high-popularity tracks from discovery pool"""
    try:
        limit = request.args.get("limit", 50, type=int)
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_popular_picks(limit=limit)
        return jsonify({
            "name": "Popular Picks",
            "tracks": tracks,
            "total": len(tracks)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching popular picks: {e}")
        return jsonify({"error": "Failed to fetch popular picks"}), 500


@bp.get("/hidden-gems")
def get_hidden_gems():
    """Get low-popularity underground tracks from discovery pool"""
    try:
        limit = request.args.get("limit", 50, type=int)
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_hidden_gems(limit=limit)
        return jsonify({
            "name": "Hidden Gems",
            "tracks": tracks,
            "total": len(tracks)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching hidden gems: {e}")
        return jsonify({"error": "Failed to fetch hidden gems"}), 500


@bp.get("/discovery-shuffle")
def get_discovery_shuffle():
    """Get random tracks from discovery pool"""
    try:
        limit = request.args.get("limit", 50, type=int)
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_discovery_shuffle(limit=limit)
        return jsonify({
            "name": "Discovery Shuffle",
            "tracks": tracks,
            "total": len(tracks)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching discovery shuffle: {e}")
        return jsonify({"error": "Failed to fetch discovery shuffle"}), 500


@bp.get("/daily-mixes")
def get_all_daily_mixes():
    """Get all daily mixes"""
    try:
        max_mixes = request.args.get("max_mixes", 4, type=int)
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        mixes = service.get_all_daily_mixes(max_mixes=max_mixes)
        return jsonify({
            "mixes": mixes,
            "total": len(mixes)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching daily mixes: {e}")
        return jsonify({"error": "Failed to fetch daily mixes"}), 500
