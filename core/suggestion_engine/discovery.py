"""
Discovery Engine for the Suggestion Engine.
Discovers new tracks for monitored artists by fetching the full tracklist
from the active metadata provider, diffing against the local database,
and publishing DOWNLOAD_INTENTs for missing tracks.
"""

from typing import List, Set
from core.plugin_loader import get_provider
from core.enums import Capability
from core.event_bus import event_bus
from database.working_database import get_working_database, UserTrackState
from database.music_database import get_database as get_music_database, Track


def discover_tracks(artist_id: str) -> None:
    """
    Fetches the full tracklist for a monitored artist from the metadata provider,
    runs a diff against the physical library and ghost tracks,
    and publishes a DOWNLOAD_INTENT for missing tracks.
    """
    # Use internal registry to get the provider that can fetch metadata
    provider = get_provider(Capability.FETCH_METADATA)

    if not provider:
        import logging
        logging.getLogger("discovery_engine").error("No provider available with FETCH_METADATA capability.")
        return

    # Call provider to get the artist's full tracklist
    # Note: If the provider exposes get_artist, it usually contains a tracks or albums list.
    # Depending on the abstract method, we might have to use search or get_artist.
    # In this implementation we assume provider has a way to return tracks, but since ProviderBase
    # only defines get_artist, we check if there's a specific method or if get_artist returns tracks.
    # The prompt explicitly said: "Call the provider's method to get a monitored artist's full tracklist"
    # We will try `get_artist_tracks` if it exists, otherwise `get_artist`.

    tracks_to_process = []

    if hasattr(provider, 'get_artist_tracks'):
        tracks_to_process = provider.get_artist_tracks(artist_id)
    else:
        # Fallback if get_artist_tracks doesn't exist, try get_artist and assume it has 'tracks' key
        artist_data = provider.get_artist(artist_id)
        if artist_data and 'tracks' in artist_data:
            tracks_to_process = artist_data['tracks']
        else:
            # If not supported, we can't discover
            import logging
            logging.getLogger("discovery_engine").error(f"Provider {provider.name} does not support fetching artist tracklist.")
            return

    if not tracks_to_process:
        return

    # 1. Generate sync_ids for all discovered tracks
    # tracks_to_process should be a list of SoulSyncTrack objects
    provider_sync_ids: dict[str, str] = {} # base_sync_id -> full_sync_id

    for track in tracks_to_process:
        full_sync_id = track.sync_id
        base_sync_id = full_sync_id.split('?')[0]
        provider_sync_ids[base_sync_id] = full_sync_id

    if not provider_sync_ids:
        return

    # 2. Get Physical Library base sync_ids
    music_db = get_music_database()
    physical_sync_ids: Set[str] = set()

    # Let's query the working.db's Download or UserTrackState for sync_ids that exist locally,
    # OR since the prompt says "Physical_Library_SyncIDs", but `Track` doesn't store `sync_id` URNs directly.
    # Actually wait, let's look at `database/music_database.py`. The `Track` model does not have a `sync_id` column.
    # Ah! The memory says "Operational tracking tables ... use a universally addressable structured URN string called sync_id (e.g., ss:track:mbid:... or ss:track:meta:...) as their tracking reference instead of local SQLite integer IDs. SoulSyncTrack implements sync_id as a dynamic property."
    # If the local `Track` does not store `sync_id`, how do we know if it's in the physical library?
    # Actually, `Download` has `sync_id`. But `Track` doesn't? Let's check `database/music_database.py` again.
    # No `sync_id` in `Track`.
    # Wait, the prompt says "For tracks in music_library.db, should I match by musicbrainz_id directly using the Track model?" And the answer was:
    # "The base identity is ss:track:meta:{base64(lowercase_artist|lowercase_title)}. In consensus.py and discovery.py, whenever you do internal database diffing or lookups, you must strip the query parameters... When publishing the DOWNLOAD_INTENT, you pass the full URI string."
    # If the physical `Track` doesn't have `sync_id` column, the only way is to construct the base identity from artist and title.
    # To avoid N+1 and loading the whole DB, we can just do a join and load only the columns we need, or better, only look for the tracks we are actually checking!
    # We only care about the tracks in `provider_sync_ids`.
    # So we can parse the base `sync_id` of the discovered tracks, decode the base64, and query ONLY those titles/artists!

    with music_db.session_scope() as session:
        import base64
        # Decode the provider base IDs to get the artist/title pairs we're looking for
        lookups = []
        for base_id in provider_sync_ids.keys():
            try:
                b64_str = base_id.split("meta:")[1]
                decoded = base64.b64decode(b64_str.encode("ascii")).decode("utf-8")
                artist, title = decoded.split("|", 1)
                lookups.append((artist, title, base_id))
            except Exception:
                pass

        # Now we only query the DB for these specific titles to avoid loading everything
        if lookups:
            from sqlalchemy import func
            from sqlalchemy.orm import joinedload
            # Fetch all tracks from the DB where the lower title is in our lookup list
            titles = [l[1] for l in lookups]
            # Batch the query if necessary, but typically an artist tracklist is < 100 tracks
            local_tracks = session.query(Track).join(Track.artist).filter(
                func.lower(Track.title).in_(titles)
            ).all()

            for t in local_tracks:
                artist = t.artist.name.lower() if t.artist else "unknown"
                title = t.title.lower() if t.title else "unknown"
                payload = f"{artist}|{title}"
                encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
                base_id = f"ss:track:meta:{encoded}"
                physical_sync_ids.add(base_id)

    # 3. Get Ghost Track base sync_ids
    working_db = get_working_database()
    ghost_track_sync_ids: Set[str] = set()

    with working_db.session_scope() as session:
        ghost_tracks = session.query(UserTrackState).filter(
            UserTrackState.is_hard_deleted == True
        ).all()
        for gt in ghost_tracks:
            gt_base_id = gt.sync_id.split('?')[0]
            ghost_track_sync_ids.add(gt_base_id)

    # 4. Run the diff: Missing = Provider - Physical - Ghost
    base_missing_ids = set(provider_sync_ids.keys()) - physical_sync_ids - ghost_track_sync_ids

    # 5. Publish DOWNLOAD_INTENT for missing IDs
    for base_id in base_missing_ids:
        full_id = provider_sync_ids[base_id]
        event_bus.publish({
            "event": "DOWNLOAD_INTENT",
            "sync_id": full_id
        })
