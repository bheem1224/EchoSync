import math
from datetime import timedelta
from typing import Dict, Optional

from sqlalchemy import func

from database.music_database import get_database, ExternalIdentifier, TrackAudioFeatures
from database.working_database import get_working_database, PlaybackHistory
from core.matching_engine.text_utils import generate_deterministic_id
from core.tiered_logger import get_logger
from time_utils import utc_now

logger = get_logger("vibe_profiler")

def calculate_user_vibe(user_id: str, days: int = 30) -> Optional[Dict[str, float]]:
    """
    Calculate a user's 'Vibe Signature' based on recent playback history.
    """
    try:
        from core.hook_manager import hook_manager
        plugin_vibe = hook_manager.apply_filters('PROVIDE_VIBE_PROFILE', None, user_id=user_id, days=days)
        if plugin_vibe is not None and isinstance(plugin_vibe, dict):
            logger.info(f"Plugin intercepted vibe calculation for user_id={user_id}")
            return plugin_vibe
    except Exception as e:
        logger.error(f"Error executing PROVIDE_VIBE_PROFILE hook: {e}")

    # Step 1: Fetch user-specific provider_item_ids from working.db.
    cutoff_date = utc_now() - timedelta(days=days)
    working_db = get_working_database()
    with working_db.session_scope() as w_session:
        rows = w_session.query(
            PlaybackHistory.provider_item_id,
            func.count(PlaybackHistory.id).label('play_count')
        ).filter(
            PlaybackHistory.user_id == str(user_id),
            PlaybackHistory.listened_at >= cutoff_date
        ).group_by(
            PlaybackHistory.provider_item_id
        ).order_by(
            func.count(PlaybackHistory.id).desc()
        ).limit(100).all()
        user_play_counts = {row.provider_item_id: row.play_count for row in rows}

    if not user_play_counts:
        logger.debug(f"No recent playback history found for user_id={user_id} in the last {days} days.")
        return None

    provider_ids_list = list(user_play_counts.keys())

    # Step 2: Batch-fetch all required records from music.db — one query each, no N+1 loop.
    music_db = get_database()
    features_accumulator = {
        'tempo': 0.0,
        'energy': 0.0,
        'valence': 0.0,
        'danceability': 0.0,
        'acousticness': 0.0
    }
    total_weight = 0

    with music_db.session_scope() as session:
        # Single batch query for all external identifiers.
        identifiers = session.query(ExternalIdentifier).filter(
            ExternalIdentifier.provider_item_id.in_(provider_ids_list)
        ).all()

        # Build pid -> sync_id mapping entirely in Python — no per-item DB calls.
        pid_to_sync_id: Dict[str, str] = {}
        for identifier in identifiers:
            track = identifier.track
            if not track or not track.artist:
                continue
            base_sync_id = f"ss:track:meta:{generate_deterministic_id(track.artist.name, track.title)}"
            pid_to_sync_id[identifier.provider_item_id] = base_sync_id

        if not pid_to_sync_id:
            logger.debug(f"Could not map any provider IDs to tracks for user_id={user_id}.")
            return None

        # Single batch query for all audio features.
        unique_sync_ids = list(set(pid_to_sync_id.values()))
        all_features = session.query(TrackAudioFeatures).filter(
            TrackAudioFeatures.sync_id.in_(unique_sync_ids)
        ).all()
        features_by_sync_id = {f.sync_id: f for f in all_features}

        # Accumulate weighted features in Python — zero additional DB calls.
        for pid, count in user_play_counts.items():
            sync_id = pid_to_sync_id.get(pid)
            if not sync_id:
                continue
            features = features_by_sync_id.get(sync_id)
            if not features:
                continue
            if all(v is not None for v in [features.tempo, features.energy, features.valence, features.danceability, features.acousticness]):
                features_accumulator['tempo'] += features.tempo * count
                features_accumulator['energy'] += features.energy * count
                features_accumulator['valence'] += features.valence * count
                features_accumulator['danceability'] += features.danceability * count
                features_accumulator['acousticness'] += features.acousticness * count
                total_weight += count

    if total_weight == 0:
        logger.debug(f"Could not calculate vibe signature for user_id={user_id}. No valid audio features found for recent tracks.")
        return None

    return {
        'tempo': features_accumulator['tempo'] / total_weight,
        'energy': features_accumulator['energy'] / total_weight,
        'valence': features_accumulator['valence'] / total_weight,
        'danceability': features_accumulator['danceability'] / total_weight,
        'acousticness': features_accumulator['acousticness'] / total_weight
    }

def calculate_vibe_distance(target_vibe: Dict[str, float], track_features: TrackAudioFeatures) -> float:
    """
    Calculate the Euclidean distance between a user's vibe and a track's audio features.
    Lower distance = better match.
    """
    if not track_features:
        return float('inf')

    if any(v is None for v in [track_features.tempo, track_features.energy, track_features.valence, track_features.danceability, track_features.acousticness]):
        return float('inf')

    # Extract target and track features
    t_tempo = target_vibe.get('tempo', 0.0)
    t_energy = target_vibe.get('energy', 0.0)
    t_valence = target_vibe.get('valence', 0.0)
    t_dance = target_vibe.get('danceability', 0.0)
    t_acoustic = target_vibe.get('acousticness', 0.0)

    f_tempo = track_features.tempo
    f_energy = track_features.energy
    f_valence = track_features.valence
    f_dance = track_features.danceability
    f_acoustic = track_features.acousticness

    # Normalize tempo (assuming max realistic tempo is around 200)
    # Scale both down so they are roughly 0.0 - 1.0 like the other features
    norm_t_tempo = t_tempo / 200.0
    norm_f_tempo = f_tempo / 200.0

    # Ensure other features are bounded between 0.0 and 1.0 (they usually are, but just to be safe)
    # The prompt says: "Normalize the features to a 0.0 - 1.0 scale (except tempo, which you should scale down by dividing by ~200) before calculating distance."
    # Since they should already be in 0.0 - 1.0 range, we just use them directly but clamping might be safer.

    def clamp(val):
        return max(0.0, min(1.0, val))

    # Calculate Euclidean distance
    distance_squared = (
        (norm_t_tempo - norm_f_tempo) ** 2 +
        (clamp(t_energy) - clamp(f_energy)) ** 2 +
        (clamp(t_valence) - clamp(f_valence)) ** 2 +
        (clamp(t_dance) - clamp(f_dance)) ** 2 +
        (clamp(t_acoustic) - clamp(f_acoustic)) ** 2
    )

    return math.sqrt(distance_squared)
