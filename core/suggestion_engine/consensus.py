"""
Core mathematical logic to calculate track consensus.
"""

from typing import List
from database.music_database import UserRating
from core.tiered_logger import get_logger

logger = get_logger("consensus")

def calculate_consensus_rating(ratings: List[UserRating]) -> float:
    """
    Calculates the consensus rating for a track based on multiple user ratings.
    Currently implements a simple average of all 0-10 user ratings.
    In the future, this will be upgraded to a weighted formula factoring in play_count and sponsor weight.
    """
    if not ratings:
        return 0.0

    valid_ratings = [r.rating for r in ratings if r.rating is not None]

    if not valid_ratings:
        return 0.0

    average_rating = sum(valid_ratings) / len(valid_ratings)
    logger.debug(f"Calculated average consensus rating: {average_rating}")
    return average_rating
