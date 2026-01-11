#!/usr/bin/env python3

from typing import Optional
from database import MusicDatabase, LibraryManager
from utils.logging_config import get_logger
from core.settings import config_manager
import logging
import threading

logger = get_logger("database_update_worker")

try:
    from PyQt6.QtCore import QThread
    HAS_QTHREAD = True
except ImportError:
    HAS_QTHREAD = False
    QThread = threading.Thread


class DatabaseUpdateWorker(QThread if HAS_QTHREAD else threading.Thread):
    """
    Worker thread for updating SoulSync database with media server library data.
    Syncs all tracks from media client into the database using bulk operations.
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
        if HAS_QTHREAD:
            self.daemon = False
        else:
            self.daemon = True

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
            
            logger.info(f"Found {len(all_tracks)} tracks in {self.server_type} library")
            logger.debug("Beginning bulk import via LibraryManager")
            
            # Use LibraryManager to bulk import tracks
            imported_count = library_manager.bulk_import(all_tracks)
            
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

    def stop(self):
        """Signal the worker to stop processing"""
        self.should_stop = True
        logger.info("Stop signal sent to database update worker")


class DatabaseStatsWorker:
    """Collects database statistics."""
    def __init__(self):
        self.db = MusicDatabase()

    def collect_stats(self):
        """Collect database statistics."""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM artists")
            artist_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM albums")
            album_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tracks")
            track_count = cursor.fetchone()[0]
            
            conn.close()
            
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