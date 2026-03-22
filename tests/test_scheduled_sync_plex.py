from web.routes.playlists import _register_scheduled_sync_job


def test_scheduled_sync_passes_target_user_id_to_plex(monkeypatch):
    captured = {}

    def fake_register_job(name, func, **kwargs):
        captured['name'] = name
        captured['func'] = func

    monkeypatch.setattr('web.routes.playlists.job_queue.register_job', fake_register_job)

    class FakeSourceProvider:
        def get_playlist_tracks(self, playlist_id):
            return [
                {
                    'title': 'Song',
                    'artist_name': 'Artist',
                    'id': 'source-1',
                }
            ]

    class FakeTargetProvider:
        def search(self, query, type='track', limit=5):
            return [
                {
                    'id': '123',
                }
            ]

    def fake_get_provider_for_account(provider_name, acc_id=None):
        if provider_name == 'spotify':
            return FakeSourceProvider(), acc_id
        if provider_name == 'plex':
            return FakeTargetProvider(), None
        return None, None

    monkeypatch.setattr('web.routes.playlists._get_provider_for_account', fake_get_provider_for_account)

    sync_calls = []

    def fake_sync_to_plex(payload, source, target, playlist_name, matches, download_missing, sync_mode, *rest):
        sync_calls.append({
            'payload': payload,
            'source': source,
            'target': target,
            'playlist_name': playlist_name,
            'matches': matches,
            'download_missing': download_missing,
            'sync_mode': sync_mode,
        })

    monkeypatch.setattr('web.routes.playlists._sync_to_plex', fake_sync_to_plex)

    sync_config = {
        'id': 'sync:spotify:plex:123',
        'source': 'spotify',
        'target': 'plex',
        'playlists': [
            {
                'id': 'playlist-1',
                'account_id': 1,
                'source_account_name': 'Kiddo Spotify',
                'target_user_id': 'managed-1',
            }
        ],
        'interval': 3600,
        'download_missing': False,
    }

    _register_scheduled_sync_job(sync_config)
    captured['func']()

    assert len(sync_calls) == 1
    assert sync_calls[0]['payload']['target_user_id'] == 'managed-1'
    assert sync_calls[0]['payload']['source_account_name'] == 'Kiddo Spotify'
    assert sync_calls[0]['matches'][0]['target_identifier'] == '123'