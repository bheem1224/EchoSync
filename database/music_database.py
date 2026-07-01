#!/usr/bin/env python3

"""Track-centric SQLAlchemy database models and helper class."""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple

from time_utils import UTCDateTime, utc_now
from sqlalchemy.orm import joinedload, selectinload
from core.matching_engine.echo_sync_track import EchosyncTrack
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import ExactSyncProfile
import re
from sqlalchemy import or_

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
    scoped_session,
    validates,
)



import string
import random

def generate_nanoid(size=8) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choices(alphabet, k=size))

def _safe_parse_date(release_date) -> date:
    if not release_date:
        return date.min
    if isinstance(release_date, date):
        return release_date
    if isinstance(release_date, str):
        release_date = release_date.strip()
        if not release_date:
            return date.min
        try:
            return date.fromisoformat(release_date)
        except ValueError:
            pass
        try:
            return datetime.fromisoformat(release_date).date()
        except ValueError:
            pass
        if len(release_date) == 4 and release_date.isdigit():
            try:
                return date(int(release_date), 1, 1)
            except ValueError:
                pass
    return date.min

def _safe_int(val, default: int = 0) -> int:
    if val is None:
        return default
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return default
        try:
            return int(float(val))
        except ValueError:
            digits = []
            for char in val:
                if char.isdigit():
                    digits.append(char)
                else:
                    break
            if digits:
                return int("".join(digits))
    return default

class Base(DeclarativeBase):

    """Base metadata class for SQLAlchemy models."""


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    normalized_name: Mapped[str] = mapped_column(String, index=True, server_default="")
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

    @validates("name")
    def validate_name(self, key, value):
        if value:
            from core.matching_engine.text_utils import normalize_text
            self.normalized_name = normalize_text(value)
        return value


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    normalized_title: Mapped[str] = mapped_column(String, index=True, server_default="")
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

    @validates("title")
    def validate_title(self, key, value):
        if value:
            from core.matching_engine.text_utils import normalize_text
            self.normalized_title = normalize_text(value)
        return value


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    normalized_title: Mapped[str] = mapped_column(String, index=True, server_default="")
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
    added_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime())

    musicbrainz_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    isrc: Mapped[Optional[str]] = mapped_column(String)
    sync_id: Mapped[str] = mapped_column(String(8), unique=True, index=True, nullable=False, default=generate_nanoid)
    global_rating: Mapped[Optional[float]] = mapped_column(Float)
    metadata_status: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, server_default='{}')

    album: Mapped[Optional[Album]] = relationship(back_populates="tracks")
    artist: Mapped[Artist] = relationship(back_populates="tracks")
    aliases: Mapped[List["TrackAlias"]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )
    media_files: Mapped[List["LocalMedia"]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )
    external_identifiers: Mapped[List["ExternalIdentifier"]] = relationship(
        "ExternalIdentifier",
        secondary="local_media",
        primaryjoin="Track.id == LocalMedia.track_id",
        secondaryjoin="LocalMedia.media_id == ExternalIdentifier.media_id",
        viewonly=True,
    )

    def get_best_media(self) -> Optional["LocalMedia"]:
        """Return the highest-quality LocalMedia file attached to this track."""
        if not self.media_files:
            return None
        _LOSSLESS = {'flac', 'alac', 'wav', 'dsd', 'dsf', 'dff', 'ape'}
        def _quality_key(m: "LocalMedia"):
            fmt = (m.file_format or '').lower()
            is_lossless = 1 if fmt in _LOSSLESS else 0
            return (is_lossless, m.bitrate or 0, m.sample_rate or 0, m.bit_depth or 0)
        return max(self.media_files, key=_quality_key)

    @property
    def media(self) -> List["LocalMedia"]:
        """Backwards-compatible accessor. Returns all attached media files."""
        return self.media_files

    @property
    def file_path(self) -> Optional[str]:
        """Backwards-compatible accessor. Returns best media's file_path."""
        best = self.get_best_media()
        return best.file_path if best else None

    @property
    def audio_fingerprints(self):
        """Aggregate all fingerprints from all attached media files."""
        fps = []
        for m in self.media_files:
            fps.extend(m.audio_fingerprints)
        return fps

    @hybrid_property
    def get_consensus_rating(self) -> int:
        if self.global_rating is None:
            return 0
        return int(round(self.global_rating))

    @validates("title")
    def validate_title(self, key, value):
        if value:
            from core.matching_engine.text_utils import normalize_title
            self.normalized_title = normalize_title(value)
        return value

class LocalMedia(Base):
    __tablename__ = "local_media"

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[str] = mapped_column(String(8), unique=True, index=True, nullable=False, default=generate_nanoid)
    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    file_format: Mapped[Optional[str]] = mapped_column(String)
    bitrate: Mapped[Optional[int]] = mapped_column(Integer)
    sample_rate: Mapped[Optional[int]] = mapped_column(Integer)
    bit_depth: Mapped[Optional[int]] = mapped_column(Integer)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    inode: Mapped[Optional[int]] = mapped_column(BigInteger, index=True)
    mtime: Mapped[Optional[float]] = mapped_column(Float)
    added_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime())

    track: Mapped[Track] = relationship(back_populates="media_files")
    audio_fingerprints: Mapped[List["AudioFingerprint"]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )
    external_identifiers: Mapped[List["ExternalIdentifier"]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )


class ExternalIdentifier(Base):
    __tablename__ = "external_identifiers"
    __table_args__ = (
        UniqueConstraint("plugin_source", "plugin_item_id", name="uq_plugin_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[str] = mapped_column(
        ForeignKey("local_media.media_id", ondelete="CASCADE"), nullable=False, index=True
    )
    plugin_source: Mapped[str] = mapped_column(String, nullable=False, index=True)
    plugin_item_id: Mapped[str] = mapped_column(String, nullable=False)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)

    media: Mapped[LocalMedia] = relationship(back_populates="external_identifiers")


class AudioFingerprint(Base):
    __tablename__ = "audio_fingerprints"

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[str] = mapped_column(
        ForeignKey("local_media.media_id", ondelete="CASCADE"), nullable=False, index=True
    )
    # chromaprint: raw locally-generated Chromaprint string (AcoustID algorithm output).
    # acoustid_id: the AcoustID service's confirmed UUID for this recording (returned after lookup).
    # These are deliberately separate — chromaprint is our local computation; acoustid_id is
    # the external service's canonical identifier.
    chromaprint: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    acoustid_id: Mapped[Optional[str]] = mapped_column(String)

    media: Mapped[LocalMedia] = relationship(back_populates="audio_fingerprints")


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
    # PERF: synchronous=NORMAL skips fsync() on every commit.  With WAL mode
    # active this is safe — only the last transaction is at risk on an *OS*
    # crash (not a process crash), acceptable for a re-syncable media library.
    try:
        cursor.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    cursor.close()


class MusicDatabase:
    """Helper for creating the engine/session and managing the schema."""

    def __init__(self, database_path: Optional[str] = None) -> None:
        from core.settings import config_manager

        uri = config_manager.get("database.music_uri")
        if uri:
            engine_url = uri
        else:
            data_dir = os.getenv("ECHOSYNC_DATA_DIR")
            if database_path:
                resolved_path = Path(database_path)
            elif data_dir:
                resolved_path = Path(data_dir) / "music_library.db"
            else:
                resolved_path = Path("data") / "music_library.db"

            self.database_path = resolved_path
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            engine_url = f"sqlite:///{self.database_path}"

        connect_args = {"check_same_thread": False} if engine_url.startswith("sqlite") else {}

        self.engine = create_engine(
            engine_url,
            future=True,
            echo=False,
            poolclass=NullPool,
            connect_args=connect_args,
        )
        if engine_url.startswith("sqlite"):
            event.listen(self.engine, "connect", _sqlite_pragmas)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

    def create_all(self) -> None:
        pass

    def drop_all(self) -> None:
        Base.metadata.drop_all(self.engine)

    def session(self) -> Session:
        return self.SessionLocal()

    @property
    def session_factory(self):
        """Expose the configured sessionmaker for external consumers (e.g., LibraryManager)."""
        return self.SessionLocal

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
            # OPTIMIZATION: joinedload eliminates N+1 lazy loading queries

            # Search Artists
            artists = session.query(Artist).filter(Artist.name.ilike(search_term)).limit(20).all()
            for artist in artists:
                results["artists"].append({
                    "id": artist.id,
                    "name": artist.name,
                    "image_url": artist.image_url
                })

            # Search Albums
            albums = session.query(Album).options(
                joinedload(Album.artist)
            ).join(Artist).filter(
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
            tracks = session.query(Track).options(
                joinedload(Track.artist),
                joinedload(Track.album)
            ).join(Artist).join(Album, isouter=True).filter(
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

        Returns a list of ``EchosyncTrack`` objects (each has a ``to_dict()`` method).
        """
        results = []
        with self.session_scope() as session:
            # OPTIMIZATION: joinedload and selectinload eliminate N+1 queries during mapping

            query = (
                session.query(Track)
                .options(
                    joinedload(Track.artist),
                    joinedload(Track.album),
                    selectinload(Track.audio_fingerprints)
                )
                .join(Artist)
                .join(Album, isouter=True)
                .filter(Track.title.ilike(f"%{title}%"))
            )
            if artist:
                query = query.filter(Artist.name.ilike(f"%{artist}%"))
            tracks = query.limit(limit).all()
            for t in tracks:
                results.append(EchosyncTrack(
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
        Returns a list of ``EchosyncTrack`` objects.
        """
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
                results.append(EchosyncTrack(
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

    def get_external_identifier_map(self, plugin_source: str, track_ids: List[int]) -> Dict[int, str]:
        if not track_ids:
            return {}

        with self.session_scope() as session:
            rows = (
                session.query(
                    LocalMedia.track_id,
                    ExternalIdentifier.plugin_item_id,
                )
                .select_from(ExternalIdentifier)
                .join(LocalMedia, ExternalIdentifier.media_id == LocalMedia.media_id)
                .filter(
                    LocalMedia.track_id.in_(track_ids),
                    ExternalIdentifier.plugin_source == plugin_source,
                )
                .all()
            )
            return {track_id: plugin_item_id for track_id, plugin_item_id in rows}

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

    def count_files(self) -> int:
        """Return total physical media files stored.

        Excludes ``virtual://`` placeholder paths and deduplicates by
        ``file_path`` (case-insensitively) so that the count matches the real
        number of files on disk.
        """
        from sqlalchemy import func as sqla_func
        with self.session_scope() as session:
            result = session.query(
                sqla_func.count(sqla_func.distinct(sqla_func.lower(LocalMedia.file_path)))
            ).filter(
                LocalMedia.file_path.isnot(None),
                LocalMedia.file_path != '',
                ~LocalMedia.file_path.startswith('virtual://'),
            ).scalar()
            return int(result or 0)

    def get_total_storage_used(self) -> int:
        """Return total size of all *unique* physical media files in bytes.

        Groups by ``file_path`` (case-insensitively) and takes the
        ``MAX(file_size_bytes)`` per path so that duplicate LocalMedia rows
        don't inflate the total. Virtual placeholder paths are excluded.
        """
        from sqlalchemy import func as sqla_func
        with self.session_scope() as session:
            # Sub-query: one row per distinct file_path with the best size
            subq = (
                session.query(
                    sqla_func.max(LocalMedia.file_size_bytes).label('best_size')
                )
                .filter(
                    LocalMedia.file_path.isnot(None),
                    LocalMedia.file_path != '',
                    ~LocalMedia.file_path.startswith('virtual://'),
                )
                .group_by(sqla_func.lower(LocalMedia.file_path))
                .subquery()
            )
            result = session.query(sqla_func.sum(subq.c.best_size)).scalar()
            return int(result or 0)

    def get_library_hierarchy(self) -> List[Dict]:
        """Fetch the entire library hierarchy (Artist -> Album -> Track)."""
        with self.session_scope() as session:
            # Use selectinload (separate SELECT per relationship) rather than joinedload
            # (which emits a single Cartesian-product JOIN). For large libraries the JOIN
            # inflates row count to artists×albums×tracks, causing an OOM spike.
            from datetime import date

            # Query only artists that have actual local media files attached to their tracks
            artists_query = (
                session.query(Artist)
                .options(
                    selectinload(Artist.albums)
                    .selectinload(Album.tracks)
                    .selectinload(Track.media_files)
                )
                .filter(Artist.albums.any(Album.tracks.any(Track.media_files.any())))
                .order_by(Artist.name)
            )

            hierarchy = []
            for artist in artists_query:
                artist_data = {
                    "id": artist.id,
                    "name": artist.name,
                    "image_url": artist.image_url,
                    "albums": []
                }

                # Sort albums by release date or title using safe date parser
                sorted_albums = sorted(artist.albums, key=lambda a: _safe_parse_date(a.release_date), reverse=True)

                for album in sorted_albums:
                    # Filter tracks that actually have local files attached to them
                    album_tracks = [t for t in album.tracks if t.media_files]
                    if not album_tracks:
                        continue

                    parsed_date = _safe_parse_date(album.release_date)
                    album_data = {
                        "id": album.id,
                        "title": album.title,
                        "cover_image_url": album.cover_image_url,
                        "year": parsed_date.year if parsed_date != date.min else None,
                        "tracks": []
                    }

                    # Sort tracks by disc number and track number safely
                    sorted_tracks = sorted(album_tracks, key=lambda t: (_safe_int(t.disc_number, 1), _safe_int(t.track_number, 0)))

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

    def clear_server_data(self, plugin_source: str):
        """Purge all tracks/albums/artists associated with a given plugin source.

        This is useful when re-syncing a media server from scratch. It deletes
        all tracks that have an ExternalIdentifier for the specified ``plugin_source``
        (e.g. "plex"), along with orphaned albums and artists.
        """
        with self.session_scope() as session:
            # delete tracks that reference this plugin
            track_ids = (
                session.query(Track.id)
                .join(ExternalIdentifier)
                .filter(ExternalIdentifier.plugin_source == plugin_source)
                .distinct()
                .all()
            )
            if track_ids:
                ids = [t[0] for t in track_ids]
                session.query(Track).filter(Track.id.in_(ids)).delete(synchronize_session=False)

            # remove identifiers themselves
            session.query(ExternalIdentifier).filter(
                ExternalIdentifier.plugin_source == plugin_source
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


music_session_registry = scoped_session(lambda: get_database().SessionLocal)


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
    "music_session_registry",
]
