"""
System-wide mutual exclusion locks for background synchronization operations.
Prevents race conditions and collision loops between library synchronization,
auto-importers, and download processing.
"""

import threading
import logging
from contextlib import contextmanager

logger = logging.getLogger("core.system_lock")

# Global re-entrant lock coordinating all library ingestion/sync pipelines
_LIBRARY_MUTEX = threading.RLock()


def get_library_mutex() -> threading.RLock:
    """Return the global library synchronization mutex."""
    return _LIBRARY_MUTEX


@contextmanager
def acquire_library_lock(task_name: str = "unknown", blocking: bool = True, timeout: float = -1):
    """
    Context manager to acquire the global library mutex with optional timeout and logging.
    """
    acquired = _LIBRARY_MUTEX.acquire(blocking=blocking, timeout=timeout)
    if not acquired:
        logger.warning(f"Task '{task_name}' failed to acquire library synchronization lock.")
        yield False
        return

    try:
        logger.debug(f"Task '{task_name}' acquired library synchronization lock.")
        yield True
    finally:
        _LIBRARY_MUTEX.release()
        logger.debug(f"Task '{task_name}' released library synchronization lock.")
