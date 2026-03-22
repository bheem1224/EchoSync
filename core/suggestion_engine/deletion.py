"""Lifecycle gate for suggestion engine deletion/upgrade actions."""

from datetime import timedelta
from typing import Dict, Any

from core.event_bus import event_bus
from core.settings import config_manager
from time_utils import utc_now
from database.working_database import get_working_database, UserTrackState, UserRating


DELETE_MONTH_END = "DELETE_MONTH_END"
UPGRADE_WEEK_END = "UPGRADE_WEEK_END"


def _normalize_sync_id(sync_id: str) -> str:
    return (sync_id or "").split("?")[0]


def _get_or_create_states_for_sync_id(session, sync_id: str):
    states = session.query(UserTrackState).filter(UserTrackState.sync_id == sync_id).all()
    if states:
        return states

    # Create minimal state rows for users that have ratings on this sync_id.
    rated_user_ids = [
        user_id for (user_id,) in session.query(UserRating.user_id).filter(UserRating.sync_id == sync_id).distinct().all()
    ]
    for user_id in rated_user_ids:
        session.add(UserTrackState(user_id=user_id, sync_id=sync_id))

    if rated_user_ids:
        session.flush()
        return session.query(UserTrackState).filter(UserTrackState.sync_id == sync_id).all()

    return []


def _clear_lifecycle_state(session, sync_id: str, mark_hard_deleted: bool = False) -> None:
    states = session.query(UserTrackState).filter(UserTrackState.sync_id == sync_id).all()
    now = utc_now()
    for state in states:
        state.lifecycle_action = None
        state.lifecycle_queued_at = None
        if mark_hard_deleted:
            state.is_hard_deleted = True
        state.updated_at = now


def execute_delete_now(sync_id: str) -> Dict[str, Any]:
    """Immediately execute deletion for a staged sync_id."""
    from services.media_manager import MediaManagerService

    base_sync_id = _normalize_sync_id(sync_id)
    media_manager = MediaManagerService()
    track_id = media_manager._resolve_track_id_from_sync_id(base_sync_id)
    if not track_id:
        return {"success": False, "sync_id": base_sync_id, "reason": "track_not_found"}

    deleted = bool(media_manager.delete_track(track_id))
    if not deleted:
        return {"success": False, "sync_id": base_sync_id, "reason": "delete_failed", "track_id": track_id}

    db = get_working_database()
    with db.session_scope() as session:
        _clear_lifecycle_state(session, base_sync_id, mark_hard_deleted=True)

    event_bus.publish(
        {
            "event": "HARD_DELETE_INTENT",
            "sync_id": base_sync_id,
            "scheduled": "IMMEDIATE",
            "reason": "lifecycle_queue_processed",
        }
    )
    return {"success": True, "sync_id": base_sync_id, "track_id": track_id}


def execute_upgrade_now(sync_id: str, quality_profile_id: str | None = None) -> Dict[str, Any]:
    """Immediately queue upgrade for a staged sync_id."""
    from services.library_hygiene import DuplicateHygieneService

    base_sync_id = _normalize_sync_id(sync_id)
    hygiene_service = DuplicateHygieneService()
    download_id = hygiene_service.queue_quality_upgrade_for_sync_id(
        base_sync_id,
        upgrade_quality_profile_id=quality_profile_id,
    )
    if not download_id:
        return {"success": False, "sync_id": base_sync_id, "reason": "upgrade_queue_failed"}

    db = get_working_database()
    with db.session_scope() as session:
        _clear_lifecycle_state(session, base_sync_id)

    event_bus.publish(
        {
            "event": "QUALITY_UPGRADE_INTENT",
            "sync_id": base_sync_id,
            "scheduled": "IMMEDIATE",
            "reason": "lifecycle_queue_processed",
            "download_id": download_id,
        }
    )
    return {"success": True, "sync_id": base_sync_id, "download_id": download_id}


def process_lifecycle_actions() -> Dict[str, Any]:
    """Process staged lifecycle actions based on configured timers and admin flags."""
    now = utc_now()
    manager_cfg = config_manager.get("manager", {}) or {}

    auto_delete_enabled = bool(manager_cfg.get("auto_delete", False))
    auto_upgrade_enabled = bool(manager_cfg.get("auto_upgrade", False))
    upgrade_quality_profile_id = manager_cfg.get("upgrade_quality_profile_id")

    delete_cutoff = now - timedelta(days=30)
    upgrade_cutoff = now - timedelta(days=7)

    db = get_working_database()
    with db.session_scope() as session:
        states = (
            session.query(UserTrackState)
            .filter(UserTrackState.lifecycle_action.in_([DELETE_MONTH_END, UPGRADE_WEEK_END]))
            .all()
        )

    grouped: Dict[str, Dict[str, Any]] = {}
    for state in states:
        row = grouped.setdefault(
            state.sync_id,
            {
                "sync_id": state.sync_id,
                "lifecycle_action": state.lifecycle_action,
                "queued_at": state.lifecycle_queued_at,
                "admin_exempt_deletion": False,
                "admin_force_upgrade": False,
            },
        )
        if state.lifecycle_queued_at and (row["queued_at"] is None or state.lifecycle_queued_at < row["queued_at"]):
            row["queued_at"] = state.lifecycle_queued_at
        row["admin_exempt_deletion"] = row["admin_exempt_deletion"] or bool(state.admin_exempt_deletion)
        row["admin_force_upgrade"] = row["admin_force_upgrade"] or bool(state.admin_force_upgrade)

    summary = {
        "auto_delete_enabled": auto_delete_enabled,
        "auto_upgrade_enabled": auto_upgrade_enabled,
        "delete_processed": 0,
        "upgrade_processed": 0,
        "delete_skipped": 0,
        "upgrade_skipped": 0,
    }

    for item in grouped.values():
        action = item["lifecycle_action"]
        queued_at = item["queued_at"]
        if queued_at is None:
            if action == DELETE_MONTH_END:
                summary["delete_skipped"] += 1
            elif action == UPGRADE_WEEK_END:
                summary["upgrade_skipped"] += 1
            continue

        if action == DELETE_MONTH_END:
            if not auto_delete_enabled or queued_at > delete_cutoff or item["admin_exempt_deletion"]:
                summary["delete_skipped"] += 1
                continue
            result = execute_delete_now(item["sync_id"])
            if result.get("success"):
                summary["delete_processed"] += 1
            else:
                summary["delete_skipped"] += 1
            continue

        if action == UPGRADE_WEEK_END:
            if not auto_upgrade_enabled or queued_at > upgrade_cutoff or item["admin_force_upgrade"]:
                summary["upgrade_skipped"] += 1
                continue
            result = execute_upgrade_now(item["sync_id"], quality_profile_id=upgrade_quality_profile_id)
            if result.get("success"):
                summary["upgrade_processed"] += 1
            else:
                summary["upgrade_skipped"] += 1

    return summary


def apply_lifecycle_action(sync_id: str, consensus_result: Dict[str, Any]) -> Dict[str, Any]:
    """Stage lifecycle actions for timed execution with admin override awareness."""
    base_sync_id = _normalize_sync_id(sync_id)

    db = get_working_database()
    with db.session_scope() as session:
        states = _get_or_create_states_for_sync_id(session, base_sync_id)

        admin_exempt_deletion = any(state.admin_exempt_deletion for state in states)
        admin_force_upgrade = any(state.admin_force_upgrade for state in states)

        action = (consensus_result or {}).get("action", "KEEP")
        now = utc_now()

        # Force-upgrade override wins.
        if admin_force_upgrade:
            for state in states:
                state.lifecycle_action = UPGRADE_WEEK_END
                state.lifecycle_queued_at = now
                state.updated_at = now
            return {"status": "UPGRADE_FORCED", "action": UPGRADE_WEEK_END, "sync_id": base_sync_id}

        if action == DELETE_MONTH_END:
            if admin_exempt_deletion:
                return {"status": "KEEP_EXEMPT", "action": "KEEP", "sync_id": base_sync_id}

            for state in states:
                state.lifecycle_action = DELETE_MONTH_END
                state.lifecycle_queued_at = now
                state.updated_at = now
            return {"status": "DELETE_STAGED", "action": DELETE_MONTH_END, "sync_id": base_sync_id}

        if action == UPGRADE_WEEK_END:
            for state in states:
                state.lifecycle_action = UPGRADE_WEEK_END
                state.lifecycle_queued_at = now
                state.updated_at = now
            return {"status": "UPGRADE_STAGED", "action": UPGRADE_WEEK_END, "sync_id": base_sync_id}

        _clear_lifecycle_state(session, base_sync_id)

        event_bus.publish(
            {
                "event": "PREFERENCE_MODEL_FEEDBACK",
                "sync_id": sync_id,
                "score_10": (consensus_result or {}).get("score_10"),
                "user_ids": (consensus_result or {}).get("user_ids", []),
            }
        )
        return {"status": "KEEP", "action": "KEEP_AND_FEED_PREFERENCE_MODEL", "sync_id": base_sync_id}
