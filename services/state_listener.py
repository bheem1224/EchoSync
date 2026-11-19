import zlib
from typing import Any

import database.config_database as _config_db_mod
from core.event_bus import event_bus as default_event_bus
from core.security.rbac import get_current_principal
from core.suggestion_engine.consensus import calculate_consensus, stars_to_ten_point
from core.suggestion_engine.deletion import apply_lifecycle_action
from core.task_manager import db_write_lease
from core.tiered_logger import get_logger
from database.config_database import get_config_database
from database.working_database import (
    Account,
    UserRating,
    UserTrackState,
    get_working_database,
)
from time_utils import utc_now

_ORIG_GET_CONFIG_DB = get_config_database
logger = get_logger("state_listener")


def _compute_deterministic_plugin_id(namespace_or_provider: str) -> int:
    """Derive deterministic unsigned 32-bit plugin_id via zlib.crc32 on canonical namespace."""
    clean = str(namespace_or_provider or "").strip().lower()
    if not clean or clean == "unknown":
        canonical = "echosync.unknown"
    elif "." in clean:
        canonical = clean
    else:
        canonical = f"echosync.{clean}"
    return zlib.crc32(canonical.encode("utf-8")) & 0xFFFFFFFF


def _coerce_uint32_plugin_id(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if 0 <= parsed <= 0xFFFFFFFF:
        return parsed
    return None


def _service_name_matches_provider(service_name: str | None, provider_name: str) -> bool:
    if not service_name or not provider_name:
        return False
    s_clean = str(service_name).strip().lower()
    p_clean = str(provider_name).strip().lower()
    if not p_clean or p_clean == "unknown":
        return False
    return s_clean == p_clean or s_clean.split(".")[-1] == p_clean.split(".")[-1]


class StateListenerService:
    def __init__(self, event_bus=None, session_factory=None, engine=None, config_db=None):
        self.event_bus = event_bus or default_event_bus
        self._config_db = config_db
        if session_factory:
            self.Session = session_factory
        else:
            self.Session = get_working_database().SessionLocal

    def _get_config_db(self):
        if self._config_db is not None:
            return self._config_db
        if get_config_database is not _ORIG_GET_CONFIG_DB:
            return get_config_database()
        return _config_db_mod.get_config_database()

    def subscribe(self):
        if hasattr(self.event_bus, "subscribe"):
            self.event_bus.subscribe("TRACK_RATED", self.handle_track_rated)
            self.event_bus.subscribe("TRACK_PLAYED", self.handle_track_played)

    def _resolve_plugin_id(
        self,
        provider_user_id: str,
        provider_name: str,
        explicit_plugin_id: Any = None,
    ) -> int:
        """Resolve deterministic uint32 plugin_id via Principal, user_managed_accounts, config.db, and zlib.crc32."""
        explicit_id = _coerce_uint32_plugin_id(explicit_plugin_id)
        if explicit_id is not None:
            return explicit_id

        clean_provider = str(provider_name or "").strip()
        has_provider = bool(clean_provider and clean_provider.lower() != "unknown")
        managed_id = str(provider_user_id)

        cfg_db = None
        try:
            cfg_db = self._get_config_db()
        except Exception:
            cfg_db = None

        # 1. Check active Principal context (plugin principal or user_managed_accounts in config.db)
        principal = get_current_principal()
        if principal is not None:
            if principal.principal_type == "plugin":
                principal_pid = _coerce_uint32_plugin_id(principal.plugin_id)
                if principal_pid is not None:
                    return principal_pid

            if principal.user_id and cfg_db is not None:
                try:
                    managed = cfg_db.get_user_managed_accounts(principal.user_id)
                    matches = [
                        m for m in managed if str(m.get("managed_account_id")) == managed_id
                    ]
                    if matches:
                        if has_provider and len(matches) > 1:
                            with cfg_db._get_connection() as conn:
                                rows = conn.execute(
                                    "SELECT plugin_id, name FROM services WHERE plugin_id IS NOT NULL"
                                ).fetchall()
                                svc_map = {int(r["plugin_id"]): r["name"] for r in rows}
                            for m in matches:
                                pid = _coerce_uint32_plugin_id(m.get("server_plugin_id"))
                                if pid is not None and _service_name_matches_provider(
                                    svc_map.get(pid), clean_provider
                                ):
                                    return pid
                        first_pid = _coerce_uint32_plugin_id(matches[0].get("server_plugin_id"))
                        if first_pid is not None:
                            return first_pid
                except Exception as exc:
                    logger.debug(f"Principal managed account resolution fallback: {exc}")

        # 2. Query config.db (services table, user_managed_accounts, and accounts)
        if cfg_db is not None:
            try:
                with cfg_db._get_connection() as conn:
                    cursor = conn.cursor()

                    if has_provider:
                        target_crc = _compute_deterministic_plugin_id(clean_provider)
                        cursor.execute(
                            "SELECT name, plugin_id FROM services ORDER BY id ASC"
                        )
                        for row in cursor.fetchall():
                            row_name = row["name"]
                            row_pid = _coerce_uint32_plugin_id(row["plugin_id"])
                            if row_pid == target_crc or _service_name_matches_provider(
                                row_name, clean_provider
                            ):
                                return (
                                    row_pid
                                    if row_pid is not None
                                    else _compute_deterministic_plugin_id(row_name)
                                )

                    cursor.execute(
                        """
                        SELECT uma.server_plugin_id, s.name AS service_name
                        FROM user_managed_accounts uma
                        LEFT JOIN services s ON s.plugin_id = uma.server_plugin_id
                        WHERE uma.managed_account_id = ?
                        ORDER BY uma.server_plugin_id ASC
                        """,
                        (managed_id,),
                    )
                    uma_rows = cursor.fetchall()
                    if uma_rows:
                        if has_provider:
                            for row in uma_rows:
                                pid = _coerce_uint32_plugin_id(row["server_plugin_id"])
                                if pid is not None and _service_name_matches_provider(
                                    row["service_name"], clean_provider
                                ):
                                    return pid
                        else:
                            pid = _coerce_uint32_plugin_id(uma_rows[0]["server_plugin_id"])
                            if pid is not None:
                                return pid

                    cursor.execute(
                        """
                        SELECT s.plugin_id, s.name AS service_name
                        FROM accounts a
                        JOIN services s ON a.service_id = s.id
                        WHERE a.user_id = ? OR a.account_name = ?
                        ORDER BY a.is_active DESC, a.id ASC
                        """,
                        (managed_id, managed_id),
                    )
                    acct_rows = cursor.fetchall()
                    if acct_rows:
                        for row in acct_rows:
                            if not has_provider or _service_name_matches_provider(
                                row["service_name"], clean_provider
                            ):
                                pid = _coerce_uint32_plugin_id(row["plugin_id"])
                                if pid is not None:
                                    return pid
                                if row["service_name"]:
                                    return _compute_deterministic_plugin_id(row["service_name"])
            except Exception as exc:
                logger.debug(f"ConfigDB plugin resolution fallback: {exc}")

        # 3. Deterministic zlib.crc32 canonical namespace derivation
        return _compute_deterministic_plugin_id(clean_provider)

    def _resolve_account_id(self, session, provider_user_id, provider_name, plugin_id=None):
        provider_user_id = str(provider_user_id)
        resolved_plugin_id = self._resolve_plugin_id(
            provider_user_id=provider_user_id,
            provider_name=provider_name,
            explicit_plugin_id=plugin_id,
        )
        user = (
            session.query(Account)
            .filter(
                Account.remote_account_id == provider_user_id,
                Account.plugin_id == resolved_plugin_id,
            )
            .first()
        )
        if not user:
            user = Account(
                username=f"{provider_name}_{provider_user_id}",
                remote_account_id=provider_user_id,
                plugin_id=resolved_plugin_id,
            )
            session.add(user)
            session.flush()
        return user.id

    def handle_track_rated(self, event_data: dict):
        sync_id = event_data.get("sync_id")
        data = event_data.get("data", {})
        rating = data.get("rating")
        provider_user_id = data.get("account_id") or data.get("user_id")
        provider_name = data.get("provider", "unknown")
        explicit_plugin_id = data.get("plugin_id")

        if not sync_id or rating is None or not provider_user_id:
            return

        with db_write_lease(task_name="handle_track_rated"), self.Session() as session:
            try:
                internal_account_id = self._resolve_account_id(
                    session,
                    provider_user_id,
                    provider_name,
                    plugin_id=explicit_plugin_id,
                )
                base_sync_id = sync_id.split("?")[0]

                existing = (
                    session.query(UserRating)
                    .filter(
                        UserRating.account_id == internal_account_id,
                        UserRating.sync_id == base_sync_id,
                    )
                    .first()
                )

                if existing:
                    existing.rating = float(rating)
                    existing.timestamp = utc_now()
                else:
                    new_rating = UserRating(
                        account_id=internal_account_id,
                        sync_id=base_sync_id,
                        rating=float(rating),
                        timestamp=utc_now(),
                    )
                    session.add(new_rating)
                session.commit()

                # Execute exact 10-point lifecycle policy.
                consensus = calculate_consensus(base_sync_id)
                apply_lifecycle_action(base_sync_id, consensus)

                # Sponsor action: if sponsor rated, remove from Suggestions for You playlist.
                self._handle_sponsor_rating_action(session, base_sync_id, internal_account_id, float(rating))
            except Exception as e:
                logger.error(f"Error in handle_track_rated: {e}", exc_info=True)
                session.rollback()

    def _handle_sponsor_rating_action(self, session, base_sync_id: str, account_id: int, rating_stars: float) -> None:
        sponsor_state = (
            session.query(UserTrackState)
            .filter(
                UserTrackState.sync_id == base_sync_id,
                UserTrackState.sponsor_id == account_id,
            )
            .first()
        )

        if not sponsor_state:
            return

        # Mark as unlinked for sponsor-facing suggestion surfaces.
        with db_write_lease(task_name="handle_sponsor_rating_action"):
            sponsor_state.is_unlinked = True
            sponsor_state.updated_at = utc_now()
            session.commit()

        self.event_bus.publish(
            {
                "event": "SUGGESTION_PLAYLIST_REMOVE_INTENT",
                "sync_id": base_sync_id,
                "account_id": account_id,
                "playlist_name": "Suggestions for You",
                "rating_stars": rating_stars,
                "rating_10": stars_to_ten_point(rating_stars),
            }
        )

    def handle_track_played(self, event_data: dict):
        pass


def start_state_listener():
    listener = StateListenerService()
    listener.subscribe()
    return listener
