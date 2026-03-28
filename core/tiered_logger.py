"""
Unified Logger Module for SoulSync

This module provides a centralized logging utility that integrates:
- Standard Python logging with `get_logger(name)`
- Automatic source tagging (e.g., [core], [provider plex])
- Tiered file logging (normal.log, debug.log, verbose.log)
- Console logging with colors and Unicode safety (Windows compatible)
- Windows-safe file rotation with deferred rollover
"""

import logging
import sys
import re
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# --- Custom Windows-Safe Rotating File Handler ---

class SafeRotatingFileHandler(RotatingFileHandler):
    """
    RotatingFileHandler that handles Windows file locking gracefully.
    Defers rollover if the file is locked, avoiding PermissionError.
    Silently skips rotation and continues logging if file cannot be rotated.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rotation_failed = False  # Track if rotation failed to avoid spam
    
    def shouldRollover(self, record):
        """Override to skip rollover check if last rotation failed."""
        # If last rotation failed and we're still within the same file size threshold,
        # don't try again immediately to avoid log spam
        if self._rotation_failed:
            # Reset flag after a while (10MB of additional writes)
            if self.stream and self.stream.tell() > (self.maxBytes + 10*1024*1024):
                self._rotation_failed = False
            else:
                return False  # Skip rollover attempt
        return super().shouldRollover(record)
    
    def doRollover(self):
        """
        Override doRollover to handle Windows file locking.
        If rollover fails due to file being locked, silently skip and continue logging.
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        
        # Try to rotate with exponential backoff for Windows
        max_retries = 5
        rotation_succeeded = False
        
        for attempt in range(max_retries):
            try:
                if self.backupCount > 0:
                    # Rotate backup files
                    for i in range(self.backupCount - 1, 0, -1):
                        sfn = self.rotation_filename(f"{self.baseFilename}.{i}")
                        dfn = self.rotation_filename(f"{self.baseFilename}.{i + 1}")
                        if os.path.exists(sfn):
                            if os.path.exists(dfn):
                                try:
                                    os.remove(dfn)
                                except OSError:
                                    pass
                            try:
                                os.rename(sfn, dfn)
                            except OSError:
                                if attempt < max_retries - 1:
                                    delay = 0.05 * (2 ** attempt)  # Exponential backoff
                                    time.sleep(delay)
                                    raise  # Re-raise to retry outer loop
                    
                    # Rename current file to .1
                    dfn = self.rotation_filename(f"{self.baseFilename}.1")
                    if os.path.exists(dfn):
                        try:
                            os.remove(dfn)
                        except OSError:
                            pass
                    
                    # Critical: rename the main log file
                    os.rename(self.baseFilename, dfn)
                
                rotation_succeeded = True
                self._rotation_failed = False
                break  # Success
                
            except OSError as e:
                if attempt < max_retries - 1:
                    delay = 0.05 * (2 ** attempt)  # Exponential backoff: 50ms, 100ms, 200ms, 400ms, 800ms
                    time.sleep(delay)
                else:
                    # After all retries failed, silently skip rotation
                    # Don't spam stderr - just mark as failed and continue logging
                    self._rotation_failed = True
        
        # Always reopen the stream, even if rotation failed
        try:
            self.stream = self._open()
        except Exception as e:
            # If we can't even open the stream, we have a serious problem
            print(f"CRITICAL: Cannot open log file {self.baseFilename}: {e}", file=sys.stderr)
            self.stream = None

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

    _NAMESPACE_COLORS = [
        '\033[38;5;39m',   # Light Blue
        '\033[38;5;213m',  # Purple
        '\033[38;5;46m',   # Green
        '\033[38;5;226m',  # Lime
        '\033[38;5;208m',  # Orange
        '\033[38;5;161m',  # Red
        '\033[38;5;198m',  # Pink
        '\033[38;5;51m',   # Cyan
        '\033[38;5;220m',  # Gold
        '\033[38;5;135m',  # Lavender
    ]

    def _hash_to_color(self, text: str) -> str:
        """Deterministically map a string to an ANSI color code."""
        hash_val = sum(ord(c) for c in text)
        return self._NAMESPACE_COLORS[hash_val % len(self._NAMESPACE_COLORS)]

    def format(self, record):
        # Create a copy to not affect other handlers
        levelname = record.levelname
        log_color = self.COLORS.get(levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']

        # Temporarily modify levelname for this format call
        record.levelname = f"{log_color}{levelname}{reset_color}"
        result = super().format(record)
        record.levelname = levelname # Restore

        # Colorize namespace tag if present (e.g. [plugin.cjk])
        import re
        msg = record.getMessage()
        if msg.startswith('['):
            match = re.match(r'^(\[[^\]]+\])( - )', msg)
            if match:
                tag = match.group(1)
                color = self._hash_to_color(tag)
                # Find the tag in the formatted result and colorize it
                result = result.replace(tag + match.group(2), f"{color}{tag}{reset_color}{match.group(2)}", 1)

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
            handler = SafeRotatingFileHandler(
                log_path / filename,
                maxBytes=10*1024*1024,  # 10MB - larger files, less frequent rotation
                backupCount=3,  # Fewer backups to reduce rotation complexity
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
