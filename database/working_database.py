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


class WorkingAccount(WorkingBase):
    __tablename__ = "working_accounts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    plugin_id: Mapped[int] = mapped_column(Integer, index=True)
    remote_user_id: Mapped[str] = mapped_column(String(255), index=True)

    __table_args__ = (
        UniqueConstraint('plugin_id', 'remote_user_id', name='uq_working_account_anchor'),
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
    account_id: Mapped[int] = mapped_column(nullable=False, index=True)
    sync_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 1-5, or system flags 0.1, 2.1, 3.1
    play_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    @validates('sync_id')
    def validate_sync_id(self, key, sync_id):
        if sync_id:
            return str(sync_id).split('?')[0]
        return sync_id


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
    file_path: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)  # pending, approved, ignored
    detected_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )


class DownloadQueue(WorkingBase):
    """Model for tracking download state (Central Control)."""
    __tablename__ = "download_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    sync_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    echo_sync_track: Mapped[dict] = mapped_column(JSON, nullable=False)  # Serialized EchosyncTrack
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    provider_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )

    @validates('sync_id')
    def validate_sync_id(self, key, sync_id):
        if sync_id:
            return str(sync_id).split('?')[0]
        return sync_id


class UserTrackState(WorkingBase):
    __tablename__ = "user_track_states"
    __table_args__ = (
        UniqueConstraint("account_id", "sync_id", name="uq_user_track_state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("working_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    sync_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    is_unlinked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_hard_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sponsor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("working_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    admin_exempt_deletion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_force_upgrade: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lifecycle_action: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    lifecycle_queued_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )

    account: Mapped["WorkingAccount"] = relationship(back_populates="track_states", foreign_keys=[account_id])
    sponsor: Mapped[Optional["WorkingAccount"]] = relationship(foreign_keys=[sponsor_id])

    @validates('sync_id')
    def validate_sync_id(self, key, sync_id):
        if sync_id:
            return str(sync_id).split('?')[0]
        return sync_id


class UserArtistRating(WorkingBase):
    __tablename__ = "user_artist_ratings"
    __table_args__ = (
        UniqueConstraint("account_id", "artist_urn", name="uq_user_artist_rating"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("working_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    artist_urn: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[float] = mapped_column(Float)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    account: Mapped["WorkingAccount"] = relationship(back_populates="artist_ratings")


class UserAlbumRating(WorkingBase):
    __tablename__ = "user_album_ratings"
    __table_args__ = (
        UniqueConstraint("account_id", "album_urn", name="uq_user_album_rating"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("working_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    album_urn: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[float] = mapped_column(Float)

    account: Mapped["WorkingAccount"] = relationship(back_populates="album_ratings")




class SuggestionStagingQueue(WorkingBase):
    """
    Staging queue for tracks that the Suggestion Engine wants to surface to a user.

    Each row is a single suggestion -- de-duplicated per the appropriate key depending
    on the entry-point that created it:

    - Tracks *found* in the local library (near-miss, vibe discovery): deduplicated on
      ``(user_id, music_db_track_id, reason)``.
    - Tracks *missing* from the local library (playlist-gap mining): deduplicated on
      ``(user_id, sync_id, reason)`` -- ``music_db_track_id`` is NULL for these rows.

    Populated by:
    - ``discovery.recommend_near_miss()``  -- duration-miss alternate editions.
    - ``discovery.mine_cached_playlists()`` -- tracks absent from the library and not
      already sitting in the Download queue.
    - Future entry points: vibe-based discovery, gap analysis, etc.

    Canonical ``reason`` values:
    - ``"near_miss_alternate_edition"`` -- duration-miss but text was near-perfect
    - ``"vibe_discovery"``              -- vibe-engine surfaced a rarely-played track
    - ``"playlist_gap"``                -- track is in a Spotify playlist but absent
                                           from the local library and the download queue

    Consumed by the UI layer (e.g. ``GET /api/suggestions``) which reads pending rows,
    presents them to the user, and marks them as accepted / dismissed.
    """
    __tablename__ = "suggestion_staging_queue"
    __table_args__ = (
        # Dedup for locally-matched tracks (near-miss, vibe).
        UniqueConstraint(
            "account_id", "music_db_track_id", "reason",
            name="uq_suggestion_per_user_track_reason"
        ),
        # Dedup for missing tracks (playlist-gap).  SQLite treats NULL as distinct in
        # unique indexes, so rows with NULL sync_id are never caught by this constraint
        # and rows with a real sync_id are correctly deduplicated.
        UniqueConstraint(
            "account_id", "sync_id", "reason",
            name="uq_suggestion_per_user_sync_reason"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # The internal user identifier (string form; mirrors PlaybackHistory.user_id).
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Primary key of the matching local track in music.db's ``tracks`` table.
    # NULL for playlist-gap suggestions where the track does not yet exist locally.
    music_db_track_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    # Deterministic Echosync sync_id (``ss:track:meta:{hash}``) used to identify a
    # track that is absent from the local library.  NULL for near-miss / vibe rows
    # where ``music_db_track_id`` is the canonical identifier instead.
    sync_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    # Short machine-readable reason tag used for UI grouping / filtering.
    reason: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Structured intent type from the 6-value Intent Engine taxonomy.
    # Nullable so existing rows (pre-migration) keep working – the UI
    # should fall back to ``reason`` when this is NULL.
    intent_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    # Human-readable label shown in the UI alongside the suggestion.
    ui_label: Mapped[str] = mapped_column(String, nullable=False)

    # Free-form JSON blob -- callers may store extra context (matched source title,
    # duration diff, sync context, playlist name, etc.) to help the user decide.
    context_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Lifecycle: "pending" -> "accepted" | "dismissed" | "vetoed"
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", index=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now
    )

    @validates('sync_id')
    def validate_sync_id(self, key, sync_id):
        if sync_id:
            return str(sync_id).split('?')[0]
        return sync_id



