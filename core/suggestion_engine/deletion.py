"""Lifecycle gate for suggestion engine deletion/upgrade actions."""

from typing import Dict, Any

from core.event_bus import event_bus
from database.working_database import get_working_database, UserTrackState


def apply_lifecycle_action(sync_id: str, consensus_result: Dict[str, Any]) -> Dict[str, Any]:
    """Apply lifecycle action with admin overrides and publish intent events."""
    base_sync_id = sync_id.split('?')[0]

    db = get_working_database()
    with db.session_scope() as session:
        states = session.query(UserTrackState).filter(UserTrackState.sync_id == base_sync_id).all()

        admin_exempt_deletion = any(state.admin_exempt_deletion for state in states)
        admin_force_upgrade = any(state.admin_force_upgrade for state in states)

        action = (consensus_result or {}).get("action", "KEEP")

        # Force-upgrade override wins unless deletion exemption is the only requested action.
        if admin_force_upgrade:
            event_bus.publish(
                {
                    "event": "QUALITY_UPGRADE_INTENT",
                    "sync_id": sync_id,
                    "scheduled": "WEEK_END",
                    "reason": "admin_force_upgrade",
                }
            )
            return {"status": "UPGRADE_FORCED", "action": "UPGRADE_WEEK_END", "sync_id": base_sync_id}

        if action == "DELETE_MONTH_END":
            if admin_exempt_deletion:
                event_bus.publish(
                    {
                        "event": "LIFECYCLE_KEEP_INTENT",
                        "sync_id": sync_id,
                        "reason": "admin_exempt_deletion",
                    }
                )
                return {"status": "KEEP_EXEMPT", "action": "KEEP", "sync_id": base_sync_id}

            event_bus.publish(
                {
                    "event": "HARD_DELETE_INTENT",
                    "sync_id": sync_id,
                    "scheduled": "MONTH_END",
                    "reason": "score_1_2",
                }
            )
            return {"status": "DELETE_SCHEDULED", "action": "DELETE_MONTH_END", "sync_id": base_sync_id}

        if action == "UPGRADE_WEEK_END":
            event_bus.publish(
                {
                    "event": "QUALITY_UPGRADE_INTENT",
                    "sync_id": sync_id,
                    "scheduled": "WEEK_END",
                    "reason": "score_3_4",
                }
            )
            return {"status": "UPGRADE_SCHEDULED", "action": "UPGRADE_WEEK_END", "sync_id": base_sync_id}

        event_bus.publish(
            {
                "event": "PREFERENCE_MODEL_FEEDBACK",
                "sync_id": sync_id,
                "score_10": (consensus_result or {}).get("score_10"),
                "user_ids": (consensus_result or {}).get("user_ids", []),
            }
        )
        return {"status": "KEEP", "action": "KEEP_AND_FEED_PREFERENCE_MODEL", "sync_id": base_sync_id}
