"""Operational state and download queue models for working.db."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, String, DateTime, JSON, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, validates, synonym

from time_utils import UTCDateTime, utc_now


class WorkingBase(DeclarativeBase):
    """Base metadata class for WorkingDatabase SQLAlchemy models."""


Base = WorkingBase


class StatusStr(str):
    """Case-insensitive string representation for download status."""
    def __eq__(self, other: Any) -> bool:
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

    def __eq__(self, other: Any) -> bool:
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

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, DownloadStatus):
            return value.value
        return str(value).upper()

    def process_result_value(self, value: Any, dialect: Any) -> Optional[StatusStr]:
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

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    sync_id: Optional[str] = Column(String(64), nullable=True, index=True)
    intent: str = Column(String(32), nullable=False, default=DownloadIntent.MANUAL_OMNI.value)
    status: str = Column(DownloadStatusType(), nullable=False, default=DownloadStatus.QUEUED.value, index=True)
    active_candidate_id: Optional[str] = Column(String(128), nullable=True)
    candidate_stack: list = Column(JSON, nullable=False, default=list)
    blacklisted_candidates: list = Column(JSON, nullable=False, default=list)
    retry_count: int = Column(Integer, nullable=False, default=0)
    error_reason: Optional[str] = Column(String(255), nullable=True)
    echo_sync_track: Optional[dict] = Column(JSON, nullable=True)
    plugin_id: Optional[str] = Column(String(128), nullable=True, index=True)
    provider_id = synonym("plugin_id")

    created_at: datetime = Column(
        UTCDateTime(), nullable=False, default=utc_now
    )
    updated_at: datetime = Column(
        UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )

    @validates("status")
    def _validate_status(self, key: str, value: Any) -> str:
        if isinstance(value, DownloadStatus):
            return value.value
        if isinstance(value, str):
            val_upper = value.upper()
            try:
                return DownloadStatus[val_upper].value
            except KeyError:
                return value
        return str(value)

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

    def rotate_candidate(self, reason: str) -> bool:
        """Appends active candidate to blacklisted_candidates, pops next candidate from stack,

        increments retry_count, and sets status to RETRYING or FAILED.
        """
        if self.active_candidate_id:
            blacklist = list(self.blacklisted_candidates or [])
            blacklist.append({"candidate_id": self.active_candidate_id, "reason": reason})
            self.blacklisted_candidates = blacklist

        stack = list(self.candidate_stack or [])
        retries = self.retry_count if self.retry_count is not None else 0
        if stack and retries < 3:
            next_candidate = stack.pop(0)
            self.candidate_stack = stack
            self.active_candidate_id = (
                next_candidate.get("id") if isinstance(next_candidate, dict) else str(next_candidate)
            )
            self.retry_count = retries + 1
            self.status = DownloadStatus.RETRYING.value
            return True

        self.status = DownloadStatus.FAILED.value
        self.error_reason = "CANDIDATES_EXHAUSTED"
        return False

    def is_exhausted(self) -> bool:
        """Returns True if retry_count >= 3, status is FAILED, or no candidates remain."""
        retries = self.retry_count if self.retry_count is not None else 0
        if retries >= 3 or self.status == DownloadStatus.FAILED.value:
            return True
        if not bool(self.candidate_stack) and not bool(self.active_candidate_id):
            return True
        return False


__all__ = [
    "Base",
    "DownloadStatus",
    "DownloadIntent",
    "DownloadQueue",
]
