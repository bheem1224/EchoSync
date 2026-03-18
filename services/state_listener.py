from core.event_bus import event_bus as default_event_bus
from core.tiered_logger import get_logger
from database.working_database import get_working_database, UserRating, UserTrackState, User
from datetime import datetime

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

    def _resolve_user_id(self, session, provider_user_id, provider_name):
        provider_user_id = str(provider_user_id)
        user = session.query(User).filter(
            User.plex_id == provider_user_id,
            User.provider == provider_name
        ).first()
        if not user:
            user = User(
                username=f"{provider_name}_{provider_user_id}",
                plex_id=provider_user_id,
                provider=provider_name
            )
            session.add(user)
            session.flush()
        return user.id

    def handle_track_rated(self, event_data: dict):
        sync_id = event_data.get("sync_id")
        data = event_data.get("data", {})
        rating = data.get("rating")
        provider_user_id = data.get("user_id")
        provider_name = data.get("provider", "unknown")

        if not sync_id or rating is None or not provider_user_id:
            return

        with self.Session() as session:
            try:
                internal_user_id = self._resolve_user_id(session, provider_user_id, provider_name)

                existing = session.query(UserRating).filter(
                    UserRating.user_id == internal_user_id,
                    UserRating.sync_id == sync_id
                ).first()

                if existing:
                    existing.rating = float(rating)
                    existing.timestamp = datetime.utcnow()
                else:
                    new_rating = UserRating(
                        user_id=internal_user_id,
                        sync_id=sync_id,
                        rating=float(rating),
                        timestamp=datetime.utcnow()
                    )
                    session.add(new_rating)
                session.commit()
            except Exception as e:
                session.rollback()

    def handle_track_played(self, event_data: dict):
        pass

def start_state_listener():
    listener = StateListenerService()
    listener.subscribe()
    return listener
