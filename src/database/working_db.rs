use rusqlite::{Connection, Result as SqlResult};
use std::path::Path;
use std::sync::Mutex;
use std::time::Duration;

/// Lightweight, thread-safe connection pool strictly scoped to working.db.
///
/// CRITICAL: Rust only manages application state and job tracking in working.db WAL mode.
/// Do NOT write any code that connects to media_library.db or library.db here.
pub struct WorkingDbPool {
    db_path: String,
    conn: Mutex<Connection>,
}

impl WorkingDbPool {
    /// Initialize a new connection to working.db with 5000ms busy timeout and WAL mode.
    pub fn new<P: AsRef<Path>>(path: P) -> SqlResult<Self> {
        let db_path = path.as_ref().to_string_lossy().to_string();
        let conn = Connection::open(&path)?;

        // Enable WAL mode and 5000ms busy timeout for SQLite concurrency
        conn.busy_timeout(Duration::from_millis(5000))?;
        let _ = conn.pragma_update(None, "journal_mode", "WAL");
        let _ = conn.pragma_update(None, "synchronous", "NORMAL");

        Ok(WorkingDbPool {
            db_path,
            conn: Mutex::new(conn),
        })
    }

    pub fn db_path(&self) -> &str {
        &self.db_path
    }

    /// Safely execute a query closure against the thread-safe connection.
    pub fn execute<F, R>(&self, f: F) -> SqlResult<R>
    where
        F: FnOnce(&Connection) -> SqlResult<R>,
    {
        let conn = self.conn.lock().unwrap();
        f(&*conn)
    }
}
