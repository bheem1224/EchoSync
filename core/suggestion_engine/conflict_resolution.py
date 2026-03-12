"""
Conflict resolution rules engine for when users disagree on a track.
"""

from typing import List
from database.music_database import UserRating
from core.tiered_logger import get_logger

logger = get_logger("conflict_resolution")

def resolve_conflict(ratings: List[UserRating]) -> bool:
    """
    Stub rules engine dictating what happens when users disagree on a track.
    Returns True if the track should be kept (e.g., someone really likes it),
    False if it should be removed.

    Currently a placeholder that defaults to keeping the track if any user has rated it.
    """
    if not ratings:
        return False

    has_rating = any(r.rating is not None for r in ratings)
    logger.debug(f"Conflict resolution (stub): Keep track? {has_rating}")
    return has_rating
