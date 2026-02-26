"""
Verification test for Provider Rate Limiting logic.
"""
import pytest
from unittest.mock import MagicMock, patch
import time
from core.provider_base import ProviderBase
from core.request_manager import RequestManager, RateLimitConfig

class MockRateLimitedProvider(ProviderBase):
    name = "test_fast"
    rate_limit = 10.0 # 10 req/s = 0.1s interval

    # Minimal implementations for abstract methods
    def authenticate(self, **kwargs): return True
    def search(self, query): return []
    def get_track(self, track_id): return None
    def get_album(self, album_id): return None
    def get_artist(self, artist_id): return None
    def get_user_playlists(self, user_id=None): return []
    def get_playlist_tracks(self, playlist_id): return []
    def is_configured(self): return True
    def get_logo_url(self): return ""

class MockSlowProvider(ProviderBase):
    name = "test_slow"
    rate_limit = 1.0 # 1 req/s = 1.0s interval

    # Minimal implementations
    def authenticate(self, **kwargs): return True
    def search(self, query): return []
    def get_track(self, track_id): return None
    def get_album(self, album_id): return None
    def get_artist(self, artist_id): return None
    def get_user_playlists(self, user_id=None): return []
    def get_playlist_tracks(self, playlist_id): return []
    def is_configured(self): return True
    def get_logo_url(self): return ""

class TestRateLimiting:
    def test_provider_initialization_respects_rate_limit(self):
        """Verify providers initialize RequestManager with correct rate limits."""
        fast = MockRateLimitedProvider()
        assert fast.http.rate.requests_per_second == 10.0

        slow = MockSlowProvider()
        assert slow.http.rate.requests_per_second == 1.0

    def test_request_manager_applies_limit(self):
        """Verify RequestManager sleeps appropriately."""
        # Mock time.sleep and time.time
        with patch('time.sleep') as mock_sleep, \
             patch('time.time') as mock_time:

            # Setup mock time to advance manually
            current_time = 1000.0
            mock_time.side_effect = lambda: current_time

            # Create manager with 1 req/s limit
            config = RateLimitConfig(requests_per_second=1.0)
            manager = RequestManager("test", rate=config)

            # First call - should not sleep (no previous call)
            manager._apply_rate_limit()
            mock_sleep.assert_not_called()

            # Second call immediately after
            # _apply_rate_limit updates _last_call_ts to current_time
            manager._apply_rate_limit()

            # Should sleep for roughly 1.0s
            # Logic: delta = 0, min_interval = 1.0. sleep(1.0 - 0)
            mock_sleep.assert_called()
            args, _ = mock_sleep.call_args
            assert 0.99 < args[0] <= 1.0
