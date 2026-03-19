import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, JSON, DateTime
from core.tiered_logger import get_logger
from core.event_bus import event_bus
from core.matching_engine.text_utils import generate_deterministic_id
from database.working_database import get_working_database

logger = get_logger("spotify_cache_manager")

class SpotifyCacheManager:
    """Manages local caching of Spotify playlists to optimize syncs and reduce API calls."""

    def __init__(self, engine=None):
        from database.working_database import ProviderStorageBox
        if engine is None:
            work_db = get_working_database()
            self.engine = work_db.engine
            self.storage = work_db.get_provider_storage('spotify')
        else:
            self.engine = engine
            from database.working_database import WorkingBase
            self.storage = ProviderStorageBox('spotify', self.engine, WorkingBase.metadata)

        self._ensure_tables()
        self._register_listeners()

    def _ensure_tables(self):
        """Ensure the prv_spotify_playlists table exists."""
        try:
            self.table = self.storage.create_table(
                'playlists',
                Column('playlist_id', String, primary_key=True),
                Column('name', String),
                Column('sync_ids', JSON),
                Column('raw_data', JSON),
                Column('last_synced', DateTime(timezone=True))
            )
            self.storage.execute()
        except Exception as e:
            logger.error(f"Failed to create cache table: {e}")

    def _register_listeners(self):
        """Subscribe to relevant Event Bus events."""
        event_bus.subscribe("TRACK_DOWNLOADED", self._on_track_downloaded)

    def _generate_base_sync_id(self, artist: str, title: str) -> str:
        """Deterministically generate the base sync_id for a track."""
        encoded = generate_deterministic_id(artist, title)
        return f"ss:track:meta:{encoded}"

    def _on_track_downloaded(self, payload: dict):
        """Handle TRACK_DOWNLOADED event to trigger syncing if track belongs to a cached playlist."""
        sync_id = payload.get("sync_id")
        if not sync_id:
            return

        # Extract base sync_id by stripping query parameters
        base_sync_id = sync_id.split('?')[0]

        try:
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.engine)
            with Session() as session:
                query = session.query(self.table.c.playlist_id, self.table.c.sync_ids)
                results = query.all()

                for playlist_id, sync_ids_json in results:
                    sync_ids = []
                    if sync_ids_json:
                        try:
                            sync_ids = json.loads(sync_ids_json) if isinstance(sync_ids_json, str) else sync_ids_json
                        except json.JSONDecodeError:
                            pass

                    if base_sync_id in sync_ids:
                        logger.info(f"Downloaded track {base_sync_id} found in cached playlist {playlist_id}. Triggering sync.")
                        event_bus.publish({
                            "event": "SYNC_PLAYLIST_INTENT",
                            "playlist_id": playlist_id,
                        })
                        # Trigger for all matching playlists
        except Exception as e:
            logger.error(f"Error checking cached playlists for {base_sync_id}: {e}")

    def save_playlist(self, playlist_data: dict):
        """
        Save a fetched Spotify playlist to the local cache.
        Extracts base sync_ids from the tracks.
        """
        if not playlist_data:
            return

        playlist_id = playlist_data.get('id')
        name = playlist_data.get('name')

        if not playlist_id:
            return

        sync_ids = []
        tracks_page = playlist_data.get('tracks', {})
        items = tracks_page.get('items', []) if isinstance(tracks_page, dict) else []

        for item in items:
            track_obj = item.get('track', {})
            if not track_obj:
                continue

            title = track_obj.get('name')
            artists = track_obj.get('artists', [])
            artist = artists[0].get('name') if artists else "unknown"

            base_sync_id = self._generate_base_sync_id(artist, title)
            sync_ids.append(base_sync_id)

        raw_data = playlist_data
        last_synced = datetime.now(timezone.utc)

        try:
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.engine)
            with Session() as session:
                # Basic upsert logic (check then update/insert)
                existing = session.query(self.table).filter(self.table.c.playlist_id == playlist_id).first()
                if existing:
                    stmt = self.table.update().where(self.table.c.playlist_id == playlist_id).values(
                        name=name,
                        sync_ids=sync_ids,
                        raw_data=raw_data,
                        last_synced=last_synced
                    )
                    session.execute(stmt)
                else:
                    stmt = self.table.insert().values(
                        playlist_id=playlist_id,
                        name=name,
                        sync_ids=sync_ids,
                        raw_data=raw_data,
                        last_synced=last_synced
                    )
                    session.execute(stmt)
                session.commit()
            logger.info(f"Cached Spotify playlist {playlist_id} ({name}) with {len(sync_ids)} tracks.")
        except Exception as e:
            logger.error(f"Error saving playlist to cache: {e}")
