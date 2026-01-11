"""
Bulk import operations using SQLAlchemy 2.0 and LibraryManager.
Efficiently ingests SoulSyncTrack objects into the database with caching.
"""
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime

from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker, Session

from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.matching_engine import text_utils
from utils.logging_config import get_logger
from .music_database import Artist, Album, Track, ExternalIdentifier

logger = get_logger("bulk_operations")

BATCH_SIZE = 100  # Commit every N tracks


class LibraryManager:
    """
    SQLAlchemy 2.0 based bulk importer for SoulSyncTrack objects.
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

        norm_name = self._normalize_name(artist_name)

        # Check cache first
        if norm_name in self.artist_cache:
            artist_id = self.artist_cache[norm_name]
            # Retrieve from DB to return attached object
            stmt = select(Artist).where(Artist.id == artist_id)
            artist = session.execute(stmt).scalar_one()
            return artist

        # Check DB
        stmt = select(Artist).where(
            func.lower(Artist.name) == norm_name
        )
        artist = session.execute(stmt).scalar_one_or_none()

        if artist is None:
            # Create new artist
            artist = Artist(name=artist_name, sort_name=sort_name)
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
    ) -> Optional[Album]:
        """
        Get or create album. Uses cache first, then DB.

        Args:
            session: SQLAlchemy session
            album_title: Album title
            artist: Artist object (already created/fetched)
            release_year: Release year
            album_type: Album type (e.g. Album, EP)
            release_group_id: MusicBrainz Release Group ID

        Returns:
            Album object or None if album_title is None
        """
        if not album_title:
            return None

        norm_title = self._normalize_name(album_title)
        cache_key = (norm_title, artist.id)

        # Check cache first
        if cache_key in self.album_cache:
            album_id = self.album_cache[cache_key]
            stmt = select(Album).where(Album.id == album_id)
            album = session.execute(stmt).scalar_one()
            # Still might need to update metadata if it was cached but fields were missing
            if release_group_id and not album.release_group_id:
                album.release_group_id = release_group_id
            if album_type and not album.album_type:
                album.album_type = album_type
            return album

        # Check DB
        stmt = select(Album).where(
            func.lower(Album.title) == norm_title,
            Album.artist_id == artist.id,
        )
        album = session.execute(stmt).scalar_one_or_none()

        release_date = date(release_year, 1, 1) if release_year else None

        if album is None:
            # Create new album
            album = Album(
                title=album_title,
                artist=artist,
                release_date=release_date,
                album_type=album_type,
                release_group_id=release_group_id,
            )
            session.add(album)
            session.flush()
        else:
            # Update metadata if needed
            if release_date and album.release_date != release_date:
                album.release_date = release_date
            if release_group_id and not album.release_group_id:
                album.release_group_id = release_group_id
            if album_type and not album.album_type:
                album.album_type = album_type

        # Cache it
        self.album_cache[cache_key] = album.id
        return album

    def _find_track_by_identifiers(
        self, session: Session, identifiers: List[Dict[str, any]]
    ) -> Optional[Track]:
        """
        Find track by checking ExternalIdentifiers.

        Args:
            session: SQLAlchemy session
            identifiers: List of identifier dicts from SoulSyncTrack

        Returns:
            Track object or None
        """
        if not identifiers:
            return None

        for identifier in identifiers:
            provider_source = identifier.get("provider_source")
            provider_item_id = identifier.get("provider_item_id")

            if not provider_source or not provider_item_id:
                continue

            stmt = (
                select(Track)
                .join(ExternalIdentifier)
                .where(
                    ExternalIdentifier.provider_source == provider_source,
                    ExternalIdentifier.provider_item_id == provider_item_id,
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
    ) -> Optional[Track]:
        """
        Fallback: find track by title + artist + album.

        Args:
            session: SQLAlchemy session
            title: Track title
            artist_id: Artist ID
            album_id: Album ID (optional)

        Returns:
            Track object or None
        """
        norm_title = self._normalize_name(title)
        conditions = [
            func.lower(Track.title) == norm_title,
            Track.artist_id == artist_id,
        ]
        if album_id:
            conditions.append(Track.album_id == album_id)

        stmt = select(Track).where(*conditions)
        return session.execute(stmt).scalar_one_or_none()

    def _upsert_track(
        self, session: Session, track_data: SoulSyncTrack, artist: Artist, album: Optional[Album]
    ) -> Track:
        """
        Insert or update a single track.

        Args:
            session: SQLAlchemy session
            track_data: SoulSyncTrack object
            artist: Artist object
            album: Album object (optional)

        Returns:
            Track object (inserted or updated)
        """
        # Try to find existing track
        track = self._find_track_by_identifiers(session, track_data.identifiers)
        if track is None:
            track = self._find_track_by_metadata(
                session,
                track_data.title,
                artist.id,
                album.id if album else None,
            )

        if track is None:
            # Create new track
            track = Track(
                title=track_data.title,
                sort_title=track_data.sort_title,
                edition=track_data.edition,
                artist=artist,
                album=album,
                duration=track_data.duration,
                track_number=track_data.track_number,
                disc_number=track_data.disc_number,
                bitrate=track_data.bitrate,
                file_path=track_data.file_path,
                file_format=track_data.file_format,
                sample_rate=track_data.sample_rate,
                bit_depth=track_data.bit_depth,
                file_size_bytes=track_data.file_size_bytes,
                added_at=track_data.added_at, # Set added_at only on insert
                musicbrainz_id=track_data.musicbrainz_id,
            )
            session.add(track)
            session.flush()
            logger.debug(f"Created new track: {track.title} by {artist.name}")
        else:
            # Update existing track (Sparse Updates)
            # Identity fields - always update
            track.title = track_data.title
            if album and track.album_id != album.id:
                track.album = album
            if track.artist_id != artist.id:
                track.artist = artist

            # Metadata fields - only update if incoming is not None
            if track_data.sort_title is not None:
                track.sort_title = track_data.sort_title
            if track_data.edition is not None:
                track.edition = track_data.edition
            if track_data.duration is not None:
                track.duration = track_data.duration
            if track_data.track_number is not None:
                track.track_number = track_data.track_number
            if track_data.disc_number is not None:
                track.disc_number = track_data.disc_number
            if track_data.bitrate is not None:
                track.bitrate = track_data.bitrate
            if track_data.file_path is not None:
                track.file_path = track_data.file_path
            if track_data.file_format is not None:
                track.file_format = track_data.file_format
            if track_data.sample_rate is not None:
                track.sample_rate = track_data.sample_rate
            if track_data.bit_depth is not None:
                track.bit_depth = track_data.bit_depth
            if track_data.file_size_bytes is not None:
                track.file_size_bytes = track_data.file_size_bytes
            if track_data.musicbrainz_id is not None:
                track.musicbrainz_id = track_data.musicbrainz_id

            # NOTE: Explicitly NOT updating added_at to preserve original import time
            logger.debug(f"Updated existing track: {track.title} by {artist.name}")

        # Ensure all identifiers are linked to this track
        for identifier in track_data.identifiers:
            provider_source = identifier.get("provider_source")
            provider_item_id = identifier.get("provider_item_id")
            raw_data = identifier.get("raw_data")

            if not provider_source or not provider_item_id:
                continue

            # Check if identifier already exists
            stmt = select(ExternalIdentifier).where(
                ExternalIdentifier.provider_source == provider_source,
                ExternalIdentifier.provider_item_id == provider_item_id,
            )
            ext_id = session.execute(stmt).scalar_one_or_none()

            if ext_id is None:
                # Create new identifier
                ext_id = ExternalIdentifier(
                    track=track,
                    provider_source=provider_source,
                    provider_item_id=provider_item_id,
                    raw_data=raw_data,
                )
                session.add(ext_id)
            else:
                # Link to track if different
                if ext_id.track_id != track.id:
                    ext_id.track = track
                if raw_data is not None:
                    ext_id.raw_data = raw_data

        return track

    def bulk_import(self, tracks: List[SoulSyncTrack]) -> int:
        """
        Bulk import SoulSyncTrack objects into database.
        Uses local caching and batched commits for efficiency.

        Args:
            tracks: List of SoulSyncTrack objects

        Returns:
            Number of tracks successfully imported
        """
        if not tracks:
            logger.warning("No tracks provided for bulk import")
            return 0

        logger.info(f"Starting bulk import of {len(tracks)} tracks")

        session = self.session_factory()
        imported_count = 0
        failed_count = 0

        try:
            for idx, track_data in enumerate(tracks):
                try:
                    # Skip tracks with missing required fields
                    if not track_data.title or not track_data.title.strip():
                        failed_count += 1
                        logger.warning(
                            "Skipping track %s/%s due to missing title: artist='%s' album='%s'",
                            idx + 1,
                            len(tracks),
                            track_data.artist_name,
                            track_data.album_title,
                        )
                        continue
                    
                    if not track_data.artist_name or not track_data.artist_name.strip():
                        failed_count += 1
                        logger.warning(
                            "Skipping track %s/%s due to missing artist: title='%s'",
                            idx + 1,
                            len(tracks),
                            track_data.title,
                        )
                        continue
                    
                    logger.debug(
                        "Processing track %s/%s: title='%s' artist='%s' album='%s'",
                        idx + 1,
                        len(tracks),
                        track_data.title,
                        track_data.artist_name,
                        track_data.album_title,
                    )

                    # Get or create artist
                    artist = self._get_or_create_artist(
                        session,
                        track_data.artist_name,
                        sort_name=track_data.artist_sort_name
                    )

                    # Get or create album
                    album = self._get_or_create_album(
                        session,
                        track_data.album_title,
                        artist,
                        track_data.release_year,
                        album_type=track_data.album_type,
                        release_group_id=track_data.album_release_group_id
                    )

                    # Upsert track
                    track = self._upsert_track(session, track_data, artist, album)
                    imported_count += 1

                except Exception as e:
                    failed_count += 1
                    logger.error(
                        f"Failed to import track '{track_data.title}': {e}",
                        exc_info=True,
                    )
                    continue

                # Batch commit every BATCH_SIZE tracks
                if (idx + 1) % BATCH_SIZE == 0:
                    session.commit()
                    logger.info(
                        f"Batch committed: {idx + 1}/{len(tracks)} tracks processed"
                    )

            # Final commit
            session.commit()
            logger.info(
                f"Bulk import complete: {imported_count} imported, {failed_count} failed"
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Bulk import failed with exception: {e}", exc_info=True)
            raise
        finally:
            session.close()

        return imported_count
