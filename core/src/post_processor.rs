use pyo3::prelude::*;
use lofty::prelude::*;
use lofty::probe::Probe;
use lofty::tag::{Tag, Accessor, ItemKey};
use lofty::file::AudioFile;
use lofty::config::WriteOptions;
use std::path::{Path, PathBuf};
use std::fs;
use crate::structs::SoulSyncTrack;

#[pyclass]
pub struct PostProcessor {}

impl PostProcessor {
    pub fn new_rust() -> Self {
        PostProcessor {}
    }

    pub fn read_tags_rust(&self, path: &str) -> Option<SoulSyncTrack> {
        let path_buf = PathBuf::from(path);

        let tagged_file = match Probe::open(&path_buf) {
            Ok(p) => match p.read() {
                Ok(tf) => tf,
                Err(_) => return None,
            },
            Err(_) => return None,
        };

        let tag = match tagged_file.primary_tag() {
            Some(t) => t,
            None => match tagged_file.first_tag() {
                Some(t) => t,
                None => return None,
            },
        };

        let title = tag.title().unwrap_or(std::borrow::Cow::Borrowed("")).to_string();
        let artist = tag.artist().unwrap_or(std::borrow::Cow::Borrowed("")).to_string();
        let album = tag.album().unwrap_or(std::borrow::Cow::Borrowed("")).to_string();

        if title.is_empty() {
             return None;
        }

        let raw_title = title;
        let artist_name = if artist.is_empty() { "Unknown Artist".to_string() } else { artist };
        let album_title = if album.is_empty() { "Unknown Album".to_string() } else { album };

        // Use new_rust instead of new
        let mut track = SoulSyncTrack::new_rust(
             raw_title,
             artist_name,
             album_title
        );

        if let Some(y) = tag.year() {
            track.release_year = Some(y as i32);
        }
        if let Some(t) = tag.track() {
            track.track_number = Some(t as i32);
        }
        if let Some(d) = tag.disk() {
            track.disc_number = Some(d as i32);
        }

        let properties = tagged_file.properties();
        track.duration = Some(properties.duration().as_millis() as i64);
        track.bitrate = Some(properties.audio_bitrate().unwrap_or(0) as i32);
        track.sample_rate = Some(properties.sample_rate().unwrap_or(0) as i32);
        track.bit_depth = properties.bit_depth().map(|b| b as i32);

        if let Ok(meta) = fs::metadata(&path_buf) {
            track.file_size_bytes = Some(meta.len() as i64);
        }

        track.file_path = Some(path.to_string());

        Some(track)
    }
}

#[pymethods]
impl PostProcessor {
    #[new]
    pub fn new() -> Self {
        Self::new_rust()
    }

    /// Reads metadata tags from a file and returns a SoulSyncTrack.
    /// Returns None if the file cannot be read or has no minimal metadata.
    pub fn read_tags(&self, path: String) -> PyResult<Option<SoulSyncTrack>> {
        Ok(self.read_tags_rust(&path))
    }

    /// Writes metadata tags to the file at `path` using the data from `track`.
    fn write_tags(&self, path: String, track: SoulSyncTrack) -> PyResult<()> {
        let path_buf = PathBuf::from(&path);

        let mut tagged_file = match Probe::open(&path_buf) {
            Ok(p) => match p.read() {
                Ok(tf) => tf,
                Err(e) => return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to read file: {}", e))),
            },
            Err(e) => return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to open file: {}", e))),
        };

        // We use the primary tag or create a new one.
        // For broad compatibility, we might want to ensure specific tag types (ID3v2 for MP3, Vorbis for FLAC).
        // Lofty handles this mostly automatically if we use the generic `Tag`.

        let tag = match tagged_file.primary_tag_mut() {
            Some(t) => t,
            None => {
                 // If no tag exists, we need to create one appropriate for the file type.
                 // This is slightly complex in Lofty generic API without knowing the type explicitly.
                 // But `tagged_file.insert_tag(Tag::new(tagged_file.file_type().primary_tag_type()))` works usually.
                 let tag_type = tagged_file.file_type().primary_tag_type();
                 tagged_file.insert_tag(Tag::new(tag_type));
                 tagged_file.primary_tag_mut().unwrap()
            }
        };

        // Set fields
        tag.set_title(track.title);
        tag.set_artist(track.artist_name);
        tag.set_album(track.album_title);

        if let Some(y) = track.release_year {
            tag.set_year(y as u32);
        }

        if let Some(n) = track.track_number {
            tag.set_track(n as u32);
        }

        if let Some(d) = track.disc_number {
            tag.set_disk(d as u32);
        }

        // Save
        if let Err(e) = tag.save_to_path(&path_buf, WriteOptions::new()) {
             return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to save tags: {}", e)));
        }

        Ok(())
    }

    /// Moves a file from src to dst, creating parent directories if needed.
    fn move_file(&self, src: String, dst: String) -> PyResult<()> {
        let src_path = PathBuf::from(&src);
        let dst_path = PathBuf::from(&dst);

        if !src_path.exists() {
            return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(format!("Source file not found: {}", src)));
        }

        if let Some(parent) = dst_path.parent() {
            if let Err(e) = fs::create_dir_all(parent) {
                return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to create directories: {}", e)));
            }
        }

        if let Err(e) = fs::rename(&src_path, &dst_path) {
            // Fallback to copy + delete if rename fails (e.g. cross-device)
            if let Err(copy_e) = fs::copy(&src_path, &dst_path) {
                 return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to move file (rename: {}, copy: {})", e, copy_e)));
            }
            let _ = fs::remove_file(src_path);
        }

        Ok(())
    }
}
