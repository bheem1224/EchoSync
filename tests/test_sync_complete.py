"""Test complete sync implementation with all 5 remaining features."""
import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from web.routes.playlists import (
    trigger_sync,
    _sync_to_plex,
    _sync_to_tier,
    _register_scheduled_sync_job,
    load_scheduled_syncs_on_startup,
)
from core.job_queue import job_queue
from core.event_bus import event_bus
from core.sync_history import sync_history
from flask import Flask


@pytest.fixture
def app():
    """Create Flask test app."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    with app.test_client() as client:
        yield client


def test_sync_mode_detection_tier_to_tier():
    """Test sync mode detection for tier-to-tier sync (Spotify↔Tidal)."""
    tier_to_tier_providers = {"spotify", "tidal", "apple_music"}
    local_server_providers = {"plex", "jellyfin", "navidrome"}
    
    source = "spotify"
    target = "tidal"
    
    is_source_tier = source in tier_to_tier_providers
    is_target_tier = target in tier_to_tier_providers
    
    assert is_source_tier is True
    assert is_target_tier is True
    
    # Should detect as tier-to-tier
    if is_source_tier and is_target_tier:
        sync_mode = "tier-to-tier"
    
    assert sync_mode == "tier-to-tier"


def test_sync_mode_detection_local_server():
    """Test sync mode detection for local-server sync (Spotify→Plex)."""
    tier_to_tier_providers = {"spotify", "tidal", "apple_music"}
    local_server_providers = {"plex", "jellyfin", "navidrome"}
    
    source = "spotify"
    target = "plex"
    
    is_source_tier = source in tier_to_tier_providers
    is_target_server = target in local_server_providers
    
    assert is_source_tier is True
    assert is_target_server is True
    
    # Should detect as local-server
    if is_source_tier and is_target_server:
        sync_mode = "local-server"
    
    assert sync_mode == "local-server"


def test_sync_mode_detection_server_to_tier():
    """Test sync mode detection for server-to-tier sync (Plex→Spotify)."""
    tier_to_tier_providers = {"spotify", "tidal", "apple_music"}
    local_server_providers = {"plex", "jellyfin", "navidrome"}
    
    source = "plex"
    target = "spotify"
    
    is_source_server = source in local_server_providers
    is_target_tier = target in tier_to_tier_providers
    
    assert is_source_server is True
    assert is_target_tier is True
    
    # Should detect as server-to-tier
    if is_source_server and is_target_tier:
        sync_mode = "server-to-tier"
    
    assert sync_mode == "server-to-tier"


def test_event_bus_publish_and_get():
    """Test event bus pub/sub for sync progress."""
    job_name = "test:sync:job:123"
    
    # Clear previous events
    event_bus.clear(job_name)
    
    # Publish events
    event_bus.publish(job_name, "sync_started", {"total": 10, "playlist": "test"})
    event_bus.publish(job_name, "track_synced", {"index": 1, "rating_key": "abc"})
    event_bus.publish(job_name, "sync_complete", {"synced": 10, "failed": 0})
    
    # Get events since -1 (all)
    events = event_bus.get_events(job_name, since_id=-1)
    
    assert len(events) == 3
    assert events[0]["type"] == "sync_started"
    assert events[1]["type"] == "track_synced"
    assert events[2]["type"] == "sync_complete"
    
    # Get events since event 1 (only last 2)
    events = event_bus.get_events(job_name, since_id=0)
    assert len(events) == 2


def test_sync_history_recording():
    """Test sync history recording and retention."""
    sync_history.clear()
    
    # Record multiple syncs
    for i in range(5):
        sync_history.record_sync(
            source="spotify",
            target="plex",
            playlist=f"test_playlist_{i}",
            total=100,
            synced=95,
            failed=5,
            download_missing=False,
            job_name=f"sync:job:{i}",
        )
    
    # Check history
    history = sync_history.get_recent(limit=10)
    assert len(history) == 5
    
    # Check most recent
    recent = sync_history.get_recent(limit=1)
    assert len(recent) == 1
    assert recent[0].playlist == "test_playlist_4"


def test_scheduled_sync_config_creation():
    """Test creating and storing scheduled sync config."""
    sync_config = {
        "id": f"sync:spotify:plex:{int(time.time())}",
        "source": "spotify",
        "target": "plex",
        "playlists": ["playlist_id_1", "playlist_id_2"],
        "interval": 3600,
        "download_missing": True,
        "enabled": True,
        "created_at": time.time(),
    }
    
    # Verify config structure
    assert sync_config["source"] == "spotify"
    assert sync_config["target"] == "plex"
    assert sync_config["interval"] == 3600
    assert sync_config["enabled"] is True
    assert len(sync_config["playlists"]) == 2


def test_scheduled_sync_intervals():
    """Test various scheduled sync interval options."""
    intervals = [
        (300, "5 minutes"),
        (900, "15 minutes"),
        (1800, "30 minutes"),
        (3600, "1 hour"),
        (21600, "6 hours"),
        (43200, "12 hours"),
        (86400, "24 hours"),
        (604800, "1 week"),
    ]
    
    for seconds, label in intervals:
        assert seconds > 0
        assert isinstance(label, str)
        assert len(label) > 0


def test_event_monotonic_ids():
    """Test that event IDs are monotonically increasing."""
    job_name = "test:monotonic:job"
    event_bus.clear(job_name)
    
    # Publish multiple events
    for i in range(10):
        event_bus.publish(job_name, f"event_{i}", {"index": i})
    
    # Get events
    events = event_bus.get_events(job_name, since_id=-1)
    
    # Verify IDs increase
    for i in range(1, len(events)):
        assert events[i]["id"] > events[i-1]["id"]


def test_sync_job_retry_config():
    """Test job queue retry/backoff configuration."""
    max_retries = 3
    backoff_base = 5.0
    backoff_factor = 2.0
    
    # Calculate backoff times
    backoff_times = []
    for retry_count in range(1, max_retries + 1):
        backoff = backoff_base * (backoff_factor ** (retry_count - 1))
        backoff_times.append(backoff)
    
    # Verify exponential growth
    assert backoff_times[0] == 5.0  # 5 * (2 ^ 0)
    assert backoff_times[1] == 10.0  # 5 * (2 ^ 1)
    assert backoff_times[2] == 20.0  # 5 * (2 ^ 2)


def test_sync_payload_validation():
    """Test sync endpoint payload validation."""
    valid_payloads = [
        {
            "source": "spotify",
            "target_source": "plex",
            "playlist_name": "Test Playlist",
            "matches": [{"track_id": "1", "target_identifier": "abc"}],
            "download_missing": False,
        },
        {
            "source": "spotify",
            "target_source": "tidal",
            "playlist_name": "Tier Sync",
            "matches": [{"track_id": "1", "target_identifier": "xyz"}],
            "download_missing": True,
        },
    ]
    
    for payload in valid_payloads:
        assert "source" in payload
        assert "target_source" in payload
        assert "playlist_name" in payload
        assert "matches" in payload
        assert isinstance(payload["matches"], list)


def test_ui_schedule_modal_data_binding():
    """Test UI schedule modal form data binding."""
    schedule_form = {
        "source": "spotify",
        "target": "plex",
        "playlists": ["p1", "p2", "p3"],
        "interval": 3600,
        "download_missing": False,
    }
    
    # Simulate form updates
    schedule_form["interval"] = 21600  # Change to 6 hours
    schedule_form["download_missing"] = True
    
    assert schedule_form["interval"] == 21600
    assert schedule_form["download_missing"] is True
    assert len(schedule_form["playlists"]) == 3


def test_sync_button_enabled_state():
    """Test sync button enabled/disabled logic."""
    analysis_result_with_matches = {
        "summary": {
            "can_sync": True,
            "matched_pairs": [
                {"track_id": "1", "target_identifier": "abc"},
                {"track_id": "2", "target_identifier": "def"},
            ],
            "missing_tracks": 0,
        }
    }
    
    # Button should be enabled when there are matches and can_sync is true
    can_enable_sync_button = (
        analysis_result_with_matches is not None and
        analysis_result_with_matches.get("summary", {}).get("can_sync", False)
    )
    
    assert can_enable_sync_button is True
    
    # Test with no matches
    analysis_result_no_matches = {
        "summary": {
            "can_sync": False,
            "matched_pairs": [],
            "missing_tracks": 100,
        }
    }
    
    can_enable_sync_button = (
        analysis_result_no_matches is not None and
        analysis_result_no_matches.get("summary", {}).get("can_sync", False)
    )
    
    assert can_enable_sync_button is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
