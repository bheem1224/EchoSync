"""
Unified Logger Module for SoulSync

This module provides a centralized logging utility that integrates:
- Standard Python logging with `get_logger(name)`
- Automatic source tagging (e.g., [core], [provider plex])
- Tiered file logging (normal.log, debug.log, verbose.log)
- Console logging with colors and Unicode safety (Windows compatible)
"""

import logging
import sys
import re
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# --- Formatters ---

class SafeFormatter(logging.Formatter):
    """Formatter that handles Unicode characters safely on Windows"""

    @staticmethod
    def strip_emojis(text):
        """Remove emoji characters from text for Windows compatibility"""
        # Remove emoji characters but keep other Unicode
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub('', text)

    def format(self, record):
        # Try to format with emojis first, fall back to stripped version
        try:
            return super().format(record)
        except UnicodeEncodeError:
            # Strip emojis and try again for Windows compatibility
            record.getMessage = lambda: self.strip_emojis(record.msg % record.args if record.args else record.msg)
            return super().format(record)

class ColoredFormatter(SafeFormatter):
    COLORS = {
        'DEBUG': '\033[94m',
        'INFO': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[95m',
        'RESET': '\033[0m'
    }

    def format(self, record):
        # Create a copy to not affect other handlers
        levelname = record.levelname
        log_color = self.COLORS.get(levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']

        # Temporarily modify levelname for this format call
        record.levelname = f"{log_color}{levelname}{reset_color}"
        result = super().format(record)
        record.levelname = levelname # Restore
        return result

# --- Adapter for Tagging ---

class SourceTagAdapter(logging.LoggerAdapter):
    """
    Adapter that adds a source tag to log messages based on the logger name.
    """
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})
        self.tag = self._derive_tag(logger.name)

    def _derive_tag(self, name: str) -> str:
        if name.startswith("core"):
            return "[core]"
        elif name.startswith("providers."):
            parts = name.split(".")
            if len(parts) > 1:
                return f"[provider {parts[1]}]"
        elif name.startswith("web."):
            return "[web]"
        elif name.startswith("plugins."):
             parts = name.split(".")
             if len(parts) > 1:
                return f"[plugin {parts[1]}]"
        return "[system]"

    def process(self, msg, kwargs):
        # Prepend tag to message
        return f"{self.tag} - {msg}", kwargs

# --- Global Setup ---

def setup_logging(level: str = "INFO", log_dir: Optional[str] = None, log_file: Optional[str] = None) -> logging.Logger:
    """
    Initialize the unified logging system.
    Configures the root logger to output to console and tiered log files.

    Args:
        level: Console log level.
        log_dir: Directory to store log files.
        log_file: Legacy argument alias. If provided and log_dir is None,
                  the directory of log_file is used.
    """
    # Handle legacy 'log_file' argument by extracting directory
    if log_file and not log_dir:
        try:
            log_dir = os.path.dirname(log_file)
        except Exception:
            pass

    # Use Env vars if provided
    if not log_dir:
        log_dir = os.getenv("SOULSYNC_LOG_DIR", "data/logs") # Default relative to cwd if not absolute

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.NOTSET) # Capture everything, handlers will filter

    # Clear existing handlers to prevent duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()

    # --- Console Handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_level = getattr(logging, level.upper(), logging.INFO)
    console_handler.setLevel(console_level)

    # Force UTF-8 encoding for Windows compatibility
    if hasattr(console_handler.stream, 'reconfigure'):
        console_handler.stream.reconfigure(encoding='utf-8', errors='replace')

    console_formatter = ColoredFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # --- File Handlers (Tiered Strategy) ---
    try:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        def add_file_handler(filename, level):
            handler = RotatingFileHandler(
                log_path / filename,
                maxBytes=5*1024*1024,
                backupCount=5,
                encoding='utf-8'
            )
            handler.setLevel(level)
            formatter = SafeFormatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)

        # Normal: INFO and up
        add_file_handler("normal.log", logging.INFO)
        # Debug: DEBUG and up
        add_file_handler("debug.log", logging.DEBUG)
        # Verbose: All
        add_file_handler("verbose.log", logging.NOTSET)

        root_logger.info(f"Logging initialized. Console Level: {level}, Log Dir: {log_path}")

    except Exception as e:
        print(f"Failed to setup file logging: {e}")

    return root_logger

def get_logger(name: str) -> logging.Logger:
    """
    Factory to get a logger with automatic source tagging.
    """
    return SourceTagAdapter(logging.getLogger(name))

def set_log_level(level: str) -> bool:
    """Dynamically change the console log level."""
    try:
        root = logging.getLogger()
        lvl = getattr(logging, level.upper(), logging.INFO)
        for h in root.handlers:
            if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler):
                h.setLevel(lvl)
        root.info(f"Console log level changed to: {level}")
        return True
    except Exception:
        return False

def get_current_log_level() -> str:
    """Get the current console log level."""
    root = logging.getLogger()
    for h in root.handlers:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler):
            return logging.getLevelName(h.level)
    return "INFO"

# --- Legacy TieredLogger Support ---

class TieredLogger:
    """
    Backward compatibility wrapper for the old TieredLogger class.
    Delegates to the unified standard logging system.
    """
    def __init__(self):
        pass

    def log(self, tier: str, level: int, message: str):
        # We delegate to a specific logger name to identify these legacy calls
        logger = logging.getLogger("core.tiered")
        # Log at the requested level.
        # The 'tier' info is implicitly handled by the handlers (normal.log gets INFO+, etc)
        logger.log(level, message)

    def set_log_directory(self, log_dir: str):
        setup_logging(log_dir=log_dir)

# Global instance for legacy support
tiered_logger = TieredLogger()
