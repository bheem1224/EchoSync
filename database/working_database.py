#!/usr/bin/env python3

"""Operational state and provider sandbox database models and helper class."""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from time_utils import UTCDateTime, utc_now

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
    validates,
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
    scoped_session,
)


# ---------------------------------------------------------------------------
# Intent type constants (Task 2 – Intent Engine)
# ---------------------------------------------------------------------------
INTENT_TYPES = (
    "USER_UPGRADE_REQUEST",      # User explicitly requested an upgrade
    "USER_DELETE_REQUEST",       # User rated 1-2 stars → delete request
    "SYSTEM_UPGRADE_SUGGESTION", # Heuristic: consensus engine upgrade proposal
    "SYSTEM_DELETE_SUGGESTION",  # Heuristic: consensus engine delete proposal
    "HYGIENE_DUPLICATION",       # Deterministic: duplicate track detected
    "HYGIENE_QUALITY_UPGRADE",   # Deterministic: lower-quality copy exists
)


class WorkingBase(DeclarativeBase):
    """Base metadata class for WorkingDatabase SQLAlchemy models."""


# Phase 2: The Unified Identity Merge
class Account(WorkingBase):
    __tablename__ = "accounts"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plugin_id: Mapped[int] = mapped_column(Integer, index=True)
    remote_account_id: Mapped[str] = mapped_column(String(255), index=True)
    username: Mapped[Optional[str]] = mapped_column(String)
    
    __table_args__ = (
        UniqueConstraint('plugin_id', 'remote_account_id', name='uq_account_plugin_remote'),
    )

    track_states: Mapped[list["UserTrackState"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        foreign_keys="[UserTrackState.account_id]"
    )
    artist_ratings: Mapped[list["UserArtistRating"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    album_ratings: Mapped[list["UserAlbumRating"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class UserRating(WorkingBase):
    __tablename__ = "user_ratings"
    __table_args__ = (
        UniqueConstraint("account_id", "sync_id", name="uq_user_sync_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    sync_id: Mapped[str] = mapped_column(String, nullable=False, index=True)  # 8-character Base62 NanoID
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 1-5, or system flags 0.1, 2.1, 3.1
    play_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


# TODO: Defer to v2.8.0 Entity Overhaul
class WatchlistArtist(WorkingBase):
    """Model for tracking watched artists and their scan status."""
    __tablename__ = "watchlist_artists"

    id: Mapped[int] = mapped_column(primary_key=True)
    spotify_artist_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    artist_name: Mapped[str] = mapped_column(String, nullable=False)
    last_scan_timestamp: Mapped[Optional[datetime]] = mapped_column(UTCDateTime())
    image_url: Mapped[Optional[str]] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )


class ReviewTask(WorkingBase):
    """Model for items in the Metadata Review Queue."""
    __tablename__ = "review_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False, index=True)
    track_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)  # pending, approved, ignored
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )

    @property
    def detected_metadata(self) -> Optional[dict]:
        if not self.track_data:
            return None
        return {
            "title": self.track_data.get("title") or self.track_data.get("raw_title"),
            "artist": self.track_data.get("artist"),
            "album": self.track_data.get("album_title") or self.track_data.get("album"),
            "year": self.track_data.get("release_year") or self.track_data.get("year"),
            "track_number": self.track_data.get("track_number"),
            "disc_number": self.track_data.get("disc_number"),
            "musicbrainz_id": self.track_data.get("mbid") or self.track_data.get("musicbrainz_id"),
            "isrc": self.track_data.get("isrc"),
            "acoustid_id": self.track_data.get("acoustid") or self.track_data.get("acoustid_id"),
            "mb_release_id": self.track_data.get("mb_release_id"),
            "fingerprint": self.track_data.get("fingerprint"),
        }

    @detected_metadata.setter
    def detected_metadata(self, val: Optional[dict]):
        if val is None:
            self.track_data = {}
            return
        if not self.track_data:
            self.track_data = {}
        self.track_data["title"] = val.get("title")
        self.track_data["raw_title"] = val.get("title") or val.get("raw_title")
        self.track_data["artist"] = val.get("artist") or val.get("artist_name")
        self.track_data["album_title"] = val.get("album") or val.get("album_title")
        self.track_data["release_year"] = val.get("year") or val.get("release_year")
        self.track_data["track_number"] = val.get("track_number")
        self.track_data["disc_number"] = val.get("disc_number")
        self.track_data["mbid"] = val.get("musicbrainz_id") or val.get("mbid")
        self.track_data["isrc"] = val.get("isrc")
        self.track_data["acoustid"] = val.get("acoustid_id") or val.get("acoustid")
        self.track_data["mb_release_id"] = val.get("mb_release_id")
        self.track_data["fingerprint"] = val.get("fingerprint")

    @property
    def media_id(self) -> str:
        return self.file_path

    @media_id.setter
    def media_id(self, val: str):
        self.file_path = val


class DownloadQueue(WorkingBase):
    """Model for tracking download state (Central Control)."""
    __tablename__ = "download_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    sync_id: Mapped[str] = mapped_column(String, nullable=False, index=True)  # 8-character Base62 NanoID
    # Serialized EchosyncTrack containing the new slimmed-down conceptual serialization 
    # (media array instead of top-level file data).
    echo_sync_track: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    provider_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )


class UserTrackState(WorkingBase):
    __tablename__ = "user_track_states"
    __table_args__ = (
        UniqueConstraint("account_id", "sync_id", name="uq_user_track_state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    sync_id: Mapped[str] = mapped_column(String, nullable=False, index=True)  # 8-character Base62 NanoID
    
    is_unlinked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_hard_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sponsor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    admin_exempt_deletion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_force_upgrade: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lifecycle_action: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    lifecycle_queued_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )

    account: Mapped["Account"] = relationship(back_populates="track_states", foreign_keys=[account_id])
    sponsor: Mapped[Optional["Account"]] = relationship(foreign_keys=[sponsor_id])


# TODO: Defer to v2.8.0 Entity Overhaul
class UserArtistRating(WorkingBase):
    __tablename__ = "user_artist_ratings"
    __table_args__ = (
        UniqueConstraint("account_id", "artist_urn", name="uq_user_artist_rating"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    artist_urn: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[float] = mapped_column(Float)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    account: Mapped["Account"] = relationship(back_populates="artist_ratings")


# TODO: Defer to v2.8.0 Entity Overhaul
class UserAlbumRating(WorkingBase):
    __tablename__ = "user_album_ratings"
    __table_args__ = (
        UniqueConstraint("account_id", "album_urn", name="uq_user_album_rating"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    album_urn: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[float] = mapped_column(Float)

    account: Mapped["Account"] = relationship(back_populates="album_ratings")


class PlaybackHistory(WorkingBase):
    __tablename__ = "playback_history"
    __table_args__ = (
        UniqueConstraint("user_id", "plugin_item_id", "listened_at", name="uq_playback_history"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    plugin_item_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    listened_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, index=True)


class SuggestionStagingQueue(WorkingBase):
    __tablename__ = "suggestion_staging_queue"
    __table_args__ = (
        UniqueConstraint(
            "account_id", "sync_id", "reason",
            name="uq_suggestion_per_account_sync_reason"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    sync_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)  # NanoID
    reason: Mapped[str] = mapped_column(String, nullable=False, index=True)

    intent_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    ui_label: Mapped[str] = mapped_column(String, nullable=False)
    context_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", index=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )


class SuggestionBlacklist(WorkingBase):
    """
    Persistent veto list for sync_ids. Once a sync_id is added here the
    Intent Engine will never surface it again in any queue, regardless of
    future rating changes.
    """
    __tablename__ = "suggestion_blacklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    sync_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)  # NanoID
    reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Optional admin note

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class PluginStateKVS(WorkingBase):
    __tablename__ = "plugin_state_kvs"

    plugin_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


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


class PluginDatabaseFactory:
    """
    Phase 1: Persistent Plugin Database Factory.
    Dynamically points to a centralized, persistent directory for plugin DBs.
    Structured to abstract away the dialect, so it can return PostgreSQL schemas in the future.
    """
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        
        # Dynamically point to data/plugin_storage/{plugin_id}/storage.db
        data_dir = os.getenv("ECHOSYNC_DATA_DIR", "data")
        self.storage_dir = Path(data_dir) / "plugin_storage" / str(self.plugin_id)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.database_path = self.storage_dir / "storage.db"
        self.engine_url = f"sqlite:///{self.database_path}"
        
        self.engine = create_engine(
            self.engine_url,
            future=True,
            echo=False,
            poolclass=NullPool,
            connect_args={"check_same_thread": False}
        )
        event.listen(self.engine, "connect", _sqlite_pragmas)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

    def get_engine(self):
        """Return the underlying engine. Future-proofs for returning a Postgres schema engine."""
        return self.engine

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


class WorkingDatabase:
    """Helper for creating the engine/session and managing the working schema."""

    def __init__(self, database_path: Optional[str] = None) -> None:
        from core.settings import config_manager

        uri = config_manager.get("database.working_uri")
        if uri:
            engine_url = uri
        else:
            data_dir = os.getenv("ECHOSYNC_DATA_DIR")
            if database_path:
                resolved_path = Path(database_path)
            elif data_dir:
                resolved_path = Path(data_dir) / "working.db"
            else:
                resolved_path = Path("data") / "working.db"

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
            account = session.query(Account).filter(Account.username == "Echosync System").first()
            if account:
                return account.id

            # Create system user account. Use plugin_id=0 for system.
            system_account = Account(
                username="Echosync System",
                plugin_id=0,
                remote_account_id="system_local_admin"
            )
            session.add(system_account)
            session.commit()
            return system_account.id

    def get_provider_storage(self, plugin_id: str) -> PluginDatabaseFactory:
        """
        Phase 1 requirement: Returns a factory that dynamically points to 
        the plugin's distinct persistent database.
        """
        return PluginDatabaseFactory(plugin_id)

    def dispose(self) -> None:
        self.engine.dispose()


_working_db_instance: Optional[WorkingDatabase] = None

def get_working_database(database_path: Optional[str] = None) -> WorkingDatabase:
    global _working_db_instance
    if _working_db_instance is None:
        _working_db_instance = WorkingDatabase(database_path)
    return _working_db_instance

def close_working_database() -> None:
    global _working_db_instance
    if _working_db_instance is not None:
        _working_db_instance.dispose()
        _working_db_instance = None


working_session_registry = scoped_session(lambda: get_working_database().SessionLocal)

__all__ = [
    "WorkingBase",
    "Account",
    "UserRating",
    "WatchlistArtist",
    "ReviewTask",
    "DownloadQueue",
    "UserTrackState",
    "UserArtistRating",
    "UserAlbumRating",
    "PlaybackHistory",
    "SuggestionStagingQueue",
    "SuggestionBlacklist",
    "PluginStateKVS",
    "PluginDatabaseFactory",
    "WorkingDatabase",
    "get_working_database",
    "close_working_database",
    "INTENT_TYPES",
    "working_session_registry",
]
