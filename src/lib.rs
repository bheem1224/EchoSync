use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Scan a directory and return metadata as a list of raw Python dictionaries.
///
/// This provides zero-overhead ingestion into SQLAlchemy core bulk inserts.
#[pyfunction]
fn scan_directory(py: Python, path: &str) -> PyResult<Vec<PyObject>> {
    let mut results = Vec::new();

    // TODO: Implement actual high-speed Rust directory walking and tag parsing
    // For now, this is a stub simulating a single parsed file.
    let dict = PyDict::new(py);
    dict.set_item("title", "Stub Title")?;
    dict.set_item("artist_name", "Stub Artist")?;
    dict.set_item("album_title", "Stub Album")?;
    dict.set_item("duration", 200.0)?;
    dict.set_item("track_number", 1)?;
    dict.set_item("disc_number", 1)?;
    dict.set_item("bitrate", 320)?;
    dict.set_item("file_path", format!("{}/stub.mp3", path))?;
    dict.set_item("file_format", "mp3")?;
    dict.set_item("file_size_bytes", 5000000)?;

    results.push(dict.into());

    Ok(results)
}

/// A Python module implemented in Rust.
#[pymodule]
fn echosync_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(scan_directory, m)?)?;
    Ok(())
}
