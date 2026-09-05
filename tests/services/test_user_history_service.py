from core.user_history import UserTrackInteraction
from database.music_database import Artist, ExternalIdentifier, LocalMedia, Track
from database.working_database import Account, UserRating
from services.user_history_service import UserHistoryService


def _test_sync_active_plex_users_to_working_db_creates_day1_users(mock_work_db):
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
        users = work_session.query(Account).order_by(Account.username).all()
        assert [u.username for u in users] == ["Kid A", "Kid B"]
        assert [u.provider_identifier for u in users] == ["plex-user-1", "plex-user-2"]


def test_process_interactions_bulk_upserts_existing_and_new_ratings(
    mock_db, mock_work_db
):
    service = UserHistoryService()
    service.music_db = mock_db
    service.working_db = mock_work_db

    with mock_db.session_scope() as music_session:
        artist = Artist(name="Artist A")
        music_session.add(artist)
        music_session.flush()
        music_session.add_all(
            [
                Track(sync_id="s1o2n3g1", title="Song One", artist=artist),
                Track(sync_id="s2o2n3g2", title="Song Two", artist=artist),
            ]
        )

    with mock_work_db.session_scope() as work_session:
        user = Account(username="listener", remote_account_id="plex", plugin_id=1)
        work_session.add(user)
        work_session.flush()
        existing_sync_id = "s1o2n3g1"
        work_session.add(
            UserRating(account_id=user.id, sync_id=existing_sync_id, rating=2.0)
        )
        user_id = user.id

    stats = {"ratings_imported": 0}
    interactions = [
        UserTrackInteraction(
            plugin_item_id="1",
            artist_name="Artist A",
            track_title="Song One",
            rating=4.5,
            play_count=7,
        ),
        UserTrackInteraction(
            plugin_item_id="2",
            artist_name="Artist A",
            track_title="Song Two",
            rating=3.0,
            play_count=3,
        ),
        UserTrackInteraction(
            plugin_item_id="3",
            artist_name="Artist A",
            track_title="Missing Song",
            rating=5.0,
        ),
    ]

    stats["listen_count_imported"] = 0

    matched_count = service._process_interactions(
        user_id, interactions, stats, plugin_source="plex"
    )

    assert matched_count == 2
    assert stats["ratings_imported"] == 2
    assert stats["listen_count_imported"] == 10

    with mock_work_db.session_scope() as work_session:
        ratings = {
            rating.sync_id: (rating.rating, rating.play_count)
            for rating in work_session.query(UserRating)
            .filter(UserRating.account_id == user_id)
            .all()
        }

    assert ratings[existing_sync_id] == (4.5, 7)
    new_sync_id = "s2o2n3g2"
    assert ratings[new_sync_id] == (3.0, 3)
    assert len(ratings) == 2


def test_process_interactions_persists_listen_count_without_rating(
    mock_db, mock_work_db
):
    service = UserHistoryService()
    service.music_db = mock_db
    service.working_db = mock_work_db

    with mock_db.session_scope() as music_session:
        artist = Artist(name="Artist B")
        music_session.add(artist)
        music_session.flush()
        track_playcount = Track(
            sync_id="p1a2y3c4", title="Playcount Only", artist=artist
        )
        music_session.add(track_playcount)

    with mock_work_db.session_scope() as work_session:
        user = Account(username="listener2", remote_account_id="plex", plugin_id=1)
        work_session.add(user)
        work_session.flush()
        user_id = user.id

    stats = {"ratings_imported": 0, "listen_count_imported": 0}
    interactions = [
        UserTrackInteraction(
            plugin_item_id="4",
            artist_name="Artist B",
            track_title="Playcount Only",
            rating=None,
            play_count=12,
        )
    ]

    matched_count = service._process_interactions(
        user_id, interactions, stats, plugin_source="plex"
    )

    assert matched_count == 1
    assert stats["ratings_imported"] == 0
    assert stats["listen_count_imported"] == 12

    sync_id = "p1a2y3c4"
    with mock_work_db.session_scope() as work_session:
        row = (
            work_session.query(UserRating)
            .filter(UserRating.account_id == user_id, UserRating.sync_id == sync_id)
            .one()
        )
        assert row.play_count == 12
        assert row.rating is None


def test_process_interactions_matches_plex_metadata_uri_to_external_identifier(
    mock_db, mock_work_db
):
    service = UserHistoryService()
    service.music_db = mock_db
    service.working_db = mock_work_db

    with mock_db.session_scope() as music_session:
        artist = Artist(name="Coolio")
        music_session.add(artist)
        music_session.flush()

        track = Track(sync_id="g1p2r3d4", title="Gangsta's Paradise", artist=artist)
        music_session.add(track)
        music_session.flush()

        lm = LocalMedia(media_id="lm_1234", track_id=track.id, file_path="/fake/path")
        music_session.add(lm)
        music_session.flush()

        music_session.add(
            ExternalIdentifier(
                media_id="lm_1234",
                plugin_source="plex",
                plugin_item_id="120760",
                raw_data=None,
            )
        )

    with mock_work_db.session_scope() as work_session:
        user = Account(username="listener3", remote_account_id="plex", plugin_id=1)
        work_session.add(user)
        work_session.flush()
        user_id = user.id

    stats = {"ratings_imported": 0, "listen_count_imported": 0}
    interactions = [
        UserTrackInteraction(
            plugin_item_id="/library/metadata/120760",
            artist_name="Various Artists",
            track_title="Gangsta's Paradise",
            rating=4.0,
            play_count=2,
        )
    ]

    matched_count = service._process_interactions(
        user_id, interactions, stats, plugin_source="plex"
    )

    assert matched_count == 1
    assert stats["ratings_imported"] == 1
    assert stats["listen_count_imported"] == 2

    expected_sync_id = "g1p2r3d4"
    with mock_work_db.session_scope() as work_session:
        row = (
            work_session.query(UserRating)
            .filter(
                UserRating.account_id == user_id, UserRating.sync_id == expected_sync_id
            )
            .one()
        )
        assert row.rating == 4.0
        assert row.play_count == 2


def test_process_interactions_extracts_provider_ids_from_legacy_fields(
    mock_db, mock_work_db
):
    service = UserHistoryService()
    service.music_db = mock_db
    service.working_db = mock_work_db

    with mock_db.session_scope() as music_session:
        artist = Artist(name="Coolio")
        music_session.add(artist)
        music_session.flush()

        track = Track(sync_id="g1p2r3d4", title="Gangsta's Paradise", artist=artist)
        music_session.add(track)
        music_session.flush()

        lm = LocalMedia(media_id="lm_1234", track_id=track.id, file_path="/fake/path")
        music_session.add(lm)
        music_session.flush()

        music_session.add(
            ExternalIdentifier(
                media_id="lm_1234",
                plugin_source="plex",
                plugin_item_id="120760",
                raw_data=None,
            )
        )

    with mock_work_db.session_scope() as work_session:
        user = Account(username="listener4", remote_account_id="plex", plugin_id=1)
        work_session.add(user)
        work_session.flush()
        user_id = user.id

    stats = {"ratings_imported": 0, "listen_count_imported": 0}

    legacy_id_interaction = UserTrackInteraction(
        plugin_item_id="",
        artist_name="Various Artists",
        track_title="Gangsta's Paradise",
        rating=5.0,
        play_count=1,
    )
    legacy_id_interaction.source_item_id = "/library/metadata/120760"

    dict_id_interaction = UserTrackInteraction(
        plugin_item_id="",
        artist_name="Various Artists",
        track_title="Gangsta's Paradise",
        rating=4.0,
        play_count=2,
    )
    dict_id_interaction.identifiers = {"plex": "120760"}

    matched_count = service._process_interactions(
        user_id,
        [legacy_id_interaction, dict_id_interaction],
        stats,
        plugin_source="plex",
    )

    assert matched_count == 2
    assert stats["ratings_imported"] == 2
    assert stats["listen_count_imported"] == 3

    expected_sync_id = "g1p2r3d4"
    with mock_work_db.session_scope() as work_session:
        row = (
            work_session.query(UserRating)
            .filter(
                UserRating.account_id == user_id, UserRating.sync_id == expected_sync_id
            )
            .one()
        )
        assert row.rating == 4.0
        assert row.play_count == 2
