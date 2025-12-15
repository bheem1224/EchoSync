
import pytest
from unittest.mock import MagicMock, patch
import time
from core.web_scan_manager import WebScanManager

# --- Mock Clients ---

class MockMediaClient:
    def __init__(self, is_connected=True):
        self._is_connected = is_connected
        self.trigger_library_scan = MagicMock(return_value=True)

    def is_connected(self):
        return self._is_connected

@pytest.fixture
def mock_clients():
    return {
        "plex_client": MockMediaClient(is_connected=True),
        "jellyfin_client": MockMediaClient(is_connected=True),
        "navidrome_client": MockMediaClient(is_connected=False), # Simulate one being disconnected
    }

# --- Fixture for the Manager ---

@pytest.fixture
def manager(mock_clients):
    # Use a short delay for testing
    m = WebScanManager(media_clients=mock_clients, delay_seconds=0.1)
    yield m
    if m._timer:
        m._timer.cancel()

# --- Tests ---

def test_initialization(manager: WebScanManager, mock_clients):
    """Test that the manager initializes correctly."""
    assert manager.media_clients == mock_clients
    assert manager.delay == 0.1
    status = manager.get_scan_status()
    assert status['status'] == 'idle'

@patch('core.web_scan_manager.config_manager')
def test_get_active_media_client(mock_config, manager: WebScanManager, mock_clients):
    """Test the logic for selecting the active media client."""
    # 1. Test getting the configured client (Jellyfin)
    mock_config.get_active_media_server.return_value = "jellyfin"
    client, server_type = manager._get_active_media_client()
    assert client == mock_clients['jellyfin_client']
    assert server_type == "jellyfin"

    # 2. Test fallback to first available connected client when configured is not connected
    mock_config.get_active_media_server.return_value = "navidrome"
    client, server_type = manager._get_active_media_client()
    # Should fall back to first available (jellyfin if first in order, or plex)
    assert client is not None
    assert client.is_connected() is True
    assert server_type in ["jellyfin", "plex"]
    
    # 3. Test when Plex is the configured client
    mock_config.get_active_media_server.return_value = "plex"
    client, server_type = manager._get_active_media_client()
    assert client == mock_clients['plex_client']
    assert server_type == "plex"

    # 4. Test when no clients are connected
    all_disconnected_clients = {
        "plex_client": MockMediaClient(is_connected=False),
        "jellyfin_client": MockMediaClient(is_connected=False),
    }
    manager_no_conn = WebScanManager(media_clients=all_disconnected_clients)
    client, server_type = manager_no_conn._get_active_media_client()
    assert client is None
    assert server_type is None

@patch('threading.Timer')
def test_request_scan_debouncing(mock_timer_class, manager: WebScanManager):
    """Test that multiple scan requests are debounced."""
    mock_timer_instance = MagicMock()
    mock_timer_class.return_value = mock_timer_instance

    # First request
    manager.request_scan("First")
    mock_timer_class.assert_called_once_with(0.1, manager._execute_scan)
    mock_timer_instance.start.assert_called_once()
    
    # Second request
    manager.request_scan("Second")
    mock_timer_instance.cancel.assert_called_once()
    assert mock_timer_class.call_count == 2
    assert mock_timer_instance.start.call_count == 2

def test_request_scan_adds_callback(manager: WebScanManager):
    """Test that a callback passed to request_scan is registered."""
    my_callback = MagicMock()
    my_callback.__name__ = 'my_callback'
    with patch('threading.Timer'): # Prevent timer from actually running
        manager.request_scan("Request with callback", callback=my_callback)
    
    assert my_callback in manager._scan_completion_callbacks

@patch('core.web_scan_manager.config_manager')
def test_execute_scan_and_completion(mock_config, manager: WebScanManager, mock_clients):
    """Test the full lifecycle from execution to completion timeout."""
    mock_config.get_active_media_server.return_value = "plex"

    # Patch the timer to control the completion check
    with patch('threading.Timer') as mock_timer:
        # --- 1. Execute the scan ---
        manager._execute_scan()
        
        assert manager.get_scan_status()['status'] == 'scanning'
        status = manager.get_scan_status()
        assert 'plex' in str(status).lower()  # Verify plex is mentioned somewhere in the status
        mock_clients['plex_client'].trigger_library_scan.assert_called_once()
        
        # Verify the completion check timer was started
        mock_timer.assert_called_with(30, pytest.ANY)
        completion_checker_func = mock_timer.call_args[0][1]
        
        # --- 2. Simulate completion ---
        # To test completion, we can't easily fast-forward a real timer.
        # Instead, we can manually call the completion handler.
        mock_callback = MagicMock()
        mock_callback.__name__ = 'mock_callback'
        manager.add_scan_completion_callback(mock_callback)
        
        with patch.object(manager, 'request_scan') as mock_request_scan:
            # Simulate downloads happening during the scan
            manager._downloads_during_scan = True
            
            manager._handle_scan_completion()
            
            # Verify callback was called
            mock_callback.assert_called_once()
            
            # Verify state is reset
            assert manager.get_scan_status()['status'] == 'idle'
            
            # Verify follow-up scan was requested
            mock_request_scan.assert_called_once()


def test_get_scan_status_states(manager: WebScanManager):
    """Test the get_scan_status method in different states."""
    # 1. Idle state
    assert manager.get_scan_status()['status'] == 'idle'
    
    # 2. Scheduled state
    with manager._lock:
        manager._timer = MagicMock()
    assert manager.get_scan_status()['status'] == 'scheduled'
    with manager._lock:
        manager._timer = None # cleanup
        
    # 3. Scanning state
    with manager._lock:
        manager._scan_in_progress = True
        manager._scan_start_time = time.time() - 10 # 10 seconds ago
        manager._current_server_type = "plex"
        manager._scan_progress = {"message": "Scanning..."}
    
    status = manager.get_scan_status()
    assert status['status'] == 'scanning'
    assert status['server_type'] == 'plex'
    assert status['elapsed_seconds'] == pytest.approx(10, 1)
    assert status['progress']['message'] == 'Scanning...'
