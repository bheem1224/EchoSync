"""
Discovery Engine for the Suggestion Engine.

Two entry points:
- ``suggest_from_library(artist_id)``  — surfaces tracks already in the local library.
- ``discover_new_tracks(artist_id)``   — fetches the full tracklist from the metadata
  provider, diffs against the local database, and publishes DOWNLOAD_INTENTs for
  tracks that are missing and haven't been hard-deleted.
"""

import datetime
from typing import List, Set
from core.plugin_loader import get_provider
from core.enums import Capability
from core.event_bus import event_bus
from database.working_database import get_working_database, UserTrackState, PlaybackHistory
from database.music_database import get_database as get_music_database, Track, Artist, TrackAudioFeatures
from core.matching_engine.text_utils import generate_deterministic_id
from core.suggestion_engine.vibe_profiler import calculate_user_vibe, calculate_vibe_distance
from core.suggestion_engine.analytics import PlaybackAnalytics
from time_utils import utc_now


def suggest_from_library(user_id: str, limit: int = 50) -> List[dict]:
    """
    Surfaces owned content from the local MusicDatabase using Content-Based Filtering.

    Calculates the user's Vibe Signature and finds rarely played tracks that match this vibe.
    Returns a list of plain dicts so callers never touch a detached ORM object.
    """
    vibe_signature = calculate_user_vibe(user_id, days=30)

    # Identify top artists in recent history to apply a score bonus.
    # Query working.db directly — get_trending_provider_ids is global/server-wide and must
    # not be called with a user filter. User-specific lookup goes straight to PlaybackHistory.
    recent_artists_set = set()
    working_db = get_working_database()
    music_db = get_music_database()

    from sqlalchemy import func as sa_func
    from database.music_database import ExternalIdentifier
    thirty_days_ago = utc_now() - datetime.timedelta(days=30)
    with working_db.session_scope() as w_session:
        user_recent_pids = [
            row.provider_item_id for row in w_session.query(PlaybackHistory.provider_item_id).filter(
                PlaybackHistory.user_id == user_id,
                PlaybackHistory.listened_at >= thirty_days_ago
            ).group_by(PlaybackHistory.provider_item_id).limit(100).all()
        ]
    if user_recent_pids:
        with music_db.session_scope() as session:
            recent_identifiers = session.query(ExternalIdentifier).filter(
                ExternalIdentifier.provider_item_id.in_(user_recent_pids)
            ).all()
            for identifier in recent_identifiers:
                if identifier.track and identifier.track.artist:
                    recent_artists_set.add(identifier.track.artist.name.lower())

    # Get "rarely played" tracks:
    # a) Not in PlaybackHistory at all
    # b) Fewer than 3 total scrobbles
    # c) Not played in the last 90 days
    # To do this efficiently, we can fetch all tracks and their play counts from working DB.
    track_play_data = {}
    with working_db.session_scope() as w_session:
        from sqlalchemy import func
        # Count all-time plays
        play_counts = w_session.query(
            PlaybackHistory.provider_item_id,
            func.count(PlaybackHistory.id).label('total_plays'),
            func.max(PlaybackHistory.listened_at).label('last_played')
        ).filter(
            PlaybackHistory.user_id == user_id
        ).group_by(PlaybackHistory.provider_item_id).all()

        for pc in play_counts:
            track_play_data[pc.provider_item_id] = {
                'total_plays': pc.total_plays,
                'last_played': pc.last_played
            }

    scored_tracks = []
    ninety_days_ago = utc_now() - datetime.timedelta(days=90)

    with music_db.session_scope() as session:
        # We need Tracks and their Audio Features.
        # Since we might have many tracks, we fetch all tracks and then filter/score.
        from sqlalchemy.orm import selectinload
        all_tracks = session.query(Track).options(
            selectinload(Track.artist),
            selectinload(Track.external_identifiers),
            selectinload(Track.album)
        ).all()

        # Pre-fetch all TrackAudioFeatures into a dictionary
        all_features = session.query(TrackAudioFeatures).all()
        features_dict = {f.sync_id: f for f in all_features}

        for t in all_tracks:
            # Check if rarely played
            is_rarely_played = False

            # Get external identifiers to check playback history
            # It's possible a track has multiple external identifiers, we check if any of them is rarely played
            provider_ids = [ei.provider_item_id for ei in t.external_identifiers]

            if not provider_ids:
                # If no provider IDs, it hasn't been played or synced to a provider. It's unplayed.
                is_rarely_played = True
            else:
                for pid in provider_ids:
                    p_data = track_play_data.get(pid)
                    if not p_data:
                        is_rarely_played = True
                        break
                    if p_data['total_plays'] < 3:
                        is_rarely_played = True
                        break
                    if p_data['last_played'] < ninety_days_ago:
                        is_rarely_played = True
                        break

            if not is_rarely_played:
                continue

            # Skip if we don't have a vibe signature, but we still want to return tracks
            # If no vibe signature, we just return them sorted randomly or by artist bonus.
            # But the requirement implies we should vibe check them.

            distance = 0.0
            if vibe_signature:
                base_sync_id = f"ss:track:meta:{generate_deterministic_id(t.artist.name, t.title)}"
                track_features = features_dict.get(base_sync_id)
                if track_features:
                    distance = calculate_vibe_distance(vibe_signature, track_features)
                else:
                    # Penalty for missing features
                    distance = 2.0

            # Apply artist bonus
            if t.artist and t.artist.name.lower() in recent_artists_set:
                distance -= 0.15
                if distance < 0.0:
                    distance = 0.0

            scored_tracks.append((distance, t))

        # Sort by distance (lowest is best)
        scored_tracks.sort(key=lambda x: x[0])
        top_tracks = scored_tracks[:limit]

        return [
            {
                "track_db_id": t.id,
                "title": t.title,
                "artist_name": t.artist.name if t.artist else None,
                "album_name": t.album.title if t.album else None,
                "duration_ms": t.duration,
                "musicbrainz_id": t.musicbrainz_id,
                "isrc": t.isrc,
                "file_path": t.file_path,
                "vibe_score": score
            }
            for score, t in top_tracks
        ]


def discover_new_tracks(user_id: str) -> List[dict]:
    """
    Discovers new tracks not in the local MusicDatabase based on the user's recent history.
    """
    # 1. Identify the top 3 artists from the user's 30-day playback history.
    # Query working.db directly — get_trending_provider_ids is global/server-wide and must
    # not be called with a user filter. User-specific lookup goes straight to PlaybackHistory.
    recent_artists_counts = {}
    music_db = get_music_database()

    from sqlalchemy import func as sa_func
    from database.music_database import ExternalIdentifier
    thirty_days_ago = utc_now() - datetime.timedelta(days=30)
    working_db = get_working_database()
    with working_db.session_scope() as w_session:
        user_play_rows = w_session.query(
            PlaybackHistory.provider_item_id,
            sa_func.count(PlaybackHistory.id).label('play_count')
        ).filter(
            PlaybackHistory.user_id == user_id,
            PlaybackHistory.listened_at >= thirty_days_ago
        ).group_by(PlaybackHistory.provider_item_id).order_by(
            sa_func.count(PlaybackHistory.id).desc()
        ).limit(200).all()
        pid_counts = {row.provider_item_id: row.play_count for row in user_play_rows}
    if pid_counts:
        with music_db.session_scope() as session:
            discover_identifiers = session.query(ExternalIdentifier).filter(
                ExternalIdentifier.provider_item_id.in_(list(pid_counts.keys()))
            ).all()
            for identifier in discover_identifiers:
                if identifier.track and identifier.track.artist:
                    artist_name = identifier.track.artist.name
                    recent_artists_counts[artist_name] = recent_artists_counts.get(artist_name, 0) + pid_counts.get(identifier.provider_item_id, 0)

    # Sort artists by play count
    sorted_artists = sorted(recent_artists_counts.items(), key=lambda x: x[1], reverse=True)
    top_3_artists = [artist for artist, count in sorted_artists[:3]]

    if not top_3_artists:
        import logging
        logging.getLogger("discovery_engine").debug("No top artists found to base discovery on.")
        return []

    # 2. Get similar artists/tracks from ListenBrainz
    # To get a specific provider by name, we can iterate over get_providers_with_capability if it exists,
    # or just use the core plugin_loader. Let's try to import the registry directly.
    from core.plugin_loader import provider_registry
    lb_provider = provider_registry.get_provider('listenbrainz')
    if not lb_provider:
        import logging
        logging.getLogger("discovery_engine").error("ListenBrainz provider not found.")
        return []

    # get_similar_artists should return a list of SoulSyncTrack or similar dictionary objects from those artists
    # Depending on implementation, we assume it returns top tracks by similar artists
    if not hasattr(lb_provider, 'get_similar_artists'):
        import logging
        logging.getLogger("discovery_engine").error("ListenBrainz provider does not support get_similar_artists.")
        return []

    discovered_tracks = lb_provider.get_similar_artists(top_3_artists)
    if not discovered_tracks:
        return []

    # 3. Filter to ensure they don't exist in our MusicDatabase (using musicbrainz_id checks)
    new_tracks = []
    with music_db.session_scope() as session:
        for track in discovered_tracks:
            # Check by musicbrainz_id
            mbid = track.get("musicbrainz_id") if isinstance(track, dict) else getattr(track, "musicbrainz_id", None)

            if mbid:
                exists = session.query(Track).filter_by(musicbrainz_id=mbid).first()
                if exists:
                    continue

            # Fallback: check by title and artist
            title = track.get("title") if isinstance(track, dict) else getattr(track, "title", None)
            artist_name = track.get("artist_name") if isinstance(track, dict) else getattr(track, "artist_name", None)

            if title and artist_name:
                base_sync_id = f"ss:track:meta:{generate_deterministic_id(artist_name, title)}"
                # Re-verify if exists by string match or generated ID logic, wait, we can just use check_track_exists
                # or a simple exact query
                exists = session.query(Track).join(Artist).filter(
                    Track.title == title,
                    Artist.name == artist_name
                ).first()

                if exists:
                    continue

            # Convert to dict if necessary
            if not isinstance(track, dict):
                track_dict = {
                    "title": getattr(track, "title", None),
                    "artist_name": getattr(track, "artist_name", None),
                    "musicbrainz_id": getattr(track, "musicbrainz_id", None)
                }
                new_tracks.append(track_dict)
            else:
                new_tracks.append(track)

    return new_tracks


# Backward-compatibility alias — prefer discover_new_tracks() in new code.
discover_tracks = discover_new_tracks
