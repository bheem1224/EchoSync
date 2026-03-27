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
import threading
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

class ColorFormatter(SafeFormatter):
    """
    Console formatter with dynamic ANSI colors.

    - levelname is colored by severity (red for errors, yellow for warnings, etc.)
    - [component] tag is colored by a stable hash of the component name so each
      async service gets a visually distinct, consistent color across log lines.
    """

    # Severity → ANSI escape code
    _LEVEL_COLORS: dict = {
        'DEBUG':    '\033[94m',   # bright blue
        'INFO':     '\033[32m',   # green
        'WARNING':  '\033[93m',   # yellow
        'ERROR':    '\033[91m',   # bright red
        'CRITICAL': '\033[91;1m', # bright red + bold
    }

    # Per-component palette: Cyan, Magenta, Green, Blue, Yellow
    _COMPONENT_PALETTE: list = [
        '\033[96m',   # Cyan
        '\033[95m',   # Magenta
        '\033[32m',   # Green
        '\033[34m',   # Blue
        '\033[33m',   # Yellow
    ]

    _RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        # --- Level color ---
        level_color = self._LEVEL_COLORS.get(record.levelname, '')
        colored_level = f"{level_color}{record.levelname:<5.5}{self._RESET}"

        # --- Component color (stable hash → palette index) ---
        # Prefer an explicitly injected 'component' extra, fall back to logger name.
        component = getattr(record, 'component', None) or record.name
        comp_color = self._COMPONENT_PALETTE[hash(component) % len(self._COMPONENT_PALETTE)]
        colored_component = f"{comp_color}[{component}]{self._RESET}"

        # --- Message (safe Unicode retrieval) ---
        try:
            msg = record.getMessage()
        except UnicodeEncodeError:
            msg = self.strip_emojis(str(record.msg))

        return f"{colored_level} {colored_component} {msg}"

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
        # Inject the short component name so ColorFormatter can pick a stable palette colour.
        # The tag (e.g. "provider plex") is stored as record.component on the LogRecord.
        kwargs.setdefault('extra', {})['component'] = self.tag.strip('[]')
        return msg, kwargs

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

    # Use ColorFormatter by default. Only suppress ANSI codes when the caller
    # explicitly sets NO_COLOR=1 (https://no-color.org) — e.g. to keep log
    # pipelines / file captures free of escape sequences.
    _no_color = os.getenv('NO_COLOR', '0') not in ('0', '')
    if not _no_color:
        console_formatter = ColorFormatter()
    else:
        console_formatter = SafeFormatter(
            fmt='%(levelname)-5.5s [%(name)s] %(message)s',
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

    # Silence verbose third-party filesystem watcher debug noise while keeping
    # warnings and errors visible.
    for logger_name in (
        "watchdog",
        "watchdog.observers",
        "watchdog.observers.inotify_buffer",
        "watchdog.observers.inotify_c",
        "watchdog.events",
    ):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

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

# Tracks an active verbose-mode timer so it can be cancelled if verbose is toggled early.
_verbose_timer: threading.Timer | None = None

def set_verbose_mode(duration_seconds: int = 60) -> None:
    """
    Temporarily set console log level to DEBUG for *duration_seconds*, then
    revert to the level that was active before this call.

    Calling this again while a timer is already running cancels the previous
    timer and starts a fresh one (extends the window).
    """
    global _verbose_timer
    if _verbose_timer is not None and _verbose_timer.is_alive():
        _verbose_timer.cancel()

    previous_level = get_current_log_level()
    set_log_level("DEBUG")
    logging.getLogger().info(
        f"Verbose mode active for {duration_seconds}s — will revert to {previous_level}"
    )

    def _revert():
        set_log_level(previous_level)
        logging.getLogger().info(f"Verbose mode expired — console level restored to {previous_level}")

    _verbose_timer = threading.Timer(duration_seconds, _revert)
    _verbose_timer.daemon = True
    _verbose_timer.start()

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
