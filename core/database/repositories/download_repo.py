"""Repository for DownloadQueue operational state and lifecycle transitions in working.db."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Union

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from core.database.models.working import DownloadQueue, DownloadStatus, DownloadIntent
from database.working_database import get_working_database
from time_utils import utc_now

logger = logging.getLogger("download_repo")


class DownloadRepository:
    """Repository providing atomic operations and queries for DownloadQueue items.

    Enforces concurrency invariants: work queues exclude items in DOWNLOADING and VERIFYING
    to avoid worker collisions.
    """

    def __init__(self, session: Optional[Session] = None, work_db: Optional[Any] = None) -> None:
        self.session = session
        self.work_db = work_db

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        if self.session is not None:
            yield self.session
        elif self.work_db is not None:
            with self.work_db.session_scope() as session:
                yield session
        else:
            with get_working_database().session_scope() as session:
                yield session

    def create_queue_item(
        self,
        sync_id: Optional[str] = None,
        intent: Union[str, DownloadIntent] = DownloadIntent.MANUAL_OMNI,
        echo_sync_track: Optional[Dict[str, Any]] = None,
        candidate_stack: Optional[List[Dict[str, Any]]] = None,
        active_candidate_id: Optional[str] = None,
        plugin_id: Optional[str] = None,
        status: Union[str, DownloadStatus] = DownloadStatus.QUEUED,
    ) -> DownloadQueue:
        """Create and persist a new DownloadQueue item."""
        intent_val = intent.value if isinstance(intent, DownloadIntent) else str(intent)
        status_val = status.value if isinstance(status, DownloadStatus) else str(status)

        with self._get_session() as session:
            item = DownloadQueue(
                sync_id=sync_id,
                intent=intent_val,
                status=status_val,
                echo_sync_track=echo_sync_track,
                candidate_stack=list(candidate_stack or []),
                active_candidate_id=active_candidate_id,
                plugin_id=plugin_id,
                retry_count=0,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(item)
            session.flush()
            session.refresh(item)
            return item

    def get_by_id(self, item_id: int) -> Optional[DownloadQueue]:
        """Fetch a DownloadQueue item by primary key."""
        with self._get_session() as session:
            return session.get(DownloadQueue, item_id)

    def get_by_sync_id(self, sync_id: str) -> List[DownloadQueue]:
        """Fetch DownloadQueue items associated with a canonical NanoID sync_id."""
        with self._get_session() as session:
            return session.query(DownloadQueue).filter(DownloadQueue.sync_id == sync_id).all()

    def get_actionable_queue(self, limit: int = 30) -> List[DownloadQueue]:
        """Fetch actionable items ready for search/dispatch (QUEUED or RETRYING).

        Strictly excludes tasks in DOWNLOADING, VERIFYING, COMPLETED, and FAILED
        to prevent concurrent worker collisions.
        """
        actionable_statuses = [DownloadStatus.QUEUED.value, DownloadStatus.RETRYING.value]
        excluded_statuses = [
            DownloadStatus.DOWNLOADING.value,
            DownloadStatus.VERIFYING.value,
            DownloadStatus.COMPLETED.value,
            DownloadStatus.FAILED.value,
        ]
        with self._get_session() as session:
            return (
                session.query(DownloadQueue)
                .filter(DownloadQueue.status.in_(actionable_statuses))
                .filter(DownloadQueue.status.notin_(excluded_statuses))
                .order_by(
                    DownloadQueue.retry_count.asc().nullsfirst(),
                    DownloadQueue.created_at.desc(),
                )
                .limit(limit)
                .all()
            )

    def get_active_downloads(self) -> List[DownloadQueue]:
        """Fetch items currently in DOWNLOADING or VERIFYING state."""
        active_statuses = [DownloadStatus.DOWNLOADING.value, DownloadStatus.VERIFYING.value]
        with self._get_session() as session:
            return (
                session.query(DownloadQueue)
                .filter(DownloadQueue.status.in_(active_statuses))
                .order_by(DownloadQueue.id.asc())
                .all()
            )

    def atomic_transition(
        self,
        item_id: int,
        from_statuses: List[Union[str, DownloadStatus]],
        to_status: Union[str, DownloadStatus],
        **updates: Any,
    ) -> bool:
        """Perform an atomic conditional status transition.

        Returns True if row was matched and transitioned, False otherwise.
        """
        from_vals = [
            s.value if isinstance(s, DownloadStatus) else str(s).upper() for s in from_statuses
        ]
        to_val = to_status.value if isinstance(to_status, DownloadStatus) else str(to_status).upper()

        update_values: Dict[str, Any] = {"status": to_val, "updated_at": utc_now()}
        update_values.update(updates)

        with self._get_session() as session:
            stmt = (
                update(DownloadQueue)
                .where(DownloadQueue.id == item_id)
                .where(DownloadQueue.status.in_(from_vals))
                .values(**update_values)
            )
            result = session.execute(stmt)
            return result.rowcount > 0

    def transition_to_searching(self, item_id: int) -> bool:
        """Transition item from QUEUED or RETRYING to SEARCHING."""
        return self.atomic_transition(
            item_id=item_id,
            from_statuses=[DownloadStatus.QUEUED, DownloadStatus.RETRYING],
            to_status=DownloadStatus.SEARCHING,
        )

    def transition_to_downloading(
        self,
        item_id: int,
        active_candidate_id: str,
        candidate_stack: Optional[List[Dict[str, Any]]] = None,
        plugin_id: Optional[str] = None,
    ) -> bool:
        """Transition item from SEARCHING (or RETRYING) to DOWNLOADING."""
        updates: Dict[str, Any] = {"active_candidate_id": active_candidate_id}
        if candidate_stack is not None:
            updates["candidate_stack"] = candidate_stack
        if plugin_id is not None:
            updates["plugin_id"] = plugin_id

        return self.atomic_transition(
            item_id=item_id,
            from_statuses=[DownloadStatus.SEARCHING, DownloadStatus.RETRYING, DownloadStatus.QUEUED],
            to_status=DownloadStatus.DOWNLOADING,
            **updates,
        )

    def transition_to_verifying(self, item_id: int) -> bool:
        """Transition item from DOWNLOADING to VERIFYING upon file acquisition."""
        return self.atomic_transition(
            item_id=item_id,
            from_statuses=[DownloadStatus.DOWNLOADING],
            to_status=DownloadStatus.VERIFYING,
        )

    def transition_to_completed(self, item_id: int) -> bool:
        """Transition item from VERIFYING (or DOWNLOADING) to COMPLETED."""
        return self.atomic_transition(
            item_id=item_id,
            from_statuses=[DownloadStatus.VERIFYING, DownloadStatus.DOWNLOADING],
            to_status=DownloadStatus.COMPLETED,
        )

    def transition_to_retrying_or_failed(self, item_id: int, reason: str) -> bool:
        """Rotate candidate on verification failure or transfer error.

        Appends rejected candidate to blacklisted_candidates, pops next candidate from stack,
        and transitions to RETRYING or FAILED.
        """
        with self._get_session() as session:
            item = session.get(DownloadQueue, item_id)
            if not item:
                logger.warning(f"DownloadQueue item {item_id} not found for candidate rotation")
                return False

            rotated = item.rotate_candidate(reason)
            item.updated_at = utc_now()
            session.commit()
            return rotated

    def transition_to_failed(self, item_id: int, error_reason: str) -> bool:
        """Directly transition item to FAILED with an explicit error reason."""
        with self._get_session() as session:
            item = session.get(DownloadQueue, item_id)
            if not item:
                return False
            item.status = DownloadStatus.FAILED.value
            item.error_reason = error_reason
            item.updated_at = utc_now()
            session.commit()
            return True


__all__ = ["DownloadRepository"]
