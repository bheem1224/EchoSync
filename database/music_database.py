#!/usr/bin/env python3

"""Track-centric SQLAlchemy database models and helper class."""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple

from time_utils import UTCDateTime, utc_now

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)


class Base(DeclarativeBase):
    """Base metadata class for SQLAlchemy models."""


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sort_name: Mapped[Optional[str]] = mapped_column(String)
    musicbrainz_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    image_url: Mapped[Optional[str]] = mapped_column(String)
    metadata_status: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, server_default='{}')

    albums: Mapped[List["Album"]] = relationship(
        back_populates="artist", cascade="all, delete-orphan"
    )
    tracks: Mapped[List["Track"]] = relationship(
        back_populates="artist", cascade="all, delete-orphan"
    )
    aliases: Mapped[List["ArtistAlias"]] = relationship(
        back_populates="artist", cascade="all, delete-orphan"
    )


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    artist_id: Mapped[int] = mapped_column(
        ForeignKey("artists.id", ondelete="CASCADE"), nullable=False
    )
    release_date: Mapped[Optional[date]] = mapped_column(Date)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String)
    release_group_id: Mapped[Optional[str]] = mapped_column(String)
    mb_release_id: Mapped[Optional[str]] = mapped_column(String)
    original_release_date: Mapped[Optional[date]] = mapped_column(Date)
    album_type: Mapped[Optional[str]] = mapped_column(String)

    artist: Mapped[Artist] = relationship(back_populates="albums")
    tracks: Mapped[List["Track"]] = relationship(
        back_populates="album", cascade="all, delete-orphan"
    )


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sort_title: Mapped[Optional[str]] = mapped_column(String)
    edition: Mapped[Optional[str]] = mapped_column(String)  # remaster, live, remix, deluxe, acoustic, etc.
    album_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("albums.id", ondelete="CASCADE")
    )
    artist_id: Mapped[int] = mapped_column(
        ForeignKey("artists.id", ondelete="CASCADE"), nullable=False
    )

    duration: Mapped[Optional[int]] = mapped_column()  # milliseconds
    track_number: Mapped[Optional[int]] = mapped_column()
    disc_number: Mapped[Optional[int]] = mapped_column()
    bitrate: Mapped[Optional[int]] = mapped_column()
    file_path: Mapped[Optional[str]] = mapped_column(String)
    file_format: Mapped[Optional[str]] = mapped_column(String)
    sample_rate: Mapped[Optional[int]] = mapped_column(Integer)
    bit_depth: Mapped[Optional[int]] = mapped_column(Integer)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    added_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime())

    musicbrainz_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    isrc: Mapped[Optional[str]] = mapped_column(String)
    global_rating: Mapped[Optional[float]] = mapped_column(Float)
    metadata_status: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, server_default='{}')

    album: Mapped[Optional[Album]] = relationship(back_populates="tracks")
    artist: Mapped[Artist] = relationship(back_populates="tracks")
    external_identifiers: Mapped[List["ExternalIdentifier"]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )
    audio_fingerprints: Mapped[List["AudioFingerprint"]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )
    aliases: Mapped[List["TrackAlias"]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )

    @hybrid_property
    def get_consensus_rating(self) -> int:
        if self.global_rating is None:
            return 0
        return int(round(self.global_rating))


class ExternalIdentifier(Base):
    __tablename__ = "external_identifiers"
    __table_args__ = (
        UniqueConstraint("provider_source", "provider_item_id", name="uq_provider_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_source: Mapped[str] = mapped_column(String, nullable=False)
    provider_item_id: Mapped[str] = mapped_column(String, nullable=False)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)

    track: Mapped[Track] = relationship(back_populates="external_identifiers")


class AudioFingerprint(Base):
    __tablename__ = "audio_fingerprints"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # chromaprint: raw locally-generated Chromaprint string (AcoustID algorithm output).
    # acoustid_id: the AcoustID service's confirmed UUID for this recording (returned after lookup).
    # These are deliberately separate — chromaprint is our local computation; acoustid_id is
    # the external service's canonical identifier.
    chromaprint: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    acoustid_id: Mapped[Optional[str]] = mapped_column(String)

    track: Mapped[Track] = relationship(back_populates="audio_fingerprints")


class TrackAlias(Base):
    """Localised / transliterated names for a track (e.g. Romaji, Pinyin)."""
    __tablename__ = "track_aliases"
    __table_args__ = (
        UniqueConstraint("track_id", "locale", "script", "name", name="uq_track_alias"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    locale: Mapped[Optional[str]] = mapped_column(String)   # e.g. 'en', 'zh', 'ja'
    script: Mapped[Optional[str]] = mapped_column(String)   # e.g. 'Latn', 'Hant', 'Hans', 'Hrkt'
    is_primary_for_locale: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    track: Mapped["Track"] = relationship(back_populates="aliases")


class ArtistAlias(Base):
    """Localised / transliterated names for an artist."""
    __tablename__ = "artist_aliases"
    __table_args__ = (
        UniqueConstraint("artist_id", "locale", "script", "name", name="uq_artist_alias"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artist_id: Mapped[int] = mapped_column(
        ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    locale: Mapped[Optional[str]] = mapped_column(String)
    script: Mapped[Optional[str]] = mapped_column(String)
    is_primary_for_locale: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    artist: Mapped["Artist"] = relationship(back_populates="aliases")


class TrackAudioFeatures(Base):
    __tablename__ = "track_audio_features"

    sync_id: Mapped[str] = mapped_column(String, primary_key=True)
    tempo: Mapped[Optional[float]] = mapped_column(Float)
    energy: Mapped[Optional[float]] = mapped_column(Float)
    valence: Mapped[Optional[float]] = mapped_column(Float)
    danceability: Mapped[Optional[float]] = mapped_column(Float)
    acousticness: Mapped[Optional[float]] = mapped_column(Float)


def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    # ensure foreign keys are enforced
    cursor.execute("PRAGMA foreign_keys=ON")
    # give other connections a bit longer before raising "database is locked" (MUST be before WAL)
    try:
        cursor.execute("PRAGMA busy_timeout=5000")
    except Exception:
        pass
    # use WAL mode so long-running writes don't block readers (fixes UI freeze during updates)
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
    except Exception:
        # older SQLite versions may not support WAL; ignore failure
        pass
    cursor.close()


class MusicDatabase:
    """Helper for creating the engine/session and managing the schema."""

    def __init__(self, database_path: Optional[str] = None) -> None:
        data_dir = os.getenv("SOULSYNC_DATA_DIR")
        if database_path:
            resolved_path = Path(database_path)
        elif data_dir:
            resolved_path = Path(data_dir) / "music_library.db"
        else:
            resolved_path = Path("data") / "music_library.db"

        self.database_path = resolved_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            f"sqlite:///{self.database_path}",
            future=True,
            echo=False,
            poolclass=NullPool,
            connect_args={"check_same_thread": False},
        )
        event.listen(self.engine, "connect", _sqlite_pragmas)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

    def create_all(self) -> None:
        pass

    def drop_all(self) -> None:
        Base.metadata.drop_all(self.engine)

    def session(self) -> Session:
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def search_library(self, query: str) -> Dict[str, List[Dict]]:
        """Search across Artists, Albums, and Tracks."""
        results = {
            "artists": [],
            "albums": [],
            "tracks": []
        }

        if not query:
            return results

        search_term = f"%{query}%"

        with self.session_scope() as session:
            # Search Artists
            artists = session.query(Artist).filter(Artist.name.ilike(search_term)).limit(20).all()
            for artist in artists:
                results["artists"].append({
                    "id": artist.id,
                    "name": artist.name,
                    "image_url": artist.image_url
                })

            # Search Albums
            albums = session.query(Album).join(Artist).filter(
                (Album.title.ilike(search_term)) |
                (Artist.name.ilike(search_term))
            ).limit(20).all()
            for album in albums:
                results["albums"].append({
                    "id": album.id,
                    "title": album.title,
                    "artist_id": album.artist_id,
                    "artist_name": album.artist.name,
                    "cover_image_url": album.cover_image_url,
                    "year": album.release_date.year if album.release_date else None
                })

            # Search Tracks
            tracks = session.query(Track).join(Artist).join(Album, isouter=True).filter(
                (Track.title.ilike(search_term)) |
                (Artist.name.ilike(search_term)) |
                (Album.title.ilike(search_term))
            ).limit(50).all()

            for track in tracks:
                results["tracks"].append({
                    "id": track.id,
                    "title": track.title,
                    "artist_id": track.artist_id,
                    "artist_name": track.artist.name,
                    "album_id": track.album_id,
                    "album_title": track.album.title if track.album else "Unknown Album",
                    "duration": track.duration
                })

        return results

    def search_canonical_fuzzy(self, title: str, artist: Optional[str] = None, limit: int = 10) -> List:
        """Fuzzy search canonical tracks by title and optional artist substring.

        Returns a list of ``SoulSyncTrack`` objects (each has a ``to_dict()`` method).
        """
        from core.matching_engine.soul_sync_track import SoulSyncTrack
        results = []
        with self.session_scope() as session:
            query = (
                session.query(Track)
                .join(Artist)
                .join(Album, isouter=True)
                .filter(Track.title.ilike(f"%{title}%"))
            )
            if artist:
                query = query.filter(Artist.name.ilike(f"%{artist}%"))
            tracks = query.limit(limit).all()
            for t in tracks:
                results.append(SoulSyncTrack(
                    raw_title=t.title,
                    artist_name=t.artist.name,
                    album_title=t.album.title if t.album else "",
                    duration=t.duration,
                    track_number=t.track_number,
                    disc_number=t.disc_number,
                    bitrate=t.bitrate,
                    file_path=t.file_path,
                    file_format=t.file_format,
                    musicbrainz_id=t.musicbrainz_id,
                    isrc=t.isrc,
                    acoustid_id=next((fp.acoustid_id for fp in t.audio_fingerprints if fp.acoustid_id), None),
                ))
        return results

    def search_canonical_by_ids(
        self,
        isrc: Optional[str] = None,
        musicbrainz_recording_id: Optional[str] = None,
        acoustid: Optional[str] = None,
    ) -> List:
        """Search canonical tracks by global identifiers (ISRC, MBID, AcoustID).

        The ``acoustid`` parameter filters via the ``audio_fingerprints`` table.
        Returns a list of ``SoulSyncTrack`` objects.
        """
        from core.matching_engine.soul_sync_track import SoulSyncTrack
        from sqlalchemy import or_
        results = []
        filters = []
        if isrc:
            filters.append(Track.isrc == isrc)
        if musicbrainz_recording_id:
            filters.append(Track.musicbrainz_id == musicbrainz_recording_id)
        if acoustid:
            filters.append(
                Track.audio_fingerprints.any(AudioFingerprint.acoustid_id == acoustid)
            )
        if not filters:
            return results
        with self.session_scope() as session:
            tracks = (
                session.query(Track)
                .join(Artist)
                .join(Album, isouter=True)
                .filter(or_(*filters))
                .all()
            )
            for t in tracks:
                results.append(SoulSyncTrack(
                    raw_title=t.title,
                    artist_name=t.artist.name,
                    album_title=t.album.title if t.album else "",
                    duration=t.duration,
                    track_number=t.track_number,
                    disc_number=t.disc_number,
                    bitrate=t.bitrate,
                    file_path=t.file_path,
                    file_format=t.file_format,
                    musicbrainz_id=t.musicbrainz_id,
                    isrc=t.isrc,
                    acoustid_id=next((fp.acoustid_id for fp in t.audio_fingerprints if fp.acoustid_id), None),
                ))
        return results

    def get_external_identifier_map(self, provider_source: str, track_ids: List[int]) -> Dict[int, str]:
        """Return a map of track_id -> provider_item_id for a provider.

        Used to quickly determine whether tracks already exist on a target source
        (e.g., Plex ratingKeys) without issuing repeated lookups.
        """
        if not track_ids:
            return {}

        with self.session_scope() as session:
            rows = (
                session.query(
                    ExternalIdentifier.track_id,
                    ExternalIdentifier.provider_item_id,
                )
                .filter(
                    ExternalIdentifier.provider_source == provider_source,
                    ExternalIdentifier.track_id.in_(track_ids),
                )
                .all()
            )

            return {track_id: provider_item_id for track_id, provider_item_id in rows}

    def get_external_identifier(self, provider_source: str, track_id: int) -> Optional[str]:
        """Return a single provider_item_id for a track/provider if present."""
        mapping = self.get_external_identifier_map(provider_source, [track_id])
        return mapping.get(track_id)

    def track_has_external_identifier(self, provider_source: str, track_id: int) -> bool:
        """Boolean helper for quick existence checks."""
        return bool(self.get_external_identifier(provider_source, track_id))

    @property
    def session_factory(self):
        """Expose the configured sessionmaker for external consumers (e.g., LibraryManager)."""
        return self.SessionLocal

    def count_artists(self) -> int:
        """Return total artists stored."""
        with self.session_scope() as session:
            return session.query(Artist).count()

    def count_albums(self) -> int:
        """Return total albums stored."""
        with self.session_scope() as session:
            return session.query(Album).count()

    def count_tracks(self) -> int:
        """Return total tracks stored."""
        with self.session_scope() as session:
            return session.query(Track).count()

    def check_track_exists(self, title: str, artist: str, confidence_threshold: float = 0.7, server_source: str = None) -> Tuple[Optional[Track], float]:
        """Check if a track exists in the database using fuzzy matching."""
        # Local imports to avoid potential circular dependency at module level
        from core.matching_engine.matching_engine import WeightedMatchingEngine
        from core.matching_engine.scoring_profile import ExactSyncProfile
        from core.matching_engine.soul_sync_track import SoulSyncTrack
        from sqlalchemy import or_
        import re

        profile = ExactSyncProfile()
        engine = WeightedMatchingEngine(profile)

        # Create source track object
        source_track = SoulSyncTrack(
            raw_title=title,
            artist_name=artist,
            album_title=""
        )

        best_match = None
        best_score = 0.0

        # Pass 2 Base String generation for broader database search
        base_title = re.sub(r'[\(\[].*?[\)\]]', '', title)
        base_title = re.sub(r'-.*$', '', base_title).strip()

        base_artist = re.sub(r'[\(\[].*?[\)\]]', '', artist)
        base_artist = re.sub(r'-.*$', '', base_artist).strip()

        with self.session_scope() as session:
            # Find candidates using the broader base strings
            candidates = session.query(Track).join(Artist).filter(
                or_(
                    Artist.name.ilike(f"%{base_artist}%"),
                    Track.title.ilike(f"%{base_title}%")
                )
            ).limit(50).all()

            for candidate in candidates:
                # Convert DB track to SoulSyncTrack for comparison
                cand_obj = SoulSyncTrack(
                    raw_title=candidate.title,
                    artist_name=candidate.artist.name,
                    album_title=candidate.album.title if candidate.album else "",
                    duration=candidate.duration,
                )

                result = engine.calculate_match(source_track, cand_obj)
                if result.confidence_score > best_score:
                    best_score = result.confidence_score
                    best_match = candidate

            if best_match:
                session.expunge(best_match)

        if best_score >= (confidence_threshold * 100):
            return best_match, best_score / 100.0

        return None, 0.0

    def get_library_hierarchy(self) -> List[Dict]:
        """Fetch the entire library hierarchy (Artist -> Album -> Track)."""
        with self.session_scope() as session:
            # Use selectinload (separate SELECT per relationship) rather than joinedload
            # (which emits a single Cartesian-product JOIN). For large libraries the JOIN
            # inflates row count to artists×albums×tracks, causing an OOM spike.
            from sqlalchemy.orm import selectinload
            artists = session.query(Artist).options(
                selectinload(Artist.albums).selectinload(Album.tracks)
            ).order_by(Artist.name).all()

            hierarchy = []
            for artist in artists:
                artist_data = {
                    "id": artist.id,
                    "name": artist.name,
                    "image_url": artist.image_url,
                    "albums": []
                }

                # Sort albums by release date or title
                sorted_albums = sorted(artist.albums, key=lambda a: a.release_date or date.min, reverse=True)

                for album in sorted_albums:
                    album_data = {
                        "id": album.id,
                        "title": album.title,
                        "cover_image_url": album.cover_image_url,
                        "year": album.release_date.year if album.release_date else None,
                        "tracks": []
                    }

                    # Sort tracks by track number
                    sorted_tracks = sorted(album.tracks, key=lambda t: (t.disc_number or 1, t.track_number or 0))

                    for track in sorted_tracks:
                        album_data["tracks"].append({
                            "id": track.id,
                            "title": track.title,
                            "duration": track.duration,
                            "track_number": track.track_number,
                            "disc_number": track.disc_number
                        })

                    artist_data["albums"].append(album_data)

                hierarchy.append(artist_data)

            return hierarchy

    def get_track_path(self, track_id: int) -> Optional[str]:
        """Fetch the local file path for a track ID."""
        with self.session_scope() as session:
            track = session.query(Track).filter(Track.id == track_id).first()
            if track:
                return track.file_path
            return None

    def clear_server_data(self, server_source: str):
        """Purge all tracks/albums/artists associated with a given provider source.

        This is useful when re-syncing a media server from scratch. It deletes
        all tracks that have an ExternalIdentifier for the specified ``server_source``
        (e.g. "plex"), along with orphaned albums and artists.
        """
        with self.session_scope() as session:
            # delete tracks that reference this provider
            track_ids = (
                session.query(Track.id)
                .join(ExternalIdentifier)
                .filter(ExternalIdentifier.provider_source == server_source)
                .distinct()
                .all()
            )
            if track_ids:
                ids = [t[0] for t in track_ids]
                session.query(Track).filter(Track.id.in_(ids)).delete(synchronize_session=False)

            # remove identifiers themselves
            session.query(ExternalIdentifier).filter(
                ExternalIdentifier.provider_source == server_source
            ).delete(synchronize_session=False)

            # clean up albums with no remaining tracks
            session.query(Album).filter(~Album.tracks.any()).delete(synchronize_session=False)

            # clean up artists with no remaining tracks
            session.query(Artist).filter(~Artist.tracks.any()).delete(synchronize_session=False)

    def dispose(self) -> None:
        self.engine.dispose()


_db_instance: Optional[MusicDatabase] = None


def get_database(database_path: Optional[str] = None) -> MusicDatabase:
    global _db_instance
    if _db_instance is None:
        _db_instance = MusicDatabase(database_path)
    return _db_instance


def close_database() -> None:
    global _db_instance
    if _db_instance is not None:
        _db_instance.dispose()
        _db_instance = None


__all__ = [
    "Base",
    "Artist",
    "Album",
    "Track",
    "ExternalIdentifier",
    "AudioFingerprint",
    "TrackAudioFeatures",
    "TrackAlias",
    "ArtistAlias",
    "MusicDatabase",
    "get_database",
    "close_database",
]
