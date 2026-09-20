#!/usr/bin/env python3

"""Track-centric SQLAlchemy database models and helper class."""

from __future__ import annotations

import os
import secrets
import string
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    event,
    or_,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    joinedload,
    mapped_column,
    relationship,
    scoped_session,
    selectinload,
    sessionmaker,
    validates,
)
from sqlalchemy.pool import NullPool

from time_utils import UTCDateTime


class ReleaseType(str, Enum):
    ALBUM = "album"
    SINGLE = "single"
    EP = "ep"
    COMPILATION = "compilation"
    STANDALONE = "standalone"


def generate_nanoid(size=8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(size))


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
    sort_name: Mapped[str | None] = mapped_column(String)
    musicbrainz_id: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    image_url: Mapped[str | None] = mapped_column(String)
    metadata_status: Mapped[dict | None] = mapped_column(JSON, default=dict, server_default="{}")
    parent_artist_id: Mapped[int | None] = mapped_column(
        ForeignKey("artists.id", ondelete="SET NULL"), nullable=True, index=True
    )

    albums: Mapped[list[Album]] = relationship(back_populates="artist", cascade="all, delete-orphan")
    tracks: Mapped[list[Track]] = relationship(back_populates="artist", cascade="all, delete-orphan")
    track_associations: Mapped[list[TrackArtist]] = relationship(back_populates="artist", cascade="all, delete-orphan")
    aliases: Mapped[list[ArtistAlias]] = relationship(back_populates="artist", cascade="all, delete-orphan")
    attributes: Mapped[list[ArtistAttribute]] = relationship(back_populates="artist", cascade="all, delete-orphan")
    parent_artist: Mapped[Artist | None] = relationship("Artist", remote_side=[id], back_populates="sub_artists")
    sub_artists: Mapped[list[Artist]] = relationship("Artist", back_populates="parent_artist")

    @validates("name")
    def validate_name(self, key, value):
        if value:
            import re

            from core.matching_engine.text_utils import normalize_artist

            clean_name = re.sub(r"\s+", " ", str(value)).strip()
            self.normalized_name = normalize_artist(clean_name)
            return clean_name
        return value


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    normalized_title: Mapped[str] = mapped_column(String, index=True, server_default="")
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), nullable=False)
    release_date: Mapped[date | None] = mapped_column(Date)
    cover_image_url: Mapped[str | None] = mapped_column(String)
    release_group_id: Mapped[str | None] = mapped_column(String)
    mb_release_id: Mapped[str | None] = mapped_column(String)
    original_release_date: Mapped[date | None] = mapped_column(Date)
    album_type: Mapped[str | None] = mapped_column(String)

    artist: Mapped[Artist] = relationship(back_populates="albums")
    tracks: Mapped[list[Track]] = relationship(back_populates="album", cascade="all, delete-orphan")
    attributes: Mapped[list[AlbumAttribute]] = relationship(back_populates="album", cascade="all, delete-orphan")

    @validates("title")
    def validate_title(self, key, value):
        if value:
            import re

            from core.matching_engine.text_utils import normalize_title

            clean_title = re.sub(r"\s+", " ", str(value)).strip()
            self.normalized_title = normalize_title(clean_title)
            return clean_title
        return value


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    normalized_title: Mapped[str] = mapped_column(String, index=True, server_default="")
    sort_title: Mapped[str | None] = mapped_column(String)
    edition: Mapped[str | None] = mapped_column(String)  # remaster, live, remix, deluxe, acoustic, etc.
    album_id: Mapped[int | None] = mapped_column(ForeignKey("albums.id", ondelete="CASCADE"))
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), nullable=False)

    duration: Mapped[int | None] = mapped_column()  # milliseconds
    track_number: Mapped[int | None] = mapped_column()
    disc_number: Mapped[int | None] = mapped_column()
    added_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    musicbrainz_id: Mapped[str | None] = mapped_column(String, index=True)
    isrc: Mapped[str | None] = mapped_column(String)
    sync_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False, default=generate_nanoid)
    release_type: Mapped[str | None] = mapped_column(String, index=True, default="album", server_default="album")
    global_rating: Mapped[float | None] = mapped_column(Float)
    metadata_status: Mapped[dict | None] = mapped_column(JSON, default=dict, server_default="{}")

    @hybrid_property
    def enhanced(self) -> bool:
        if self.metadata_status and isinstance(self.metadata_status, dict):
            return bool(self.metadata_status.get("enhanced"))
        return False

    @enhanced.setter
    def enhanced(self, value: bool) -> None:
        if not self.metadata_status or not isinstance(self.metadata_status, dict):
            self.metadata_status = {}
        self.metadata_status["enhanced"] = bool(value)
        try:
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(self, "metadata_status")
        except Exception:
            pass

    @enhanced.expression
    def enhanced(cls):
        from sqlalchemy import func, or_

        return or_(
            func.json_extract(cls.metadata_status, "$.enhanced") == True,
            func.json_extract(cls.metadata_status, "$.enhanced") == "true",
            func.json_extract(cls.metadata_status, "$.enhanced") == 1,
        )

    @hybrid_property
    def metadata_enhanced(self) -> bool:
        return self.enhanced

    @metadata_enhanced.setter
    def metadata_enhanced(self, value: bool) -> None:
        self.enhanced = value

    @metadata_enhanced.expression
    def metadata_enhanced(cls):
        return cls.enhanced

    @hybrid_property
    def musicbrainz_track_id(self) -> str | None:
        return self.musicbrainz_id

    @musicbrainz_track_id.setter
    def musicbrainz_track_id(self, value: str | None) -> None:
        self.musicbrainz_id = value

    @musicbrainz_track_id.expression
    def musicbrainz_track_id(cls):
        return cls.musicbrainz_id

    @hybrid_property
    def echosync_signature(self) -> str | None:
        if self.metadata_status and isinstance(self.metadata_status, dict):
            return self.metadata_status.get("echosync_signature")
        return None

    @echosync_signature.setter
    def echosync_signature(self, value: str | None) -> None:
        if not self.metadata_status or not isinstance(self.metadata_status, dict):
            self.metadata_status = {}
        if value is None:
            self.metadata_status.pop("echosync_signature", None)
        else:
            self.metadata_status["echosync_signature"] = str(value)
        try:
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(self, "metadata_status")
        except Exception:
            pass

    @echosync_signature.expression
    def echosync_signature(cls):
        from sqlalchemy import func

        return func.json_extract(cls.metadata_status, "$.echosync_signature")

    @property
    def is_verified(self) -> bool:
        if self.metadata_status and isinstance(self.metadata_status, dict):
            if "is_verified" in self.metadata_status:
                return bool(self.metadata_status["is_verified"])
            if "verified" in self.metadata_status:
                return bool(self.metadata_status["verified"])
        return bool(self.musicbrainz_id or (self.artist_id and self.album_id))

    __table_args__ = (UniqueConstraint("sync_id", name="uq_tracks_sync_id"),)

    album: Mapped[Album | None] = relationship(back_populates="tracks")
    artist: Mapped[Artist] = relationship(back_populates="tracks")
    artist_associations: Mapped[list[TrackArtist]] = relationship(
        "TrackArtist",
        back_populates="track",
        cascade="all, delete-orphan",
        order_by="TrackArtist.position",
    )
    all_artists: Mapped[list[Artist]] = relationship(
        "Artist",
        secondary="track_artists",
        order_by="TrackArtist.position",
        viewonly=True,
    )
    aliases: Mapped[list[TrackAlias]] = relationship(back_populates="track", cascade="all, delete-orphan")
    attributes: Mapped[list[TrackAttribute]] = relationship(back_populates="track", cascade="all, delete-orphan")
    media_files: Mapped[list[LocalMedia]] = relationship(
        "LocalMedia",
        back_populates="track",
        cascade="all, delete-orphan",
        order_by="desc(LocalMedia.bitrate), desc(LocalMedia.sample_rate), desc(LocalMedia.bit_depth)",
    )
    external_identifiers: Mapped[list[ExternalIdentifier]] = relationship(
        "ExternalIdentifier",
        secondary="local_media",
        primaryjoin="Track.id == LocalMedia.track_id",
        secondaryjoin="LocalMedia.media_id == ExternalIdentifier.media_id",
        viewonly=True,
    )

    @property
    def year(self) -> int | None:
        if self.album and self.album.release_date:
            try:
                return int(str(self.album.release_date)[:4])
            except Exception:
                pass
        return None

    @property
    def file_format(self) -> str | None:
        return self.local_media[0].file_format if self.local_media else None

    @property
    def bitrate(self) -> int | None:
        return self.local_media[0].bitrate if self.local_media else None

    @property
    def sample_rate(self) -> int | None:
        return self.local_media[0].sample_rate if self.local_media else None

    @property
    def bit_depth(self) -> int | None:
        return self.local_media[0].bit_depth if self.local_media else None

    @property
    def channels(self) -> int | None:
        return self.local_media[0].channels if self.local_media else None

    @property
    def file_size_bytes(self) -> int | None:
        return self.local_media[0].file_size_bytes if self.local_media else None

    def get_best_media(self) -> LocalMedia | None:
        """Return the highest-quality LocalMedia file attached to this track."""
        if not self.media_files:
            return None
        _LOSSLESS = {"flac", "alac", "wav", "dsd", "dsf", "dff", "ape"}

        def _quality_key(m: LocalMedia):
            fmt = (m.file_format or "").lower()
            is_lossless = 1 if fmt in _LOSSLESS else 0
            return (is_lossless, m.bitrate or 0, m.sample_rate or 0, m.bit_depth or 0)

        return max(self.media_files, key=_quality_key)

    @property
    def local_media(self) -> list[LocalMedia]:
        """Return attached LocalMedia files ordered deterministically by quality (bitrate DESC, sample_rate DESC, bit_depth DESC)."""
        return sorted(
            self.media_files or [],
            key=lambda m: (
                m.bitrate or 0,
                m.sample_rate or 0,
                m.bit_depth or 0,
            ),
            reverse=True,
        )

    @property
    def media(self) -> list[LocalMedia]:
        """Backwards-compatible accessor. Returns quality-ordered media files."""
        return self.local_media

    @property
    def satisfied_plugins(self) -> list[str]:
        """List of plugin identifiers whose enhancement has been satisfied for this track."""
        if self.metadata_status and isinstance(self.metadata_status, dict):
            return list(self.metadata_status.get("satisfied_plugins", []))
        return []

    def is_plugin_satisfied(self, plugin_key: str) -> bool:
        """Check if a given plugin has run and been recorded as satisfied."""
        return plugin_key in self.satisfied_plugins

    def mark_plugin_satisfied(self, plugin_key: str) -> None:
        """Record a plugin key as satisfied in metadata_status."""
        if not self.metadata_status or not isinstance(self.metadata_status, dict):
            self.metadata_status = {}
        satisfied = set(self.metadata_status.get("satisfied_plugins", []))
        satisfied.add(plugin_key)
        self.metadata_status["satisfied_plugins"] = sorted(satisfied)
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(self, "metadata_status")

    @property
    def file_path(self) -> str | None:
        """Backwards-compatible accessor. Returns best media's file_path."""
        best = self.get_best_media()
        return best.file_path if best else None

    @property
    def artist_name(self) -> str | None:
        return self.artist.name if self.artist else None

    @property
    def album_title(self) -> str | None:
        return self.album.title if self.album else None

    @property
    def media_ids(self) -> list[str]:
        return [m.media_id for m in self.media_files if m.media_id]

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
        return round(self.global_rating)

    @validates("title")
    def validate_title(self, key, value):
        if value:
            import re

            from core.matching_engine.text_utils import normalize_title

            clean_title = re.sub(r"\s+", " ", str(value)).strip()
            self.normalized_title = normalize_title(clean_title)
            return clean_title
        return value


class TrackArtist(Base):
    """Junction table capturing all collaborating artists for a track with roles and position."""

    __tablename__ = "track_artists"
    __table_args__ = (UniqueConstraint("track_id", "artist_id", "role", name="uq_track_artist_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, default="primary", nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    track: Mapped[Track] = relationship(back_populates="artist_associations")
    artist: Mapped[Artist] = relationship(back_populates="track_associations")


class LocalMedia(Base):
    __tablename__ = "local_media"

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[str] = mapped_column(String(8), unique=True, index=True, nullable=False, default=generate_nanoid)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    file_format: Mapped[str | None] = mapped_column(String)
    bitrate: Mapped[int | None] = mapped_column(Integer)
    sample_rate: Mapped[int | None] = mapped_column(Integer)
    bit_depth: Mapped[int | None] = mapped_column(Integer)
    channels: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    inode: Mapped[int | None] = mapped_column(BigInteger, index=True)
    mtime: Mapped[float | None] = mapped_column(Float)
    added_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    track: Mapped[Track] = relationship(back_populates="media_files")
    audio_fingerprints: Mapped[list[AudioFingerprint]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )
    external_identifiers: Mapped[list[ExternalIdentifier]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )


class ExternalIdentifier(Base):
    __tablename__ = "external_identifiers"
    __table_args__ = (UniqueConstraint("plugin_source", "plugin_item_id", name="uq_plugin_item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[str] = mapped_column(
        ForeignKey("local_media.media_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plugin_source: Mapped[str] = mapped_column(String, nullable=False, index=True)
    plugin_item_id: Mapped[str] = mapped_column(String, nullable=False)
    raw_data: Mapped[dict | None] = mapped_column(JSON)

    media: Mapped[LocalMedia] = relationship(back_populates="external_identifiers")


class AudioFingerprint(Base):
    __tablename__ = "audio_fingerprints"
    __table_args__ = (UniqueConstraint("media_id", name="uq_audio_fingerprints_media_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[str] = mapped_column(
        ForeignKey("local_media.media_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # chromaprint: raw locally-generated Chromaprint string (AcoustID algorithm output).
    # acoustid_id: the AcoustID service's confirmed UUID for this recording (returned after lookup).
    # These are deliberately separate — chromaprint is our local computation; acoustid_id is
    # the external service's canonical identifier.
    chromaprint: Mapped[str] = mapped_column(String, index=True, nullable=False)
    acoustid_id: Mapped[str | None] = mapped_column(String)

    media: Mapped[LocalMedia] = relationship(back_populates="audio_fingerprints")


class TrackAlias(Base):
    """Localised / transliterated names for a track (e.g. Romaji, Pinyin)."""

    __tablename__ = "track_aliases"
    __table_args__ = (UniqueConstraint("track_id", "locale", "script", "name", name="uq_track_alias"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    plugin_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    locale: Mapped[str | None] = mapped_column(String)  # e.g. 'en', 'zh', 'ja'
    script: Mapped[str | None] = mapped_column(String)  # e.g. 'Latn', 'Hant', 'Hans', 'Hrkt'
    alias_type: Mapped[str | None] = mapped_column(String(30))
    is_primary_for_locale: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    track: Mapped[Track] = relationship(back_populates="aliases")


class ArtistAlias(Base):
    """Localised / transliterated names for an artist."""

    __tablename__ = "artist_aliases"
    __table_args__ = (UniqueConstraint("artist_id", "locale", "script", "name", name="uq_artist_alias"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True)
    plugin_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    locale: Mapped[str | None] = mapped_column(String)
    script: Mapped[str | None] = mapped_column(String)
    alias_type: Mapped[str | None] = mapped_column(String(30))
    is_primary_for_locale: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    artist: Mapped[Artist] = relationship(back_populates="aliases")

    @property
    def language(self) -> str | None:
        return self.locale

    @language.setter
    def language(self, val: str | None) -> None:
        self.locale = val

    @property
    def alias_name(self) -> str:
        return self.name

    @alias_name.setter
    def alias_name(self, val: str) -> None:
        self.name = val


class TrackAttribute(Base):
    """Namespaced Key-Value store for plugin metadata attached to a Track."""

    __tablename__ = "track_attributes"
    __table_args__ = (
        UniqueConstraint("track_id", "plugin_id", "key", name="uq_track_attr_key"),
        Index("ix_track_attr_lookup", "track_id", "plugin_id", "key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    plugin_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON, nullable=True)

    track: Mapped[Track] = relationship(back_populates="attributes")


class ArtistAttribute(Base):
    """Namespaced Key-Value store for plugin metadata attached to an Artist."""

    __tablename__ = "artist_attributes"
    __table_args__ = (
        UniqueConstraint("artist_id", "plugin_id", "key", name="uq_artist_attr_key"),
        Index("ix_artist_attr_lookup", "artist_id", "plugin_id", "key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True)
    plugin_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON, nullable=True)

    artist: Mapped[Artist] = relationship(back_populates="attributes")


class AlbumAttribute(Base):
    """Namespaced Key-Value store for plugin metadata attached to an Album."""

    __tablename__ = "album_attributes"
    __table_args__ = (
        UniqueConstraint("album_id", "plugin_id", "key", name="uq_album_attr_key"),
        Index("ix_album_attr_lookup", "album_id", "plugin_id", "key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    album_id: Mapped[int] = mapped_column(ForeignKey("albums.id", ondelete="CASCADE"), nullable=False, index=True)
    plugin_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON, nullable=True)

    album: Mapped[Album] = relationship(back_populates="attributes")


class TrackAudioFeatures(Base):
    __tablename__ = "track_audio_features"

    sync_id: Mapped[str] = mapped_column(String, primary_key=True)
    tempo: Mapped[float | None] = mapped_column(Float)
    energy: Mapped[float | None] = mapped_column(Float)
    valence: Mapped[float | None] = mapped_column(Float)
    danceability: Mapped[float | None] = mapped_column(Float)
    acousticness: Mapped[float | None] = mapped_column(Float)


def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    # ensure foreign keys are enforced
    cursor.execute("PRAGMA foreign_keys=ON")
    # allocate ~8MB cache
    try:
        cursor.execute("PRAGMA cache_size=-8000")
    except Exception:
        pass
    # give other connections a bit longer before raising "database is locked" (MUST be before WAL)
    try:
        cursor.execute("PRAGMA busy_timeout=30000")
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


def _ensure_alias_and_attribute_schema(engine) -> None:
    """Ensure track_aliases, artist_aliases, and attribute tables exist with correct schema idempotently."""
    try:
        with engine.connect() as conn:
            # 1. artist_aliases columns
            try:
                cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(artist_aliases);").fetchall()]
                if cols:
                    if "alias_type" not in cols:
                        conn.exec_driver_sql(
                            "ALTER TABLE artist_aliases ADD COLUMN alias_type VARCHAR(50) DEFAULT 'default';"
                        )
                    if "plugin_id" not in cols:
                        conn.exec_driver_sql("ALTER TABLE artist_aliases ADD COLUMN plugin_id INTEGER;")
                    conn.commit()
            except Exception:
                pass

            # 2. track_aliases table & columns
            try:
                conn.exec_driver_sql("""
                    CREATE TABLE IF NOT EXISTS track_aliases (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        track_id INTEGER NOT NULL,
                        plugin_id INTEGER,
                        name VARCHAR NOT NULL,
                        locale VARCHAR,
                        script VARCHAR,
                        alias_type VARCHAR(30),
                        is_primary_for_locale BOOLEAN DEFAULT 0,
                        CONSTRAINT uq_track_alias UNIQUE (track_id, locale, script, name),
                        FOREIGN KEY(track_id) REFERENCES tracks (id) ON DELETE CASCADE
                    );
                """)
                conn.commit()
                cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(track_aliases);").fetchall()]
                if "plugin_id" not in cols:
                    conn.exec_driver_sql("ALTER TABLE track_aliases ADD COLUMN plugin_id INTEGER;")
                if "alias_type" not in cols:
                    conn.exec_driver_sql("ALTER TABLE track_aliases ADD COLUMN alias_type VARCHAR(30);")
                conn.commit()
            except Exception:
                pass

            # 3. track_attributes table
            try:
                conn.exec_driver_sql("""
                    CREATE TABLE IF NOT EXISTS track_attributes (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        track_id INTEGER NOT NULL,
                        plugin_id INTEGER NOT NULL,
                        key VARCHAR(100) NOT NULL,
                        value JSON,
                        CONSTRAINT uq_track_attr_key UNIQUE (track_id, plugin_id, key),
                        FOREIGN KEY(track_id) REFERENCES tracks (id) ON DELETE CASCADE
                    );
                """)
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_track_attributes_track_id ON track_attributes (track_id);"
                )
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_track_attributes_plugin_id ON track_attributes (plugin_id);"
                )
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_track_attr_lookup ON track_attributes (track_id, plugin_id, key);"
                )
                conn.commit()
            except Exception:
                pass

            # 4. artist_attributes table
            try:
                conn.exec_driver_sql("""
                    CREATE TABLE IF NOT EXISTS artist_attributes (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        artist_id INTEGER NOT NULL,
                        plugin_id INTEGER NOT NULL,
                        key VARCHAR(100) NOT NULL,
                        value JSON,
                        CONSTRAINT uq_artist_attr_key UNIQUE (artist_id, plugin_id, key),
                        FOREIGN KEY(artist_id) REFERENCES artists (id) ON DELETE CASCADE
                    );
                """)
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_artist_attributes_artist_id ON artist_attributes (artist_id);"
                )
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_artist_attributes_plugin_id ON artist_attributes (plugin_id);"
                )
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_artist_attr_lookup ON artist_attributes (artist_id, plugin_id, key);"
                )
                conn.commit()
            except Exception:
                pass

            # 5. album_attributes table
            try:
                conn.exec_driver_sql("""
                    CREATE TABLE IF NOT EXISTS album_attributes (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        album_id INTEGER NOT NULL,
                        plugin_id INTEGER NOT NULL,
                        key VARCHAR(100) NOT NULL,
                        value JSON,
                        CONSTRAINT uq_album_attr_key UNIQUE (album_id, plugin_id, key),
                        FOREIGN KEY(album_id) REFERENCES albums (id) ON DELETE CASCADE
                    );
                """)
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_album_attributes_album_id ON album_attributes (album_id);"
                )
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_album_attributes_plugin_id ON album_attributes (plugin_id);"
                )
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_album_attr_lookup ON album_attributes (album_id, plugin_id, key);"
                )
                conn.commit()
            except Exception:
                pass
    except Exception:
        pass


class MusicDatabase:
    """Helper for creating the engine/session and managing the schema."""

    def __init__(self, database_path: str | None = None) -> None:
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

        connect_args = {"timeout": 30.0, "check_same_thread": False} if engine_url.startswith("sqlite") else {}

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
        _ensure_alias_and_attribute_schema(self.engine)
        self._sanitize_existing_metadata()

    def _sanitize_existing_metadata(self) -> None:
        """Startup repair: collapse double spaces in title/artist/album and backfill missing edition markers."""
        try:
            with self.session_scope() as session:
                import re

                from core.matching_engine.text_utils import (
                    normalize_title,
                )

                # Fix double spaces in tracks
                double_space_tracks = (
                    session.query(Track)
                    .filter((Track.title.like("%  %")) | (Track.normalized_title.like("%  %")))
                    .all()
                )
                for t in double_space_tracks:
                    if t.title:
                        t.title = re.sub(r"\s+", " ", t.title).strip()
                        t.normalized_title = normalize_title(t.title)
                        if t.sort_title:
                            t.sort_title = re.sub(r"\s+", " ", t.sort_title).strip()

                # Backfill edition for tracks where edition is NULL but media filename indicates Remix/Edit/Live
                null_ed_tracks = (
                    session.query(Track)
                    .join(LocalMedia)
                    .filter(
                        Track.edition.is_(None),
                        (
                            LocalMedia.file_path.ilike("%remix%")
                            | LocalMedia.file_path.ilike("%acoustic%")
                            | LocalMedia.file_path.ilike("%live%")
                        ),
                    )
                    .all()
                )
                for t in null_ed_tracks:
                    for m in t.media_files:
                        if m.file_path:
                            m_ed = re.search(
                                r"[\(\[]([^\]\)]*(?:remix|mix|edit|version|live|acoustic|instrumental|remaster)[^\]\)]*)[\)\]]",
                                m.file_path,
                                re.IGNORECASE,
                            )
                            if m_ed:
                                t.edition = m_ed.group(1).strip()
                                break
        except Exception:
            pass

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
            from core.task_manager import db_write_lease

            with db_write_lease(task_name="music_database_session"):
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def search_library(self, query: str) -> dict[str, list[dict]]:
        """Search across Artists, Albums, and Tracks."""
        results = {"artists": [], "albums": [], "tracks": []}

        if not query:
            return results

        search_term = f"%{query}%"

        with self.session_scope() as session:
            # OPTIMIZATION: joinedload eliminates N+1 lazy loading queries

            # Search Artists
            artists = (
                session.query(Artist)
                .filter((Artist.name.ilike(search_term)) | (Artist.aliases.any(ArtistAlias.name.ilike(search_term))))
                .limit(20)
                .all()
            )
            for artist in artists:
                results["artists"].append(
                    {
                        "id": artist.id,
                        "name": artist.name,
                        "image_url": artist.image_url,
                    }
                )

            # Search Albums
            albums = (
                session.query(Album)
                .options(joinedload(Album.artist))
                .join(Artist)
                .filter(
                    (Album.title.ilike(search_term))
                    | (Artist.name.ilike(search_term))
                    | (Artist.aliases.any(ArtistAlias.name.ilike(search_term)))
                )
                .limit(20)
                .all()
            )
            for album in albums:
                results["albums"].append(
                    {
                        "id": album.id,
                        "title": album.title,
                        "artist_id": album.artist_id,
                        "artist_name": album.artist.name,
                        "cover_image_url": album.cover_image_url,
                        "year": album.release_date.year if album.release_date else None,
                    }
                )

            # Search Tracks
            tracks = (
                session.query(Track)
                .options(joinedload(Track.artist), joinedload(Track.album))
                .join(Artist)
                .join(Album, isouter=True)
                .filter(
                    (Track.title.ilike(search_term))
                    | (Track.aliases.any(TrackAlias.name.ilike(search_term)))
                    | (Artist.name.ilike(search_term))
                    | (Artist.aliases.any(ArtistAlias.name.ilike(search_term)))
                    | (Album.title.ilike(search_term))
                )
                .limit(50)
                .all()
            )

            for track in tracks:
                results["tracks"].append(
                    {
                        "id": track.id,
                        "title": track.title,
                        "artist_id": track.artist_id,
                        "artist_name": track.artist.name,
                        "album_id": track.album_id,
                        "album_title": track.album.title if track.album else "Unknown Album",
                        "duration": track.duration,
                    }
                )

        return results

    def search_canonical_fuzzy(self, title: str, artist: str | None = None, limit: int = 10) -> list:
        """Fuzzy search canonical tracks by title and optional artist substring.

        Returns a list of ``EchosyncTrack`` objects (each has a ``to_dict()`` method).
        """
        results = []
        with self.session_scope() as session:
            # OPTIMIZATION: joinedload and selectinload eliminate N+1 queries during mapping

            title_filter = or_(
                Track.title.ilike(f"%{title}%"),
                Track.aliases.any(TrackAlias.name.ilike(f"%{title}%")),
            )
            query = (
                session.query(Track)
                .options(
                    joinedload(Track.artist),
                    joinedload(Track.album),
                    selectinload(Track.audio_fingerprints),
                )
                .join(Artist)
                .join(Album, isouter=True)
                .filter(title_filter)
            )
            if artist:
                artist_filter = or_(
                    Artist.name.ilike(f"%{artist}%"),
                    Artist.aliases.any(ArtistAlias.name.ilike(f"%{artist}%")),
                )
                query = query.filter(artist_filter)
            tracks = query.limit(limit).all()
            for t in tracks:
                from core.db.echo_sync_track import EchosyncTrack

                results.append(
                    EchosyncTrack(
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
                        acoustid_id=next(
                            (fp.acoustid_id for fp in t.audio_fingerprints if fp.acoustid_id),
                            None,
                        ),
                    )
                )
        return results

    def search_canonical_by_ids(
        self,
        isrc: str | None = None,
        musicbrainz_recording_id: str | None = None,
        acoustid: str | None = None,
    ) -> list:
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
            filters.append(Track.audio_fingerprints.any(AudioFingerprint.acoustid_id == acoustid))
        if not filters:
            return results
        with self.session_scope() as session:
            tracks = session.query(Track).join(Artist).join(Album, isouter=True).filter(or_(*filters)).all()
            for t in tracks:
                from core.db.echo_sync_track import EchosyncTrack

                results.append(
                    EchosyncTrack(
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
                        acoustid_id=next(
                            (fp.acoustid_id for fp in t.audio_fingerprints if fp.acoustid_id),
                            None,
                        ),
                    )
                )
        return results

    def get_external_identifier_map(self, plugin_source: str, track_ids: list[int]) -> dict[int, str]:
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

    def count_lossless_files(self) -> int:
        """Return total lossless physical media files stored."""
        with self.session_scope() as session:
            return (
                session.query(LocalMedia)
                .filter(LocalMedia.file_format.in_({"flac", "alac", "wav", "dsd", "dsf", "dff", "ape"}))
                .count()
            )

    def count_files(self) -> int:
        """Return total physical media files stored.

        Deduplicates by
        ``file_path`` (case-insensitively) so that the count matches the real
        number of files on disk. Virtual placeholder paths are excluded.
        """
        from sqlalchemy import func as sqla_func

        with self.session_scope() as session:
            result = (
                session.query(sqla_func.count(sqla_func.distinct(sqla_func.lower(LocalMedia.file_path))))
                .filter(
                    LocalMedia.file_path.isnot(None),
                    LocalMedia.file_path != "",
                    ~LocalMedia.file_path.like("virtual://%"),
                )
                .scalar()
            )
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
                session.query(sqla_func.max(LocalMedia.file_size_bytes).label("best_size"))
                .filter(
                    LocalMedia.file_path.isnot(None),
                    LocalMedia.file_path != "",
                    ~LocalMedia.file_path.like("virtual://%"),
                )
                .group_by(sqla_func.lower(LocalMedia.file_path))
                .subquery()
            )
            result = session.query(sqla_func.sum(subq.c.best_size)).scalar()
            return int(result or 0)

    def get_library_hierarchy(self) -> list[dict]:
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
                    selectinload(Artist.albums).selectinload(Album.tracks).selectinload(Track.media_files),
                    selectinload(Artist.tracks).selectinload(Track.media_files),
                )
                .filter(Artist.tracks.any(Track.media_files.any()))
                .order_by(Artist.name)
            )

            hierarchy = []
            for artist in artists_query:
                artist_data = {
                    "id": artist.id,
                    "name": artist.name,
                    "image_url": artist.image_url,
                    "albums": [],
                }

                # Sort albums by release date or title using safe date parser
                sorted_albums = sorted(
                    artist.albums,
                    key=lambda a: _safe_parse_date(a.release_date),
                    reverse=True,
                )

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
                        "tracks": [],
                    }

                    # Sort tracks by disc number and track number safely
                    sorted_tracks = sorted(
                        album_tracks,
                        key=lambda t: (
                            _safe_int(t.disc_number, 1),
                            _safe_int(t.track_number, 0),
                        ),
                    )

                    for track in sorted_tracks:
                        album_data["tracks"].append(
                            {
                                "id": track.id,
                                "sync_id": track.sync_id,
                                "title": track.title,
                                "duration": track.duration,
                                "track_number": track.track_number,
                                "disc_number": track.disc_number,
                                "media_ids": [m.media_id for m in track.media_files if getattr(m, "media_id", None)],
                            }
                        )

                    artist_data["albums"].append(album_data)

                # Handle loose tracks without an album
                loose_tracks = [t for t in artist.tracks if t.album_id is None and t.media_files]
                if loose_tracks:
                    album_data = {
                        "id": "unknown_" + str(artist.id),
                        "title": "Unknown Album",
                        "cover_image_url": None,
                        "year": None,
                        "tracks": [],
                    }
                    sorted_tracks = sorted(
                        loose_tracks,
                        key=lambda t: (
                            _safe_int(t.disc_number, 1),
                            _safe_int(t.track_number, 0),
                        ),
                    )
                    for track in sorted_tracks:
                        album_data["tracks"].append(
                            {
                                "id": track.id,
                                "title": track.title,
                                "duration": track.duration,
                                "track_number": track.track_number,
                                "disc_number": track.disc_number,
                            }
                        )
                    artist_data["albums"].append(album_data)

                hierarchy.append(artist_data)

            return hierarchy

    def get_track_path(self, track_id: int | str) -> str | None:
        """Fetch the local file path for a track ID (integer, numeric string, sync_id, or media_id)."""
        with self.session_scope() as session:
            if isinstance(track_id, int) or (isinstance(track_id, str) and track_id.isdigit()):
                tid = int(track_id)
                track = session.query(Track).filter(Track.id == tid).first()
                if track and track.file_path:
                    return track.file_path

            track = session.query(Track).filter(Track.sync_id == str(track_id)).first()
            if track and track.file_path:
                return track.file_path

            lm = session.query(LocalMedia).filter(LocalMedia.media_id == str(track_id)).first()
            if lm and lm.file_path:
                return lm.file_path

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
            session.query(ExternalIdentifier).filter(ExternalIdentifier.plugin_source == plugin_source).delete(
                synchronize_session=False
            )

            # clean up albums with no remaining tracks
            session.query(Album).filter(~Album.tracks.any()).delete(synchronize_session=False)

            # clean up artists with no remaining tracks
            session.query(Artist).filter(~Artist.tracks.any()).delete(synchronize_session=False)

    def get_session(self) -> Session:
        """Return a new SQLAlchemy Session instance."""
        return self.SessionLocal()

    def dispose(self) -> None:
        self.engine.dispose()


_db_instance: MusicDatabase | None = None


def get_database(database_path: str | None = None) -> MusicDatabase:
    global _db_instance
    if _db_instance is None:
        _db_instance = MusicDatabase(database_path)
    return _db_instance


def close_database() -> None:
    global _db_instance
    if _db_instance is not None:
        _db_instance.dispose()
        _db_instance = None


def _ensure_artist_alias_schema(engine) -> None:
    """Ensure the artist_aliases table contains the alias_type column."""
    with engine.connect() as conn:
        tables = [
            row[0] for row in conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        if "artist_aliases" in tables:
            cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(artist_aliases);").fetchall()]
            if "alias_type" not in cols:
                conn.exec_driver_sql("ALTER TABLE artist_aliases ADD COLUMN alias_type VARCHAR;")
                conn.commit()


def init_music_db(engine=None) -> None:
    """Initialize or migrate the music database schema."""
    if engine is None:
        db = get_database()
        engine = db.engine
    Base.metadata.create_all(engine)
    _ensure_artist_alias_schema(engine)


music_session_registry = scoped_session(lambda: get_database().SessionLocal)


__all__ = [
    "Album",
    "Artist",
    "ArtistAlias",
    "AudioFingerprint",
    "Base",
    "ExternalIdentifier",
    "MusicDatabase",
    "Track",
    "TrackAlias",
    "TrackArtist",
    "TrackArtistAlias",
    "TrackAudioFeatures",
    "_ensure_artist_alias_schema",
    "close_database",
    "get_database",
    "init_music_db",
    "music_session_registry",
]
