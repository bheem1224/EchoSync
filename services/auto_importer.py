"""
Auto Import Service - Orchestrator for scanning, identifying, and importing audio files.

This service is responsible for:
1. Watching the download directory for new files via OS filesystem events (watchdog).
2. Falling back to a periodic scheduled scan for files missed during downtime.
3. Coordinating with MetadataEnhancerService to identify files.
4. Decision making (Auto-Import vs Review Queue).
5. Moving and Renaming files (using "Keep Both" conflict resolution).

Event-Driven model
------------------
The watchdog observer monitors the download directory in real-time.  When a new
audio file is created or an incomplete file is renamed into place (the common
download-manager pattern), a 5-second debounce timer fires and then calls
``process_batch([path])`` from the background observer thread.

The scheduled ``scan_and_process`` job still runs every 5 minutes as a safety
net for files written while the service was offline.

48-Hour Review Queue backoff
----------------------------
Files already sitting in the Review Queue with status ``pending`` are skipped
both by the watcher and the scheduled scan unless their ``updated_at`` timestamp
is more than 48 hours in the past.  This prevents hammering AcoustID and
MusicBrainz for recently-failed tracks on every scan cycle.
"""

import os
import threading
from datetime import timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from watchdog.events import FileSystemEventHandler, FileSystemEvent  # type: ignore[import-untyped]
from watchdog.observers import Observer  # type: ignore[import-untyped]

from core.settings import config_manager
from core.job_queue import register_job
from core.tiered_logger import get_logger
from services.metadata_enhancer import RetroactiveEnhancer
from database.working_database import get_working_database, ReviewTask

logger = get_logger("services.auto_importer")

# Audio extensions monitored by the watchdog handler.
_AUDIO_EXTENSIONS: frozenset[str] = frozenset({
    '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.alac', '.ape',
    '.wav', '.dsd', '.dsf', '.dff',
})

# How long to wait after the last filesystem event before attempting to read
# the file.  Covers download managers that either write in chunks or rename a
# .tmp file into place — both patterns generate multiple events per file.
_DEBOUNCE_SECONDS: float = 5.0

# Pending review queue items younger than this window are skipped to avoid
# hammering AcoustID / MusicBrainz for recently-failed tracks.
_REVIEW_QUEUE_BACKOFF: timedelta = timedelta(hours=48)


class AutoImportService:
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        _lib = config_manager.get('storage.library_dir') or config_manager.get('library_dir')
        self.library_root = Path(_lib) if _lib else None
        self.enhancer = RetroactiveEnhancer()
        self._scan_lock = threading.Lock()
        self._processing_lock = threading.Lock()
        self._processing_files = set()
        self._recently_completed = {}  # Track completed files to avoid duplicate processing
        # Watchdog state
        self._observer: Any = None
        self._handler: "_DownloadDirEventHandler | None" = None
        self._register_jobs()
        self._start_watcher()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = AutoImportService()
        return cls._instance

    # ── Watchdog lifecycle ────────────────────────────────────────────────────

    def _start_watcher(self) -> None:
        """Start a watchdog Observer on the download directory.

        If the directory is not configured or does not exist yet, the observer
        is not started — the scheduled ``scan_and_process`` job acts as the
        fallback in that case.
        """
        _dl = config_manager.get('storage.download_dir') or config_manager.get('download_dir')
        download_dir = Path(_dl) if _dl else None
        if not download_dir:
            logger.info(
                "Auto-importer watchdog: download directory not configured — "
                "relying on scheduled scan only."
            )
            return

        download_path = Path(download_dir)
        if not download_path.exists():
            logger.info(
                "Auto-importer watchdog: download directory does not exist yet (%s) — "
                "relying on scheduled scan only.",
                download_path,
            )
            return

        self._handler = _DownloadDirEventHandler(self)
        self._observer = Observer()
        self._observer.schedule(self._handler, str(download_path), recursive=True)
        self._observer.start()
        logger.info(
            "Auto-importer watchdog started — monitoring '%s' (recursive, debounce=%.1fs)",
            download_path,
            _DEBOUNCE_SECONDS,
        )

    def stop_watcher(self) -> None:
        """Gracefully shut down the watchdog observer and cancel pending debounce timers."""
        if self._handler is not None:
            self._handler.cancel_all()
        if self._observer is not None:
            self._observer.stop()
            try:
                self._observer.join(timeout=5)
            except Exception as exc:
                logger.warning("Auto-importer watchdog join error: %s", exc)
        self._observer = None
        self._handler = None
        logger.info("Auto-importer watchdog stopped.")

    def _register_jobs(self):
        """Register background jobs"""
        register_job(
            name="auto_import_scan",
            func=self.scan_and_process,
            interval_seconds=10800,  # 3 hours fallback — real-time coverage is via Watchdog
            start_after=600,  # Wait 10 minutes before first poll so boot completes first
            enabled=True,
            tags=["echosync", "import"],
            max_retries=3
        )

    def scan_and_process(self, force_scan: bool = False, params: Optional[Dict[str, Any]] = None, **kwargs):
        """Scan download directory for audio files and process them."""
        params = params or {}
        if force_scan:
            params["force_scan"] = True
        if not self._scan_lock.acquire(blocking=False):
            logger.info("Auto-import scan skipped: Another scan/process is already running.")
            return
        meta_config = config_manager.get('metadata_enhancement') or {}

        try:
            if not meta_config.get('enabled', True):
                logger.info("Auto-import scan skipped: Feature disabled in settings.")
                return

            _dl = config_manager.get('storage.download_dir') or config_manager.get('download_dir')
            download_dir = Path(_dl) if _dl else None
            logger.debug(f"Download directory from config: {download_dir}")
            logger.debug(f"Download directory type: {type(download_dir)}")
            logger.debug(f"Download directory exists: {download_dir.exists() if download_dir else 'None'}")
            
            if not download_dir:
                logger.error("Download directory is None!")
                return
                
            if not download_dir.exists():
                logger.warning(f"Auto-import scan skipped: Download directory does not exist ({download_dir})")
                logger.debug(f"Attempted to access: {download_dir.resolve()}")
                return

            logger.debug(f"Starting scan of download directory: {download_dir}")
            supported_exts = {'.mp3', '.flac', '.ogg', '.m4a', '.aac', '.alac', '.ape', '.wav', '.dsd', '.dsf', '.dff'}
            files_to_process = []
            stats = {"found": 0, "imported": 0, "pending_review": 0, "failed": 0}

            for root, dirs, files in os.walk(download_dir):
                logger.debug(f"Scanning directory: {root}")
                logger.debug(f"Found {len(files)} files in {root}")
                for file in files:
                    path = Path(root) / file
                    logger.debug(f"Checking file: {path}")
                    if path.suffix.lower() in supported_exts:
                        logger.debug(f"File matches audio extension: {path.suffix}")

                        # Check if file is ignored via DB check (avoids loading all ignored files into memory)
                        if self._is_path_ignored(str(path), params=params):
                            logger.debug(f"File is ignored in review queue, skipping: {path}")
                            continue

                        with self._processing_lock:
                            if str(path) in self._processing_files:
                                logger.debug(f"File already being processed, skipping: {path}")
                                continue
                        logger.debug(f"File not in ignored queue, adding: {path}")
                        files_to_process.append(path)
                        stats["found"] += 1

            if files_to_process:
                logger.info(f"Found {len(files_to_process)} new files to process")
                batch_stats = self.process_batch(files_to_process)
                if batch_stats:
                    stats["imported"] += batch_stats.get("imported", 0)
                    stats["pending_review"] += batch_stats.get("pending_review", 0)
                    stats["failed"] += batch_stats.get("failed", 0)
            else:
                logger.info(f"Auto-import scan completed: No new files found in {download_dir}")
                
            logger.info(f"[system] - Auto-import complete. Found: {stats['found']} | Imported: {stats['imported']} | Pending Review: {stats['pending_review']} | Failed: {stats['failed']}")
        finally:
            self._scan_lock.release()

    def _is_path_ignored(self, file_path: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """Check if a file should be skipped by the scanner.

        Returns True for:
        * Files explicitly marked ``ignored`` in the Review Queue.
        * Files with a ``pending`` Review Queue entry whose ``updated_at``
          is within the 48-hour backoff window.  This prevents re-querying
          AcoustID / MusicBrainz for recently-failed tracks on every scan.
        """
        work_db = get_working_database()
        try:
            with work_db.session_scope() as session:
                task = (
                    session.query(ReviewTask)
                    .filter(ReviewTask.file_path == file_path)
                    .first()
                )
                if task is None:
                    return False

                if task.status == 'ignored':
                    return True

                if task.status == 'pending':
                    if params and params.get("force_scan"):
                        logger.info("[system] - Force scan enabled: Bypassing cooldown queue.")
                    else:
                        # Use updated_at if available (column added in migration
                        # a1b2c3d4e5f6), otherwise fall back to created_at so the
                        # guard works even on databases that haven't been migrated
                        # yet (e.g. in CI / test environments running without a
                        # live Alembic upgrade).
                        last_attempt = getattr(task, 'updated_at', None) or task.created_at
                        if last_attempt is not None:
                            from time_utils import utc_now
                            age = utc_now() - last_attempt
                            if age < _REVIEW_QUEUE_BACKOFF:
                                logger.debug(
                                    "Skipping pending review item (%.1fh old, backoff=48h): %s",
                                    age.total_seconds() / 3600,
                                    file_path,
                                )
                                return True

                return False
        except Exception as e:
            logger.error(f"Error checking ignored status for {file_path}: {e}")
            return False

    def process_batch(self, files: List[Path]):
        """Process a batch of files: Identify → Decide → (Tag & Move) OR Queue.

        Files are grouped by parent directory before identification so
        MetadataEnhancerService can apply its per-album memory cache.  This
        eliminates N−1 redundant AcoustID / MusicBrainz calls when multiple
        tracks from the same album arrive together (the common case for
        downloaded albums).

        Decision Logic:
        - Metadata identification FAILS → Queue for manual review
        - metadata found AND auto_import ON AND confidence >= threshold → Auto-import
        - Otherwise → Queue for manual review
        """
        import time

        meta_config = config_manager.get('metadata_enhancement') or {}
        auto_import = meta_config.get('auto_import', False)
        confidence_threshold = meta_config.get('confidence_threshold', 90) / 100.0
        
        batch_stats = {"imported": 0, "pending_review": 0, "failed": 0}

        # Purge stale completion markers in one pass.
        now = time.time()
        stale = [k for k, ts in self._recently_completed.items() if now - ts >= 10]
        for k in stale:
            del self._recently_completed[k]

        # ── Phase 1: filter and group eligible files by parent directory ──────
        by_dir: Dict[str, List[Path]] = {}
        for file_path in files:
            file_key = str(file_path)
            if file_key in self._recently_completed:
                logger.debug("File recently processed, skipping: %s", file_path)
                continue

            with self._processing_lock:
                if file_key in self._processing_files:
                    logger.debug("File already being processed, skipping: %s", file_path)
                    continue
                self._processing_files.add(file_key)

            if not file_path.exists():
                logger.warning("File disappeared before processing: %s", file_path)
                with self._processing_lock:
                    self._processing_files.discard(file_key)
                continue

            by_dir.setdefault(str(file_path.parent), []).append(file_path)

        # ── Phase 2: identify each directory group together (album-aware) ─────
        for dir_path, dir_files in by_dir.items():
            logger.info(
                "Processing directory group: %s (%d file(s))", dir_path, len(dir_files)
            )
            try:
                dir_files_str = [str(f) for f in dir_files]
                batch_results = self.enhancer.identify_batch(dir_files_str)
            except Exception as exc:
                logger.error(
                    "identify_batch error for '%s': %s", dir_path, exc, exc_info=True
                )
                batch_results = {}

            # ── Phase 3: per-file decision logic (Chunked Concurrency) ─────────
            import asyncio

            CHUNK_SIZE = 50
            for chunk_start in range(0, len(dir_files), CHUNK_SIZE):
                chunk_files = dir_files[chunk_start:chunk_start + CHUNK_SIZE]

                # Step D: Process Results and Finalize
                for file_path in chunk_files:
                    res = batch_results.get(str(file_path))
                    metadata, confidence = res if res else (None, 0.0)
                    file_key = str(file_path)
                    try:
                        # Finally Decide
                        if metadata and confidence >= confidence_threshold:
                            if auto_import:
                                self.finalize_import(file_path, metadata)
                                batch_stats["imported"] += 1
                            else:
                                logger.info(f"Match found but auto_import is False for {file_path}")
                                self.enhancer.create_or_update_review_task(
                                    str(file_path), "Match found but auto_import is False", match_data=metadata
                                )
                                batch_stats["pending_review"] += 1
                        else:
                            self.enhancer.create_or_update_review_task(
                                str(file_path), "No confident match found", match_data=metadata
                            )
                            batch_stats["pending_review"] += 1

                    except Exception as e:
                        logger.error(f"Error processing decision for {file_path}: {e}", exc_info=True)
                        try:
                            self.enhancer.create_or_update_review_task(
                                str(file_path), f"Error processing decision: {e}", match_data=None
                            )
                            batch_stats["pending_review"] += 1
                        except Exception as e2:
                            logger.error(f"Failed to create review task for {file_path}: {e2}")
                            batch_stats["failed"] += 1
                    finally:
                        self._recently_completed[file_key] = time.time()
                        with self._processing_lock:
                            self._processing_files.discard(file_key)

                # Yield to let tasks clear out
                asyncio.run(asyncio.sleep(0))

                # Cleanup empty directories.
        for f in files:
            self._cleanup_empty_directories(f.parent)
            
        return batch_stats

    def finalize_import(self, file_path: Path, metadata: Dict[str, Any]):
        """
        Public method to Tag and Move a file.
        Used by Auto-Import logic and 'Approve' button in UI.
        
        SAFETY: Validates metadata before moving file to library.
        """
        # SAFETY CHECK: Ensure we have valid metadata before moving
        if not metadata or not isinstance(metadata, dict):
            raise ValueError(f"Cannot finalize import: invalid metadata for {file_path.name}")
        
        # Ensure critical fields exist
        required_fields = ['title', 'artist']
        missing = [field for field in required_fields if not metadata.get(field)]
        if missing:
            raise ValueError(f"Cannot finalize import: missing required metadata fields {missing} for {file_path.name}")

        # 1. Tag
        self.enhancer.tag_file(file_path, metadata)

        # 2. Move
        self._move_file(file_path, metadata)

        # 3. Update Review Task status if it exists
        self.enhancer.create_or_update_review_task(file_path, metadata, 1.0, status='approved')

    def _move_file(self, file_path: Path, metadata: Dict[str, Any]):
        """
        Rename and move file to library with 'Keep Both' conflict resolution.
        """
        try:
            # Load template from config
            meta_config = config_manager.get('metadata_enhancement') or {}
            template = meta_config.get('naming_template', "{Artist}/{Album}/{Track} - {Title}.{ext}")

            from core.utils import extract_primary_artist
            raw_artist = metadata.get('artist') or "Unknown Artist"
            primary_artist = extract_primary_artist(raw_artist)
            artist = self._sanitize(primary_artist)
            
            album = self._sanitize(metadata.get('album') or "Unknown Album")
            title = self._sanitize(metadata.get('title') or file_path.stem)

            track_num = metadata.get('track_number')
            track_padded = f"{int(track_num):02d}" if track_num and str(track_num).isdigit() else "00"

            year = str(metadata.get('date', '0000'))[:4]
            ext = file_path.suffix.lower().lstrip('.')

            # Replace tokens
            new_name = template.replace("{Artist}", artist)\
                               .replace("{Album}", album)\
                               .replace("{Track}", track_padded)\
                               .replace("{Title}", title)\
                               .replace("{Year}", year)\
                               .replace("{Format}", ext)\
                               .replace("{ext}", ext)

            # Destination Path
            rel_path = Path(new_name)
            dest_path = self.library_root / rel_path

            # Force Keep Both / Rename Duplicate logic
            if dest_path.exists() and dest_path.resolve() != file_path.resolve():
                counter = 1
                stem = dest_path.stem
                parent = dest_path.parent
                ext_with_dot = dest_path.suffix

                while dest_path.exists() and dest_path.resolve() != file_path.resolve():
                    dest_path = parent / f"{stem} ({counter}){ext_with_dot}"
                    counter += 1

            moved_to = LocalFileHandler.get_instance().safe_move(file_path, dest_path)
            logger.info(f"Moved {file_path.name} → {moved_to}")

        except Exception as e:
            logger.error(f"Failed to move file {file_path}: {e}")
            raise e

    def _sanitize(self, filename: str) -> str:
        """Sanitize filename components"""
        import re
        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename).strip()

    def _cleanup_empty_directories(self, directory: Path):
        """Recursively remove empty directories."""
        try:
            if not directory.exists():
                return
            _dl = config_manager.get('storage.download_dir') or config_manager.get('download_dir')
            download_dir = Path(_dl) if _dl else None
            if directory == download_dir:
                return
            if not any(directory.iterdir()):
                directory.rmdir()
                self._cleanup_empty_directories(directory.parent)
        except Exception:
            pass

def get_auto_importer():
    return AutoImportService.get_instance()

def register_auto_import_service():
    service = AutoImportService.get_instance()
    logger.info("Auto Import Service initialized, watchdog started, and jobs registered")


# ── Watchdog event handler ─────────────────────────────────────────────────────

class _DownloadDirEventHandler(FileSystemEventHandler):
    """Watchdog handler that debounces new audio files in the download directory.

    When a file write/rename event fires, a 5-second timer is (re-)scheduled.
    Once the timer expires without another event for the same path, the file is
    handed to :meth:`AutoImportService.process_batch`.  This ensures that
    partially-written or still-downloading files are never read prematurely.
    """

    def __init__(self, service: AutoImportService) -> None:
        super().__init__()
        self._service = service
        # Maps resolved abs path → active threading.Timer
        self._pending: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    # ── Watchdog callbacks ─────────────────────────────────────────────────

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(os.fsdecode(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        # on_moved fires when a download manager renames a .part/.tmp → .flac etc.
        # We care about the *destination* path.
        if event.is_directory:
            return
        dest = getattr(event, "dest_path", event.src_path)
        self._schedule(os.fsdecode(dest))

    # ── Internal helpers ───────────────────────────────────────────────────

    def _schedule(self, raw_path: str) -> None:
        """(Re-)schedule processing for *raw_path* after the debounce window."""
        path = Path(raw_path)
        if path.suffix.lower() not in _AUDIO_EXTENSIONS:
            return

        abs_path = str(path.resolve())

        with self._lock:
            existing = self._pending.pop(abs_path, None)
            if existing is not None:
                existing.cancel()

            timer = threading.Timer(
                _DEBOUNCE_SECONDS,
                self._fire,
                args=(abs_path,),
            )
            timer.daemon = True
            self._pending[abs_path] = timer
            timer.start()
            logger.debug(
                "Auto-importer watchdog: scheduled processing for '%s' in %.0fs",
                path.name,
                _DEBOUNCE_SECONDS,
            )

    def _fire(self, abs_path: str) -> None:
        """Called by the debounce timer once the settling window has elapsed."""
        with self._lock:
            self._pending.pop(abs_path, None)

        p = Path(abs_path)
        if not p.exists():
            logger.debug("Auto-importer watchdog: file vanished before debounce expired: %s", abs_path)
            return

        logger.info("Auto-importer watchdog: debounce elapsed — processing '%s'", p.name)
        try:
            self._service.process_batch([p])
        except Exception as exc:
            logger.error(
                "Auto-importer watchdog: unexpected error processing '%s': %s",
                p.name,
                exc,
                exc_info=True,
            )

    def cancel_all(self) -> None:
        """Cancel all pending debounce timers (called on service stop)."""
        with self._lock:
            for timer in self._pending.values():
                timer.cancel()
            self._pending.clear()

