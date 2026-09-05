from core.event_bus import event_bus as default_event_bus
from core.suggestion_engine.consensus import calculate_consensus, stars_to_ten_point
from core.suggestion_engine.deletion import apply_lifecycle_action
from core.tiered_logger import get_logger
from database.working_database import (
    Account,
    UserRating,
    UserTrackState,
    get_working_database,
)
from time_utils import utc_now

logger = get_logger("state_listener")


class StateListenerService:
    def __init__(self, event_bus=None, session_factory=None, engine=None):
        self.event_bus = event_bus or default_event_bus
        if session_factory:
            self.Session = session_factory
        else:
            self.Session = get_working_database().SessionLocal

    def subscribe(self):
        if hasattr(self.event_bus, "subscribe"):
            self.event_bus.subscribe("TRACK_RATED", self.handle_track_rated)
            self.event_bus.subscribe("TRACK_PLAYED", self.handle_track_played)

    def _resolve_account_id(self, session, provider_user_id, provider_name):
        provider_user_id = str(provider_user_id)
        user = (
            session.query(Account)
            .filter(
                Account.remote_account_id == provider_user_id, Account.plugin_id == 1
            )
            .first()
        )
        if not user:
            user = Account(
                username=f"{provider_name}_{provider_user_id}",
                remote_account_id=provider_user_id,
                plugin_id=1,
            )
            session.add(user)
            session.flush()
        return user.id

    def handle_track_rated(self, event_data: dict):
        sync_id = event_data.get("sync_id")
        data = event_data.get("data", {})
        rating = data.get("rating")
        provider_user_id = data.get("account_id") or data.get("user_id")
        provider_name = data.get("provider", "unknown")

        if not sync_id or rating is None or not provider_user_id:
            return

        with self.Session() as session:
            try:
                internal_account_id = self._resolve_account_id(
                    session, provider_user_id, provider_name
                )
                base_sync_id = sync_id.split("?")[0]

                existing = (
                    session.query(UserRating)
                    .filter(
                        UserRating.account_id == internal_account_id,
                        UserRating.sync_id == base_sync_id,
                    )
                    .first()
                )

                if existing:
                    existing.rating = float(rating)
                    existing.timestamp = utc_now()
                else:
                    new_rating = UserRating(
                        account_id=internal_account_id,
                        sync_id=base_sync_id,
                        rating=float(rating),
                        timestamp=utc_now(),
                    )
                    session.add(new_rating)
                session.commit()

                # Execute exact 10-point lifecycle policy.
                consensus = calculate_consensus(base_sync_id)
                apply_lifecycle_action(base_sync_id, consensus)

                # Sponsor action: if sponsor rated, remove from Suggestions for You playlist.
                self._handle_sponsor_rating_action(
                    session, base_sync_id, internal_account_id, float(rating)
                )
            except Exception as e:
                logger.error(f"Error in handle_track_rated: {e}", exc_info=True)
                session.rollback()

    def _handle_sponsor_rating_action(
        self, session, base_sync_id: str, account_id: int, rating_stars: float
    ) -> None:
        sponsor_state = (
            session.query(UserTrackState)
            .filter(
                UserTrackState.sync_id == base_sync_id,
                UserTrackState.sponsor_id == account_id,
            )
            .first()
        )

        if not sponsor_state:
            return

        # Mark as unlinked for sponsor-facing suggestion surfaces.
        sponsor_state.is_unlinked = True
        sponsor_state.updated_at = utc_now()
        session.commit()

        self.event_bus.publish(
            {
                "event": "SUGGESTION_PLAYLIST_REMOVE_INTENT",
                "sync_id": base_sync_id,
                "account_id": account_id,
                "playlist_name": "Suggestions for You",
                "rating_stars": rating_stars,
                "rating_10": stars_to_ten_point(rating_stars),
            }
        )

    def handle_track_played(self, event_data: dict):
        pass


def start_state_listener():
    listener = StateListenerService()
    listener.subscribe()
    return listener
