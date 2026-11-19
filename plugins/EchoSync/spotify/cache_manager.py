from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3

from core.event_bus import event_bus
from core.matching_engine.text_utils import generate_deterministic_id
from core.plugins.sdk import compute_plugin_crc32
from core.task_manager.task_queue import db_write_lease
from core.tiered_logger import get_logger

PLUGIN_NAMESPACE = "EchoSync.spotify"
PLUGIN_CRC32 = compute_plugin_crc32(PLUGIN_NAMESPACE)
logger = get_logger("spotify_cache_manager", plugin_id=PLUGIN_CRC32)


class SpotifyCacheManager:
    """Manages local caching of Spotify playlists to optimize syncs and reduce API calls."""

    def __init__(self, sdk=None):
        self.sdk = sdk
        if self.sdk:
            plugin_data_dir = Path(self.sdk.get_plugin_data_dir())
            plugin_data_dir.mkdir(parents=True, exist_ok=True)
            self.cache_db_path = str(plugin_data_dir / "cache.db")
        else:
            raise ValueError("SpotifyCacheManager requires SDK instance to acquire isolated cache database")

        self._ensure_tables()
        self._register_listeners()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.cache_db_path)

    def _ensure_tables(self):
        """Ensure the playlist table exists."""
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS playlists (
                        playlist_id TEXT PRIMARY KEY,
                        name TEXT,
                        snapshot_id TEXT,
                        sync_ids TEXT,
                        raw_data TEXT,
                        last_synced TEXT
                    )
                    """
                )
                conn.commit()
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

        base_sync_id = sync_id.split("?")[0]

        try:
            with self._connect() as conn:
                rows = conn.execute("SELECT playlist_id, sync_ids FROM playlists").fetchall()
                for playlist_id, sync_ids_json in rows:
                    sync_ids = []
                    if sync_ids_json:
                        try:
                            sync_ids = json.loads(sync_ids_json) if isinstance(sync_ids_json, str) else sync_ids_json
                        except json.JSONDecodeError:
                            pass

                    if base_sync_id in sync_ids:
                        logger.info(
                            f"Downloaded track {base_sync_id} found in cached playlist {playlist_id}. Triggering sync."
                        )
                        event_bus.publish(
                            {
                                "event": "SYNC_PLAYLIST_INTENT",
                                "playlist_id": playlist_id,
                            }
                        )
        except Exception as e:
            logger.error(f"Error checking cached playlists for {base_sync_id}: {e}")

    def save_playlist(self, playlist_data: dict):
        """Save a fetched Spotify playlist to the local cache."""
        if not playlist_data:
            return

        playlist_id = playlist_data.get("id")
        name = playlist_data.get("name")
        snapshot_id = playlist_data.get("snapshot_id")

        if not playlist_id:
            return

        sync_ids = []
        tracks_page = playlist_data.get("tracks", {})
        items = tracks_page.get("items", []) if isinstance(tracks_page, dict) else []

        for item in items:
            track_obj = item.get("track", {})
            if not track_obj:
                continue

            title = track_obj.get("name")
            artists = track_obj.get("artists", [])
            artist = artists[0].get("name") if artists else "unknown"

            base_sync_id = self._generate_base_sync_id(artist, title)
            sync_ids.append(base_sync_id)

        last_synced = datetime.now(UTC).isoformat()

        try:
            with db_write_lease(task_name=f"plugin_{PLUGIN_CRC32}"), self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO playlists (playlist_id, name, snapshot_id, sync_ids, raw_data, last_synced)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(playlist_id) DO UPDATE SET
                        name = excluded.name,
                        snapshot_id = excluded.snapshot_id,
                        sync_ids = excluded.sync_ids,
                        raw_data = excluded.raw_data,
                        last_synced = excluded.last_synced
                    """,
                    (
                        playlist_id,
                        name,
                        snapshot_id,
                        json.dumps(sync_ids),
                        json.dumps(playlist_data),
                        last_synced,
                    ),
                )
                conn.commit()
            logger.info(f"Cached Spotify playlist {playlist_id} ({name}) with {len(sync_ids)} tracks.")
        except Exception as e:
            logger.error(f"Error saving playlist to cache: {e}")

    def list_cached_playlists(self) -> list:
        """Return all cached playlists as a list of dicts with 'playlist_id' and 'name'."""
        try:
            with self._connect() as conn:
                rows = conn.execute("SELECT playlist_id, name FROM playlists").fetchall()
            return [{"playlist_id": row[0], "name": row[1]} for row in rows]
        except Exception as e:
            logger.error(f"Error listing cached playlists: {e}")
            return []

    def get_snapshot_id(self, playlist_id: str) -> str | None:
        """Return the cached snapshot_id for *playlist_id*, or None if not cached."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT snapshot_id FROM playlists WHERE playlist_id = ?",
                    (playlist_id,),
                ).fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error reading snapshot_id for {playlist_id}: {e}")
            return None

    def get_snapshot_ids_bulk(self, playlist_ids: list[str]) -> dict[str, str | None]:
        """Return a dict mapping playlist_id → cached snapshot_id for all requested IDs."""
        if not playlist_ids:
            return {}
        try:
            placeholders = ",".join("?" for _ in playlist_ids)
            with self._connect() as conn:
                rows = conn.execute(
                    f"SELECT playlist_id, snapshot_id FROM playlists WHERE playlist_id IN ({placeholders})",
                    tuple(playlist_ids),
                ).fetchall()
            cached = {row[0]: row[1] for row in rows}
            return {pid: cached.get(pid) for pid in playlist_ids}
        except Exception as e:
            logger.error(f"Error bulk-reading snapshot_ids: {e}")
            return {pid: None for pid in playlist_ids}

    def get_cached_tracks(self, playlist_id: str) -> list | None:
        """Return the list of EchosyncTrack objects stored in raw_data, or None when not cached."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT raw_data FROM playlists WHERE playlist_id = ?",
                    (playlist_id,),
                ).fetchone()
            if not row or not row[0]:
                return None
            raw = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            tracks_page = raw.get("tracks", {})
            items = tracks_page.get("items", []) if isinstance(tracks_page, dict) else []
            if not items:
                return None
            from core.db.echo_sync_track import EchosyncTrack

            tracks = []
            for item in items:
                track_obj = item.get("track")
                if not track_obj or not track_obj.get("id"):
                    continue
                artists = track_obj.get("artists", [])
                artist_name = artists[0].get("name", "") if artists else ""
                album = track_obj.get("album", {})
                t = EchosyncTrack(
                    raw_title=track_obj.get("name", ""),
                    artist_name=artist_name,
                    album_title=(album.get("name") if isinstance(album, dict) else "") or "",
                    duration=track_obj.get("duration_ms"),
                    isrc=(track_obj.get("external_ids") or {}).get("isrc"),
                    identifiers={
                        "spotify": track_obj.get("id"),
                        "provider_id": track_obj.get("id"),
                    },
                )
                tracks.append(t)
            return tracks if tracks else None
        except Exception as e:
            logger.error(f"Error reading cached tracks for {playlist_id}: {e}")
            return None
