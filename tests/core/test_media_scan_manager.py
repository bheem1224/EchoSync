
import pytest
from unittest.mock import MagicMock, patch, call
import time
from core.media_scan_manager import MediaScanManager

# We use real threading here but mock time.sleep to speed up tests.
# This makes testing the timer logic more realistic.

class MockMediaClient:
    def __init__(self, server_type="plex"):
        self.server_type = server_type
        self.trigger_library_scan = MagicMock(return_value=True)
        self.is_library_scanning = MagicMock(return_value=True)

@pytest.fixture
def mock_media_client():
    return MockMediaClient()

@pytest.fixture
def manager(mock_media_client):
    # Patch the client getter to always return our mock client
    with patch.object(MediaScanManager, '_get_active_media_client', return_value=(mock_media_client, "plex")):
        m = MediaScanManager(delay_seconds=0.1) # Use a short delay for testing
        yield m
        # Shutdown to clean up any running timers
        m.shutdown()

# --- Tests ---

def test_initialization():
    """Test the initial state of the manager."""
    m = MediaScanManager(delay_seconds=30)
    status = m.get_status()
    assert status['delay_seconds'] == 30
    assert status['scan_in_progress'] is False
    assert status['timer_active'] is False

@patch('threading.Timer')
def test_request_scan_debouncing(mock_timer_class, manager: MediaScanManager):
    """Test that multiple scan requests are debounced correctly."""
    mock_timer_instance = MagicMock()
    mock_timer_class.return_value = mock_timer_instance

    # First request should start a timer
    manager.request_scan("First request")
    mock_timer_class.assert_called_once_with(0.1, manager._execute_scan)
    mock_timer_instance.start.assert_called_once()
    
    # Second request should cancel the old timer and start a new one
    manager.request_scan("Second request")
    mock_timer_instance.cancel.assert_called_once()
    assert mock_timer_class.call_count == 2
    assert mock_timer_instance.start.call_count == 2

def test_request_scan_while_scan_in_progress(manager: MediaScanManager):
    """Test that a request during a scan flags for a follow-up scan."""
    with manager._lock:
        manager._scan_in_progress = True
    
    with patch.object(manager, '_timer') as mock_timer:
        manager.request_scan("Request during scan")
        
        # Should not start a new timer
        mock_timer.assert_not_called()
        # Should set the flag for a follow-up
        assert manager._downloads_during_scan is True

def test_execute_scan_triggers_client(manager: MediaScanManager, mock_media_client):
    """Test that executing a scan calls the media client's trigger method."""
    # We patch the periodic updates to not interfere with this test
    with patch.object(manager, '_start_periodic_updates') as mock_periodic:
        manager._execute_scan()

        assert manager._scan_in_progress is True
        mock_media_client.trigger_library_scan.assert_called_once()
        mock_periodic.assert_called_once()

def test_scan_completion_callback(manager: MediaScanManager):
    """Test that registered callbacks are called upon scan completion."""
    mock_callback = MagicMock()
    mock_callback.__name__ = 'mock_callback'
    manager.add_scan_completion_callback(mock_callback)

    # Manually simulate a scan being in progress and then completing
    with manager._lock:
        manager._scan_in_progress = True
    
    manager._scan_completed()
    
    mock_callback.assert_called_once()

def test_follow_up_scan(manager: MediaScanManager):
    """Test that a follow-up scan is triggered if downloads happened during a scan."""
    # Simulate a scan that just finished, but with downloads during it
    with manager._lock:
        manager._scan_in_progress = True
        manager._downloads_during_scan = True

    with patch.object(manager, 'request_scan') as mock_request_scan:
        manager._scan_completed()
        
        mock_request_scan.assert_called_once_with("Follow-up scan for downloads during previous scan")

def test_periodic_update_logic(manager: MediaScanManager, mock_media_client):
    """Test the periodic update flow from scanning to completion."""
    # Patch the timer to control its execution
    with patch('threading.Timer') as mock_timer_class:
        # --- 1. Start the scan ---
        # intercept periodic callback invocations
        manager._call_completion_callbacks = MagicMock()
        manager._execute_scan()
        manager._scan_start_time = time.time()
        
        # --- 2. First periodic update: still scanning ---
        mock_media_client.is_library_scanning.return_value = True
        # Manually call the periodic update function
        manager._do_periodic_update()

        # Verify the periodic callback invocations and a new timer was scheduled
        assert manager._call_completion_callbacks.call_count > 0
        assert mock_timer_class.call_count == 2 # Initial and the one inside _do_periodic_update

        # --- 3. Second periodic update: scan finished ---
        mock_media_client.is_library_scanning.return_value = False
        # Manually call it again
        manager._do_periodic_update()
        
        # It should call scan_completed, which calls the callbacks
        # Let's check the state
        assert manager._scan_in_progress is False
        assert manager._is_doing_periodic_updates is False

def test_force_scan(manager: MediaScanManager):
    """Test that force_scan bypasses the debounce timer."""
    with patch.object(manager, '_execute_scan') as mock_execute:
        # Set up a pending timer
        with manager._lock:
            manager._timer = MagicMock()
        
        manager.force_scan()
        
        # The pending timer should be cancelled
        manager._timer.cancel.assert_called_once()
        # _execute_scan should be called directly
        mock_execute.assert_called_once()
