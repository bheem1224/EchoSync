pub mod database;
pub mod errors;
pub mod file_handling;
pub mod metadata;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};
use lofty::file::{AudioFile, TaggedFileExt};
use lofty::probe::Probe;
use lofty::tag::{Accessor, ItemKey};
use rusqlite::{Connection, Result as SqlResult};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use walkdir::WalkDir;

pub use errors::EchoSyncError;

/// Thread-safe cancellation token shared across Python/Rust FFI boundary.
#[pyclass]
#[derive(Clone)]
pub struct CancellationToken {
    is_cancelled: Arc<AtomicBool>,
}

#[pymethods]
impl CancellationToken {
    #[new]
    pub fn new() -> Self {
        CancellationToken {
            is_cancelled: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn cancel(&self) {
        self.is_cancelled.store(true, Ordering::SeqCst);
    }

    pub fn is_cancelled(&self) -> bool {
        self.is_cancelled.load(Ordering::SeqCst)
    }
}

/// Open a SQLite connection with a strict 5000ms busy timeout.
pub fn open_db_connection(db_path: &str) -> SqlResult<Connection> {
    let conn = Connection::open(db_path)?;
    conn.busy_timeout(Duration::from_millis(5000))?;
    Ok(conn)
}

struct TrackData {
    title: Option<String>,
    artist_name: Option<String>,
    album_title: Option<String>,
    duration_ms: i32,
    track_number: u32,
    disc_number: u32,
    isrc: Option<String>,
    bitrate: u32,
    file_path: String,
    file_format: String,
    file_size_bytes: u64,
}

fn flush_batch(py: Python, batch: &[TrackData], callback: &PyObject) -> PyResult<()> {
    let mut py_list_elements = Vec::with_capacity(batch.len());

    for data in batch {
        let dict = PyDict::new_bound(py);
        dict.set_item("title", &data.title)?;
        dict.set_item("artist_name", &data.artist_name)?;
        dict.set_item("album_title", &data.album_title)?;
        dict.set_item("duration_ms", data.duration_ms)?;
        dict.set_item("track_number", data.track_number)?;
        dict.set_item("disc_number", data.disc_number)?;
        dict.set_item("isrc", &data.isrc)?;
        dict.set_item("bitrate", data.bitrate)?;
        dict.set_item("file_path", &data.file_path)?;
        dict.set_item("file_format", &data.file_format)?;
        dict.set_item("file_size_bytes", data.file_size_bytes)?;
        py_list_elements.push(dict);
    }

    let py_list = PyList::new_bound(py, py_list_elements);
    callback.call1(py, (py_list,))?;
    Ok(())
}

/// Telemetry Yielding Pattern (Event Bus Prep)
/// Yields progress tuples `(processed: usize, total: usize, status: String)` back to Python via callback or return vector.
#[pyfunction]
#[pyo3(signature = (total_items, callback=None))]
pub fn test_batch_process<'py>(
    py: Python<'py>,
    total_items: usize,
    callback: Option<PyObject>,
) -> PyResult<Vec<(usize, usize, String)>> {
    let mut progress_records = Vec::with_capacity(total_items);

    py.allow_threads(|| {
        for i in 1..=total_items {
            let status = if i == total_items {
                "Completed".to_string()
            } else {
                format!("Processing item {}/{}", i, total_items)
            };

            progress_records.push((i, total_items, status.clone()));

            if let Some(ref cb) = callback {
                Python::with_gil(|py| -> PyResult<()> {
                    let tuple = PyTuple::new_bound(
                        py,
                        &[i.into_py(py), total_items.into_py(py), status.into_py(py)],
                    );
                    cb.call1(py, (tuple,))?;
                    Ok(())
                })?;
            }
        }
        Ok::<(), PyErr>(())
    })?;

    Ok(progress_records)
}

/// Scan a directory and flush metadata batches to a Python callback, respecting CancellationToken.
#[pyfunction]
#[pyo3(signature = (path, callback, batch_size, cancel_token=None))]
fn scan_directory<'py>(
    py: Python<'py>,
    path: &str,
    callback: PyObject,
    batch_size: usize,
    cancel_token: Option<CancellationToken>,
) -> PyResult<()> {
    let path_str = path.to_string();

    py.allow_threads(move || {
        let mut batch = Vec::new();

        for entry in WalkDir::new(&path_str).into_iter().filter_map(|e| e.ok()) {
            if let Some(token) = &cancel_token {
                if token.is_cancelled() {
                    if !batch.is_empty() {
                        Python::with_gil(|py| -> PyResult<()> {
                            flush_batch(py, &batch, &callback)?;
                            Ok(())
                        })?;
                        batch.clear();
                    }
                    return Ok::<(), PyErr>(());
                }
            }

            let path = entry.path();
            if path.is_file() {
                let tagged_file = match Probe::open(path) {
                    Ok(probe) => match probe.read() {
                        Ok(file) => file,
                        Err(_) => continue,
                    },
                    Err(_) => continue,
                };

                let properties = tagged_file.properties();
                let duration_ms = properties.duration().as_millis() as i32;
                let bitrate = properties.audio_bitrate().unwrap_or(0) * 1000;

                let tag = match tagged_file.primary_tag() {
                    Some(primary_tag) => Some(primary_tag),
                    None => tagged_file.first_tag(),
                };

                let mut title = None;
                let mut artist_name = None;
                let mut album_title = None;
                let mut track_number = 0;
                let mut disc_number = 1;
                let mut isrc = None;

                if let Some(t) = tag {
                    title = t.title().as_deref().map(|s| s.to_string());
                    artist_name = t.artist().as_deref().map(|s| s.to_string());
                    album_title = t.album().as_deref().map(|s| s.to_string());
                    track_number = t.track().unwrap_or(0);
                    disc_number = t.disk().unwrap_or(1);

                    if let Some(isrc_item) = t.get(&ItemKey::Isrc) {
                        isrc = isrc_item.value().text().map(|s| s.to_string());
                    }
                }

                let ext = path
                    .extension()
                    .map(|e| e.to_string_lossy().into_owned().to_lowercase())
                    .unwrap_or_else(|| "".to_string());

                let file_size_bytes = std::fs::metadata(path).map(|m| m.len()).unwrap_or(0);

                batch.push(TrackData {
                    title,
                    artist_name,
                    album_title,
                    duration_ms,
                    track_number,
                    disc_number,
                    isrc,
                    bitrate,
                    file_path: path.to_string_lossy().into_owned(),
                    file_format: ext,
                    file_size_bytes,
                });

                if batch.len() >= batch_size {
                    Python::with_gil(|py| -> PyResult<()> {
                        flush_batch(py, &batch, &callback)?;
                        Ok(())
                    })?;
                    batch.clear();
                }
            }
        }

        if !batch.is_empty() {
            Python::with_gil(|py| -> PyResult<()> {
                flush_batch(py, &batch, &callback)?;
                Ok(())
            })?;
            batch.clear();
        }

        Ok::<(), PyErr>(())
    })
}

/// PyO3 Module Registration for echosync_core
#[pymodule]
fn echosync_core<'py>(_py: Python<'py>, m: &Bound<'py, PyModule>) -> PyResult<()> {
    m.add_class::<CancellationToken>()?;
    m.add_function(wrap_pyfunction!(scan_directory, m)?)?;
    m.add_function(wrap_pyfunction!(test_batch_process, m)?)?;
    Ok(())
}
