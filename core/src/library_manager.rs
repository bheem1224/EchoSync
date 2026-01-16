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
use crossbeam_channel::{unbounded, bounded, Sender, Receiver};

// --- Message Enum ---
enum LibraryMessage {
    UpsertTrack {
        track: SoulSyncTrack,
        reply: Sender<Result<i64, String>>,
    },
    BulkInsert {
        tracks: Vec<SoulSyncTrack>,
    },
    Search {
        query: String,
        reply: Sender<Vec<SoulSyncTrack>>,
    },
    GetAllPaths {
        reply: Sender<Result<HashSet<String>, String>>,
    },
    DeleteTrack {
        path: String,
        reply: Sender<Result<(), String>>,
    },
}

// --- Actor Implementation ---
struct LibraryActor {
    conn: Connection,
    artist_cache: HashMap<String, i64>,
    album_cache: HashMap<(String, i64), i64>,
}

impl LibraryActor {
    fn new(db_path: PathBuf) -> Result<Self, String> {
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }

        debug!("Opening database at {:?}", db_path);
        let conn = Connection::open(db_path).map_err(|e| format!("Failed to open DB: {}", e))?;

        // Enable Foreign Keys
        conn.execute("PRAGMA foreign_keys = ON", []).map_err(|e| format!("Failed to enable FK: {}", e))?;

        Ok(LibraryActor {
            conn,
            artist_cache: HashMap::new(),
            album_cache: HashMap::new(),
        })
    }

    fn run(&mut self, receiver: Receiver<LibraryMessage>) {
        while let Ok(msg) = receiver.recv() {
            match msg {
                LibraryMessage::UpsertTrack { track, reply } => {
                    let res = self.handle_upsert_track(track);
                    let _ = reply.send(res);
                }
                LibraryMessage::BulkInsert { tracks } => {
                    self.handle_bulk_insert(tracks);
                }
                LibraryMessage::Search { query, reply } => {
                    let res = self.handle_search(query);
                    let _ = reply.send(res);
                }
                LibraryMessage::GetAllPaths { reply } => {
                    let res = self.handle_get_all_paths();
                    let _ = reply.send(res);
                }
                LibraryMessage::DeleteTrack { path, reply } => {
                    let res = self.handle_delete_track(path);
                    let _ = reply.send(res);
                }
            }
        }
    }

    fn normalize(s: &str) -> String {
        s.trim().to_lowercase()
    }

    fn get_or_create_artist(
        tx: &Transaction,
        artist_cache: &mut HashMap<String, i64>,
        name: &str,
        sort_name: Option<&str>
    ) -> Result<i64, String> {
        let norm_name = Self::normalize(name);

        if let Some(id) = artist_cache.get(&norm_name) {
            return Ok(*id);
        }

        let mut stmt = tx.prepare("SELECT id FROM artists WHERE lower(name) = ?1").unwrap();
        let artist_id: Option<i64> = stmt.query_row(params![norm_name], |row| row.get(0)).optional().unwrap();

        if let Some(id) = artist_id {
            artist_cache.insert(norm_name, id);
            return Ok(id);
        }

        tx.execute(
            "INSERT INTO artists (name, sort_name) VALUES (?1, ?2)",
            params![name, sort_name],
        ).map_err(|e| format!("Failed to insert artist: {}", e))?;

        let id = tx.last_insert_rowid();
        artist_cache.insert(norm_name, id);
        Ok(id)
    }

    #[allow(clippy::too_many_arguments)]
    fn get_or_create_album(
        tx: &Transaction,
        album_cache: &mut HashMap<(String, i64), i64>,
        title: &str,
        artist_id: i64,
        release_year: Option<i32>,
        album_type: Option<&str>,
        release_group_id: Option<&str>,
        mb_release_id: Option<&str>,
        original_release_date: Option<NaiveDate>,
    ) -> Result<i64, String> {
        let norm_title = Self::normalize(title);
        let cache_key = (norm_title.clone(), artist_id);

        if let Some(id) = album_cache.get(&cache_key) {
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

        let mut stmt = tx.prepare("SELECT id FROM albums WHERE lower(title) = ?1 AND artist_id = ?2").unwrap();
        let album_id: Option<i64> = stmt.query_row(params![norm_title, artist_id], |row| row.get(0)).optional().unwrap();

        let release_date = release_year.map(|y| NaiveDate::from_ymd_opt(y, 1, 1).unwrap());

        if let Some(id) = album_id {
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

             album_cache.insert(cache_key, id);
             return Ok(id);
        }

        tx.execute(
            "INSERT INTO albums (title, artist_id, release_date, album_type, release_group_id, mb_release_id, original_release_date)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![title, artist_id, release_date, album_type, release_group_id, mb_release_id, original_release_date],
        ).map_err(|e| format!("Failed to insert album: {}", e))?;

        let id = tx.last_insert_rowid();
        album_cache.insert(cache_key, id);
        Ok(id)
    }

    fn find_track_by_identifiers(tx: &Transaction, identifiers: &HashMap<String, String>) -> Result<Option<i64>, String> {
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

    fn find_track_by_metadata(tx: &Transaction, title: &str, artist_id: i64, album_id: i64) -> Result<Option<i64>, String> {
        let norm_title = Self::normalize(title);
        let mut stmt = tx.prepare("SELECT id FROM tracks WHERE lower(title) = ?1 AND artist_id = ?2 AND album_id = ?3").unwrap();
        let track_id: Option<i64> = stmt.query_row(params![norm_title, artist_id, album_id], |row| row.get(0)).optional().unwrap();
        Ok(track_id)
    }

    fn upsert_track_inner(
        tx: &Transaction,
        artist_cache: &mut HashMap<String, i64>,
        album_cache: &mut HashMap<(String, i64), i64>,
        track: &SoulSyncTrack
    ) -> Result<i64, String> {
        let artist_id = Self::get_or_create_artist(tx, artist_cache, &track.artist_name, track.artist_sort_name.as_deref())?;

        let album_id = Self::get_or_create_album(
            tx,
            album_cache,
            &track.album_title,
            artist_id,
            track.release_year,
            track.album_type.as_deref(),
            track.album_release_group_id.as_deref(),
            track.mb_release_id.as_deref(),
            track.original_release_date
        )?;

        let mut track_id = Self::find_track_by_identifiers(tx, &track.identifiers)?;
        if track_id.is_none() {
            track_id = Self::find_track_by_metadata(tx, &track.title, artist_id, album_id)?;
        }

        let final_track_id = if let Some(tid) = track_id {
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
            ]).map_err(|e| format!("Failed to update track: {}", e))?;

            debug!("Updated track: {} (id: {})", track.title, tid);
            tid
        } else {
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
            ]).map_err(|e| format!("Failed to insert track: {}", e))?;

            let tid = tx.last_insert_rowid();
            debug!("Inserted track: {} (id: {})", track.title, tid);
            tid
        };

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

        if let Some(ref fingerprint) = track.fingerprint {
            let mut check_stmt = tx.prepare("SELECT id, track_id, acoustid_id FROM audio_fingerprints WHERE fingerprint_hash = ?1").unwrap();

            let existing: Option<(i64, i64, Option<String>)> = check_stmt.query_row(params![fingerprint], |row| {
                Ok((row.get(0)?, row.get(1)?, row.get(2)?))
            }).optional().unwrap();

            if let Some((row_id, current_track_id, current_aid)) = existing {
                 if current_track_id != final_track_id {
                     tx.execute("UPDATE audio_fingerprints SET track_id = ?1 WHERE id = ?2", params![final_track_id, row_id]).unwrap();
                 }
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

    fn handle_upsert_track(&mut self, track: SoulSyncTrack) -> Result<i64, String> {
        let tx = self.conn.transaction().map_err(|e| format!("Failed to start transaction: {}", e))?;
        // Pass caches explicitly to avoid "cannot borrow *self as mutable more than once"
        match Self::upsert_track_inner(&tx, &mut self.artist_cache, &mut self.album_cache, &track) {
            Ok(id) => {
                tx.commit().map_err(|e| format!("Failed to commit transaction: {}", e))?;
                Ok(id)
            },
            Err(e) => Err(e),
        }
    }

    fn handle_bulk_insert(&mut self, tracks: Vec<SoulSyncTrack>) {
        if tracks.is_empty() { return; }

        let tx = match self.conn.transaction() {
            Ok(tx) => tx,
            Err(e) => {
                error!("Failed to start transaction for bulk insert: {}", e);
                return;
            }
        };

        let mut count = 0;
        for track in tracks {
            if let Err(e) = Self::upsert_track_inner(&tx, &mut self.artist_cache, &mut self.album_cache, &track) {
                error!("Failed to upsert track in bulk: {}", e);
            } else {
                count += 1;
            }
        }

        if let Err(e) = tx.commit() {
             error!("Failed to commit bulk insert transaction: {}", e);
        } else {
             info!("Bulk insert completed: {} tracks", count);
        }
    }

    fn handle_get_all_paths(&mut self) -> Result<HashSet<String>, String> {
        let mut stmt = self.conn.prepare("SELECT file_path FROM tracks WHERE file_path IS NOT NULL").unwrap();
        let paths: HashSet<String> = stmt.query_map([], |row| row.get(0)).map_err(|e| e.to_string())?
            .filter_map(Result::ok)
            .collect();
        Ok(paths)
    }

    fn handle_delete_track(&mut self, path: String) -> Result<(), String> {
        self.conn.execute("DELETE FROM tracks WHERE file_path = ?1", params![path])
            .map_err(|e| format!("Failed to delete track: {}", e))?;
        Ok(())
    }

    fn handle_search(&mut self, query: String) -> Vec<SoulSyncTrack> {
        // Broad search: Title, Artist, or Album matches query
        let q = format!("%{}%", query.trim());
        let sql = "
            SELECT
                t.title, ar.name, al.title
            FROM tracks t
            JOIN artists ar ON t.artist_id = ar.id
            JOIN albums al ON t.album_id = al.id
            WHERE t.title LIKE ?1 OR ar.name LIKE ?1 OR al.title LIKE ?1
            LIMIT 50
        ";

        let mut stmt = match self.conn.prepare(sql) {
            Ok(s) => s,
            Err(e) => {
                error!("Failed to prepare search statement: {}", e);
                return Vec::new();
            }
        };

        let rows = stmt.query_map(params![q], |row| {
             let title: String = row.get(0)?;
             let artist: String = row.get(1)?;
             let album: String = row.get(2)?;
             Ok(SoulSyncTrack::new_rust(title, artist, album))
        });

        match rows {
            Ok(iter) => iter.filter_map(Result::ok).collect(),
            Err(e) => {
                 error!("Search query failed: {}", e);
                 Vec::new()
            }
        }
    }
}

// --- LibraryManager Facade ---
#[pyclass]
pub struct LibraryManager {
    sender: Sender<LibraryMessage>,

    // Debouncing Logic
    pending_scans: Arc<Mutex<HashMap<String, (Instant, Py<PyAny>)>>>,
    scan_running: Arc<Mutex<bool>>,
}

#[pymethods]
impl LibraryManager {
    #[new]
    fn new() -> PyResult<Self> {
        let db_path = config_manager::get_database_path();

        let (sender, receiver) = unbounded();

        // Spawn Actor Thread
        thread::spawn(move || {
            match LibraryActor::new(db_path) {
                Ok(mut actor) => actor.run(receiver),
                Err(e) => error!("Failed to initialize LibraryActor: {}", e),
            }
        });

        let manager = LibraryManager {
            sender,
            pending_scans: Arc::new(Mutex::new(HashMap::new())),
            scan_running: Arc::new(Mutex::new(true)),
        };

        // Start background scanner thread (Separate from DB Actor)
        manager.start_scan_monitor();

        Ok(manager)
    }

    /// Schedules a debounced scan for the given path.
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
        // Note: The actor thread will exit when the channel sender is dropped (when LibraryManager is dropped)
    }

    pub fn upsert_track(&self, track: SoulSyncTrack) -> PyResult<i64> {
        let (reply_tx, reply_rx) = bounded(1);

        self.sender.send(LibraryMessage::UpsertTrack { track, reply: reply_tx })
            .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Failed to send message to DB Actor"))?;

        // Block waiting for response
        match reply_rx.recv() {
            Ok(Ok(id)) => Ok(id),
            Ok(Err(e)) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e)),
            Err(_) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("DB Actor closed channel")),
        }
    }

    pub fn process_batch(&self, tracks: Vec<SoulSyncTrack>) -> PyResult<()> {
        self.sender.send(LibraryMessage::BulkInsert { tracks })
             .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Failed to send message to DB Actor"))?;

        Ok(())
    }

    pub fn get_all_paths(&self) -> PyResult<HashSet<String>> {
        let (reply_tx, reply_rx) = bounded(1);
        self.sender.send(LibraryMessage::GetAllPaths { reply: reply_tx })
             .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Failed to send message to DB Actor"))?;

        match reply_rx.recv() {
            Ok(Ok(paths)) => Ok(paths),
            Ok(Err(e)) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e)),
            Err(_) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("DB Actor closed channel")),
        }
    }

    pub fn delete_track_by_path(&self, path: String) -> PyResult<()> {
        let (reply_tx, reply_rx) = bounded(1);
        self.sender.send(LibraryMessage::DeleteTrack { path, reply: reply_tx })
             .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Failed to send message to DB Actor"))?;

        match reply_rx.recv() {
            Ok(Ok(())) => Ok(()),
            Ok(Err(e)) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e)),
            Err(_) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("DB Actor closed channel")),
        }
    }

    pub fn search(&self, query: String) -> PyResult<Vec<SoulSyncTrack>> {
        let (reply_tx, reply_rx) = bounded(1);
        self.sender.send(LibraryMessage::Search { query, reply: reply_tx })
             .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Failed to send message to DB Actor"))?;

        match reply_rx.recv() {
            Ok(tracks) => Ok(tracks),
            Err(_) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("DB Actor closed channel")),
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
                        if let Some((deadline, _)) = map.get(&key) {
                            if now >= *deadline {
                                if let Some((_, callback)) = map.remove(&key) {
                                    tasks_to_run.push((key, callback));
                                }
                            }
                        }
                    }
                }

                // Execute tasks (Calls Python, triggering GIL)
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
}
