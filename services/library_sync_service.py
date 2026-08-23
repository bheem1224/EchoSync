import os
import time
import logging
from typing import Dict, List, Set
from concurrent.futures import ThreadPoolExecutor

from core.io_gatekeeper import Gatekeeper
from core.settings import config_manager
from database import get_database, _canonicalize_path
from services.library_watcher import is_path_suppressed
from database.music_database import LocalMedia, TrackArtist, Track, Album, Artist, MusicDatabase
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
        self.db = MusicDatabase(database_path) if database_path else get_database()
        self.gatekeeper = Gatekeeper()

    def sync_library(self, scan_mode: str = "incremental"):
        logger.info(f"Starting library sync in '{scan_mode}' mode...")
        
        # Step 1: Gatekeeper Boundary Check
        library_dir = config_manager.get("storage.library_dir") or config_manager.get("library_dir")
        if not library_dir:
            logger.error("Library sync aborted: No library_dir configured.")
            return

        is_safe = self.gatekeeper.validate_path(library_dir)
        if not is_safe:
            logger.error(f"Library sync aborted: {library_dir} is out of Gatekeeper bounds.")
            return

        # Full rebuild: truncate library tables prior to cold scan
        if scan_mode == "full_rebuild":
            logger.info("Executing full_rebuild: clearing music library tables...")
            with self.db.session_factory() as session:
                session.execute(delete(LocalMedia))
                session.execute(delete(TrackArtist))
                session.execute(delete(Track))
                session.execute(delete(Album))
                session.execute(delete(Artist))
                session.commit()
                logger.info("Tables cleared for full_rebuild.")

        # Step 2: Rapid Directory Walk & mtime Comparison
        logger.info(f"Scanning library directory: {library_dir}")
        db_state: Dict[str, float] = {}
        
        if scan_mode != "full_rebuild":
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
                if is_path_suppressed(file_path):
                    logger.debug(f"Skipping suppressed in-flight path: {file_path}")
                    continue

                canon_path = _canonicalize_path(file_path)
                current_disk_paths.add(canon_path)

                if scan_mode in ("force_rescan", "full_rebuild"):
                    dirty_or_new.append(file_path)
                else:
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
        if orphans and scan_mode != "full_rebuild":
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

        # Step 4: Streaming FFI Ingestion & Incremental Chunked UPSERT Pipeline
        CHUNK_SIZE = 250
        logger.info(f"Extracting metadata and streaming upsert for {len(dirty_or_new)} files (chunk size {CHUNK_SIZE})...")
        
        _dl = config_manager.get("storage.download_dir") or config_manager.get("download_dir")
        if not _dl:
            if "/data/library" in library_dir or "\\data\\library" in library_dir:
                _dl = "/data/downloads"
            else:
                _dl = os.path.join(os.path.dirname(library_dir.rstrip("/\\")), "downloads")
        download_dir = _dl
        os.makedirs(download_dir, exist_ok=True)

        def parse_file(path: str):
            if supervisor.is_current_task_cancelled():
                return None, path
            try:
                return echosync_core.extract_metadata(path), path
            except Exception as e:
                logger.debug(f"Failed to extract metadata from {path}: {e}")
                return None, path
        
        total_affected_rows = 0
        total_extracted_tracks = 0
        ejected_files_count = 0
        chunk = []
        chunk_idx = 0

        def upsert_chunk(tracks_chunk, idx):
            nonlocal total_affected_rows
            if not tracks_chunk:
                return
            with self.db.session_factory() as session:
                TrackRepository.resolve_artists_and_albums(session, tracks_chunk)
                if supervisor.is_current_task_cancelled():
                    logger.info("Library sync cancelled before committing chunk upsert.")
                    return
                affected = TrackRepository.bulk_upsert_tracks(session, tracks_chunk)
                session.commit()
                total_affected_rows += (affected or 0)
            logger.info(f"Upserted chunk {idx} ({len(tracks_chunk)} tracks)...")
            time.sleep(0.01)

        import shutil
        with ThreadPoolExecutor(max_workers=min(2, os.cpu_count() or 1)) as executor:
            for raw_dict, file_path in executor.map(parse_file, dirty_or_new):
                if supervisor.is_current_task_cancelled():
                    logger.info("Library sync cancelled during streaming extraction.")
                    return

                # Check unidentifiable files (e.g. untagged WAV / missing title/artist)
                title = None
                artist = None
                if raw_dict:
                    title = raw_dict.get("title") or raw_dict.get("raw_title")
                    artist = raw_dict.get("artist_name") or raw_dict.get("artist")

                title_str = str(title).strip() if title else ""
                artist_str = str(artist).strip() if artist else ""

                is_unidentifiable = (
                    not title_str
                    or not artist_str
                    or title_str.lower() in {"unknown title", "untitled", "unknown"}
                    or artist_str.lower() in {"unknown artist", "unknown"}
                )

                if is_unidentifiable and os.path.exists(file_path):
                    logger.warning(f"Unidentifiable media file detected: '{file_path}'. Ejecting to staging: '{download_dir}'.")
                    try:
                        dest_file_name = os.path.basename(file_path)
                        dest_path = os.path.join(download_dir, dest_file_name)
                        if os.path.exists(dest_path) and os.path.abspath(dest_path) != os.path.abspath(file_path):
                            base, ext = os.path.splitext(dest_file_name)
                            dest_path = os.path.join(download_dir, f"{base}_{int(time.time())}{ext}")
                        shutil.move(file_path, dest_path)
                        logger.info(f"Moved unidentifiable file: '{file_path}' -> '{dest_path}'")

                        with self.db.session_factory() as session:
                            TrackRepository.purge_ejected_media_cascade(session, file_path)

                        # Prune empty parent directories in library after ejection
                        from core.utils.file_utils import prune_empty_parent_directories
                        lib_stop_roots = {Path(library_dir).resolve()} if library_dir else set()
                        prune_empty_parent_directories(file_path, stop_at_roots=lib_stop_roots)

                        ejected_files_count += 1
                    except Exception as e:
                        logger.error(f"Failed to eject unidentifiable file {file_path}: {e}", exc_info=True)
                    continue

                if raw_dict is None:
                    continue

                track = _parse_telemetry_dict(raw_dict)
                if track:
                    chunk.append(track)
                    total_extracted_tracks += 1

                if len(chunk) >= CHUNK_SIZE:
                    chunk_idx += 1
                    upsert_chunk(chunk, chunk_idx)
                    chunk.clear()

        # Upsert any remaining tracks in the final chunk
        if chunk:
            if not supervisor.is_current_task_cancelled():
                chunk_idx += 1
                upsert_chunk(chunk, chunk_idx)
            chunk.clear()

        # Clear file paths list to free memory
        dirty_or_new.clear()

        logger.info(f"Upserted {total_extracted_tracks} tracks across {chunk_idx} chunk(s) affecting {total_affected_rows} rows.")

        if ejected_files_count > 0:
            logger.info(f"Ejected {ejected_files_count} unidentifiable file(s) to downloads directory. Enqueueing auto-importer.")
            try:
                from services.auto_importer import AutoImporter
                AutoImporter.enqueue_scan()
            except Exception as e:
                logger.warning(f"Failed to trigger auto-importer: {e}")

        # Post-sync bottom-up cleanup of empty library directories
        try:
            from core.utils.file_utils import prune_empty_directories_tree
            pruned_dirs = prune_empty_directories_tree(library_dir)
            if pruned_dirs > 0:
                logger.info(f"Pruned {pruned_dirs} empty directory(ies) across library tree.")
        except Exception as prune_err:
            logger.warning(f"Failed to prune empty library directories: {prune_err}")

        # Release system memory / trigger glibc malloc_trim
        try:
            from core.task_manager.supervisor import release_system_memory
            release_system_memory()
        except Exception:
            pass

        logger.info("Library sync complete.")
