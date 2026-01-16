use pyo3::prelude::*;
use walkdir::WalkDir;
use std::collections::HashSet;
use std::path::Path;
use log::{info, error, debug};
use crate::library_manager::LibraryManager;
use crate::structs::SoulSyncTrack;
use crate::post_processor::PostProcessor;

#[pyclass]
pub struct ScannerService {}

#[pymethods]
impl ScannerService {
    #[new]
    fn new() -> Self {
        ScannerService {}
    }

    /// Scans the directory and syncs with DB.
    /// Returns (added_count, removed_count)
    fn scan(&self, py: Python<'_>, library_manager: Py<LibraryManager>, root_path: String) -> PyResult<(usize, usize)> {
        let manager = library_manager.borrow(py);
        let pp = PostProcessor::new_rust();

        info!("Starting scan of {}", root_path);

        // 1. Get existing paths from DB
        let db_paths = manager.get_all_paths()?;
        debug!("Found {} tracks in DB", db_paths.len());

        // 2. Walk directory
        let mut fs_paths = HashSet::new();
        let mut added_tracks = Vec::new();

        for entry in WalkDir::new(&root_path).into_iter().filter_map(|e| e.ok()) {
            if entry.file_type().is_file() {
                if let Some(path_str) = entry.path().to_str() {
                    let s = path_str.to_string();
                    // Filter extensions
                    if is_audio_file(&s) {
                        fs_paths.insert(s.clone());

                        if !db_paths.contains(&s) {
                            // New file!
                            // Read tags using PostProcessor logic
                            if let Some(track) = pp.read_tags_rust(&s) {
                                added_tracks.push(track);
                            }
                        }
                    }
                }
            }
        }

        // 3. Detect Removed
        let mut removed_count = 0;
        for db_path in &db_paths {
            if !fs_paths.contains(db_path) && db_path.starts_with(&root_path) {
                // Only remove if it belongs to the scanned root!
                manager.delete_track_by_path(db_path.to_string())?;
                removed_count += 1;
            }
        }

        // 4. Batch Insert Added
        let added_count = added_tracks.len();
        if added_count > 0 {
             info!("Importing {} new tracks...", added_count);
             // We can insert in batches
             for chunk in added_tracks.chunks(100) {
                 manager.process_batch(chunk.to_vec())?;
             }
        }

        info!("Scan complete. Added: {}, Removed: {}", added_count, removed_count);
        Ok((added_count, removed_count))
    }
}

fn is_audio_file(path: &str) -> bool {
    let lower = path.to_lowercase();
    lower.ends_with(".mp3") || lower.ends_with(".flac") || lower.ends_with(".m4a") ||
    lower.ends_with(".ogg") || lower.ends_with(".wav") || lower.ends_with(".opus")
}
