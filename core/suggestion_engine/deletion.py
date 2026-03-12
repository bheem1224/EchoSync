"""
Handles deletion logic and enforces the primary rule:
Never delete a file if the sponsor_id has not yet rated it.
Also implements Soft Delete.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from database.music_database import Track, UserTrackState, UserRating
from core.tiered_logger import get_logger

logger = get_logger("deletion")

def should_delete_file(session: Session, track_id: int) -> bool:
    """
    Never delete a file if the sponsor_id has not yet rated it.
    Returns True if safe to hard delete.
    """
    track = session.scalars(select(Track).where(Track.id == track_id)).first()

    if not track:
        logger.warning(f"Deletion guard: Track {track_id} not found.")
        return False

    if track.sponsor_id is None:
        logger.debug(f"Deletion guard: Track {track_id} has no sponsor. Safe to delete.")
        return True

    # Check if the sponsor has rated the track
    sponsor_rating = session.scalars(
        select(UserRating).where(
            and_(
                UserRating.track_id == track_id,
                UserRating.user_id == track.sponsor_id
            )
        )
    ).first()

    if sponsor_rating is None or sponsor_rating.rating is None:
        logger.info(f"Deletion guard: Sponsor {track.sponsor_id} has not rated track {track_id}. Cannot hard delete.")
        return False

    return True

def soft_delete_track(session: Session, track_id: int, user_id: int) -> bool:
    """
    Unlinks a track from a user's library without deleting the physical file.
    The Sync Service will read this table to issue API calls (e.g., Plex/Navidrome removal).
    """
    state = session.scalars(
        select(UserTrackState).where(
            and_(
                UserTrackState.track_id == track_id,
                UserTrackState.user_id == user_id
            )
        )
    ).first()

    if state:
        if state.is_unlinked:
            logger.debug(f"Track {track_id} already soft deleted for user {user_id}.")
            return True
        state.is_unlinked = True
    else:
        new_state = UserTrackState(
            track_id=track_id,
            user_id=user_id,
            is_unlinked=True
        )
        session.add(new_state)

    logger.info(f"Soft deleted track {track_id} for user {user_id}.")
    return True
