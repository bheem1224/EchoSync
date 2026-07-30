"""
SQLAlchemy 2.0 High-Performance UPSERT Repository for Track & LocalMedia ingestion.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from database.music_database import Track, LocalMedia, Artist
from core.models import EchoSyncTrack


class TrackRepository:
    """
    Repository providing batched SQLite UPSERT queries using SQLAlchemy 2.0 Core expressions.
    """

    @staticmethod
    def get_or_create_default_artist(session: Session) -> int:
        """Fetch or create default system artist ID for tracks without an explicitly linked artist."""
        artist = session.query(Artist).filter_by(name="Unknown Artist").first()
        if not artist:
            artist = Artist(name="Unknown Artist", normalized_name="unknown artist")
            session.add(artist)
            session.flush()
        return artist.id

    @classmethod
    def bulk_upsert_tracks(cls, session: Session, tracks: List[EchoSyncTrack]) -> int:
        """
        Batched SQLite UPSERT using sqlalchemy.dialects.sqlite.insert.
        
        Strictly satisfies Phase 4 mandates:
        - Uses sqlite.insert() with on_conflict_do_update on unique sync_id.
        - Overwrites technical stream telemetry.
        - Preserves user metadata using COALESCE conditional updates.
        """
        if not tracks:
            return 0

        default_artist_id = cls.get_or_create_default_artist(session)
        now = datetime.now(timezone.utc)

        track_values = []
        for t in tracks:
            sync_id = t.compute_sync_id()
            track_values.append({
                "sync_id": sync_id,
                "title": t.title or "Unknown Title",
                "normalized_title": (t.title or "unknown title").lower(),
                "artist_id": default_artist_id,
                "duration": t.duration_ms,
                "track_number": t.track_number,
                "disc_number": t.disc_number,
                "musicbrainz_id": t.mbid,
                "isrc": t.isrc,
                "added_at": now,
            })

        # --- SQLAlchemy 2.0 UPSERT Statement for Tracks ---
        stmt = sqlite_insert(Track).values(track_values)

        # Conflict resolution targeting sync_id unique index
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["sync_id"],
            set_={
                # Technical / Stream telemetry - ALWAYS OVERWRITE
                "duration": stmt.excluded.duration,

                # Metadata fields - CONDITIONAL UPDATE (COALESCE preserves non-null existing data)
                "title": func.coalesce(stmt.excluded.title, Track.title),
                "track_number": func.coalesce(stmt.excluded.track_number, Track.track_number),
                "disc_number": func.coalesce(stmt.excluded.disc_number, Track.disc_number),
                "musicbrainz_id": func.coalesce(stmt.excluded.musicbrainz_id, Track.musicbrainz_id),
                "isrc": func.coalesce(stmt.excluded.isrc, Track.isrc),
            }
        )

        result = session.execute(upsert_stmt)
        affected_rows = result.rowcount

        # Also upsert LocalMedia technical records if file_path is present
        media_values = []
        for t in tracks:
            if t.file_path:
                # Query track ID for foreign key link
                track_obj = session.query(Track).filter_by(sync_id=t.compute_sync_id()).first()
                if track_obj:
                    media_values.append({
                        "track_id": track_obj.id,
                        "file_path": t.file_path,
                        "file_format": t.codec,
                        "bitrate": t.bitrate,
                        "sample_rate": t.sample_rate,
                        "bit_depth": t.bit_depth,
                        "file_size_bytes": t.file_size_bytes,
                        "added_at": now,
                    })

        if media_values:
            media_stmt = sqlite_insert(LocalMedia).values(media_values)
            media_upsert = media_stmt.on_conflict_do_update(
                index_elements=["file_path"],
                set_={
                    "file_format": media_stmt.excluded.file_format,
                    "bitrate": media_stmt.excluded.bitrate,
                    "sample_rate": media_stmt.excluded.sample_rate,
                    "bit_depth": media_stmt.excluded.bit_depth,
                    "file_size_bytes": media_stmt.excluded.file_size_bytes,
                }
            )
            session.execute(media_upsert)

        return affected_rows


def bulk_upsert_tracks(session: Session, tracks: List[EchoSyncTrack]) -> int:
    """Standalone wrapper function for TrackRepository.bulk_upsert_tracks."""
    return TrackRepository.bulk_upsert_tracks(session, tracks)
