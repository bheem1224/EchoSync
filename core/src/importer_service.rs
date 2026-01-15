use pyo3::prelude::*;
use notify::{Watcher, RecursiveMode, Result, Event, EventKind};
use std::sync::mpsc::{channel, Receiver, Sender};
use std::thread;
use std::time::Duration;
use std::path::PathBuf;
use log::{info, error, debug, warn};
use crate::library_manager::LibraryManager;
use crate::post_processor::PostProcessor;
use std::sync::{Arc, Mutex};

#[pyclass]
pub struct ImporterService {
    // We keep the watcher alive
    watcher: Arc<Mutex<Option<notify::RecommendedWatcher>>>,
    // Channel to stop the thread? Or just let it run.
    running: Arc<Mutex<bool>>,
}

#[pymethods]
impl ImporterService {
    #[new]
    fn new() -> Self {
        ImporterService {
            watcher: Arc::new(Mutex::new(None)),
            running: Arc::new(Mutex::new(false)),
        }
    }

    /// Starts the file watcher on the given directory.
    /// Uses a background thread to process events and sync with LibraryManager.
    /// Note: This spawns a thread that creates its own Python GIL context when needed.
    fn start_watcher(&self, _py: Python<'_>, path: String, library_manager: Py<LibraryManager>) -> PyResult<()> {
        let (tx, rx): (Sender<Result<Event>>, Receiver<Result<Event>>) = channel();

        // Initialize Watcher
        let mut watcher = notify::recommended_watcher(tx).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create watcher: {}", e))
        })?;

        let path_buf = PathBuf::from(&path);
        watcher.watch(&path_buf, RecursiveMode::Recursive).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to watch path: {}", e))
        })?;

        {
            let mut w = self.watcher.lock().unwrap();
            *w = Some(watcher);
            let mut r = self.running.lock().unwrap();
            *r = true;
        }

        let running_clone = self.running.clone();

        // Spawn background thread to handle events
        thread::spawn(move || {
            let pp = PostProcessor::new_rust();

            loop {
                // Check stop condition
                {
                    let r = running_clone.lock().unwrap();
                    if !*r { break; }
                }

                // Blocking receive with timeout to allow checking stop condition
                match rx.recv_timeout(Duration::from_millis(500)) {
                    Ok(res) => {
                        match res {
                            Ok(event) => {
                                handle_event(event, &library_manager, &pp);
                            },
                            Err(e) => error!("Watch error: {}", e),
                        }
                    },
                    Err(_) => {
                        // Timeout, just check running loop
                    }
                }
            }
            info!("Watcher thread stopped.");
        });

        info!("Started watcher on {}", path);
        Ok(())
    }

    fn stop_watcher(&self) {
        let mut r = self.running.lock().unwrap();
        *r = false;
        // Watcher is dropped when struct is dropped or overwritten, but we keep it in Arc.
        // Explicitly dropping/clearing it:
        let mut w = self.watcher.lock().unwrap();
        *w = None;
    }
}

fn handle_event(event: Event, library_manager: &Py<LibraryManager>, pp: &PostProcessor) {
    debug!("FS Event: {:?}", event);

    match event.kind {
        EventKind::Create(_) | EventKind::Modify(_) => {
            for path in event.paths {
                 if path.is_file() {
                     if let Some(s) = path.to_str() {
                         if is_audio_file(s) {
                             // Process File
                             info!("File changed/added: {}", s);

                             // Parse and Upsert
                             // We need to acquire GIL to call LibraryManager
                             if let Some(track) = pp.read_tags_rust(s) {
                                 Python::with_gil(|py| {
                                     let manager = library_manager.borrow(py);
                                     if let Err(e) = manager.upsert_track(track) {
                                         error!("Failed to upsert track {}: {}", s, e);
                                     }
                                 });
                             }
                         }
                     }
                 }
            }
        },
        EventKind::Remove(_) => {
             for path in event.paths {
                 if let Some(s) = path.to_str() {
                     // Remove from DB
                     info!("File removed: {}", s);
                     Python::with_gil(|py| {
                         let manager = library_manager.borrow(py);
                         if let Err(e) = manager.delete_track_by_path(s.to_string()) {
                             error!("Failed to delete track {}: {}", s, e);
                         }
                     });
                 }
             }
        },
        _ => {}
    }
}

fn is_audio_file(path: &str) -> bool {
    let lower = path.to_lowercase();
    lower.ends_with(".mp3") || lower.ends_with(".flac") || lower.ends_with(".m4a") ||
    lower.ends_with(".ogg") || lower.ends_with(".wav") || lower.ends_with(".opus")
}
