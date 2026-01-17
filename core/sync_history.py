"""Sync history and logging for observability."""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import threading

from core.tiered_logger import get_logger

logger = get_logger("sync_history")


@dataclass
class SyncRecord:
    """Record of a single sync operation."""
    timestamp: str  # ISO format
    source: str  # e.g. "spotify"
    target: str  # e.g. "plex"
    playlist: str
    total_tracks: int
    synced: int
    failed: int
    missing: int = 0
    download_missing: bool = False
    job_name: Optional[str] = None
    errors: List[str] = field(default_factory=lambda: [])

    def to_dict(self):
        """Convert to dict for serialization."""
        return asdict(self)


class SyncHistory:
    """Thread-safe sync history tracker (in-memory + optional file logging)."""

    def __init__(self, history_file: Optional[str] = None, max_records: int = 100):
        self._lock = threading.Lock()
        self._records: List[SyncRecord] = []
        self._max_records = max_records
        self._history_file = Path(history_file) if history_file else None

    def record_sync(
        self,
        source: str,
        target: str,
        playlist: str,
        total: int,
        synced: int,
        failed: int,
        missing: int = 0,
        download_missing: bool = False,
        job_name: Optional[str] = None,
        errors: Optional[List[str]] = None,
    ) -> SyncRecord:
        """Record a completed sync operation."""
        record = SyncRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            target=target,
            playlist=playlist,
            total_tracks=total,
            synced=synced,
            failed=failed,
            missing=missing,
            download_missing=download_missing,
            job_name=job_name,
            errors=errors or [],
        )

        with self._lock:
            self._records.append(record)
            # Keep only the most recent max_records
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]

        # Log to file if configured
        if self._history_file:
            self._write_record(record)

        logger.info(
            f"Sync recorded: {source}→{target} playlist '{playlist}' "
            f"({synced}/{total} synced, {failed} failed, {missing} missing)"
        )

        return record

    def get_records(self, source: Optional[str] = None, target: Optional[str] = None) -> List[SyncRecord]:
        """Get recent sync records, optionally filtered by source/target."""
        with self._lock:
            records = list(self._records)

        if source:
            records = [r for r in records if r.source == source]
        if target:
            records = [r for r in records if r.target == target]

        return records

    def get_recent(self, limit: int = 10) -> List[SyncRecord]:
        """Get the N most recent sync records."""
        with self._lock:
            return list(self._records[-limit:])

    def clear(self) -> None:
        """Clear all sync history (typically used for testing)."""
        with self._lock:
            self._records.clear()

    def _write_record(self, record: SyncRecord) -> None:
        """Write sync record to history file."""
        if not self._history_file:
            return

        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._history_file, "a") as f:
                f.write(json.dumps(record.to_dict()) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write sync history: {e}")


# Global singleton
sync_history = SyncHistory(history_file="data/sync_history.jsonl")
