from pathlib import Path

from database.working_database import WorkingDatabase, User, UserTrackState, UserRating
from services.state_listener import StateListenerService


class _Bus:
    def __init__(self):
        self.events = []

    def subscribe(self, *_args, **_kwargs):
        return None

    def publish(self, payload):
        self.events.append(payload)


def _build_working_db(tmp_path: Path) -> WorkingDatabase:
    db = WorkingDatabase(str(tmp_path / "working_state_listener.db"))
    db.create_all()
    return db


def test_sponsor_rating_removes_from_suggestions_playlist(tmp_path, monkeypatch):
    db = _build_working_db(tmp_path)
    bus = _Bus()

    # Patch lifecycle modules to use this isolated DB.
    from core.suggestion_engine import consensus as consensus_mod
    from core.suggestion_engine import deletion as deletion_mod
    monkeypatch.setattr(consensus_mod, "get_working_database", lambda: db)
    monkeypatch.setattr(deletion_mod, "get_working_database", lambda: db)
    monkeypatch.setattr(deletion_mod, "event_bus", bus)

    base_sync_id = "ss:track:meta:sponsor-track"

    with db.session_scope() as session:
        user = User(username="plex_42", provider_identifier="42", provider="plex")
        session.add(user)
        session.flush()

        session.add(
            UserTrackState(
                user_id=user.id,
                sync_id=base_sync_id,
                sponsor_id=user.id,
            )
        )

    listener = StateListenerService(event_bus=bus, session_factory=db.SessionLocal)

    listener.handle_track_rated(
        {
            "event": "TRACK_RATED",
            "sync_id": base_sync_id + "?dur=200000",
            "data": {
                "rating": 4.0,
                "user_id": "42",
                "provider": "plex",
            },
        }
    )

    with db.session_scope() as session:
        rating = session.query(UserRating).filter(UserRating.sync_id == base_sync_id).first()
        state = session.query(UserTrackState).filter(UserTrackState.sync_id == base_sync_id).first()

    assert rating is not None
    assert rating.rating == 4.0
    assert state is not None
    assert state.is_unlinked is True

    suggestion_events = [e for e in bus.events if e.get("event") == "SUGGESTION_PLAYLIST_REMOVE_INTENT"]
    assert len(suggestion_events) == 1
    assert suggestion_events[0]["playlist_name"] == "Suggestions for You"
    assert suggestion_events[0]["sync_id"] == base_sync_id
