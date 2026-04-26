#!/usr/bin/env python3

import threading
from typing import Optional, Dict
from database import MusicDatabase, LibraryManager
from core.tiered_logger import get_logger
from core.settings import config_manager
import logging

logger = get_logger("database_update_worker")


class DatabaseUpdateWorker:
    """
    Worker for updating Echosync database with media server library data.
    Syncs all tracks from media client into the database using bulk operations.

    The ``run()`` method is a plain synchronous callable — it can be invoked
    directly by the JobQueue worker pool (blocking) or dispatched into a
    background thread via ``start()`` for fire-and-forget HTTP route use.
    """

    def __init__(
        self,
        media_client,
        database_path: Optional[str] = None,
        full_refresh: bool = False,
        server_type: str = "generic",
        force_sequential: bool = False
    ):
        self.media_client = media_client
        self.server_type = server_type
        self.database_path = database_path
        self.full_refresh = full_refresh
        self.force_sequential = force_sequential
        self.should_stop = False

        # Statistics tracking
        self.processed_artists = 0
        self.processed_albums = 0
        self.processed_tracks = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.total_tracks = 0

        # Thread reference populated by start(); callers that need is_alive() check this.
        self.thread: Optional[threading.Thread] = None

        logger.info(f"DatabaseUpdateWorker initialized for {server_type} ({('full' if full_refresh else 'incremental')} mode)")

    def run(self):
        """Main execution loop for the worker thread."""
        logger.info(f"Starting database update worker for {self.server_type}")
        try:
            db = MusicDatabase(self.database_path)
            library_manager = LibraryManager(db.session_factory)
            logger.debug("Database path resolved to %s", db.database_path)
            
            logger.debug(f"Fetching library from {self.server_type}...")
            
            # OPTIMIZATION: Use a generator to stream tracks instead of dumping all to a list
            all_tracks_generator = self.media_client.get_all_tracks()
            
            logger.debug("Beginning streaming bulk import via LibraryManager")
            
            def _on_progress(progress: Dict[str, int]):
                try:
                    # Update worker stats live
                    self.processed_tracks = progress.get("processed", self.processed_tracks)
                    self.successful_operations = progress.get("imported", 0) + progress.get("updated", 0)
                    self.failed_operations = progress.get("failed", 0)
                    # Optional: track artists/albums if provided
                    self.processed_artists = progress.get("artists", self.processed_artists)
                    self.processed_albums = progress.get("albums", self.processed_albums)
                    # yield to other threads, helping HTTP request handling
                    import time
                    time.sleep(0)
                except Exception:
                    pass

            imported_count = library_manager.bulk_import(all_tracks_generator, progress_callback=_on_progress)
            
            logger.info(f"Successfully imported {imported_count} tracks from {self.server_type}")
            logger.debug(
                "Bulk import finished for %s: imported=%s",
                self.server_type,
                imported_count,
            )
            self.processed_tracks = imported_count
            self.successful_operations = imported_count

            # --- Backfill missing provider identifiers ---
            try:
                backfill_count = library_manager.backfill_provider_identifiers(self.server_type)
                if backfill_count:
                    logger.info(
                        "Backfill: linked %d missing '%s' identifier(s) to existing tracks.",
                        backfill_count, self.server_type,
                    )
            except Exception as bf_err:
                logger.warning(
                    "Backfill of provider identifiers failed (non-fatal): %s", bf_err, exc_info=True
                )
            
        except Exception as e:
            logger.error(f"Error in DatabaseUpdateWorker: {e}", exc_info=True)
            self.failed_operations += 1
        finally:
            logger.info("Database update worker finished")

    def start(self):
        """Dispatch run() via the centralized job queue for fire-and-forget use (e.g. HTTP routes).

        Uses the shared JobQueue worker pool rather than a raw daemon thread so the
        job is visible in the scheduler and benefits from the pool's lifecycle management.
        """
        from core.job_queue import job_queue
        job_name = f"db_update_worker_{self.server_type}_{id(self)}"
        # Expose the job name so get_database_update_status() can query the
        # job queue's _is_running flag for accurate concurrency detection.
        self._job_name = job_name
        job_queue.register_job(name=job_name, func=self.run, interval_seconds=None)
        job_queue.execute_job_now(job_name)
        logger.info(f"DatabaseUpdateWorker queued via job_queue for {self.server_type}")

    def stop(self):
        """Signal the worker to stop processing."""
        self.should_stop = True
        logger.info("Stop signal sent to database update worker")


class DatabaseStatsWorker:
    """Collects database statistics."""
    def __init__(self):
        self.db = MusicDatabase()

    def collect_stats(self):
        """Collect database statistics."""
        try:
            # Use MusicDatabase methods which handle sessions correctly
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