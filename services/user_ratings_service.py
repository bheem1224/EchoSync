"""
Service for processing incoming user ratings and scrobbles.
Upserts data into the `user_ratings` table, mapped correctly per source and user.
"""

from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from database.music_database import get_database, Track, Artist, User, UserRating
from core.tiered_logger import get_logger
from datetime import datetime

logger = get_logger("user_ratings_service")

class UserRatingsService:
    def __init__(self):
        self.db = get_database()

    def _get_or_create_user(self, session: Session, user_identifier: str, source: str) -> int:
        """
        Get or create a User entry for the given external user_identifier and source.
        This ensures that we can use user_id (int) in the UserRating table while storing
        the provider's identifier in `username` for mapping.
        """
        internal_username = f"{source}_{user_identifier}"

        user = session.scalars(
            select(User).where(User.username == internal_username)
        ).first()

        if user:
            return user.id

        new_user = User(
            username=internal_username,
            provider=source
        )
        session.add(new_user)
        session.flush() # flush to get the ID
        return new_user.id

    def _get_track_id(self, session: Session, artist_name: str, track_title: str) -> Optional[int]:
        """Look up internal track_id by artist name and track title."""
        # We can use the fuzzy matcher from check_track_exists, or simple exact match.
        # Requirements state "Look up the internal track_id based on artist/title".
        # We will use check_track_exists for robustness.
        track, score = self.db.check_track_exists(title=track_title, artist=artist_name, confidence_threshold=0.8)
        if track:
            return track.id
        return None

    def update_rating(self, artist_name: str, track_title: str, rating: float, source: str, user_identifier: str) -> None:
        """
        Updates the rating for a specific track, user, and source.
        """
        with self.db.session_scope() as session:
            track_id = self._get_track_id(session, artist_name, track_title)
            if not track_id:
                logger.debug(f"Track not found locally: {artist_name} - {track_title}. Ignoring rating payload.")
                return

            user_id = self._get_or_create_user(session, user_identifier, source)

            user_rating = session.scalars(
                select(UserRating).where(
                    and_(
                        UserRating.track_id == track_id,
                        UserRating.user_id == user_id,
                        UserRating.source == source
                    )
                )
            ).first()

            if user_rating:
                user_rating.rating = float(rating)
                user_rating.timestamp = datetime.utcnow()
            else:
                user_rating = UserRating(
                    user_id=user_id,
                    track_id=track_id,
                    source=source,
                    rating=float(rating),
                    play_count=0
                )
                session.add(user_rating)

            logger.info(f"Updated rating for {artist_name} - {track_title} to {rating} for user {user_identifier} ({source})")

    def increment_play_count(self, artist_name: str, track_title: str, source: str, user_identifier: str) -> None:
        """
        Increments the play count for a specific track, user, and source.
        """
        with self.db.session_scope() as session:
            track_id = self._get_track_id(session, artist_name, track_title)
            if not track_id:
                logger.debug(f"Track not found locally: {artist_name} - {track_title}. Ignoring scrobble payload.")
                return

            user_id = self._get_or_create_user(session, user_identifier, source)

            user_rating = session.scalars(
                select(UserRating).where(
                    and_(
                        UserRating.track_id == track_id,
                        UserRating.user_id == user_id,
                        UserRating.source == source
                    )
                )
            ).first()

            if user_rating:
                user_rating.play_count = (user_rating.play_count or 0) + 1
                user_rating.timestamp = datetime.utcnow()
            else:
                user_rating = UserRating(
                    user_id=user_id,
                    track_id=track_id,
                    source=source,
                    play_count=1,
                    rating=None # or 0.0 depending on preference
                )
                session.add(user_rating)

            logger.info(f"Incremented play count for {artist_name} - {track_title} for user {user_identifier} ({source})")

    def set_play_count(self, artist_name: str, track_title: str, play_count: int, source: str, user_identifier: str) -> None:
        """
        Sets the absolute play count for a specific track, user, and source.
        Useful for polling adapters (like Navidrome) that return total playCount rather than incremental scrobbles.
        """
        with self.db.session_scope() as session:
            track_id = self._get_track_id(session, artist_name, track_title)
            if not track_id:
                logger.debug(f"Track not found locally: {artist_name} - {track_title}. Ignoring play_count payload.")
                return

            user_id = self._get_or_create_user(session, user_identifier, source)

            user_rating = session.scalars(
                select(UserRating).where(
                    and_(
                        UserRating.track_id == track_id,
                        UserRating.user_id == user_id,
                        UserRating.source == source
                    )
                )
            ).first()

            if user_rating:
                user_rating.play_count = play_count
                user_rating.timestamp = datetime.utcnow()
            else:
                user_rating = UserRating(
                    user_id=user_id,
                    track_id=track_id,
                    source=source,
                    play_count=play_count,
                    rating=None
                )
                session.add(user_rating)

            logger.info(f"Set play count to {play_count} for {artist_name} - {track_title} for user {user_identifier} ({source})")
