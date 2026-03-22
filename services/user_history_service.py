"""
User History Service for v2.1.0 Suggestion Engine baseline population.

Syncs historical play counts and ratings from providers into working.db,
indexed by deterministic sync_id generated from normalized track metadata.
"""

from typing import Optional, Dict, List
from core.tiered_logger import get_logger
from database.config_database import get_config_database
from database.working_database import get_working_database, UserRating, User
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
                # Try to find existing user by plex_id
                if plex_user_id:
                    user = session.query(User).filter(
                        User.plex_id == plex_user_id
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
                    plex_id=plex_user_id,
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

                    provider_item_ids = [interaction.provider_item_id for interaction in interactions if interaction.provider_item_id]

                    # O(1) match via ExternalIdentifiers
                    ext_idents = music_session.query(ExternalIdentifier, Track.title, Artist.name).join(
                        Track, ExternalIdentifier.track_id == Track.id
                    ).join(
                        Artist, Track.artist_id == Artist.id
                    ).filter(
                        ExternalIdentifier.provider_source == 'plex',
                        ExternalIdentifier.provider_item_id.in_(provider_item_ids)
                    ).all()

                    plex_id_to_track_info = {
                        ext_ident.provider_item_id: (artist_name, track_title)
                        for ext_ident, track_title, artist_name in ext_idents
                    }

                    for interaction in interactions:
                        try:
                            # O(1) lookup via identifiers
                            if interaction.provider_item_id in plex_id_to_track_info:
                                artist_name, track_title = plex_id_to_track_info[interaction.provider_item_id]
                                sync_id = f"ss:track:meta:{generate_deterministic_id(artist_name, track_title)}"
                            else:
                                if interaction.provider_item_id and interaction.provider_item_id.startswith('ss:track:meta:'):
                                    sync_id = interaction.provider_item_id.split('?')[0]
                                    interaction_records.append({
                                        "interaction": interaction,
                                        "sync_id": sync_id,
                                    })
                                else:
                                    # Always fallback to text matching if not matched by O(1) ID or fat pointer URI
                                    sync_id = f"ss:track:meta:{generate_deterministic_id(interaction.artist_name, interaction.track_title)}"
                                    pair = (interaction.artist_name, interaction.track_title)
                                    unique_pairs.add(pair)
                                    interaction_records.append({
                                        "interaction": interaction,
                                        "pair": pair,
                                        "sync_id": sync_id,
                                        "matched_by_id": False
                                    })
                                    continue

                            interaction_records.append({
                                "interaction": interaction,
                                "sync_id": sync_id,
                                "matched_by_id": True
                            })
                        except Exception as e:
                            self.logger.warning(
                                f"Error preparing interaction {interaction.artist_name} - {interaction.track_title}: {e}"
                            )

                    if not interaction_records:
                        return 0

                    matched_pairs = set()
                    if unique_pairs:
                        matched_tracks = music_session.query(Track).join(Track.artist).filter(
                            tuple_(Artist.name, Track.title).in_(list(unique_pairs))
                        ).all()
                        matched_pairs = {(track.artist.name, track.title) for track in matched_tracks}

                    rating_payload_by_sync_id: Dict[str, Dict[str, object]] = {}

                    for record in interaction_records:
                        interaction = record["interaction"]
                        # Validate text fallback matches, skip if not matched by ID and not in matched_pairs
                        if not record.get("matched_by_id") and record.get("pair") not in matched_pairs:
                            self.logger.debug(
                                f"No track found for {interaction.artist_name} - {interaction.track_title}"
                            )
                            continue

                        # Store Day-1 historical context when a real rating exists OR listen count exists.
                        play_count = int(getattr(interaction, 'play_count', 0) or 0)
                        if interaction.rating is None and play_count <= 0:
                            continue

                        matched_count += 1
                        rating_value = float(interaction.rating) if interaction.rating is not None else None
                        rating_payload_by_sync_id[record["sync_id"]] = {
                            "user_id": user_id,
                            "sync_id": record["sync_id"],
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

    def _bulk_upsert_user_ratings(self, work_session, rating_payloads: List[Dict[str, object]]) -> None:
        """Write matched user ratings in a single bulk transaction."""
        if not rating_payloads:
            return

        if self.working_db.engine.dialect.name == 'sqlite':
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
