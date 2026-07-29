#!/usr/bin/env python3

import threading
import time
from typing import Optional, Dict
from database import MusicDatabase, LibraryManager
from core.matching_engine.echo_sync_track import EchosyncTrack
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
    Now acts as a lightweight orchestrator delegating heavy lifting to the echosync_core Rust engine.
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
            library_manager = LibraryManager(db.session_factory)
            
            def _on_progress(progress: Dict[str, int]):
                try:
                    failed = progress.get("failed", 0)
                    if failed > self.failed_operations:
                        for _ in range(failed - self.failed_operations):
                            scan_state_manager.add_error()
                    self.processed_tracks = progress.get("processed", self.processed_tracks)
                    self.successful_operations = progress.get("imported", 0) + progress.get("updated", 0)
                    self.failed_operations = progress.get("failed", 0)
                    self.processed_artists = progress.get("artists", self.processed_artists)
                    self.processed_albums = progress.get("albums", self.processed_albums)
                except Exception:
                    pass

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

                        def _track_generator():
                            for raw in batch_dicts:
                                yield EchosyncTrack(
                                    title=raw.get("title") or "Unknown Title",
                                    artist_name=raw.get("artist_name") or "Unknown Artist",
                                    album_title=raw.get("album_title"),
                                    duration=raw.get("duration_ms") or 0, # CRITICAL: direct integer mapping
                                    track_number=raw.get("track_number") or 0,
                                    disc_number=raw.get("disc_number") or 1,
                                    bitrate=raw.get("bitrate") or 0,
                                    file_path=raw.get("file_path"),
                                    file_format=raw.get("file_format"),
                                    file_size_bytes=raw.get("file_size_bytes") or 0,
                                    isrc=raw.get("isrc")
                                )

                        # Ingest the batched DTOs immediately
                        library_manager.bulk_import(
                            _track_generator(),
                            progress_callback=_on_progress,
                            identifiers_only=self.identifiers_only,
                            source_name=self.server_type
                        )

                    # Scan directory using Rust PyO3 engine with callback batching
                    echosync_core.scan_directory(self.scan_directory_path, flush_batch, 1000)

                    scan_time = time.time() - start_time
                    logger.info(f"Rust core completed scanning {total_scanned} files in {scan_time:.3f}s")

                    self.processed_tracks = total_scanned
                    self.successful_operations = total_scanned
                    scan_state_manager.complete_scan()

                except Exception as rust_err:
                    scan_state_manager.set_error(str(rust_err))
                    logger.error(f"Rust scanner panicked or failed: {rust_err}", exc_info=True)
                    return

            # --- LEGACY REMOTE MEDIA CLIENT PATH ---
            else:
                logger.debug(f"Fetching library from {self.server_type} via media_client...")
                all_tracks_generator = self.media_client.get_all_tracks()

                imported_count = library_manager.bulk_import(
                    all_tracks_generator,
                    progress_callback=_on_progress,
                    identifiers_only=self.identifiers_only,
                    source_name=self.server_type
                )

                logger.info(f"Successfully imported {imported_count} tracks from {self.server_type}")
                self.processed_tracks = imported_count
                self.successful_operations = imported_count

        except Exception as e:
            logger.error(f"Error in DatabaseUpdateWorker: {e}", exc_info=True)
            self.failed_operations += 1
        finally:
            logger.info("Database update worker finished")

    def start(self):
        from core.job_queue import job_queue
        job_name = f"db_update_worker_{self.server_type}_{id(self)}"
        self._job_name = job_name
        job_queue.register_job(name=job_name, func=self.run, interval_seconds=None, tags=["system", "database"])
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
