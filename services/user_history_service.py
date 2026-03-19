"""
User History Service for v2.1.0 Suggestion Engine baseline population.

Syncs historical play counts and ratings from providers into working.db,
indexed by deterministic sync_id generated from normalized track metadata.
"""

from typing import Optional, Dict, List
from core.tiered_logger import get_logger
from core.settings import config_manager
from database.config_database import get_config_database
from database.working_database import get_working_database, UserRating, User
from database.music_database import get_database as get_music_database, Track, Artist
from core.matching_engine.text_utils import generate_deterministic_id
from core.user_history import UserTrackInteraction
from datetime import datetime
import base64

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
            'accounts_processed': 0,
            'interactions_fetched': 0,
            'matches_found': 0,
            'ratings_imported': 0,
            'errors': []
        }
        
        try:
            # Get all active Plex accounts (currently only Plex supports history fetching)
            plex_service_id = self.config_db.get_or_create_service_id('plex')
            accounts = self.config_db.get_accounts(service_id=plex_service_id, is_active=True)
            
            if not accounts:
                self.logger.info("No active Plex accounts found for history sync")
                return stats
            
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
        
        try:
            with self.music_db.session_scope() as music_session:
                with self.working_db.session_scope() as work_session:
                    
                    for interaction in interactions:
                        try:
                            # Generate base sync_id from normalized artist|title
                            base_sync_id = generate_deterministic_id(
                                interaction.artist_name,
                                interaction.track_title
                            )
                            
                            # Format as full sync_id
                            sync_id = f"ss:track:meta:{base_sync_id}"
                            
                            # Try to find track in music_database
                            track = music_session.query(Track).join(
                                Track.artist
                            ).filter(
                                Artist.name == interaction.artist_name,
                                Track.title == interaction.track_title
                            ).first()
                            
                            if track:
                                # Store rating in working.db
                                # Rating scale: use provider rating directly
                                # If we have a rating, convert to 1-5 scale (assuming provider uses this)
                                if interaction.rating is not None:
                                    rating_value = float(interaction.rating)
                                    
                                    # Create or update UserRating
                                    existing_rating = work_session.query(UserRating).filter(
                                        UserRating.user_id == user_id,
                                        UserRating.sync_id == sync_id
                                    ).first()
                                    
                                    if existing_rating:
                                        # Update existing rating with new value
                                        existing_rating.rating = rating_value
                                    else:
                                        # Create new rating record
                                        rating = UserRating(
                                            user_id=user_id,
                                            sync_id=sync_id,
                                            rating=rating_value
                                        )
                                        work_session.add(rating)
                                    
                                    stats['ratings_imported'] += 1
                                    matched_count += 1
                            else:
                                self.logger.debug(
                                    f"No track found for {interaction.artist_name} - {interaction.track_title}"
                                )
                        
                        except Exception as e:
                            self.logger.warning(
                                f"Error processing interaction {interaction.artist_name} - {interaction.track_title}: {e}"
                            )
        
        except Exception as e:
            self.logger.error(f"Error in _process_interactions: {e}", exc_info=True)
        
        return matched_count
