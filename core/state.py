import threading
import time

class SystemState:
    """Thread-safe global application state manager."""
    def __init__(self):
        self._start_time = time.time()
        self._restart_pending = False
        self._lock = threading.Lock()

    @property
    def start_time(self) -> float:
        """Returns the application start time as a Unix timestamp."""
        with self._lock:
            return self._start_time

    @property
    def restart_pending(self) -> bool:
        """Returns True if a system restart is required (e.g. after plugin updates)."""
        with self._lock:
            return self._restart_pending

    @restart_pending.setter
    def restart_pending(self, value: bool):
        with self._lock:
            self._restart_pending = value

# Global singleton
system_state = SystemState()
