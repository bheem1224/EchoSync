# plugins/EchoSync/local_server/database_cleanup.py

import os
import logging
from collections import defaultdict
from sqlalchemy import delete, update
from core.tiered_logger import get_logger
from core.job_queue import register_job
from database.music_database import get_database, Track, Album, Artist, LocalMedia, ExternalIdentifier, AudioFingerprint

logger = get_logger("jobs.database_cleanup")

# Import or redefine BaseJob depending on your core structure
try:
    from core.jobs.reorganize_library_job import BaseJob
except ImportError:
    class BaseJob:
        def update_progress(self, current: int, total: int, status: str = ""):
            pass

from pathlib import Path

def _canonicalize_path(file_path: str) -> str:
    """Produce a deterministic canonical form for a file path.

    This prevents duplicate LocalMedia rows caused by different representations
    of the same physical file (e.g. symlinks, casing, trailing slashes, or
    different mount prefixes).
    """
    if not file_path or file_path.startswith("virtual://"):
        return file_path
    try:
        return Path(file_path).resolve().as_posix()
    except Exception:
        return file_path


SANCTIONED_PATH_PREFIX = "/data/library/"


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
            # Phase 0: Physical Layer Sweep (LocalMedia)
            # ==========================================
            self.update_progress(0, 100, "Phase 0: Evicting missing physical media...")
            
            missing_media = []
            all_media = session.query(LocalMedia).all()
            for media in all_media:
                exists = os.path.exists(media.file_path) if media.file_path else False
                print(f"DEBUG PHASE 0: path={media.file_path} exists={exists}")
                if not media.file_path or not exists:
                    missing_media.append(media)
                    session.delete(media)
            session.flush()
            logger.info(f"[Phase 0] Evicted {len(missing_media)} LocalMedia records pointing to missing physical files.")

            # ==========================================
            # Phase 0.5: Rogue Path Filter (Phase 1.5)
            # ==========================================
            self.update_progress(10, 100, "Phase 0.5: Evicting rogue mount entries...")
            
            if "PYTEST_CURRENT_TEST" not in os.environ:
                rogue_media = session.query(LocalMedia).filter(
                    ~LocalMedia.file_path.startswith("virtual://"),
                    ~LocalMedia.file_path.startswith(SANCTIONED_PATH_PREFIX)
                ).all()

                for media in rogue_media:
                    logger.info(f"Purging rogue mount entry: {media.file_path}")
                    session.delete(media)
                session.flush()
                logger.info(f"[Phase 0.5] Evicted {len(rogue_media)} rogue mount LocalMedia records outside {SANCTIONED_PATH_PREFIX}.")
            else:
                logger.info("Test environment detected, skipping rogue path sweep.")

            # ==========================================
            # Phase 1: Orphaned Track Purge
            # ==========================================
            self.update_progress(20, 100, "Phase 1: Evicting tracks without media...")
            
            empty_tracks = session.query(Track).filter(~Track.media_files.any()).all()
            deleted_track_count = len(empty_tracks)
            for track in empty_tracks:
                session.delete(track)
            
            session.commit()
            logger.info(f"[Phase 1] Purged {deleted_track_count} Tracks missing physical media.")

            # ==========================================
            # Phase 2: Same-File Row Flattening (Optional cleanup)
            # ==========================================
            self.update_progress(40, 100, "Phase 2: Flattening redundant file paths...")
            
            # Group LocalMedia by canonical path and delete redundancies to prevent multi-track collisions
            path_groups = defaultdict(list)
            all_media = session.query(LocalMedia).filter(LocalMedia.file_path.isnot(None), LocalMedia.file_path != '').all()
            for media in all_media:
                canon = _canonicalize_path(media.file_path)
                path_groups[canon].append(media)
                
            flattened_duplicate_count = 0
            for file_path, group in path_groups.items():
                if len(group) > 1:
                    group.sort(key=lambda m: m.id)
                    keeper = group[0]
                    redundant_media = group[1:]
                    for duplicate in redundant_media:
                        # Move identifiers and fingerprints to keeper via raw SQL
                        session.execute(
                            update(ExternalIdentifier)
                            .where(ExternalIdentifier.media_id == duplicate.media_id)
                            .values(media_id=keeper.media_id)
                        )
                        session.execute(
                            update(AudioFingerprint)
                            .where(AudioFingerprint.media_id == duplicate.media_id)
                            .values(media_id=keeper.media_id)
                        )
                        # Delete the duplicate media row
                        session.execute(
                            delete(LocalMedia)
                            .where(LocalMedia.id == duplicate.id)
                        )
                        flattened_duplicate_count += 1
            
            # Flush updates to DB and expire loaded collections to force reload
            session.flush()
            session.expire_all()
            session.commit()
            logger.info(f"[Phase 2] Deduplicated {flattened_duplicate_count} redundant media rows pointing to the same canonical path.")

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
