"""
SQLAlchemy 2.0 High-Performance UPSERT Repository for Track & LocalMedia ingestion.

2-Model Architecture:
- EchosyncTrack: logical music metadata -> tracks table (keyed by sync_id)
- EchosyncMedia: physical file telemetry -> local_media table (keyed by media_id)
"""
from typing import List, Optional, Any
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import or_, and_, Integer

from database.music_database import Track, LocalMedia, Artist, Album, TrackArtist, generate_nanoid
from database import _canonicalize_path
# Canonical model: EchosyncTrack + EchosyncMedia from core.db
from core.db.echo_sync_track import EchosyncTrack, EchosyncMedia
from core.matching_engine.text_utils import split_artists

from core.database.utils import calculate_safe_batch_size


class TrackRepository:
    """
    Repository providing batched SQLite UPSERT queries using SQLAlchemy 2.0 Core expressions.
    Enforces strict 2-Model separation: Track rows hold metadata only, LocalMedia rows hold
    physical file telemetry.
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session

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
    def resolve_artists_and_albums(cls, session: Session, tracks: List[EchosyncTrack]) -> None:
        """
        Batch resolve and upsert missing Artists and Albums, attaching their IDs 
        back onto the EchosyncTrack instances.
        """
        if not tracks:
            return

        default_artist_id = cls.get_or_create_default_artist(session)
        
        # ── Step 0a: Batch Resolve & Upsert Atomic Artists ────────────────────
        all_atomic_artist_names = set()
        for t in tracks:
            art = (
                getattr(t, "artist_name", None)
                or getattr(t, "artist", None)
                or getattr(t, "album_artist", None)
            )
            if art and art.strip() and art.strip().lower() != "unknown artist":
                tokens = split_artists(art.strip())
                if not tokens:
                    tokens = [art.strip()]
                t._raw_artist_tokens = tokens
                for tok in tokens:
                    all_atomic_artist_names.add(tok)
            else:
                t._raw_artist_tokens = ["Unknown Artist"]

            # Also ensure album_artist (TPE2) is collected if present
            alb_art = getattr(t, "album_artist", None)
            if alb_art and alb_art.strip() and alb_art.strip().lower() != "unknown artist":
                all_atomic_artist_names.add(alb_art.strip())

        artist_map = {}  # lower name -> artist_id
        if all_atomic_artist_names:
            existing_artists = session.query(Artist).filter(
                Artist.name.in_(list(all_atomic_artist_names))
            ).all()
            for a in existing_artists:
                artist_map[a.name.lower()] = a.id
                if a.normalized_name:
                    artist_map[a.normalized_name.lower()] = a.id

            missing_artists = [name for name in all_atomic_artist_names if name.lower() not in artist_map]
            if missing_artists:
                for name in missing_artists:
                    new_artist = Artist(name=name)
                    session.add(new_artist)
                session.flush()
                new_artists_db = session.query(Artist).filter(
                    Artist.name.in_(missing_artists)
                ).all()
                for a in new_artists_db:
                    artist_map[a.name.lower()] = a.id
                    if a.normalized_name:
                        artist_map[a.normalized_name.lower()] = a.id

        # Update track objects with resolved primary artist_id and associations
        for t in tracks:
            tokens = getattr(t, "_raw_artist_tokens", ["Unknown Artist"])
            primary_name = tokens[0] if tokens else "Unknown Artist"
            t.artist_id = artist_map.get(primary_name.lower(), default_artist_id)

            associations = []
            for i, tok in enumerate(tokens):
                a_id = artist_map.get(tok.lower(), default_artist_id)
                role = "primary" if i == 0 else "featured"
                associations.append((a_id, role, i))
            t._resolved_artist_associations = associations

        # ── Step 0b: Batch Resolve & Upsert Albums ────────────────────────────
        # Decouple TPE1 (performer) from TPE2 (album artist / compilation).
        # For compilation albums (e.g. "Various Artists"), Album.artist_id attaches to
        # the compilation artist entity while Track.artist_id remains the track performer.
        album_pairs = set()  # (album_title, album_artist_id)
        for t in tracks:
            alb_art = getattr(t, "album_artist", None)
            if alb_art and alb_art.strip():
                album_artist_id = artist_map.get(alb_art.strip().lower(), t.artist_id)
            else:
                album_artist_id = getattr(t, "artist_id", None) or default_artist_id

            t._resolved_album_artist_id = album_artist_id
            alb = getattr(t, "album_title", None) or getattr(t, "album", None)
            if alb and alb.strip():
                alb_clean = alb.strip()
                album_pairs.add((alb_clean, album_artist_id))

        album_map = {}  # (album_title.lower(), album_artist_id) -> album_id
        if album_pairs:
            all_album_titles = list({pair[0] for pair in album_pairs})
            all_artist_ids = list({pair[1] for pair in album_pairs})
            existing_albums = session.query(Album).filter(
                Album.title.in_(all_album_titles),
                Album.artist_id.in_(all_artist_ids),
            ).all()
            for alb in existing_albums:
                album_map[(alb.title.lower(), alb.artist_id)] = alb.id

            missing_albums = [pair for pair in album_pairs if (pair[0].lower(), pair[1]) not in album_map]
            if missing_albums:
                for title, a_id in missing_albums:
                    new_album = Album(title=title, artist_id=a_id)
                    session.add(new_album)
                session.flush()
                new_albums_db = session.query(Album).filter(
                    Album.title.in_([p[0] for p in missing_albums]),
                    Album.artist_id.in_([p[1] for p in missing_albums]),
                ).all()
                for alb in new_albums_db:
                    album_map[(alb.title.lower(), alb.artist_id)] = alb.id

        # Update track objects with resolved IDs
        for t in tracks:
            alb_str = (getattr(t, "album_title", None) or getattr(t, "album", "") or "").strip().lower()
            alb_aid = getattr(t, "_resolved_album_artist_id", t.artist_id)
            t.album_id = album_map.get((alb_str, alb_aid))

    def bulk_upsert_tracks(self_or_cls, session_or_tracks: Any, tracks: Optional[List[EchosyncTrack]] = None) -> int:
        if isinstance(self_or_cls, Session):
            # Called as TrackRepository.bulk_upsert_tracks(session, tracks)
            tracks_list = session_or_tracks if isinstance(session_or_tracks, list) else (tracks or [])
            return TrackRepository._execute_bulk_upsert(self_or_cls, tracks_list)

        if isinstance(self_or_cls, TrackRepository):
            if tracks is None and isinstance(session_or_tracks, list):
                # Called as repo.bulk_upsert_tracks(tracks)
                if self_or_cls.session is None:
                    raise ValueError("TrackRepository instance was initialized without a Session")
                return TrackRepository._execute_bulk_upsert(self_or_cls.session, session_or_tracks)
            elif isinstance(session_or_tracks, Session) and isinstance(tracks, list):
                # Called as repo.bulk_upsert_tracks(session, tracks)
                return TrackRepository._execute_bulk_upsert(session_or_tracks, tracks)

        if isinstance(session_or_tracks, Session) and isinstance(tracks, list):
            return TrackRepository._execute_bulk_upsert(session_or_tracks, tracks)

        return 0

    @classmethod
    def _execute_bulk_upsert(cls, session: Session, tracks: List[EchosyncTrack]) -> int:
        if not tracks:
            return 0

        now = datetime.now(timezone.utc)
        default_artist_id = cls.get_or_create_default_artist(session)

        # Ensure artists and albums are resolved if not already set
        if any(getattr(t, "artist_id", None) is None for t in tracks):
            cls.resolve_artists_and_albums(session, tracks)

        # Batch lookup existing tracks by (normalized_title, artist_id, normalized_edition), sync_id, or file_path
        batch_titles = set()
        batch_artist_ids = set()
        batch_sync_ids = set()
        batch_file_paths = set()

        for t in tracks:
            norm_title = (getattr(t, "normalized_title", None) or getattr(t, "title", None) or getattr(t, "raw_title", "") or "").strip().lower()
            if norm_title:
                batch_titles.add(norm_title)
            if getattr(t, "artist_id", None):
                batch_artist_ids.add(t.artist_id)
            raw_sid = getattr(t, "sync_id", None)
            if raw_sid and not raw_sid.startswith("ss:"):
                batch_sync_ids.add(raw_sid.split("?")[0])

            for m in getattr(t, "media", []) or []:
                if getattr(m, "file_path", None):
                    batch_file_paths.add(_canonicalize_path(m.file_path))
            if getattr(t, "file_path", None):
                batch_file_paths.add(_canonicalize_path(t.file_path))

        existing_track_map = {}  # (norm_title, artist_id, norm_edition) -> (sync_id, duration)
        existing_sync_ids_in_db = set()
        media_path_to_track_info = {}  # file_path -> (sync_id, track_id, duration)

        if batch_file_paths:
            lm_rows = session.execute(
                select(LocalMedia.file_path, Track.sync_id, Track.id, Track.duration)
                .join(Track, LocalMedia.track_id == Track.id)
                .where(LocalMedia.file_path.in_(list(batch_file_paths)))
            ).all()
            for row in lm_rows:
                media_path_to_track_info[row.file_path] = (row.sync_id, row.id, row.duration)
                existing_sync_ids_in_db.add(row.sync_id)

        if batch_titles and batch_artist_ids:
            found_tracks = session.query(Track).filter(
                Track.normalized_title.in_(list(batch_titles)),
                Track.artist_id.in_(list(batch_artist_ids)),
            ).all()
            for ft in found_tracks:
                ft_norm_title = (ft.normalized_title or ft.title.lower() or "").strip().lower()
                ft_norm_ed = (ft.edition or "").strip().lower()
                existing_track_map[(ft_norm_title, ft.artist_id, ft_norm_ed)] = (ft.sync_id, ft.duration)
                existing_sync_ids_in_db.add(ft.sync_id)

        if batch_sync_ids:
            found_by_sync_id = session.query(Track).filter(
                Track.sync_id.in_(list(batch_sync_ids))
            ).all()
            for ft in found_by_sync_id:
                ft_norm_title = (ft.normalized_title or ft.title.lower() or "").strip().lower()
                ft_norm_ed = (ft.edition or "").strip().lower()
                existing_track_map[(ft_norm_title, ft.artist_id, ft_norm_ed)] = (ft.sync_id, ft.duration)
                existing_sync_ids_in_db.add(ft.sync_id)

        # Build / resolve sync_id for each track (ensures unique NanoIDs and version separation)
        def _get_or_assign_sync_id(t: EchosyncTrack) -> str:
            # 1. Prioritize existing physical file_path binding in DB
            t_paths = []
            for m in getattr(t, "media", []) or []:
                if getattr(m, "file_path", None):
                    t_paths.append(_canonicalize_path(m.file_path))
            if getattr(t, "file_path", None):
                t_paths.append(_canonicalize_path(t.file_path))

            for path in t_paths:
                if path in media_path_to_track_info:
                    sid, _, _ = media_path_to_track_info[path]
                    t.sync_id = sid
                    return sid

            # 2. Prioritize explicitly known sync_id from DB
            raw_sid = getattr(t, "sync_id", None)
            if raw_sid and not raw_sid.startswith("ss:") and raw_sid.split("?")[0] in existing_sync_ids_in_db:
                sid = raw_sid.split("?")[0]
                t.sync_id = sid
                return sid

            # 3. Match against (normalized_title, artist_id, normalized_edition)
            norm_title = (getattr(t, "normalized_title", None) or getattr(t, "title", None) or getattr(t, "raw_title", "") or "").strip().lower()
            a_id = getattr(t, "artist_id", None) or default_artist_id
            norm_ed = (getattr(t, "edition", None) or "").strip().lower()
            key = (norm_title, a_id, norm_ed)
            t_dur = getattr(t, "duration_ms", None) or getattr(t, "duration", None)

            if key in existing_track_map:
                sid, existing_dur = existing_track_map[key]
                # If duration delta is significant (> 5000ms), decouple into separate track
                if existing_dur is not None and t_dur is not None and abs(t_dur - existing_dur) > 5000:
                    sid = generate_nanoid()
                    # Store distinct key with duration tag
                    existing_track_map[(norm_title, a_id, f"{norm_ed}_{t_dur}")] = (sid, t_dur)
                else:
                    if sid.startswith("ss:"):
                        sid = generate_nanoid()
                        existing_track_map[key] = (sid, t_dur or existing_dur)
                t.sync_id = sid
                return sid

            # 4. Generate fresh NanoID if not already possessing a valid one
            if raw_sid and not raw_sid.startswith("ss:"):
                sid = raw_sid.split("?")[0]
            else:
                sid = generate_nanoid()

            existing_track_map[key] = (sid, t_dur)
            t.sync_id = sid
            return sid

        # --- Phase 1: Batch UPSERT tracks ---
        track_values = []
        sync_ids_in_batch = []
        seen_sync_ids = set()

        for t in tracks:
            sync_id = _get_or_assign_sync_id(t)
            sync_ids_in_batch.append(sync_id)
            if sync_id in seen_sync_ids:
                continue
            seen_sync_ids.add(sync_id)

            duration = getattr(t, "duration_ms", None) or getattr(t, "duration", None)
            mbid = getattr(t, "mbid", None) or getattr(t, "musicbrainz_id", None)
            track_title = getattr(t, "title", None) or getattr(t, "raw_title", None) or "Unknown Title"

            artist_id = getattr(t, "artist_id", None) or default_artist_id
            album_id = getattr(t, "album_id", None)
            norm_title = (getattr(t, "normalized_title", None) or track_title).strip().lower()

            track_values.append({
                "sync_id": sync_id,
                "title": track_title,
                "normalized_title": norm_title,
                "sort_title": getattr(t, "sort_title", None),
                "edition": getattr(t, "edition", None),
                "artist_id": artist_id,
                "album_id": album_id,
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
                    "sort_title": func.coalesce(stmt.excluded.sort_title, Track.sort_title),
                    "edition": func.coalesce(stmt.excluded.edition, Track.edition),
                    "artist_id": func.coalesce(stmt.excluded.artist_id, Track.artist_id),
                    "album_id": func.coalesce(stmt.excluded.album_id, Track.album_id),
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

        # --- Phase 1b: Batch UPSERT TrackArtist associations ---
        track_artist_values = []
        for t in tracks:
            sync_id = t.sync_id
            track_id = sync_id_to_track_id.get(sync_id)
            if not track_id:
                continue

            associations = getattr(t, "_resolved_artist_associations", None)
            if not associations:
                a_id = getattr(t, "artist_id", None) or default_artist_id
                associations = [(a_id, "primary", 0)]

            for a_id, role, pos in associations:
                track_artist_values.append({
                    "track_id": track_id,
                    "artist_id": a_id,
                    "role": role,
                    "position": pos,
                })

        if track_artist_values:
            ta_chunk_size = calculate_safe_batch_size(column_count=5)
            for i in range(0, len(track_artist_values), ta_chunk_size):
                ta_chunk = track_artist_values[i:i + ta_chunk_size]
                ta_stmt = sqlite_insert(TrackArtist).values(ta_chunk)
                ta_upsert = ta_stmt.on_conflict_do_update(
                    index_elements=["track_id", "artist_id", "role"],
                    set_={"position": ta_stmt.excluded.position},
                )
                session.execute(ta_upsert)

        media_values = []
        for t in tracks:
            sync_id = t.sync_id
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
                    channels=getattr(t, "channels", None),
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
                    "channels": getattr(m, "channels", None),
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
                        # Always refresh track_id and physical telemetry on conflict
                        "track_id": media_stmt.excluded.track_id,
                        "file_format": media_stmt.excluded.file_format,
                        "bitrate": media_stmt.excluded.bitrate,
                        "sample_rate": media_stmt.excluded.sample_rate,
                        "bit_depth": media_stmt.excluded.bit_depth,
                        "channels": media_stmt.excluded.channels,
                        "file_size_bytes": media_stmt.excluded.file_size_bytes,
                        "inode": media_stmt.excluded.inode,
                        "mtime": media_stmt.excluded.mtime,
                    }
                )
                session.execute(media_upsert)

        # --- Phase 3: Batch UPSERT ExternalIdentifiers ---
        from database.music_database import ExternalIdentifier
        track_id_to_media_id = {}
        if sync_id_to_track_id:
            batch_track_ids = list(sync_id_to_track_id.values())
            media_rows = session.execute(
                select(LocalMedia.track_id, LocalMedia.media_id).where(LocalMedia.track_id.in_(batch_track_ids))
            ).all()
            for row in media_rows:
                if row.track_id not in track_id_to_media_id:
                    track_id_to_media_id[row.track_id] = row.media_id

        ident_values = []
        for t in tracks:
            sync_id = t.sync_id
            track_id = sync_id_to_track_id.get(sync_id)
            if not track_id:
                continue
            media_id = track_id_to_media_id.get(track_id)
            if not media_id:
                continue

            identifiers = getattr(t, "identifiers", []) or []
            for ident in identifiers:
                if isinstance(ident, dict):
                    source = ident.get("plugin_source") or ident.get("source")
                    item_id = ident.get("plugin_item_id") or ident.get("item_id")
                    raw_data = ident.get("raw_data")
                    if source and item_id:
                        ident_values.append({
                            "media_id": media_id,
                            "plugin_source": source,
                            "plugin_item_id": str(item_id),
                            "raw_data": raw_data,
                        })

        if ident_values:
            ident_chunk_size = calculate_safe_batch_size(column_count=4)
            for i in range(0, len(ident_values), ident_chunk_size):
                i_chunk = ident_values[i:i + ident_chunk_size]
                ident_stmt = sqlite_insert(ExternalIdentifier).values(i_chunk)
                ident_upsert = ident_stmt.on_conflict_do_update(
                    constraint="uq_plugin_item",
                    set_={
                        "media_id": ident_stmt.excluded.media_id,
                        "raw_data": ident_stmt.excluded.raw_data,
                    }
                )
                session.execute(ident_upsert)

        return affected_rows

    @classmethod
    def decouple_collapsed_media(cls, session: Session, duration_threshold_ms: int = 5000) -> int:
        """
        Scan database for Tracks with multiple LocalMedia files that have distinct
        editions or significant duration divergence (> threshold_ms), separating them
        into their own distinct Track entities with unique NanoIDs.
        """
        from sqlalchemy.orm import selectinload
        from core.matching_engine.text_utils import extract_version_info

        tracks_with_multi_media = (
            session.query(Track)
            .options(selectinload(Track.media_files))
            .filter(
                Track.id.in_(
                    session.query(LocalMedia.track_id)
                    .group_by(LocalMedia.track_id)
                    .having(func.count(LocalMedia.id) > 1)
                )
            )
            .all()
        )

        decoupled_count = 0
        now = datetime.now(timezone.utc)
        for parent_track in tracks_with_multi_media:
            media_files = list(parent_track.media_files)
            if len(media_files) <= 1:
                continue

            # First media file stays with the parent track
            # Subsequent media files with differing edition or path are decoupled
            for media in media_files[1:]:
                path_str = media.file_path or ""
                _, extracted_ver = extract_version_info(path_str)
                extracted_ed = extracted_ver or "Remix"

                new_sync_id = generate_nanoid(8)
                new_track = Track(
                    sync_id=new_sync_id,
                    title=parent_track.title,
                    normalized_title=parent_track.normalized_title,
                    sort_title=parent_track.sort_title,
                    artist_id=parent_track.artist_id,
                    album_id=parent_track.album_id,
                    duration=parent_track.duration,
                    edition=extracted_ed,
                    track_number=parent_track.track_number,
                    disc_number=parent_track.disc_number,
                    musicbrainz_id=parent_track.musicbrainz_id,
                    isrc=parent_track.isrc,
                    added_at=media.added_at or parent_track.added_at or now,
                )
                session.add(new_track)
                session.flush()

                media.track_id = new_track.id
                decoupled_count += 1

        if decoupled_count > 0:
            session.flush()

        return decoupled_count


def bulk_upsert_tracks(session: Session, tracks: List[EchosyncTrack]) -> int:
    """Standalone wrapper function for TrackRepository.bulk_upsert_tracks."""
    return TrackRepository.bulk_upsert_tracks(session, tracks)
