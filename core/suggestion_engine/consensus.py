"""
Consensus Calculator for the Suggestion Engine.
Reads all ratings for a given sync_id from the user_ratings table in working.db.
Calculates the global average and decides if a track should be rejected based on rules.
"""

from typing import Dict, Any
from database.working_database import get_working_database, UserRating


def calculate_consensus(sync_id: str) -> Dict[str, Any]:
    """
    Reads ratings for a given sync_id, calculates the global average,
    and returns REJECTED status if there are at least 2 ratings and the average is < 4.0.
    """
    # Important: Remove query parameters from the sync_id to get the base identity
    base_sync_id = sync_id.split('?')[0]

    db = get_working_database()
    with db.session_scope() as session:
        # Get all ratings for this base_sync_id
        ratings_records = session.query(UserRating).filter(UserRating.sync_id == base_sync_id).all()

        if not ratings_records:
            return {"status": "KEEP"}

        total_rating = 0.0
        downvoters = []

        for record in ratings_records:
            total_rating += record.rating
            if record.rating < 4.0:
                downvoters.append(record.user_id)

        avg_rating = total_rating / len(ratings_records)

        # Rule: At least 2 ratings, and average falls below 4.0
        if len(ratings_records) >= 2 and avg_rating < 4.0:
            return {
                "status": "REJECTED",
                "sync_id": base_sync_id,
                "downvoters": downvoters
            }

        return {"status": "KEEP"}
