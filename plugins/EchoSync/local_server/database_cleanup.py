# plugins/EchoSync/local_server/database_cleanup.py

import os
import logging
from collections import defaultdict
from core.tiered_logger import get_logger
from core.job_queue import register_job
from database.music_database import get_database, Track, Album, Artist

logger = get_logger("jobs.database_cleanup")

# Import or redefine BaseJob depending on your core structure
try:
    from core.jobs.reorganize_library_job import BaseJob
except ImportError:
    class BaseJob:
        def update_progress(self, current: int, total: int, status: str = ""):
            pass

class DatabaseCleanupJob(BaseJob):
    """
    A manual dev utility designed to correct database drift by aggressively 
    evicting ghost paths, deduplicating identical tracks, and pruning structural orphans.
    """
    
    def execute(self, *args, **kwargs):
        logger.info("Starting manual Database Cleanup Job...")
        db = get_database()
        
        with db.session_scope() as session:
            # ==========================================
            # Phase 1: Broken Path Eviction
            # ==========================================
            self.update_progress(0, 100, "Phase 1: Evicting broken paths...")
            
            tracks = session.query(Track).filter(Track.file_path.isnot(None), Track.file_path != '').all()
            deleted_broken_count = 0
            
            for track in tracks:
                if not os.path.exists(track.file_path):
                    session.delete(track)
                    deleted_broken_count += 1
            
            session.commit()
            logger.info(f"[Phase 1] Evicted {deleted_broken_count} tracks pointing to missing physical files.")

            # ==========================================
            # Phase 2: Same-File Row Flattening
            # ==========================================
            self.update_progress(33, 100, "Phase 2: Flattening redundant file paths...")
            
            # Fetch remaining tracks after Phase 1
            remaining_tracks = session.query(Track).filter(Track.file_path.isnot(None), Track.file_path != '').all()
            path_groups = defaultdict(list)
            
            for track in remaining_tracks:
                path_groups[track.file_path].append(track)
                
            flattened_duplicate_count = 0
            
            for file_path, group in path_groups.items():
                if len(group) > 1:
                    # Sort the group by ID so the lowest ID (earliest created) is kept
                    group.sort(key=lambda t: t.id)
                    master_track = group[0]
                    redundant_tracks = group[1:]
                    
                    for duplicate in redundant_tracks:
                        session.delete(duplicate)
                        flattened_duplicate_count += 1
                        
            session.commit()
            logger.info(f"[Phase 2] Deduplicated {flattened_duplicate_count} redundant track rows pointing to the same file path.")

            # ==========================================
            # Phase 3: Structural Orphan Purge
            # ==========================================
            self.update_progress(66, 100, "Phase 3: Purging structural orphans...")
            
            # Delete albums without tracks
            empty_albums = session.query(Album).filter(~Album.tracks.any()).all()
            empty_album_count = len(empty_albums)
            for album in empty_albums:
                session.delete(album)
            
            # Delete artists without tracks AND without albums
            empty_artists = session.query(Artist).filter(~Artist.tracks.any(), ~Artist.albums.any()).all()
            empty_artist_count = len(empty_artists)
            for artist in empty_artists:
                session.delete(artist)
                
            session.commit()
            logger.info(f"[Phase 3] Purged {empty_album_count} orphaned Albums and {empty_artist_count} orphaned Artists.")
            
        self.update_progress(100, 100, "Database cleanup complete.")
        logger.info("Manual Database Cleanup Job finished successfully.")


def register_database_cleanup_job(enabled: bool = True):
    """
    Registration snippet for the global JobRegistry (job_queue).
    Set with a massive interval and delay so it never runs automatically.
    """
    job_instance = DatabaseCleanupJob()
    
    register_job(
        name="database_cleanup",
        func=job_instance.execute,
        interval_seconds=315360000, # 10 years
        start_after=315360000,      # 10 years
        enabled=enabled
    )
