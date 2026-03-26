"""
User History Service for v2.1.0 Suggestion Engine baseline population.

Syncs historical play counts and ratings from providers into working.db,
indexed by deterministic sync_id generated from normalized track metadata.
"""

from typing import Optional, Dict, List, Set
import re
from core.tiered_logger import get_logger
from database.config_database import get_config_database
from database.working_database import get_working_database, UserRating, User, PlaybackHistory
from database.music_database import get_database as get_music_database, Track, Artist
from core.matching_engine.text_utils import generate_deterministic_id
from core.user_history import UserTrackInteraction
from sqlalchemy import tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from database.music_database import ExternalIdentifier
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
    
    def sync_baseline_history(self) -> Dict[str, int]:
        """
        Synchronize baseline user history from active media server to working.db.
        
        This should run after music_database.db has been populated with library metadata
        but before the Suggestion Engine starts making recommendations.
        
        Returns:
            Statistics dict with keys:
            - accounts_processed: Number of accounts synced
            - interactions_fetched: Total interactions received from provider
            - matches_found: Interactions successfully matched to local tracks
            - ratings_imported: UserRating records created
            - errors: List of error messages encountered
        """
        stats = {
            'users_synced': 0,
            'accounts_processed': 0,
            'interactions_fetched': 0,
            'matches_found': 0,
            'ratings_imported': 0,
            'listen_count_imported': 0,
            'errors': []
        }
        
        try:
            # Get all active Plex accounts (currently only Plex supports history fetching)
            plex_service_id = self.config_db.get_or_create_service_id('plex')
            accounts = self.config_db.get_accounts(service_id=plex_service_id, is_active=True)
            
            if not accounts:
                self.logger.info("No active Plex accounts found for history sync")
                return stats

            # Day-1 bootstrap: ensure all active Plex managed users exist before history sync.
            stats['users_synced'] = self.sync_active_plex_users_to_working_db(accounts)
            
            # Get Plex provider to call fetch_user_history()
            try:
                from core.provider import ProviderRegistry
                plex_provider = ProviderRegistry.create_instance('plex')
            except Exception as e:
                error_msg = f"Failed to create Plex provider instance: {e}"
                self.logger.error(error_msg)
                stats['errors'].append(error_msg)
                return stats
            
            # Check if provider supports history fetching
            if not hasattr(plex_provider, 'fetch_user_history'):
                error_msg = "Plex provider does not support fetch_user_history()"
                self.logger.error(error_msg)
                stats['errors'].append(error_msg)
                return stats
            
            # Sync history for each account
            for account in accounts:
                account_id = account['id']
                account_name = account.get('display_name') or account.get('account_name') or 'Unknown'
                
                try:
                    self.logger.info(f"Syncing history for account {account_name} (ID: {account_id})")
                    
                    # Fetch history from provider
                    interactions = plex_provider.fetch_user_history(account_id)
                    stats['interactions_fetched'] += len(interactions)
                    
                    if not interactions:
                        self.logger.info(f"No history items found for account {account_name}")
                        stats['accounts_processed'] += 1
                        continue
                    
                    # Get or create user in working_db
                    working_user = self._get_or_create_working_user(
                        account_id, 
                        account_name,
                        account.get('user_id'),
                        account.get('account_email')
                    )
                    
                    if not working_user:
                        error_msg = f"Failed to create working user for account {account_name}"
                        self.logger.error(error_msg)
                        stats['errors'].append(error_msg)
                        continue
                    
                    # Process each interaction
                    matched_count = self._process_interactions(
                        working_user.id,
                        interactions,
                        stats
                    )
                    
                    self.logger.info(
                        f"Completed history sync for {account_name}: "
                        f"{len(interactions)} interactions, {matched_count} matched to local tracks"
                    )
                    stats['accounts_processed'] += 1
                    stats['matches_found'] += matched_count
                    
                except Exception as e:
                    error_msg = f"Error syncing history for account {account_name}: {e}"
                    self.logger.error(error_msg, exc_info=True)
                    stats['errors'].append(error_msg)
        
        except Exception as e:
            error_msg = f"Fatal error in sync_baseline_history: {e}"
            self.logger.error(error_msg, exc_info=True)
            stats['errors'].append(error_msg)
        
        self.logger.info(f"User history sync complete: {stats}")
        return stats
    
    def _get_or_create_working_user(
        self,
        account_id: int,
        account_name: str,
        plex_user_id: Optional[str] = None,
        account_email: Optional[str] = None
    ) -> Optional[User]:
        """
        Get or create user record in working.db.
        
        Args:
            account_id: Config database account ID
            account_name: Display name for the user
            plex_user_id: Plex user ID (for linking)
            account_email: User's email address
            
        Returns:
            User object from working_db, or None if creation failed
        """
        try:
            with self.working_db.session_scope() as session:
                # Try to find existing user by provider_identifier
                if plex_user_id:
                    user = session.query(User).filter(
                        User.provider_identifier == plex_user_id
                    ).first()
                    if user:
                        return user
                
                # Try to find by username (account_name)
                user = session.query(User).filter(
                    User.username == account_name
                ).first()
                
                if user:
                    return user
                
                # Create new user
                user = User(
                    username=account_name,
                    provider_identifier=plex_user_id,
                    provider='plex'
                )
                session.add(user)
                session.commit()
                return user
        
        except Exception as e:
            self.logger.error(f"Failed to get/create working user: {e}", exc_info=True)
            return None

    def sync_active_plex_users_to_working_db(self, accounts: Optional[List[Dict]] = None) -> int:
        """Ensure all active Plex accounts in config.db exist in working.db users."""
        users_synced = 0
        try:
            if accounts is None:
                plex_service_id = self.config_db.get_or_create_service_id('plex')
                accounts = self.config_db.get_accounts(service_id=plex_service_id, is_active=True)

            for account in accounts or []:
                account_name = account.get('display_name') or account.get('account_name') or 'Unknown'
                user = self._get_or_create_working_user(
                    account_id=account.get('id'),
                    account_name=account_name,
                    plex_user_id=account.get('user_id'),
                    account_email=account.get('account_email'),
                )
                if user:
                    users_synced += 1
        except Exception as e:
            self.logger.error(f"Failed syncing active Plex users to working DB: {e}", exc_info=True)

        return users_synced
    
    def _process_interactions(
        self,
        user_id: int,
        interactions: List[UserTrackInteraction],
        stats: Dict
    ) -> int:
        """
        Process a list of user interactions and store ratings in working.db.
        
        For each interaction:
        1. Generate cache ID from artist|title
        2. Lookup track in music_database
        3. Extract or create sync_id
        4. Create/upsert UserRating record
        
        Args:
            user_id: Working database user ID
            interactions: List of UserTrackInteraction objects
            stats: Statistics dict to update
            
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

                    provider_item_ids: Set[str] = set()
                    for interaction in interactions:
                        raw_id = self._extract_provider_item_id(interaction)
                        if not raw_id:
                            continue
                        provider_item_ids.add(raw_id)
                        normalized_id = self._normalize_provider_item_id(raw_id)
                        if normalized_id:
                            provider_item_ids.add(normalized_id)

                    if not provider_item_ids:
                        self.logger.debug("No provider item IDs found in interactions; using text fallback only")

                    # Primary O(1) lookup via ExternalIdentifiers.
                    ext_idents = []
                    if provider_item_ids:
                        ext_idents = (
                            music_session.query(ExternalIdentifier, Track)
                            .join(Track, ExternalIdentifier.track_id == Track.id)
                            .filter(
                                ExternalIdentifier.provider_item_id.in_(list(provider_item_ids))
                            )
                            .all()
                        )

                    provider_id_to_track: Dict[str, Track] = {}
                    for ext_ident, track in ext_idents:
                        raw_ext_id = str(ext_ident.provider_item_id)
                        provider_id_to_track[raw_ext_id] = track
                        normalized_ext_id = self._normalize_provider_item_id(raw_ext_id)
                        if normalized_ext_id:
                            provider_id_to_track[normalized_ext_id] = track

                    # 1) Record playback history catch-up
                    playback_payloads = []
                    for interaction in interactions:
                        try:
                            extracted_id = self._extract_provider_item_id(interaction)
                            interaction_provider_id = self._normalize_provider_item_id(extracted_id) or extracted_id

                            user_record = work_session.query(User).filter_by(id=user_id).first()
                            playback_user_id = user_record.provider_identifier if user_record and user_record.provider_identifier else str(user_id)

                            if interaction_provider_id:
                                playback_payloads.append({
                                    "user_id": str(playback_user_id),
                                    "provider_item_id": str(interaction_provider_id),
                                    "listened_at": interaction.last_played_at or utc_now()
                                })
                        except Exception as e:
                            self.logger.warning(f"Error preparing playback history for interaction: {e}")

                    if playback_payloads:
                        if self.working_db.engine.dialect.name == 'sqlite':
                            insert_stmt = sqlite_insert(PlaybackHistory).values(playback_payloads)
                            upsert_stmt = insert_stmt.on_conflict_do_nothing(
                                index_elements=['user_id', 'provider_item_id', 'listened_at']
                            )
                            work_session.execute(upsert_stmt)

                    # 2) Continue with UserRatings matching
                    for interaction in interactions:
                        try:
                            extracted_id = self._extract_provider_item_id(interaction)
                            interaction_provider_id = self._normalize_provider_item_id(extracted_id) or extracted_id

                            if interaction_provider_id in provider_id_to_track:
                                track = provider_id_to_track[interaction_provider_id]
                                sync_id = f"ss:track:meta:{generate_deterministic_id(track.artist.name, track.title)}"
                                interaction_records.append({
                                    "interaction": interaction,
                                    "sync_id": sync_id,
                                    "matched_by_id": True,
                                })
                                continue

                            if interaction_provider_id and interaction_provider_id.startswith('ss:track:meta:'):
                                interaction_records.append({
                                    "interaction": interaction,
                                    "sync_id": interaction_provider_id.split('?')[0],
                                    "matched_by_id": True,
                                })
                                continue

                            # Fallback: text tuple lookup only for rows unmatched by ExternalIdentifier.
                            pair = (interaction.artist_name, interaction.track_title)
                            unique_pairs.add(pair)
                            interaction_records.append({
                                "interaction": interaction,
                                "pair": pair,
                                "matched_by_id": False,
                            })

                        except Exception as e:
                            self.logger.warning(
                                f"Error preparing interaction {interaction.artist_name} - {interaction.track_title}: {e}"
                            )

                    if not interaction_records:
                        return 0

                    matched_pairs = set()
                    pair_to_track: Dict[tuple, Track] = {}
                    if unique_pairs:
                        matched_tracks = (
                            music_session.query(Track)
                            .join(Track.artist)
                            .filter(tuple_(Artist.name, Track.title).in_(list(unique_pairs)))
                            .all()
                        )
                        matched_pairs = {(track.artist.name, track.title) for track in matched_tracks}
                        pair_to_track = {(track.artist.name, track.title): track for track in matched_tracks}

                    rating_payload_by_sync_id: Dict[str, Dict[str, object]] = {}

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
                            sync_id = f"ss:track:meta:{generate_deterministic_id(matched_track.artist.name, matched_track.title)}"

                        play_count = int(getattr(interaction, 'play_count', 0) or 0)
                        if interaction.rating is None and play_count <= 0:
                            continue

                        matched_count += 1
                        rating_value = float(interaction.rating) if interaction.rating is not None else None
                        rating_payload_by_sync_id[sync_id] = {
                            "user_id": user_id,
                            "sync_id": sync_id,
                            "rating": rating_value,
                            "play_count": play_count,
                            "timestamp": utc_now(),
                        }

                        if interaction.rating is not None:
                            stats['ratings_imported'] += 1
                        stats['listen_count_imported'] += play_count

                    if rating_payload_by_sync_id:
                        self._bulk_upsert_user_ratings(
                            work_session,
                            list(rating_payload_by_sync_id.values()),
                        )

        except Exception as e:
            self.logger.error(f"Error in _process_interactions: {e}", exc_info=True)

        return matched_count

    def _extract_provider_item_id(self, interaction: UserTrackInteraction) -> str:
        """Extract provider item ID from current and legacy interaction fields."""
        direct_id = str(getattr(interaction, 'provider_item_id', '') or '').strip()
        if direct_id:
            return direct_id

        identifiers = getattr(interaction, 'identifiers', None)
        if isinstance(identifiers, dict):
            # Iterate all known provider keys; 'plex' is kept for legacy dict shapes
            for key in (getattr(interaction, 'provider', None), 'plex', 'jellyfin', 'navidrome'):
                if key:
                    provider_id = str(identifiers.get(key, '') or '').strip()
                    if provider_id:
                        return provider_id

        source_item_id = str(getattr(interaction, 'source_item_id', '') or '').strip()
        if source_item_id:
            return source_item_id

        return ''

    def _normalize_provider_item_id(self, provider_item_id: Optional[str]) -> str:
        """Normalize provider item IDs for robust reverse lookups.

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

    def _bulk_upsert_user_ratings(self, work_session, rating_payloads: List[Dict[str, object]]) -> None:
        """Write matched user ratings in a single bulk transaction."""
        if not rating_payloads:
            return

        if self.working_db.engine.dialect.name == 'sqlite':
            # Backward compatibility: some existing working.db files have
            # user_ratings.rating declared NOT NULL. Listen-only rows (rating=None)
            # would fail inserts in that schema, so coerce missing ratings to 0.0.
            # This preserves listen_count ingestion until schema migration is applied.
            try:
                needs_non_null_rating = False
                with self.working_db.engine.connect() as conn:
                    pragma_rows = conn.exec_driver_sql("PRAGMA table_info('user_ratings')").fetchall()
                    for row in pragma_rows:
                        col_name = str(row[1]) if len(row) > 1 else ""
                        not_null_flag = int(row[3]) if len(row) > 3 and row[3] is not None else 0
                        if col_name == 'rating' and not_null_flag == 1:
                            needs_non_null_rating = True
                            break

                if needs_non_null_rating:
                    adjusted_payloads = []
                    for payload in rating_payloads:
                        if payload.get('rating') is None:
                            patched = dict(payload)
                            patched['rating'] = 0.0
                            adjusted_payloads.append(patched)
                        else:
                            adjusted_payloads.append(payload)
                    rating_payloads = adjusted_payloads
            except Exception:
                # Best-effort compatibility guard; continue with original payloads.
                pass

            insert_stmt = sqlite_insert(UserRating).values(rating_payloads)
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['user_id', 'sync_id'],
                set_={
                    'rating': insert_stmt.excluded.rating,
                    'play_count': insert_stmt.excluded.play_count,
                    'timestamp': insert_stmt.excluded.timestamp,
                }
            )
            work_session.execute(upsert_stmt)
            return

        sync_ids = [payload['sync_id'] for payload in rating_payloads]
        existing_sync_ids = {
            sync_id
            for (sync_id,) in work_session.query(UserRating.sync_id).filter(
                UserRating.user_id == rating_payloads[0]['user_id'],
                UserRating.sync_id.in_(sync_ids),
            ).all()
        }

        new_objects = []
        update_mappings = []
        for payload in rating_payloads:
            if payload['sync_id'] in existing_sync_ids:
                update_mappings.append(payload)
            else:
                new_objects.append(UserRating(**payload))

        if new_objects:
            work_session.bulk_save_objects(new_objects)
        if update_mappings:
            work_session.bulk_update_mappings(UserRating, update_mappings)


def run_day1_ingestion_on_startup() -> Dict[str, int]:
    """Startup hook: seed working.db users + baseline ratings/listen counts from active Plex accounts."""
    service = UserHistoryService()
    return service.sync_baseline_history()
