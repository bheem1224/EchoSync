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
        file_count = 0
        from core.task_manager.supervisor import supervisor

        for root, _, files in os.walk(library_dir):
            if supervisor.is_current_task_cancelled():
                logger.info("Library sync cancelled during directory walk.")
                return

            for file in files:
                file_count += 1
                if file_count % 100 == 0 and supervisor.is_current_task_cancelled():
                    logger.info("Library sync cancelled during directory walk.")
                    return

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

        if supervisor.is_current_task_cancelled():
            logger.info("Library sync cancelled after directory walk.")
            return

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
                    if supervisor.is_current_task_cancelled():
                        logger.info("Library sync cancelled during orphan pruning.")
                        return
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

        if supervisor.is_current_task_cancelled():
            logger.info("Library sync cancelled before metadata extraction.")
            return

        # Step 4: Targeted Threaded FFI Ingestion
        logger.info(f"Extracting metadata for {len(dirty_or_new)} files...")
        
        raw_dicts = []
        def parse_file(path: str):
            if supervisor.is_current_task_cancelled():
                return None
            try:
                return echosync_core.extract_metadata(path)
            except Exception as e:
                logger.debug(f"Failed to extract metadata from {path}: {e}")
                return None
        
        with ThreadPoolExecutor(max_workers=min(2, os.cpu_count() or 1)) as executor:
            results = list(executor.map(parse_file, dirty_or_new))
            for res in results:
                if res is not None:
                    raw_dicts.append(res)

        # Clear file paths list to free memory
        dirty_or_new.clear()

        if supervisor.is_current_task_cancelled():
            logger.info("Library sync cancelled after metadata extraction.")
            return
                    
        tracks = []
        for raw_dict in raw_dicts:
            if supervisor.is_current_task_cancelled():
                logger.info("Library sync cancelled during track parsing.")
                return
            track = _parse_telemetry_dict(raw_dict)
            if track:
                tracks.append(track)

        # Clear raw dicts list to free memory
        raw_dicts.clear()

        if supervisor.is_current_task_cancelled():
            logger.info("Library sync cancelled before database upsert.")
            return

        # Step 5: Relational Hydration & Batch UPSERT in Chunks
        if tracks:
            CHUNK_SIZE = 250
            total_tracks = len(tracks)
            total_chunks = (total_tracks + CHUNK_SIZE - 1) // CHUNK_SIZE
            logger.info(f"Batch upserting {total_tracks} tracks to database in {total_chunks} chunks (chunk size {CHUNK_SIZE})...")

            total_affected_rows = 0
            for chunk_idx in range(total_chunks):
                if supervisor.is_current_task_cancelled():
                    logger.info("Library sync cancelled during chunked upsert.")
                    return

                start_i = chunk_idx * CHUNK_SIZE
                end_i = min(start_i + CHUNK_SIZE, total_tracks)
                chunk = tracks[start_i:end_i]

                with self.db.session_factory() as session:
                    TrackRepository.resolve_artists_and_albums(session, chunk)
                    if supervisor.is_current_task_cancelled():
                        logger.info("Library sync cancelled before committing chunk upsert.")
                        return
                    affected = TrackRepository.bulk_upsert_tracks(session, chunk)
                    session.commit()
                    total_affected_rows += (affected or 0)

                logger.info(f"Upserted chunk {chunk_idx + 1}/{total_chunks} ({len(chunk)} tracks)...")

                # Explicitly yield GIL and allow the event loop to process web requests & other transactions
                time.sleep(0.01)

            logger.info(f"Upserted tracks affecting {total_affected_rows} rows.")

        # Release system memory / trigger glibc malloc_trim
        try:
            from core.task_manager.supervisor import release_system_memory
            release_system_memory()
        except Exception:
            pass

        logger.info("Library sync complete.")
