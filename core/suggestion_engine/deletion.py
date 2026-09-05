from typing import Any

"""Lifecycle gate for suggestion engine deletion/upgrade actions."""

from datetime import timedelta

from core.event_bus import event_bus
from core.settings import config_manager
from database.working_database import UserRating, UserTrackState, get_working_database
from time_utils import utc_now

DELETE_MONTH_END = "DELETE_MONTH_END"
UPGRADE_WEEK_END = "UPGRADE_WEEK_END"


def _normalize_sync_id(sync_id: str) -> str:
    return (sync_id or "").split("?")[0]


def _get_or_create_states_for_sync_id(session, sync_id: str):
    states = (
        session.query(UserTrackState).filter(UserTrackState.sync_id == sync_id).all()
    )
    if states:
        return states

    # Create minimal state rows for users that have ratings on this sync_id.
    rated_user_ids = [
        user_id
        for (user_id,) in session.query(UserRating.account_id)
        .filter(UserRating.sync_id == sync_id)
        .distinct()
        .all()
    ]
    for user_id in rated_user_ids:
        session.add(UserTrackState(account_id=user_id, sync_id=sync_id))

    if rated_user_ids:
        session.flush()
        return (
            session.query(UserTrackState)
            .filter(UserTrackState.sync_id == sync_id)
            .all()
        )

    return []


def _clear_lifecycle_state(
    session, sync_id: str, mark_hard_deleted: bool = False
) -> None:
    states = (
        session.query(UserTrackState).filter(UserTrackState.sync_id == sync_id).all()
    )
    now = utc_now()
    for state in states:
        state.lifecycle_action = None
        state.lifecycle_queued_at = None
        if mark_hard_deleted:
            state.is_hard_deleted = True
        state.updated_at = now


def execute_delete_now(sync_id: str) -> dict[str, Any]:
    """Immediately execute deletion for a staged sync_id."""
    from services.media_manager import MediaManagerService

    base_sync_id = _normalize_sync_id(sync_id)
    media_manager = MediaManagerService()
    track_id = media_manager._resolve_track_id_from_sync_id(base_sync_id)
    if not track_id:
        return {"success": False, "sync_id": base_sync_id, "reason": "track_not_found"}

    deleted = bool(media_manager.delete_track(track_id))
    if not deleted:
        return {
            "success": False,
            "sync_id": base_sync_id,
            "reason": "delete_failed",
            "track_id": track_id,
        }

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


def execute_upgrade_now(
    sync_id: str, quality_profile_id: str | None = None
) -> dict[str, Any]:
    """Immediately queue upgrade for a staged sync_id."""
    from services.library_hygiene import DuplicateHygieneService

    base_sync_id = _normalize_sync_id(sync_id)
    hygiene_service = DuplicateHygieneService()
    download_id = hygiene_service.queue_quality_upgrade_for_sync_id(
        base_sync_id,
        upgrade_quality_profile_id=quality_profile_id,
    )
    if not download_id:
        return {
            "success": False,
            "sync_id": base_sync_id,
            "reason": "upgrade_queue_failed",
        }

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


def process_lifecycle_actions() -> dict[str, Any]:
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
            .filter(
                UserTrackState.lifecycle_action.in_(
                    [DELETE_MONTH_END, UPGRADE_WEEK_END]
                )
            )
            .all()
        )

    grouped: dict[str, dict[str, Any]] = {}
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
        if state.lifecycle_queued_at and (
            row["queued_at"] is None or state.lifecycle_queued_at < row["queued_at"]
        ):
            row["queued_at"] = state.lifecycle_queued_at
        row["admin_exempt_deletion"] = row["admin_exempt_deletion"] or bool(
            state.admin_exempt_deletion
        )
        row["admin_force_upgrade"] = row["admin_force_upgrade"] or bool(
            state.admin_force_upgrade
        )

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
            if (
                not auto_delete_enabled
                or queued_at > delete_cutoff
                or item["admin_exempt_deletion"]
            ):
                summary["delete_skipped"] += 1
                continue
            result = execute_delete_now(item["sync_id"])
            if result.get("success"):
                summary["delete_processed"] += 1
            else:
                summary["delete_skipped"] += 1
            continue

        if action == UPGRADE_WEEK_END:
            if (
                not auto_upgrade_enabled
                or queued_at > upgrade_cutoff
                or item["admin_force_upgrade"]
            ):
                summary["upgrade_skipped"] += 1
                continue
            result = execute_upgrade_now(
                item["sync_id"], quality_profile_id=upgrade_quality_profile_id
            )
            if result.get("success"):
                summary["upgrade_processed"] += 1
            else:
                summary["upgrade_skipped"] += 1

    return summary


def apply_lifecycle_actions_batch(
    consensus_map: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Stage lifecycle actions for timed execution with admin override awareness in bulk."""

    from sqlalchemy import and_, func, or_

    from core.tiered_logger import get_logger
    from database.music_database import Artist, ExternalIdentifier, Track
    from database.music_database import get_database as get_music_database

    logger = get_logger("deletion")
    db = get_working_database()
    now = utc_now()
    results = {}

    # 1. Normalize and identify tracks needing veto check
    normalized_map = {}
    veto_checks = []
    parsed_tracks = []

    for raw_sync_id, consensus in consensus_map.items():
        base_sync_id = _normalize_sync_id(raw_sync_id)
        normalized_map[base_sync_id] = consensus

        action = (consensus or {}).get("action", "KEEP")
        if action == DELETE_MONTH_END:
            veto_checks.append(base_sync_id)
            try:
                music_db = get_music_database()
                with music_db.session_scope() as music_session:
                    track = (
                        music_session.query(Track)
                        .filter_by(sync_id=base_sync_id)
                        .first()
                    )
                    if track and track.artist:
                        artist_name = track.artist.name
                        title = track.title
                        parsed_tracks.append(
                            (artist_name.lower(), title.lower(), base_sync_id)
                        )
            except Exception:
                pass

    # 2. Bulk veto resolution using MusicDB
    vetoed_sync_ids = set()
    if parsed_tracks:
        music_db = get_music_database()
        with music_db.session_scope() as music_session:
            chunk_size = 400
            track_mapping = {}  # (artist, title) -> track_id

            for i in range(0, len(parsed_tracks), chunk_size):
                chunk = parsed_tracks[i : i + chunk_size]
                conditions = [
                    and_(func.lower(Artist.name) == a, func.lower(Track.title) == t)
                    for a, t, _ in chunk
                ]

                tracks = (
                    music_session.query(Track.id, Track.title, Artist.name)
                    .join(Artist, Track.artist_id == Artist.id)
                    .filter(or_(*conditions))
                    .all()
                )

                for t_id, t_title, a_name in tracks:
                    track_mapping[(a_name.lower(), t_title.lower())] = t_id

            if track_mapping:
                track_ids = list(track_mapping.values())
                ext_idents = (
                    music_session.query(
                        ExternalIdentifier.track_id, ExternalIdentifier.provider_item_id
                    )
                    .filter(
                        ExternalIdentifier.track_id.in_(track_ids),
                        ExternalIdentifier.provider_item_id.isnot(None),
                    )
                    .all()
                )

                ext_mapping = {row[0]: row[1] for row in ext_idents}

                # Fetch playback history for the resolved provider_item_ids
                provider_item_ids = set(ext_mapping.values())
                if provider_item_ids:
                    from datetime import timedelta

                    from database.working_database import PlaybackHistory

                    cutoff_date = now - timedelta(days=30)
                    with db.session_scope() as w_session:
                        # Chunk the playback history query too
                        listen_counts = {}
                        provider_list = list(provider_item_ids)
                        for i in range(0, len(provider_list), chunk_size):
                            chunk = provider_list[i : i + chunk_size]
                            counts = (
                                w_session.query(
                                    PlaybackHistory.provider_item_id,
                                    func.count(PlaybackHistory.id),
                                )
                                .filter(
                                    PlaybackHistory.provider_item_id.in_(chunk),
                                    PlaybackHistory.listened_at >= cutoff_date,
                                )
                                .group_by(PlaybackHistory.provider_item_id)
                                .all()
                            )

                            for p_id, count in counts:
                                listen_counts[p_id] = count

                    # Resolve which sync_ids are vetoed
                    for artist_name, title, base_sync_id in parsed_tracks:
                        t_id = track_mapping.get((artist_name, title))
                        if t_id:
                            p_id = ext_mapping.get(t_id)
                            if p_id and listen_counts.get(p_id, 0) >= 5:
                                vetoed_sync_ids.add(base_sync_id)
                                logger.info(
                                    f"Vetoed Deletion: Track '{p_id}' is actively trending ({listen_counts[p_id]} listens/30d)."
                                )

    # 3. Apply state updates to WorkingDB in a single transaction with nested savepoints
    with db.session_scope() as session:
        for raw_sync_id, consensus in consensus_map.items():
            try:
                with session.begin_nested():
                    base_sync_id = _normalize_sync_id(raw_sync_id)
                    states = _get_or_create_states_for_sync_id(session, base_sync_id)

                    admin_exempt_deletion = any(
                        state.admin_exempt_deletion for state in states
                    )
                    admin_force_upgrade = any(
                        state.admin_force_upgrade for state in states
                    )
                    action = (consensus or {}).get("action", "KEEP")

                    if base_sync_id in vetoed_sync_ids:
                        admin_exempt_deletion = True
                        for state in states:
                            state.admin_exempt_deletion = True

                    # Force-upgrade override wins.
                    if admin_force_upgrade:
                        for state in states:
                            state.lifecycle_action = UPGRADE_WEEK_END
                            state.lifecycle_queued_at = now
                            state.updated_at = now
                        results[raw_sync_id] = {
                            "status": "UPGRADE_FORCED",
                            "action": UPGRADE_WEEK_END,
                            "sync_id": base_sync_id,
                        }
                        continue

                    if action == DELETE_MONTH_END:
                        if admin_exempt_deletion:
                            results[raw_sync_id] = {
                                "status": "KEEP_EXEMPT",
                                "action": "KEEP",
                                "sync_id": base_sync_id,
                            }
                            continue
                        for state in states:
                            state.lifecycle_action = DELETE_MONTH_END
                            state.lifecycle_queued_at = now
                            state.updated_at = now
                        results[raw_sync_id] = {
                            "status": "DELETE_STAGED",
                            "action": DELETE_MONTH_END,
                            "sync_id": base_sync_id,
                        }
                        continue

                    if action == UPGRADE_WEEK_END:
                        for state in states:
                            state.lifecycle_action = UPGRADE_WEEK_END
                            state.lifecycle_queued_at = now
                            state.updated_at = now
                        results[raw_sync_id] = {
                            "status": "UPGRADE_STAGED",
                            "action": UPGRADE_WEEK_END,
                            "sync_id": base_sync_id,
                        }
                        continue

                    _clear_lifecycle_state(session, base_sync_id)
                    from core.event_bus import event_bus

                    event_bus.publish(
                        {
                            "event": "PREFERENCE_MODEL_FEEDBACK",
                            "sync_id": raw_sync_id,
                            "score_10": (consensus or {}).get("score_10"),
                            "user_ids": (consensus or {}).get("user_ids", []),
                        }
                    )
                    results[raw_sync_id] = {
                        "status": "KEEP",
                        "action": "KEEP_AND_FEED_PREFERENCE_MODEL",
                        "sync_id": base_sync_id,
                    }

            except Exception as e:
                logger.error(
                    f"Error applying lifecycle action for {raw_sync_id}: {e}",
                    exc_info=True,
                )
                results[raw_sync_id] = {"status": "ERROR", "reason": str(e)}

    return results


def apply_lifecycle_action(
    sync_id: str, consensus_result: dict[str, Any]
) -> dict[str, Any]:
    """Stage lifecycle actions for timed execution with admin override awareness."""
    results = apply_lifecycle_actions_batch({sync_id: consensus_result})
    return results.get(sync_id, {})
