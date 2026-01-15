use pyo3::prelude::*;
use std::collections::HashSet;
use std::sync::{Arc, RwLock};
use rusqlite::{params, Connection};
use log::{debug, error, info};
use crate::structs::SoulSyncTrack;
use crate::config_manager;

#[pyclass]
pub struct WishlistManager {
    // In-memory set of "type:id" strings
    items: Arc<RwLock<HashSet<String>>>,
}

#[pymethods]
impl WishlistManager {
    #[new]
    fn new() -> PyResult<Self> {
        let db_path = config_manager::get_database_path();

        // Ensure DB parent dir exists (just in case, though ConfigManager usually handles this)
        if let Some(parent) = db_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }

        let conn = Connection::open(&db_path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to open DB: {}", e))
        })?;

        // Prepare the set
        let mut items = HashSet::new();

        // Query existing wishlist
        // We assume the table exists. If not, we just log a warning or start empty.
        // The prompt says "Assumption: The table likely exists... Just query it."
        // We handle the case where it might not exist gracefully by checking tables or just trying to query.

        let query = "SELECT item_type, item_id FROM wishlist WHERE satisfied = 0";

        let mut stmt = match conn.prepare(query) {
            Ok(s) => s,
            Err(e) => {
                // If table doesn't exist, it's fine, start empty.
                // SQLite error for missing table usually contains "no such table"
                debug!("Could not query wishlist table (might not exist yet): {}", e);
                return Ok(WishlistManager {
                    items: Arc::new(RwLock::new(items)),
                });
            }
        };

        let rows = stmt.query_map([], |row| {
            let item_type: String = row.get(0)?;
            let item_id: String = row.get(1)?;
            Ok((item_type, item_id))
        }).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to query wishlist: {}", e))
        })?;

        for row in rows {
            if let Ok((t, id)) = row {
                let key = format!("{}:{}", t, id);
                items.insert(key);
            }
        }

        info!("Initialized WishlistManager with {} items", items.len());

        Ok(WishlistManager {
            items: Arc::new(RwLock::new(items)),
        })
    }

    /// Check if a track matches any item in the wishlist.
    /// Returns true if it matches.
    /// O(1) complexity.
    fn check_track(&self, track: &SoulSyncTrack) -> bool {
        let items = self.items.read().unwrap();

        // 1. Check Album (MB Release ID)
        if let Some(ref mid) = track.mb_release_id {
            let key = format!("album:{}", mid);
            if items.contains(&key) {
                debug!("Wishlist match found for album: {}", key);
                return true;
            }
        }

        // 2. Check Artist (MusicBrainz Artist ID)
        // Check both 'musicbrainz_artist_id' in identifiers and potentially other fields if we had them.
        // Identifiers is a HashMap<String, String>
        if let Some(artist_id) = track.identifiers.get("musicbrainz_artist_id") {
            let key = format!("artist:{}", artist_id);
            if items.contains(&key) {
                debug!("Wishlist match found for artist: {}", key);
                return true;
            }
        }

        false
    }

    /// Add a new item to the wishlist (DB and Memory).
    #[pyo3(signature = (id, type_))]
    fn add_wish(&self, id: String, type_: String) -> PyResult<()> {
        let key = format!("{}:{}", type_, id);

        // 1. Update Memory
        {
            let mut items = self.items.write().unwrap();
            if items.contains(&key) {
                return Ok(()); // Already exists
            }
            items.insert(key.clone());
        }

        // 2. Update DB
        let db_path = config_manager::get_database_path();
        let conn = Connection::open(db_path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to open DB: {}", e))
        })?;

        // Ensure table exists (idempotent) - Just to be safe for writes
        conn.execute(
            "CREATE TABLE IF NOT EXISTS wishlist (
                item_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                satisfied BOOLEAN DEFAULT 0,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (item_id, item_type)
            )",
            [],
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create table: {}", e)))?;

        conn.execute(
            "INSERT OR IGNORE INTO wishlist (item_id, item_type, satisfied) VALUES (?1, ?2, 0)",
            params![id, type_],
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to insert wish: {}", e)))?;

        info!("Added wish: {}", key);
        Ok(())
    }
}
