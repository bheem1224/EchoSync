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
            enabled=True,
            tags=["soulsync", "import"],
            max_retries=3
        )

    def scan_and_process(self):
        """Scan download directory for audio files and process them."""
        # Check global enabled setting (re-using metadata_enhancement config for now as requested)
        meta_config = config_manager.get('metadata_enhancement') or {}
        # The prompt implies "Auto-Import Switch" controls this.
        # But if the switch is OFF, should we still scan and populate the review queue?
        # The prompt says: "Auto-Import Switch: Toggle for auto_import_enabled."
        # Usually, if auto-import is off, we might still want to Identify and Queue, just not Move.
        # But for now, let's assume we scan if the feature "metadata_enhancement" is generally enabled,
        # and "auto_import" specifically controls the automatic move.

        # However, there isn't a separate "Metadata Service Enabled" toggle in the new UI plan,
        # just "Auto Import".
        # If I look at `scan_and_process` in original code:
        # `if not meta_config.get('enabled', True): return`
        # I'll stick to that.

        if not meta_config.get('enabled', True):
            return

        download_dir = config_manager.get_download_dir()
        if not download_dir.exists():
            return

        supported_exts = {'.mp3', '.flac', '.ogg', '.m4a', '.wav'}
        files_to_process = []

        # We also need to skip files that are already in the review queue
        pending_files = self._get_pending_review_files()

        for root, dirs, files in os.walk(download_dir):
            for file in files:
                path = Path(root) / file
                if path.suffix.lower() in supported_exts:
                    if str(path) not in pending_files:
                         files_to_process.append(path)

        if files_to_process:
            logger.info(f"Found {len(files_to_process)} new files to process")
            self.process_batch(files_to_process)

    def _get_pending_review_files(self) -> set:
        """Get set of file paths currently in pending or ignored review tasks."""
        # This duplicates logic from MetadataEnhancer, but that's okay for decoupling.
        db = get_database()
        with db.session_scope() as session:
            rows = session.query(ReviewTask.file_path).filter(ReviewTask.status.in_(['pending', 'ignored'])).all()
            return {row[0] for row in rows}

    def process_batch(self, files: List[Path]):
        """
        Process a batch of files: Identify -> Decide -> (Tag & Move) OR Queue.
        """
        meta_config = config_manager.get('metadata_enhancement') or {}
        auto_import = meta_config.get('auto_import', False)
        confidence_threshold = meta_config.get('confidence_threshold', 90) / 100.0

        for file_path in files:
            if not file_path.exists():
                continue

            logger.info(f"Processing file: {file_path}")

            try:
                # Delegate identification to MetadataEnhancerService
                # We need a new method in MetadataEnhancer that returns (metadata, confidence)
                # For now, I will assume I'll add `identify_file` to MetadataEnhancer.
                metadata, confidence = self.enhancer.identify_file(file_path)

                # Decision Logic
                if metadata and auto_import and confidence >= confidence_threshold:
                    logger.info(f"Auto-importing {file_path.name} (Confidence: {confidence:.2f})")
                    self.finalize_import(file_path, metadata)

                    # Create/Update task as approved for history/audit
                    # Note: Original code did this. I'll keep it for consistency.
                    self.enhancer.create_or_update_review_task(file_path, metadata, confidence, status='approved')
                else:
                    if metadata:
                        logger.info(f"Low confidence ({confidence:.2f}) or Auto-Import OFF. Sending to Review Queue.")
                    else:
                        logger.info(f"No metadata found. Sending to Review Queue.")

                    self.enhancer.create_or_update_review_task(file_path, metadata, confidence, status='pending')

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}", exc_info=True)

        # Cleanup
        for f in files:
             self._cleanup_empty_directories(f.parent)

    def finalize_import(self, file_path: Path, metadata: Dict[str, Any]):
        """
        Public method to Tag and Move a file.
        Used by Auto-Import logic and 'Approve' button in UI.
        """
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
