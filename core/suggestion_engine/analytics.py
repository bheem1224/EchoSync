"""Playback Analytics Aggregator for calculating listening trends and stale track metrics."""

from datetime import timedelta
from sqlalchemy import func
from core.tiered_logger import get_logger
from database.working_database import get_working_database, PlaybackHistory
from time_utils import utc_now

logger = get_logger("analytics")


class PlaybackAnalytics:
    """Aggregates playback history metrics for library hygiene and suggestions."""

    @classmethod
    def _is_empty(cls, session) -> bool:
        """Check if PlaybackHistory contains any records."""
        return session.query(PlaybackHistory.id).first() is None

    @classmethod
    def get_listen_count(cls, provider_item_id: str, days: int = 30) -> int:
        """Get the total scrobbles for a specific track in the last X days."""
        try:
            working_db = get_working_database()
            with working_db.session_scope() as session:
                if cls._is_empty(session):
                    logger.debug("No playback data available (PlaybackHistory is empty).")
                    return 0

                cutoff_date = utc_now() - timedelta(days=days)
                count = session.query(func.count(PlaybackHistory.id)).filter(
                    PlaybackHistory.provider_item_id == provider_item_id,
                    PlaybackHistory.listened_at >= cutoff_date
                ).scalar()

                return count or 0
        except Exception as e:
            logger.error(f"Error getting listen count for {provider_item_id}: {e}", exc_info=True)
            return 0

    @classmethod
    def get_trending_provider_ids(cls, days: int = 7, limit: int = 50) -> dict[str, int]:
        """Get a dictionary of {provider_item_id: count} for the most played tracks recently."""
        try:
            working_db = get_working_database()
            with working_db.session_scope() as session:
                if cls._is_empty(session):
                    logger.debug("No playback data available (PlaybackHistory is empty).")
                    return {}

                cutoff_date = utc_now() - timedelta(days=days)
                results = session.query(
                    PlaybackHistory.provider_item_id,
                    func.count(PlaybackHistory.id).label('play_count')
                ).filter(
                    PlaybackHistory.listened_at >= cutoff_date
                ).group_by(
                    PlaybackHistory.provider_item_id
                ).order_by(
                    func.count(PlaybackHistory.id).desc()
                ).limit(limit).all()

                return {str(row.provider_item_id): int(row.play_count) for row in results}
        except Exception as e:
            logger.error(f"Error getting trending provider IDs: {e}", exc_info=True)
            return {}

    @classmethod
    def get_stale_provider_ids(cls, inactive_days: int = 90) -> list[str]:
        """Get provider_item_ids that have > 0 all-time listens, but 0 listens in the last X days."""
        try:
            working_db = get_working_database()
            with working_db.session_scope() as session:
                if cls._is_empty(session):
                    logger.debug("No playback data available (PlaybackHistory is empty).")
                    return []

                cutoff_date = utc_now() - timedelta(days=inactive_days)

                # Get items with any listens
                all_time_listened_subq = session.query(
                    PlaybackHistory.provider_item_id
                ).group_by(PlaybackHistory.provider_item_id).subquery()

                # Get items listened to recently
                recently_listened_subq = session.query(
                    PlaybackHistory.provider_item_id
                ).filter(
                    PlaybackHistory.listened_at >= cutoff_date
                ).group_by(PlaybackHistory.provider_item_id).subquery()

                # Find the difference
                stale_results = session.query(
                    all_time_listened_subq.c.provider_item_id
                ).outerjoin(
                    recently_listened_subq,
                    all_time_listened_subq.c.provider_item_id == recently_listened_subq.c.provider_item_id
                ).filter(
                    recently_listened_subq.c.provider_item_id.is_(None)
                ).all()

                return [str(row.provider_item_id) for row in stale_results]
        except Exception as e:
            logger.error(f"Error getting stale provider IDs: {e}", exc_info=True)
            return []
