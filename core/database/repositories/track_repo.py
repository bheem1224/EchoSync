"""
SQLAlchemy 2.0 High-Performance UPSERT Repository for Track & LocalMedia ingestion.

2-Model Architecture:
- EchosyncTrack: logical music metadata -> tracks table (keyed by sync_id)
- EchosyncMedia: physical file telemetry -> local_media table (keyed by media_id)
"""
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import or_, and_, Integer

from database.music_database import Track, LocalMedia, Artist, generate_nanoid
from database import _canonicalize_path
# Canonical model: EchosyncTrack + EchosyncMedia from core.db
from core.db.echo_sync_track import EchosyncTrack, EchosyncMedia

from core.database.utils import calculate_safe_batch_size


class TrackRepository:
    """
    Repository providing batched SQLite UPSERT queries using SQLAlchemy 2.0 Core expressions.
    Enforces strict 2-Model separation: Track rows hold metadata only, LocalMedia rows hold
    physical file telemetry.
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

    # --- UUID Lookup Helpers ---

    @staticmethod
    def get_track_by_sync_id(session: Session, sync_id: str) -> Optional[Track]:
        """Fetch a Track by its canonical sync_id. Strips query params from sync_id."""
        clean_sync_id = sync_id.split("?")[0]
        return session.query(Track).filter_by(sync_id=clean_sync_id).first()

    @staticmethod
    def get_media_by_media_id(session: Session, media_id: str) -> Optional[LocalMedia]:
        """Fetch a LocalMedia record by its canonical media_id (NanoID)."""
        return session.query(LocalMedia).filter_by(media_id=media_id).first()

    @staticmethod
    def get_media_for_track(session: Session, track_id: int) -> List[LocalMedia]:
        """Fetch all LocalMedia records associated with a Track by its internal PK."""
        return session.query(LocalMedia).filter_by(track_id=track_id).all()

    # --- Enhancement Query ---

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

    # --- Core Upsert ---

    @classmethod
    def bulk_upsert_tracks(cls, session: Session, tracks: List[EchosyncTrack]) -> int:
        """
        Batched SQLite UPSERT using sqlalchemy.dialects.sqlite.insert.

        2-Model contract:
        - Phase 1: Batch UPSERT all tracks into the `tracks` table using sync_id.
        - Phase 2: For each EchosyncMedia in track.media, UPSERT into `local_media`
                   using file_path as conflict key. Resolves track_id via a single
                   WHERE sync_id IN (...) bulk query (no N+1).

        Metadata preservation: COALESCE ensures existing non-null values are never
        overwritten by incoming None/empty values.
        """
        if not tracks:
            return 0

        default_artist_id = cls.get_or_create_default_artist(session)
        now = datetime.now(timezone.utc)

        # Build sync_id for each track (strips query params)
        def _build_sync_id(t: EchosyncTrack) -> str:
            raw_sid = getattr(t, "sync_id", None)
            if raw_sid:
                return raw_sid.split("?")[0]
            title_val = getattr(t, "title", None) or getattr(t, "raw_title", "") or ""
            artist_val = getattr(t, "artist_name", None) or getattr(t, "artist", "") or ""
            return f"ss:track:meta:{title_val.lower()}:{artist_val.lower()}"

        # --- Phase 1: Batch UPSERT tracks ---
        track_values = []
        sync_ids_in_batch = []
        for t in tracks:
            sync_id = _build_sync_id(t)
            sync_ids_in_batch.append(sync_id)
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

        affected_rows = 0
        track_chunk_size = calculate_safe_batch_size(column_count=10)
        for i in range(0, len(track_values), track_chunk_size):
            chunk = track_values[i:i + track_chunk_size]
            stmt = sqlite_insert(Track).values(chunk)
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["sync_id"],
                set_={
                    "duration": stmt.excluded.duration,
                    "title": func.coalesce(stmt.excluded.title, Track.title),
                    "track_number": func.coalesce(stmt.excluded.track_number, Track.track_number),
                    "disc_number": func.coalesce(stmt.excluded.disc_number, Track.disc_number),
                    "musicbrainz_id": func.coalesce(stmt.excluded.musicbrainz_id, Track.musicbrainz_id),
                    "isrc": func.coalesce(stmt.excluded.isrc, Track.isrc),
                }
            )
            result = session.execute(upsert_stmt)
            affected_rows += result.rowcount

        # Flush to ensure track rows are committed before FK resolution
        session.flush()

        # --- Phase 2: Batch UPSERT LocalMedia (2-Model split) ---
        # Resolve sync_id -> Track.id with a single bulk SELECT (no N+1)
        sync_id_to_track_id = {}
        if sync_ids_in_batch:
            rows = session.execute(
                select(Track.sync_id, Track.id).where(Track.sync_id.in_(sync_ids_in_batch))
            ).all()
            sync_id_to_track_id = {row.sync_id: row.id for row in rows}

        media_values = []
        for t in tracks:
            sync_id = _build_sync_id(t)
            track_id = sync_id_to_track_id.get(sync_id)
            if not track_id:
                continue  # Track insert failed or was filtered — skip media

            media_list: List[EchosyncMedia] = list(getattr(t, "media", []) or [])
            # Fallback for legacy objects that possess a flat file_path attribute
            if not media_list and getattr(t, "file_path", None):
                flat_path = getattr(t, "file_path")
                media_list.append(EchosyncMedia(
                    file_path=flat_path,
                    media_id=getattr(t, "media_id", None) or generate_nanoid(),
                    file_format=getattr(t, "file_format", None) or getattr(t, "codec", None),
                    bitrate=getattr(t, "bitrate", None),
                    sample_rate=getattr(t, "sample_rate", None),
                    bit_depth=getattr(t, "bit_depth", None),
                    file_size_bytes=getattr(t, "file_size_bytes", None) or getattr(t, "file_size", None),
                ))

            for m in media_list:
                raw_path = getattr(m, "file_path", None)
                if not raw_path:
                    continue  # No physical file — skip (streaming-only media)

                canon_path = _canonicalize_path(raw_path)
                media_values.append({
                    "media_id": m.media_id if m.media_id else generate_nanoid(),
                    "track_id": track_id,
                    "file_path": canon_path,
                    "file_format": getattr(m, "file_format", None),
                    "bitrate": getattr(m, "bitrate", None),
                    "sample_rate": getattr(m, "sample_rate", None),
                    "bit_depth": getattr(m, "bit_depth", None),
                    "file_size_bytes": getattr(m, "file_size_bytes", None),
                    "inode": getattr(m, "inode", None),
                    "mtime": getattr(m, "mtime", None),
                    "added_at": now,
                })

        if media_values:
            media_chunk_size = calculate_safe_batch_size(column_count=10)
            for i in range(0, len(media_values), media_chunk_size):
                m_chunk = media_values[i:i + media_chunk_size]
                media_stmt = sqlite_insert(LocalMedia).values(m_chunk)
                media_upsert = media_stmt.on_conflict_do_update(
                    index_elements=["file_path"],
                    set_={
                        # Always refresh physical telemetry on conflict
                        "file_format": media_stmt.excluded.file_format,
                        "bitrate": media_stmt.excluded.bitrate,
                        "sample_rate": media_stmt.excluded.sample_rate,
                        "bit_depth": media_stmt.excluded.bit_depth,
                        "file_size_bytes": media_stmt.excluded.file_size_bytes,
                        "inode": media_stmt.excluded.inode,
                        "mtime": media_stmt.excluded.mtime,
                    }
                )
                session.execute(media_upsert)

        return affected_rows


def bulk_upsert_tracks(session: Session, tracks: List[EchosyncTrack]) -> int:
    """Standalone wrapper function for TrackRepository.bulk_upsert_tracks."""
    return TrackRepository.bulk_upsert_tracks(session, tracks)
