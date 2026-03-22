from web.routes.playlists import _register_scheduled_sync_job


def test_scheduled_sync_passes_target_user_id_to_plex(monkeypatch):
    captured = {}

    def fake_register_job(name, func, **kwargs):
        captured['name'] = name
        captured['func'] = func

    monkeypatch.setattr('web.routes.playlists.job_queue.register_job', fake_register_job)

    analysis_calls = []

    def fake_analyze_playlists_internal(source, target_source, playlists, quality_profile='Auto'):
        analysis_calls.append({
            'source': source,
            'target_source': target_source,
            'playlists': playlists,
            'quality_profile': quality_profile,
        })
        return {
            'summary': {
                'matched_pairs': [
                    {
                        'track_id': 42,
                        'target_identifier': '123',
                    }
                ]
            }
        }

    monkeypatch.setattr('web.routes.playlists._analyze_playlists_internal', fake_analyze_playlists_internal)

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

    assert len(analysis_calls) == 1
    assert analysis_calls[0]['source'] == 'spotify'
    assert analysis_calls[0]['target_source'] == 'plex'
    assert analysis_calls[0]['playlists'][0]['target_user_id'] == 'managed-1'

    assert len(sync_calls) == 1
    assert sync_calls[0]['payload']['target_user_id'] == 'managed-1'
    assert sync_calls[0]['payload']['source_account_name'] == 'Kiddo Spotify'
    assert sync_calls[0]['matches'][0]['target_identifier'] == '123'