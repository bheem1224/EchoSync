import math
from typing import Dict, Optional

from core.suggestion_engine.analytics import PlaybackAnalytics
from database.music_database import get_database, ExternalIdentifier, Track, TrackAudioFeatures
from core.matching_engine.text_utils import generate_deterministic_id
from core.tiered_logger import get_logger

logger = get_logger("vibe_profiler")

def calculate_user_vibe(user_id: str, days: int = 30) -> Optional[Dict[str, float]]:
    """
    Calculate a user's 'Vibe Signature' based on recent playback history.
    """
    # 1. Get recent trending provider_item_ids and their play counts
    trending_items = PlaybackAnalytics.get_trending_provider_ids(days=days, limit=100, user_id=user_id)
    if not trending_items:
        logger.debug(f"No recent playback history found for user_id={user_id} in the last {days} days.")
        return None

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
        for provider_item_id, count in trending_items.items():
            # Find the track through ExternalIdentifier
            identifier = session.query(ExternalIdentifier).filter_by(
                provider_item_id=provider_item_id
            ).first()

            if not identifier:
                continue

            track = identifier.track
            if not track or not track.artist:
                continue

            # Reconstruct the sync_id
            base_sync_id = f"ss:track:meta:{generate_deterministic_id(track.artist.name, track.title)}"

            # Fetch the audio features
            features = session.query(TrackAudioFeatures).filter_by(sync_id=base_sync_id).first()
            if not features:
                continue

            # Accumulate the weighted features (only if all features are present)
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

    # Calculate weighted average
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
