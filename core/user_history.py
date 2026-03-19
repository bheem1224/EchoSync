"""
User History data structures and provider interface.

Standardized representation of user track interactions from various providers,
suitable for populating the v2.1.0 Suggestion Engine.
"""

from dataclasses import dataclass
from typing import Optional, List, Protocol
from datetime import datetime


@dataclass
class UserTrackInteraction:
    """
    Standardized user track interaction data from any provider.
    
    Fields represent provider-agnostic metadata for a user's interaction with a track.
    """
    provider_item_id: str  # Provider's unique track ID (e.g., Plex ratingKey, MusicBrainz MBID)
    artist_name: str  # Artist name for cache ID generation
    track_title: str  # Track title for cache ID generation
    play_count: int = 0  # How many times user has played this track
    rating: Optional[float] = None  # User's rating (1-5 stars, or provider-specific scale)
    last_played_at: Optional[datetime] = None  # When the track was last played


class UserHistoryProvider(Protocol):
    """
    Protocol for providers supporting user history fetching.
    
    Providers that can retrieve user's play history, ratings, etc. must implement
    fetch_user_history() to conform to this interface.
    """
    
    def fetch_user_history(self, account_id: int) -> List[UserTrackInteraction]:
        """
        Fetch user's historical track interactions from the provider.
        
        Args:
            account_id: Database account ID for the user
            
        Returns:
            List of UserTrackInteraction objects representing user's history
            
        Raises:
            RuntimeError: If unable to fetch history (auth failed, API error, etc.)
        """
        ...
