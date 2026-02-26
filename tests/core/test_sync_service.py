import pytest
from unittest.mock import MagicMock, patch

from services.sync_service import PlaylistSyncService
from providers.spotify.client import SpotifyClient


class FakeSpotifyClient:
    def __init__(self, account_id=None):
        self.account_id = account_id
        self.playlists = []
    def is_configured(self):
        return True
    def get_user_playlists(self):
        # return a playlist per account so we can see which client was hit
        return [{'id': f"pl{self.account_id}", 'name': f"P{self.account_id}", 'track_count': 1}]
    def get_playlist_tracks(self, pid):
        # return dummy track with minimal attributes
        class T:
            def __init__(self, title):
                self.title = title
                self.artist_name = 'A'
                self.album_title = 'B'
                self.duration = 100
                self.identifiers = {}
        return [T(pid)]


@pytest.fixture(autouse=True)
def patch_spotify_client(monkeypatch):
    # intercept SpotifyClient constructor to return fake instance
    def factory(provider_name, account_id=None, **kwargs):
        if provider_name == 'spotify':
            return FakeSpotifyClient(account_id=account_id)
        return MagicMock()

    # patch ProviderRegistry.create_instance used by sync_service
    monkeypatch.setattr('core.provider.ProviderRegistry.create_instance', factory)

    # disable provider registry registration which isn't needed for these fakes
    monkeypatch.setattr('core.provider.ProviderRegistry.register', lambda *args, **kwargs: None)

    # also patch account manager to return two accounts
    fake_storage = MagicMock()
    # Mock AccountManager.list_accounts to return accounts
    monkeypatch.setattr('core.account_manager.AccountManager.list_accounts',
                        lambda service: [{'id': 1}, {'id': 2}] if service == 'spotify' else [])

    yield


def test_multiple_spotify_clients_created():
    service = PlaylistSyncService()
    # should create two clients based on storage.list_accounts
    assert len(service.spotify_clients) == 2
    assert {c.account_id for c in service.spotify_clients} == {1, 2}
    # default spotify_client is first one
    assert service.spotify_client.account_id == 1


def test_get_spotify_playlist_respects_account_id(monkeypatch):
    service = PlaylistSyncService()
    # ask for playlist from account 2 explicitly
    pl = service._get_spotify_playlist('P2', account_id=2)
    assert pl is not None
    assert '(P2' not in pl.name  # name should not be suffixed here
    # ask without account_id should return first match across clients
    pl_all = service._get_spotify_playlist('P1')
    assert pl_all and pl_all.id == 'pl1'


def test_get_all_spotify_playlists_filters_active(monkeypatch):
    # monkeypatch config manager to return account configs including active flag
    monkeypatch.setattr('core.settings.config_manager.get_spotify_accounts', 
                        lambda: [
                            {'id': 1, 'name': 'First', 'is_active': True},
                            {'id': 2, 'name': 'Second', 'is_active': False},
                            {'id': 3, 'name': 'Third', 'enabled': True}
                        ])
    service = PlaylistSyncService()
    # run the async helper
    import asyncio
    playlists = asyncio.run(service._get_all_spotify_playlists())
    # since account 2 inactive it should be skipped
    assert any('First' in p.name for p in playlists)
    assert not any('Second' in p.name for p in playlists)
    assert any('Third' in p.name for p in playlists)
