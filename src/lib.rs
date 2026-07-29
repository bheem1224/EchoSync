use pyo3::prelude::*;
use pyo3::types::PyDict;
use walkdir::WalkDir;
use lofty::probe::Probe;
use lofty::file::AudioFile;
use lofty::tag::{Accessor, TagExt, ItemKey};

/// Scan a directory and return metadata as a list of raw Python dictionaries.
#[pyfunction]
fn scan_directory<'py>(py: Python<'py>, path: &str) -> PyResult<Vec<Bound<'py, PyDict>>> {
    let mut results = Vec::new();

    for entry in WalkDir::new(path).into_iter().filter_map(|e| e.ok()) {
        let path = entry.path();
        if path.is_file() {
            // Attempt to parse audio file
            let tagged_file = match Probe::open(path) {
                Ok(probe) => match probe.read() {
                    Ok(file) => file,
                    Err(_) => continue, // Skip files we cannot read properly
                },
                Err(_) => continue, // Skip files that aren't recognized audio formats
            };

            let properties = tagged_file.properties();
            let duration_ms = properties.duration().as_millis() as i32;
            let bitrate = properties.audio_bitrate().unwrap_or(0) * 1000;

            // Extract tags
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
                title = t.title().map(|s| s.into_owned());
                artist_name = t.artist().map(|s| s.into_owned());
                album_title = t.album().map(|s| s.into_owned());
                track_number = t.track().unwrap_or(0);
                disc_number = t.disk().unwrap_or(1);

                // Get ISRC from items
                if let Some(isrc_item) = t.get(&ItemKey::Isrc) {
                    isrc = isrc_item.value().text().map(|s| s.to_string());
                }
            }

            // Construct dictionary matching EchoSync track kwargs exactly
            let dict = PyDict::new_bound(py);
            dict.set_item("title", title)?;
            dict.set_item("artist_name", artist_name)?;
            dict.set_item("album_title", album_title)?;
            dict.set_item("duration_ms", duration_ms)?;
            dict.set_item("track_number", track_number)?;
            dict.set_item("disc_number", disc_number)?;
            dict.set_item("isrc", isrc)?;
            dict.set_item("bitrate", bitrate)?;
            dict.set_item("file_path", path.to_string_lossy().into_owned())?;

            let ext = path.extension()
                .map(|e| e.to_string_lossy().into_owned().to_lowercase())
                .unwrap_or_else(|| "".to_string());
            dict.set_item("file_format", ext)?;

            let file_size_bytes = std::fs::metadata(path)
                .map(|m| m.len())
                .unwrap_or(0);
            dict.set_item("file_size_bytes", file_size_bytes)?;

            results.push(dict);
        }
    }

    Ok(results)
}

/// A Python module implemented in Rust.
#[pymodule]
fn echosync_core<'py>(_py: Python<'py>, m: &Bound<'py, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(scan_directory, m)?)?;
    Ok(())
}
