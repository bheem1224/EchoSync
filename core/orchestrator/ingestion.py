"""
Ingestion Orchestrator (core/orchestrator/ingestion.py).

Parses raw PyDict telemetry payloads from the Rust FFI (echosync_core) and
performs batched UPSERT transactions into the database using the strict 2-Model contract:

  EchosyncTrack  -> tracks table       (logical metadata, keyed by sync_id)
  EchosyncMedia  -> local_media table  (physical telemetry, keyed by media_id)
"""

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from core.database.repositories.track_repo import TrackRepository, bulk_upsert_tracks
from core.database.utils import calculate_safe_batch_size
from core.db.echo_sync_track import EchosyncMedia, EchosyncTrack
from database.music_database import get_database

logger = logging.getLogger("ingestion_orchestrator")


def _parse_telemetry_dict(raw_dict: dict[str, Any]) -> EchosyncTrack | None:
    """
    Parse a single raw FFI PyDict into an EchosyncTrack with attached EchosyncMedia objects.

    Handles two input shapes:
    1. Rust FFI flat dict (legacy / current Rust engine output):
       {"title": "...", "artist": "...", "file_path": "/music/track.flac", "duration_ms": 240000, ...}
    2. Plugin SDK structured dict (new 2-Model format):
       {"raw_title": "...", "artist_name": "...", "album_title": "...",
        "media": [{"file_path": "/music/track.flac", "bitrate": 1411, ...}]}
    """
    try:
        # --- Extract and build media list first ---
        raw_media = raw_dict.pop("media", []) or []
        media_list: list[EchosyncMedia] = []
        for m in raw_media:
            if isinstance(m, dict):
                try:
                    media_list.append(EchosyncMedia.from_dict(m))
                except Exception as me:
                    logger.debug(f"Skipping malformed media entry: {me}")

        # --- Normalize flat FFI field names to EchosyncTrack constructor names ---
        # Unconditionally pop alias/computed fields so init=False fields are never passed to __init__
        title_val = (
            raw_dict.pop("raw_title", None)
            or raw_dict.pop("title", None)
            or "Unknown Title"
        )
        artist_val = (
            raw_dict.pop("artist_name", None)
            or raw_dict.pop("artist", None)
            or "Unknown Artist"
        )
        album_val = (
            raw_dict.pop("album_title", None)
            or raw_dict.pop("album", None)
            or "Unknown Album"
        )
        duration_val = raw_dict.pop("duration_ms", None) or raw_dict.pop(
            "duration", None
        )
        mbid_val = raw_dict.pop("musicbrainz_id", None) or raw_dict.pop("mbid", None)
        year_val = raw_dict.pop("year", None) or raw_dict.pop("release_year", None)

        # Always strip non-init/computed fields (like display_title, media_ids)
        raw_dict.pop("display_title", None)
        raw_dict.pop("media_ids", None)

        # Set mandatory constructor fields
        raw_dict["raw_title"] = title_val
        raw_dict["artist_name"] = artist_val
        raw_dict["album_title"] = album_val
        if duration_val is not None:
            raw_dict["duration"] = duration_val
        if mbid_val is not None:
            raw_dict["musicbrainz_id"] = mbid_val
        if year_val is not None:
            raw_dict["release_year"] = int(year_val)

        # Hoist flat physical file fields into an EchosyncMedia if no media list was given
        flat_file_path = raw_dict.pop("file_path", None)
        flat_file_format = raw_dict.pop("file_format", None) or raw_dict.pop(
            "codec", None
        )
        flat_bitrate = raw_dict.pop("bitrate", None)
        flat_sample_rate = raw_dict.pop("sample_rate", None)
        flat_bit_depth = raw_dict.pop("bit_depth", None)
        flat_channels = raw_dict.pop("channels", None)
        flat_file_size = raw_dict.pop("file_size_bytes", None) or raw_dict.pop(
            "file_size", None
        )

        if flat_file_path and not media_list:
            media_list.append(
                EchosyncMedia(
                    file_path=flat_file_path,
                    file_format=flat_file_format,
                    bitrate=flat_bitrate,
                    sample_rate=flat_sample_rate,
                    bit_depth=flat_bit_depth,
                    channels=flat_channels,
                    file_size_bytes=flat_file_size,
                )
            )

        # Filter strictly by dataclass fields where f.init is True
        import dataclasses

        valid_init_fields = {
            f.name for f in dataclasses.fields(EchosyncTrack) if f.init
        }
        clean_data = {k: v for k, v in raw_dict.items() if k in valid_init_fields}

        track = EchosyncTrack(**clean_data)
        track.media = media_list
        return track
    except Exception as e:
        logger.warning(f"Skipping invalid telemetry record: {e} | data={raw_dict}")
        return None


class IngestionOrchestrator:
    """
    Orchestrates high-throughput telemetry ingestion with dynamic chunking to prevent
    database locking and SQLite parameter count limits.
    """

    def __init__(
        self,
        batch_size: int | None = None,
        session_factory: Callable[[], Session] | None = None,
    ):
        self.batch_size = (
            batch_size
            if batch_size is not None
            else calculate_safe_batch_size(column_count=10)
        )
        self.session_factory = session_factory or (lambda: get_database().get_session())

    def ingest_telemetry_batch(self, pydict_batch: list[dict[str, Any]]) -> int:
        """
        Process a list of PyDict records yielded by the Rust FFI, parse into the
        2-Model structure, and UPSERT into the database.
        """
        if not pydict_batch:
            return 0

        tracks: list[EchosyncTrack] = []
        for raw_dict in pydict_batch:
            # Work on a copy so we don't mutate the caller's dict
            track = _parse_telemetry_dict(dict(raw_dict))
            if track is not None:
                tracks.append(track)

        if not tracks:
            return 0

        session = self.session_factory()
        try:
            total_upserted = 0
            for i in range(0, len(tracks), self.batch_size):
                chunk = tracks[i : i + self.batch_size]
                TrackRepository.resolve_artists_and_albums(session, chunk)
                affected = bulk_upsert_tracks(session, chunk)
                session.commit()
                total_upserted += affected

            logger.info(
                f"Ingested {total_upserted} tracks "
                f"({sum(len(t.media) for t in tracks)} media files) "
                f"from {len(tracks)} telemetry records."
            )
            return total_upserted
        except Exception as e:
            session.rollback()
            logger.error(f"Failed during ingestion transaction: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def create_telemetry_callback(self) -> Any:
        """
        Create a streaming telemetry callback that buffers incoming PyDict batches
        and triggers a UPSERT transaction whenever the buffer reaches batch_size records.
        """
        buffer: list[dict[str, Any]] = []

        def callback(pydict_list: list[dict[str, Any]]) -> None:
            buffer.extend(pydict_list)
            while len(buffer) >= self.batch_size:
                chunk = buffer[: self.batch_size]
                del buffer[: self.batch_size]
                self.ingest_telemetry_batch(chunk)

        def flush() -> int:
            if buffer:
                count = self.ingest_telemetry_batch(buffer)
                buffer.clear()
                return count
            return 0

        callback.flush = flush  # type: ignore
        return callback
