"""
Account History Service for v2.1.0 Suggestion Engine baseline population.

Syncs historical play counts and ratings from providers into working.db,
indexed by deterministic sync_id generated from normalized track metadata.
"""

import re

from sqlalchemy import tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from core.tiered_logger import get_logger
from core.user_history import UserTrackInteraction
from database.config_database import get_config_database
from database.music_database import Artist, ExternalIdentifier, LocalMedia, Track
from database.music_database import get_database as get_music_database
from database.working_database import (
    Account,
    PlaybackHistory,
    UserRating,
    get_working_database,
)
from time_utils import utc_now

logger = get_logger("user_history_service")


class UserHistoryService:
    """
    Service for syncing baseline user history from providers into working.db.

    Architecture:
    1. Query active accounts from config_database
    2. For each account, call provider's fetch_user_history()
    3. For each interaction, generate cache ID from normalized artist|title
    4. Lookup track in music_database by cache ID
    5. Store interaction data (ratings, play counts) in working.db linked to sync_id
    """

    def __init__(self):
        """Initialize service with database connections."""
        self.config_db = get_config_database()
        self.working_db = get_working_database()
        self.music_db = get_music_database()
        self.logger = logger

    def sync_baseline_history(self) -> dict[str, int]:
        """
        Synchronize baseline user history from active media servers to working.db.

        This should run after music_database.db has been populated with library metadata
        but before the Suggestion Engine starts making recommendations.

        Returns:
            Statistics dict with keys:
            - accounts_processed: Number of accounts synced
            - interactions_fetched: Total interactions received from providers
            - matches_found: Interactions successfully matched to local tracks
            - ratings_imported: UserRating records created
            - errors: List of error messages encountered
        """
        stats = {
            "users_synced": 0,
            "accounts_processed": 0,
            "interactions_fetched": 0,
            "matches_found": 0,
            "ratings_imported": 0,
            "listen_count_imported": 0,
            "errors": [],
        }

        try:
            # Get all active media servers
            from core.nexus_framework.plugin_loader import PluginRegistry

            active_servers = PluginRegistry.get_active_services_by_type("media_server")

            if not active_servers:
                self.logger.info("No active media servers found for history sync")
                return stats

            for server_id in active_servers:
                try:
                    plugin_cls = PluginRegistry.get_plugin_class(server_id)
                    server_name = (
                        getattr(plugin_cls, "name", str(server_id))
                        if plugin_cls
                        else str(server_id)
                    )

                    plugin_id = self.config_db.get_or_create_service_id(server_name)
                    accounts = self.config_db.get_accounts(
                        service_id=plugin_id, is_active=True
                    )

                    if not accounts:
                        self.logger.debug(f"No active accounts found for {server_name}")
                        continue

                    # Ensure all active managed users exist before history sync.
                    stats["users_synced"] += self.sync_active_media_server_users(
                        server_id, accounts
                    )

                    # Create provider instance
                    try:
                        provider = PluginRegistry.create_instance(server_id)
                    except Exception as e:
                        error_msg = f"Failed to create provider instance for ID {server_id}: {e}"
                        self.logger.error(error_msg)
                        stats["errors"].append(error_msg)
                        continue

                    # Check if provider supports history fetching
                    if not hasattr(provider, "fetch_user_history"):
                        self.logger.debug(
                            f"Provider ID {server_id} does not support fetch_user_history()"
                        )
                        continue

                    # Sync history for each account
                    for account in accounts:
                        account_id_raw = account["id"]
                        account_name = (
                            account.get("display_name")
                            or account.get("account_name")
                            or "Unknown"
                        )

                        # Handle provider-specific account ID casting/validation
                        try:
                            # Assume account_id can be cast to int if it's numeric
                            if str(account_id_raw).isdigit():
                                account_id = int(account_id_raw)
                            else:
                                account_id = str(account_id_raw)
                        except (TypeError, ValueError):
                            self.logger.error(
                                f"Skipping account '{account_name}' on provider ID {server_id}: "
                                f"account_id {account_id_raw!r} invalid"
                            )
                            stats["errors"].append(
                                f"Bad account_id for {account_name} on {server_id}"
                            )
                            continue

                        try:
                            self.logger.info(
                                f"Syncing history from ID {server_id} for account {account_name}"
                            )

                            # Fetch history from provider
                            interactions = provider.fetch_user_history(account_id)
                            stats["interactions_fetched"] += len(interactions)

                            if not interactions:
                                self.logger.info(
                                    f"No history items found for account {account_name}"
                                )
                                stats["accounts_processed"] += 1
                                continue

                            # Get or create user in working_db
                            working_user = self._get_or_create_working_user(
                                account_id=account_id,
                                account_name=account_name,
                                provider_user_id=account.get("user_id"),
                                provider=str(server_id),
                            )

                            if not working_user:
                                error_msg = f"Failed to create working user for account {account_name}"
                                self.logger.error(error_msg)
                                stats["errors"].append(error_msg)
                                continue

                            # Process each interaction
                            matched_count = self._process_interactions(
                                account_id=working_user.id,
                                interactions=interactions,
                                stats=stats,
                                plugin_source=str(server_id),
                            )

                            self.logger.info(
                                f"Completed history sync for {account_name}: "
                                f"{len(interactions)} interactions, {matched_count} matched to local tracks"
                            )
                            stats["accounts_processed"] += 1
                            stats["matches_found"] += matched_count

                        except Exception as e:
                            error_msg = f"Error syncing history for account {account_name} on ID {server_id}: {e}"
                            self.logger.error(error_msg, exc_info=True)
                            stats["errors"].append(error_msg)
                except Exception as e:
                    self.logger.error(
                        f"Failed to process history sync for ID {server_id}: {e}",
                        exc_info=True,
                    )

        except Exception as e:
            error_msg = f"Fatal error in sync_baseline_history: {e}"
            self.logger.error(error_msg, exc_info=True)
            stats["errors"].append(error_msg)

        self.logger.info(f"Account history sync complete: {stats}")
        return stats

    def _get_or_create_working_user(
        self,
        account_id: object,
        account_name: str,
        provider_user_id: str | None = None,
        provider: str = "unknown",
    ) -> Account | None:
        """
        Get or create user record in working.db.

        Returns:
            Account object from working_db, or None if creation failed
        """
        try:
            with self.working_db.session_scope() as session:
                # Try to find existing user by provider_identifier
                if provider_user_id:
                    user = (
                        session.query(Account)
                        .filter(
                            Account.remote_account_id == provider_user_id,
                            Account.plugin_id == 1,
                        )
                        .first()
                    )
                    if user:
                        return user

                # Try to find by username + provider
                user = (
                    session.query(Account)
                    .filter(Account.username == account_name, Account.plugin_id == 1)
                    .first()
                )

                if user:
                    return user

                # Create new user
                user = Account(
                    username=account_name,
                    remote_account_id=provider_user_id,
                    plugin_id=1,
                )
                session.add(user)
                session.commit()
                return user

        except Exception as e:
            self.logger.error(f"Failed to get/create working user: {e}", exc_info=True)
            return None

    def sync_active_media_server_users(
        self, server_name: str, accounts: list[dict] | None = None
    ) -> int:
        """Ensure all active accounts for a server in config.db exist in working.db users."""
        users_synced = 0
        try:
            if accounts is None:
                plugin_id = self.config_db.get_or_create_service_id(server_name)
                accounts = self.config_db.get_accounts(
                    service_id=plugin_id, is_active=True
                )

            for account in accounts or []:
                account_name = (
                    account.get("display_name")
                    or account.get("account_name")
                    or "Unknown"
                )
                user = self._get_or_create_working_user(
                    account_id=account.get("id"),
                    account_name=account_name,
                    provider_user_id=account.get("user_id"),
                    provider=server_name,
                )
                if user:
                    users_synced += 1
        except Exception as e:
            self.logger.error(
                f"Failed syncing active users for {server_name} to working DB: {e}",
                exc_info=True,
            )

        return users_synced

    def _process_interactions(
        self,
        account_id: int,
        interactions: list[UserTrackInteraction],
        stats: dict,
        plugin_source: str | None = None,
    ) -> int:
        """
        Process a list of user interactions and store ratings in working.db.

        For each interaction:
        1. Generate cache ID from artist|title
        2. Lookup track in music_database
        3. Extract or create sync_id
        4. Create/upsert UserRating record

        Args:
            account_id: Working database user ID (account_id)
            interactions: List[UserTrackInteraction] objects
            stats: Statistics dict to update
            plugin_id: Optional plugin ID for ExternalIdentifier matching

        Returns:
            Number of interactions successfully matched and stored
        """
        matched_count = 0
        if not interactions:
            return matched_count

        try:
            with self.music_db.session_scope() as music_session:
                with self.working_db.session_scope() as work_session:
                    interaction_records = []
                    unique_pairs = set()

                    plugin_item_ids: set[str] = set()
                    for interaction in interactions:
                        raw_id = self._extract_plugin_item_id(interaction)
                        if not raw_id:
                            continue
                        plugin_item_ids.add(raw_id)
                        normalized_id = self._normalize_plugin_item_id(raw_id)
                        if normalized_id:
                            plugin_item_ids.add(normalized_id)

                    if not plugin_item_ids:
                        self.logger.debug(
                            "No plugin item IDs found in interactions; using text fallback only"
                        )

                    # Primary O(1) lookup via ExternalIdentifiers.
                    ext_idents = []
                    if plugin_item_ids and plugin_source:
                        ext_idents = (
                            music_session.query(ExternalIdentifier, Track)
                            .join(
                                LocalMedia,
                                ExternalIdentifier.media_id == LocalMedia.media_id,
                            )
                            .join(Track, LocalMedia.track_id == Track.id)
                            .filter(
                                ExternalIdentifier.plugin_source == plugin_source,
                                ExternalIdentifier.plugin_item_id.in_(
                                    list(plugin_item_ids)
                                ),
                            )
                            .all()
                        )

                    plugin_id_to_track: dict[str, Track] = {}
                    for ext_ident, track in ext_idents:
                        raw_ext_id = str(ext_ident.plugin_item_id)
                        plugin_id_to_track[raw_ext_id] = track
                        normalized_ext_id = self._normalize_plugin_item_id(raw_ext_id)
                        if normalized_ext_id:
                            plugin_id_to_track[normalized_ext_id] = track

                    # 1) Record playback history catch-up
                    playback_payloads = []
                    for interaction in interactions:
                        try:
                            extracted_id = self._extract_plugin_item_id(interaction)
                            interaction_plugin_id = (
                                self._normalize_plugin_item_id(extracted_id)
                                or extracted_id
                            )

                            user_record = (
                                work_session.query(Account)
                                .filter_by(id=account_id)
                                .first()
                            )
                            playback_user_id = (
                                user_record.remote_account_id
                                if user_record and user_record.remote_account_id
                                else str(account_id)
                            )

                            if interaction_plugin_id:
                                playback_payloads.append(
                                    {
                                        "user_id": str(playback_user_id),
                                        "plugin_item_id": str(interaction_plugin_id),
                                        "listened_at": interaction.last_played_at
                                        or utc_now(),
                                    }
                                )
                        except Exception as e:
                            self.logger.warning(
                                f"Error preparing playback history for interaction: {e}"
                            )

                    if playback_payloads:
                        if self.working_db.engine.dialect.name == "sqlite":
                            insert_stmt = sqlite_insert(PlaybackHistory).values(
                                playback_payloads
                            )
                            upsert_stmt = insert_stmt.on_conflict_do_nothing(
                                index_elements=[
                                    "user_id",
                                    "plugin_item_id",
                                    "listened_at",
                                ]
                            )
                            work_session.execute(upsert_stmt)

                    # 2) Continue with UserRatings matching
                    for interaction in interactions:
                        try:
                            extracted_id = self._extract_plugin_item_id(interaction)
                            interaction_plugin_id = (
                                self._normalize_plugin_item_id(extracted_id)
                                or extracted_id
                            )

                            if interaction_plugin_id in plugin_id_to_track:
                                track = plugin_id_to_track[interaction_plugin_id]
                                sync_id = track.sync_id
                                interaction_records.append(
                                    {
                                        "interaction": interaction,
                                        "sync_id": sync_id,
                                        "matched_by_id": True,
                                    }
                                )
                                continue

                            if (
                                interaction_plugin_id
                                and interaction_plugin_id.startswith("ss:track:meta:")
                            ):
                                interaction_records.append(
                                    {
                                        "interaction": interaction,
                                        "sync_id": interaction_plugin_id,
                                        "matched_by_id": True,
                                    }
                                )
                                continue

                            # Fallback: text tuple lookup only for rows unmatched by ExternalIdentifier.
                            pair = (interaction.artist_name, interaction.track_title)
                            unique_pairs.add(pair)
                            interaction_records.append(
                                {
                                    "interaction": interaction,
                                    "pair": pair,
                                    "matched_by_id": False,
                                }
                            )

                        except Exception as e:
                            self.logger.warning(
                                f"Error preparing interaction {interaction.artist_name} - {interaction.track_title}: {e}"
                            )

                    if not interaction_records:
                        return 0

                    matched_pairs = set()
                    pair_to_track: dict[tuple, Track] = {}
                    if unique_pairs:
                        matched_tracks = (
                            music_session.query(Track)
                            .join(Track.artist)
                            .filter(
                                tuple_(Artist.name, Track.title).in_(list(unique_pairs))
                            )
                            .all()
                        )
                        matched_pairs = {
                            (track.artist.name, track.title) for track in matched_tracks
                        }
                        pair_to_track = {
                            (track.artist.name, track.title): track
                            for track in matched_tracks
                        }

                    rating_payload_by_sync_id: dict[str, dict[str, object]] = {}

                    for record in interaction_records:
                        interaction = record["interaction"]
                        if record.get("matched_by_id"):
                            sync_id = record["sync_id"]
                        else:
                            pair = record.get("pair")
                            if pair not in matched_pairs:
                                self.logger.debug(
                                    f"No track found for {interaction.artist_name} - {interaction.track_title}"
                                )
                                continue
                            matched_track = pair_to_track[pair]
                            sync_id = matched_track.sync_id

                        play_count = int(getattr(interaction, "play_count", 0) or 0)
                        if interaction.rating is None and play_count <= 0:
                            continue

                        matched_count += 1
                        rating_value = (
                            float(interaction.rating)
                            if interaction.rating is not None
                            else None
                        )
                        rating_payload_by_sync_id[sync_id] = {
                            "account_id": account_id,
                            "sync_id": sync_id,
                            "rating": rating_value,
                            "play_count": play_count,
                            "timestamp": utc_now(),
                        }

                        if interaction.rating is not None:
                            stats["ratings_imported"] += 1
                        stats["listen_count_imported"] += play_count

                    if rating_payload_by_sync_id:
                        self._bulk_upsert_user_ratings(
                            work_session,
                            list(rating_payload_by_sync_id.values()),
                        )

        except Exception as e:
            self.logger.error(f"Error in _process_interactions: {e}", exc_info=True)

        return matched_count

    def _extract_plugin_item_id(self, interaction: UserTrackInteraction) -> str:
        """Extract plugin item ID from current and legacy interaction fields."""
        direct_id = str(
            getattr(
                interaction,
                "plugin_item_id",
                getattr(interaction, "provider_item_id", ""),
            )
            or ""
        ).strip()
        if direct_id:
            return direct_id

        identifiers = getattr(interaction, "identifiers", None)
        if isinstance(identifiers, dict):
            # Iterate known provider key from interaction or fallback to all identifier keys
            provider_key = getattr(interaction, "provider", None)
            keys_to_check = [provider_key] if provider_key else []
            keys_to_check.extend(identifiers.keys())
            for key in keys_to_check:
                if key:
                    provider_id = str(identifiers.get(key, "") or "").strip()
                    if provider_id:
                        return provider_id

        source_item_id = str(getattr(interaction, "source_item_id", "") or "").strip()
        if source_item_id:
            return source_item_id

        return ""

    def _normalize_plugin_item_id(self, provider_item_id: str | None) -> str:
        """Normalize provider/plugin item IDs for robust reverse lookups.

        Handles common Plex representations such as:
        - "120760"
        - "/library/metadata/120760"
        - "http://host:32400/library/metadata/120760"
        - "plex://track/120760"
        """
        raw = str(provider_item_id or "").strip()
        if not raw:
            return ""

        if raw.startswith("ss:track:meta:"):
            return raw

        metadata_match = re.search(r"/library/metadata/(\d+)", raw)
        if metadata_match:
            return metadata_match.group(1)

        trailing_digits = re.search(r"(\d+)$", raw)
        if trailing_digits:
            return trailing_digits.group(1)

        return raw

    def _bulk_upsert_user_ratings(
        self, work_session, rating_payloads: list[dict[str, object]]
    ) -> None:
        """Write matched user ratings in a single bulk transaction."""
        if not rating_payloads:
            return

        for p in rating_payloads:
            p["sync_id"] = str(p["sync_id"])

        if self.working_db.engine.dialect.name == "sqlite":
            # Backward compatibility: some existing working.db files have
            # user_ratings.rating declared NOT NULL. Listen-only rows (rating=None)
            # would fail inserts in that schema, so coerce missing ratings to 0.0.
            # This preserves listen_count ingestion until schema migration is applied.
            try:
                needs_non_null_rating = False
                with self.working_db.engine.connect() as conn:
                    pragma_rows = conn.exec_driver_sql(
                        "PRAGMA table_info('user_ratings')"
                    ).fetchall()
                    for row in pragma_rows:
                        col_name = str(row[1]) if len(row) > 1 else ""
                        not_null_flag = (
                            int(row[3]) if len(row) > 3 and row[3] is not None else 0
                        )
                        if col_name == "rating" and not_null_flag == 1:
                            needs_non_null_rating = True
                            break

                if needs_non_null_rating:
                    adjusted_payloads = []
                    for payload in rating_payloads:
                        if payload.get("rating") is None:
                            patched = dict(payload)
                            patched["rating"] = 0.0
                            adjusted_payloads.append(patched)
                        else:
                            adjusted_payloads.append(payload)
                    rating_payloads = adjusted_payloads
            except Exception:
                # Best-effort compatibility guard; continue with original payloads.
                pass

            insert_stmt = sqlite_insert(UserRating).values(rating_payloads)
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=["account_id", "sync_id"],
                set_={
                    "rating": insert_stmt.excluded.rating,
                    "play_count": insert_stmt.excluded.play_count,
                    "timestamp": insert_stmt.excluded.timestamp,
                },
            )
            work_session.execute(upsert_stmt)
            return

        sync_ids = [payload["sync_id"] for payload in rating_payloads]
        existing_sync_ids = {
            sync_id
            for (sync_id,) in work_session.query(UserRating.sync_id)
            .filter(
                UserRating.account_id == rating_payloads[0]["account_id"],
                UserRating.sync_id.in_(sync_ids),
            )
            .all()
        }

        new_objects = []
        update_mappings = []
        for payload in rating_payloads:
            if payload["sync_id"] in existing_sync_ids:
                update_mappings.append(payload)
            else:
                new_objects.append(UserRating(**payload))

        if new_objects:
            work_session.bulk_save_objects(new_objects)
        if update_mappings:
            # M2: bulk_update_mappings requires the ORM primary key ('id') in each
            # dict to build WHERE clauses.  Payloads from _process_interactions
            # never carry 'id', so this path will silently no-op or raise on
            # non-SQLite engines (PostgreSQL, MySQL).  Guard explicitly until the
            # call-site is updated to include PKs in update payloads.
            if any("id" not in m for m in update_mappings):
                self.logger.warning(
                    "_bulk_upsert_user_ratings: update_mappings path requires the "
                    "'id' primary key in each payload but it is absent. "
                    "Skipping bulk_update_mappings to prevent silent data corruption. "
                    "Re-insert via bulk_save_objects instead."
                )
                missing_pk_objects = [
                    UserRating(**{k: v for k, v in m.items() if k != "id"})
                    for m in update_mappings
                ]
                work_session.bulk_save_objects(missing_pk_objects)
            else:
                work_session.bulk_update_mappings(UserRating, update_mappings)


def run_day1_ingestion_on_startup() -> dict[str, int]:
    """Startup hook: seed working.db users + baseline ratings/listen counts from active Plex accounts."""
    service = UserHistoryService()
    return service.sync_baseline_history()
