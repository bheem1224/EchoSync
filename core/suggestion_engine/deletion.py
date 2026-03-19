"""
Deletion Gate for the Suggestion Engine.
Evaluates rules to determine whether a rejected track should be
soft deleted (unlinked for specific users) or hard deleted (physically removed).
"""

from typing import List
from database.working_database import get_working_database, UserTrackState, UserRating
from core.event_bus import event_bus


def should_delete_file(sync_id: str, downvoters: List[int]) -> None:
    """
    Evaluates deletion rules for a REJECTED track and publishes the appropriate intent.

    Args:
        sync_id: The full sync_id URI (or base sync_id). We strip query params to check the DB.
        downvoters: List of user IDs who rated the track < 4.0.
    """
    base_sync_id = sync_id.split('?')[0]

    db = get_working_database()
    with db.session_scope() as session:
        # Get the UserTrackState for this track to find the sponsor
        # We assume the first sponsor found is the main sponsor, or we check any user track state
        # that has a sponsor_id set. Let's look for a record with sponsor_id.
        track_states = session.query(UserTrackState).filter(
            UserTrackState.sync_id == base_sync_id,
            UserTrackState.sponsor_id.isnot(None)
        ).all()

        # If there's no explicitly recorded sponsor, we assume Soft Delete to be safe,
        # or we could attempt to infer. Let's assume we have a sponsor_id.
        sponsor_id = None
        if track_states:
             # Just use the first one's sponsor_id as the primary sponsor for this track
             sponsor_id = track_states[0].sponsor_id

        # If we can't find a sponsor_id, we default to Soft Delete to avoid accidental data loss.
        # But if we do, we check the sponsor's rating.
        sponsor_rated_badly = False

        if sponsor_id is not None:
             # Check if sponsor rated it < 4.0
             sponsor_rating_record = session.query(UserRating).filter(
                 UserRating.sync_id == base_sync_id,
                 UserRating.user_id == sponsor_id
             ).first()

             if sponsor_rating_record and sponsor_rating_record.rating < 4.0:
                 sponsor_rated_badly = True

        # Rule B: Hard Delete (Sponsor also rated it < 4.0)
        if sponsor_rated_badly:
             event_bus.publish({
                 "event": "HARD_DELETE_INTENT",
                 "sync_id": sync_id
             })
        else:
             # Rule A: Soft Delete (Sponsor hasn't rated, or rated >= 4.0)
             event_bus.publish({
                 "event": "SOFT_UNLINK_INTENT",
                 "sync_id": sync_id,
                 "downvoters": downvoters
             })
