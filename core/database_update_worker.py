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
    Worker for updating SoulSync database with media server library data.
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
            # Initialize database with SQLAlchemy
            db = MusicDatabase(self.database_path)
            db.create_all()  # Ensure schema exists
            library_manager = LibraryManager(db.session_factory)
            logger.debug("Database path resolved to %s", db.database_path)
            
            # Fetch all tracks from media client (now returns SoulSyncTrack objects)
            logger.debug(f"Fetching library from {self.server_type}...")
            all_tracks = self.media_client.get_all_tracks()
            
            if not all_tracks:
                logger.warning(f"No tracks found in {self.server_type} library")
                return
            
            self.total_tracks = len(all_tracks)
            logger.info(f"Found {self.total_tracks} tracks in {self.server_type} library")
            logger.debug("Beginning bulk import via LibraryManager")
            
            # Use LibraryManager to bulk import tracks
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

            imported_count = library_manager.bulk_import(all_tracks, progress_callback=_on_progress)
            
            logger.info(f"Successfully imported {imported_count} tracks from {self.server_type}")
            logger.debug(
                "Bulk import finished for %s: requested=%s imported=%s", 
                self.server_type,
                len(all_tracks),
                imported_count,
            )
            self.processed_tracks = imported_count
            self.successful_operations = imported_count
            
        except Exception as e:
            logger.error(f"Error in DatabaseUpdateWorker: {e}", exc_info=True)
            self.failed_operations += 1
        finally:
            logger.info("Database update worker finished")

    def start(self):
        """Dispatch run() in a daemon thread for fire-and-forget use (e.g. HTTP routes).

        Stores the thread in ``self.thread`` so callers can check ``is_alive()``.
        For the JobQueue path call ``run()`` directly — it is already executing in a
        JobQueue worker thread and does not need an additional thread.
        """
        t = threading.Thread(target=self.run, daemon=True)
        self.thread = t
        t.start()
        logger.info(f"DatabaseUpdateWorker thread started for {self.server_type}")

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