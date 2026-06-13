"""
Discovery Engine for the Suggestion Engine.

Two entry points:
- ``suggest_from_library(artist_id)``  — surfaces tracks already in the local library.
- ``discover_new_tracks(artist_id)``   — fetches the full tracklist from the metadata
  provider, diffs against the local database, and publishes DOWNLOAD_INTENTs for
  tracks that are missing and haven't been hard-deleted.
"""

import datetime
from typing import List, Optional
from database.working_database import get_working_database, PlaybackHistory
from database.music_database import get_database as get_music_database, Track, Artist, TrackAudioFeatures
from core.matching_engine.text_utils import generate_deterministic_id
from core.suggestion_engine.vibe_profiler import calculate_user_vibe, calculate_vibe_distance
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
        ).yield_per(1000)

        # Pre-fetch all TrackAudioFeatures into a dictionary
        all_features = session.query(TrackAudioFeatures).yield_per(1000)
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
    from core.nexus_framework.plugin_loader import get_plugin
    lb_plugin = get_plugin('listenbrainz')
    if not lb_plugin:
        import logging
        logging.getLogger("discovery_engine").error("ListenBrainz plugin not found.")
        return []

    # get_similar_artists should return a list of EchosyncTrack or similar dictionary objects from those artists
    # Depending on implementation, we assume it returns top tracks by similar artists
    if not hasattr(lb_plugin, 'get_similar_artists'):
        import logging
        logging.getLogger("discovery_engine").error("ListenBrainz plugin does not support get_similar_artists.")
        return []

    discovered_tracks = lb_plugin.get_similar_artists(top_3_artists)
    if not discovered_tracks:
        return []

    # 3. ListenBrainz / MusicBrainz cross-referencing loop (Chunked Concurrency)
    new_tracks = []

    mb_plugin = get_plugin('musicbrainz')
    import asyncio

    CHUNK_SIZE = 50
    for chunk_start in range(0, len(discovered_tracks), CHUNK_SIZE):
        chunk = discovered_tracks[chunk_start:chunk_start + CHUNK_SIZE]

        async def fetch_mbids(chunk_list):
            if not mb_plugin:
                return [[] for _ in chunk_list]

            tasks = []
            for track in chunk_list:
                mbid = track.get("musicbrainz_id") if isinstance(track, dict) else getattr(track, "musicbrainz_id", None)
                if not mbid:
                    title = track.get("title") if isinstance(track, dict) else getattr(track, "title", None)
                    artist_name = track.get("artist_name") if isinstance(track, dict) else getattr(track, "artist_name", None)
                    if title and artist_name:
                        tasks.append(mb_plugin.search_recording_strict(artist_name, title, immediate=False))
                    else:
                        tasks.append(asyncio.sleep(0, result=[]))
                else:
                    tasks.append(asyncio.sleep(0, result=[]))

            return await asyncio.gather(*tasks, return_exceptions=True)

        mb_results_batch = asyncio.run(fetch_mbids(chunk)) if mb_plugin else [[] for _ in chunk]

        with music_db.session_scope() as session:
            from database.music_database import Track, Artist
            from sqlalchemy import and_, or_

            # 1. Pre-process the chunk to gather all potential MBIDs and Title/Artist pairs
            pending_tracks = []
            mbids_to_check = set()
            pairs_to_check = set()

            for track, mb_results in zip(chunk, mb_results_batch):
                mbid = track.get("musicbrainz_id") if isinstance(track, dict) else getattr(track, "musicbrainz_id", None)

                if not mbid and not isinstance(mb_results, Exception) and mb_results:
                    top_match = mb_results[0]
                    mbid = top_match.musicbrainz_id
                    if isinstance(track, dict):
                        track["musicbrainz_id"] = mbid
                    else:
                        setattr(track, "musicbrainz_id", mbid)

                title = track.get("title") if isinstance(track, dict) else getattr(track, "title", None)
                artist_name = track.get("artist_name") if isinstance(track, dict) else getattr(track, "artist_name", None)

                if mbid:
                    mbids_to_check.add(mbid)
                if title and artist_name:
                    pairs_to_check.add((title, artist_name))

                pending_tracks.append({
                    "original_track": track,
                    "mbid": mbid,
                    "title": title,
                    "artist_name": artist_name
                })

            # 2. Batch Query existing matches
            existing_mbids = set()
            if mbids_to_check:
                # Chunk the IN clause to be safe (SQLite limit, though chunk size is 50 here anyway)
                mbids_list = list(mbids_to_check)
                for i in range(0, len(mbids_list), 500):
                    batch = mbids_list[i:i + 500]
                    found = session.query(Track.musicbrainz_id).filter(
                        Track.musicbrainz_id.in_(batch)
                    ).all()
                    existing_mbids.update([row[0] for row in found])

            existing_pairs = set()
            if pairs_to_check:
                pairs_list = list(pairs_to_check)
                for i in range(0, len(pairs_list), 250):  # 250 pairs = 500 expressions
                    batch = pairs_list[i:i + 250]
                    or_conditions = [and_(Track.title == t, Artist.name == a) for t, a in batch]
                    found = session.query(Track.title, Artist.name).join(Artist).filter(
                        or_(*or_conditions)
                    ).all()
                    existing_pairs.update([(row[0], row[1]) for row in found])

            # 3. Filter tracks using the pre-populated sets (O(1) lookup)
            for p_track in pending_tracks:
                mbid = p_track["mbid"]
                title = p_track["title"]
                artist_name = p_track["artist_name"]
                original_track = p_track["original_track"]

                if mbid and mbid in existing_mbids:
                    continue

                if title and artist_name and (title, artist_name) in existing_pairs:
                    continue

                if not isinstance(original_track, dict):
                    track_dict = {
                        "title": getattr(original_track, "title", None),
                        "artist_name": getattr(original_track, "artist_name", None),
                        "musicbrainz_id": getattr(original_track, "musicbrainz_id", None)
                    }
                    new_tracks.append(track_dict)
                else:
                    new_tracks.append(original_track)

        # Yield to let tasks clear out
        asyncio.run(asyncio.sleep(0))

        return new_tracks


# Backward-compatibility alias — prefer discover_new_tracks() in new code.
discover_tracks = discover_new_tracks


def recommend_near_miss(
    user_id: str,
    music_db_track_id: int,
    context: Optional[dict] = None,
) -> bool:
    """
    Insert a near-miss suggestion into the staging queue.

    Called by the playlist sync loop when the Matching Engine signals
    ``MatchResult.is_near_miss = True`` — i.e. the text match was
    near-perfect (title ≥ 0.95, artist ≥ 0.95) but the duration
    exceeded the strict tolerance, indicating an alternate edition
    (Radio Edit, Single Mix, Club Version, Album Version, etc.) rather
    than a genuine mismatch.

    The match is *not* created (score remains 0.0 in the engine).  This
    function only records the suggestion so the UI can surface it to the
    user for manual review.

    Args:
        user_id:           User whose suggestion queue to write to.
        music_db_track_id: ``tracks.id`` PK from music.db for the local
                           candidate that was a near-miss.
        context:           Optional free-form dict with debugging context
                           (e.g. source title, duration diff, sync origin).

    Returns:
        True  — new suggestion inserted.
        False — already existed (idempotent; not an error).
    """
    import logging
    from database.working_database import get_working_database, SuggestionStagingQueue
    from sqlalchemy.exc import IntegrityError

    logger = logging.getLogger("suggestion_engine.discovery")

    working_db = get_working_database()
    try:
        with working_db.session_scope() as session:
            suggestion = SuggestionStagingQueue(
                user_id=str(user_id),
                music_db_track_id=music_db_track_id,
                reason="near_miss_alternate_edition",
                ui_label="Alternate Edition / Near Miss",
                context_data=context or {},
                status="pending",
            )
            session.add(suggestion)
            # flush triggers the UNIQUE constraint check immediately
            session.flush()
        logger.info(
            "Near-miss suggestion queued: user=%s track_id=%s ctx=%s",
            user_id, music_db_track_id, context,
        )
        return True
    except IntegrityError:
        # Already queued for this (user, track, reason) triplet — idempotent.
        logger.debug(
            "Near-miss suggestion already exists: user=%s track_id=%s",
            user_id, music_db_track_id,
        )
        return False
    except Exception:
        logger.exception(
            "Failed to queue near-miss suggestion: user=%s track_id=%s",
            user_id, music_db_track_id,
        )
        return False


def mine_cached_playlists(user_id: str, limit: int = 20) -> int:
    """
    Scan all locally-cached Spotify playlist tracks for library gaps and queue
    suggestions for tracks that are genuinely absent and not already being handled.

    Two-gate filter applied per track:

    Gate 1 -- MusicDatabase check
        Query ``music.db`` by ISRC (exact) then by title + artist name (exact).
        If the track is already in the library, skip it.

    Gate 2 -- Download queue check
        Generate the track's deterministic ``sync_id`` and look for a row in the
        ``downloads`` table with ``status IN ('queued', 'searching', 'downloading')``.
        If an active job exists the track is already being fetched from Slskd -- skip it.

    Tracks that pass both gates are inserted into ``SuggestionStagingQueue`` with
    ``reason="playlist_gap"``.  The ``sync_id`` column is used for deduplication
    (``music_db_track_id`` is NULL because the track is absent from the local library).

    Args:
        user_id: User whose suggestion queue to write to.
        limit:   Maximum new suggestions to insert per call.  Acts as a safety cap
                 against bulk-inserting hundreds of rows in a single sweep.

    Returns:
        Number of new suggestion rows inserted.
    """
    import logging
    from itertools import islice
    from sqlalchemy import or_, and_
    from sqlalchemy.exc import IntegrityError
    from plugins.spotify.cache_manager import SpotifyCacheManager
    from database.working_database import get_working_database, SuggestionStagingQueue, Download
    from database.music_database import get_database as get_music_database, Track, Artist

    logger = logging.getLogger("suggestion_engine.discovery")

    # Download statuses that mean the track is already being handled.
    ACTIVE_STATUSES = {"queued", "searching", "downloading"}

    cm = SpotifyCacheManager()
    cached_playlists = cm.list_cached_playlists()
    if not cached_playlists:
        logger.debug("mine_cached_playlists: no cached Spotify playlists found.")
        return 0

    music_db = get_music_database()
    working_db = get_working_database()

    # 1. Extraction: Collect candidates
    candidates = []

    for pl in cached_playlists:
        playlist_id = pl["playlist_id"]
        playlist_name = pl.get("name", playlist_id)
        tracks = cm.get_cached_tracks(playlist_id)
        if not tracks:
            continue

        for track in tracks:
            title = getattr(track, "title", None) or getattr(track, "raw_title", None)
            artist_name = getattr(track, "artist_name", None)
            isrc = getattr(track, "isrc", None)

            # 1. Gather data for the batch
            batch_data = []
            isrcs = set()
            title_artist_pairs = set()
            sync_ids = set()

            for track in chunk:
                title = getattr(track, "title", None) or getattr(track, "raw_title", None)
                artist_name = getattr(track, "artist_name", None)
                isrc = getattr(track, "isrc", None)

                if not title or not artist_name:
                    continue

                sync_id = f"ss:track:meta:{generate_deterministic_id(artist_name, title)}"

                batch_data.append({
                    "title": title,
                    "artist_name": artist_name,
                    "isrc": isrc,
                    "sync_id": sync_id,
                    "track_obj": track
                })

            sync_id = f"ss:track:meta:{generate_deterministic_id(artist_name, title)}"
            candidates.append({
                "title": title,
                "artist_name": artist_name,
                "isrc": isrc,
                "sync_id": sync_id,
                "playlist_id": playlist_id,
                "playlist_name": playlist_name,
            })

    if not candidates:
        return 0

    # Helper function for chunking lists
    def chunked_iterable(iterable, size):
        it = iter(iterable)
        for first in it:
            yield [first] + list(islice(it, size - 1))

    existing_isrcs = set()
    existing_pairs = set()
    active_sync_ids = set()

    # 2. Gate 1: Batch Process Music Database (ISRC & Title/Artist)
    all_isrcs = [c["isrc"] for c in candidates if c["isrc"]]
    all_pairs = [(c["title"], c["artist_name"]) for c in candidates]
    all_sync_ids = [c["sync_id"] for c in candidates]

    with music_db.session_scope() as m_session:
        # ISRC matching
        if all_isrcs:
            for chunk in chunked_iterable(all_isrcs, 500):
                found = m_session.query(Track.isrc).filter(Track.isrc.in_(chunk)).all()
                existing_isrcs.update([r[0] for r in found])

        # Title + Artist matching
        # Needs to join Artist
        for chunk in chunked_iterable(all_pairs, 500):
            conditions = [and_(Track.title == t, Artist.name == a) for t, a in chunk]
            found = m_session.query(Track.title, Artist.name).join(Artist).filter(or_(*conditions)).all()
            existing_pairs.update([(r[0], r[1]) for r in found])

    # 3. Gate 2: Batch Process Working Database (Active Downloads & Staging Queue)
    already_queued_sync_ids = set()
    with working_db.session_scope() as w_session:
        # Active Downloads
        for chunk in chunked_iterable(all_sync_ids, 500):
            found = w_session.query(Download.sync_id).filter(
                Download.sync_id.in_(chunk),
                Download.status.in_(ACTIVE_STATUSES)
            ).all()
            active_sync_ids.update([r[0] for r in found])

        # Staging Queue (to prevent IntegrityError logging spam)
        for chunk in chunked_iterable(all_sync_ids, 500):
            found = w_session.query(SuggestionStagingQueue.sync_id).filter(
                SuggestionStagingQueue.user_id == str(user_id),
                SuggestionStagingQueue.reason == "playlist_gap",
                SuggestionStagingQueue.sync_id.in_(chunk)
            ).all()
            already_queued_sync_ids.update([r[0] for r in found])

    # 4. Filter and Insert
    inserted = 0
    with working_db.session_scope() as w_session:
        for c in candidates:
            if inserted >= limit:
                break

            title = c["title"]
            artist_name = c["artist_name"]
            isrc = c["isrc"]
            sync_id = c["sync_id"]

            if isrc and isrc in existing_isrcs:
                continue

            if (title, artist_name) in existing_pairs:
                continue

            if sync_id in active_sync_ids:
                logger.debug(
                    "mine_cached_playlists: '%s' by '%s' skipped -- active download job (sync_id=%s).",
                    title, artist_name, sync_id,
                )
                continue

            if sync_id in already_queued_sync_ids:
                continue

            try:
                row = SuggestionStagingQueue(
                    user_id=str(user_id),
                    music_db_track_id=None,
                    sync_id=sync_id,
                    reason="playlist_gap",
                    ui_label="Missing from Library",
                    context_data={
                        "title": title,
                        "artist_name": artist_name,
                        "isrc": isrc,
                        "playlist_id": c["playlist_id"],
                        "playlist_name": c["playlist_name"],
                    },
                    status="pending",
                )
                w_session.add(row)
                w_session.flush()
                # we track inserted to stop early, and add to already_queued_sync_ids in case of duplicates in the candidates list
                already_queued_sync_ids.add(sync_id)
                inserted += 1
                logger.info(
                    "mine_cached_playlists: suggestion queued '%s' by '%s' (sync_id=%s).",
                    title, artist_name, sync_id,
                )
            except IntegrityError:
                logger.debug(
                    "mine_cached_playlists: duplicate skipped '%s' by '%s'.",
                    title, artist_name,
                )

    logger.info(
        "mine_cached_playlists: complete for user=%s -- %d new suggestion(s) inserted.",
        user_id, inserted,
    )
    return inserted
