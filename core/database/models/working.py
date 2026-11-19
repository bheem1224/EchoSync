"""Operational state and download queue models for working.db."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, Integer, String, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, synonym, validates

from time_utils import UTCDateTime, utc_now


class WorkingBase(DeclarativeBase):
    """Base metadata class for WorkingDatabase SQLAlchemy models."""


Base = WorkingBase


class StatusStr(str):
    """Case-insensitive string representation for download status."""

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (str, DownloadStatus)):
            val = other.value if isinstance(other, DownloadStatus) else str(other)
            return self.upper() == val.upper()
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.upper())


class DownloadStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    SEARCHING = "SEARCHING"
    DOWNLOADING = "DOWNLOADING"
    VERIFYING = "VERIFYING"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PENDING_BLOCKED = "PENDING_BLOCKED"

    # Backward-compatible aliases
    COMPLETE = "COMPLETED"
    VERIFIED = "COMPLETED"
    CANCELED = "CANCELLED"
    IN_PROGRESS = "DOWNLOADING"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (str, DownloadStatus)):
            val = other.value if isinstance(other, DownloadStatus) else str(other)
            return self.value.upper() == val.upper()
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.value.upper())


class DownloadStatusType(TypeDecorator):
    """SQLAlchemy TypeDecorator for DownloadStatus."""

    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, DownloadStatus):
            return value.value
        return str(value).upper()

    def process_result_value(self, value: Any, dialect: Any) -> StatusStr | None:
        if value is None:
            return None
        return StatusStr(str(value).upper())


class DownloadIntent(str, enum.Enum):
    MANUAL_OMNI = "MANUAL_OMNI"
    PLAYLIST_SYNC = "PLAYLIST_SYNC"
    SUGGESTION_BACKFILL = "SUGGESTION_BACKFILL"
    UNTRACKED_DROP = "UNTRACKED_DROP"


class DownloadQueue(WorkingBase):
    """Model for tracking download state in working.db (Central Control)."""

    __tablename__ = "download_queue"

    id: int = Column(Integer, primary_key=True)
    sync_id: str | None = Column(String(64), nullable=True, index=True)
    intent: str = Column(
        String(32), nullable=False, default=DownloadIntent.MANUAL_OMNI.value
    )
    status: str = Column(
        DownloadStatusType(),
        nullable=False,
        default=DownloadStatus.QUEUED.value,
        index=True,
    )
    active_candidate_id: str | None = Column(String(128), nullable=True)
    candidate_stack: list = Column(JSON, nullable=False, default=list)
    blacklisted_candidates: list = Column(JSON, nullable=False, default=list)
    retry_count: int = Column(Integer, nullable=False, default=0)
    error_reason: str | None = Column(String(255), nullable=True)
    echo_sync_track: dict | None = Column(JSON, nullable=True)
    plugin_id: str | None = Column(String(128), nullable=True, index=True)
    provider_id = synonym("plugin_id")

    created_at: datetime = Column(UTCDateTime(), nullable=False, default=utc_now)
    updated_at: datetime = Column(
        UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )

    @validates("status")
    def _validate_status(self, key: str, value: Any) -> StatusStr:
        if isinstance(value, DownloadStatus):
            return StatusStr(value.value)
        if isinstance(value, str):
            val_upper = value.strip().upper()
            try:
                return StatusStr(DownloadStatus[val_upper].value)
            except KeyError:
                return StatusStr(val_upper)
        return StatusStr(str(value).upper())

    @validates("intent")
    def _validate_intent(self, key: str, value: Any) -> str:
        if isinstance(value, DownloadIntent):
            return value.value
        if isinstance(value, str):
            val_upper = value.upper()
            try:
                return DownloadIntent[val_upper].value
            except KeyError:
                return value
        return str(value)

    def __init__(self, **kwargs):
        if "retry_count" not in kwargs:
            kwargs["retry_count"] = 0
        if "candidate_stack" not in kwargs:
            kwargs["candidate_stack"] = []
        if "blacklisted_candidates" not in kwargs:
            kwargs["blacklisted_candidates"] = []
        if "intent" not in kwargs:
            kwargs["intent"] = DownloadIntent.MANUAL_OMNI.value
        if "status" not in kwargs:
            kwargs["status"] = DownloadStatus.QUEUED.value
        super().__init__(**kwargs)

    def rotate_candidate(
        self,
        failed_candidate_id: str | None = None,
        max_retries: int = 3,
        *,
        reason: str | None = None,
    ) -> bool:
        """Record the failed candidate in blacklisted_candidates, increment retry_count,

        clear active_candidate_id, and transition status to RETRYING (or FAILED when
        retry_count >= max_retries).
        """
        candidate_to_blacklist = (
            failed_candidate_id or self.active_candidate_id or self.plugin_id
        )
        blacklist = list(self.blacklisted_candidates or [])
        if candidate_to_blacklist:
            existing_ids = {
                b.get("candidate_id") if isinstance(b, dict) else str(b)
                for b in blacklist
            }
            if candidate_to_blacklist not in existing_ids:
                blacklist.append(
                    {
                        "candidate_id": candidate_to_blacklist,
                        "reason": reason or "CANDIDATE_FAILED",
                    }
                )
            self.blacklisted_candidates = blacklist

        blacklisted_ids = {
            b.get("candidate_id") if isinstance(b, dict) else str(b)
            for b in blacklist
        }

        retries = (self.retry_count if self.retry_count is not None else 0) + 1
        self.retry_count = retries
        self.active_candidate_id = None
        self.plugin_id = None

        if retries >= max_retries:
            self.status = DownloadStatus.FAILED.value
            self.error_reason = "CANDIDATES_EXHAUSTED"
            return False

        stack = list(self.candidate_stack or [])
        while stack:
            next_candidate = stack.pop(0)
            next_id = (
                next_candidate.get("id")
                if isinstance(next_candidate, dict)
                else str(next_candidate)
            )
            if next_id and next_id in blacklisted_ids:
                continue
            self.candidate_stack = stack
            self.active_candidate_id = next_id
            self.status = DownloadStatus.RETRYING.value
            return True

        self.candidate_stack = []
        self.status = DownloadStatus.RETRYING.value
        return True

    def is_exhausted(self, max_retries: int = 3) -> bool:
        """Returns True if retry_count >= max_retries, status is FAILED, or no candidates remain."""
        retries = self.retry_count if self.retry_count is not None else 0
        if retries >= max_retries or self.status == DownloadStatus.FAILED.value:
            return True
        if self.status in (
            DownloadStatus.QUEUED.value,
            DownloadStatus.SEARCHING.value,
            DownloadStatus.RETRYING.value,
        ):
            return False
        if not bool(self.candidate_stack) and not bool(self.active_candidate_id):
            return True
        return False


__all__ = [
    "Base",
    "DownloadIntent",
    "DownloadQueue",
    "DownloadStatus",
]
