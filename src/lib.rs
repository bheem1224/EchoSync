pub mod audio;
pub mod database;
pub mod errors;
pub mod file_handling;
pub mod metadata;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};
use rayon::prelude::*;
use rusqlite::{Connection, Result as SqlResult};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::{channel, Receiver, RecvTimeoutError, Sender};
use std::sync::Arc;
use std::time::{Duration, Instant};
use walkdir::WalkDir;

pub use errors::EchoSyncError;
pub use file_handling::fs_ops::FsOperations;
pub use file_handling::scanner::ProgressMsg;
pub use metadata::{MetadataExtractor, MetadataWriter, TrackMetadata};

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

fn track_metadata_to_pydict<'py>(
    py: Python<'py>,
    meta: &TrackMetadata,
) -> PyResult<Bound<'py, PyDict>> {
    let dict = PyDict::new_bound(py);
    dict.set_item("title", &meta.title)?;
    dict.set_item("artist_name", &meta.artist)?;
    dict.set_item("artist", &meta.artist)?;
    dict.set_item("album_artist", &meta.album_artist)?;
    dict.set_item("album_title", &meta.album)?;
    dict.set_item("album", &meta.album)?;
    dict.set_item("track_number", meta.track_no)?;
    dict.set_item("track_no", meta.track_no)?;
    dict.set_item("disc_number", meta.disc_no)?;
    dict.set_item("disc_no", meta.disc_no)?;
    dict.set_item("year", meta.year)?;
    dict.set_item("genre", &meta.genre)?;
    dict.set_item("mbid", &meta.mbid)?;
    dict.set_item("version", &meta.version)?;
    dict.set_item("isrc", &meta.isrc)?;
    dict.set_item("musicbrainz_track_id", &meta.musicbrainz_track_id)?;
    dict.set_item("musicbrainz_album_id", &meta.musicbrainz_album_id)?;
    dict.set_item("echosync_track_uuid", &meta.echosync_track_uuid)?;
    dict.set_item("echosync_media_uuid", &meta.echosync_media_uuid)?;
    dict.set_item("codec", &meta.codec)?;
    dict.set_item("bit_depth", meta.bit_depth)?;
    dict.set_item("sample_rate", meta.sample_rate)?;
    dict.set_item("channels", meta.channels)?;
    dict.set_item("bitrate", meta.bitrate)?;
    dict.set_item("duration_ms", meta.duration_ms)?;
    dict.set_item("file_path", &meta.file_path)?;
    dict.set_item("file_size_bytes", meta.file_size_bytes)?;
    dict.set_item("mtime", meta.mtime)?;
    dict.set_item("inode", meta.inode)?;
    Ok(dict)
}

/// Extract audiophile metadata and stream properties using lofty.
#[pyfunction]
pub fn extract_metadata<'py>(py: Python<'py>, path: String) -> PyResult<PyObject> {
    let extract_result = py.allow_threads(|| MetadataExtractor::extract(&path));
    match extract_result {
        Ok(meta) => {
            let dict = track_metadata_to_pydict(py, &meta)?;
            Ok(dict.into_py(py))
        }
        Err(err) => Err(pyo3::exceptions::PyValueError::new_err(err)),
    }
}

/// Read audio metadata tags directly (alias to extract_metadata).
#[pyfunction]
pub fn read_metadata<'py>(py: Python<'py>, path: String) -> PyResult<PyObject> {
    extract_metadata(py, path)
}

/// Write audio metadata tags directly to audio files using lofty with GIL release during I/O.
#[pyfunction]
pub fn write_metadata(py: Python<'_>, path: String, tags: &Bound<'_, PyDict>) -> PyResult<bool> {
    let mut tag_map = std::collections::HashMap::new();
    for (k, v) in tags.iter() {
        if let (Ok(key), Ok(val)) = (k.extract::<String>(), v.extract::<String>()) {
            tag_map.insert(key.to_lowercase(), val);
        }
    }
    py.allow_threads(|| MetadataWriter::write_map(&path, &tag_map))
        .map(|_| true)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e))
}

/// Atomic file move with EXDEV cross-device link fallback.
#[pyfunction]
pub fn safe_move_file(py: Python<'_>, src: String, dst: String) -> PyResult<()> {
    py.allow_threads(|| FsOperations::safe_move(&src, &dst))
        .map_err(|e| e.into())
}

/// High-speed copy file.
#[pyfunction]
pub fn copy_file(py: Python<'_>, src: String, dst: String) -> PyResult<u64> {
    py.allow_threads(|| FsOperations::copy_file(&src, &dst))
        .map_err(|e| e.into())
}

/// Delete file safely.
#[pyfunction]
pub fn delete_file(py: Python<'_>, path: String) -> PyResult<()> {
    py.allow_threads(|| FsOperations::delete_file(&path))
        .map_err(|e| e.into())
}

/// Telemetry Yielding Pattern (Event Bus Prep)
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

/// Parallel directory scanning & telemetry channel using Rayon and std::sync::mpsc.
#[pyfunction]
#[pyo3(signature = (path, callback=None, batch_interval_ms=50))]
pub fn batch_process_directory<'py>(
    py: Python<'py>,
    path: String,
    callback: Option<PyObject>,
    batch_interval_ms: u64,
) -> PyResult<()> {
    let path_buf = std::path::PathBuf::from(&path);
    if !path_buf.exists() {
        return Err(pyo3::exceptions::PyFileNotFoundError::new_err(format!(
            "Path does not exist: {}",
            path
        )));
    }

    let entries: Vec<_> = WalkDir::new(&path_buf)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().is_file())
        .collect();

    let total = entries.len();
    if total == 0 {
        if let Some(ref cb) = callback {
            Python::with_gil(|py| -> PyResult<()> {
                let py_list = PyList::empty_bound(py);
                cb.call1(py, (py_list,))?;
                Ok(())
            })?;
        }
        return Ok(());
    }

    let (tx, rx): (Sender<ProgressMsg>, Receiver<ProgressMsg>) = channel();

    let tx_worker = tx.clone();
    let worker_handle = std::thread::spawn(move || {
        use std::sync::atomic::{AtomicUsize, Ordering};
        let counter = AtomicUsize::new(0);

        entries.par_iter().for_each(|entry| {
            let curr = counter.fetch_add(1, Ordering::SeqCst) + 1;
            let file_name = entry
                .path()
                .file_name()
                .map(|n| n.to_string_lossy().to_string())
                .unwrap_or_else(|| "unknown".to_string());

            let status = if curr == total {
                "Completed".to_string()
            } else {
                format!("Processing {}", file_name)
            };

            let _ = tx_worker.send(ProgressMsg {
                processed: curr,
                total,
                status,
            });
        });
    });

    drop(tx);

    py.allow_threads(move || {
        let mut buffer = Vec::new();
        let interval = Duration::from_millis(batch_interval_ms);
        let mut last_flush = Instant::now();

        loop {
            match rx.recv_timeout(Duration::from_millis(10)) {
                Ok(msg) => {
                    buffer.push(msg);
                    while let Ok(pending_msg) = rx.try_recv() {
                        buffer.push(pending_msg);
                    }
                }
                Err(RecvTimeoutError::Timeout) => {}
                Err(RecvTimeoutError::Disconnected) => {
                    while let Ok(remaining_msg) = rx.try_recv() {
                        buffer.push(remaining_msg);
                    }
                    break;
                }
            }

            if (last_flush.elapsed() >= interval || !buffer.is_empty()) && !buffer.is_empty() {
                Python::with_gil(|py| -> PyResult<()> {
                    if let Some(ref cb) = &callback {
                        let mut py_items = Vec::with_capacity(buffer.len());
                        for item in &buffer {
                            let tuple = PyTuple::new_bound(
                                py,
                                &[
                                    item.processed.into_py(py),
                                    item.total.into_py(py),
                                    item.status.clone().into_py(py),
                                ],
                            );
                            py_items.push(tuple);
                        }
                        let py_list = PyList::new_bound(py, py_items);
                        cb.call1(py, (py_list,))?;
                    }
                    Ok(())
                })?;
                buffer.clear();
                last_flush = Instant::now();
            }
        }

        if !buffer.is_empty() {
            Python::with_gil(|py| -> PyResult<()> {
                if let Some(ref cb) = &callback {
                    let mut py_items = Vec::with_capacity(buffer.len());
                    for item in &buffer {
                        let tuple = PyTuple::new_bound(
                            py,
                            &[
                                item.processed.into_py(py),
                                item.total.into_py(py),
                                item.status.clone().into_py(py),
                            ],
                        );
                        py_items.push(tuple);
                    }
                    let py_list = PyList::new_bound(py, py_items);
                    cb.call1(py, (py_list,))?;
                }
                Ok(())
            })?;
        }

        let _ = worker_handle.join();
        Ok::<(), PyErr>(())
    })?;

    Ok(())
}

/// Scan a directory and flush metadata batches to a Python callback.
#[pyfunction]
#[pyo3(signature = (path, callback, batch_size, cancel_token=None))]
fn scan_directory<'py>(
    py: Python<'py>,
    path: String,
    callback: PyObject,
    batch_size: usize,
    cancel_token: Option<CancellationToken>,
) -> PyResult<()> {
    use pyo3::exceptions::PyRuntimeError;
    use std::panic::{catch_unwind, AssertUnwindSafe};

    let safe_batch_size = std::cmp::max(1, batch_size);
    let path_str = path.to_string();

    let result = catch_unwind(AssertUnwindSafe(|| {
        py.allow_threads(move || -> PyResult<()> {
            let mut batch = Vec::new();

            for entry in WalkDir::new(&path_str).into_iter().filter_map(|e| e.ok()) {
                if let Some(token) = &cancel_token {
                    if token.is_cancelled() {
                        if !batch.is_empty() {
                            Python::with_gil(|py| -> PyResult<()> {
                                let mut py_list_elements = Vec::with_capacity(batch.len());
                                for data in &batch {
                                    let dict = track_metadata_to_pydict(py, data)?;
                                    py_list_elements.push(dict);
                                }
                                let py_list = PyList::new_bound(py, py_list_elements);
                                callback.call1(py, (py_list,))?;
                                Ok(())
                            })?;
                            batch.clear();
                        }
                        return Ok(());
                    }
                }

                let path = entry.path();
                if path.is_file() {
                    if let Ok(meta) = MetadataExtractor::extract(path.to_str().unwrap_or("")) {
                        batch.push(meta);

                        if batch.len() >= safe_batch_size {
                            Python::with_gil(|py| -> PyResult<()> {
                                let mut py_list_elements = Vec::with_capacity(batch.len());
                                for data in &batch {
                                    let dict = track_metadata_to_pydict(py, data)?;
                                    py_list_elements.push(dict);
                                }
                                let py_list = PyList::new_bound(py, py_list_elements);
                                callback.call1(py, (py_list,))?;
                                Ok(())
                            })?;
                            batch.clear();
                        }
                    }
                }
            }

            if !batch.is_empty() {
                Python::with_gil(|py| -> PyResult<()> {
                    let mut py_list_elements = Vec::with_capacity(batch.len());
                    for data in &batch {
                        let dict = track_metadata_to_pydict(py, data)?;
                        py_list_elements.push(dict);
                    }
                    let py_list = PyList::new_bound(py, py_list_elements);
                    callback.call1(py, (py_list,))?;
                    Ok(())
                })?;
                batch.clear();
            }

            Ok::<(), PyErr>(())
        })
    }));

    match result {
        Ok(py_res) => py_res,
        Err(_) => Err(PyRuntimeError::new_err(
            "Rust FFI panic intercepted during scan_directory",
        )),
    }
}

/// Generate Chromaprint fingerprint and duration from audio file with silence trimming.
#[pyfunction]
#[pyo3(signature = (path, trim_silence=true))]
pub fn fingerprint_audio<'py>(
    py: Python<'py>,
    path: String,
    trim_silence: bool,
) -> PyResult<(String, f64)> {
    let result = py.allow_threads(|| audio::fingerprint::generate_fingerprint(&path, trim_silence));
    match result {
        Ok((fp, dur)) => Ok((fp, dur)),
        Err(err) => Err(pyo3::exceptions::PyRuntimeError::new_err(err)),
    }
}

/// PyO3 Module Registration for echosync_core
#[pymodule]
fn echosync_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CancellationToken>()?;
    m.add_function(wrap_pyfunction!(scan_directory, m)?)?;
    m.add_function(wrap_pyfunction!(test_batch_process, m)?)?;
    m.add_function(wrap_pyfunction!(batch_process_directory, m)?)?;
    m.add_function(wrap_pyfunction!(extract_metadata, m)?)?;
    m.add_function(wrap_pyfunction!(read_metadata, m)?)?;
    m.add_function(wrap_pyfunction!(write_metadata, m)?)?;
    m.add_function(wrap_pyfunction!(safe_move_file, m)?)?;
    m.add_function(wrap_pyfunction!(copy_file, m)?)?;
    m.add_function(wrap_pyfunction!(delete_file, m)?)?;
    m.add_function(wrap_pyfunction!(fingerprint_audio, m)?)?;
    Ok(())
}
