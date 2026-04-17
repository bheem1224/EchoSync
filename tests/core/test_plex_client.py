
import pytest
from unittest.mock import MagicMock, patch
from providers.plex.client import PlexClient
from core.user_history import UserTrackInteraction

@pytest.fixture
def plex_client():
    with patch('providers.plex.client.config_manager') as mock_cm:
        mock_cm.get_plex_config.return_value = {}
        client = PlexClient()
        return client

def test_initialization(plex_client):
    assert plex_client.name == 'plex'
    assert plex_client.supports_downloads is False
    assert plex_client.server is None
    assert plex_client.music_library is None

def test_is_configured_false(plex_client):
    plex_client.account_id = None
    assert plex_client.is_configured() is False

def test_is_configured_true(plex_client):
    plex_client.account_id = 1
    with patch('core.file_handling.storage.get_storage_service') as mock_get_storage, \
         patch('core.settings.config_manager.get') as mock_config_get:
        mock_storage = MagicMock()

        def mock_get_account_token(acc_id):
            return {'access_token': 'encrypted_abc'}

        mock_storage.get_account_token.side_effect = mock_get_account_token
        mock_get_storage.return_value = mock_storage

        def mock_config(key, default=None):
            if key == 'plex':
                return {'base_url': 'http://plex'}
            return default

        mock_config_get.side_effect = mock_config

        assert plex_client.is_configured() is True


def test_auto_detect_prefers_token_backed_account(monkeypatch):
    fake_storage = MagicMock()
    fake_storage.list_accounts.return_value = [
        {'id': 11, 'display_name': 'Managed User'},
        {'id': 22, 'display_name': 'Admin User'},
    ]
    fake_storage.get_account_token.side_effect = lambda account_id: None if account_id == 11 else {'access_token': 'token'}

    monkeypatch.setattr('core.file_handling.storage.get_storage_service', lambda: fake_storage)

    client = PlexClient()
    assert client.account_id == 22


def test_import_managed_users_upserts_admin_and_managed(monkeypatch):
    client = PlexClient(account_id=7)
    client.ensure_connection = lambda: True

    managed_user = MagicMock()
    managed_user.id = 'managed-1'
    managed_user.uuid = None
    managed_user.username = 'kiddo'
    managed_user.title = 'Kiddo'
    managed_user.email = 'kiddo@example.com'

    myplex_account = MagicMock()
    myplex_account.uuid = 'admin-uuid'
    myplex_account.id = 123
    myplex_account.username = 'admin'
    myplex_account.title = 'Admin'
    myplex_account.email = 'admin@example.com'
    myplex_account.users.return_value = [managed_user]

    server = MagicMock()
    server.myPlexAccount.return_value = myplex_account
    client.server = server

    fake_storage = MagicMock()
    fake_storage.get_account_token.return_value = {'access_token': 'encrypted-token'}
    fake_storage.upsert_account.side_effect = [7, 8]
    fake_storage.list_accounts.return_value = [
        {'id': 7, 'display_name': 'admin', 'user_id': 'admin-uuid'},
        {'id': 8, 'display_name': 'Kiddo', 'user_id': 'managed-1'},
    ]

    monkeypatch.setattr('core.file_handling.storage.get_storage_service', lambda: fake_storage)

    accounts = client.import_managed_users()

    assert [account['id'] for account in accounts] == [7, 8]
    assert fake_storage.upsert_account.call_count == 2
    admin_call = fake_storage.upsert_account.call_args_list[0].kwargs
    managed_call = fake_storage.upsert_account.call_args_list[1].kwargs
    assert admin_call['account_id'] == 7
    assert admin_call['user_id'] == 'admin-uuid'
    assert managed_call['user_id'] == 'managed-1'
    assert managed_call['is_authenticated'] is False


def test_add_tracks_to_managed_playlist_uses_exact_target_user_id(monkeypatch):
    client = PlexClient(account_id=7)
    client.ensure_connection = lambda: True
    client.music_library = MagicMock()

    matched_user = MagicMock()
    matched_user.id = 'managed-1'
    matched_user.uuid = None
    matched_user.username = 'kiddo'
    matched_user.title = 'Kiddo'

    other_user = MagicMock()
    other_user.id = 'managed-2'
    other_user.uuid = None
    other_user.username = 'other'
    other_user.title = 'Other'

    server = MagicMock()
    server.myPlexAccount.return_value.users.return_value = [matched_user, other_user]
    target_server = MagicMock()
    target_server.fetchItem.return_value = MagicMock(ratingKey='100')
    server.switchUser.return_value = target_server
    client.server = server
    client._find_managed_playlist = lambda *args, **kwargs: None

    created_playlist = MagicMock()
    created_playlist.items.return_value = [MagicMock(ratingKey='100')]

    with patch('plexapi.playlist.Playlist.create', return_value=created_playlist):
        ok = client.add_tracks_to_managed_playlist(
            'Road Trip',
            ['100'],
            source_account_name='Something Else',
            target_user_id='managed-1',
        )

    assert ok is True
    server.switchUser.assert_called_once_with('kiddo')


def test_add_tracks_to_managed_playlist_falls_back_to_source_account_name(monkeypatch):
    client = PlexClient(account_id=7)
    client.ensure_connection = lambda: True
    client.music_library = MagicMock()

    matched_user = MagicMock()
    matched_user.id = None
    matched_user.uuid = 'plex-uuid-22'
    matched_user.username = 'simi'
    matched_user.title = 'Simi'
    matched_user.email = None

    server = MagicMock()
    server.myPlexAccount.return_value.users.return_value = [matched_user]
    target_server = MagicMock()
    target_server.fetchItem.return_value = MagicMock(ratingKey='100')
    server.switchUser.return_value = target_server
    client.server = server
    client._find_managed_playlist = lambda *args, **kwargs: None

    created_playlist = MagicMock()
    created_playlist.items.return_value = [MagicMock(ratingKey='100')]

    with patch('plexapi.playlist.Playlist.create', return_value=created_playlist):
        ok = client.add_tracks_to_managed_playlist(
            'Road Trip',
            ['100'],
            source_account_name='Simi',
            target_user_id='managed-id-that-does-not-match-runtime-shape',
        )

    assert ok is True
    server.switchUser.assert_called_once_with('simi')


def test_add_tracks_to_managed_playlist_falls_back_via_substring_account_name(monkeypatch):
    """'Simi's Spotify' should resolve to Plex managed user 'Simi' via substring match."""
    client = PlexClient(account_id=7)
    client.ensure_connection = lambda: True
    client.music_library = MagicMock()

    matched_user = MagicMock()
    matched_user.id = None
    matched_user.uuid = 'plex-uuid-33'
    matched_user.username = 'simi'
    matched_user.title = 'Simi'
    matched_user.email = None

    server = MagicMock()
    server.myPlexAccount.return_value.users.return_value = [matched_user]
    target_server = MagicMock()
    target_server.fetchItem.return_value = MagicMock(ratingKey='200')
    server.switchUser.return_value = target_server
    client.server = server
    client._find_managed_playlist = lambda *args, **kwargs: None

    created_playlist = MagicMock()
    created_playlist.items.return_value = [MagicMock(ratingKey='200')]

    with patch('plexapi.playlist.Playlist.create', return_value=created_playlist):
        ok = client.add_tracks_to_managed_playlist(
            'Chill Vibes',
            ['200'],
            # target_user_id is None — simulates the providers.py gap before the fix
            source_account_name="Simi's Spotify",
            target_user_id=None,
        )

    assert ok is True
    # Must have switched to the matched user, not stayed on admin
    server.switchUser.assert_called_once_with('simi')


def test_fetch_user_history_switches_to_managed_user_context(monkeypatch):
    client = PlexClient(account_id=7)
    client.ensure_connection = lambda: True
    client.music_library = MagicMock()

    managed_user = MagicMock()
    managed_user.id = 42  # numeric Plex account ID — int() cast must succeed
    managed_user.uuid = None
    managed_user.title = 'Kiddo'

    myplex_account = MagicMock()
    myplex_account.uuid = 'admin-uuid'
    myplex_account.id = 123
    myplex_account.username = 'admin'
    myplex_account.users.return_value = [managed_user]

    target_server = MagicMock()
    target_server.history.return_value = [MagicMock()]

    server = MagicMock()
    server.myPlexAccount.return_value = myplex_account
    server.switchUser.return_value = target_server
    client.server = server

    client._find_music_library_for_server = lambda _: MagicMock()
    client._track_to_interaction = lambda _: UserTrackInteraction(
        provider_item_id='1',
        artist_name='Artist',
        track_title='Song',
        play_count=3,
    )

    fake_storage = MagicMock()
    fake_storage.list_accounts.return_value = [
        {'id': 8, 'display_name': 'Kiddo', 'user_id': '42'}  # matches managed_user.id
    ]
    monkeypatch.setattr('core.file_handling.storage.get_storage_service', lambda: fake_storage)

    # Add type track so the interaction is included
    mock_history_item = MagicMock()
    mock_history_item.type = 'track'
    target_server.history.return_value = [mock_history_item]
    interactions = client.fetch_user_history(account_id=8, limit=10)

    assert len(interactions) == 1
    server.switchUser.assert_called_once_with('Kiddo')
    target_server.history.assert_called_once_with(maxresults=10, accountID=42)


def test_track_to_interaction_extracts_user_rating_and_play_count():
    client = PlexClient(account_id=7)

    # Avoid coupling this test to full conversion internals.
    converted = MagicMock()
    converted.artist_name = 'Artist'
    converted.title = 'Song'
    converted.identifiers = {'plex': '100'}
    client._convert_track_to_echosync = lambda _: converted

    plex_track = MagicMock()
    plex_track.ratingKey = '100'
    plex_track.viewCount = 11
    plex_track.userRating = 8.0  # Plex wire-format (1–10); display stars = wire / 2 = 4.0
    plex_track.lastViewedAt = None

    interaction = client._track_to_interaction(plex_track)

    assert interaction is not None
    assert interaction.play_count == 11
    assert interaction.rating == 4.0


def test_track_to_interaction_treats_zero_rating_as_unrated():
    client = PlexClient(account_id=7)

    converted = MagicMock()
    converted.artist_name = 'Artist'
    converted.title = 'Song'
    converted.identifiers = {'plex': '100'}
    client._convert_track_to_echosync = lambda _: converted

    plex_track = MagicMock()
    plex_track.ratingKey = '100'
    plex_track.viewCount = 1
    plex_track.userRating = 0
    plex_track.lastViewedAt = None

    interaction = client._track_to_interaction(plex_track)

    assert interaction is not None
    assert interaction.rating is None


def test_enrich_interactions_with_user_ratings_fetches_missing_only():
    client = PlexClient(account_id=7)

    missing_rating = UserTrackInteraction(
        provider_item_id='100',
        artist_name='Artist A',
        track_title='Song A',
        play_count=1,
        rating=None,
    )
    existing_rating = UserTrackInteraction(
        provider_item_id='200',
        artist_name='Artist B',
        track_title='Song B',
        play_count=2,
        rating=7.0,
    )

    rated_item = MagicMock()
    rated_item.userRating = 9.0  # wire-format 9.0 → display 4.5

    target_server = MagicMock()
    target_server.fetchItem.return_value = rated_item

    interactions = [missing_rating, existing_rating]
    client._enrich_interactions_with_user_ratings(interactions, target_server)

    assert missing_rating.rating == 4.5
    assert existing_rating.rating == 7.0
    target_server.fetchItem.assert_called_once_with(100)


def test_fetch_user_history_enriches_ratings_from_metadata(monkeypatch):
    client = PlexClient(account_id=7)
    client.ensure_connection = lambda: True
    client.music_library = MagicMock()

    managed_user = MagicMock()
    managed_user.id = 42  # numeric Plex account ID
    managed_user.uuid = None
    managed_user.title = 'Kiddo'

    myplex_account = MagicMock()
    myplex_account.uuid = 'admin-uuid'
    myplex_account.id = 123
    myplex_account.username = 'admin'
    myplex_account.users.return_value = [managed_user]

    target_server = MagicMock()
    history_item = MagicMock()
    history_item.type = 'track'
    target_server.history.return_value = [history_item]

    rated_metadata = MagicMock()
    rated_metadata.userRating = 8.5  # wire-format 8.5 → display 4.25
    target_server.fetchItem.return_value = rated_metadata

    server = MagicMock()
    server.myPlexAccount.return_value = myplex_account
    server.switchUser.return_value = target_server
    client.server = server

    client._find_music_library_for_server = lambda _: MagicMock()
    client._track_to_interaction = lambda _: UserTrackInteraction(
        provider_item_id='123',
        artist_name='Artist',
        track_title='Song',
        play_count=1,
        rating=None,
    )

    fake_storage = MagicMock()
    fake_storage.list_accounts.return_value = [
        {'id': 8, 'display_name': 'Kiddo', 'user_id': '42'}  # matches managed_user.id
    ]
    monkeypatch.setattr('core.file_handling.storage.get_storage_service', lambda: fake_storage)

    interactions = client.fetch_user_history(account_id=8, limit=10)

    assert len(interactions) == 1
    assert interactions[0].rating == 4.25
    target_server.fetchItem.assert_called_once_with(123)
