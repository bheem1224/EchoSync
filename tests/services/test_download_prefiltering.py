from types import SimpleNamespace

import pytest

from providers.slskd.client import SlskdProvider
from core.matching_engine.echo_sync_track import EchosyncTrack
from services.download_manager import DownloadManager


class TestSlskdPreFiltering:
    def test_process_search_responses_drops_suspicious_flac_with_quality_profile(self):
        provider = object.__new__(SlskdProvider)

        responses_data = [
            {
                "username": "peerA",
                "freeUploadSlots": 3,
                "uploadSpeed": 150000,
                "queueLength": 1,
                "files": [
                    {
                        "filename": "Artist - Track (fake).flac",
                        "size": 5_000_000,
                        "length": 200,
                        "bitRate": 900,
                    },
                    {
                        "filename": "Artist - Track (real).flac",
                        "size": 40_000_000,
                        "length": 200,
                        "bitRate": 1000,
                    },
                ],
            }
        ]

        quality_profile = {
            "advanced_filters": {
                "fake_flac_min_bytes_per_second": 70000,
                "fake_flac_min_kbps": 500,
            }
        }

        tracks = provider._process_search_responses(responses_data, quality_profile=quality_profile)
        filenames = [t.filename for t in tracks]

        assert len(tracks) == 1
        assert "Artist - Track (real).flac" in filenames
        assert "Artist - Track (fake).flac" not in filenames


class TestDownloadManagerQualityProfileForwarding:
    @pytest.mark.asyncio
    async def test_invoke_provider_search_forwards_quality_profile(self):
        manager = object.__new__(DownloadManager)

        captured = {}

        class SyncProvider:
            def search(self, query, basic_filters=None, limit=10, quality_profile=None):
                captured["query"] = query
                captured["basic_filters"] = basic_filters
                captured["quality_profile"] = quality_profile
                return [{"ok": True}]

        provider = SyncProvider()
        strategy_filters = {"min_bitrate": 320, "allowed_extensions": ["flac"]}
        quality_profile = {"advanced_filters": {"fake_flac_min_kbps": 500}}

        results, sniper_hit = await manager._invoke_provider_search(
            provider,
            "artist title",
            strategy_filters,
            quality_profile,
        )

        assert results == [{"ok": True}]
        assert not sniper_hit
        assert captured["query"] == "artist title"
        assert captured["basic_filters"] == strategy_filters
        assert captured["quality_profile"] == quality_profile


class TestDownloadManagerPrefilterBypass:
    @pytest.mark.asyncio
    async def test_execute_waterfall_search_skips_matcher_for_prefiltered_provider(self):
        manager = object.__new__(DownloadManager)

        target_track = EchosyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="Album",
            duration=180000,
        )
        queued_download = SimpleNamespace(echo_sync_track=target_track.to_dict())

        class FakeQuery:
            def __init__(self, item):
                self._item = item

            def get(self, _download_id):
                return self._item

        class FakeSession:
            def __init__(self, item):
                self._item = item

            def query(self, _model):
                return FakeQuery(self._item)

        class FakeSessionScope:
            def __init__(self, item):
                self._item = item

            def __enter__(self):
                return FakeSession(self._item)

            def __exit__(self, exc_type, exc, tb):
                return False

        manager.work_db = SimpleNamespace(session_scope=lambda: FakeSessionScope(queued_download))
        manager._get_quality_profile = lambda requested_profile_id: {
            "formats": [{"type": "flac", "priority": 1, "min_bitrate": 320}],
            "prefer_larger_files": True,
        }
        manager._extract_allowed_formats = lambda profile: ["flac"]
        manager._get_min_bitrate = lambda profile: 320
        manager._generate_search_strategies = lambda track, tolerance: [
            {"query": "Artist Song", "duration_tolerance_ms": tolerance, "name": "artist+title"}
        ]
        manager._get_priority_tiers = lambda profile: [(1, ["flac"])]
        manager._filter_by_formats = lambda candidates, formats: candidates
        manager._get_matching_engine = lambda: (_ for _ in ()).throw(AssertionError("matcher should not be used"))

        status_updates = []
        manager._update_status = lambda download_id, status, provider_id=None: status_updates.append((download_id, status, provider_id))

        candidate = EchosyncTrack(
            raw_title="Song",
            artist_name="Artist",
            album_title="Album",
            file_format="flac",
        )
        candidate.identifiers["username"] = "peerA"
        candidate.identifiers["provider_item_id"] = "Artist/Album/01 - Song.flac"
        candidate.identifiers["size"] = 50_000_000
        candidate.identifiers["bitrate"] = 1000
        candidate.identifiers["free_upload_slots"] = 2
        candidate.identifiers["upload_speed"] = 2_000_000
        candidate.identifiers["queue_length"] = 0

        async def fake_search(
            provider, query, strategy_filters, quality_profile,
            target_track=None, strategy_name="", perfect_match_threshold=90,
            includes=None, excludes=None,
        ):
            return [candidate], False

        manager._invoke_provider_search = fake_search

        class PrefilterProvider:
            name = "slskd"
            supports_pre_filtering = True

            async def _async_download(self, username, filename, size):
                assert username == "peerA"
                assert filename == "Artist/Album/01 - Song.flac"
                assert size == 50_000_000
                return "provider-download-id"

        provider = PrefilterProvider()

        await manager._execute_waterfall_search_and_download(42, [provider])

        assert status_updates == [(42, "downloading", "provider-download-id")]
