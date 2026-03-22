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
from database.music_database import get_database as get_music_database, Track, Artist
from core.matching_engine.text_utils import generate_deterministic_id


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
        # Canonical base identity: normalized deterministic track key
        base_sync_id = f"ss:track:meta:{generate_deterministic_id(track.artist_name, track.title)}"
        provider_sync_ids[base_sync_id] = full_sync_id

    if not provider_sync_ids:
        return

    # 2. Get Physical Library base sync_ids
    music_db = get_music_database()
    physical_sync_ids: Set[str] = set()

    with music_db.session_scope() as session:
        from sqlalchemy import func, or_

        local_tracks = (
            session.query(Track)
            .join(Artist, Track.artist_id == Artist.id)
            .filter(
                or_(
                    func.lower(Artist.name) == str(artist_id or "").lower(),
                    Artist.musicbrainz_id == artist_id,
                )
            )
            .all()
        )

        for t in local_tracks:
            artist_name = t.artist.name if t.artist else "unknown"
            title = t.title if t.title else "unknown"
            base_id = f"ss:track:meta:{generate_deterministic_id(artist_name, title)}"
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
