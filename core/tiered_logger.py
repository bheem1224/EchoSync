"""
Tiered Logger Module for SoulSync

This module provides a logging utility with support for multiple tiers:
- Normal: Minimal logging for production environments.
- Debug: Detailed logging for debugging purposes.
- Verbose: Highly detailed logging for in-depth analysis.

The logger supports log rotation and can write logs to separate files based on the tier.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

class TieredLogger:
    """
    A logger with tiered logging levels and file-based log rotation.
    """

    def __init__(self, log_dir: str = "/data/logs", max_bytes: int = 5 * 1024 * 1024, backup_count: int = 5):
        """
        Initialize the tiered logger.

        Args:
            log_dir: Directory to store log files (default: /data/logs for Docker compatibility).
            max_bytes: Maximum size of a log file before rotation (default: 5MB).
            backup_count: Number of backup log files to keep (default: 5).
        """
        import os
        env_log_dir = os.getenv("SOULSYNC_LOG_DIR")
        if env_log_dir:
            log_dir = env_log_dir

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.normal_logger = self._create_logger("normal", logging.INFO, max_bytes, backup_count)
        self.debug_logger = self._create_logger("debug", logging.DEBUG, max_bytes, backup_count)
        self.verbose_logger = self._create_logger("verbose", logging.NOTSET, max_bytes, backup_count)

    def _create_logger(self, name: str, level: int, max_bytes: int, backup_count: int) -> logging.Logger:
        """
        Create a logger with the specified level and log rotation.

        Args:
            name: Name of the logger (used for the log file name).
            level: Logging level (e.g., logging.INFO, logging.DEBUG).
            max_bytes: Maximum size of a log file before rotation.
            backup_count: Number of backup log files to keep.

        Returns:
            A configured logger instance.
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)

        log_file = self.log_dir / f"{name}.log"
        handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def log(self, tier: str, level: int, message: str):
        """
        Log a message to the specified tier.

        Args:
            tier: The logging tier ("normal", "debug", or "verbose").
            level: The logging level (e.g., logging.INFO, logging.ERROR).
            message: The message to log.
        """
        if tier == "normal":
            self.normal_logger.log(level, message)
        elif tier == "debug":
            self.debug_logger.log(level, message)
        elif tier == "verbose":
            self.verbose_logger.log(level, message)
        else:
            raise ValueError(f"Unknown logging tier: {tier}")

    def set_log_directory(self, log_dir: str):
        """
        Dynamically update the log directory and reinitialize loggers.

        Args:
            log_dir: New directory to store log files.
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.normal_logger = self._create_logger("normal", logging.INFO, 5 * 1024 * 1024, 5)
        self.debug_logger = self._create_logger("debug", logging.DEBUG, 5 * 1024 * 1024, 5)
        self.verbose_logger = self._create_logger("verbose", logging.NOTSET, 5 * 1024 * 1024, 5)

        logging.info(f"Log directory updated to: {log_dir}")

# Global instance for convenience
tiered_logger = TieredLogger()