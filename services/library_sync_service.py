import os
import time
import logging
from typing import Dict, List, Set
from concurrent.futures import ThreadPoolExecutor

from core.io_gatekeeper import Gatekeeper
from core.settings import config_manager
from database import get_database, _canonicalize_path
from database.music_database import LocalMedia, Track
from core.orchestrator.ingestion import _parse_telemetry_dict
from core.database.repositories.track_repo import TrackRepository
import echosync_core
from sqlalchemy import delete, select

logger = logging.getLogger("LibrarySyncService")


class LibrarySyncService:
    """
    High-performance O(1) Library Synchronizer.
    Replaces the legacy DatabaseUpdateWorker.
    """
    
    def __init__(self, database_path: str = None):
        self.db = get_database(database_path)
        self.gatekeeper = Gatekeeper()

    def sync_library(self):
        logger.info("Starting O(1) library sync...")
        
        # Step 1: Gatekeeper Boundary Check
        library_dir = config_manager.get("storage.library_dir") or config_manager.get("library_dir")
        if not library_dir:
            logger.error("Library sync aborted: No library_dir configured.")
            return

        is_safe = self.gatekeeper.validate_path(library_dir)
        if not is_safe:
            logger.error(f"Library sync aborted: {library_dir} is out of Gatekeeper bounds.")
            return

        # Step 2: Rapid Directory Walk & mtime Comparison
        logger.info(f"Scanning library directory: {library_dir}")
        db_state: Dict[str, float] = {}
        
        with self.db.session_factory() as session:
            rows = session.execute(select(LocalMedia.file_path, LocalMedia.mtime)).all()
            for r in rows:
                db_state[r.file_path] = r.mtime or 0.0

        current_disk_paths: Set[str] = set()
        dirty_or_new: List[str] = []

        start_walk = time.time()
        for root, _, files in os.walk(library_dir):
            for file in files:
                if not file.lower().endswith(('.flac', '.mp3', '.m4a', '.ogg', '.opus', '.wav', '.wma', '.aac')):
                    continue
                
                file_path = os.path.join(root, file)
                canon_path = _canonicalize_path(file_path)
                current_disk_paths.add(canon_path)

                try:
                    stat = os.stat(file_path)
                    st_mtime = stat.st_mtime
                except Exception as e:
                    logger.debug(f"Failed to stat {file_path}: {e}")
                    continue

                db_mtime = db_state.get(canon_path)
                if db_mtime is None or st_mtime > db_mtime:
                    dirty_or_new.append(file_path)

        walk_time = time.time() - start_walk
        logger.info(f"Walk completed in {walk_time:.2f}s. Found {len(dirty_or_new)} dirty/new files.")

        db_paths = set(db_state.keys())
        orphans = list(db_paths - current_disk_paths)

        # Step 3: Orphan Reconciliation
        if orphans:
            logger.info(f"Reconciling {len(orphans)} orphaned paths.")
            with self.db.session_factory() as session:
                # Delete LocalMedia
                # Splitting into chunks to avoid SQLite parameter limits
                chunk_size = 900
                for i in range(0, len(orphans), chunk_size):
                    chunk = orphans[i:i + chunk_size]
                    session.execute(delete(LocalMedia).where(LocalMedia.file_path.in_(chunk)))
                
                # Prune empty tracks
                subq = select(LocalMedia.track_id).distinct()
                session.execute(delete(Track).where(Track.id.not_in(subq)))
                session.commit()
                logger.info("Orphans pruned successfully.")

        if not dirty_or_new:
            logger.info("No new or modified files. Sync complete.")
            return

        # Step 4: Targeted Threaded FFI Ingestion
        logger.info(f"Extracting metadata for {len(dirty_or_new)} files...")
        
        raw_dicts = []
        def parse_file(path: str):
            try:
                return echosync_core.extract_metadata(path)
            except Exception as e:
                logger.debug(f"Failed to extract metadata from {path}: {e}")
                return None
        
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            results = list(executor.map(parse_file, dirty_or_new))
            for res in results:
                if res is not None:
                    raw_dicts.append(res)
                    
        tracks = []
        for raw_dict in raw_dicts:
            track = _parse_telemetry_dict(raw_dict)
            if track:
                tracks.append(track)

        # Step 5: Relational Hydration & Batch UPSERT
        if tracks:
            logger.info(f"Batch upserting {len(tracks)} tracks to database...")
            with self.db.session_factory() as session:
                TrackRepository.resolve_artists_and_albums(session, tracks)
                affected_rows = TrackRepository.bulk_upsert_tracks(session, tracks)
                session.commit()
                logger.info(f"Upserted tracks affecting {affected_rows} rows.")

        logger.info("Library sync complete.")
