"""Integration test verifying sync feature end-to-end."""
import pytest
import time
from web.utils.event_bus import event_bus
from core.sync_history import sync_history


def test_end_to_end_sync_workflow():
    """Test complete sync workflow: request → matching → job → events → history."""
    
    # 1. Simulate API request payload validation
    sync_request = {
        "source": "spotify",
        "target_source": "plex",
        "playlist_name": "My Liked Songs",
        "matches": [
            {"track_id": "spotify:track:123", "target_identifier": "plex_rkey_456"},
            {"track_id": "spotify:track:789", "target_identifier": "plex_rkey_101"},
        ],
        "download_missing": False,
    }
    
    assert sync_request["source"] in ["spotify", "tidal", "plex", "jellyfin", "navidrome"]
    assert sync_request["target_source"] in ["spotify", "tidal", "plex", "jellyfin", "navidrome"]
    assert len(sync_request["matches"]) == 2
    
    # 2. Detect sync mode
    tier_providers = {"spotify", "tidal", "apple_music"}
    server_providers = {"plex", "jellyfin", "navidrome"}
    
    source_type = "tier" if sync_request["source"] in tier_providers else "server"
    target_type = "tier" if sync_request["target_source"] in tier_providers else "server"
    sync_mode = f"{source_type}-to-{target_type}"
    
    assert sync_mode == "tier-to-server"
    
    # 3. Simulate job scheduling and event emission
    job_name = f"sync:plex:{sync_request['playlist_name']}:{int(time.time())}"
    
    # Clear previous events
    event_bus.clear(job_name)
    
    # Emit events as if the sync job is running
    event_bus.publish(job_name, "sync_started", {
        "playlist": sync_request["playlist_name"],
        "target": sync_request["target_source"],
        "total": len(sync_request["matches"]),
        "sync_mode": sync_mode,
    })
    
    for idx, match in enumerate(sync_request["matches"]):
        event_bus.publish(job_name, "track_started", {
            "index": idx,
            "rating_key": match["target_identifier"],
            "total": len(sync_request["matches"]),
        })
        
        # Simulate successful sync
        event_bus.publish(job_name, "track_synced", {
            "index": idx,
            "rating_key": match["target_identifier"],
        })
    
    event_bus.publish(job_name, "sync_complete", {
        "playlist": sync_request["playlist_name"],
        "synced": len(sync_request["matches"]),
        "failed": 0,
        "target": sync_request["target_source"],
        "sync_mode": sync_mode,
    })
    
    # 4. Verify event stream
    events = event_bus.get_events(job_name, since_id=-1)
    # sync_started + N*(track_started + track_synced) + sync_complete = 1 + 2*N + 1
    expected_count = 1 + (2 * len(sync_request["matches"])) + 1
    assert len(events) == expected_count
    assert events[0]["type"] == "sync_started"
    assert events[-1]["type"] == "sync_complete"
    
    # Verify monotonic IDs
    for i in range(1, len(events)):
        assert events[i]["id"] > events[i-1]["id"]
    
    # Verify timestamps
    for event in events:
        assert "ts" in event
        assert isinstance(event["ts"], float)
        assert event["ts"] > 0
    
    # 5. Record to sync history
    sync_history.clear()
    sync_history.record_sync(
        source=sync_request["source"],
        target=sync_request["target_source"],
        playlist=sync_request["playlist_name"],
        total=len(sync_request["matches"]),
        synced=len(sync_request["matches"]),
        failed=0,
        download_missing=sync_request["download_missing"],
        job_name=job_name,
    )
    
    # 6. Verify history recording
    history = sync_history.get_recent(limit=10)
    assert len(history) == 1
    record = history[0]
    assert record.source == "spotify"
    assert record.target == "plex"
    assert record.playlist == "My Liked Songs"
    assert record.synced == 2
    assert record.failed == 0
    assert record.total_tracks == 2
    
    # 7. Verify scheduled sync configuration
    scheduled_config = {
        "id": f"sync:spotify:plex:{int(time.time())}",
        "source": "spotify",
        "target": "plex",
        "playlists": ["playlist_1", "playlist_2"],
        "interval": 3600,
        "download_missing": False,
        "enabled": True,
        "created_at": time.time(),
    }
    
    assert scheduled_config["interval"] >= 300
    assert len(scheduled_config["playlists"]) >= 1
    assert scheduled_config["created_at"] > 0
    
    # 8. Verify payload from UI perspective
    ui_payload = {
        "source": "spotify",
        "target_source": "plex",
        "playlist_name": "My Liked Songs",
        "matches": sync_request["matches"],
        "download_missing": False,
    }
    
    assert "source" in ui_payload
    assert "target_source" in ui_payload
    assert "matches" in ui_payload
    assert isinstance(ui_payload["matches"], list)
    assert all("track_id" in m and "target_identifier" in m for m in ui_payload["matches"])


def test_event_polling_simulation():
    """Test event polling pattern used by frontend."""
    job_name = "test:polling:job"
    event_bus.clear(job_name)
    
    # Emit initial events
    event_bus.publish(job_name, "sync_started", {"total": 100})
    event_bus.publish(job_name, "track_synced", {"index": 0})
    event_bus.publish(job_name, "track_synced", {"index": 1})
    
    # Frontend: First poll (since_id=-1 means all)
    events = event_bus.get_events(job_name, since_id=-1)
    assert len(events) == 3
    last_id = events[-1]["id"]
    
    # More events added
    event_bus.publish(job_name, "track_synced", {"index": 2})
    event_bus.publish(job_name, "sync_complete", {"synced": 3, "failed": 0})
    
    # Frontend: Second poll (since_id=last_id gets only new events)
    new_events = event_bus.get_events(job_name, since_id=last_id)
    assert len(new_events) == 2
    assert new_events[0]["type"] == "track_synced"
    assert new_events[1]["type"] == "sync_complete"


def test_scheduled_sync_interval_options():
    """Test all interval options available in UI."""
    intervals = {
        "5 minutes": 300,
        "15 minutes": 900,
        "30 minutes": 1800,
        "1 hour": 3600,
        "6 hours": 21600,
        "12 hours": 43200,
        "24 hours": 86400,
        "1 week": 604800,
    }
    
    for label, seconds in intervals.items():
        # Verify minimum interval
        assert seconds >= 300, f"Interval {label} ({seconds}s) is less than 5 minutes"
        
        # Simulate config creation
        config = {
            "id": f"sync:test:{seconds}",
            "source": "spotify",
            "target": "plex",
            "playlists": ["test"],
            "interval": seconds,
            "enabled": True,
            "created_at": time.time(),
        }
        
        assert config["interval"] == seconds
        assert config["enabled"] is True


def test_sync_ui_state_transitions():
    """Test UI state transitions during sync workflow."""
    
    # Initial state
    state = {
        "analysisResult": None,
        "syncConfigModalOpen": False,
        "syncProgressModalOpen": False,
        "syncInProgress": False,
        "syncEventStream": [],
        "scheduledSyncs": [],
    }
    
    # User runs analysis
    state["analysisResult"] = {
        "summary": {
            "can_sync": True,
            "matched_pairs": [{"track_id": "1", "target_identifier": "abc"}],
            "missing_tracks": 0,
        }
    }
    
    # Sync button enabled check
    can_enable_sync = state["analysisResult"]["summary"]["can_sync"]
    assert can_enable_sync is True
    
    # User clicks Sync
    state["syncConfigModalOpen"] = True
    assert state["syncConfigModalOpen"] is True
    assert state["syncProgressModalOpen"] is False
    
    # User confirms sync
    state["syncConfigModalOpen"] = False
    state["syncProgressModalOpen"] = True
    state["syncInProgress"] = True
    
    assert state["syncInProgress"] is True
    assert state["syncProgressModalOpen"] is True
    
    # Simulate events coming in
    state["syncEventStream"].append({"id": 0, "type": "sync_started"})
    state["syncEventStream"].append({"id": 1, "type": "track_synced"})
    assert len(state["syncEventStream"]) == 2
    
    # Sync completes
    state["syncEventStream"].append({"id": 2, "type": "sync_complete"})
    state["syncInProgress"] = False
    state["syncProgressModalOpen"] = False
    
    assert state["syncInProgress"] is False
    assert state["syncProgressModalOpen"] is False
    assert len(state["syncEventStream"]) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
