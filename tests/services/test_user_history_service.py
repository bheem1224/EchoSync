from services.user_history_service import UserHistoryService
from core.user_history import UserTrackInteraction
from core.matching_engine.text_utils import generate_deterministic_id
from database.music_database import Artist, Track
from database.working_database import User, UserRating


def test_process_interactions_bulk_upserts_existing_and_new_ratings(mock_db, mock_work_db):
    service = UserHistoryService()
    service.music_db = mock_db
    service.working_db = mock_work_db

    with mock_db.session_scope() as music_session:
        artist = Artist(name="Artist A")
        music_session.add(artist)
        music_session.flush()
        music_session.add_all([
            Track(title="Song One", artist=artist),
            Track(title="Song Two", artist=artist),
        ])

    with mock_work_db.session_scope() as work_session:
        user = User(username="listener", provider="plex")
        work_session.add(user)
        work_session.flush()
        existing_sync_id = f"ss:track:meta:{generate_deterministic_id('Artist A', 'Song One')}"
        work_session.add(UserRating(user_id=user.id, sync_id=existing_sync_id, rating=2.0))
        user_id = user.id

    stats = {"ratings_imported": 0}
    interactions = [
        UserTrackInteraction(provider_item_id="1", artist_name="Artist A", track_title="Song One", rating=4.5),
        UserTrackInteraction(provider_item_id="2", artist_name="Artist A", track_title="Song Two", rating=3.0),
        UserTrackInteraction(provider_item_id="3", artist_name="Artist A", track_title="Missing Song", rating=5.0),
    ]

    matched_count = service._process_interactions(user_id, interactions, stats)

    assert matched_count == 2
    assert stats["ratings_imported"] == 2

    with mock_work_db.session_scope() as work_session:
        ratings = {
            rating.sync_id: rating.rating
            for rating in work_session.query(UserRating).filter(UserRating.user_id == user_id).all()
        }

    assert ratings[existing_sync_id] == 4.5
    new_sync_id = f"ss:track:meta:{generate_deterministic_id('Artist A', 'Song Two')}"
    assert ratings[new_sync_id] == 3.0
    assert len(ratings) == 2