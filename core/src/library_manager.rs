use pyo3::prelude::*;
use rusqlite::{params, Connection, OptionalExtension, Transaction};
use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use std::thread;
use std::path::PathBuf;
use log::{debug, info, warn, error};
use crate::structs::SoulSyncTrack;
use crate::config_manager;
use chrono::NaiveDate;

#[pyclass]
pub struct LibraryManager {
    conn: Arc<Mutex<Connection>>,
    artist_cache: Arc<Mutex<HashMap<String, i64>>>,
    album_cache: Arc<Mutex<HashMap<(String, i64), i64>>>,

    // Debouncing Logic
    pending_scans: Arc<Mutex<HashMap<String, (Instant, Py<PyAny>)>>>,
    scan_running: Arc<Mutex<bool>>,
}

#[pymethods]
impl LibraryManager {
    #[new]
    fn new() -> PyResult<Self> {
        let db_path = config_manager::get_database_path();

        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        debug!("Opening database at {:?}", db_path);
        let conn = Connection::open(db_path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to open DB: {}", e))
        })?;

        // Enable Foreign Keys
        conn.execute("PRAGMA foreign_keys = ON", []).map_err(|e| {
             PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to enable FK: {}", e))
        })?;

        let manager = LibraryManager {
            conn: Arc::new(Mutex::new(conn)),
            artist_cache: Arc::new(Mutex::new(HashMap::new())),
            album_cache: Arc::new(Mutex::new(HashMap::new())),
            pending_scans: Arc::new(Mutex::new(HashMap::new())),
            scan_running: Arc::new(Mutex::new(true)),
        };

        // Start background scanner thread
        manager.start_scan_monitor();

        Ok(manager)
    }

    /// Schedules a debounced scan for the given path.
    /// If a scan is already pending for this path, the timer is reset.
    fn debounced_scan(&self, path: String, callback: Py<PyAny>) {
        let mut pending = self.pending_scans.lock().unwrap();
        let deadline = Instant::now() + Duration::from_secs(5);

        if pending.contains_key(&path) {
            debug!("Rescheduling scan for path: {}", path);
        } else {
            debug!("Scheduling new scan for path: {}", path);
        }

        pending.insert(path, (deadline, callback));
    }

    fn stop(&self) {
        let mut running = self.scan_running.lock().unwrap();
        *running = false;
    }

    fn upsert_track(&self, track: &SoulSyncTrack) -> PyResult<i64> {
        let conn_guard = self.conn.lock().unwrap();
        let mut conn = conn_guard;
        let tx = conn.transaction().map_err(|e| {
             PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to start transaction: {}", e))
        })?;

        let result = self.upsert_track_inner(&tx, track);

        match result {
            Ok(track_id) => {
                tx.commit().map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to commit transaction: {}", e))
                })?;
                Ok(track_id)
            }
            Err(e) => {
                Err(e)
            }
        }
    }
}

impl LibraryManager {
    fn start_scan_monitor(&self) {
        let pending = self.pending_scans.clone();
        let running = self.scan_running.clone();

        thread::spawn(move || {
            loop {
                // Check if we should stop
                {
                    let r = running.lock().unwrap();
                    if !*r {
                        break;
                    }
                }

                thread::sleep(Duration::from_millis(500));

                let now = Instant::now();
                let mut tasks_to_run = Vec::new();

                // Check for expired timers
                {
                    let mut map = pending.lock().unwrap();
                    let keys: Vec<String> = map.keys().cloned().collect();

                    for key in keys {
                        // Check if expired
                        let should_run = if let Some((deadline, _)) = map.get(&key) {
                            now >= *deadline
                        } else {
                            false
                        };

                        if should_run {
                            // Remove and take ownership of callback
                            if let Some((_, callback)) = map.remove(&key) {
                                tasks_to_run.push((key, callback));
                            }
                        }
                    }
                }

                // Execute tasks
                for (path, callback) in tasks_to_run {
                    info!("Executing scan for path: {}", path);
                    Python::with_gil(|py| {
                        if let Err(e) = callback.call1(py, (path.clone(),)) {
                            error!("Scan callback failed for path {}: {}", path, e);
                            e.print(py);
                        }
                    });
                }
            }
        });
    }

    fn normalize(&self, s: &str) -> String {
        s.trim().to_lowercase()
    }

    fn get_or_create_artist(&self, tx: &Transaction, name: &str, sort_name: Option<&str>) -> PyResult<i64> {
        let norm_name = self.normalize(name);

        // 1. Check Cache
        {
            let cache = self.artist_cache.lock().unwrap();
            if let Some(id) = cache.get(&norm_name) {
                return Ok(*id);
            }
        }

        // 2. Check DB
        let mut stmt = tx.prepare("SELECT id FROM artists WHERE lower(name) = ?1").unwrap();
        let artist_id: Option<i64> = stmt.query_row(params![norm_name], |row| row.get(0)).optional().unwrap();

        if let Some(id) = artist_id {
            let mut cache = self.artist_cache.lock().unwrap();
            cache.insert(norm_name, id);
            return Ok(id);
        }

        // 3. Create
        tx.execute(
            "INSERT INTO artists (name, sort_name) VALUES (?1, ?2)",
            params![name, sort_name],
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to insert artist: {}", e)))?;

        let id = tx.last_insert_rowid();

        {
            let mut cache = self.artist_cache.lock().unwrap();
            cache.insert(norm_name, id);
        }

        Ok(id)
    }

    #[allow(clippy::too_many_arguments)]
    fn get_or_create_album(
        &self,
        tx: &Transaction,
        title: &str,
        artist_id: i64,
        release_year: Option<i32>,
        album_type: Option<&str>,
        release_group_id: Option<&str>,
        mb_release_id: Option<&str>,
        original_release_date: Option<NaiveDate>,
    ) -> PyResult<i64> {
        let norm_title = self.normalize(title);
        let cache_key = (norm_title.clone(), artist_id);

        // 1. Check Cache
        {
            let cache = self.album_cache.lock().unwrap();
            if let Some(id) = cache.get(&cache_key) {
                 let sql = "UPDATE albums SET
                    release_group_id = COALESCE(release_group_id, ?1),
                    album_type = COALESCE(album_type, ?2),
                    mb_release_id = COALESCE(mb_release_id, ?3),
                    original_release_date = COALESCE(original_release_date, ?4),
                    release_date = COALESCE(release_date, ?5)
                    WHERE id = ?6";

                 let release_date = release_year.map(|y| NaiveDate::from_ymd_opt(y, 1, 1).unwrap());

                 tx.execute(sql, params![
                     release_group_id, album_type, mb_release_id, original_release_date, release_date, id
                 ]).unwrap();

                return Ok(*id);
            }
        }

        // 2. Check DB
        let mut stmt = tx.prepare("SELECT id FROM albums WHERE lower(title) = ?1 AND artist_id = ?2").unwrap();
        let album_id: Option<i64> = stmt.query_row(params![norm_title, artist_id], |row| row.get(0)).optional().unwrap();

        let release_date = release_year.map(|y| NaiveDate::from_ymd_opt(y, 1, 1).unwrap());

        if let Some(id) = album_id {
            // Update Metadata
             let sql = "UPDATE albums SET
                release_group_id = COALESCE(release_group_id, ?1),
                album_type = COALESCE(album_type, ?2),
                mb_release_id = COALESCE(mb_release_id, ?3),
                original_release_date = COALESCE(original_release_date, ?4),
                release_date = COALESCE(release_date, ?5)
                WHERE id = ?6";

             tx.execute(sql, params![
                 release_group_id, album_type, mb_release_id, original_release_date, release_date, id
             ]).unwrap();

             {
                 let mut cache = self.album_cache.lock().unwrap();
                 cache.insert(cache_key, id);
             }
             return Ok(id);
        }

        // 3. Create
        tx.execute(
            "INSERT INTO albums (title, artist_id, release_date, album_type, release_group_id, mb_release_id, original_release_date)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![title, artist_id, release_date, album_type, release_group_id, mb_release_id, original_release_date],
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to insert album: {}", e)))?;

        let id = tx.last_insert_rowid();
        {
            let mut cache = self.album_cache.lock().unwrap();
            cache.insert(cache_key, id);
        }

        Ok(id)
    }

    fn find_track_by_identifiers(&self, tx: &Transaction, identifiers: &HashMap<String, String>) -> PyResult<Option<i64>> {
        if identifiers.is_empty() {
            return Ok(None);
        }

        let mut stmt = tx.prepare("SELECT track_id FROM external_identifiers WHERE provider_source = ?1 AND provider_item_id = ?2").unwrap();

        for (source, id) in identifiers {
            let track_id: Option<i64> = stmt.query_row(params![source, id], |row| row.get(0)).optional().unwrap();
            if let Some(tid) = track_id {
                return Ok(Some(tid));
            }
        }
        Ok(None)
    }

    fn find_track_by_metadata(&self, tx: &Transaction, title: &str, artist_id: i64, album_id: i64) -> PyResult<Option<i64>> {
        let norm_title = self.normalize(title);
        let mut stmt = tx.prepare("SELECT id FROM tracks WHERE lower(title) = ?1 AND artist_id = ?2 AND album_id = ?3").unwrap();
        let track_id: Option<i64> = stmt.query_row(params![norm_title, artist_id, album_id], |row| row.get(0)).optional().unwrap();
        Ok(track_id)
    }

    fn upsert_track_inner(&self, tx: &Transaction, track: &SoulSyncTrack) -> PyResult<i64> {
        // 1. Get Dependencies
        let artist_id = self.get_or_create_artist(tx, &track.artist_name, track.artist_sort_name.as_deref())?;

        let album_id = self.get_or_create_album(
            tx,
            &track.album_title,
            artist_id,
            track.release_year,
            track.album_type.as_deref(),
            track.album_release_group_id.as_deref(),
            track.mb_release_id.as_deref(),
            track.original_release_date
        )?;

        // 2. Find Track
        let mut track_id = self.find_track_by_identifiers(tx, &track.identifiers)?;
        if track_id.is_none() {
            track_id = self.find_track_by_metadata(tx, &track.title, artist_id, album_id)?;
        }

        // 3. Insert or Update
        let final_track_id = if let Some(tid) = track_id {
            // UPDATE
            let sql = "UPDATE tracks SET
                title = ?1,
                artist_id = ?2,
                album_id = ?3,
                sort_title = COALESCE(?4, sort_title),
                edition = COALESCE(?5, edition),
                duration = COALESCE(?6, duration),
                track_number = COALESCE(?7, track_number),
                disc_number = COALESCE(?8, disc_number),
                bitrate = COALESCE(?9, bitrate),
                file_path = COALESCE(?10, file_path),
                file_format = COALESCE(?11, file_format),
                sample_rate = COALESCE(?12, sample_rate),
                bit_depth = COALESCE(?13, bit_depth),
                file_size_bytes = COALESCE(?14, file_size_bytes),
                musicbrainz_id = COALESCE(?15, musicbrainz_id)
                WHERE id = ?16";

            tx.execute(sql, params![
                track.title,
                artist_id,
                album_id,
                track.sort_title,
                track.edition,
                track.duration,
                track.track_number,
                track.disc_number,
                track.bitrate,
                track.file_path,
                track.file_format,
                track.sample_rate,
                track.bit_depth,
                track.file_size_bytes,
                track.musicbrainz_id,
                tid
            ]).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to update track: {}", e)))?;

            debug!("Updated track: {} (id: {})", track.title, tid);
            tid
        } else {
            // INSERT
            let sql = "INSERT INTO tracks (
                title, artist_id, album_id, sort_title, edition, duration, track_number, disc_number,
                bitrate, file_path, file_format, sample_rate, bit_depth, file_size_bytes, musicbrainz_id, added_at
            ) VALUES (
                ?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16
            )";

            tx.execute(sql, params![
                track.title,
                artist_id,
                album_id,
                track.sort_title,
                track.edition,
                track.duration,
                track.track_number,
                track.disc_number,
                track.bitrate,
                track.file_path,
                track.file_format,
                track.sample_rate,
                track.bit_depth,
                track.file_size_bytes,
                track.musicbrainz_id,
                track.added_at
            ]).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to insert track: {}", e)))?;

            let tid = tx.last_insert_rowid();
            debug!("Inserted track: {} (id: {})", track.title, tid);
            tid
        };

        // 4. Update External Identifiers
        {
             let mut check_stmt = tx.prepare("SELECT id, track_id FROM external_identifiers WHERE provider_source = ?1 AND provider_item_id = ?2").unwrap();
             let mut update_stmt = tx.prepare("UPDATE external_identifiers SET track_id = ?1 WHERE id = ?2").unwrap();
             let mut insert_stmt = tx.prepare("INSERT INTO external_identifiers (track_id, provider_source, provider_item_id) VALUES (?1, ?2, ?3)").unwrap();

             for (source, id_val) in &track.identifiers {
                 let existing: Option<(i64, i64)> = check_stmt.query_row(params![source, id_val], |row| Ok((row.get(0)?, row.get(1)?))).optional().unwrap();

                 if let Some((row_id, current_track_id)) = existing {
                     if current_track_id != final_track_id {
                         update_stmt.execute(params![final_track_id, row_id]).unwrap();
                     }
                 } else {
                     insert_stmt.execute(params![final_track_id, source, id_val]).unwrap();
                 }
             }
        }

        // 5. Update Audio Fingerprint
        if let Some(ref fingerprint) = track.fingerprint {
            let mut check_stmt = tx.prepare("SELECT id, track_id, acoustid_id FROM audio_fingerprints WHERE fingerprint_hash = ?1").unwrap();

            let existing: Option<(i64, i64, Option<String>)> = check_stmt.query_row(params![fingerprint], |row| {
                Ok((row.get(0)?, row.get(1)?, row.get(2)?))
            }).optional().unwrap();

            if let Some((row_id, current_track_id, current_aid)) = existing {
                 // Update linking
                 if current_track_id != final_track_id {
                     tx.execute("UPDATE audio_fingerprints SET track_id = ?1 WHERE id = ?2", params![final_track_id, row_id]).unwrap();
                 }
                 // Update acoustid if missing in DB but present in track
                 if current_aid.is_none() && track.acoustid_id.is_some() {
                     tx.execute("UPDATE audio_fingerprints SET acoustid_id = ?1 WHERE id = ?2", params![track.acoustid_id, row_id]).unwrap();
                 }
            } else {
                tx.execute(
                    "INSERT INTO audio_fingerprints (track_id, fingerprint_hash, acoustid_id) VALUES (?1, ?2, ?3)",
                    params![final_track_id, fingerprint, track.acoustid_id]
                ).unwrap();
            }
        }

        Ok(final_track_id)
    }

    /// Helper for batch upserts
    pub fn process_batch(&self, tracks: Vec<SoulSyncTrack>) -> PyResult<usize> {
        let conn_guard = self.conn.lock().unwrap();
        let mut conn = conn_guard;
        let tx = conn.transaction().map_err(|e| {
             PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to start transaction: {}", e))
        })?;

        let mut count = 0;
        for track in tracks {
            self.upsert_track_inner(&tx, &track)?;
            count += 1;
        }

        tx.commit().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to commit transaction: {}", e))
        })?;

        Ok(count)
    }
}
