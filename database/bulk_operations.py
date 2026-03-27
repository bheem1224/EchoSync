"""
Bulk import operations using SQLAlchemy 2.0 and LibraryManager.
Efficiently ingests SoulSyncTrack objects into the database with caching.
"""
from collections import defaultdict
from typing import List, Dict, Optional, Tuple, Callable, Iterable
from datetime import date, datetime
import time

from sqlalchemy import select, func, delete
from sqlalchemy.orm import sessionmaker, Session

from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.matching_engine import text_utils
from core.tiered_logger import get_logger
from .music_database import Artist, Album, Track, ExternalIdentifier, AudioFingerprint

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

        # Check DB using case-insensitive lookup (may not strip accents)
        stmt = select(Artist).where(
            func.lower(Artist.name) == norm_name
        )
        artist = session.execute(stmt).scalar_one_or_none()
        # Additional fallback: try Python normalization to catch accent variants
        if artist is None:
            # since artist_cache may already contain normalized values from DB,
            # we can leverage it here to avoid another query
            if norm_name in self.artist_cache:
                uid = self.artist_cache[norm_name]
                stmt2 = select(Artist).where(Artist.id == uid)
                artist = session.execute(stmt2).scalar_one_or_none()
            else:
                # final brute-force scan (should be rare after cache prepopulate)
                stmt2 = select(Artist)
                for a in session.execute(stmt2).scalars().all():
                    if self._normalize_name(a.name) == norm_name:
                        artist = a
                        break

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
        mb_release_id: Optional[str] = None,
        original_release_date: Optional[date] = None,
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
            mb_release_id: MusicBrainz Release ID
            original_release_date: Original release date

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
            if mb_release_id and not album.mb_release_id:
                album.mb_release_id = mb_release_id
            if original_release_date and not album.original_release_date:
                album.original_release_date = original_release_date
            return album

        # Check DB using case-insensitive lookup (may not strip accents)
        stmt = select(Album).where(
            func.lower(Album.title) == norm_title,
            Album.artist_id == artist.id,
        )
        album = session.execute(stmt).scalar_one_or_none()
        # Fallback via normalization similar to artists
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

        release_date = date(release_year, 1, 1) if release_year else None

        if album is None:
            # Create new album
            album = Album(
                title=album_title,
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
            # Update metadata if needed
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
            identifiers: Dict of identifiers from SoulSyncTrack (key=source, value=id)

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
                .join(ExternalIdentifier)
                .where(
                    ExternalIdentifier.provider_source == source,
                    ExternalIdentifier.provider_item_id == item_id,
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

        Args:
            session: SQLAlchemy session
            title: Track title
            artist_id: Artist ID
            album_id: Album ID (optional)
            track_number: Track number (optional)
            file_path: File path (optional)

        Returns:
            Track object or None
        """
        # Highest confidence: if file_path matches, it's definitely the same physical file/track
        if file_path:
            stmt = select(Track).where(Track.file_path == file_path)
            track = session.execute(stmt).scalar_one_or_none()
            if track:
                return track

        # Otherwise, match strictly on title + artist + album + track_number
        norm_title = self._normalize_name(title)
        conditions = [
            func.lower(Track.title) == norm_title,
            Track.artist_id == artist_id,
        ]
        if album_id:
            conditions.append(Track.album_id == album_id)
        if track_number is not None:
            conditions.append(Track.track_number == track_number)

        stmt = select(Track).where(*conditions)
        # Using first() to handle edge cases gracefully, but ideally this composite is unique
        return session.execute(stmt).scalars().first()

    def _upsert_track(
        self, session: Session, track_data: SoulSyncTrack, artist: Artist, album: Optional[Album]
    ) -> tuple[Track, bool]:
        """
        Insert or update a single track.

        Args:
            session: SQLAlchemy session
            track_data: SoulSyncTrack object
            artist: Artist object
            album: Album object (optional)

        Returns:
            Tuple of (Track object, is_new: bool)
            is_new is True if track was newly created, False if updated
        """
        # Strict guard: every track ingested through this path must carry a sync_id.
        if not track_data.sync_id:
            logger.error(
                f"Rejecting track '{track_data.title}' by '{track_data.artist_name}' "
                "due to missing sync_id"
            )
            return None, False

        # FIRST: Check for existing external identifiers (provider-agnostic deduplication)
        # This prevents duplicates across ALL providers (Plex ratingKey, Jellyfin ID, Navidrome ID, etc.)
        # If same external ID exists, it must be the same track - update it instead of creating new
        track = None
        if track_data.identifiers:
            for provider_source, provider_item_id in track_data.identifiers.items():
                if provider_source and provider_item_id:
                    stmt = select(ExternalIdentifier).where(
                        ExternalIdentifier.provider_source == provider_source,
                        ExternalIdentifier.provider_item_id == str(provider_item_id)
                    )
                    ext_id = session.execute(stmt).scalar_one_or_none()
                    if ext_id and ext_id.track:
                        track = ext_id.track
                        # Found match - no logging needed here, will log in update section if needed
                        break  # Use first match
        
        # SECOND: Try to find by other methods if external ID didn't match
        if track is None:
            track = self._find_track_by_identifiers(session, track_data.identifiers)
        
        # THIRD: Try to find by metadata
        if track is None:
            track = self._find_track_by_metadata(
                session,
                track_data.title,
                artist.id,
                album.id if album else None,
                track_number=track_data.track_number,
                file_path=track_data.file_path,
            )
            # If we matched via metadata but the incoming identifier for this provider
            # is not already linked to the returned track then we should treat
            # the record as a *new* track rather than merging. This prevents
            # distinct Plex items (different ratingKeys) with identical
            # metadata from collapsing into one row.
            if track is not None and track_data.identifiers:
                # build set of (source, id) currently attached to track
                existing_ids = { (e.provider_source, e.provider_item_id) for e in track.external_identifiers }
                mismatch = True
                for src, pid in track_data.identifiers.items():
                    if src and pid and (src, str(pid)) in existing_ids:
                        mismatch = False
                        break
                if mismatch:
                    # nullify track so creation path runs
                    track = None

        if track is None:
            # Create new track
            track = Track(
                sync_id=track_data.sync_id,
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
                isrc=track_data.isrc,
            )
            session.add(track)
            session.flush()
            logger.debug(f"Created new track: {track.title} by {artist.name}")
            is_new = True
        else:
            # Update existing track (Sparse Updates)
            # Identity fields - always update
            old_title = track.title
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
            else:
                # Special case: If title changed significantly and edition looks corrupted, clear it
                # Corruption patterns: dangling parenthesis, typos like "titile", very short strings
                # Also check if edition content is actually part of the new title (split corruption)
                if track.edition and old_title != track_data.title:
                    edition_lower = track.edition.lower()
                    new_title_lower = track_data.title.lower()
                    
                    is_corrupted = (
                        'titile' in edition_lower or  # Common typo
                        track.edition.startswith(') -') or  # Dangling parenthesis
                        track.edition.startswith('(') and ')' not in track.edition or  # Unmatched paren
                        len(track.edition.strip()) < 3 or  # Too short
                        track.edition.count('(') != track.edition.count(')') or  # Mismatched parens
                        edition_lower in new_title_lower  # Edition content is now part of title (split fix)
                    )
                    if is_corrupted:
                        logger.info(
                            f"Corruption fix: Clearing corrupted edition '{track.edition}' "
                            f"for track '{track_data.title}'"
                        )
                        track.edition = None
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
            if track_data.isrc is not None:
                track.isrc = track_data.isrc
            if track.sync_id != track_data.sync_id:
                track.sync_id = track_data.sync_id

            # NOTE: Explicitly NOT updating added_at to preserve original import time
            
            # Only log at DEBUG level for routine updates (reduces log spam)
            logger.debug(f"Updated existing track: {track.title} by {artist.name}")
            is_new = False

        # Ensure all identifiers are linked to this track
        for source, item_id in track_data.identifiers.items():
            if not source or not item_id:
                continue

            # Ensure item_id is a string
            if not isinstance(item_id, str):
                item_id = str(item_id)

            # Fast-path bulk upserts can skip relationship change detection, so explicitly
            # upsert identifier rows keyed by (track_id, provider_source).
            stmt = select(ExternalIdentifier).where(
                ExternalIdentifier.track_id == track.id,
                ExternalIdentifier.provider_source == source,
            )
            ext_id = session.execute(stmt).scalar_one_or_none()

            if ext_id is None:
                ext_id = ExternalIdentifier(
                    track_id=track.id,
                    provider_source=source,
                    provider_item_id=item_id,
                    raw_data=None,  # Raw data not supported in simple dict mapping
                )
                session.add(ext_id)
            elif ext_id.provider_item_id != item_id:
                ext_id.provider_item_id = item_id

        # Handle Audio Fingerprint
        if track_data.fingerprint:
            stmt = select(AudioFingerprint).where(
                AudioFingerprint.fingerprint_hash == track_data.fingerprint
            )
            af = session.execute(stmt).scalar_one_or_none()

            if af is None:
                af = AudioFingerprint(
                    track=track,
                    fingerprint_hash=track_data.fingerprint,
                    acoustid_id=track_data.acoustid_id
                )
                session.add(af)
            else:
                if af.track_id != track.id:
                    af.track = track
                if track_data.acoustid_id and not af.acoustid_id:
                    af.acoustid_id = track_data.acoustid_id

        return track, is_new

    def _delete_missing_tracks(self, session: Session, observed_identifiers: Dict[str, set[str]]) -> int:
        """Remove tracks that are no longer present for a given provider source.

        Args:
            session: SQLAlchemy session
            observed_identifiers: Map of provider_source -> set of provider_item_id values seen in this import

        Returns:
            Number of tracks deleted
        """
        if not observed_identifiers:
            return 0

        deleted_track_ids: set[int] = set()

        for source, item_ids in observed_identifiers.items():
            stmt = select(Track.id).join(ExternalIdentifier).where(
                ExternalIdentifier.provider_source == source
            )

            # If no items were observed for this provider, delete all entries for that source
            if item_ids:
                stmt = stmt.where(~ExternalIdentifier.provider_item_id.in_(item_ids))

            stale_ids = session.execute(stmt).scalars().all()
            deleted_track_ids.update(stale_ids)

        if not deleted_track_ids:
            return 0

        session.execute(delete(Track).where(Track.id.in_(list(deleted_track_ids))))
        return len(deleted_track_ids)

    def bulk_import(
        self,
        tracks: Iterable[SoulSyncTrack],
        progress_callback: Optional[Callable[[Dict[str, int]], None]] = None,
        total_count: Optional[int] = None
    ) -> int:
        """
        Bulk import SoulSyncTrack objects into database.
        Uses local caching and batched commits for efficiency.
        Supports generators to minimize memory usage.

        Args:
            tracks: Iterable (list or generator) of SoulSyncTrack objects
            total_count: Optional total count for progress reporting (if tracks is a generator)

        Returns:
            Number of tracks processed (new + updated)
        """
        if not tracks:
            logger.warning("No tracks provided for bulk import")
            return 0

        # Try to determine length if not provided
        if total_count is None:
            try:
                total_count = len(tracks)
            except TypeError:
                total_count = 0  # Unknown total

        logger.info(f"Starting bulk import of {total_count if total_count > 0 else 'unknown number of'} tracks")

        session = self.session_factory()
        imported_count = 0
        updated_count = 0
        failed_count = 0
        observed_identifiers: Dict[str, set[str]] = defaultdict(set)
        # Progress tracking (unique artists/albums encountered)
        seen_artist_ids: set[int] = set()
        seen_album_ids: set[int] = set()

        # === prepopulate caches with existing database entries ===
        # This avoids creating duplicates due to normalization mismatch (e.g. accents)
        if not self.artist_cache:
            try:
                stmt = select(Artist)
                for a in session.execute(stmt).scalars().all():
                    norm = self._normalize_name(a.name)
                    if norm in self.artist_cache:
                        # existing artist with same normalized name -> merge
                        primary_id = self.artist_cache[norm]
                        primary = session.get(Artist, primary_id)
                        if primary and primary.id != a.id:
                            # reassign albums and tracks to primary
                            for alb in list(a.albums):
                                alb.artist = primary
                            for tr in list(a.tracks):
                                tr.artist = primary
                            # delete duplicate artist
                            try:
                                session.delete(a)
                                logger.info(f"Merged duplicate artist '{a.name}' into '{primary.name}'")
                            except Exception:
                                logger.debug(f"Failed to delete duplicate artist {a.name}")
                            continue  # skip caching this one
                    # cache valid id
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
                        # merge duplicate album into primary
                        primary_id = self.album_cache[key]
                        primary = session.get(Album, primary_id)
                        if primary and primary.id != alb.id:
                            for tr in list(alb.tracks):
                                tr.album = primary
                            try:
                                session.delete(alb)
                                logger.info(f"Merged duplicate album '{alb.title}' into '{primary.title}'")
                            except Exception:
                                logger.debug(f"Failed to delete duplicate album {alb.title}")
                            continue
                    self.album_cache[key] = alb.id
            except Exception:
                pass

        try:
            for idx, track_data in enumerate(tracks):
                # yield occasionally to allow other threads to run and avoid hogging the GIL
                if idx and idx % 10 == 0:
                    import time
                    time.sleep(0)

                try:
                    # Skip tracks with missing required fields
                    if not track_data.title or not track_data.title.strip():
                        failed_count += 1
                        logger.warning(
                            "Skipping track %s due to missing title: artist='%s' album='%s'",
                            idx + 1,
                            track_data.artist_name,
                            track_data.album_title,
                        )
                        continue
                    
                    if not track_data.artist_name or not track_data.artist_name.strip():
                        failed_count += 1
                        logger.warning(
                            "Skipping track %s due to missing artist: title='%s'",
                            idx + 1,
                            track_data.title,
                        )
                        continue
                    
                    # Only log every 100 tracks to reduce spam (batch commits log at that interval)
                    if (idx + 1) % 100 == 0 or idx == 0:
                        logger.debug(
                            "Processing track %s: title='%s' artist='%s' album='%s'",
                            idx + 1,
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
                    if artist and artist.id:
                        seen_artist_ids.add(artist.id)

                    # Get or create album
                    album = self._get_or_create_album(
                        session,
                        track_data.album_title,
                        artist,
                        track_data.release_year,
                        album_type=track_data.album_type,
                        release_group_id=track_data.album_release_group_id,
                        mb_release_id=track_data.mb_release_id,
                        original_release_date=track_data.original_release_date
                    )
                    if album and album.id:
                        seen_album_ids.add(album.id)

                    # Upsert track
                    track, is_new = self._upsert_track(session, track_data, artist, album)

                    # Track identifier observations for deletion detection
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
                    logger.error(
                        f"Failed to import track '{track_data.title}': {e}",
                        exc_info=True,
                    )
                    continue

                # Batch commit every BATCH_SIZE tracks
                if (idx + 1) % BATCH_SIZE == 0:
                    session.commit()
                    logger.info(
                        f"Batch committed: {idx + 1} tracks processed"
                    )

                # Emit progress updates periodically (every 25 items and on each batch commit)
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
                        # Progress should never break import; ignore callback errors
                        pass

            # Final commit for inserts/updates
            session.commit()

            # Remove tracks that no longer exist for observed providers
            deleted_count = self._delete_missing_tracks(session, observed_identifiers)
            if deleted_count:
                session.commit()

            total_processed = imported_count + updated_count
            logger.info(
                f"Bulk import complete: {imported_count} new, {updated_count} updated, {deleted_count} deleted, {failed_count} failed (total processed: {total_processed})"
            )

            # Final progress callback
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
