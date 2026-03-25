"""Consensus lifecycle for suggestion/deletion decisions.

Rules (from product intent):
- Ratings are stored as display stars (0.5-5.0) and mapped to 1-10 via stars_to_ten_point.
- 1   (0.5 stars): deletion candidate at month-end.
- 2   (1 star):   explicit upgrade request at week-end.
- 3-10 (1.5-5 stars): keep and feed preference model (opinion zone for suggestion engine).

The half-star is the sole delete signal.  One whole star is the explicit upgrade
signal, kept separate from the implicit upgrade logic that will be driven by the
suggestion engine.  Stars 1.5-5 are free for users to express how much they like
a track without triggering any lifecycle action.
"""

from typing import Dict, Any

from database.working_database import get_working_database, UserRating


def stars_to_ten_point(stars: float) -> int:
    """Map 0.5-5.0 stars to integer 1-10 scale."""
    bounded = max(0.5, min(5.0, float(stars)))
    return int(round(bounded * 2.0))


def calculate_consensus(sync_id: str) -> Dict[str, Any]:
    """Calculate lifecycle action for a track based on mapped consensus rating."""
    base_sync_id = sync_id.split('?')[0]

    db = get_working_database()
    with db.session_scope() as session:
        ratings_records = session.query(UserRating).filter(UserRating.sync_id == base_sync_id).all()

        if not ratings_records:
            return {"status": "KEEP", "action": "KEEP", "sync_id": base_sync_id}

        mapped_scores = [stars_to_ten_point(record.rating) for record in ratings_records]
        avg_score = sum(mapped_scores) / len(mapped_scores)

        # Follow the explicit lifecycle thresholds.
        # 0.5 star (internal 1): sole deletion signal.
        # 1 star (internal 2): explicit upgrade request.
        # 1.5-5 stars (internal 3-10): neutral opinion zone; feed suggestion engine.
        if avg_score <= 1.0:
            return {
                "status": "DELETE_CANDIDATE",
                "action": "DELETE_MONTH_END",
                "sync_id": base_sync_id,
                "score_10": avg_score,
                "user_ids": [record.user_id for record in ratings_records],
            }

        if avg_score <= 2.0:
            return {
                "status": "UPGRADE_CANDIDATE",
                "action": "UPGRADE_WEEK_END",
                "sync_id": base_sync_id,
                "score_10": avg_score,
                "user_ids": [record.user_id for record in ratings_records],
            }

        return {
            "status": "KEEP",
            "action": "KEEP_AND_FEED_PREFERENCE_MODEL",
            "sync_id": base_sync_id,
            "score_10": avg_score,
            "user_ids": [record.user_id for record in ratings_records],
        }
