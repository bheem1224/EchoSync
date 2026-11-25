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
from dataclasses import is_dataclass, replace
from datetime import timedelta
from pathlib import Path
from typing import Any

from watchdog.events import (  # type: ignore[import-untyped]
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer  # type: ignore[import-untyped]

from core.event_bus import event_bus
from core.task_manager.task_queue import register_job
from core.settings import config_manager
from core.tiered_logger import get_logger
from database.working_database import ReviewTask, get_working_database
from services.metadata_enhancer import RetroactiveEnhancer
from time_utils import utc_now

logger = get_logger("services.auto_importer")

# Audio extensions monitored by the watchdog handler.
_AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".mp3",
        ".flac",
        ".ogg",
        ".m4a",
        ".aac",
        ".alac",
        ".ape",
        ".wav",
        ".dsd",
        ".dsf",
        ".dff",
    }
)

# How long to wait after the last filesystem event before attempting to read
# the file.  Covers download managers that either write in chunks or rename a
# .tmp file into place — both patterns generate multiple events per file.
_DEBOUNCE_SECONDS: float = 5.0

# Pending review queue items younger than this window are skipped to avoid
# hammering AcoustID / MusicBrainz for recently-failed tracks.
_REVIEW_QUEUE_BACKOFF: timedelta = timedelta(hours=48)


_TEMP_EXTENSIONS: tuple[str, ...] = (".tmp", ".part", ".crdownload")


def _is_path_component_ignored(file_path: str | Path, ignored_directories: set[str] | None = None) -> bool:
    """Check if a file or directory path contains an ignored path component."""
    if ignored_directories is None:
        ignored_directories = {"poor_metadata", "incomplete", "quarantine", ".staging"}
    try:
        p = Path(file_path)
        parts_lower = {part.lower().strip("/\\") for part in p.parts}
        if bool(parts_lower.intersection(ignored_directories)):
            return True
        name_lower = p.name.lower()
        if name_lower.endswith(_TEMP_EXTENSIONS) or any(part.lower().endswith(_TEMP_EXTENSIONS) for part in p.parts):
            return True
    except Exception:
        pass
    return False


def parse_fallback_filename(path: str | Path) -> tuple[str | None, str]:
    r"""
    Robust filename parsing for fallback metadata:
    - Strips track number prefixes ("04 - ", "01. ", "00 - ")
    - Splits Artist - Title ONLY on hyphens flanked by whitespace (\s+[-–—]\s+)
    - Preserves internal hyphenated words (e.g. "Drawing-Down")
    """
    import re

    p = Path(path)
    clean_stem = re.sub(r"^\d+[\s\-_.]+", "", p.stem).strip()
    parts = re.split(r"\s+[-–—]\s+", clean_stem, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip() or None, parts[1].strip()
    return None, clean_stem.strip()


class AutoImportService:
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self, library_root: Path | None = None):
        if library_root is not None:
            self.library_root = Path(library_root)
        else:
            _lib = config_manager.get("storage.library_dir") or config_manager.get("library_dir")
            self.library_root = Path(_lib) if _lib else None
        self.enhancer = RetroactiveEnhancer()
        from core.metadata.engine import MetadataResolutionEngine

        self.engine = MetadataResolutionEngine()
        self._scan_lock = threading.Lock()
        self._processing_lock = threading.Lock()
        self._processing_files = set()
        self._recently_completed = {}  # Track completed files to avoid duplicate processing
        self._staged_unidentifiable: dict[int, Path] = {}  # Option B: dl_id -> staged Pick #1 path
        # Watchdog state
        self._observer: Any = None
        self._handler: _DownloadDirEventHandler | None = None
        self._register_jobs()
        self._start_watcher()

        event_bus.subscribe("TRACK_IMPORTED", self._on_track_imported)

    def _on_track_imported(self, payload: dict) -> None:
        """Handle TRACK_IMPORTED by evicting matching pending ReviewTasks and /poor_metadata orphans."""
        try:
            track_data = payload.get("track")
            if not track_data or not isinstance(track_data, dict):
                return

            target_isrc = (track_data.get("isrc") or "").strip().upper()
            target_artist = (track_data.get("artist_name") or track_data.get("artist") or "").strip().lower()
            target_title = (track_data.get("title") or track_data.get("raw_title") or "").strip().lower()
            target_dur = track_data.get("duration_ms") or track_data.get("duration")

            if not target_isrc and (not target_artist or not target_title):
                return

            work_db = get_working_database()
            evicted_count = 0
            with work_db.session_scope() as session:
                pending_tasks = session.query(ReviewTask).filter(ReviewTask.status == "pending").all()
                for task in pending_tasks:
                    cand_meta = task.detected_metadata or {}
                    cand_data = task.track_data or {}
                    cand_isrc = (cand_meta.get("isrc") or cand_data.get("isrc") or "").strip().upper()

                    is_match = False
                    if target_isrc and cand_isrc and target_isrc == cand_isrc:
                        is_match = True
                    else:
                        cand_artist = (
                            (cand_meta.get("artist") or cand_data.get("artist") or cand_data.get("artist_name") or "")
                            .strip()
                            .lower()
                        )
                        cand_title = (
                            (cand_meta.get("title") or cand_data.get("title") or cand_data.get("raw_title") or "")
                            .strip()
                            .lower()
                        )

                        if target_artist and target_title and cand_artist and cand_title:
                            if target_artist == cand_artist and target_title == cand_title:
                                cand_dur = (
                                    cand_data.get("duration_ms")
                                    or cand_data.get("duration")
                                    or cand_meta.get("duration_ms")
                                )
                                if target_dur and cand_dur:
                                    try:
                                        if abs(int(target_dur) - int(cand_dur)) <= 2000:
                                            is_match = True
                                    except (ValueError, TypeError):
                                        is_match = True
                                else:
                                    is_match = True

                    if is_match:
                        logger.info(
                            "Evicting ReviewTask #%s for newly imported track: %s - %s",
                            task.id,
                            target_artist,
                            target_title,
                        )
                        task.status = "approved"
                        task.updated_at = utc_now()
                        evicted_count += 1

                        # Clean up orphan in /poor_metadata if applicable
                        if task.file_path:
                            try:
                                file_p = Path(task.file_path)
                                if "poor_metadata" in {p.lower() for p in file_p.parts} and file_p.exists():
                                    file_p.unlink(missing_ok=True)
                                    logger.info(
                                        "Deleted quarantined orphan file: %s",
                                        task.file_path,
                                    )
                            except Exception as fe:
                                logger.debug(
                                    "Failed to delete quarantined file %s: %s",
                                    task.file_path,
                                    fe,
                                )

            if evicted_count > 0:
                logger.info(
                    "Evicted %d stale review tasks matching imported track.",
                    evicted_count,
                )
        except Exception as e:
            logger.error("Error handling TRACK_IMPORTED in auto_importer: %s", e, exc_info=True)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = AutoImportService()
        return cls._instance

    @classmethod
    def enqueue_scan(cls, force_scan: bool = True) -> None:
        """Trigger an asynchronous auto-import scan managed by JobQueue."""
        from core.enums import TaskCategory
        from core.task_manager.task_queue import job_queue

        instance = cls.get_instance()
        if "auto_import_scan" not in job_queue._jobs:
            job_queue.register_job(
                name="auto_import_scan",
                func=instance.scan_and_process,
                category=TaskCategory.GENERAL,
                params={"force_scan": force_scan},
            )
        job_queue.trigger_job_by_name("auto_import_scan", params={"force_scan": force_scan})

    # ── Watchdog lifecycle ────────────────────────────────────────────────────

    def _start_watcher(self) -> None:
        """Start a watchdog Observer on the download directory.

        If the directory is not configured or does not exist yet, the observer
        is not started — the scheduled ``scan_and_process`` job acts as the
        fallback in that case.
        """
        _dl = config_manager.get("storage.download_dir") or config_manager.get("download_dir")
        download_dir = Path(_dl) if _dl else None
        if not download_dir:
            logger.info("Auto-importer watchdog: download directory not configured — relying on scheduled scan only.")
            return

        download_path = Path(download_dir)
        if not download_path.exists():
            logger.info(
                "Auto-importer watchdog: download directory does not exist yet (%s) — relying on scheduled scan only.",
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
            max_retries=3,
        )
        register_job(
            name="retry_aged_review_tasks",
            func=self._retry_aged_review_tasks,
            interval_seconds=86400,  # Run daily
            start_after=1200,  # Wait 20 minutes before initial check
            enabled=True,
            tags=["echosync", "metadata", "review"],
            max_retries=3,
        )

    def _retry_aged_review_tasks(self, force_check: bool = False, **kwargs) -> None:
        """Proactively re-evaluate review queue items older than 7 days, or all pending items if force_check=True."""
        work_db = get_working_database()
        from time_utils import utc_now

        force_val = kwargs.get("force_check", kwargs.get("force", force_check))
        is_force = force_val if isinstance(force_val, bool) else (str(force_val).lower() in ("true", "1", "yes"))

        cutoff = utc_now() - timedelta(days=7)
        batch_size = 50
        last_seen_id = 0
        total_processed = 0

        meta_config = config_manager.get("metadata_enhancement") or {}
        auto_import = meta_config.get("auto_import", False)
        raw_thresh = float(meta_config.get("confidence_threshold", 90) or 90)
        confidence_threshold = raw_thresh / 100.0 if raw_thresh > 1.0 else raw_thresh

        while True:
            tasks_to_retry: list[dict[str, Any]] = []
            try:
                with work_db.session_scope() as session:
                    query = session.query(ReviewTask).filter(
                        ReviewTask.id > last_seen_id,
                        ReviewTask.status == "pending",
                    )
                    if not is_force:
                        query = query.filter(ReviewTask.updated_at < cutoff)

                    batch = query.order_by(ReviewTask.id.asc()).limit(batch_size).all()
                    if not batch:
                        break

                    for t in batch:
                        tasks_to_retry.append({"id": t.id, "file_path": t.file_path})
                        last_seen_id = t.id
            except Exception as e:
                logger.error(f"Error querying review tasks for re-evaluation: {e}", exc_info=True)
                break

            if not tasks_to_retry:
                break

            if total_processed == 0:
                if is_force:
                    logger.info("Force re-evaluating pending review task(s) (bypassing 7-day age cutoff)...")
                else:
                    logger.info("Re-evaluating aged review task(s) (>7 days old)...")

            for item in tasks_to_retry:
                total_processed += 1
                task_id = item["id"]
                file_path_str = item["file_path"]
                p = Path(file_path_str)

                if not p.exists():
                    logger.info(f"Review task file no longer on disk: {file_path_str}")
                    try:
                        with work_db.session_scope() as session:
                            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
                            if task:
                                task.last_checked_at = utc_now()
                                task.updated_at = utc_now()
                    except Exception:
                        pass
                    continue

                try:
                    metadata = None
                    confidence = 0.0
                    res_dict = None
                    if hasattr(self, "enhancer") and hasattr(self.enhancer, "identify_file"):
                        try:
                            metadata, confidence = self.enhancer.identify_file(p)
                            if metadata:
                                res_dict = metadata
                        except Exception as enh_err:
                            logger.debug("enhancer.identify_file failed, falling back to engine: %s", enh_err)

                    if res_dict is None:
                        from core.metadata.schemas import ResolutionRequest

                        req = ResolutionRequest(
                            media_id=f"review_{task_id}",
                            file_path=p,
                            ignore_cache=True,
                        )
                        res = self.engine.resolve_track(req)
                        metadata = res.to_dict() if (res.success and res.musicbrainz_track_id) else None
                        confidence = res.confidence_score
                        res_dict = res.to_dict()

                    now = utc_now()
                    with work_db.session_scope() as session:
                        task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
                        if task:
                            task.last_checked_at = now
                            task.updated_at = now
                            task.retry_count = (task.retry_count or 0) + 1
                            task.confidence_score = confidence
                            task.detected_metadata = res_dict

                    if metadata and confidence >= confidence_threshold:
                        if auto_import:
                            logger.info(f"Review task match found and auto_import is True; importing: {p}")
                            self.finalize_import(p, metadata)
                        else:
                            logger.info(f"Review task match found but auto_import is False for {p}")
                except Exception as err:
                    logger.warning(f"Failed to re-evaluate review task #{task_id} ({file_path_str}): {err}")
                    try:
                        with work_db.session_scope() as session:
                            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
                            if task:
                                task.last_checked_at = utc_now()
                                task.updated_at = utc_now()
                    except Exception:
                        pass

        if total_processed == 0:
            if is_force:
                logger.debug("No pending review tasks found for force re-evaluation.")
            else:
                logger.debug("No aged review tasks pending re-evaluation (>7 days).")
        else:
            logger.info(f"Finished re-evaluating {total_processed} review task(s).")

    def scan_and_process(self, force_scan: bool = False, params: dict[str, Any] | None = None, **kwargs):
        """Scan download directory for audio files and process them."""
        import time

        from core.system_lock import acquire_library_lock

        params = params or {}
        if force_scan:
            params["force_scan"] = True
        if not self._scan_lock.acquire(blocking=False):
            logger.info("Auto-import scan skipped: Another scan/process is already running.")
            return

        try:
            with acquire_library_lock(task_name="auto_import_scan", blocking=False) as acquired:
                if not acquired:
                    logger.info(
                        "Auto-import scan skipped: Library sync or another library operation is currently running."
                    )
                    return

                meta_config = config_manager.get("metadata_enhancement") or {}
                if not meta_config.get("enabled", True):
                    logger.info("Auto-import scan skipped: Feature disabled in settings.")
                    return

                _dl = config_manager.get("storage.download_dir") or config_manager.get("download_dir")
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
                supported_exts = {
                    ".mp3",
                    ".flac",
                    ".ogg",
                    ".m4a",
                    ".aac",
                    ".alac",
                    ".ape",
                    ".wav",
                    ".dsd",
                    ".dsf",
                    ".dff",
                }
                files_to_process = []
                stats = {"found": 0, "imported": 0, "pending_review": 0, "failed": 0}

                for root, dirs, files in os.walk(download_dir):
                    # Filter out poor_metadata, incomplete, quarantine, and temporary directories
                    dirs[:] = [d for d in dirs if not _is_path_component_ignored(Path(root) / d)]
                    logger.debug(f"Scanning directory: {root}")
                    logger.debug(f"Found {len(files)} files in {root}")
                    for file in files:
                        path = Path(root) / file
                        if _is_path_component_ignored(path):
                            continue

                        logger.debug(f"Checking file: {path}")
                        if path.suffix.lower() in supported_exts:
                            logger.debug(f"File matches audio extension: {path.suffix}")

                            # Strict I/O safety lock check: verify size > 64KB (65536 bytes) and age > 15s
                            try:
                                f_size = os.path.getsize(path)
                                f_mtime = os.path.getmtime(path)
                                if f_size <= 65536:
                                    logger.debug(f"I/O safety guard: skipping file <= 64KB ({f_size} bytes): {path}")
                                    continue
                                if time.time() - f_mtime <= 15:
                                    logger.debug(f"I/O safety guard: skipping file within 15s cool-off: {path}")
                                    continue
                            except Exception as e:
                                logger.debug(f"I/O safety guard check failed for {path}: {e}")
                                continue

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

                logger.info(
                    f"[system] - Auto-import complete. Found: {stats['found']} | Imported: {stats['imported']} | Pending Review: {stats['pending_review']} | Failed: {stats['failed']}"
                )
        finally:
            self._scan_lock.release()

    def _is_path_ignored(self, file_path: str, params: dict[str, Any] | None = None) -> bool:
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
                task = session.query(ReviewTask).filter(ReviewTask.file_path == file_path).first()
                if task is None:
                    return False

                if task.status == "ignored":
                    return True

                if task.status == "pending":
                    if params and params.get("force_scan"):
                        logger.info("[system] - Force scan enabled: Bypassing cooldown queue.")
                    else:
                        # Use updated_at if available (column added in migration
                        # a1b2c3d4e5f6), otherwise fall back to created_at so the
                        # guard works even on databases that haven't been migrated
                        # yet (e.g. in CI / test environments running without a
                        # live Alembic upgrade).
                        last_attempt = getattr(task, "updated_at", None) or task.created_at
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

    def process_batch(self, files: list[Path]):
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

        from core.system_lock import acquire_library_lock

        with acquire_library_lock(task_name="auto_import_batch", blocking=True, timeout=60.0) as acquired:
            if not acquired:
                logger.warning("Auto-import process_batch timed out waiting for library lock.")
                return {"imported": 0, "pending_review": 0, "failed": len(files)}

            meta_config = config_manager.get("metadata_enhancement") or {}
            auto_import = meta_config.get("auto_import", False)
            raw_thresh = float(meta_config.get("confidence_threshold", 90) or 90)
            confidence_threshold = raw_thresh / 100.0 if raw_thresh > 1.0 else raw_thresh

            batch_stats = {"imported": 0, "pending_review": 0, "failed": 0}

            # Purge stale completion markers in one pass.
            now = time.time()
            stale = [k for k, ts in self._recently_completed.items() if now - ts >= 10]
            for k in stale:
                del self._recently_completed[k]

            # ── Phase 1: filter and group eligible files by parent directory ──────
            by_dir: dict[str, list[Path]] = {}
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

                # Strict I/O safety lock
                try:
                    f_size = os.path.getsize(file_path)
                    f_mtime = os.path.getmtime(file_path)
                    if f_size <= 65536:
                        logger.debug(
                            "I/O safety guard: skipping file <= 64KB (%d bytes): %s",
                            f_size,
                            file_path,
                        )
                        with self._processing_lock:
                            self._processing_files.discard(file_key)
                        continue
                    if time.time() - f_mtime <= 4.0:
                        logger.debug(
                            "I/O safety guard: skipping file within 4s cool-off: %s",
                            file_path,
                        )
                        with self._processing_lock:
                            self._processing_files.discard(file_key)
                        continue
                except Exception as stat_err:
                    logger.warning("I/O safety guard: error checking %s: %s", file_path, stat_err)
                    with self._processing_lock:
                        self._processing_files.discard(file_key)
                    continue

                by_dir.setdefault(str(file_path.parent), []).append(file_path)

            # ── Phase 2: identify and decide per directory group ─────
            from core.metadata.schemas import ResolutionRequest

            for dir_path, dir_files in by_dir.items():
                logger.info(
                    "Processing directory group: %s (%d file(s))",
                    dir_path,
                    len(dir_files),
                )

                # ── Phase 3: per-file decision logic (Chunked Concurrency) ─────────
                CHUNK_SIZE = 50
                for chunk_start in range(0, len(dir_files), CHUNK_SIZE):
                    chunk_files = dir_files[chunk_start : chunk_start + CHUNK_SIZE]

                    # Step D: Process Results and Finalize
                    for file_path in chunk_files:
                        file_key = str(file_path)
                        try:
                            req = ResolutionRequest(
                                media_id=f"media_{file_path.stem}",
                                file_path=file_path,
                                ignore_cache=True,
                            )
                            res = self.engine.resolve_track(req)
                            metadata = res.to_dict() if (res.success and res.musicbrainz_track_id) else None
                            confidence = res.confidence_score

                            # Post-download verification against active DownloadQueue intent (if tracked)
                            dl_match = self._find_verifying_download_item(file_path)
                            if dl_match is not None:
                                dl_id, target_track = dl_match
                                from services.download_manager import get_download_manager

                                dm = get_download_manager()
                                allow_remaster_fb = dm.is_remaster_fallback_allowed(dl_id)
                                verified, fail_reason = self._verify_downloaded_file_against_intent(
                                    file_path=file_path,
                                    target_track=target_track,
                                    resolved_track=res,
                                    allow_remaster_fallback=allow_remaster_fb,
                                )
                                if not verified:
                                    if fail_reason == "UNIDENTIFIABLE_AUDIO":
                                        # Option B: Park Pick #1 silently in .staging while trying backups #2/#3.
                                        # Only promote Pick #1 to ReviewTask if all backups also fail to identify.
                                        staged_existing = self._staged_unidentifiable.get(dl_id)
                                        if staged_existing is None:
                                            staged_path = self._stage_unidentifiable_file(dl_id, file_path)
                                            if staged_path is not None:
                                                self._staged_unidentifiable[dl_id] = staged_path
                                            rotated = dm.handle_verification_failure(
                                                dl_id,
                                                reason="UNIDENTIFIABLE_AUDIO",
                                                file_path=None,
                                            )
                                        else:
                                            # Backup is also unidentifiable — delete duplicate backup via Gatekeeper
                                            rotated = dm.handle_verification_failure(
                                                dl_id,
                                                reason="UNIDENTIFIABLE_AUDIO",
                                                file_path=str(file_path),
                                                delete_file=True,
                                            )

                                        if not rotated:
                                            # All backups exhausted — surface single Pick #1 to Review Queue
                                            final_staged = self._staged_unidentifiable.pop(dl_id, None)
                                            if final_staged and final_staged.exists():
                                                logger.info(
                                                    "All backups exhausted for DownloadQueue #%s; promoting staged Pick #1 (%s) to Review Queue.",
                                                    dl_id,
                                                    final_staged.name,
                                                )
                                                self.enhancer.create_or_update_review_task(
                                                    str(final_staged),
                                                    "Unidentifiable download (all backups exhausted)",
                                                    match_data=target_track.to_dict() if hasattr(target_track, "to_dict") else res.to_dict(),
                                                    confidence_score=confidence,
                                                )
                                                batch_stats["pending_review"] += 1
                                        else:
                                            batch_stats["failed"] += 1
                                        continue

                                    # Corrupt audio, fake lossless, interior silence dropout, or confirmed wrong track:
                                    # delete immediately via Gatekeeper and blacklist/rotate to next backup.
                                    logger.warning(
                                        "Post-download verification FAILED for DownloadQueue #%s (%s): %s. "
                                        "Deleting rejected file and rotating candidate.",
                                        dl_id,
                                        file_path.name,
                                        fail_reason,
                                    )
                                    dm.handle_verification_failure(
                                        dl_id,
                                        reason=fail_reason,
                                        file_path=str(file_path),
                                        delete_file=True,
                                    )
                                    batch_stats["failed"] += 1
                                    continue
                                else:
                                    # Verification succeeded — delete any earlier staged unidentifiable Pick #1
                                    self._cleanup_staged_unidentifiable(dl_id)
                                    dm.handle_verification_success(dl_id, file_path=str(file_path))

                            # Finally Decide
                            if metadata and confidence >= confidence_threshold:
                                if auto_import:
                                    self.finalize_import(file_path, metadata)
                                    batch_stats["imported"] += 1
                                else:
                                    logger.info(f"Match found but auto_import is False for {file_path}")
                                    self.enhancer.create_or_update_review_task(
                                        str(file_path),
                                        "Match found but auto_import is False",
                                        match_data=res.to_dict(),
                                        confidence_score=confidence,
                                    )
                                    batch_stats["pending_review"] += 1
                            else:
                                self.enhancer.create_or_update_review_task(
                                    str(file_path),
                                    "No confident match found",
                                    match_data=res.to_dict(),
                                    confidence_score=confidence,
                                )
                                batch_stats["pending_review"] += 1

                        except Exception as e:
                            logger.error(
                                f"Error processing decision for {file_path}: {e}",
                                exc_info=True,
                            )
                            try:
                                self.enhancer.create_or_update_review_task(
                                    str(file_path),
                                    f"Error processing decision: {e}",
                                    match_data=None,
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
                    time.sleep(0.01)

            # Cleanup empty directories.
            for f in files:
                self._cleanup_empty_directories(f.parent)

            return batch_stats

    def _find_verifying_download_item(self, file_path: Path):
        """Find a VERIFYING/DOWNLOADING DownloadQueue entry corresponding to *file_path*."""
        try:
            from core.database.models.working import DownloadQueue, DownloadStatus
            from core.db.echo_sync_track import EchosyncTrack

            target_name = file_path.name.lower()
            target_str = str(file_path).replace("\\", "/").lower()
            work_db = get_working_database()
            with work_db.session_scope() as session:
                items = (
                    session.query(DownloadQueue)
                    .filter(
                        DownloadQueue.status.in_(
                            [DownloadStatus.VERIFYING.value, DownloadStatus.DOWNLOADING.value]
                        )
                    )
                    .order_by(DownloadQueue.updated_at.desc())
                    .all()
                )
                for item in items:
                    payload = item.echo_sync_track if isinstance(item.echo_sync_track, dict) else {}
                    dl_path = str(payload.get("downloaded_file_path") or "").replace("\\", "/").lower()
                    active_cand = str(item.active_candidate_id or "").replace("\\", "/").lower()
                    if (
                        (dl_path and (dl_path == target_str or Path(dl_path).name == target_name))
                        or (active_cand and active_cand.endswith(target_name))
                    ):
                        return item.id, EchosyncTrack.from_dict(payload)
        except Exception as exc:
            logger.debug("DownloadQueue lookup skipped for %s: %s", file_path.name, exc)
        return None

    def _stage_unidentifiable_file(self, dl_id: int, file_path: Path) -> Path | None:
        """Park Pick #1 unidentifiable download silently in downloads/.staging via Gatekeeper."""
        try:
            from core.io_gatekeeper import Gatekeeper

            _dl = config_manager.get("storage.download_dir") or config_manager.get("download_dir")
            staging_root = (Path(_dl) if _dl else file_path.parent) / ".staging"
            staging_root.mkdir(parents=True, exist_ok=True)
            dest = staging_root / f"dl_{dl_id}_{file_path.name}"
            Gatekeeper.authorize_and_execute(
                {
                    "operation": "safe_move",
                    "src": str(file_path),
                    "dst": str(dest),
                }
            )
            logger.info("Staged unidentifiable Pick #1 for DownloadQueue #%s at %s", dl_id, dest)
            return dest
        except Exception as exc:
            logger.warning("Failed to stage unidentifiable file %s: %s", file_path, exc)
            return None

    def _cleanup_staged_unidentifiable(self, dl_id: int) -> None:
        """Delete staged unidentifiable Pick #1 via Gatekeeper once a backup succeeds."""
        staged_path = self._staged_unidentifiable.pop(dl_id, None)
        if not staged_path or not staged_path.exists():
            return
        try:
            from core.io_gatekeeper import Gatekeeper

            Gatekeeper.authorize_and_execute({"operation": "delete", "src": str(staged_path)})
            logger.info("Deleted superseded staged file for DownloadQueue #%s: %s", dl_id, staged_path.name)
        except Exception as exc:
            logger.debug("Failed to delete staged file %s: %s", staged_path, exc)

    def _verify_downloaded_file_against_intent(
        self,
        file_path: Path,
        target_track: Any,
        resolved_track: Any,
        *,
        allow_remaster_fallback: bool = False,
    ) -> tuple[bool, str]:
        """Verify audio integrity, fake-lossless spectrum, mid-track dropouts, duration alignment,
        and semantic/version match before import.
        """
        import echosync_core

        from core.matching_engine.matching_engine import WeightedMatchingEngine
        from core.matching_engine.scoring_profile import ExactSyncProfile

        # 1. Native Rust header probe
        try:
            meta = echosync_core.extract_metadata(str(file_path)) or {}
            raw_dur_ms = meta.get("duration_ms")
            if raw_dur_ms is None and meta.get("duration") is not None:
                raw_dur_ms = int(round(float(meta["duration"]) * 1000))
            if not raw_dur_ms or int(raw_dur_ms) <= 0:
                return False, "CORRUPT_AUDIO"
            raw_dur_ms = int(raw_dur_ms)
        except Exception as exc:
            logger.warning("Audio integrity probe failed for %s: %s", file_path.name, exc)
            return False, "CORRUPT_AUDIO"

        # 2. Single-pass Rust PCM decode + spectral fake-lossless + mid-track digital-zero dropout check
        ext_lower = file_path.suffix.lower().lstrip(".")
        is_lossless_pcm = ext_lower in {"flac", "wav", "alac", "aiff"}
        active_dur_ms = None
        if ext_lower not in {"dsf", "dff", "dsd"}:
            try:
                if hasattr(echosync_core, "analyze_and_fingerprint_audio"):
                    analysis = echosync_core.analyze_and_fingerprint_audio(
                        str(file_path), True, is_lossless_pcm
                    )
                    if analysis.get("is_corrupt"):
                        return False, f"CORRUPT_AUDIO (decode_errors={analysis.get('decode_error_count', 0)})"
                    if is_lossless_pcm and analysis.get("is_fake_lossless"):
                        cutoff = float(analysis.get("estimated_cutoff_hz") or 0.0)
                        drop_db = float(analysis.get("high_freq_drop_db") or 0.0)
                        return False, f"FAKE_LOSSLESS (cutoff={cutoff:.0f}Hz, drop={drop_db:.1f}dB)"
                    if analysis.get("has_interior_silence_dropout"):
                        gap_ms = int(analysis.get("max_interior_silence_ms") or 0)
                        return False, f"INTERIOR_SILENCE_DROPOUT ({gap_ms}ms)"
                    if analysis.get("active_duration_ms") and int(analysis["active_duration_ms"]) > 0:
                        active_dur_ms = int(analysis["active_duration_ms"])
                elif hasattr(echosync_core, "fingerprint_hash_and_active_duration"):
                    _, _, _, active_ms = echosync_core.fingerprint_hash_and_active_duration(str(file_path), True)
                    if active_ms and int(active_ms) > 0:
                        active_dur_ms = int(active_ms)
                else:
                    _, dur_sec, _ = echosync_core.fingerprint_and_hash_audio(str(file_path), True)
                    if dur_sec and float(dur_sec) > 0:
                        active_dur_ms = int(round(float(dur_sec) * 1000))
            except ValueError as decode_err:
                logger.warning("Native PCM decode failed for %s: %s", file_path.name, decode_err)
                return False, "CORRUPT_AUDIO"
            except Exception:
                pass

        # 3. Duration sanity gate against requested target track
        target_dur_ms = getattr(target_track, "duration_ms", None) or getattr(target_track, "duration", None)
        if target_dur_ms and int(target_dur_ms) > 0:
            target_dur_ms = int(target_dur_ms)
            best_delta = abs(raw_dur_ms - target_dur_ms)
            if active_dur_ms:
                best_delta = min(best_delta, abs(active_dur_ms - target_dur_ms))
            if best_delta > 10000:
                return False, f"DURATION_MISMATCH ({best_delta}ms > 10000ms)"

        # 4. Semantic & version cross-check if MetadataResolutionEngine resolved a candidate
        res_title = getattr(resolved_track, "title", None) if resolved_track else None
        res_artist = getattr(resolved_track, "artist_name", None) if resolved_track else None
        res_method = getattr(resolved_track, "resolution_method", None) if resolved_track else None
        res_conf = float(getattr(resolved_track, "confidence_score", 0.0) or 0.0) if resolved_track else 0.0
        res_mbid = (
            getattr(resolved_track, "musicbrainz_track_id", None)
            or getattr(resolved_track, "musicbrainz_id", None)
            if resolved_track
            else None
        )

        # If the resolution engine ran and could not identify the file at all (0 confidence & no MBID),
        # classify as UNIDENTIFIABLE_AUDIO so Option B staging can hold Pick #1 while trying backups.
        if resolved_track is not None and res_method is not None and not res_mbid and res_conf < 0.70:
            return False, "UNIDENTIFIABLE_AUDIO"

        if res_title and res_artist:
            matcher = WeightedMatchingEngine(ExactSyncProfile())
            cand_for_check = resolved_track
            if active_dur_ms and isinstance(getattr(cand_for_check, "extra_metadata", None), dict):
                updated_extra = {**cand_for_check.extra_metadata, "active_duration_ms": active_dur_ms}
                if is_dataclass(cand_for_check) and not isinstance(cand_for_check, type):
                    cand_for_check = replace(cand_for_check, extra_metadata=updated_extra)
                else:
                    cand_for_check.extra_metadata = updated_extra
            match_ctx = "download_remaster_fallback" if allow_remaster_fallback else "sync"
            match_res = matcher.calculate_match(target_track, cand_for_check, context=match_ctx)
            if not match_res.passed_version_check:
                return False, f"MISMATCH_EDITION: {match_res.reasoning}"
            if match_res.confidence_score < 70.0:
                return False, f"MISMATCH_TRACK (score={match_res.confidence_score:.1f}%)"
        elif resolved_track is not None:
            return False, "UNIDENTIFIABLE_AUDIO"

        return True, "OK"

    def finalize_import(self, file_path: Path, metadata: dict[str, Any]):
        """
        Public method to Tag and Move a file.
        Used by Auto-Import logic and 'Approve' button in UI.

        SAFETY: Validates metadata before moving file to library.
        """
        # SAFETY CHECK: Ensure we have valid metadata before moving
        if not metadata or not isinstance(metadata, dict):
            raise ValueError(f"Cannot finalize import: invalid metadata for {file_path.name}")

        # Ensure critical fields exist
        required_fields = ["title", "artist"]
        missing = [field for field in required_fields if not metadata.get(field)]
        if missing:
            raise ValueError(f"Cannot finalize import: missing required metadata fields {missing} for {file_path.name}")

        # 1. Tag and verify
        self.enhancer.tag_file_verified(file_path, metadata)

        # 2. Move & persist/deduplicate into library DB
        dest_path = self._move_file(file_path, metadata)

        # 3. Publish TRACK_IMPORTED so DownloadManager reconciles any matching queue rows
        #    (including FAILED rows from manual retries or when webhooks are disabled)
        try:
            from core.event_bus import event_bus

            track_payload = dict(metadata)
            if "artist_name" not in track_payload and track_payload.get("artist"):
                track_payload["artist_name"] = track_payload["artist"]
            if "album_title" not in track_payload and track_payload.get("album"):
                track_payload["album_title"] = track_payload["album"]
            event_bus.publish(
                "TRACK_IMPORTED",
                {
                    "track": track_payload,
                    "file_path": str(dest_path),
                    "source_file_path": str(file_path),
                },
            )
        except Exception as eb_err:
            logger.debug("Could not publish TRACK_IMPORTED after finalize_import: %s", eb_err)

        # 4. Update Review Task status if it exists
        self.enhancer.create_or_update_review_task(file_path, metadata, 1.0, status="approved")
        return dest_path

    @staticmethod
    def _enrich_physical_telemetry(file_path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
        """Copy metadata and enrich missing physical audio telemetry via echosync_core."""
        meta = dict(metadata)
        try:
            import echosync_core

            raw_probe = echosync_core.extract_metadata(str(file_path)) or {}
            for key in (
                "codec",
                "file_format",
                "bit_depth",
                "sample_rate",
                "bitrate",
                "channels",
                "duration_ms",
                "file_size_bytes",
                "mtime",
                "inode",
            ):
                if meta.get(key) is None and raw_probe.get(key) is not None:
                    meta[key] = raw_probe[key]
        except Exception:
            pass

        if meta.get("file_format") is None:
            meta["file_format"] = (
                str(meta.get("codec") or file_path.suffix).lstrip(".").lower() or None
            )
        if file_path.exists():
            try:
                st = file_path.stat()
                if meta.get("file_size_bytes") is None:
                    meta["file_size_bytes"] = st.st_size
                if meta.get("mtime") is None:
                    meta["mtime"] = st.st_mtime
                if meta.get("inode") is None:
                    meta["inode"] = getattr(st, "st_ino", None)
            except OSError:
                pass
        return meta

    @staticmethod
    def _build_import_track_dto(dest_path: Path, meta: dict[str, Any]) -> Any:
        """Build a normalized EchosyncTrack + EchosyncMedia DTO for imported file persistence."""
        from core.db.echo_sync_track import EchosyncMedia, EchosyncTrack
        from core.matching_engine.track_parser import normalize_track_dto
        from services.library_watcher import _coerce_optional_int

        duration_ms = _coerce_optional_int(meta.get("duration_ms"))
        if duration_ms is None and meta.get("duration") is not None:
            try:
                raw_dur = float(meta["duration"])
                duration_ms = int(round(raw_dur * 1000.0)) if raw_dur < 10000.0 else int(round(raw_dur))
            except (ValueError, TypeError):
                duration_ms = None

        release_year = _coerce_optional_int(meta.get("release_year"))
        if release_year is None and meta.get("year") is not None:
            raw_year = str(meta["year"]).strip()
            if len(raw_year) >= 4 and raw_year[:4].isdigit():
                release_year = int(raw_year[:4])

        file_size = _coerce_optional_int(meta.get("file_size_bytes"))
        mtime_val = meta.get("mtime")
        if dest_path.exists():
            try:
                st = dest_path.stat()
                file_size = st.st_size
                mtime_val = st.st_mtime
            except OSError:
                pass

        title = str(meta.get("title") or meta.get("raw_title") or dest_path.stem)
        artist_name = str(meta.get("artist_name") or meta.get("artist") or "Unknown Artist")
        album_title = str(meta.get("album_title") or meta.get("album") or "")
        file_format = (
            str(meta.get("file_format") or meta.get("codec") or dest_path.suffix)
            .lstrip(".")
            .lower()
            or None
        )

        media_obj = EchosyncMedia(
            file_path=str(dest_path),
            file_format=file_format,
            bitrate=_coerce_optional_int(meta.get("bitrate")),
            sample_rate=_coerce_optional_int(meta.get("sample_rate")),
            bit_depth=_coerce_optional_int(meta.get("bit_depth")),
            channels=_coerce_optional_int(meta.get("channels")),
            duration_ms=duration_ms,
            file_size_bytes=file_size,
            inode=_coerce_optional_int(meta.get("inode")),
            mtime=mtime_val,
        )

        return normalize_track_dto(
            EchosyncTrack(
                raw_title=title,
                title=title,
                artist_name=artist_name,
                album_title=album_title,
                edition=meta.get("edition") or meta.get("version") or None,
                duration_ms=duration_ms,
                track_number=_coerce_optional_int(
                    meta.get("track_number") if meta.get("track_number") is not None else meta.get("track_no")
                ),
                disc_number=_coerce_optional_int(
                    meta.get("disc_number") if meta.get("disc_number") is not None else meta.get("disc_no")
                ),
                release_year=release_year,
                musicbrainz_id=meta.get("musicbrainz_track_id") or meta.get("musicbrainz_id") or meta.get("mbid"),
                mb_release_id=meta.get("musicbrainz_release_id") or meta.get("musicbrainz_album_id") or meta.get("mb_release_id"),
                acoustid_id=meta.get("acoustid_id"),
                fingerprint=meta.get("fingerprint") or meta.get("chromaprint"),
                isrc=meta.get("isrc"),
                media=[media_obj],
            )
        )

    def _move_file(self, file_path: Path, metadata: dict[str, Any]) -> Path:
        """
        Rename and move file to library with collision-safe edition path resolution and
        session.no_autoflush Track deduplication/re-parenting.
        """
        try:
            from sqlalchemy import inspect, or_

            from core.database.repositories.track_repo import TrackRepository
            from core.io_gatekeeper import Gatekeeper
            from core.path_formatter import (
                build_destination_path,
                get_library_preferences,
            )
            from core.task_manager.task_queue import db_write_lease
            from core.utils.file_utils import prune_empty_parent_directories
            from database import _canonicalize_path
            from database.music_database import AudioFingerprint, LocalMedia, get_database
            from services.library_watcher import (
                deduplicate_and_reparent_track,
                resolve_collision_safe_edition_path,
                suppress_path,
            )

            meta = self._enrich_physical_telemetry(file_path, metadata)
            pref_lib_root, pattern = get_library_preferences()
            base_library_path = str(self.library_root) if getattr(self, "library_root", None) else pref_lib_root
            ext = file_path.suffix.lower().lstrip(".")

            base_dest = build_destination_path(
                base_library_path=base_library_path,
                pattern=pattern,
                meta=meta,
                ext=ext,
            )

            db = getattr(self, "_music_db", None) or get_database()
            has_music_schema = False
            try:
                has_music_schema = inspect(db.engine).has_table("local_media")
            except Exception:
                has_music_schema = False

            dest_path = base_dest
            if has_music_schema:
                with db.session_factory() as session:
                    try:
                        with session.no_autoflush:
                            dest_path = resolve_collision_safe_edition_path(
                                base_dest,
                                metadata=meta,
                                session=session,
                                current_file=file_path,
                            )

                            if dest_path.resolve() != file_path.resolve():
                                with suppress_path(str(file_path)), suppress_path(str(dest_path)):
                                    moved_to = Gatekeeper.authorize_and_execute(
                                        {
                                            "operation": "safe_move",
                                            "src": str(file_path),
                                            "dst": str(dest_path),
                                        }
                                    )
                                logger.info(f"Moved {file_path.name} → {moved_to}")

                            canon_src = _canonicalize_path(str(file_path))
                            src_lm = (
                                session.query(LocalMedia)
                                .filter(
                                    or_(
                                        LocalMedia.file_path == canon_src,
                                        LocalMedia.file_path == str(file_path),
                                    )
                                )
                                .first()
                            )
                            if src_lm is not None:
                                src_lm.file_path = _canonicalize_path(str(dest_path))
                                session.flush()

                            track_obj = self._build_import_track_dto(dest_path, meta)
                            TrackRepository(session).bulk_upsert_tracks([track_obj])
                            deduplicate_and_reparent_track(
                                session=session,
                                media_path=dest_path,
                                track_dto=track_obj,
                                metadata=meta,
                            )

                            fp_val = meta.get("fingerprint") or meta.get("chromaprint")
                            if fp_val:
                                canon_dest = _canonicalize_path(str(dest_path))
                                new_lm = (
                                    session.query(LocalMedia)
                                    .filter(
                                        or_(
                                            LocalMedia.file_path == canon_dest,
                                            LocalMedia.file_path == str(dest_path),
                                        )
                                    )
                                    .first()
                                )
                                if new_lm and new_lm.media_id:
                                    existing_fp = (
                                        session.query(AudioFingerprint)
                                        .filter_by(media_id=new_lm.media_id)
                                        .first()
                                    )
                                    if not existing_fp:
                                        session.add(
                                            AudioFingerprint(
                                                media_id=new_lm.media_id,
                                                chromaprint=fp_val,
                                                acoustid_id=meta.get("acoustid_id"),
                                            )
                                        )
                        with db_write_lease(task_name="auto_importer"):
                            session.commit()
                    except Exception:
                        session.rollback()
                        raise
            else:
                dest_path = resolve_collision_safe_edition_path(
                    base_dest,
                    metadata=meta,
                    session=None,
                    current_file=file_path,
                )
                if dest_path.resolve() != file_path.resolve():
                    with suppress_path(str(file_path)), suppress_path(str(dest_path)):
                        moved_to = Gatekeeper.authorize_and_execute(
                            {
                                "operation": "safe_move",
                                "src": str(file_path),
                                "dst": str(dest_path),
                            }
                        )
                    logger.info(f"Moved {file_path.name} → {moved_to}")

            # Prune empty source parent directories halting at download_dir
            _dl = config_manager.get("storage.download_dir") or config_manager.get("download_dir")
            stop_roots = {Path(_dl).resolve()} if _dl else set()
            prune_empty_parent_directories(file_path, stop_at_roots=stop_roots)
            return dest_path

        except Exception as e:
            logger.error(f"Failed to move file {file_path}: {e}")
            raise e

    def _sanitize(self, filename: str) -> str:
        """Sanitize filename components"""
        import re

        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", filename).strip()

    def _cleanup_empty_directories(self, directory: Path):
        """Recursively remove empty directories halting at download_dir."""
        try:
            from core.utils.file_utils import prune_empty_parent_directories

            _dl = config_manager.get("storage.download_dir") or config_manager.get("download_dir")
            stop_roots = {Path(_dl).resolve()} if _dl else set()
            prune_empty_parent_directories(directory, stop_at_roots=stop_roots)
        except Exception:
            pass


def get_auto_importer():
    return AutoImportService.get_instance()


def register_auto_import_service():
    _ = AutoImportService.get_instance()
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

    def on_modified(self, event: FileSystemEvent) -> None:
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
        if _is_path_component_ignored(raw_path):
            return

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
            logger.debug(
                "Auto-importer watchdog: file vanished before debounce expired: %s",
                abs_path,
            )
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


# Canonical alias
AutoImporter = AutoImportService
