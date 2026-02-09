"""
Auto Import Service - Orchestrator for scanning, identifying, and importing audio files.

This service is responsible for:
1. Scanning the download directory for new files.
2. Coordinating with MetadataEnhancerService to identify files.
3. Decision making (Auto-Import vs Review Queue).
4. Moving and Renaming files (using "Keep Both" conflict resolution).
"""

import os
import shutil
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any
import datetime

from core.settings import config_manager
from core.job_queue import register_job
from core.tiered_logger import get_logger
from services.metadata_enhancer import get_metadata_enhancer
from database import get_database
from database.music_database import ReviewTask

logger = get_logger("services.auto_importer")

class AutoImportService:
    _instance = None

    def __init__(self):
        self.library_root = config_manager.get_library_dir()
        self.enhancer = get_metadata_enhancer()
        self._scan_lock = threading.Lock()
        self._processing_lock = threading.Lock()
        self._processing_files = set()
        self._recently_completed = {}  # Track completed files to avoid duplicate processing
        self._register_jobs()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AutoImportService()
        return cls._instance

    def _register_jobs(self):
        """Register background jobs"""
        register_job(
            name="auto_import_scan",
            func=self.scan_and_process,
            interval_seconds=300,  # 5 minutes
            start_after=300,  # Wait 5 minutes before first run
            enabled=True,
            tags=["soulsync", "import"],
            max_retries=3
        )

    def scan_and_process(self):
        """Scan download directory for audio files and process them."""
        if not self._scan_lock.acquire(blocking=False):
            logger.info("Auto-import scan skipped: Another scan/process is already running.")
            return
        meta_config = config_manager.get('metadata_enhancement') or {}

        try:
            if not meta_config.get('enabled', True):
                logger.info("Auto-import scan skipped: Feature disabled in settings.")
                return

            download_dir = config_manager.get_download_dir()
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

            # We also need to skip files that are already ignored
            pending_files = self._get_pending_review_files()

            for root, dirs, files in os.walk(download_dir):
                logger.debug(f"Scanning directory: {root}")
                logger.debug(f"Found {len(files)} files in {root}")
                for file in files:
                    path = Path(root) / file
                    logger.debug(f"Checking file: {path}")
                    if path.suffix.lower() in supported_exts:
                        logger.debug(f"File matches audio extension: {path.suffix}")
                        if str(path) in pending_files:
                            logger.debug(f"File is ignored in review queue, skipping: {path}")
                            continue
                        with self._processing_lock:
                            if str(path) in self._processing_files:
                                logger.debug(f"File already being processed, skipping: {path}")
                                continue
                        logger.debug(f"File not in ignored queue, adding: {path}")
                        files_to_process.append(path)

            if files_to_process:
                logger.info(f"Found {len(files_to_process)} new files to process")
                self.process_batch(files_to_process)
            else:
                logger.info(f"Auto-import scan completed: No new files found in {download_dir}")
        finally:
            self._scan_lock.release()

    def _get_pending_review_files(self) -> set:
        """Get set of file paths currently ignored (NOT reprocessing pending items).
        
        Only skip files that are explicitly 'ignored' by the user.
        Files in 'pending' status should be reprocessed (they're waiting for manual review).
        """
        db = get_database()
        with db.session_scope() as session:
            rows = session.query(ReviewTask.file_path).filter(ReviewTask.status == 'ignored').all()
            return {row[0] for row in rows}

    def process_batch(self, files: List[Path]):
        """
        Process a batch of files: Identify -> Decide -> (Tag & Move) OR Queue.
        
        Decision Logic:
        - If metadata identification FAILS (returns None) -> Queue for manual review (no file movement)
        - If metadata found AND auto_import enabled AND confidence >= threshold -> Auto-import
        - Otherwise -> Queue for manual review
        """
        import time
        
        meta_config = config_manager.get('metadata_enhancement') or {}
        auto_import = meta_config.get('auto_import', False)
        confidence_threshold = meta_config.get('confidence_threshold', 90) / 100.0

        for file_path in files:
            file_key = str(file_path)
            
            # Check if file was recently completed (within last 10 seconds)
            if file_key in self._recently_completed:
                if time.time() - self._recently_completed[file_key] < 10:
                    logger.debug(f"File recently processed, skipping: {file_path}")
                    continue
                else:
                    # Cleanup old entries
                    del self._recently_completed[file_key]
            
            with self._processing_lock:
                if file_key in self._processing_files:
                    logger.debug(f"File already being processed, skipping: {file_path}")
                    continue
                self._processing_files.add(file_key)

            if not file_path.exists():
                logger.warning(f"File disappeared before processing: {file_path}")
                with self._processing_lock:
                    self._processing_files.discard(file_key)
                continue

            logger.info(f"Processing file: {file_path}")

            try:
                # Delegate identification to MetadataEnhancerService
                metadata, confidence = self.enhancer.identify_file(file_path)

                # CRITICAL: If metadata is None, identification FAILED
                if metadata is None:
                    logger.warning(f"Metadata identification FAILED for {file_path.name}. Marking for manual review.")
                    self.enhancer.create_or_update_review_task(file_path, None, 0.0, status='pending')
                    self._recently_completed[file_key] = time.time()
                    continue

                # Decision Logic: Auto-import vs. Review Queue
                if auto_import and confidence >= confidence_threshold:
                    logger.info(f"Auto-importing {file_path.name} (Confidence: {confidence:.2f})")
                    if not file_path.exists():
                        logger.warning(f"File missing before finalize_import, skipping: {file_path}")
                        self.enhancer.create_or_update_review_task(file_path, metadata, confidence, status='pending')
                        self._recently_completed[file_key] = time.time()
                        continue
                    self.finalize_import(file_path, metadata)
                    self._recently_completed[file_key] = time.time()
                else:
                    logger.info(f"Low confidence ({confidence:.2f}) or Auto-Import OFF. Sending to Review Queue.")
                    self.enhancer.create_or_update_review_task(file_path, metadata, confidence, status='pending')
                    self._recently_completed[file_key] = time.time()

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}", exc_info=True)
                # Even on exceptions, ensure file is queued for review
                try:
                    self.enhancer.create_or_update_review_task(file_path, None, 0.0, status='pending')
                except Exception as e2:
                    logger.error(f"Failed to create review task for {file_path}: {e2}")
            finally:
                with self._processing_lock:
                    self._processing_files.discard(file_key)

        # Cleanup
        for f in files:
             self._cleanup_empty_directories(f.parent)

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

            # Prepare tokens (reusing logic, maybe could be util but fine here)
            artist = self._sanitize(metadata.get('artist') or "Unknown Artist")
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

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(file_path), str(dest_path))
            logger.info(f"Moved {file_path.name} -> {dest_path}")

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
            download_dir = config_manager.get_download_dir()
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
    logger.info("Auto Import Service initialized and jobs registered")
