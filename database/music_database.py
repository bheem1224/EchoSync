#!/usr/bin/env python3

"""Track-centric SQLAlchemy database models and helper class."""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import Generator, List, Optional, Tuple

from sqlalchemy import (
    BigInteger,
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

    albums: Mapped[List["Album"]] = relationship(
        back_populates="artist", cascade="all, delete-orphan"
    )
    tracks: Mapped[List["Track"]] = relationship(
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
    added_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    musicbrainz_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    global_rating: Mapped[Optional[float]] = mapped_column(Float)

    album: Mapped[Optional[Album]] = relationship(back_populates="tracks")
    artist: Mapped[Artist] = relationship(back_populates="tracks")
    external_identifiers: Mapped[List["ExternalIdentifier"]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )
    user_ratings: Mapped[List["UserRating"]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )
    audio_fingerprints: Mapped[List["AudioFingerprint"]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )

    @hybrid_property
    def get_consensus_rating(self) -> int:
        if not self.user_ratings:
            return 0
        return max((rating.rating or 0) for rating in self.user_ratings)


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


class UserRating(Base):
    __tablename__ = "user_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "track_id", name="uq_user_track"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column()  # 1-5
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    track: Mapped[Track] = relationship(back_populates="user_ratings")


class AudioFingerprint(Base):
    __tablename__ = "audio_fingerprints"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fingerprint_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    track: Mapped[Track] = relationship(back_populates="audio_fingerprints")


class Wishlist(Base):
    __tablename__ = "wishlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_string: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
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
            connect_args={"check_same_thread": False},
        )
        event.listen(self.engine, "connect", _sqlite_pragmas)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

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

    def dispose(self) -> None:
        self.engine.dispose()


_db_instance: Optional[MusicDatabase] = None


def get_database(database_path: Optional[str] = None) -> MusicDatabase:
    global _db_instance
    if _db_instance is None:
        _db_instance = MusicDatabase(database_path)
        _db_instance.create_all()
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
    "UserRating",
    "AudioFingerprint",
    "Wishlist",
    "MusicDatabase",
    "get_database",
    "close_database",
]
