#!/usr/bin/env python3

"""Operational state and provider sandbox database models and helper class."""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Table,
    create_engine,
    event,
    MetaData,
    ForeignKey,
    UniqueConstraint
)
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)


class WorkingBase(DeclarativeBase):
    """Base metadata class for WorkingDatabase SQLAlchemy models."""


class User(WorkingBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    plex_id: Mapped[Optional[str]] = mapped_column(String, unique=True)
    provider: Mapped[Optional[str]] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    track_states: Mapped[list["UserTrackState"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    artist_ratings: Mapped[list["UserArtistRating"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    album_ratings: Mapped[list["UserAlbumRating"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserRating(WorkingBase):
    __tablename__ = "user_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "sync_id", name="uq_user_sync_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    sync_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[float] = mapped_column(Float)  # 1-5, or system flags 0.1, 2.1, 3.1
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Wishlist(WorkingBase):
    __tablename__ = "wishlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_string: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class WatchlistArtist(WorkingBase):
    """Model for tracking watched artists and their scan status."""
    __tablename__ = "watchlist_artists"

    id: Mapped[int] = mapped_column(primary_key=True)
    spotify_artist_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    artist_name: Mapped[str] = mapped_column(String, nullable=False)
    last_scan_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime)
    image_url: Mapped[Optional[str]] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ReviewTask(WorkingBase):
    """Model for items in the Metadata Review Queue."""
    __tablename__ = "review_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)  # pending, approved, ignored
    detected_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Download(WorkingBase):
    """Model for tracking download state (Central Control)."""
    __tablename__ = "downloads"

    id: Mapped[int] = mapped_column(primary_key=True)
    sync_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    soul_sync_track: Mapped[dict] = mapped_column(JSON, nullable=False)  # Serialized SoulSyncTrack
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    provider_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class UserTrackState(WorkingBase):
    __tablename__ = "user_track_states"
    __table_args__ = (
        UniqueConstraint("user_id", "sync_id", name="uq_user_track_state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sync_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    is_unlinked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped[User] = relationship(back_populates="track_states")


class UserArtistRating(WorkingBase):
    __tablename__ = "user_artist_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "artist_urn", name="uq_user_artist_rating"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    artist_urn: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[float] = mapped_column(Float)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="artist_ratings")


class UserAlbumRating(WorkingBase):
    __tablename__ = "user_album_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "album_urn", name="uq_user_album_rating"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    album_urn: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[float] = mapped_column(Float)

    user: Mapped[User] = relationship(back_populates="album_ratings")


class ProviderStorageBox:
    """Sandbox wrapper for providers to create their own tables."""

    def __init__(self, provider_name: str, engine, metadata: MetaData):
        self.provider_name = provider_name
        self.engine = engine
        self.metadata = metadata

    def create_table(self, table_name_suffix: str, *columns_definition) -> Table:
        """
        Create a table with the enforced `prv_{provider_name}_` prefix.

        Args:
            table_name_suffix: The name of the table without the provider prefix.
            *columns_definition: SQLAlchemy Columns to define the schema.

        Returns:
            The SQLAlchemy Table object created.
        """
        table_name = f"prv_{self.provider_name}_{table_name_suffix}"

        # Check if table already exists in metadata to avoid re-creation errors
        if table_name in self.metadata.tables:
            return self.metadata.tables[table_name]

        table = Table(
            table_name,
            self.metadata,
            *columns_definition,
            extend_existing=True
        )
        return table

    def execute(self) -> None:
        """Execute the table creations."""
        self.metadata.create_all(self.engine)


def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    try:
        cursor.execute("PRAGMA busy_timeout=5000")
    except Exception:
        pass
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    cursor.close()


class WorkingDatabase:
    """Helper for creating the engine/session and managing the working schema."""

    def __init__(self, database_path: Optional[str] = None) -> None:
        data_dir = os.getenv("SOULSYNC_DATA_DIR")
        if database_path:
            resolved_path = Path(database_path)
        elif data_dir:
            resolved_path = Path(data_dir) / "working.db"
        else:
            resolved_path = Path("data") / "working.db"

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
        WorkingBase.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        WorkingBase.metadata.drop_all(self.engine)

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

    def get_system_user_id(self) -> int:
        """Get or create the system user ID for automated flags."""
        with self.session_scope() as session:
            user = session.query(User).filter(User.username == "SoulSync System").first()
            if user:
                return user.id

            # Create system user
            system_user = User(
                username="SoulSync System",
                plex_id="system_local_admin",
                provider="local"
            )
            session.add(system_user)
            session.commit()
            return system_user.id

    def get_provider_storage(self, provider_name: str) -> ProviderStorageBox:
        """Get a sandbox storage wrapper for a specific provider."""
        return ProviderStorageBox(provider_name, self.engine, WorkingBase.metadata)

    def dispose(self) -> None:
        self.engine.dispose()


_working_db_instance: Optional[WorkingDatabase] = None


def get_working_database(database_path: Optional[str] = None) -> WorkingDatabase:
    global _working_db_instance
    if _working_db_instance is None:
        _working_db_instance = WorkingDatabase(database_path)
        _working_db_instance.create_all()
    return _working_db_instance


def close_working_database() -> None:
    global _working_db_instance
    if _working_db_instance is not None:
        _working_db_instance.dispose()
        _working_db_instance = None


__all__ = [
    "WorkingBase",
    "User",
    "UserRating",
    "Wishlist",
    "WatchlistArtist",
    "ReviewTask",
    "Download",
    "UserTrackState",
    "UserArtistRating",
    "UserAlbumRating",
    "WorkingDatabase",
    "get_working_database",
    "close_working_database",
]
