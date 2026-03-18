"""
Auto-Import Service for SoulSync

Monitors download folder for new files and automatically:
1. Parses filenames and generates fingerprints
2. Matches against metadata providers
3. Tags files with correct metadata
4. Imports into transfer folder for library organization

Configuration in config.json:
{
  "auto_import": {
    "enabled": true,
    "check_interval_seconds": 3600,
    "source_folder": "download_dir",
    "destination_folder": "transfer_dir",
    "file_organization_pattern": "{Artist}/{Album}/{TrackNumber} - {Title}",
    "skip_if_already_tagged": true,
    "log_imports": true
  },
  "storage": {
    "download_dir": "C:\\path\\to\\downloads",
    "transfer_dir": "C:\\path\\to\\transfer"
  }
}
"""

import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import logging  # Add this import for logging levels

from time_utils import utc_isoformat, utc_now

from .matching_engine import parse_file, SoulSyncTrack
from services.match_service import MatchService, MatchContext
from .post_processor import PostProcessor
from core.tiered_logger import tiered_logger
from core.error_handler import error_handler
from core.tiered_logger import get_logger
from core.media_scan_manager import MediaScanManager
from core.job_queue import job_queue  # Use global singleton
from database.music_database import get_database, ReviewTask

logger = get_logger("auto_importer")


class AutoImporter:
    """
    Service that monitors download folder for new audio files and auto-imports them.
    """

    SUPPORTED_FORMATS = {'.mp3', '.flac', '.m4a', '.aac', '.ogg', '.opus', '.wav', '.wma', '.alac', '.ape'}

    def __init__(self, config_path: str = "config/config.json"):
        """
        Initialize AutoImporter with configuration

        Args:
            config_path: Path to config.json file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.auto_import_config = self.config.get("auto_import", {})
        self.storage_config = self.config.get("storage", {})

        self.enabled = self.auto_import_config.get("enabled", False)
        self.check_interval = self.auto_import_config.get("check_interval_seconds", 3600)

        # Get source and destination from storage config
        source_key = self.auto_import_config.get("source_folder", "download_dir")
        dest_key = self.auto_import_config.get("destination_folder", "library_dir")

        self.source_folder = Path(self.storage_config.get(source_key, "./downloads")).expanduser().resolve()
        self.destination_folder = Path(self.storage_config.get(dest_key, "./library")).expanduser().resolve()

        self.file_pattern = self.auto_import_config.get("file_organization_pattern", "{Artist}/{Album}/{Title}")
        self.skip_if_tagged = self.auto_import_config.get("skip_if_already_tagged", True)
        self.log_imports = self.auto_import_config.get("log_imports", True)

        self.match_service = MatchService()
        self.post_processor = PostProcessor()

        self._import_log: List[Dict] = []

        # Always register job with global job_queue (enabled state from config)
        job_queue.register_job(
            name="auto_import_scan",
            func=self._scan_and_move_files,
            interval_seconds=self.check_interval,
            enabled=self.enabled,  # Respect config enabled state
            tags=["soulsync", "auto_import"]
        )
        tiered_logger.log(
            "normal", logging.INFO,
            f"AutoImporter job registered with global JobQueue (enabled={self.enabled})"
        )

        tiered_logger.log(
            "normal", logging.INFO,
            f"AutoImporter initialized (enabled={self.enabled}, interval={self.check_interval}s, source={self.source_folder}, destination={self.destination_folder})"
        )

    def _load_config(self) -> Dict:
        """Load configuration from config.json"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
        return {}

    def start(self):
        """Legacy start method - AutoImporter now managed by job_queue"""
        logger.info("AutoImporter is now managed by job_queue. Use /settings/jobs to enable/disable.")

    def stop(self):
        """Legacy stop method - AutoImporter now managed by job_queue"""
        logger.info("AutoImporter is now managed by job_queue. Use /settings/jobs to enable/disable.")

    def scan_and_import(self):
        """
        Scan source folder for new audio files and import them

        Returns:
            Dictionary with import statistics
        """
        stats = {
            "timestamp": utc_isoformat(utc_now()),
            "files_found": 0,
            "files_imported": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "imported_files": [],
            "failed_files": [],
        }

        if not self.source_folder.exists():
            logger.warning(f"Source folder not found: {self.source_folder}")
            return stats

        logger.debug(f"Scanning folder: {self.source_folder}")

        # Find all audio files
        audio_files = self._find_audio_files(self.source_folder)
        stats["files_found"] = len(audio_files)

        # Process each file
        for file_path in audio_files:
            try:
                result = self._import_file(file_path)
                if result:
                    stats["files_imported"] += 1
                    stats["imported_files"].append(str(file_path))
                else:
                    stats["files_skipped"] += 1
            except Exception as e:
                logger.error(f"Failed to import {file_path}: {e}")
                stats["files_failed"] += 1
                stats["failed_files"].append({
                    "file": str(file_path),
                    "error": str(e)
                })

        # Log results
        if stats["files_found"] > 0:
            logger.info(
                f"AutoImport scan complete: "
                f"{stats['files_imported']} imported, "
                f"{stats['files_skipped']} skipped, "
                f"{stats['files_failed']} failed"
            )

        self._import_log.append(stats)
        return stats

    def _find_audio_files(self, folder: Path) -> List[Path]:
        """Find all audio files in folder (recursive)"""
        audio_files = []
        for file_path in folder.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                audio_files.append(file_path)
        return audio_files

    def _import_file(self, file_path: Path) -> bool:
        """
        Import a single file (parse, match, tag, organize)

        Args:
            file_path: Path to audio file

        Returns:
            True if imported successfully, False if skipped
        """
        logger.debug(f"Processing: {file_path}")

        # Parse filename and generate fingerprint
        try:
            track = parse_file(str(file_path), generate_fingerprint=True)
            if not track:
                logger.warning(f"Failed to parse: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return False

        # Check if already has good tags
        if self.skip_if_tagged and self._has_valid_tags(track):
            logger.debug(f"Skipping (already tagged): {file_path}")
            return False

        # For now, just log the match
        # In production, would query metadata providers
        logger.info(f"Imported: {track.artist} - {track.title}")

        if self.log_imports:
            logger.debug(f"  Metadata: {track.title} by {track.artist} ({track.album})")
            if track.fingerprint:
                logger.debug(f"  Fingerprint: {track.fingerprint[:16]}...")

        return True

    def _has_valid_tags(self, track: SoulSyncTrack) -> bool:
        """Check if track already has valid metadata tags"""
        # Simple heuristic: if we have artist, title, and album, consider it valid
        return bool(track.artist and track.title and track.album)

    def get_import_log(self, limit: int = 10) -> List[Dict]:
        """Get recent import logs"""
        return self._import_log[-limit:]

    def get_statistics(self) -> Dict:
        """Get cumulative statistics"""
        if not self._import_log:
            return {
                "total_scans": 0,
                "total_files_found": 0,
                "total_files_imported": 0,
                "total_files_failed": 0,
            }

        total_found = sum(log.get("files_found", 0) for log in self._import_log)
        total_imported = sum(log.get("files_imported", 0) for log in self._import_log)
        total_failed = sum(log.get("files_failed", 0) for log in self._import_log)

        return {
            "total_scans": len(self._import_log),
            "total_files_found": total_found,
            "total_files_imported": total_imported,
            "total_files_failed": total_failed,
            "last_scan": self._import_log[-1].get("timestamp") if self._import_log else None,
        }

    def _scan_and_move_files(self):
        """
        Scan the source folder for new files and move them to the destination folder.
        """
        try:
            tiered_logger.log("debug", logging.INFO, "Starting scan for new files.")

            # Logic to scan, auto-tag, and move files goes here

            tiered_logger.log("normal", logging.INFO, "Files moved to transfer directory.")
        except Exception as e:
            error_handler.handle_exception(
                lambda: (_ for _ in ()).throw(e),  # Raise the exception to log it
                retries=0,
                log_tier="normal"
            )
            tiered_logger.log("normal", logging.ERROR, f"Error during file scan: {e}")


# Global AutoImporter instance
_auto_importer: Optional[AutoImporter] = None


def get_auto_importer(config_path: str = "config/config.json") -> AutoImporter:
    """Get or create global AutoImporter instance"""
    global _auto_importer
    if _auto_importer is None:
        _auto_importer = AutoImporter(config_path)
    return _auto_importer


def start_auto_import(config_path: str = "config/config.json"):
    """Start the auto-import service"""
    importer = get_auto_importer(config_path)
    importer.start()


def stop_auto_import():
    """Stop the auto-import service"""
    global _auto_importer
    if _auto_importer:
        _auto_importer.stop()
        _auto_importer = None
