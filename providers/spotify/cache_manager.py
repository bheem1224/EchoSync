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
                Column('snapshot_id', String, nullable=True),
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
        snapshot_id = playlist_data.get('snapshot_id')

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
                        snapshot_id=snapshot_id,
                        sync_ids=sync_ids,
                        raw_data=raw_data,
                        last_synced=last_synced
                    )
                    session.execute(stmt)
                else:
                    stmt = self.table.insert().values(
                        playlist_id=playlist_id,
                        name=name,
                        snapshot_id=snapshot_id,
                        sync_ids=sync_ids,
                        raw_data=raw_data,
                        last_synced=last_synced
                    )
                    session.execute(stmt)
                session.commit()
            logger.info(f"Cached Spotify playlist {playlist_id} ({name}) with {len(sync_ids)} tracks.")
        except Exception as e:
            logger.error(f"Error saving playlist to cache: {e}")

    def list_cached_playlists(self) -> list:
        """Return all cached playlists as a list of dicts with 'playlist_id' and 'name'."""
        try:
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.engine)
            with Session() as session:
                rows = session.query(
                    self.table.c.playlist_id, self.table.c.name
                ).all()
            return [{"playlist_id": row[0], "name": row[1]} for row in rows]
        except Exception as e:
            logger.error(f"Error listing cached playlists: {e}")
            return []

    def get_snapshot_id(self, playlist_id: str) -> str | None:
        """Return the cached snapshot_id for *playlist_id*, or None if not cached."""
        try:
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.engine)
            with Session() as session:
                row = session.query(self.table.c.snapshot_id).filter(
                    self.table.c.playlist_id == playlist_id
                ).first()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error reading snapshot_id for {playlist_id}: {e}")
            return None

    def get_snapshot_ids_bulk(self, playlist_ids: list[str]) -> dict[str, str | None]:
        """Return a dict mapping playlist_id → cached snapshot_id for all requested IDs.

        Missing entries are returned as ``None`` so callers can distinguish
        *stale* (snapshot mismatch) from *missing* (never cached).
        """
        if not playlist_ids:
            return {}
        try:
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.engine)
            with Session() as session:
                rows = session.query(
                    self.table.c.playlist_id, self.table.c.snapshot_id
                ).filter(self.table.c.playlist_id.in_(playlist_ids)).all()
            cached = {row[0]: row[1] for row in rows}
            return {pid: cached.get(pid) for pid in playlist_ids}
        except Exception as e:
            logger.error(f"Error bulk-reading snapshot_ids: {e}")
            return {pid: None for pid in playlist_ids}

    def get_cached_tracks(self, playlist_id: str) -> list | None:
        """Return the list of ``SoulSyncTrack`` objects stored in *raw_data*, or
        ``None`` when the playlist has not been cached yet.

        The raw Spotify track items are re-converted so callers always receive
        the same ``SoulSyncTrack`` objects that the live API would produce.
        """
        try:
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.engine)
            with Session() as session:
                row = session.query(self.table.c.raw_data).filter(
                    self.table.c.playlist_id == playlist_id
                ).first()
            if not row or not row[0]:
                return None
            raw = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            tracks_page = raw.get('tracks', {})
            items = tracks_page.get('items', []) if isinstance(tracks_page, dict) else []
            if not items:
                return None
            # Import lazily to avoid circular deps at module load time
            from core.matching_engine.soul_sync_track import SoulSyncTrack
            tracks = []
            for item in items:
                track_obj = item.get('track')
                if not track_obj or not track_obj.get('id'):
                    continue
                artists = track_obj.get('artists', [])
                artist_name = artists[0].get('name', '') if artists else ''
                album = track_obj.get('album', {})
                t = SoulSyncTrack(
                    raw_title=track_obj.get('name', ''),
                    artist_name=artist_name,
                    album_title=(album.get('name') if isinstance(album, dict) else '') or '',
                    duration=track_obj.get('duration_ms'),
                    isrc=(track_obj.get('external_ids') or {}).get('isrc'),
                )
                t.identifiers = {
                    'spotify': track_obj.get('id'),
                    'provider_id': track_obj.get('id'),
                }
                tracks.append(t)
            return tracks if tracks else None
        except Exception as e:
            logger.error(f"Error reading cached tracks for {playlist_id}: {e}")
            return None
