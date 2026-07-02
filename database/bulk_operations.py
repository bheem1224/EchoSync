"""
Bulk import operations using SQLAlchemy 2.0 and LibraryManager.
Efficiently ingests EchosyncTrack objects into the database with caching.
"""
import unicodedata
from collections import defaultdict
from typing import List, Dict, Optional, Tuple, Callable, Iterable
from datetime import date, datetime
import time
from pathlib import Path

from sqlalchemy import select, func, delete
from sqlalchemy.orm import sessionmaker, Session, selectinload

from core.matching_engine.echo_sync_track import EchosyncTrack
from core.matching_engine import text_utils
from core.tiered_logger import get_logger
from .music_database import Artist, Album, Track, ExternalIdentifier, AudioFingerprint, LocalMedia, generate_nanoid

logger = get_logger("bulk_operations")

BATCH_SIZE = 2000  # Commit every N tracks (tuned for SQLite WAL throughput)


def normalize_text(text: str) -> str:
    if not text:
        return text
    return unicodedata.normalize('NFC', text).strip()


def _canonicalize_path(file_path: str) -> str:
    """Produce a deterministic canonical form for a file path.

    This prevents duplicate LocalMedia rows caused by the same file being
    reported with different path representations by different providers
    (e.g. local scanner vs Plex vs resolved symlinks).

    Rules applied:
      1. Resolve to absolute path (follows symlinks).
      2. Convert to POSIX style (forward slashes).
      3. Strip trailing slashes.
    """
    if not file_path or file_path.startswith("virtual://"):
        return file_path
    try:
        canon = Path(file_path).resolve().as_posix()
        return normalize_text(canon)
    except Exception:
        return normalize_text(file_path)


class LibraryManager:
    """
    SQLAlchemy 2.0 based bulk importer for EchosyncTrack objects.
    Uses local caching to minimize database round-trips.
    """

    def __init__(self, session_factory: sessionmaker):
        """
        Initialize LibraryManager.

        Args:
            session_factory: SQLAlchemy sessionmaker bound to engine
        """
        self.session_factory = session_factory
        # Local caches to minimize DB lookups
        self.artist_cache: Dict[str, int] = {}  # normalized_name -> artist_id
        self.album_cache: Dict[Tuple[str, int], int] = {}  # (normalized_title, artist_id) -> album_id

    def _normalize_name(self, name: Optional[str]) -> str:
        """Normalize name for cache lookup."""
        if not name:
            return ""
        return text_utils.normalize_text(name).lower()

    def _get_or_create_artist(self, session: Session, artist_name: str, sort_name: Optional[str] = None) -> Artist:
        """
        Get or create artist. Uses cache first, then DB.

        Args:
            session: SQLAlchemy session
            artist_name: Artist name
            sort_name: Optional sort name to use if creating new

        Returns:
            Artist object
        """
        if not artist_name:
            raise ValueError("Artist name is required")

        artist_name = normalize_text(artist_name)
        sort_name = normalize_text(sort_name)
        norm_name = normalize_text(self._normalize_name(artist_name))

        # Check cache first
        if norm_name in self.artist_cache:
            artist_id = self.artist_cache[norm_name]
            # Retrieve from DB to return attached object
            stmt = select(Artist).where(Artist.id == artist_id)
            artist = session.execute(stmt).scalar_one()
            return artist

        # INGESTION SAFETY GUARD: Artist Generation
        # Always normalize and strictly query before allowing a session.add()
        
        stmt = select(Artist).where(
            Artist.normalized_name == norm_name
        )
        artist = session.execute(stmt).scalar_one_or_none()
        # Fallback for normalized lookup
        if artist is None:
            if norm_name in self.artist_cache:
                uid = self.artist_cache[norm_name]
                stmt2 = select(Artist).where(Artist.id == uid)
                artist = session.execute(stmt2).scalar_one_or_none()
            else:
                stmt2 = select(Artist)
                for a in session.execute(stmt2).scalars().all():
                    if self._normalize_name(a.name) == norm_name:
                        artist = a
                        break

        if artist is None:
            # Create new artist only if strict lookup failed
            artist = Artist(name=artist_name, normalized_name=norm_name, sort_name=sort_name)
            session.add(artist)
            session.flush()

        # Cache it
        self.artist_cache[norm_name] = artist.id
        return artist

    def _get_or_create_album(
        self,
        session: Session,
        album_title: Optional[str],
        artist: Artist,
        release_year: Optional[int],
        album_type: Optional[str] = None,
        release_group_id: Optional[str] = None,
        mb_release_id: Optional[str] = None,
        original_release_date: Optional[date] = None,
    ) -> Optional[Album]:
        """
        Get or create album. Uses cache first, then DB.

        Args:
            session: SQLAlchemy session
            album_title: Album title
            artist: Artist object
            release_year: Release year
            album_type: Album type
            release_group_id: MusicBrainz Release Group ID
            mb_release_id: MusicBrainz Release ID
            original_release_date: Original release date

        Returns:
            Album object or None if album_title is None
        """
        if not album_title:
            return None

        album_title = normalize_text(album_title)
        album_type = normalize_text(album_type)
        norm_title = normalize_text(self._normalize_name(album_title))
        cache_key = (norm_title, artist.id)

        # Check cache first
        if cache_key in self.album_cache:
            album_id = self.album_cache[cache_key]
            stmt = select(Album).where(Album.id == album_id)
            album = session.execute(stmt).scalar_one()
            # Update fields if missing
            if release_group_id and not album.release_group_id:
                album.release_group_id = release_group_id
            if album_type and not album.album_type:
                album.album_type = album_type
            if mb_release_id and not album.mb_release_id:
                album.mb_release_id = mb_release_id
            if original_release_date and not album.original_release_date:
                album.original_release_date = original_release_date
            return album

        # INGESTION SAFETY GUARD: Album Generation
        # Strictly verify album title + artist_id combo before insert
        
        stmt = select(Album).where(
            Album.normalized_title == norm_title,
            Album.artist_id == artist.id,
        )
        album = session.execute(stmt).scalar_one_or_none()
        # Fallback via normalization
        if album is None:
            cache_key = (norm_title, artist.id)
            if cache_key in self.album_cache:
                aid = self.album_cache[cache_key]
                stmt2 = select(Album).where(Album.id == aid)
                album = session.execute(stmt2).scalar_one_or_none()
            else:
                stmt2 = select(Album).where(Album.artist_id == artist.id)
                for alb in session.execute(stmt2).scalars().all():
                    if self._normalize_name(alb.title) == norm_title:
                        album = alb
                        break

        try:
            year_int = int(release_year) if release_year else None
            release_date = date(year_int, 1, 1) if year_int else None
        except (ValueError, TypeError):
            release_date = None

        if album is None:
            album = Album(
                title=album_title,
                normalized_title=norm_title,
                artist=artist,
                release_date=release_date,
                album_type=album_type,
                release_group_id=release_group_id,
                mb_release_id=mb_release_id,
                original_release_date=original_release_date,
            )
            session.add(album)
            session.flush()
        else:
            if release_date and album.release_date != release_date:
                album.release_date = release_date
            if release_group_id and not album.release_group_id:
                album.release_group_id = release_group_id
            if album_type and not album.album_type:
                album.album_type = album_type
            if mb_release_id and not album.mb_release_id:
                album.mb_release_id = mb_release_id
            if original_release_date and not album.original_release_date:
                album.original_release_date = original_release_date

        # Cache it
        self.album_cache[cache_key] = album.id
        return album

    def _find_track_by_identifiers(
        self, session: Session, identifiers: Dict[str, any]
    ) -> Optional[Track]:
        """
        Find track by checking ExternalIdentifiers.

        Args:
            session: SQLAlchemy session
            identifiers: Dict of identifiers (key=plugin_source, value=id)

        Returns:
            Track object or None
        """
        if not identifiers:
            return None

        for source, item_id in identifiers.items():
            if not source or not item_id:
                continue

            # Ensure item_id is a string
            if not isinstance(item_id, str):
                item_id = str(item_id)

            stmt = (
                select(Track)
                .join(LocalMedia, Track.id == LocalMedia.track_id)
                .join(ExternalIdentifier, LocalMedia.media_id == ExternalIdentifier.media_id)
                .where(
                    ExternalIdentifier.plugin_source == source,
                    ExternalIdentifier.plugin_item_id == item_id,
                )
            )
            track = session.execute(stmt).scalar_one_or_none()
            if track:
                return track

        return None

    def _find_track_by_metadata(
        self,
        session: Session,
        title: str,
        artist_id: int,
        album_id: Optional[int],
        track_number: Optional[int] = None,
        file_path: Optional[str] = None,
    ) -> Optional[Track]:
        """
        Fallback: find track by file_path OR (title + artist + album + track_number).
        """
        title = normalize_text(title)
        if file_path:
            norm_fp = normalize_text(file_path)
            stmt = select(Track).join(LocalMedia).where(func.lower(LocalMedia.file_path) == func.lower(norm_fp))
            track = session.execute(stmt).scalar_one_or_none()
            if track:
                return track

        norm_title = normalize_text(text_utils.normalize_title(title))
        conditions = [
            Track.normalized_title == norm_title,
            Track.artist_id == artist_id,
        ]
        if album_id:
            conditions.append(Track.album_id == album_id)
        if track_number is not None:
            conditions.append(Track.track_number == track_number)

        stmt = select(Track).where(*conditions)
        return session.execute(stmt).scalars().first()

    def _track_exists_locally(
        self,
        session: Session,
        track_data: EchosyncTrack,
        _prefetched_ids: Optional[Dict[str, set]] = None,
    ) -> bool:
        """
        Lightweight existence check that does NOT create Artist or Album rows.

        Used as an early-exit gate when identifiers_only=True to prevent
        orphan Artist/Album rows from being committed for tracks that
        don't exist in the local database.

        Checks (in order):
          0. In-memory pre-fetched identifier set (O(1), no DB hit)
          1. ExternalIdentifiers (fast, indexed) — only if no pre-fetched set
          2. file_path (fast, indexed)
          3. Normalized title + artist name via JOIN (no Artist row needed)

        Args:
            _prefetched_ids: Optional dict of {plugin_source: set(plugin_item_id)}.
                             When provided, step 0 replaces step 1 entirely,
                             eliminating per-row SELECT queries.
        """
        # 0/1. Check by external identifiers
        if track_data.identifiers:
            for source, item_id in track_data.identifiers.items():
                if not source or not item_id:
                    continue
                if not isinstance(item_id, str):
                    item_id = str(item_id)

                # Fast path: O(1) in-memory lookup from pre-fetched set
                if _prefetched_ids and source in _prefetched_ids:
                    if item_id in _prefetched_ids[source]:
                        return True
                    continue  # source was fully pre-fetched, skip DB

                # Slow path: per-row DB query (only for sources not pre-fetched)
                stmt = select(ExternalIdentifier.id).where(
                    ExternalIdentifier.plugin_source == source,
                    ExternalIdentifier.plugin_item_id == item_id,
                )
                if session.execute(stmt).first() is not None:
                    return True

        # 2. Check by file_path
        media_files = getattr(track_data, 'media', [])
        primary_file_path = media_files[0].file_path if media_files else None
        if primary_file_path:
            norm_pf = normalize_text(primary_file_path)
            stmt = select(Track.id).join(LocalMedia).where(func.lower(LocalMedia.file_path) == func.lower(norm_pf))
            if session.execute(stmt).first() is not None:
                return True

        # 3. Check by normalized title + artist name (JOIN avoids needing an artist_id)
        if track_data.title and track_data.artist_name:
            norm_title = normalize_text(text_utils.normalize_title(track_data.title))
            norm_artist = normalize_text(self._normalize_name(track_data.artist_name))
            stmt = (
                select(Track.id)
                .join(Artist, Track.artist_id == Artist.id)
                .where(
                    Track.normalized_title == norm_title,
                    Artist.normalized_name == norm_artist,
                )
            )
            if session.execute(stmt).first() is not None:
                return True

        return False

    def _upsert_track(
        self, session: Session, track_data: EchosyncTrack, artist: Artist, album: Optional[Album], identifiers_only: bool = False
    ) -> tuple[Optional[Track], bool]:
        """
        Insert or update a single track.
        """
        track = None
        if track_data.identifiers:
            for source, plugin_item_id in track_data.identifiers.items():
                if source and plugin_item_id:
                    stmt = select(ExternalIdentifier).where(
                        ExternalIdentifier.plugin_source == source,
                        ExternalIdentifier.plugin_item_id == str(plugin_item_id)
                    )
                    ext_id = session.execute(stmt).scalar_one_or_none()
                    if ext_id and ext_id.media and ext_id.media.track:
                        track = ext_id.media.track
                        break

        if track is None:
            track = self._find_track_by_identifiers(session, track_data.identifiers)

        if track is None:
            media_files = getattr(track_data, 'media', [])
            primary_file_path = media_files[0].file_path if media_files else None
            track = self._find_track_by_metadata(
                session,
                track_data.title,
                artist.id,
                album.id if album else None,
                track_number=track_data.track_number,
                file_path=primary_file_path,
            )
            if track is not None and track_data.identifiers:
                existing_ids = set()
                existing_plugins = set()
                for m in track.media_files:
                    for e in m.external_identifiers:
                        existing_ids.add((e.plugin_source, e.plugin_item_id))
                        existing_plugins.add(e.plugin_source)
                conflict = False
                for src, pid in track_data.identifiers.items():
                    if src and pid:
                        if src in existing_plugins:
                            if (src, str(pid)) not in existing_ids:
                                conflict = True
                                break
                if conflict:
                    track = None

        if track is None:
            if identifiers_only:
                return None, False

            norm_title = text_utils.normalize_title(track_data.title)
            track = Track(
                title=normalize_text(track_data.title),
                normalized_title=normalize_text(norm_title),
                sort_title=normalize_text(track_data.sort_title),
                edition=normalize_text(track_data.edition),
                artist=artist,
                album=album,
                duration=track_data.duration,
                track_number=track_data.track_number,
                disc_number=track_data.disc_number,
                musicbrainz_id=track_data.musicbrainz_id,
                isrc=track_data.isrc,
                sync_id=track_data.sync_id,
            )
            session.add(track)
            session.flush()
            logger.debug(f"Created new track: {track.title} by {artist.name}")
            is_new = True
        else:
            old_title = track.title
            if not identifiers_only:
                track.title = normalize_text(track_data.title)
            if album and track.album_id != album.id:
                track.album = album
            if track.artist_id != artist.id:
                track.artist = artist

            if track_data.sort_title is not None:
                track.sort_title = normalize_text(track_data.sort_title)
            if track_data.edition is not None:
                track.edition = normalize_text(track_data.edition)
            else:
                if track.edition and old_title != track_data.title:
                    edition_lower = track.edition.lower()
                    new_title_lower = track_data.title.lower()
                    is_corrupted = (
                        'titile' in edition_lower or
                        track.edition.startswith(') -') or
                        track.edition.startswith('(') and ')' not in track.edition or
                        len(track.edition.strip()) < 3 or
                        track.edition.count('(') != track.edition.count(')') or
                        edition_lower in new_title_lower
                    )
                    if is_corrupted:
                        logger.info(f"Corruption fix: Clearing corrupted edition '{track.edition}' for track '{track_data.title}'")
                        track.edition = None

            if track_data.duration is not None:
                track.duration = track_data.duration
            if track_data.track_number is not None:
                track.track_number = track_data.track_number
            if track_data.disc_number is not None:
                track.disc_number = track_data.disc_number
            if track_data.added_at is not None:
                track.added_at = track_data.added_at
            if track_data.musicbrainz_id is not None:
                track.musicbrainz_id = track_data.musicbrainz_id
            if track_data.isrc is not None:
                track.isrc = track_data.isrc

            # Validate and clear invalid ISRCs in DB
            if track.isrc:
                import re
                isrc_clean = str(track.isrc).strip().upper().replace("-", "")
                if not re.match(r"^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$", isrc_clean):
                    track.isrc = None

            if track_data.sync_id is not None:
                track.sync_id = track_data.sync_id

            logger.debug(f"Updated existing track: {track.title} by {artist.name}")
            is_new = False

        # Upsert Media Files
        primary_media = None
        for media_data in getattr(track_data, 'media', []):
            if not media_data.file_path:
                continue

            # Canonicalize the path so that different representations of the
            # same physical file (symlinks, trailing slashes, Plex vs local
            # scanner) always produce the same LocalMedia row.
            media_data.file_path = _canonicalize_path(media_data.file_path)
            normalized_path = normalize_text(media_data.file_path)

            stmt = select(LocalMedia).where(func.lower(LocalMedia.file_path) == func.lower(normalized_path))
            media_row = session.execute(stmt).scalar_one_or_none()

            if media_row is None:
                m_id = media_data.media_id
                if not m_id:
                    m_id = generate_nanoid(size=8)

                media_row = LocalMedia(
                    track=track,
                    media_id=m_id,
                    file_path=normalized_path,
                    file_format=media_data.file_format,
                    bitrate=media_data.bitrate,
                    sample_rate=media_data.sample_rate,
                    bit_depth=media_data.bit_depth,
                    file_size_bytes=media_data.file_size_bytes,
                    added_at=media_data.added_at,
                    inode=media_data.inode,
                    mtime=media_data.mtime,
                )
                session.add(media_row)
            else:
                if media_row.track_id != track.id:
                    logger.warning(f"Media file {media_row.file_path} moved to track {track.id}")
                    media_row.track = track
                if media_data.file_format is not None: media_row.file_format = media_data.file_format
                if media_data.bitrate is not None: media_row.bitrate = media_data.bitrate
                if media_data.sample_rate is not None: media_row.sample_rate = media_data.sample_rate
                if media_data.bit_depth is not None: media_row.bit_depth = media_data.bit_depth
                if media_data.file_size_bytes is not None: media_row.file_size_bytes = media_data.file_size_bytes
                if media_data.added_at is not None: media_row.added_at = media_data.added_at
                if media_data.inode is not None: media_row.inode = media_data.inode
                if media_data.mtime is not None: media_row.mtime = media_data.mtime
            
            if not primary_media:
                primary_media = media_row

        if not primary_media and track.media_files:
            primary_media = track.get_best_media()

        # Only create a virtual media row if the track has NO real media at all.
        # This prevents phantom virtual:// entries from inflating file/storage counts
        # when the track already has physical files attached from a prior scan.
        if not primary_media and track_data.identifiers:
            # Check if the track already has any real (non-virtual) media
            has_real_media = any(
                m for m in track.media_files
                if m.file_path and not m.file_path.startswith("virtual://")
            )
            if has_real_media:
                # Use the best existing real media as the primary for linking identifiers
                primary_media = track.get_best_media()
            else:
                plugin_id = ""
                for source, pid in track_data.identifiers.items():
                    if source and pid and source != 'acoustid_id':
                        plugin_id = f"{source}/{pid}"
                        break
                
                if plugin_id:
                    virtual_path = f"virtual://{plugin_id}"
                else:
                    virtual_path = f"virtual://{track_data.sync_id or track.sync_id}"

                stmt = select(LocalMedia).where(LocalMedia.file_path == virtual_path)
                media_row = session.execute(stmt).scalar_one_or_none()
                if media_row is None:
                    m_id = generate_nanoid(size=8)
                    media_row = LocalMedia(
                        track=track,
                        media_id=m_id,
                        file_path=virtual_path,
                    )
                    session.add(media_row)
                primary_media = media_row

        # Link identifiers (Only if we have a primary_media to attach it to)
        if primary_media:
            album_artist_keys = {
                'musicbrainz_release_id', 'musicbrainz_albumid', 'musicbrainz_artistid',
                'musicbrainz_release_group_id', 'musicbrainz_albumartistid', 'mb_release_id'
            }
            for source, item_id in track_data.identifiers.items():
                if not source or not item_id or source == 'acoustid_id':
                    continue

                if source in album_artist_keys:
                    continue  # Skip. These belong on the Album/Artist models, not LocalMedia.

                if not isinstance(item_id, str):
                    item_id = str(item_id)

                stmt = select(ExternalIdentifier).where(
                    ExternalIdentifier.plugin_source == source,
                    ExternalIdentifier.plugin_item_id == item_id,
                )
                ext_id = session.execute(stmt).scalar_one_or_none()

                if ext_id is None:
                    ext_id = ExternalIdentifier(
                        media=primary_media,
                        plugin_source=source,
                        plugin_item_id=item_id,
                        raw_data=None,
                    )
                    session.add(ext_id)
                else:
                    if ext_id.media_id != primary_media.media_id:
                        logger.warning(
                            f"ExternalIdentifier collision resolved: Re-mapping {source}:{item_id} from media {ext_id.media_id} to {primary_media.media_id}"
                        )
                        ext_id.media = primary_media

            # Audio Fingerprint
            if getattr(track_data, 'fingerprint', None):
                stmt = select(AudioFingerprint).where(
                    AudioFingerprint.chromaprint == track_data.fingerprint
                )
                af = session.execute(stmt).scalar_one_or_none()

                if af is None:
                    af = AudioFingerprint(
                        media=primary_media,
                        chromaprint=track_data.fingerprint,
                        acoustid_id=track_data.acoustid_id
                    )
                    session.add(af)
                else:
                    if af.media_id != primary_media.media_id:
                        af.media = primary_media
                    if getattr(track_data, 'acoustid_id', None) and not af.acoustid_id:
                        af.acoustid_id = track_data.acoustid_id
        else:
            if getattr(track_data, 'identifiers', None) or getattr(track_data, 'fingerprint', None):
                logger.warning(f"Could not link identifiers or fingerprint for track '{track.title}' because no media file was associated.")

        # --- Post-upsert deduplication ---
        # If the track now has multiple LocalMedia rows pointing to the same
        # canonical path (caused by prior runs with non-canonical paths), merge
        # them by keeping the row with the lowest id and deleting the rest.
        try:
            session.flush()  # ensure all pending media rows have IDs
            path_groups: Dict[str, list] = defaultdict(list)
            for m in track.media_files:
                canon = _canonicalize_path(m.file_path) if m.file_path else m.file_path
                path_groups[canon].append(m)

            for canon_path, group in path_groups.items():
                if len(group) <= 1:
                    continue
                # Keep the row with the lowest id (oldest)
                group.sort(key=lambda m: m.id)
                keeper = group[0]
                for dup in group[1:]:
                    # Re-point any ExternalIdentifiers and AudioFingerprints
                    for ext in list(dup.external_identifiers):
                        ext.media_id = keeper.media_id
                    for fp in list(dup.audio_fingerprints):
                        fp.media_id = keeper.media_id
                    session.delete(dup)
                    logger.info(
                        "Dedup: removed duplicate LocalMedia id=%s for track '%s' (path=%s, kept id=%s)",
                        dup.id, track.title, canon_path, keeper.id,
                    )
        except Exception as dedup_err:
            logger.warning("Post-upsert dedup failed for track '%s': %s", track.title, dedup_err)

        return track, is_new

    def _delete_missing_tracks(self, session: Session, observed_identifiers: Dict[str, set[str]]) -> int:
        """Remove tracks that are no longer present for a given plugin source."""
        if not observed_identifiers:
            return 0

        deleted_track_ids: set[int] = set()

        for plugin_source, item_ids in observed_identifiers.items():
            stmt = select(Track.id).join(LocalMedia).join(ExternalIdentifier, LocalMedia.media_id == ExternalIdentifier.media_id).where(
                ExternalIdentifier.plugin_source == plugin_source
            )

            if item_ids:
                stmt = stmt.where(~ExternalIdentifier.plugin_item_id.in_(item_ids))

            stale_ids = session.execute(stmt).scalars().all()
            deleted_track_ids.update(stale_ids)

        if not deleted_track_ids:
            return 0

        session.execute(delete(Track).where(Track.id.in_(list(deleted_track_ids))))
        return len(deleted_track_ids)

    def _delete_missing_local_tracks(self, session: Session, observed_file_paths: set[str]) -> int:
        """Remove tracks that have a local file path but were not observed during scan."""
        from core.settings import config_manager
        from pathlib import Path

        library_dir_str = config_manager.get('storage.library_dir') or config_manager.get('library_dir')
        if not library_dir_str:
            return 0
        
        try:
            library_dir = str(Path(library_dir_str).resolve())
        except Exception:
            return 0
        
        stmt = select(Track.id, LocalMedia.file_path).join(LocalMedia).where(
            LocalMedia.file_path.isnot(None),
            LocalMedia.file_path != ''
        )
        
        stale_ids = []
        for track_id, fpath in session.execute(stmt):
            try:
                if str(Path(fpath).resolve()).startswith(library_dir):
                    if fpath not in observed_file_paths:
                        stale_ids.append(track_id)
            except Exception:
                pass
                
        if not stale_ids:
            return 0
            
        session.execute(delete(Track).where(Track.id.in_(stale_ids)))
        return len(stale_ids)

    def bulk_import(
        self,
        tracks: Iterable[EchosyncTrack],
        progress_callback: Optional[Callable[[Dict[str, int]], None]] = None,
        total_count: Optional[int] = None,
        identifiers_only: bool = False,
        source_name: Optional[str] = None
    ) -> int:
        """
        Bulk import EchosyncTrack objects into database.
        """
        if not tracks:
            logger.warning("No tracks provided for bulk import")
            return 0

        if total_count is None:
            try:
                total_count = len(tracks)
            except TypeError:
                total_count = 0

        logger.info(f"Starting bulk import of {total_count if total_count > 0 else 'unknown number of'} tracks")

        session = self.session_factory()
        
        if source_name == "EchoSync.local_server":
            try:
                session.execute(delete(ExternalIdentifier).where(ExternalIdentifier.plugin_source == "EchoSync.local_server"))
                session.execute(delete(ExternalIdentifier).where(ExternalIdentifier.plugin_source == "acoustid_id"))
                session.commit()
                logger.info("Purged legacy EchoSync.local_server and duplicate acoustid_id external identifiers")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to purge legacy local/acoustid identifiers: {e}")

        imported_count = 0
        updated_count = 0
        failed_count = 0
        observed_identifiers: Dict[str, set[str]] = defaultdict(set)
        observed_file_paths: set[str] = set()
        seen_artist_ids: set[int] = set()
        seen_album_ids: set[int] = set()

        if not self.artist_cache:
            try:
                stmt = select(Artist)
                for a in session.execute(stmt).scalars().all():
                    norm = self._normalize_name(a.name)
                    if norm in self.artist_cache:
                        primary_id = self.artist_cache[norm]
                        primary = session.get(Artist, primary_id)
                        if primary and primary.id != a.id:
                            for alb in list(a.albums):
                                alb.artist = primary
                            for tr in list(a.tracks):
                                tr.artist = primary
                            try:
                                session.delete(a)
                                logger.info(f"Merged duplicate artist '{a.name}' into '{primary.name}'")
                            except Exception:
                                pass
                            continue
                    self.artist_cache[norm] = a.id
            except Exception:
                pass

        if not self.album_cache:
            try:
                stmt = select(Album)
                for alb in session.execute(stmt).scalars().all():
                    norm = self._normalize_name(alb.title)
                    key = (norm, alb.artist_id)
                    if key in self.album_cache:
                        primary_id = self.album_cache[key]
                        primary = session.get(Album, primary_id)
                        if primary and primary.id != alb.id:
                            for tr in list(alb.tracks):
                                tr.album = primary
                            try:
                                session.delete(alb)
                                logger.info(f"Merged duplicate album '{alb.title}' into '{primary.title}'")
                            except Exception:
                                pass
                            continue
                    self.album_cache[key] = alb.id
            except Exception:
                pass

        # PERF: Pre-fetch all known identifier IDs for the source plugin into
        # an in-memory set. This replaces 13K+ per-row SELECT queries with a
        # single bulk query + O(1) set lookups inside _track_exists_locally.
        prefetched_ids: Optional[Dict[str, set]] = None
        if identifiers_only and source_name:
            try:
                stmt = select(ExternalIdentifier.plugin_item_id).where(
                    ExternalIdentifier.plugin_source == source_name
                )
                source_ids = {row[0] for row in session.execute(stmt).all()}
                prefetched_ids = {source_name: source_ids}
                logger.info(
                    "Pre-fetched %d existing identifiers for source '%s'",
                    len(source_ids), source_name,
                )
            except Exception as e:
                logger.warning("Failed to pre-fetch identifiers for '%s': %s", source_name, e)

        try:
            for idx, track_data in enumerate(tracks):
                if idx and idx % 10 == 0:
                    time.sleep(0)

                try:
                    if not track_data.title or not track_data.title.strip():
                        failed_count += 1
                        logger.warning(
                            "Skipping track %s due to missing title: artist='%s' album='%s'",
                            idx + 1, track_data.artist_name, track_data.album_title,
                        )
                        continue

                    if not track_data.artist_name or not track_data.artist_name.strip():
                        failed_count += 1
                        logger.warning(
                            "Skipping track %s due to missing artist: title='%s'",
                            idx + 1, track_data.title,
                        )
                        continue

                    if (idx + 1) % 100 == 0 or idx == 0:
                        logger.debug(
                            "Processing track %s: title='%s' artist='%s' album='%s'",
                            idx + 1, track_data.title, track_data.artist_name, track_data.album_title,
                        )

                    # ORPHAN GUARD: When identifiers_only=True, check if the
                    # track exists locally BEFORE creating Artist/Album rows.
                    # Without this gate, _get_or_create_artist and
                    # _get_or_create_album would flush new rows that become
                    # orphans when _upsert_track later returns None.
                    if identifiers_only and not self._track_exists_locally(session, track_data, _prefetched_ids=prefetched_ids):
                        logger.debug(
                            "identifiers_only skip: no local match for '%s' by '%s'",
                            track_data.title, track_data.artist_name,
                        )
                        continue

                    artist = self._get_or_create_artist(
                        session,
                        track_data.artist_name,
                        sort_name=track_data.artist_sort_name
                    )
                    if artist and artist.id:
                        seen_artist_ids.add(artist.id)

                    album_artist_str = track_data.album_artist
                    if not album_artist_str or not album_artist_str.strip():
                        album_artist_str = track_data.artist_name

                    album_artist_entity = self._get_or_create_artist(
                        session,
                        album_artist_str,
                        # sort_name for the album artist is not strictly defined in EchosyncTrack,
                        # but we can try falling back to artist_sort_name or leave it None.
                    )

                    album = self._get_or_create_album(
                        session,
                        track_data.album_title,
                        album_artist_entity,
                        track_data.release_year,
                        album_type=track_data.album_type,
                        release_group_id=track_data.album_release_group_id,
                        mb_release_id=track_data.mb_release_id,
                        original_release_date=track_data.original_release_date
                    )
                    if album and album.id:
                        seen_album_ids.add(album.id)

                    track, is_new = self._upsert_track(session, track_data, artist, album, identifiers_only=identifiers_only)

                    if track is None:
                        # Skip if identifiers_only=True and no matching track is found
                        continue

                    for media_item in getattr(track_data, "media", []):
                        if media_item.file_path:
                            observed_file_paths.add(media_item.file_path)

                    for source, item_id in (track_data.identifiers or {}).items():
                        if not source or item_id is None:
                            continue
                        if not isinstance(item_id, str):
                            item_id = str(item_id)
                        observed_identifiers[source].add(item_id)

                    if is_new:
                        imported_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to import track '{track_data.title}': {e}", exc_info=True)
                    continue

                if (idx + 1) % BATCH_SIZE == 0:
                    session.commit()
                    logger.info(f"Batch committed: {idx + 1} tracks processed")

                if progress_callback and (((idx + 1) % 25 == 0) or ((idx + 1) % BATCH_SIZE == 0)):
                    try:
                        progress_callback({
                            "processed": idx + 1,
                            "total": total_count,
                            "imported": imported_count,
                            "updated": updated_count,
                            "failed": failed_count,
                            "artists": len(seen_artist_ids),
                            "albums": len(seen_album_ids),
                        })
                    except Exception:
                        pass

            session.commit()

            deleted_count = self._delete_missing_tracks(session, observed_identifiers)
            if source_name == "EchoSync.local_server" and not identifiers_only:
                local_deleted = self._delete_missing_local_tracks(session, observed_file_paths)
                if local_deleted > 0:
                    deleted_count += local_deleted
                    
            if deleted_count:
                session.commit()

            total_processed = imported_count + updated_count
            logger.info(
                f"Bulk import complete: {imported_count} new, {updated_count} updated, {deleted_count} deleted, {failed_count} failed (total processed: {total_processed})"
            )

            if progress_callback:
                try:
                    progress_callback({
                        "processed": imported_count + updated_count + failed_count,
                        "total": total_count,
                        "imported": imported_count,
                        "updated": updated_count,
                        "failed": failed_count,
                        "artists": len(seen_artist_ids),
                        "albums": len(seen_album_ids),
                    })
                except Exception:
                    pass

        except Exception as e:
            session.rollback()
            logger.error(f"Bulk import failed with exception: {e}", exc_info=True)
            raise
        finally:
            session.close()

        return total_processed

    def backfill_plugin_identifiers(self, plugin_source: str) -> int:
        """
        Repair missing external identifiers caused by the old duplicate-row bug.
        """
        session = self.session_factory()
        try:
            # --- Step 1: build file_path → (plugin_item_id, ext_id pk) map ---
            rows = session.execute(
                select(LocalMedia.file_path, ExternalIdentifier.plugin_item_id, ExternalIdentifier.id)
                .select_from(Track)
                .join(LocalMedia, Track.id == LocalMedia.track_id)
                .join(ExternalIdentifier, LocalMedia.media_id == ExternalIdentifier.media_id)
                .where(
                    ExternalIdentifier.plugin_source == plugin_source,
                    LocalMedia.file_path.isnot(None),
                    LocalMedia.file_path != '',
                )
            ).all()

            if not rows:
                logger.info(
                    "backfill_plugin_identifiers(%s): no source rows found — nothing to backfill.",
                    plugin_source,
                )
                return 0

            # Keep the first (earliest) ext_id row seen per file_path.
            fp_to_info: Dict[str, tuple] = {}  # fp → (plugin_item_id, ext_id_pk)
            for fp, pid, ext_pk in rows:
                if fp and fp not in fp_to_info:
                    fp_to_info[fp] = (pid, ext_pk)

            target_file_paths = list(fp_to_info.keys())
            logger.info(
                "backfill_plugin_identifiers(%s): %d file paths carry an identifier for this plugin.",
                plugin_source, len(target_file_paths),
            )

            # --- Step 2: find tracks at those file_paths that lack the identifier ---
            already_linked_subq = (
                select(LocalMedia.track_id)
                .join(ExternalIdentifier, LocalMedia.media_id == ExternalIdentifier.media_id)
                .where(ExternalIdentifier.plugin_source == plugin_source)
                .scalar_subquery()
            )

            BACKFILL_BATCH = 500
            updated_count = 0

            for batch_start in range(0, len(target_file_paths), BACKFILL_BATCH):
                batch_paths = target_file_paths[batch_start : batch_start + BACKFILL_BATCH]

                # Fetch orphan tracks without triggering autoflush of pending state.
                with session.no_autoflush:
                    orphan_tracks = session.execute(
                        select(Track)
                        .options(selectinload(Track.media_files))
                        .join(LocalMedia, Track.id == LocalMedia.track_id)
                        .where(
                            LocalMedia.file_path.in_(batch_paths),
                            Track.id.not_in(already_linked_subq),
                        )
                    ).scalars().all()

                for track in orphan_tracks:
                    # Find the LocalMedia for this track that has the batch path
                    target_media = next((m for m in track.media_files if m.file_path in fp_to_info), None)
                    if not target_media:
                        continue
                    pid, ext_pk = fp_to_info.get(target_media.file_path, (None, None))
                    if not pid or not ext_pk:
                        continue

                    # Re-point the existing ExternalIdentifier row to this media.
                    ext_row = session.get(ExternalIdentifier, ext_pk)
                    if ext_row is None:
                        continue
                    old_media_id = ext_row.media_id
                    ext_row.media_id = target_media.media_id
                    updated_count += 1
                    logger.debug(
                        "backfill: re-pointed %s identifier '%s' from media %s → media %s ('%s')",
                        plugin_source, pid, old_media_id, target_media.media_id, track.title,
                    )

            session.commit()
            logger.info(
                "backfill_plugin_identifiers(%s): re-pointed %d missing identifier(s).",
                plugin_source, updated_count,
            )
            return updated_count

        except Exception as exc:
            session.rollback()
            logger.error(
                "backfill_plugin_identifiers(%s) failed: %s", plugin_source, exc, exc_info=True
            )
            raise
        finally:
            session.close()
