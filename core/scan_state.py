import threading
from typing import Dict, Any, Optional
import time

class ScanStateManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ScanStateManager, cls).__new__(cls)
                cls._instance._init_state()
            return cls._instance

    def _init_state(self):
        self.state_lock = threading.Lock()
        self.reset()

    def reset(self):
        with self.state_lock:
            self.status = "idle"
            self.tracks_processed = 0
            self.batch_size = 0
            self.errors_encountered = 0
            self.current_phase = "idle"
            self.total_tracks = 0
            self.start_time = None
            self.elapsed_time_ms = 0
            self.error_message = None

    def start_scan(self, batch_size: int = 500):
        with self.state_lock:
            self.status = "scanning"
            self.tracks_processed = 0
            self.batch_size = batch_size
            self.errors_encountered = 0
            self.current_phase = "metadata_extraction"
            self.start_time = time.time()
            self.elapsed_time_ms = 0
            self.error_message = None

    def add_processed(self, count: int):
        with self.state_lock:
            self.tracks_processed += count

    def add_error(self):
        with self.state_lock:
            self.errors_encountered += 1

    def complete_scan(self):
        with self.state_lock:
            self.status = "complete"
            self.total_tracks = self.tracks_processed
            if self.start_time:
                self.elapsed_time_ms = int((time.time() - self.start_time) * 1000)

    def set_error(self, message: str):
        with self.state_lock:
            self.status = "failed"
            self.error_message = message

    def get_state_payload(self) -> Dict[str, Any]:
        with self.state_lock:
            if self.status == "scanning":
                return {
                    "status": "scanning",
                    "tracks_processed": self.tracks_processed,
                    "batch_size": self.batch_size,
                    "errors_encountered": self.errors_encountered,
                    "current_phase": self.current_phase
                }
            elif self.status == "complete":
                return {
                    "status": "complete",
                    "total_tracks": self.total_tracks,
                    "total_errors": self.errors_encountered,
                    "elapsed_time_ms": self.elapsed_time_ms
                }
            elif self.status == "failed":
                return {
                    "status": "failed",
                    "error_message": self.error_message
                }
            else:
                return {"status": "idle"}

scan_state_manager = ScanStateManager()
