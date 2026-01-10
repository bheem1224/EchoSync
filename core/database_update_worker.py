#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Callable
from core.tiered_logger import tiered_logger
from core.error_handler import error_handler
from database import get_database, MusicDatabase
from utils.logging_config import get_logger
from core.settings import config_manager
from core.matching_engine.soul_sync_track import SoulSyncTrack
import logging  # Add this import for logging levels
from PyQt6.QtCore import QThread  # Ensure QThread is imported for GUI compatibility

logger = get_logger("database_update_worker")


class DatabaseUpdateWorker(QThread):
    """
    Worker thread for updating SoulSync database with media server library data.
    This class adheres strictly to the SoulSyncTrack model to ensure provider-agnostic behavior.
    """

    def __init__(
        self,
        media_client,
        database_path: Optional[str] = None,
        full_refresh: bool = False,
        server_type: str = "generic",
        force_sequential: bool = False
    ):
        super().__init__()

        self.force_sequential = force_sequential
        self.media_client = media_client
        self.server_type = server_type
        self.database_path = database_path
        self.full_refresh = full_refresh
        self.should_stop = False

        # Statistics tracking
        self.processed_artists = 0
        self.processed_albums = 0
        self.processed_tracks = 0
        self.successful_operations = 0
        self.failed_operations = 0

        # Threading control - get from config or default to 5
        database_config = config_manager.get('database', {})
        self.max_workers = database_config.get('max_workers', 5)

        tiered_logger.log(
            "normal", logging.INFO,
            f"DatabaseUpdateWorker initialized (server_type={self.server_type}, max_workers={self.max_workers})"
        )

    def run(self):
        """
        Main execution loop for the worker thread.
        """
        tiered_logger.log("normal", logging.INFO, "Starting database update worker.")
        try:
            if self.force_sequential:
                self._process_sequentially()
            else:
                self._process_concurrently()
        except Exception as e:
            error_handler.handle_exception(
                lambda: (_ for _ in ()).throw(e),  # Raise the exception to log it
                retries=0,
                log_tier="normal"
            )
            tiered_logger.log("normal", logging.ERROR, f"Error in DatabaseUpdateWorker: {e}")
        finally:
            tiered_logger.log("normal", logging.INFO, "Database update worker finished.")

    def _process_sequentially(self):
        """
        Process updates sequentially to avoid threading issues.
        """
        tiered_logger.log("debug", logging.INFO, "Processing updates sequentially.")
        for item in self.media_client.get_library():
            self._process_item(item)

    def _process_concurrently(self):
        """
        Process updates using a thread pool for concurrency.
        """
        tiered_logger.log("debug", logging.INFO, "Processing updates concurrently.")
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._process_item, item) for item in self.media_client.get_library()]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    tiered_logger.log("normal", logging.ERROR, f"Error processing item: {e}")

    def _process_item(self, item):
        """
        Process a single library item, ensuring it adheres to the SoulSyncTrack model.
        """
        try:
            if not isinstance(item, SoulSyncTrack):
                raise ValueError("Item does not conform to the SoulSyncTrack model.")

            # Example processing logic
            tiered_logger.log("debug", logging.INFO, f"Processing item: {item}")
            self.processed_tracks += 1
            self.successful_operations += 1
        except Exception as e:
            self.failed_operations += 1
            tiered_logger.log("normal", logging.ERROR, f"Failed to process item: {e}")


class DatabaseStatsWorker:
    """Placeholder for DatabaseStatsWorker functionality."""
    def __init__(self):
        pass

    def collect_stats(self):
        """Collect database statistics."""
        return {
            "artists": 0,
            "albums": 0,
            "tracks": 0
        }