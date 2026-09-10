"""TaskRepository for managing ReviewTasks and related tasks in working.db."""

from __future__ import annotations

from typing import Any

import database.working_database as wdb
from database.working_database import ReviewTask


class TaskRepository:
    """Repository for managing review tasks in working.db."""

    @classmethod
    def create_review_task(
        cls,
        session: Any | None = None,
        file_path: str = "",
        action: str = "RESOLVE_LIBRARY_ORPHAN",
        track_id: int | None = None,
        media_id: int | None = None,
        track_data: dict[str, Any] | None = None,
        confidence_score: float = 0.0,
        status: str = "pending",
        **kwargs: Any,
    ) -> ReviewTask:
        """Create or update a ReviewTask in working.db non-destructively."""
        data = track_data.copy() if isinstance(track_data, dict) else {}
        if action:
            data["action"] = action
        if track_id is not None:
            data["track_id"] = track_id
        if media_id is not None:
            data["media_id"] = media_id
        for k, v in kwargs.items():
            data[k] = v

        file_path_str = str(file_path)

        def _upsert(s: Any) -> ReviewTask:
            existing = (
                s.query(ReviewTask)
                .filter(ReviewTask.file_path == file_path_str)
                .first()
            )
            if existing:
                existing.track_data = data
                existing.status = status
                existing.confidence_score = confidence_score
                s.flush()
                return existing

            task = ReviewTask(
                file_path=file_path_str,
                status=status,
                track_data=data,
                confidence_score=confidence_score,
            )
            s.add(task)
            s.flush()
            return task

        if session is not None:
            return _upsert(session)
        else:
            w_db = wdb.get_working_database()
            with w_db.session_scope() as s:
                return _upsert(s)
