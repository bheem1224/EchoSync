import logging
import re
from urllib.parse import quote
from flask import Blueprint, jsonify, request
from web.services.sync_service import SyncAdapter
from core.personalized_playlists import get_personalized_playlists_service
from database.music_database import MusicDatabase
from core.tiered_logger import get_logger
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import ScoringProfile
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.job_queue import job_queue
from web.utils.event_bus import event_bus
from core.sync_history import sync_history
from core.account_manager import AccountManager
import time

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
    target_source = payload.get("target_source") or target
    playlists = payload.get("playlists") or []
    quality_profile = payload.get("quality_profile", "Auto")

    if not source:
        return jsonify({"error": "source provider required"}), 400
    
    if not playlists:
        return jsonify({"error": "playlists list required"}), 400

    try:
        from core.provider import ProviderRegistry
        from database.music_database import MusicDatabase
        
        # Helper to instantiate a provider, optionally tied to a specific account
        def _get_provider_for_account(acc_id=None):
            if source in ['spotify', 'tidal']:
                if acc_id is None:
                    # fall back to active/first account if no id provided
                    accounts = AccountManager.list_accounts(source)
                    if not accounts:
                        return None, None
                    acc_id_local = accounts[0]['id']
                else:
                    acc_id_local = acc_id

                if source == 'spotify':
                    from providers.spotify.client import SpotifyClient
                    return SpotifyClient(account_id=acc_id_local), acc_id_local
                elif source == 'tidal':
                    from providers.tidal.client import TidalClient
                    return TidalClient(account_id=str(acc_id_local)), acc_id_local
            else:
                try:
                    return ProviderRegistry.create_instance(source), None
                except ValueError:
                    return None, None

        # Prepare base provider instance (may be overridden per-playlist)
        source_provider, default_acc = _get_provider_for_account(None)
        if source_provider is None:
            return jsonify({"error": f"No {source.title()} accounts configured. Please add an account in Settings."}), 400

        try:
            # see above; provider instance created already
            pass
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

            # if account_id present, ensure we use provider instance tied to that account
            acc_id = playlist_info.get('account_id')
            if acc_id and source in ['spotify', 'tidal']:
                provider_instance, _ = _get_provider_for_account(acc_id)
                if provider_instance:
                    # use the per-account client for fetching tracks
                    source_provider = provider_instance

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
                    track_artist = source_track.artist_name
                    track_album = source_track.album_title or ''
                    track_duration = source_track.duration
                    track_isrc = source_track.isrc

                    def _strip_feat(title: str) -> str:
                        if not title:
                            return ""
                        # Remove parenthetical/bracketed feat/with sections
                        cleaned = re.sub(r"\s*[\(\[\{]\s*(feat\.?|featuring|with)\b[^\)\]\}]*[\)\]\}]", "", title, flags=re.IGNORECASE)
                        # Remove trailing feat/with clauses
                        cleaned = re.sub(r"\s+(feat\.?|featuring|with)\b.*$", "", cleaned, flags=re.IGNORECASE)
                        return cleaned.strip() or title

                    search_title = _strip_feat(track_title)
                    
                    # Search database for matching tracks
                    library_match = "Not Found"
                    best_score = 0
                    try:
                        # Get all candidates from database with similar title/artist
                        from sqlalchemy import text
                        
                        with db.engine.connect() as conn:
                            # TIER 1: Search with artist matching (preferred)
                            # exact artist match + fuzzy title match takes priority
                            # Then fall back to fuzzy artist + exact title match
                            # Then fuzzy artist + fuzzy title
                            tier1_query = text("""
                                SELECT t.id, t.title, t.duration, t.edition, a.name as artist_name, a.id as artist_id, t.sort_title
                                FROM tracks t
                                JOIN artists a ON t.artist_id = a.id
                                WHERE (
                                    -- Priority 1: Exact artist match + any title containing search term
                                    (LOWER(a.name) = LOWER(:artist_exact) AND LOWER(t.title) LIKE LOWER(:title_pattern))
                                    OR
                                    -- Priority 2: Artist contains search + exact title match
                                    (LOWER(a.name) LIKE LOWER(:artist_pattern) AND LOWER(t.title) = LOWER(:title_exact))
                                    OR
                                    -- Priority 3: Both artist and title contain search terms
                                    (LOWER(a.name) LIKE LOWER(:artist_pattern) AND LOWER(t.title) LIKE LOWER(:title_pattern))
                                )
                                ORDER BY 
                                    -- Prioritize exact matches
                                    (LOWER(a.name) = LOWER(:artist_exact)) DESC,
                                    (LOWER(t.title) = LOWER(:title_exact)) DESC,
                                    -- Then fuzzy matches with higher specificity
                                    ABS(t.duration - :duration) ASC
                                LIMIT 20
                            """)

                            result = conn.execute(tier1_query, {
                                "artist_exact": track_artist,
                                "artist_pattern": f"%{track_artist}%",
                                "title_exact": search_title,
                                "title_pattern": f"%{search_title}%",
                                "duration": track_duration or 0
                            })
                            candidates = result.fetchall()
                            tier2_mode = False  # Track if we're using Tier 2
                            
                            # TIER 2: Fallback - If Tier 1 returns 0 results, search by exact title ONLY
                            # Guard rail: Duration filter for SQL (2 seconds) to retrieve candidates
                            # The matching engine will apply the same 2s strict tolerance after retrieval
                            if not candidates and track_duration:
                                # Use 2 seconds for SQL query to align with scoring tolerance
                                sql_duration_tolerance_ms = 2000  # 2 seconds for candidate retrieval
                                duration_min = track_duration - sql_duration_tolerance_ms
                                duration_max = track_duration + sql_duration_tolerance_ms
                                
                                logger.debug(
                                    f"Tier 1 found 0 candidates for '{track_title}' by '{track_artist}'. "
                                    f"Attempting Tier 2 with title='{search_title}', duration={track_duration}ms ±{sql_duration_tolerance_ms}ms"
                                )
                                tier2_query = text("""
                                    SELECT t.id, t.title, t.duration, t.edition, a.name as artist_name, a.id as artist_id, t.sort_title
                                    FROM tracks t
                                    JOIN artists a ON t.artist_id = a.id
                                    WHERE (
                                        LOWER(t.title) = LOWER(:title_exact)
                                                                                OR LOWER(REPLACE(REPLACE(t.title, '''', ''), '’', '')) = LOWER(REPLACE(REPLACE(:title_exact, '''', ''), '’', ''))
                                    )
                                      AND t.duration IS NOT NULL
                                      AND t.duration BETWEEN :duration_min AND :duration_max
                                    ORDER BY ABS(t.duration - :duration) ASC
                                    LIMIT 10
                                """)
                                
                                result = conn.execute(tier2_query, {
                                    "title_exact": search_title,
                                    "duration": track_duration,
                                    "duration_min": duration_min,
                                    "duration_max": duration_max
                                })
                                candidates = result.fetchall()
                                tier2_mode = True  # Mark that we're using Tier 2 scoring
                                
                                if candidates:
                                    logger.debug(
                                        f"Tier 2 fallback activated for '{track_title}' by '{track_artist}' "
                                        f"(duration: {track_duration} ms). Found {len(candidates)} title+duration matches."
                                    )
                                else:
                                    logger.debug(
                                        f"Tier 2 found 0 candidates for exact title match '{search_title}' with duration {track_duration}ms. "
                                        f"Either no exact title match exists or all candidates outside {sql_duration_tolerance_ms}ms tolerance."
                                    )
                        
                        # Prefetch external identifiers for target source, if provided
                        external_ids_map = {}
                        if target_source and candidates:
                            candidate_ids = [row[0] for row in candidates]
                            try:
                                external_ids_map = db.get_external_identifier_map(target_source, candidate_ids)
                            except Exception as ext_err:
                                logger.debug(
                                    f"External identifier lookup failed for target '{target_source}': {ext_err}"
                                )

                        # Score each candidate using matching engine
                        best_match = None
                        best_match_track_id = None
                        best_match_target_id = None
                        # Collect diagnostics for unmatched verbose logging
                        candidate_diagnostics = []
                        
                        for candidate_row in candidates:
                            candidate_target_id = external_ids_map.get(candidate_row[0]) if target_source else None
                            # Use actual title for matching; extract edition from sort_title if edition is NULL
                            raw_title_candidate = candidate_row[1]  # Actual title
                            edition_candidate = candidate_row[3]  # Edition from DB
                            sort_title_candidate = None
                            try:
                                sort_title_candidate = candidate_row[6]
                            except Exception:
                                sort_title_candidate = None
                            
                            # If edition is NULL, try to extract version keywords from sort_title
                            if edition_candidate is None and sort_title_candidate and sort_title_candidate != raw_title_candidate:
                                version_pattern = r'\b(Remix|Mix|Live|Demo|Remaster|Deluxe|Edit|Version|Acoustic|Instrumental|Bonus|Extended|Original)\b'
                                version_match = re.search(version_pattern, sort_title_candidate, re.IGNORECASE)
                                if version_match:
                                    edition_candidate = version_match.group(0)
                            
                            candidate_track = SoulSyncTrack(
                                raw_title=raw_title_candidate,
                                artist_name=candidate_row[4],
                                album_title="",
                                duration=candidate_row[2] if candidate_row[2] else 0,
                                edition=edition_candidate,
                            )
                            
                            # Log version info for debugging
                            if source_track.edition or candidate_track.edition:
                                logger.debug(
                                    f"Version comparison: source='{source_track.edition}' vs candidate='{candidate_track.edition}' "
                                    f"(source_title='{source_track.title}', candidate_title='{candidate_track.title}')"
                                )
                            
                            # Choose scoring method based on tier
                            if tier2_mode:
                                # Tier 2: Use title+duration only matching (ignores artist)
                                result = matching_engine.calculate_title_duration_match(
                                    source_track,
                                    candidate_track,
                                    target_source=target_source,
                                    target_identifier=candidate_target_id,
                                )
                            else:
                                # Tier 1: Use standard full matching
                                result = matching_engine.calculate_match(
                                    source_track,
                                    candidate_track,
                                    target_source=target_source,
                                    target_identifier=candidate_target_id,
                                )
                            
                            logger.debug(f"Match score for '{track_title}' vs '{candidate_track.title}': {result.confidence_score}")
                            
                            # Collect detailed diagnostics for later verbose logging
                            candidate_diagnostics.append({
                                "candidate": {
                                    "title": candidate_track.title,
                                    "artist": candidate_track.artist_name,
                                    "duration": candidate_track.duration or 0,
                                },
                                "result": {
                                    "score": result.confidence_score,
                                    "passed_version": result.passed_version_check,
                                    "passed_edition": result.passed_edition_check,
                                    "fuzzy_text": result.fuzzy_text_score,
                                    "duration_score": result.duration_match_score,
                                    "quality_bonus": result.quality_bonus_applied,
                                    "version_penalty": result.version_penalty_applied,
                                    "edition_penalty": result.edition_penalty_applied,
                                },
                                "reasoning": result.reasoning,
                            })

                            if result.confidence_score > best_score:
                                best_score = result.confidence_score
                                best_match = (candidate_row[0], result)
                                best_match_track_id = candidate_row[0]
                                best_match_target_id = candidate_target_id
                        
                        # Escalate to Tier 2 if Tier 1 failed:
                        # - All candidates rejected due to version mismatch, OR
                        # - No candidate reached minimum confidence threshold
                        tier2_needed_due_to_version = (
                            not tier2_mode and len(candidates) > 0 and best_score == 0.0 and 
                            all(not d["result"]["passed_version"] for d in candidate_diagnostics)
                        )
                        tier2_needed_due_to_failure = (
                            not tier2_mode and len(candidates) > 0 and best_score < 70 and track_duration
                        )
                        if tier2_needed_due_to_version or tier2_needed_due_to_failure:
                            logger.debug(
                                (
                                    f"Tier 2 escalation triggered for '{track_title}' by '{track_artist}'. "
                                    + ("Reason: version mismatch." if tier2_needed_due_to_version else "Reason: no acceptable Tier 1 match.")
                                )
                            )
                            
                            # Reset for Tier 2 search
                            candidates = []
                            candidate_diagnostics = []
                            best_score = 0
                            best_match = None
                            
                            if track_duration:
                                sql_duration_tolerance_ms = 2000
                                duration_min = track_duration - sql_duration_tolerance_ms
                                duration_max = track_duration + sql_duration_tolerance_ms
                                
                                # Create a new connection for Tier 2 to avoid any connection state issues
                                with db.engine.connect() as tier2_conn:
                                    tier2_query = text("""
                                        SELECT t.id, t.title, t.duration, t.edition, a.name as artist_name, a.id as artist_id, t.sort_title
                                        FROM tracks t
                                        JOIN artists a ON t.artist_id = a.id
                                        WHERE LOWER(t.title) = LOWER(:title_exact)
                                        AND t.duration IS NOT NULL
                                        AND t.duration BETWEEN :duration_min AND :duration_max
                                        ORDER BY ABS(t.duration - :duration) ASC
                                        LIMIT 10
                                    """)
                                    
                                    result = tier2_conn.execute(tier2_query, {
                                        "title_exact": search_title,
                                        "duration": track_duration,
                                        "duration_min": duration_min,
                                        "duration_max": duration_max
                                    })
                                    candidates = result.fetchall()
                                
                                if candidates:
                                    logger.debug(
                                        f"Tier 2 escalation found {len(candidates)} title+duration matches for '{track_title}'. "
                                        f"Re-scoring with Tier 2 profile..."
                                    )
                                    
                                    # Prefetch external identifiers again for Tier 2 candidates
                                    external_ids_map = {}
                                    if target_source:
                                        candidate_ids = [row[0] for row in candidates]
                                        try:
                                            external_ids_map = db.get_external_identifier_map(target_source, candidate_ids)
                                        except Exception as ext_err:
                                            logger.debug(
                                                f"External identifier lookup failed for Tier 2: {ext_err}"
                                            )
                                    
                                    # Re-score all Tier 2 candidates
                                    for candidate_row in candidates:
                                        candidate_target_id = external_ids_map.get(candidate_row[0]) if target_source else None
                                        # Use actual title for matching; extract edition from sort_title if edition is NULL
                                        raw_title_candidate = candidate_row[1]  # Actual title
                                        edition_candidate = candidate_row[3]  # Edition from DB
                                        sort_title_candidate = None
                                        try:
                                            sort_title_candidate = candidate_row[6]
                                        except Exception:
                                            sort_title_candidate = None
                                        
                                        # If edition is NULL, try to extract version keywords from sort_title
                                        if edition_candidate is None and sort_title_candidate and sort_title_candidate != raw_title_candidate:
                                            version_pattern = r'\b(Remix|Mix|Live|Demo|Remaster|Deluxe|Edit|Version|Acoustic|Instrumental|Bonus|Extended|Original)\b'
                                            version_match = re.search(version_pattern, sort_title_candidate, re.IGNORECASE)
                                            if version_match:
                                                edition_candidate = version_match.group(0)
                                        
                                        candidate_track = SoulSyncTrack(
                                            raw_title=raw_title_candidate,
                                            artist_name=candidate_row[4],
                                            album_title="",
                                            duration=candidate_row[2] if candidate_row[2] else 0,
                                            edition=edition_candidate,
                                        )
                                        
                                        # Use Tier 2 scoring (title+duration only)
                                        result = matching_engine.calculate_title_duration_match(
                                            source_track,
                                            candidate_track,
                                            target_source=target_source,
                                            target_identifier=candidate_target_id,
                                        )
                                        
                                        logger.debug(f"Tier 2 re-score: '{track_title}' vs '{candidate_track.title}': {result.confidence_score}")
                                        
                                        candidate_diagnostics.append({
                                            "candidate": {
                                                "title": candidate_track.title,
                                                "artist": candidate_track.artist_name,
                                                "duration": candidate_track.duration or 0,
                                            },
                                            "result": {
                                                "score": result.confidence_score,
                                                "passed_version": result.passed_version_check,
                                                "passed_edition": result.passed_edition_check,
                                                "fuzzy_text": result.fuzzy_text_score,
                                                "duration_score": result.duration_match_score,
                                                "quality_bonus": result.quality_bonus_applied,
                                                "version_penalty": result.version_penalty_applied,
                                                "edition_penalty": result.edition_penalty_applied,
                                            },
                                            "reasoning": result.reasoning,
                                        })

                                        if result.confidence_score > best_score:
                                            best_score = result.confidence_score
                                            best_match = (candidate_row[0], result)
                                            best_match_track_id = candidate_row[0]
                                            best_match_target_id = candidate_target_id
                                    
                                    tier2_mode = True
                                else:
                                    logger.debug(
                                        f"Tier 2 escalation found 0 candidates for '{track_title}'. "
                                        f"Unable to find alternative versions."
                                    )
                        
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
                            # Emit verbose diagnostics only when debug logging enabled
                            if logger.isEnabledFor(logging.DEBUG):
                                try:
                                    src_dur = source_track.duration or 0
                                    logger.debug(
                                        f"Unmatched: '{track_title}' by '{track_artist}' (duration: {src_dur} ms). "
                                        f"Considered {len(candidate_diagnostics)} candidates.")

                                    # Sort candidates by score desc and limit to top 5 for readability
                                    top_candidates = sorted(
                                        candidate_diagnostics,
                                        key=lambda c: c["result"]["score"],
                                        reverse=True
                                    )[:5]

                                    for idx, diag in enumerate(top_candidates, start=1):
                                        cand = diag["candidate"]
                                        res = diag["result"]
                                        logger.debug(
                                            (
                                                f"  Candidate {idx}: '{cand['title']}' by '{cand['artist']}' "
                                                f"(duration: {cand['duration']} ms) → score {res['score']:.1f} | "
                                                f"version_pass={res['passed_version']}, edition_pass={res['passed_edition']}, "
                                                f"fuzzy={res['fuzzy_text']:.2f}, duration={res['duration_score']:.2f}, "
                                                f"penalties=V-{res['version_penalty']:.1f} E-{res['edition_penalty']:.1f}, "
                                                f"quality=+{res['quality_bonus']:.1f}"
                                            )
                                        )
                                        # Include reasoning to understand failure path
                                        logger.debug(f"    Reasoning: {diag['reasoning']}")
                                except Exception as log_err:
                                    # Do not disrupt flow due to logging errors
                                    logger.debug(f"Verbose unmatched diagnostics failed: {log_err}")
                        
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
                        "duration_ms": track_duration,
                        "library_match": library_match,
                        "download_status": "-",
                        "matched_track_id": best_match_track_id,
                        "match_score": best_score,
                        "target_source": target_source,
                        "target_identifier": best_match_target_id,
                        "target_exists": bool(best_match_target_id),
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
        
        # Build sync-ready payload with matched pairs
        matched_pairs = []
        missing_tracks = []
        for track in all_tracks:
            if track.get("matched_track_id") and track.get("target_identifier"):
                matched_pairs.append({
                    "track_id": track["matched_track_id"],
                    "target_identifier": track["target_identifier"],
                })
            elif not track.get("matched_track_id"):
                missing_tracks.append({
                    "title": track["title"],
                    "artist": track["artist"],
                    "album": track["album"],
                    "duration": track.get("duration_ms"),
                })
        
        return jsonify({
            "summary": {
                "total_tracks": total_tracks,
                "found_in_library": found_count,
                "missing_tracks": missing_count,
                "downloaded": 0,
                "quality_profile": quality_profile,
                "source": source,
                "target": target_source,
                "matched_pairs": matched_pairs,
                "can_sync": len(matched_pairs) > 0,
            },
            "tracks": all_tracks,
            "missing": missing_tracks,
        }), 200
        
    except Exception as e:
        logger.error(f"Error analyzing playlists: {e}", exc_info=True)
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@bp.post("/sync")
def trigger_sync():
    payload = request.get_json(silent=True) or {}
    target = payload.get("target_source") or payload.get("target")
    playlist_name = payload.get("playlist_name")
    matches = payload.get("matches") or []
    download_missing = payload.get("download_missing", False)
    source = payload.get("source", "unknown")

    if not target:
        return jsonify({"accepted": False, "error": "target_source required"}), 400

    if not playlist_name:
        return jsonify({"accepted": False, "error": "playlist_name required"}), 400

    # Detect sync mode: tier-to-tier (streaming↔streaming) vs local-server (streaming→plex)
    tier_to_tier_providers = {"spotify", "tidal", "apple_music"}
    local_server_providers = {"plex", "jellyfin", "navidrome"}
    
    is_source_tier = source in tier_to_tier_providers
    is_target_tier = target in tier_to_tier_providers
    is_source_server = source in local_server_providers
    is_target_server = target in local_server_providers
    
    sync_mode = None
    if is_source_tier and is_target_tier:
        sync_mode = "tier-to-tier"
    elif is_source_tier and is_target_server:
        sync_mode = "local-server"
    elif is_source_server and is_target_tier:
        sync_mode = "server-to-tier"
    else:
        sync_mode = "unknown"
    
    logger.info(f"Sync mode detected: {sync_mode} ({source} → {target})")

    # For non-Plex targets, return not implemented
    if target == "plex":
        # Local-server sync: add tracks to managed playlist with overwrite
        return _sync_to_plex(payload, source, target, playlist_name, matches, download_missing, sync_mode)
    elif target in tier_to_tier_providers:
        # Tier-to-tier sync: add tracks to target provider's playlist
        return _sync_to_tier(payload, source, target, playlist_name, matches, download_missing, sync_mode)
    else:
        return jsonify({"accepted": False, "error": f"Sync to {target} not implemented"}), 400


def _sync_to_plex(payload, source, target, playlist_name, matches, download_missing, sync_mode):
    """Sync matched tracks to a Plex managed playlist."""
    # Collect ratingKeys from matches (target_identifier)
    rating_keys = [m.get("target_identifier") for m in matches if m.get("target_identifier")]
    if not rating_keys:
        return jsonify({"accepted": False, "error": "No Plex ratingKeys provided in matches"}), 400

    # Schedule a one-off sync job with retry/backoff
    job_name = f"sync:plex:{playlist_name}:{int(time.time())}"

    def _run_sync():
        from providers.plex.client import PlexClient

        marker = "⇄"
        total = len(rating_keys)
        logger.info(f"[{job_name}] Starting Plex sync for playlist '{playlist_name}' with {total} tracks")
        event_bus.publish(job_name, "sync_started", {
            "playlist": playlist_name,
            "target": target,
            "total": total,
            "download_missing": download_missing,
            "sync_mode": sync_mode,
        })

        try:
            client = PlexClient()
            if not client.ensure_connection():
                raise RuntimeError("Plex connection failed")

            valid_keys = []
            for idx, rk in enumerate(rating_keys):
                logger.debug(f"[{job_name}] Processing track {idx + 1}/{total} (ratingKey: {rk}, type: {type(rk).__name__})")
                event_bus.publish(job_name, "track_started", {
                    "index": idx,
                    "rating_key": rk,
                    "total": total,
                })
                try:
                    # Ensure ratingKey is an integer
                    try:
                        rk_int = int(rk) if rk else None
                    except (ValueError, TypeError):
                        raise RuntimeError(f"Invalid ratingKey format: {rk}")
                    
                    if not rk_int:
                        raise RuntimeError("Empty or invalid ratingKey")
                    
                    item = client.server.fetchItem(rk_int) if client.server else None
                    if not item:
                        raise RuntimeError("Track not found on Plex")
                    valid_keys.append(rk)
                    logger.debug(f"[{job_name}] Track {idx + 1} synced successfully")
                    event_bus.publish(job_name, "track_synced", {
                        "index": idx,
                        "rating_key": rk,
                    })
                except Exception as fe:
                    logger.warning(f"[{job_name}] Track {idx + 1} failed: {str(fe)}")
                    event_bus.publish(job_name, "track_failed", {
                        "index": idx,
                        "rating_key": rk,
                        "error": str(fe),
                    })

            if not valid_keys:
                raise RuntimeError("No valid Plex items resolved for playlist sync")

            # Local-server sync: overwrite managed playlist
            logger.info(f"[{job_name}] Creating/updating managed playlist with {len(valid_keys)} tracks")
            updated = client.add_tracks_to_managed_playlist(
                playlist_name,
                valid_keys,
                marker=marker,
                overwrite=True,
            )
            event_bus.publish(job_name, "playlist_updated", {
                "playlist": playlist_name,
                "synced": len(valid_keys),
                "failed": total - len(valid_keys),
                "updated": bool(updated),
            })

            logger.info(f"[{job_name}] Sync complete: {len(valid_keys)} synced, {total - len(valid_keys)} failed")
            event_bus.publish(job_name, "sync_complete", {
                "playlist": playlist_name,
                "synced": len(valid_keys),
                "failed": total - len(valid_keys),
                "target": target,
                "sync_mode": sync_mode,
            })
            
            # Record in history
            sync_history.record_sync(
                source=source,
                target=target,
                playlist=playlist_name,
                total=total,
                synced=len(valid_keys),
                failed=total - len(valid_keys),
                download_missing=download_missing,
                job_name=job_name,
            )
        except Exception as e:
            logger.error(f"[{job_name}] Sync error: {str(e)}")
            event_bus.publish(job_name, "sync_error", {"message": str(e)})
            raise

    try:
        job_queue.register_job(
            name=job_name,
            func=_run_sync,
            interval_seconds=None,
            enabled=True,
            max_retries=3,
            backoff_base=5.0,
            backoff_factor=2.0,
        )
        job_queue.run_now(job_name)
    except Exception as e:
        logger.error(f"Failed to schedule Plex sync job '{job_name}': {e}")
        return jsonify({"accepted": False, "error": f"Failed to schedule sync: {e}"}), 500

    return jsonify({
        "accepted": True,
        "job": job_name,
        "target": target,
        "playlist": playlist_name,
        "match_count": len(rating_keys),
        "sync_mode": sync_mode,
        "events_path": f"/api/playlists/sync/events?job={quote(job_name, safe='')}",
    }), 202


def _sync_to_tier(payload, source, target, playlist_name, matches, download_missing, sync_mode):
    """Sync matched tracks to a tier provider (Spotify, Tidal, etc.)."""
    # Collect provider-specific IDs from matches (target_identifier for tier target)
    track_ids = [m.get("target_identifier") for m in matches if m.get("target_identifier")]
    if not track_ids:
        return jsonify({"accepted": False, "error": f"No {target} track IDs provided in matches"}), 400

    # Schedule a one-off sync job
    job_name = f"sync:{target}:{playlist_name}:{int(time.time())}"

    def _run_sync():
        logger.info(f"[{job_name}] Starting {target} sync for playlist '{playlist_name}' with {len(track_ids)} tracks")
        event_bus.publish(job_name, "sync_started", {
            "playlist": playlist_name,
            "target": target,
            "total": len(track_ids),
            "download_missing": download_missing,
            "sync_mode": sync_mode,
        })

        try:
            from core.provider import ProviderRegistry
            target_provider = ProviderRegistry.get_provider(target)
            
            if not target_provider:
                raise RuntimeError(f"Provider {target} not found")

            # Add tracks to target provider's playlist
            synced = 0
            failed = 0
            
            for idx, track_id in enumerate(track_ids):
                logger.debug(f"[{job_name}] Processing track {idx + 1}/{len(track_ids)} (ID: {track_id})")
                event_bus.publish(job_name, "track_started", {
                    "index": idx,
                    "track_id": track_id,
                    "total": len(track_ids),
                })
                try:
                    # Provider-specific add-to-playlist logic
                    target_provider.add_to_playlist(playlist_name, track_id)
                    synced += 1
                    logger.debug(f"[{job_name}] Track {idx + 1} synced successfully")
                    event_bus.publish(job_name, "track_synced", {
                        "index": idx,
                        "track_id": track_id,
                    })
                except Exception as fe:
                    failed += 1
                    logger.warning(f"[{job_name}] Track {idx + 1} failed: {str(fe)}")
                    event_bus.publish(job_name, "track_failed", {
                        "index": idx,
                        "track_id": track_id,
                        "error": str(fe),
                    })

            logger.info(f"[{job_name}] Sync complete: {synced} synced, {failed} failed")
            event_bus.publish(job_name, "sync_complete", {
                "playlist": playlist_name,
                "synced": synced,
                "failed": failed,
                "target": target,
                "sync_mode": sync_mode,
            })
            
            # Record in history
            sync_history.record_sync(
                source=source,
                target=target,
                playlist=playlist_name,
                total=len(track_ids),
                synced=synced,
                failed=failed,
                download_missing=download_missing,
                job_name=job_name,
            )
        except Exception as e:
            event_bus.publish(job_name, "sync_error", {"message": str(e)})
            raise

    try:
        job_queue.register_job(
            name=job_name,
            func=_run_sync,
            interval_seconds=None,
            enabled=True,
            max_retries=3,
            backoff_base=5.0,
            backoff_factor=2.0,
        )
        job_queue.run_now(job_name)
    except Exception as e:
        logger.error(f"Failed to schedule {target} sync job '{job_name}': {e}")
        return jsonify({"accepted": False, "error": f"Failed to schedule sync: {e}"}), 500

    return jsonify({
        "accepted": True,
        "job": job_name,
        "target": target,
        "playlist": playlist_name,
        "track_count": len(track_ids),
        "sync_mode": sync_mode,
        "events_path": f"/api/playlists/sync/events?job={quote(job_name, safe='')}",
    }), 202


@bp.get("/sync/events")
def sync_events():
    job_name = request.args.get("job")
    since = request.args.get("since", type=int)

    if not job_name:
        return jsonify({"error": "job query parameter required"}), 400

    events = event_bus.get_events(job_name, since_id=since)
    return jsonify({
        "job": job_name,
        "events": events,
        "count": len(events),
    }), 200


@bp.get("/sync/history")
def sync_history_endpoint():
    """Get recent sync records for observability."""
    source = request.args.get("source")
    target = request.args.get("target")
    limit = request.args.get("limit", 20, type=int)
    
    records = sync_history.get_records(source=source, target=target)
    recent = records[-limit:] if records else []
    
    return jsonify({
        "records": [r.to_dict() for r in recent],
        "total": len(recent),
    }), 200


@bp.post("/download-missing")
def download_missing_tracks():
    """Trigger downloads for missing tracks identified during analysis.
    
    Accepts a list of missing track metadata and enqueues download jobs.
    """
    payload = request.get_json(silent=True) or {}
    missing = payload.get("missing") or []
    
    if not missing:
        return jsonify({"accepted": False, "error": "missing tracks list required"}), 400
    
    job_name = f"download:missing:{int(time.time())}"
    
    def _run_downloads():
        from services.download_manager import get_download_manager
        from core.matching_engine.soul_sync_track import SoulSyncTrack
        
        event_bus.publish(job_name, "download_started", {
            "total": len(missing),
        })
        
        try:
            download_manager = get_download_manager()
            download_manager.ensure_background_task()  # kick off processing loop when user triggers downloads
            success_count = 0
            
            for idx, track_info in enumerate(missing):
                event_bus.publish(job_name, "download_started_track", {
                    "index": idx,
                    "title": track_info.get("title"),
                    "artist": track_info.get("artist"),
                })
                
                try:
                    # Create SoulSyncTrack from metadata
                    track = SoulSyncTrack(
                        raw_title=track_info.get("title"),
                        artist_name=track_info.get("artist"),
                        album_title=track_info.get("album") or "",
                        duration=track_info.get("duration_ms")
                    )

                    # Queue the download
                    download_id = download_manager.queue_download(track)

                    if download_id:
                        success_count += 1
                        event_bus.publish(job_name, "download_queued_track", {
                            "index": idx,
                            "title": track_info.get("title"),
                            "download_id": download_id
                        })
                    else:
                        event_bus.publish(job_name, "download_failed_track", {
                            "index": idx,
                            "title": track_info.get("title"),
                            "reason": "Failed to queue",
                        })
                except Exception as e:
                    event_bus.publish(job_name, "download_failed_track", {
                        "index": idx,
                        "title": track_info.get("title"),
                        "error": str(e),
                    })
            
            event_bus.publish(job_name, "download_complete", {
                "total": len(missing),
                "success": success_count,
                "failed": len(missing) - success_count,
            })
        except Exception as e:
            event_bus.publish(job_name, "download_error", {"message": str(e)})
            raise
    
    try:
        job_queue.register_job(
            name=job_name,
            func=_run_downloads,
            interval_seconds=None,
            enabled=True,
            max_retries=1,
            backoff_base=5.0,
        )
        job_queue.run_now(job_name)
    except Exception as e:
        logger.error(f"Failed to schedule download job '{job_name}': {e}")
        return jsonify({"accepted": False, "error": f"Failed to schedule downloads: {e}"}), 500
    
    return jsonify({
        "accepted": True,
        "job": job_name,
        "track_count": len(missing),
        "events_path": f"/api/playlists/sync/events?job={quote(job_name, safe='')}",
    }), 202


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


@bp.post("/sync/schedule")
def schedule_recurring_sync():
    """Schedule a recurring playlist sync job (e.g., every 6 hours)."""
    payload = request.get_json(silent=True) or {}
    source = payload.get("source")
    target = payload.get("target_source") or payload.get("target")
    playlists = payload.get("playlists", [])
    interval = payload.get("interval", 3600)  # Default: 1 hour in seconds
    download_missing = payload.get("download_missing", False)
    enabled = payload.get("enabled", True)

    if not source or not target or not playlists:
        return jsonify({"error": "source, target, and playlists required"}), 400

    if interval < 300:
        return jsonify({"error": "interval must be at least 300 seconds (5 minutes)"}), 400

    # Create scheduled sync config
    from core.settings import config_manager
    scheduled_syncs = config_manager.get("scheduled_syncs", [])
    
    sync_config = {
        "id": f"sync:{source}:{target}:{int(time.time())}",
        "source": source,
        "target": target,
        "playlists": playlists,
        "interval": interval,
        "download_missing": download_missing,
        "enabled": enabled,
        "created_at": time.time(),
    }
    
    scheduled_syncs.append(sync_config)
    config_manager.set("scheduled_syncs", scheduled_syncs)
    config_manager.save_config()
    
    # Register the job immediately if enabled
    if enabled:
        _register_scheduled_sync_job(sync_config)
    
    logger.info(f"Scheduled sync created: {sync_config['id']} (interval: {interval}s)")
    return jsonify({
        "accepted": True,
        "sync_id": sync_config["id"],
        "interval": interval,
    }), 201


@bp.get("/sync/scheduled")
def list_scheduled_syncs():
    """List all scheduled playlist sync jobs."""
    from core.settings import config_manager
    scheduled_syncs = config_manager.get("scheduled_syncs", [])
    
    # Enrich with job status from job_queue
    for sync in scheduled_syncs:
        job_name = f"scheduled:{sync['id']}"
        if job_name in job_queue.jobs:
            job_info = job_queue.jobs[job_name]
            sync["running"] = job_queue.running.get(job_name, False)
            sync["last_run"] = job_info.get("last_run")
            sync["last_error"] = job_info.get("last_error")
        else:
            sync["running"] = False
    
    return jsonify({
        "scheduled_syncs": scheduled_syncs,
        "count": len(scheduled_syncs),
    }), 200


@bp.delete("/sync/scheduled/<sync_id>")
def delete_scheduled_sync(sync_id):
    """Delete a scheduled sync job."""
    from core.settings import config_manager
    scheduled_syncs = config_manager.get("scheduled_syncs", [])
    
    # Find and remove sync
    updated_syncs = [s for s in scheduled_syncs if s.get("id") != sync_id]
    if len(updated_syncs) == len(scheduled_syncs):
        return jsonify({"error": "Sync not found"}), 404
    
    config_manager.set("scheduled_syncs", updated_syncs)
    config_manager.save_config()
    
    # Unregister from job queue
    job_name = f"scheduled:{sync_id}"
    if job_name in job_queue.jobs:
        job_queue.unregister_job(job_name)
    
    logger.info(f"Scheduled sync deleted: {sync_id}")
    return jsonify({"accepted": True}), 200


def _register_scheduled_sync_job(sync_config):
    """Register a scheduled sync config as a recurring job in the job queue."""
    job_name = f"scheduled:{sync_config['id']}"
    source = sync_config["source"]
    target = sync_config["target"]
    playlists = sync_config["playlists"]
    download_missing = sync_config.get("download_missing", False)
    interval = sync_config["interval"]

    def _run_scheduled_sync():
        try:
            # Analyze playlists
            from database.music_database import MusicDatabase
            db = MusicDatabase()
            from core.provider import ProviderRegistry
            
            source_provider = ProviderRegistry.get_provider(source)
            if not source_provider:
                raise RuntimeError(f"Source provider {source} not found")

            # Fetch playlists and run matching (abbreviated)
            all_tracks = []
            for playlist_id in playlists:
                try:
                    playlist_tracks = source_provider.get_playlist_tracks(playlist_id)
                    all_tracks.extend(playlist_tracks)
                except Exception as e:
                    logger.warning(f"Failed to fetch playlist {playlist_id}: {e}")
            
            if not all_tracks:
                logger.warning(f"No tracks found for scheduled sync {sync_config['id']}")
                return

            # Match against target provider
            target_provider = ProviderRegistry.get_provider(target)
            if not target_provider:
                raise RuntimeError(f"Target provider {target} not found")

            matches = []
            for track in all_tracks:
                try:
                    # Search target provider
                    search_results = target_provider.search(track.get("title"), track.get("artist"))
                    if search_results:
                        best_match = search_results[0]
                        matches.append({
                            "track_id": track.get("id"),
                            "target_identifier": best_match.get("id"),
                        })
                except Exception as e:
                    logger.debug(f"Failed to match track: {e}")

            if matches:
                # Trigger sync with matched tracks
                playlist_name = f"Synced Playlist ({sync_config['id']})"
                if target == "plex":
                    _sync_to_plex({
                        "source": source,
                        "target": target,
                    }, source, target, playlist_name, matches, download_missing, "scheduled")
                elif target in {"spotify", "tidal", "apple_music"}:
                    _sync_to_tier({
                        "source": source,
                        "target": target,
                    }, source, target, playlist_name, matches, download_missing, "scheduled")
        except Exception as e:
            logger.error(f"Scheduled sync {sync_config['id']} failed: {e}")
            raise

    try:
        job_queue.register_job(
            name=job_name,
            func=_run_scheduled_sync,
            interval_seconds=interval,
            enabled=True,
            max_retries=3,
            backoff_base=5.0,
            backoff_factor=2.0,
        )
        logger.info(f"Registered scheduled sync job: {job_name} (interval: {interval}s)")
    except Exception as e:
        logger.error(f"Failed to register scheduled sync job '{job_name}': {e}")


def load_scheduled_syncs_on_startup():
    """Load all enabled scheduled syncs from config at startup."""
    from core.settings import config_manager
    scheduled_syncs = config_manager.get("scheduled_syncs", [])
    
    for sync_config in scheduled_syncs:
        if sync_config.get("enabled", True):
            _register_scheduled_sync_job(sync_config)
    
    logger.info(f"Loaded {len([s for s in scheduled_syncs if s.get('enabled')])} scheduled syncs")
