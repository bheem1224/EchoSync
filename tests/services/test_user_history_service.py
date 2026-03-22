from services.user_history_service import UserHistoryService
from core.user_history import UserTrackInteraction
from core.matching_engine.text_utils import generate_deterministic_id
from database.music_database import Artist, Track
from database.working_database import User, UserRating


def test_sync_active_plex_users_to_working_db_creates_day1_users(mock_work_db):
    service = UserHistoryService()
    service.working_db = mock_work_db

    accounts = [
        {
            "id": 1,
            "display_name": "Kid A",
            "account_name": "Kid A",
            "user_id": "plex-user-1",
            "account_email": "kida@example.com",
        },
        {
            "id": 2,
            "display_name": "Kid B",
            "account_name": "Kid B",
            "user_id": "plex-user-2",
            "account_email": "kidb@example.com",
        },
    ]

    synced = service.sync_active_plex_users_to_working_db(accounts)
    assert synced == 2

    with mock_work_db.session_scope() as work_session:
        users = work_session.query(User).order_by(User.username).all()
        assert [u.username for u in users] == ["Kid A", "Kid B"]
        assert [u.plex_id for u in users] == ["plex-user-1", "plex-user-2"]


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
        UserTrackInteraction(provider_item_id="1", artist_name="Artist A", track_title="Song One", rating=4.5, play_count=7),
        UserTrackInteraction(provider_item_id="2", artist_name="Artist A", track_title="Song Two", rating=3.0, play_count=3),
        UserTrackInteraction(provider_item_id="3", artist_name="Artist A", track_title="Missing Song", rating=5.0),
    ]

    stats["listen_count_imported"] = 0

    matched_count = service._process_interactions(user_id, interactions, stats)

    assert matched_count == 2
    assert stats["ratings_imported"] == 2
    assert stats["listen_count_imported"] == 10

    with mock_work_db.session_scope() as work_session:
        ratings = {
            rating.sync_id: (rating.rating, rating.play_count)
            for rating in work_session.query(UserRating).filter(UserRating.user_id == user_id).all()
        }

    assert ratings[existing_sync_id] == (4.5, 7)
    new_sync_id = f"ss:track:meta:{generate_deterministic_id('Artist A', 'Song Two')}"
    assert ratings[new_sync_id] == (3.0, 3)
    assert len(ratings) == 2


def test_process_interactions_persists_listen_count_without_rating(mock_db, mock_work_db):
    service = UserHistoryService()
    service.music_db = mock_db
    service.working_db = mock_work_db

    with mock_db.session_scope() as music_session:
        artist = Artist(name="Artist B")
        music_session.add(artist)
        music_session.flush()
        music_session.add(Track(title="Playcount Only", artist=artist))

    with mock_work_db.session_scope() as work_session:
        user = User(username="listener2", provider="plex")
        work_session.add(user)
        work_session.flush()
        user_id = user.id

    stats = {"ratings_imported": 0, "listen_count_imported": 0}
    interactions = [
        UserTrackInteraction(
            provider_item_id="4",
            artist_name="Artist B",
            track_title="Playcount Only",
            rating=None,
            play_count=12,
        )
    ]

    matched_count = service._process_interactions(user_id, interactions, stats)

    assert matched_count == 1
    assert stats["ratings_imported"] == 0
    assert stats["listen_count_imported"] == 12

    sync_id = f"ss:track:meta:{generate_deterministic_id('Artist B', 'Playcount Only')}"
    with mock_work_db.session_scope() as work_session:
        row = work_session.query(UserRating).filter(UserRating.user_id == user_id, UserRating.sync_id == sync_id).one()
        assert row.play_count == 12
        assert row.rating is None