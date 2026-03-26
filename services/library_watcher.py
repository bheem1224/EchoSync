"""
Library Watcher Service — Real-time file-system monitoring for the local library.

Architecture
============
This service bridges the OS file-system notification layer (watchdog) with the
SoulSync event bus so new audio files land in the database and trigger
TRACK_IMPORTED *immediately*, without waiting for the next scheduled scan.

Flow
----
  OS FS event (inotify / FSEvents / ReadDirectoryChangesW)
      ↓  watchdog Observer thread
  _AudioEventHandler.on_created / on_moved
      ↓  per-path debounce timer (threading.Timer, 1.5 s)
  _process_new_file(path)
      ├─ LocalFileHandler.read_tags()   → extract title / artist / isrc / …
      ├─ LibraryManager._upsert_track() → insert / update DB row atomically
      └─ event_bus.publish({"event": "TRACK_IMPORTED", …})
             ↓
         DownloadManager._on_track_imported → cancel redundant queue entries
         (any other subscriber)

Design notes
------------
Debounce (1.5 s):
  Many tools write a file by creating a temporary name and then renaming it
  into place.  Others write in small chunks, each triggering a new event.
  A short timer that resets on every event for the same path ensures we only
  run tag-extraction once the write is complete.

Thread safety:
  The Observer runs in its own daemon thread.  _process_new_file() is called
  from that thread via the timer callback.  All DB access goes through SQLAlchemy
  session_scope() which manages isolation.  The event bus dispatch is thread-safe
  (locked internally).

Minimum file size guard (64 KB):
  Rejects stub / zero-byte files that are sometimes created by download managers
  before the actual content arrives.  This is a heuristic — the debounce timer
  is the primary protection against reading partial files.
"""

import os
import threading
from pathlib import Path
from typing import Any, Optional

from watchdog.events import FileSystemEventHandler, FileSystemEvent  # type: ignore[import-untyped]
from watchdog.observers import Observer  # type: ignore[import-untyped]

from core.event_bus import event_bus
from core.file_handling.local_io import LocalFileHandler
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.settings import config_manager
from core.tiered_logger import get_logger
from database.bulk_operations import LibraryManager
from database.music_database import get_database

logger = get_logger("library_watcher")

# Audio extensions that the watcher responds to.
# Must stay in sync with LocalServerProvider.get_library_tracks() and
# web/routes/local_server.py format sets.
_AUDIO_EXTENSIONS: frozenset[str] = frozenset({
    ".flac", ".mp3", ".ogg", ".m4a", ".aac", ".alac",
    ".ape", ".wav", ".dsf", ".dff", ".wma",
})

# Minimum on-disk size before tag extraction is attempted.
# Prevents reading half-written files created by download managers.
_MIN_FILE_BYTES: int = 64 * 1024  # 64 KB

# Settling delay.  Timer resets if the same path fires another event within
# this window, guaranteeing tags are read only after the write is complete.
_DEBOUNCE_SECONDS: float = 1.5


class _AudioEventHandler(FileSystemEventHandler):
    """Watchdog event handler that debounces and processes new audio files."""

    def __init__(self) -> None:
        super().__init__()
        # Maps abs path → active threading.Timer awaiting expiry
        self._pending: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    # ── Public watchdog callbacks ──────────────────────────────────────────

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(os.fsdecode(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        # on_moved fires when a download manager renames a .tmp → .flac etc.
        # We care about the *destination* path.
        if event.is_directory:
            return
        dest = getattr(event, "dest_path", event.src_path)
        self._schedule(os.fsdecode(dest))

    # ── Internal helpers ───────────────────────────────────────────────────

    def _schedule(self, raw_path: str) -> None:
        """(Re-)schedule processing for a path after the debounce window."""
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

    def _fire(self, abs_path: str) -> None:
        """Called by the timer once the debounce window has elapsed."""
        with self._lock:
            self._pending.pop(abs_path, None)

        _process_new_file(Path(abs_path))

    def cancel_all(self) -> None:
        """Cancel all pending timers (called on service stop)."""
        with self._lock:
            for timer in self._pending.values():
                timer.cancel()
            self._pending.clear()


# ── File processing ────────────────────────────────────────────────────────────

def _process_new_file(path: Path) -> None:
    """
    Extract tags, upsert the track into the database, and emit TRACK_IMPORTED.

    Any exception is caught and logged so a single bad file never crashes the
    watcher thread.
    """
    try:
        if not path.exists():
            logger.debug("Watcher: file vanished before processing: %s", path)
            return

        if path.stat().st_size < _MIN_FILE_BYTES:
            logger.debug(
                "Watcher: skipping small file (%d bytes): %s",
                path.stat().st_size,
                path,
            )
            return

        logger.info("Watcher: new audio file detected: %s", path.name)

        # ── 1. Extract tags ────────────────────────────────────────────────
        tags: dict[str, Any] = {}
        try:
            tags = LocalFileHandler.get_instance().read_tags(path)
        except Exception as tag_err:
            logger.warning("Watcher: tag extraction failed for %s: %s", path.name, tag_err)

        title: str = tags.get("title") or path.stem
        artist_name: str = tags.get("artist") or "Unknown Artist"
        isrc: Optional[str] = tags.get("isrc") or None
        album_title: Optional[str] = tags.get("album") or None
        duration_ms: Optional[int] = None

        raw_duration = tags.get("duration_ms")
        if raw_duration is None:
            raw_duration = tags.get("duration")
            if raw_duration is not None:
                try:
                    raw_duration = int(float(raw_duration) * 1000)
                except (ValueError, TypeError):
                    raw_duration = None
        if raw_duration is not None:
            try:
                duration_ms = int(raw_duration)
            except (ValueError, TypeError):
                duration_ms = None

        # ── 2. Upsert into the music database ─────────────────────────────
        # Build a minimal SoulSyncTrack so the existing LibraryManager
        # upsert pipeline handles Artist / Album / Track creation.
        # album_title is a required positional field on SoulSyncTrack; fall
        # back to empty string when the tag is absent.
        track_obj = SoulSyncTrack(
            raw_title=title,
            artist_name=artist_name,
            album_title=album_title or "",
            duration=duration_ms,
            isrc=isrc,
            file_path=str(path),
        )

        try:
            db = get_database()
            # bulk_import is the only public upsert API; it manages its own
            # session via session_factory and handles Artist / Album / Track
            # get-or-create internally.
            lib_manager = LibraryManager(db.session_factory)
            lib_manager.bulk_import([track_obj])
            logger.info("Watcher: DB upsert complete for '%s' by '%s'", title, artist_name)
        except Exception as db_err:
            logger.error("Watcher: DB upsert failed for %s: %s", path.name, db_err)

        # ── 3. Emit TRACK_IMPORTED via the event bus ───────────────────────
        # The DownloadManager listens for this event and will silently cancel
        # any queued downloads whose ISRC matches the newly arrived file.
        payload: dict[str, Any] = {
            "event": "TRACK_IMPORTED",
            "track": {
                "title": title,
                "artist_name": artist_name,
                "album_title": album_title,
                "duration_ms": duration_ms,
                "isrc": isrc,
                "file_path": str(path),
                "source": "local_server",
            },
        }
        event_bus.publish(payload)  # type: ignore[union-attr]
        logger.info(
            "Watcher: emitted TRACK_IMPORTED for '%s' by '%s' (ISRC: %s)",
            title,
            artist_name,
            isrc or "n/a",
        )

    except Exception as exc:
        logger.error(
            "Watcher: unexpected error processing %s: %s",
            path,
            exc,
            exc_info=True,
        )


# ── Service class ──────────────────────────────────────────────────────────────

class LibraryWatcherService:
    """
    Manages the watchdog Observer lifecycle.

    Usage:
        watcher = LibraryWatcherService()
        watcher.start()          # non-blocking; observer runs in a daemon thread
        …
        watcher.stop()           # graceful shutdown
    """

    def __init__(self) -> None:
        self._observer: Any = None  # watchdog Observer — no PEP 484 stubs shipped
        self._handler: Optional[_AudioEventHandler] = None
        self._started = False

    def start(self) -> None:
        """
        Resolve the library directory from config and start the OS watcher.

        If the library directory is not configured or does not exist, the
        watcher is not started and a warning is logged.  This allows the app
        to boot cleanly even before a user has pointed it at a library.
        """
        if self._started:
            logger.warning("LibraryWatcherService.start() called more than once — ignoring")
            return

        library_dir = config_manager.get_library_dir()
        if not library_dir:
            logger.warning(
                "LibraryWatcherService: library directory is not configured — watcher disabled"
            )
            return

        library_path = Path(library_dir)
        if not library_path.exists():
            logger.warning(
                "LibraryWatcherService: library directory does not exist (%s) — watcher disabled",
                library_path,
            )
            return

        self._handler = _AudioEventHandler()
        self._observer = Observer()
        assert self._observer is not None
        self._observer.schedule(
            self._handler,
            str(library_path),
            recursive=True,
        )
        self._observer.start()
        self._started = True
        logger.info(
            "LibraryWatcherService started — monitoring '%s' (recursive)",
            library_path,
        )

    def stop(self) -> None:
        """Gracefully stop the observer thread and cancel pending debounce timers."""
        if not self._started:
            return

        if self._handler is not None:
            self._handler.cancel_all()

        if self._observer is not None:
            self._observer.stop()
            try:
                self._observer.join(timeout=5)
            except Exception as exc:
                logger.warning("LibraryWatcherService: error joining observer thread: %s", exc)

        self._started = False
        logger.info("LibraryWatcherService stopped")


# ── Module-level singleton ─────────────────────────────────────────────────────

_watcher_instance: Optional[LibraryWatcherService] = None
_watcher_lock = threading.Lock()


def get_library_watcher() -> LibraryWatcherService:
    """Return the process-wide LibraryWatcherService singleton (lazy-init)."""
    global _watcher_instance
    if _watcher_instance is None:
        with _watcher_lock:
            if _watcher_instance is None:
                _watcher_instance = LibraryWatcherService()
    return _watcher_instance
