"""
SQLAlchemy 2.0 High-Performance UPSERT Repository for Track & LocalMedia ingestion.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from database.music_database import Track, LocalMedia, Artist
from database import _canonicalize_path
from core.models import EchoSyncTrack
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_, Integer

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
    def get_tracks_for_enhancement(
        cls, session: Session, batch_size: int = 100, check_all_files: bool = False
    ) -> List[Track]:
        query = session.query(Track).join(LocalMedia, LocalMedia.track_id == Track.id)
        query = query.options(joinedload(Track.media_files))

        if not check_all_files:
            from core.hook_manager import hook_manager
            required_keys = hook_manager.apply_filters('register_metadata_requirements', [])

            MAX_REATTEMPTS = 5
            needs_identification = or_(
                Track.musicbrainz_id.is_(None),
                and_(
                    Track.musicbrainz_id == "NOT_FOUND",
                    func.coalesce(
                        func.json_extract(Track.metadata_status, '$.enhancement_attempts'),
                        0,
                    ).cast(Integer) < MAX_REATTEMPTS,
                ),
            )
            conditions = [needs_identification]
            for key in required_keys:
                conditions.append(
                    and_(
                        Track.musicbrainz_id.isnot(None),
                        Track.musicbrainz_id != "NOT_FOUND",
                        func.json_extract(Track.metadata_status, f'$.{key}').is_(None),
                    )
                )

            _va_artist_ids_subq = (
                session.query(Artist.id)
                .filter(Artist.name.ilike('various artist%'))
            )
            conditions.append(
                and_(
                    Track.artist_id.in_(_va_artist_ids_subq),
                    func.json_extract(
                        Track.metadata_status, '$.artist_fixed_from_tags'
                    ).is_(None),
                )
            )

            query = query.filter(or_(*conditions))

        return query.limit(batch_size).all()

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
            f_path = getattr(t, "file_path", None)
            if not f_path and getattr(t, "media", None):
                m_list = getattr(t, "media")
                if m_list and hasattr(m_list[0], "file_path"):
                    f_path = m_list[0].file_path

            if hasattr(t, "compute_sync_id"):
                sync_id = t.compute_sync_id()
            elif getattr(t, "sync_id", None):
                sync_id = t.sync_id
            elif f_path:
                sync_id = f"ss:track:file:{_canonicalize_path(f_path)}"
            else:
                title_val = getattr(t, "title", None) or getattr(t, "raw_title", "")
                artist_val = getattr(t, "artist_name", None) or getattr(t, "artist", "")
                sync_id = f"ss:track:meta:{title_val.lower()}:{artist_val.lower()}"

            duration = getattr(t, "duration_ms", None) or getattr(t, "duration", None)
            mbid = getattr(t, "mbid", None) or getattr(t, "musicbrainz_id", None)
            track_title = getattr(t, "title", None) or getattr(t, "raw_title", None) or "Unknown Title"
            track_values.append({
                "sync_id": sync_id,
                "title": track_title,
                "normalized_title": track_title.lower(),
                "artist_id": default_artist_id,
                "duration": duration,
                "track_number": getattr(t, "track_number", None),
                "disc_number": getattr(t, "disc_number", None),
                "musicbrainz_id": mbid,
                "isrc": getattr(t, "isrc", None),
                "added_at": now,
            })

        from core.database.utils import calculate_safe_batch_size
        
        # --- SQLAlchemy 2.0 UPSERT Statement for Tracks ---
        affected_rows = 0
        track_chunk_size = calculate_safe_batch_size(column_count=10)
        for i in range(0, len(track_values), track_chunk_size):
            chunk = track_values[i:i + track_chunk_size]
            stmt = sqlite_insert(Track).values(chunk)
    
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
            affected_rows += result.rowcount

        # Also upsert LocalMedia technical records if file_path is present
        media_values = []
        for t in tracks:
            f_path = getattr(t, "file_path", None)
            first_media = None
            if not f_path and getattr(t, "media", None):
                m_list = getattr(t, "media")
                if m_list and hasattr(m_list[0], "file_path"):
                    first_media = m_list[0]
                    f_path = first_media.file_path
            if f_path:
                canon_path = _canonicalize_path(f_path)
                if hasattr(t, "compute_sync_id"):
                    s_id = t.compute_sync_id()
                elif getattr(t, "sync_id", None):
                    s_id = t.sync_id
                elif f_path:
                    s_id = f"ss:track:file:{canon_path}"
                else:
                    title_val = getattr(t, "title", None) or getattr(t, "raw_title", "")
                    artist_val = getattr(t, "artist_name", None) or getattr(t, "artist", "")
                    s_id = f"ss:track:meta:{title_val.lower()}:{artist_val.lower()}"
                track_obj = session.query(Track).filter_by(sync_id=s_id).first()
                if track_obj:
                    m_obj = first_media if first_media is not None else t
                    media_values.append({
                        "track_id": track_obj.id,
                        "file_path": canon_path,
                        "file_format": getattr(m_obj, "file_format", None) or getattr(m_obj, "codec", None),
                        "bitrate": getattr(m_obj, "bitrate", None) or getattr(m_obj, "bitrate_kbps", None),
                        "sample_rate": getattr(m_obj, "sample_rate", None) or getattr(m_obj, "sample_rate_hz", None),
                        "bit_depth": getattr(m_obj, "bit_depth", None),
                        "file_size_bytes": getattr(m_obj, "file_size_bytes", None),
                        "added_at": now,
                    })

        if media_values:
            media_chunk_size = calculate_safe_batch_size(column_count=8)
            for i in range(0, len(media_values), media_chunk_size):
                m_chunk = media_values[i:i + media_chunk_size]
                media_stmt = sqlite_insert(LocalMedia).values(m_chunk)
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
