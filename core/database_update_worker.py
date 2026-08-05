#!/usr/bin/env python3

import threading
import time
from typing import Optional, Dict
from database import MusicDatabase
from core.orchestrator.ingestion import IngestionOrchestrator
from core.tiered_logger import get_logger
from core.scan_state import scan_state_manager
import logging

# Import the new compiled Rust engine
try:
    import echosync_core
except ImportError as e:
    echosync_core = None
    logging.getLogger("database_update_worker").critical(f"Failed to import echosync_core Rust engine: {e}")

logger = get_logger("database_update_worker")


class DatabaseUpdateWorker:
    """
    Worker for updating Echosync database with media server library data.
    Routes all telemetry batches strictly through IngestionOrchestrator using SQLAlchemy 2.0 UPSERTs.
    """

    def __init__(
        self,
        media_client,
        database_path: Optional[str] = None,
        full_refresh: bool = False,
        server_type: str = "generic",
        force_sequential: bool = False,
        identifiers_only: bool = False,
        scan_directory_path: Optional[str] = None
    ):
        self.media_client = media_client
        self.server_type = server_type
        self.database_path = database_path
        self.full_refresh = full_refresh
        self.force_sequential = force_sequential
        self.identifiers_only = identifiers_only
        self.scan_directory_path = scan_directory_path
        self.should_stop = False
        self.cancel_token = echosync_core.CancellationToken() if echosync_core and hasattr(echosync_core, "CancellationToken") else None

        # Statistics tracking
        self.processed_artists = 0
        self.processed_albums = 0
        self.processed_tracks = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.total_tracks = 0

        self.thread: Optional[threading.Thread] = None
        logger.info(f"DatabaseUpdateWorker initialized for {server_type} ({('full' if full_refresh else 'incremental')} mode)")

    def run(self):
        """Main execution loop for the worker thread."""
        logger.info(f"Starting database update worker for {self.server_type}")
        try:
            db = MusicDatabase(self.database_path)
            orchestrator = IngestionOrchestrator(batch_size=1000, session_factory=db.session_factory)
            telemetry_cb = orchestrator.create_telemetry_callback()

            # --- RUST HIGH-PERFORMANCE SCANNING PATH ---
            if self.server_type == "EchoSync.Local Server" and self.scan_directory_path and echosync_core:
                logger.info(f"Delegating local directory scan to Rust core: {self.scan_directory_path}")
                scan_state_manager.start_scan(batch_size=1000)
                start_time = time.time()
                try:
                    total_scanned = 0

                    def flush_batch(batch_dicts):
                        nonlocal total_scanned
                        count = len(batch_dicts)
                        total_scanned += count
                        scan_state_manager.add_processed(count)
                        telemetry_cb(batch_dicts)

                    # Scan directory using Rust PyO3 engine with callback batching and cancel token
                    echosync_core.scan_directory(self.scan_directory_path, flush_batch, 1000, self.cancel_token)
                    flushed_count = telemetry_cb.flush()

                    scan_time = time.time() - start_time
                    logger.info(f"Rust core completed scanning {total_scanned} files in {scan_time:.3f}s")

                    self.processed_tracks = total_scanned
                    self.successful_operations = total_scanned
                    scan_state_manager.complete_scan()

                except Exception as rust_err:
                    scan_state_manager.set_error(str(rust_err))
                    logger.error(f"Rust scanner panicked or failed: {rust_err}", exc_info=True)
                    return

            # --- REMOTE MEDIA CLIENT PATH ---
            else:
                logger.debug(f"Fetching library from {self.server_type} via media_client...")
                all_tracks = list(self.media_client.get_all_tracks())

                dicts = []
                for t in all_tracks:
                    if hasattr(t, "to_dict"):
                        dicts.append(t.to_dict())
                    elif hasattr(t, "model_dump"):
                        dicts.append(t.model_dump())
                    elif isinstance(t, dict):
                        dicts.append(t)

                imported_count = orchestrator.ingest_telemetry_batch(dicts)
                logger.info(f"Successfully imported {imported_count} tracks from {self.server_type}")
                self.processed_tracks = imported_count
                self.successful_operations = imported_count

        except Exception as e:
            logger.error(f"Error in DatabaseUpdateWorker: {e}", exc_info=True)
            self.failed_operations += 1
        finally:
            logger.info("Database update worker finished")

    def start(self):
        from core.job_queue import job_queue, TaskCategory
        job_name = f"db_update_worker_{self.server_type}_{id(self)}"
        self._job_name = job_name
        job_queue.register_job(
            name=job_name,
            func=self.run,
            interval_seconds=None,
            category=TaskCategory.DATABASE_WRITE_HEAVY,
            cancel_token=self.cancel_token,
            tags=["system", "database"]
        )
        job_queue.execute_job_now(job_name)
        logger.info(f"DatabaseUpdateWorker queued via job_queue for {self.server_type}")

    def stop(self):
        self.should_stop = True


class DatabaseStatsWorker:
    """Collects database statistics."""
    def __init__(self):
        self.db = MusicDatabase()

    def collect_stats(self):
        try:
            artist_count = self.db.count_artists()
            album_count = self.db.count_albums()
            track_count = self.db.count_tracks()
            
            return {
                "artists": artist_count,
                "albums": album_count,
                "tracks": track_count
            }
        except Exception as e:
            logger.error(f"Error collecting database stats: {e}")
            return {
                "artists": 0,
                "albums": 0,
                "tracks": 0
            }
