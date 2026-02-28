import sqlite3
import threading
import queue
import time
from typing import Callable, Any, Optional


class _DBWriter:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._tasks: "queue.Queue[tuple]" = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._stop = threading.Event()
        self._thread.start()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _run(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        while not self._stop.is_set():
            try:
                task, result_q = self._tasks.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                # task is a callable that receives a cursor
                res = task(cursor)
                conn.commit()
                if result_q:
                    result_q.put((True, res))
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                if result_q:
                    result_q.put((False, e))
            finally:
                self._tasks.task_done()

    def enqueue(self, fn: Callable[[sqlite3.Cursor], Any], wait: bool = True, timeout: Optional[float] = None):
        result_q: Optional[queue.Queue] = queue.Queue() if wait else None
        self._tasks.put((fn, result_q))
        if not wait:
            return None
        try:
            ok, value = result_q.get(timeout=timeout)
            if not ok:
                raise value
            return value
        finally:
            # help GC
            pass

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1.0)


_writers: dict[str, _DBWriter] = {}


def ensure_writer(db_path: str) -> _DBWriter:
    key = str(db_PATH_normalize(db_path))
    if key not in _writers:
        _writers[key] = _DBWriter(key)
    return _writers[key]


def db_PATH_normalize(p: str) -> str:
    # sqlite accepts normal paths; ensure string
    return str(p)


def execute_write(db_path: str, fn: Callable[[sqlite3.Cursor], Any], wait: bool = True, timeout: Optional[float] = None):
    writer = ensure_writer(db_path)
    return writer.enqueue(fn, wait=wait, timeout=timeout)


def execute_write_sql(db_path: str, sql: str, params: tuple = (), return_lastrowid: bool = False):
    def _task(cursor):
        cursor.execute(sql, params)
        if return_lastrowid:
            return cursor.lastrowid
        return cursor.rowcount

    return execute_write(db_path, _task)
