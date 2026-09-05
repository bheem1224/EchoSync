import logging
import queue
import sqlite3
import threading
import time
from collections.abc import Callable
from typing import Any

_engine_logger = logging.getLogger("database.engine")

# SQLite error messages that indicate the connection itself is permanently broken
# and must be recycled rather than just rolled back.
_FATAL_IO_MSGS = ("disk i/o error", "database disk image is malformed")


def _is_fatal_connection_error(exc: Exception) -> bool:
    """Return True if the exception indicates the connection is permanently broken."""
    msg = str(exc).lower()
    return any(pat in msg for pat in _FATAL_IO_MSGS)


class _DBWriter:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._tasks: queue.Queue[tuple] = queue.Queue(maxsize=1000)
        self._stop = threading.Event()
        self._thread = self._make_thread()
        self._thread.start()

    def _make_thread(self) -> threading.Thread:
        t = threading.Thread(
            target=self._run, daemon=True, name=f"DBWriter:{self.db_path}"
        )
        return t

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=60.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -2000")
        conn.execute("PRAGMA wal_autocheckpoint = 100")
        return conn

    def _run(self):
        conn = None
        cursor = None

        def _connect():
            nonlocal conn, cursor
            # Close any stale connection before reconnecting
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            retries = 0
            while not self._stop.is_set():
                try:
                    conn = self._get_connection()
                    cursor = conn.cursor()
                    return
                except Exception as exc:
                    retries += 1
                    wait = min(2**retries, 30)
                    _engine_logger.warning(
                        f"[DBWriter] Cannot open {self.db_path}, retrying in {wait}s: {exc}"
                    )
                    time.sleep(wait)

        _connect()

        while not self._stop.is_set():
            try:
                task, result_q = self._tasks.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                res = task(cursor)
                conn.commit()
                if result_q:
                    result_q.put((True, res))
            except Exception as e:
                # Attempt rollback; if it fails, the connection is broken
                try:
                    conn.rollback()
                except Exception:
                    pass

                if _is_fatal_connection_error(e):
                    _engine_logger.error(
                        f"[DBWriter] Fatal connection error on {self.db_path}, reconnecting: {e}"
                    )
                    # Fail this task to its caller, then reconnect for the next one
                    if result_q:
                        result_q.put((False, e))
                    _connect()
                else:
                    if result_q:
                        result_q.put((False, e))
            finally:
                self._tasks.task_done()

    def _ensure_alive(self):
        """Restart the writer thread if it has died unexpectedly."""
        if not self._thread.is_alive():
            _engine_logger.warning(
                f"[DBWriter] Writer thread for {self.db_path} died — restarting."
            )
            self._thread = self._make_thread()
            self._thread.start()

    def enqueue(
        self,
        fn: Callable[[sqlite3.Cursor], Any],
        wait: bool = True,
        timeout: float | None = None,
    ):
        self._ensure_alive()
        result_q: queue.Queue | None = queue.Queue() if wait else None
        try:
            self._tasks.put((fn, result_q), timeout=2.0)
        except queue.Full:
            _engine_logger.critical(
                f"[DBWriter] Queue is full! Dropping configuration update to prevent MemoryError. "
                f"The database disk may be locked or too slow. DB: {self.db_path}"
            )
            if wait:
                raise TimeoutError("Database writer queue is full. Task dropped.")
            return None

        if not wait:
            return None
        try:
            ok, value = result_q.get(timeout=timeout)
            if not ok:
                raise value
            return value
        finally:
            pass

    def stop(self):
        self._tasks.join()  # drain all pending writes before stopping
        self._stop.set()
        self._thread.join(timeout=5.0)


_writers: dict[str, _DBWriter] = {}
_writers_lock = threading.Lock()


def ensure_writer(db_path: str) -> _DBWriter:
    key = str(db_PATH_normalize(db_path))
    with _writers_lock:
        if key not in _writers:
            _writers[key] = _DBWriter(key)
    return _writers[key]


def db_PATH_normalize(p: str) -> str:
    # sqlite accepts normal paths; ensure string
    return str(p)


def execute_write(
    db_path: str,
    fn: Callable[[sqlite3.Cursor], Any],
    wait: bool = True,
    timeout: float | None = None,
):
    writer = ensure_writer(db_path)
    return writer.enqueue(fn, wait=wait, timeout=timeout)


def execute_write_sql(
    db_path: str, sql: str, params: tuple = (), return_lastrowid: bool = False
):
    def _task(cursor):
        cursor.execute(sql, params)
        if return_lastrowid:
            return cursor.lastrowid
        return cursor.rowcount

    return execute_write(db_path, _task)
