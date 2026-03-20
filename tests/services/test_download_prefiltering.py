import pytest

from providers.slskd.client import SlskdProvider
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

        result = await manager._invoke_provider_search(
            provider,
            "artist title",
            strategy_filters,
            quality_profile,
        )

        assert result == [{"ok": True}]
        assert captured["query"] == "artist title"
        assert captured["basic_filters"] == strategy_filters
        assert captured["quality_profile"] == quality_profile
