from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from web.auth import require_auth


class ManagerSettingsRequest(BaseModel):
    enabled: bool | None = None
    delete_threshold: int | None = None
    upgrade_threshold: int | None = None
    auto_delete: bool | None = None
    auto_upgrade: bool | None = None
    upgrade_quality_profile_id: str | None = None
    auto_delete_low_quality_duplicates: bool | None = None
    auto_process_suggestion_engine_ratings: bool | None = None
    automation_level: int | None = None


class UIBetaRequest(BaseModel):
    enabled: bool | None = None


class OverrideRequest(BaseModel):
    sync_id: str
    field: str | None = None
    value: Any | None = None


class TrackOverrideRequest(BaseModel):
    action: str


class VetoRequest(BaseModel):
    sync_id: str
    reason: str | None = None


class ExecuteRequest(BaseModel):
    sync_id: str
    quality_profile_id: str | None = None


class ConflictResolveRequest(BaseModel):
    resolution: str


from pathlib import Path

from sqlalchemy import func

from core.nexus_framework.plugin_store import plugin_store
from core.settings import config_manager
from core.suggestion_engine.consensus import calculate_consensus
from core.suggestion_engine.deletion import (
    apply_lifecycle_actions_batch,
    execute_delete_now,
)
from core.tiered_logger import get_logger
from database.config_database import get_config_database
from database.music_database import Artist, Track, get_database
from database.working_database import (
    Account,
    SuggestionBlacklist,
    SuggestionStagingQueue,
    UserTrackState,
    get_working_database,
)
from database.working_database import UserRating as WorkingUserRating
from services.library_hygiene import DuplicateHygieneService
from services.metadata_enhancer import get_metadata_enhancer
from time_utils import utc_now

logger = get_logger("web.routes.manager")
router = APIRouter(prefix="/api/v1/system/manager", tags=["Manager"])


# ---------------------------------------------------------------------------
# Automation Level → Intent Routing (Task 2 – Intent Engine)
# ---------------------------------------------------------------------------

DEFAULT_AUTO_ROUTE_INTENTS: dict[int, frozenset[str]] = {
    # Level 1: Only deterministic hygiene actions are auto-routed to Pending Actions.
    1: frozenset({"HYGIENE_DUPLICATION", "HYGIENE_QUALITY_UPGRADE"}),
    # Level 2: Adds heuristic upgrade suggestions.
    2: frozenset(
        {"HYGIENE_DUPLICATION", "HYGIENE_QUALITY_UPGRADE", "SYSTEM_UPGRADE_SUGGESTION"}
    ),
    # Level 3: Adds heuristic delete suggestions (full automation).
    3: frozenset(
        {
            "HYGIENE_DUPLICATION",
            "HYGIENE_QUALITY_UPGRADE",
            "SYSTEM_UPGRADE_SUGGESTION",
            "SYSTEM_DELETE_SUGGESTION",
        }
    ),
}


def automation_level_to_routing(level: int) -> dict:
    """Translate a single integer automation_level (1-3) to internal routing booleans.

    Returns a dict with:
        auto_route_intents   : frozenset of intent_type strings that skip the
                               Suggestions queue and land directly in Pending Actions.
        auto_hygiene         : bool – deterministic hygiene actions are auto-routed.
        auto_system_upgrade  : bool – heuristic upgrade suggestions are auto-routed.
        auto_system_delete   : bool – heuristic delete suggestions are auto-routed.
    """
    level = max(1, min(level, 3))  # clamp to valid range
    auto_route = DEFAULT_AUTO_ROUTE_INTENTS[level]
    return {
        "level": level,
        "auto_route_intents": list(auto_route),
        "auto_hygiene": level >= 1,
        "auto_system_upgrade": level >= 2,
        "auto_system_delete": level >= 3,
    }


def _normalize_sync_id(sync_id: str) -> str:
    return str(sync_id or "").strip()


def _sync_id_from_track_id(track_id: int) -> str | None:
    db = get_database()
    with db.session_scope() as session:
        row = session.query(Track.sync_id).filter(Track.id == track_id).first()
        if not row:
            return None
        return row.sync_id


def _resolve_track_preview(sync_id: str):
    base_sync_id = _normalize_sync_id(sync_id)
    if not base_sync_id:
        return None

    db = get_database()
    with db.session_scope() as session:
        row = (
            session.query(Track.id, Track.title, Artist.name)
            .join(Artist, Track.artist_id == Artist.id)
            .filter(Track.sync_id == base_sync_id)
            .first()
        )
        if not row:
            return None

        return {
            "track_id": row.id,
            "title": row.title,
            "artist": row.name,
        }


def _resolve_working_user_for_trends(
    user_id: int | None = None, account_id: int | None = None
):
    """Resolve the working DB user for trends filtering.

    Resolution order:
    1) Explicit query params: user_id, then account_id
    2) Active Plex managed account fallback (first active account)
    """
    config_db = get_config_database()
    working_db = get_working_database()

    requested_user_id = user_id
    requested_account_id = account_id

    resolved_user = None
    resolved_account_id = None

    with working_db.session_scope() as session:
        if requested_user_id:
            resolved_user = (
                session.query(User).filter(Account.id == requested_user_id).first()
            )
            if resolved_user:
                session.expunge(resolved_user)
                return resolved_user, None, "user_id"

        if requested_account_id:
            plex_service_id = config_db.get_or_create_service_id("plex")
            account = next(
                (
                    acc
                    for acc in config_db.get_accounts(service_id=plex_service_id)
                    if acc.get("id") == requested_account_id
                ),
                None,
            )
            if account:
                resolved_account_id = account.get("id")
                plex_user_id = str(account.get("user_id") or "").strip()
                if plex_user_id:
                    resolved_user = (
                        session.query(User)
                        .filter(Account.provider_identifier == plex_user_id)
                        .first()
                    )
                if not resolved_user:
                    display_name = (
                        account.get("display_name") or account.get("account_name") or ""
                    ).strip()
                    if display_name:
                        resolved_user = (
                            session.query(User)
                            .filter(Account.username == display_name)
                            .first()
                        )
                if resolved_user:
                    session.expunge(resolved_user)
                    return resolved_user, resolved_account_id, "account_id"

        plex_service_id = config_db.get_or_create_service_id("plex")
        active_accounts = config_db.get_accounts(
            service_id=plex_service_id, is_active=True
        )
        fallback_account = next(
            (acc for acc in active_accounts if acc.get("user_id")), None
        )
        if fallback_account is None and active_accounts:
            fallback_account = active_accounts[0]

        if fallback_account:
            resolved_account_id = fallback_account.get("id")
            plex_user_id = str(fallback_account.get("user_id") or "").strip()
            if plex_user_id:
                resolved_user = (
                    session.query(User)
                    .filter(Account.provider_identifier == plex_user_id)
                    .first()
                )
            if not resolved_user:
                display_name = (
                    fallback_account.get("display_name")
                    or fallback_account.get("account_name")
                    or ""
                ).strip()
                if display_name:
                    resolved_user = (
                        session.query(User)
                        .filter(Account.username == display_name)
                        .first()
                    )

        # Expunge before the session closes so commit() does not expire the object's
        # attributes and callers can safely access .id / .username after this function returns.
        if resolved_user is not None:
            session.expunge(resolved_user)

    return resolved_user, resolved_account_id, "active_account"


@router.api_route("/settings", methods=["GET", "POST"])
def manager_settings(
    request: Request,
    payload: ManagerSettingsRequest | None = None,
    _=Depends(require_auth),
):
    """Get or update manager settings."""
    if request.method == "POST":
        payload_data = payload.model_dump(exclude_unset=True) if payload else {}
        try:
            manager_config = config_manager.get("manager", {})
            for key in [
                "enabled",
                "delete_threshold",
                "upgrade_threshold",
                "auto_delete",
                "auto_upgrade",
                "upgrade_quality_profile_id",
                "auto_delete_low_quality_duplicates",
                "auto_process_suggestion_engine_ratings",
                "automation_level",
            ]:
                if key in payload:
                    manager_config[key] = payload_data[key]

            # Compute and persist routing booleans derived from automation_level
            level = int(manager_config.get("automation_level", 1))
            routing = automation_level_to_routing(level)
            manager_config["_routing"] = routing

            config_manager.set("manager", manager_config)
            return {"success": True, "settings": manager_config, "routing": routing}
        except Exception as e:
            logger.error(f"Error updating manager settings: {e}", exc_info=True)
            return {"error": "Failed to update manager settings"}
    else:
        # GET
        try:
            defaults = {
                "enabled": True,
                "delete_threshold": 1,
                "upgrade_threshold": 2,
                "auto_delete": False,
                "auto_upgrade": False,
                "upgrade_quality_profile_id": None,
                "auto_delete_low_quality_duplicates": False,
                "auto_process_suggestion_engine_ratings": True,
                "automation_level": 1,
            }
            settings = config_manager.get("manager", defaults)
            level = int(settings.get("automation_level", 1))
            routing = automation_level_to_routing(level)
            settings["_routing"] = routing
            return {"success": True, "settings": settings, "routing": routing}
        except Exception as e:
            logger.error(f"Error getting manager settings: {e}", exc_info=True)
            return {"error": "Failed to get manager settings"}


@router.api_route("/ui-beta", methods=["GET", "POST"])
def ui_beta_opt(
    request: Request, payload: UIBetaRequest | None = None, _=Depends(require_auth)
):
    """Get or set the UI plugin beta opt-in flag stored in config.json.

    GET: returns { beta_opt_in: bool, dev_mode: bool }
    POST: accepts JSON { beta_opt_in: true|false } and persists to config.json
    """
    import os

    try:
        if request.method == "POST":
            payload_data = payload.model_dump(exclude_unset=True) if payload else {}
            val = payload_data.get("beta_opt_in")
            if val is None or not isinstance(val, bool):
                return {"error": "beta_opt_in (boolean) required"}
            # Persist to config under ui.beta_plugin_ui
            config_manager.set("ui.beta_plugin_ui", bool(val))
            if not val:
                restore_result = plugin_store.restore_stable_plugins()
                logger.info(f"Beta opt-out restored stable plugins: {restore_result}")
            else:
                restore_result = {}
            config_manager.save_settings(config_manager.get_settings())
            return {
                "success": True,
                "beta_opt_in": bool(val),
                "restore_result": restore_result,
            }

        # GET: return current saved value and dev_mode env flag
        saved = bool(config_manager.get("ui.beta_plugin_ui", False))
        dev_mode = False
        # Support two common env names for dev mode
        if os.environ.get("ECHOSYNC_DEV_MODE", "").lower() in ("1", "true", "yes"):
            dev_mode = True
        if os.environ.get("DEV_MODE", "").lower() in ("1", "true", "yes"):
            dev_mode = True

        return {"beta_opt_in": saved, "dev_mode": dev_mode}
    except Exception as e:
        logger.error(f"Error handling ui-beta opt: {e}", exc_info=True)
        return {"error": "Failed to process UI beta option"}


@router.get("/suggestion-candidates")
def get_suggestion_candidates(limit: int = Query(100), _=Depends(require_auth)):
    """Get consensus-threshold candidates from working DB using the 10-point lifecycle model."""
    work_db = get_working_database()
    limit = limit or 100
    limit = max(1, min(limit, 500))

    try:
        with work_db.session_scope() as session:
            rated_sync_ids = [
                row[0]
                for row in session.query(WorkingUserRating.sync_id).distinct().all()
            ]

            delete_candidates = []
            upgrade_candidates = []

            for sync_id in rated_sync_ids:
                lifecycle = calculate_consensus(sync_id)
                ratings_count = int(lifecycle.get("ratings_count", 0))
                avg_score = float(lifecycle.get("avg_score", 0.0))
                preview = _resolve_track_preview(sync_id) or {}

                candidate = {
                    "sync_id": sync_id,
                    "title": preview.get("title") or sync_id,
                    "artist": preview.get("artist") or "Unknown Artist",
                    "score_10": round(avg_score * 2.0, 1),
                    "ratings_count": ratings_count,
                    "preview": preview,
                    "admin_exempt_deletion": lifecycle.get(
                        "admin_exempt_deletion", False
                    ),
                    "admin_force_upgrade": lifecycle.get("admin_force_upgrade", False),
                }

                if avg_score <= 2.0:
                    delete_candidates.append(candidate)
                elif avg_score <= 4.0:
                    upgrade_candidates.append(candidate)

            delete_candidates.sort(
                key=lambda item: (item["score_10"], -item["ratings_count"])
            )
            upgrade_candidates.sort(
                key=lambda item: (item["score_10"], -item["ratings_count"])
            )

            return {
                "success": True,
                "delete_candidates": delete_candidates[:limit],
                "upgrade_candidates": upgrade_candidates[:limit],
                "thresholds": {
                    "delete_month_end": "score 1-2",
                    "upgrade_week_end": "score 3-4",
                },
            }
    except Exception as e:
        logger.error(f"Error getting suggestion candidates: {e}", exc_info=True)
        return {"error": "Failed to get suggestion candidates"}


@router.post("/suggestion-candidates/override")
def toggle_suggestion_candidate_override(payload: dict, _=Depends(require_auth)):
    """Toggle admin exemption flags used by the suggestion engine lifecycle gate."""
    sync_id = _normalize_sync_id(payload.get("sync_id"))
    field = payload.get("field")
    value = bool(payload.get("value"))

    valid_fields = {"admin_exempt_deletion", "admin_force_upgrade"}
    if not sync_id:
        return {"error": "sync_id is required"}
    if field not in valid_fields:
        return {"error": f"field must be one of: {sorted(valid_fields)}"}

    work_db = get_working_database()
    try:
        with work_db.session_scope() as session:
            rating_user_ids = [
                user_id
                for (user_id,) in (
                    session.query(WorkingUserRating.user_id)
                    .filter(WorkingUserRating.sync_id == sync_id)
                    .distinct()
                    .all()
                )
            ]

            if not rating_user_ids:
                return {"error": "No ratings found for the provided sync_id"}

            existing_states = (
                session.query(UserTrackState)
                .filter(
                    UserTrackState.sync_id == sync_id,
                    UserTrackState.user_id.in_(rating_user_ids),
                )
                .all()
            )
            state_by_user = {state.user_id: state for state in existing_states}

            for user_id in rating_user_ids:
                state = state_by_user.get(user_id)
                if state is None:
                    state = UserTrackState(user_id=user_id, sync_id=sync_id)
                    session.add(state)
                setattr(state, field, value)

            session.flush()

            all_states = (
                session.query(UserTrackState)
                .filter(UserTrackState.sync_id == sync_id)
                .all()
            )
            response_state = {
                "sync_id": sync_id,
                "admin_exempt_deletion": any(
                    state.admin_exempt_deletion for state in all_states
                ),
                "admin_force_upgrade": any(
                    state.admin_force_upgrade for state in all_states
                ),
            }

            return {"success": True, "state": response_state}
    except Exception as e:
        logger.error(
            f"Error toggling suggestion candidate override for {sync_id}: {e}",
            exc_info=True,
        )
        return {"error": "Failed to toggle suggestion candidate override"}


@router.post("/scan")
def run_manager_scan(_=Depends(require_auth)):
    """Scan for duplicates and stage lifecycle actions — no actions are executed.

    This always runs regardless of auto flags. Duplicates are returned for the
    Duplicate Resolution queue. All rated tracks are re-evaluated and any
    DELETE_MONTH_END / UPGRADE_WEEK_END actions are staged in the Pending Actions
    queue for admin review. Admin must explicitly approve or auto flags must be
    set for the scheduled job to act.
    """
    try:
        # 1. Find duplicates (scan only — no deletions)
        hygiene = DuplicateHygieneService()
        dup_result = hygiene.find_duplicates()
        auto_resolve_count = len(dup_result.get("auto_resolve", []))
        manual_review_count = len(dup_result.get("manual_review", []))

        # 2. Re-evaluate all rated tracks and stage lifecycle actions
        work_db = get_working_database()
        staged_deletes = 0
        staged_upgrades = 0

        with work_db.session_scope() as session:
            rated_sync_ids = [
                row[0]
                for row in session.query(WorkingUserRating.sync_id).distinct().all()
            ]

        consensus_map = {}
        for sync_id in rated_sync_ids:
            consensus = calculate_consensus(sync_id)
            action = consensus.get("action", "KEEP")
            if action in ("DELETE_MONTH_END", "UPGRADE_WEEK_END"):
                consensus_map[sync_id] = consensus

        if consensus_map:
            results = apply_lifecycle_actions_batch(consensus_map)
            for raw_sync_id, res in results.items():
                res_action = res.get("action")
                if res_action == "DELETE_MONTH_END":
                    staged_deletes += 1
                elif res_action == "UPGRADE_WEEK_END":
                    staged_upgrades += 1

        logger.info(
            f"Manager scan complete: {auto_resolve_count} auto-resolve duplicates, "
            f"{manual_review_count} manual-review duplicates, "
            f"{staged_deletes} staged deletes, {staged_upgrades} staged upgrades"
        )

        return {
            "success": True,
            "summary": {
                "duplicates_auto_resolve": auto_resolve_count,
                "duplicates_manual_review": manual_review_count,
                "staged_deletes": staged_deletes,
                "staged_upgrades": staged_upgrades,
            },
        }

    except Exception as e:
        logger.error(f"Error running manager scan: {e}", exc_info=True)
        return {"error": "Failed to run manager scan"}


@router.post("/prune/run")
def run_prune_job(_=Depends(require_auth)):
    """Immediately triggers the background 'Prune/Delete' job."""
    try:
        service = DuplicateHygieneService()
        # Run synchronously for now as per "Immediately triggers"
        result = service.run_prune_job()
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error running prune job: {e}", exc_info=True)
        return {"error": "Failed to run prune job"}


@router.get("/duplicates")
def get_duplicates(_=Depends(require_auth)):
    """Get all duplicate groups (auto-resolve and manual-review) for the queue."""
    try:
        service = DuplicateHygieneService()
        result = service.find_duplicates()
        # Combine both types — auto_resolve groups are sorted by quality (recommended_keep_id set),
        # manual_review groups have recommended_keep_id=None. Both have a unified 'tracks' list.
        all_duplicates = result.get("auto_resolve", []) + result.get(
            "manual_review", []
        )
        return {"success": True, "duplicates": all_duplicates}
    except Exception as e:
        logger.error(f"Error getting duplicates: {e}", exc_info=True)
        return {"error": "Failed to get duplicates"}


@router.get("/queue/actions")
def get_action_queue(_=Depends(require_auth)):
    """Get currently staged lifecycle actions and their queue age."""
    now = utc_now()
    work_db = get_working_database()

    try:
        with work_db.session_scope() as session:
            states = (
                session.query(UserTrackState)
                .filter(
                    UserTrackState.lifecycle_action.in_(
                        ["DELETE_MONTH_END", "UPGRADE_WEEK_END"]
                    )
                )
                .all()
            )

        grouped = {}
        for state in states:
            row = grouped.setdefault(
                state.sync_id,
                {
                    "sync_id": state.sync_id,
                    "action_needed": state.lifecycle_action,
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

        queue = []
        for item in grouped.values():
            queued_at = item["queued_at"]
            days_in_queue = 0
            if queued_at:
                days_in_queue = max(0, int((now - queued_at).total_seconds() // 86400))

            preview = _resolve_track_preview(item["sync_id"]) or {}

            queue.append(
                {
                    "sync_id": item["sync_id"],
                    "track_id": preview.get("track_id"),
                    "title": preview.get("title"),
                    "artist": preview.get("artist"),
                    "action_needed": item["action_needed"],
                    "queued_at": queued_at.isoformat() if queued_at else None,
                    "days_in_queue": days_in_queue,
                    "admin_exempt_deletion": item["admin_exempt_deletion"],
                    "admin_force_upgrade": item["admin_force_upgrade"],
                }
            )

        queue.sort(key=lambda row: (row["action_needed"], -(row["days_in_queue"] or 0)))

        return {"success": True, "queue": queue, "count": len(queue)}
    except Exception as e:
        logger.error(f"Error getting staged lifecycle queue: {e}", exc_info=True)
        return {"error": "Failed to get staged lifecycle queue"}


@router.post("/track/{track_id}/force_delete")
def force_delete_track(track_id: int, _=Depends(require_auth)):
    """Force immediate lifecycle delete execution for a track, bypassing timers."""
    sync_id = _sync_id_from_track_id(track_id)
    if not sync_id:
        return {"error": "Track not found"}

    try:
        result = execute_delete_now(sync_id)
        status = 200 if result.get("success") else 400

        # Drop it from the pending queue
        if status == 200:
            work_db = get_working_database()
            from database.working_database import SuggestionStagingQueue

            with work_db.session_scope() as session:
                intent = (
                    session.query(SuggestionStagingQueue)
                    .filter_by(sync_id=sync_id)
                    .first()
                )
                if intent:
                    session.delete(intent)

        return result, status
    except Exception as e:
        logger.error(f"Error forcing delete for track {track_id}: {e}", exc_info=True)
        return {"error": "Failed to force delete track"}


@router.post("/track/{track_id}/force_upgrade")
def force_upgrade_track(track_id: int, _=Depends(require_auth)):
    """Force immediate lifecycle upgrade execution for a track, bypassing timers."""
    from core.event_bus import event_bus

    sync_id = _sync_id_from_track_id(track_id)
    if not sync_id:
        return {"error": "Track not found"}

    payload_data = payload.model_dump(exclude_unset=True) if payload else {}
    quality_profile_id = payload_data.get("quality_profile_id")

    try:
        # Fetch EchosyncTrack dict
        from database.music_database import get_database

        db = get_database()
        track_dict = {}
        with db.session_scope() as session:
            from database.music_database import Album, Artist, Track

            track = session.query(Track).filter_by(id=track_id).first()
            if track:
                artist = session.query(Artist).filter_by(id=track.artist_id).first()
                album = session.query(Album).filter_by(id=track.album_id).first()

                track_dict = {
                    "id": track.id,
                    "title": track.title,
                    "artist_name": artist.name if artist else None,
                    "album_title": album.title if album else None,
                    "duration": track.duration,
                    "musicbrainz_id": track.musicbrainz_id,
                    "isrc": track.isrc,
                    "acoustid_id": track.acoustid_id,
                    "sync_id": sync_id,
                }

        event_bus.publish(
            {
                "event": "DOWNLOAD_INTENT",
                "sync_id": sync_id,
                "track": track_dict,
                "target_quality_profile": quality_profile_id,
                "priority": 1,
            }
        )

        # Drop it from the pending queue
        work_db = get_working_database()
        from database.working_database import SuggestionStagingQueue

        with work_db.session_scope() as session:
            intent = (
                session.query(SuggestionStagingQueue).filter_by(sync_id=sync_id).first()
            )
            if intent:
                session.delete(intent)

        return {"success": True}
    except Exception as e:
        logger.error(f"Error forcing upgrade for track {track_id}: {e}", exc_info=True)
        return {"error": "Failed to force upgrade track"}


@router.post("/track/{track_id}/fetch_metadata")
def fetch_metadata(track_id: int, _=Depends(require_auth)):
    """Manually triggers metadata identification for a library track and creates/updates
    a ReviewTask in working.db so the user can edit and approve tags in the full Metadata Editor."""
    import os

    from sqlalchemy.orm.attributes import flag_modified

    from database.music_database import Track, get_database
    from database.working_database import ReviewTask, get_working_database

    db = get_database()
    working_db = get_working_database()
    try:
        with db.session_scope() as session:
            track = session.query(Track).filter(Track.id == track_id).first()
            if not track:
                return {"error": "Track not found"}

            file_path = track.file_path
            if not file_path or not os.path.exists(file_path):
                return {"error": f"Track file not found on disk: {file_path}"}

            artist_name = track.artist.name if track.artist else "Unknown Artist"
            album_title = track.album.title if track.album else "Unknown Album"
            release_year = (
                track.album.release_date.year
                if (track.album and track.album.release_date)
                else None
            )

            track_dict = {
                "title": track.title,
                "raw_title": track.title,
                "display_title": track.title,
                "artist": artist_name,
                "artist_name": artist_name,
                "album": album_title,
                "album_title": album_title,
                "year": release_year,
                "release_year": release_year,
                "track_number": track.track_number,
                "disc_number": track.disc_number,
                "duration": track.duration,
                "musicbrainz_id": track.musicbrainz_id,
                "isrc": track.isrc,
                "file_path": file_path,
            }

        enhancer = get_metadata_enhancer()
        identified_metadata, confidence = enhancer.identify_file(Path(file_path))

        detected = (
            dict(identified_metadata) if identified_metadata else dict(track_dict)
        )
        if not detected.get("artist"):
            detected["artist"] = artist_name
        if not detected.get("title"):
            detected["title"] = track_dict["title"]
        if not detected.get("album"):
            detected["album"] = album_title

        with working_db.session_scope() as w_session:
            task = (
                w_session.query(ReviewTask)
                .filter(ReviewTask.file_path == file_path)
                .first()
            )
            if not task:
                task = ReviewTask(
                    file_path=file_path,
                    status="pending",
                    confidence_score=confidence if confidence is not None else 0.5,
                    track_data=track_dict,
                )
                task.detected_metadata = detected
                w_session.add(task)
                w_session.flush()
            else:
                task.status = "pending"
                task.track_data = track_dict
                task.detected_metadata = detected
                task.confidence_score = (
                    confidence if confidence is not None else task.confidence_score
                )
                flag_modified(task, "track_data")
                w_session.flush()

            from web.routes.metadata_review import _serialize_task

            serialized_task = _serialize_task(task, detected_metadata=detected)

        return {
            "success": True,
            "task": serialized_task,
            "metadata": detected,
            "confidence": confidence or 0.5,
        }
    except Exception as e:
        logger.error(
            f"Error fetching metadata for track {track_id}: {e}", exc_info=True
        )
        return {"error": f"Failed to fetch track metadata: {e}"}


@router.post("/track/{track_id}/override")
def override_track(
    track_id: int, payload: TrackOverrideRequest, _=Depends(require_auth)
):
    """DEPRECATED: Manual overrides removed in Phase 3.

    Phase 3 Suggestion Engine uses event-driven consensus, not system flags.
    Deletion decisions are now made by the Deletion Gate based on:
    - Global consensus (>= 2 ratings AND avg < 4.0)
    - Sponsor rating (from user_track_states)

    Manual track management should happen through the auto_importer or library hygiene service.
    """
    raise HTTPException(
        status_code=410,
        detail={
            "success": False,
            "error": "Manual track overrides are deprecated. Use Phase 3 Suggestion Engine consensus rules.",
        },
    )


@router.post("/conflicts/resolve")
def resolve_conflict(payload: ConflictResolveRequest, _=Depends(require_auth)):
    """Manually resolve a conflict by keeping one track and deleting others."""
    payload_data = payload.model_dump(exclude_unset=True) if payload else {}
    keep_id = payload_data.get("keep_id")
    delete_ids = payload_data.get("delete_ids", [])

    if not keep_id or not delete_ids:
        return {"error": "keep_id and delete_ids are required"}

    try:
        service = DuplicateHygieneService()
        success = service.resolve_conflict(keep_id, delete_ids)
        if success:
            return {"success": True}
        else:
            return {"error": "Failed to resolve some conflicts"}
    except Exception as e:
        logger.error(f"Error resolving conflict: {e}", exc_info=True)
        return {"error": "Failed to resolve conflict"}


@router.get("/trends")
def get_trends(
    user_id: int | None = Query(None),
    account_id: int | None = Query(None),
    _=Depends(require_auth),
):
    """Returns library stats (filtered)."""
    work_db = get_working_database()
    try:
        target_user, resolved_account_id, source = _resolve_working_user_for_trends(
            user_id=user_id, account_id=account_id
        )

        with work_db.session_scope() as session:
            # Use SQL aggregation for efficiency
            distribution_stmt = session.query(
                func.round(WorkingUserRating.rating), func.count(WorkingUserRating.id)
            ).filter(WorkingUserRating.rating.isnot(None))

            if target_user:
                distribution_stmt = distribution_stmt.filter(
                    WorkingUserRating.user_id == target_user.id
                )

            distribution_query = distribution_stmt.group_by(
                func.round(WorkingUserRating.rating)
            ).all()

            distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            total_filtered = 0
            sum_ratings = 0

            for rating_val, count in distribution_query:
                if rating_val is None:
                    continue
                r = int(rating_val)
                if r in distribution:
                    distribution[r] = count
                total_filtered += count
                sum_ratings += r * count

            avg = sum_ratings / total_filtered if total_filtered > 0 else 0

            return {
                "total_ratings": total_filtered,
                "average_rating": avg,
                "distribution": distribution,
                "user_scope": {
                    "source": source,
                    "account_id": resolved_account_id,
                    "working_user_id": target_user.id if target_user else None,
                    "working_username": target_user.username if target_user else None,
                },
                "note": "Genre stats unavailable (schema limitation)",
            }
    except Exception as e:
        logger.error(f"Error getting trends: {e}", exc_info=True)
        return {"error": "Failed to get library trends"}


@router.get("/search")
def search_library(q: str = Query(None), _=Depends(require_auth)):
    """Unified search endpoint."""
    query = q
    if not query:
        return {"artists": [], "albums": [], "tracks": []}

    db = get_database()
    try:
        results = db.search_library(query)
        return results
    except Exception as e:
        logger.error(f"Error searching library: {e}", exc_info=True)
        return {"error": "Failed to search library"}


@router.post("/settings")
def set_manager_settings(payload: ManagerSettingsRequest, _=Depends(require_auth)):
    from core.settings import config_manager

    payload_data = payload.model_dump(exclude_unset=True) if payload else {}
    config_manager.set("media_manager", payload)
    config_manager.save_settings(config_manager.get_settings())
    return {"success": True}


@router.get("/queue/suggestions")
def get_suggestion_queue(_=Depends(require_auth)):
    work_db = get_working_database()
    try:
        with work_db.session_scope() as session:
            # Use SuggestionStagingQueue (the real table) instead of invented SuggestionIntent
            items = (
                session.query(SuggestionStagingQueue)
                .filter(SuggestionStagingQueue.status == "pending")
                .all()
            )
            return {
                "success": True,
                "suggestions": [
                    {
                        "sync_id": item.sync_id,
                        "type": item.reason,
                        "originator": (item.context_data or {}).get(
                            "originator", "Consensus Engine"
                        ),
                        "title": item.ui_label,
                        "track_id": item.music_db_track_id,
                        "action_needed": (item.context_data or {}).get(
                            "action_needed", "SUGGESTION"
                        ),
                        "user_id": item.user_id,
                        "account_id": item.account_id,
                    }
                    for item in items
                ],
            }
    except Exception as e:
        logger.error(f"Error getting suggestion queue: {e}", exc_info=True)
        return {"error": "Failed to get suggestion queue"}


@router.post("/suggestion-candidates/override")
def override_suggestion_candidate(payload: OverrideRequest, _=Depends(require_auth)):
    payload_data = payload.model_dump(exclude_unset=True) if payload else {}
    sync_id = payload_data.get("sync_id")
    # Note: These fields are usually in UserTrackState, but if the UI is overriding the staging queue directly:
    field = payload_data.get("field")
    value = payload_data.get("value")

    if not sync_id or value is None:
        return {"error": "Invalid payload"}

    work_db = get_working_database()
    try:
        with work_db.session_scope() as session:
            item = (
                session.query(SuggestionStagingQueue).filter_by(sync_id=sync_id).first()
            )
            if not item:
                return {"error": "Suggestion not found"}

            # Update context_data if the field is not a direct column
            if hasattr(item, field):
                setattr(item, field, value)
            else:
                ctx = dict(item.context_data or {})
                ctx[field] = value
                item.context_data = ctx
            return {"success": True}
    except Exception as e:
        logger.error(f"Error overriding suggestion candidate: {e}", exc_info=True)
        return {"error": "Failed to override suggestion candidate"}


@router.post("/veto")
def veto_suggestion(payload: VetoRequest, _=Depends(require_auth)):
    """Add a sync_id to the persistent veto / blacklist so the Intent Engine
    never surfaces it again.  Also marks any matching SuggestionStagingQueue
    row as 'vetoed'.

    Body: { "sync_id": "ss:track:meta:...", "reason": "<optional note>" }
    """
    payload_data = payload.model_dump(exclude_unset=True) if payload else {}
    sync_id = _normalize_sync_id(payload_data.get("sync_id", ""))
    reason = payload_data.get("reason", "")

    if not sync_id:
        return {"error": "sync_id is required"}

    work_db = get_working_database()
    try:
        with work_db.session_scope() as session:
            # Upsert into the blacklist table
            existing = (
                session.query(SuggestionBlacklist).filter_by(sync_id=sync_id).first()
            )
            if existing is None:
                session.add(SuggestionBlacklist(sync_id=sync_id, reason=reason or None))
            else:
                if reason:
                    existing.reason = reason

            # Mark any pending suggestions as vetoed
            items = (
                session.query(SuggestionStagingQueue).filter_by(sync_id=sync_id).all()
            )
            for item in items:
                item.status = "vetoed"

        logger.info(f"Vetoed sync_id={sync_id} (reason={reason!r})")
        return {"success": True, "sync_id": sync_id}
    except Exception as e:
        logger.error(f"Error vetoing suggestion {sync_id}: {e}", exc_info=True)
        return {"error": "Failed to veto suggestion"}


@router.post("/execute")
def execute_pending_action(payload: ExecuteRequest, _=Depends(require_auth)):
    """Bypass countdown timers and immediately execute a Pending Actions entry.

    Dispatches DELETE_MONTH_END → execute_delete_now
               UPGRADE_WEEK_END → execute_upgrade_now (fires DOWNLOAD_INTENT).

    Body: { "sync_id": "ss:track:meta:...", "quality_profile_id": "<optional>" }
    """
    from core.event_bus import event_bus

    payload_data = payload.model_dump(exclude_unset=True) if payload else {}
    sync_id = _normalize_sync_id(payload_data.get("sync_id", ""))
    quality_profile_id = payload_data.get("quality_profile_id")

    if not sync_id:
        return {"error": "sync_id is required"}

    work_db = get_working_database()
    try:
        # Determine the lifecycle action for this sync_id
        with work_db.session_scope() as session:
            states = (
                session.query(UserTrackState)
                .filter(
                    UserTrackState.sync_id == sync_id,
                    UserTrackState.lifecycle_action.in_(
                        ["DELETE_MONTH_END", "UPGRADE_WEEK_END"]
                    ),
                )
                .all()
            )
            if not states:
                return {"error": "No pending lifecycle action found for this sync_id"}

            action = states[0].lifecycle_action  # All rows share the same action

        if action == "DELETE_MONTH_END":
            result = execute_delete_now(sync_id)
            if not result.get("success"):
                return result
        elif action == "UPGRADE_WEEK_END":
            preview = _resolve_track_preview(sync_id) or {}
            event_bus.publish(
                {
                    "event": "DOWNLOAD_INTENT",
                    "sync_id": sync_id,
                    "track": preview,
                    "target_quality_profile": quality_profile_id,
                    "priority": 1,
                }
            )
        else:
            return {"error": f"Unknown lifecycle action: {action}"}

        # Clear the lifecycle action from working DB rows
        with work_db.session_scope() as session:
            session.query(UserTrackState).filter(
                UserTrackState.sync_id == sync_id
            ).update({"lifecycle_action": None, "lifecycle_queued_at": None})

        logger.info(f"Executed pending action {action} for sync_id={sync_id}")
        return {"success": True, "sync_id": sync_id, "executed_action": action}
    except Exception as e:
        logger.error(
            f"Error executing pending action for {sync_id}: {e}", exc_info=True
        )
        return {"error": "Failed to execute pending action"}
