use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use chrono::NaiveDate;
use crate::parser::TrackParser;

#[pyclass]
#[derive(Clone, Debug)]
pub struct SoulSyncTrack {
    // Required Fields
    #[pyo3(get, set)]
    pub raw_title: String,
    #[pyo3(get, set)]
    pub artist_name: String,
    #[pyo3(get, set)]
    pub album_title: String,

    // Core Fields (Auto-Populated)
    #[pyo3(get, set)]
    pub title: String,
    #[pyo3(get, set)]
    pub edition: Option<String>,
    #[pyo3(get, set)]
    pub sort_title: Option<String>,
    #[pyo3(get, set)]
    pub display_title: String,

    // Artist/Album Metadata
    #[pyo3(get, set)]
    pub artist_sort_name: Option<String>,
    #[pyo3(get, set)]
    pub album_sort_title: Option<String>,
    #[pyo3(get, set)]
    pub album_type: Option<String>,
    #[pyo3(get, set)]
    pub album_release_group_id: Option<String>,

    // Track Metadata
    #[pyo3(get, set)]
    pub duration: Option<i64>, // Milliseconds
    #[pyo3(get, set)]
    pub track_number: Option<i32>,
    #[pyo3(get, set)]
    pub disc_number: Option<i32>,
    #[pyo3(get, set)]
    pub bitrate: Option<i32>,
    #[pyo3(get, set)]
    pub file_path: Option<String>,
    #[pyo3(get, set)]
    pub file_format: Option<String>,
    #[pyo3(get, set)]
    pub release_year: Option<i32>,
    #[pyo3(get, set)]
    pub added_at: Option<chrono::NaiveDateTime>,

    // Technical Metadata
    #[pyo3(get, set)]
    pub sample_rate: Option<i32>,
    #[pyo3(get, set)]
    pub bit_depth: Option<i32>,
    #[pyo3(get, set)]
    pub file_size_bytes: Option<i64>,

    // Identifiers
    #[pyo3(get, set)]
    pub musicbrainz_id: Option<String>,
    #[pyo3(get, set)]
    pub isrc: Option<String>,

    // New Identifiers
    #[pyo3(get, set)]
    pub acoustid_id: Option<String>,
    #[pyo3(get, set)]
    pub mb_release_id: Option<String>,
    #[pyo3(get, set)]
    pub original_release_date: Option<NaiveDate>,

    // Audio fingerprint
    #[pyo3(get, set)]
    pub fingerprint: Option<String>,

    // Quality tags
    #[pyo3(get, set)]
    pub quality_tags: Option<Vec<String>>,

    // External Provider Links
    #[pyo3(get, set)]
    pub identifiers: HashMap<String, String>, // Flattened to String: String
}

#[pymethods]
impl SoulSyncTrack {
    #[new]
    #[pyo3(signature = (
        raw_title,
        artist_name,
        album_title,
        identifiers=None,
        **kwargs
    ))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        raw_title: String,
        artist_name: String,
        album_title: String,
        identifiers: Option<&Bound<'_, PyAny>>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Self> {
        // 0. Handle identifiers normalization
        let mut final_identifiers: HashMap<String, String> = HashMap::new();

        if let Some(ids) = identifiers {
            if let Ok(list) = ids.downcast::<PyList>() {
                // Handle legacy List[Dict]
                for item in list {
                    if let Ok(dict) = item.downcast::<PyDict>() {
                        let key: Option<String> = dict.get_item("provider_source")?.and_then(|v| v.extract().ok());
                        let val_obj = dict.get_item("provider_item_id")?;

                        let val: Option<String> = if let Some(v) = val_obj {
                             Some(v.to_string())
                        } else if let Some(v) = dict.get_item("id")? {
                             Some(v.to_string())
                        } else {
                             None
                        };

                        if let Some(k) = key {
                            if let Some(v) = val {
                                final_identifiers.insert(k, v);
                            }
                        }
                    }
                }
            } else if let Ok(dict) = ids.downcast::<PyDict>() {
                // Handle Dict[str, Any]
                for (k, v) in dict {
                    let key: String = k.extract()?;
                    let val: String = v.to_string(); // Convert value to string (e.g. int IDs)
                    final_identifiers.insert(key, val);
                }
            }
        }

        // Use TrackParser to clean and normalize initial data
        let parsed_metadata = TrackParser::clean_metadata(&raw_title, &artist_name, &album_title);

        // Initialize instance
        let mut track = SoulSyncTrack {
            raw_title: raw_title.clone(),
            artist_name: parsed_metadata.artist,
            album_title: parsed_metadata.album.unwrap_or(album_title.to_string()),
            title: parsed_metadata.title,
            edition: parsed_metadata.edition,
            sort_title: None,
            display_title: raw_title.clone(),
            artist_sort_name: None,
            album_sort_title: None,
            album_type: None,
            album_release_group_id: None,
            duration: None,
            track_number: None,
            disc_number: None,
            bitrate: None,
            file_path: None,
            file_format: None,
            release_year: None,
            added_at: None,
            sample_rate: None,
            bit_depth: None,
            file_size_bytes: None,
            musicbrainz_id: None,
            isrc: None,
            acoustid_id: None,
            mb_release_id: None,
            original_release_date: None,
            fingerprint: None,
            quality_tags: Some(parsed_metadata.quality_tags),
            identifiers: final_identifiers,
        };

        // Populate optional fields from kwargs
        if let Some(kw) = kwargs {
             macro_rules! extract_opt {
                ($field:ident, $type:ty) => {
                    if let Some(val) = kw.get_item(stringify!($field))? {
                         if !val.is_none() {
                             if let Ok(v) = val.extract::<$type>() {
                                 track.$field = Some(v);
                             }
                         }
                    }
                };
            }
            macro_rules! extract_date_opt {
                ($field:ident) => {
                    if let Some(val) = kw.get_item(stringify!($field))? {
                         if !val.is_none() {
                             // Handle Python date objects or strings
                             if let Ok(d) = val.extract::<NaiveDate>() {
                                 track.$field = Some(d);
                             } else if let Ok(s) = val.extract::<String>() {
                                 if let Ok(d) = NaiveDate::parse_from_str(&s, "%Y-%m-%d") {
                                      track.$field = Some(d);
                                 }
                             }
                         }
                    }
                };
            }
             macro_rules! extract_datetime_opt {
                ($field:ident) => {
                    if let Some(val) = kw.get_item(stringify!($field))? {
                         if !val.is_none() {
                            // Try extracting datetime, or string and parse
                             if let Ok(d) = val.extract::<chrono::NaiveDateTime>() {
                                 track.$field = Some(d);
                             } else if let Ok(s) = val.extract::<String>() {
                                 // Try ISO format
                                 if let Ok(d) = chrono::NaiveDateTime::parse_from_str(&s, "%Y-%m-%dT%H:%M:%S%.f") {
                                     track.$field = Some(d);
                                 } else if let Ok(d) = chrono::NaiveDateTime::parse_from_str(&s, "%Y-%m-%dT%H:%M:%S") {
                                     track.$field = Some(d);
                                 }
                             }
                         }
                    }
                };
            }

            // Note: If edition is passed in kwargs, it might override extracted edition.
            // We'll let kwargs override.
            extract_opt!(edition, String);

            extract_opt!(sort_title, String);
            extract_opt!(artist_sort_name, String);
            extract_opt!(album_sort_title, String);
            extract_opt!(album_type, String);
            extract_opt!(album_release_group_id, String);
            extract_opt!(duration, i64);
            extract_opt!(track_number, i32);
            extract_opt!(disc_number, i32);
            extract_opt!(bitrate, i32);
            extract_opt!(file_path, String);
            extract_opt!(file_format, String);
            extract_opt!(release_year, i32);
            extract_opt!(sample_rate, i32);
            extract_opt!(bit_depth, i32);
            extract_opt!(file_size_bytes, i64);
            extract_opt!(musicbrainz_id, String);
            extract_opt!(isrc, String);
            extract_opt!(acoustid_id, String);
            extract_opt!(mb_release_id, String);
            extract_opt!(fingerprint, String);

            // Append quality tags if provided in kwargs
            if let Some(val) = kw.get_item("quality_tags")? {
                 if !val.is_none() {
                     if let Ok(mut v) = val.extract::<Vec<String>>() {
                         if let Some(ref mut existing) = track.quality_tags {
                             existing.append(&mut v);
                         } else {
                             track.quality_tags = Some(v);
                         }
                     }
                 }
            }

            extract_date_opt!(original_release_date);
            extract_datetime_opt!(added_at);
        }

        // 1.5 Sync Top-Level fields
        // mb_release_id
        if let Some(ref mid) = track.mb_release_id {
            track.identifiers.insert("musicbrainz_release_id".to_string(), mid.clone());
        } else if let Some(mid) = track.identifiers.get("musicbrainz_release_id") {
            track.mb_release_id = Some(mid.clone());
        }

        // acoustid_id
        if let Some(ref aid) = track.acoustid_id {
            track.identifiers.insert("acoustid_id".to_string(), aid.clone());
        } else if let Some(aid) = track.identifiers.get("acoustid_id") {
            track.acoustid_id = Some(aid.clone());
        }

        // 4. Sort Title Generation (if not provided)
        if track.sort_title.is_none() {
            let lower = track.title.to_lowercase();
            if lower.starts_with("the ") {
                 track.sort_title = Some(format!("{}, The", &track.title[4..]));
            } else if lower.starts_with("a ") {
                 track.sort_title = Some(format!("{}, A", &track.title[2..]));
            } else if lower.starts_with("an ") {
                 track.sort_title = Some(format!("{}, An", &track.title[3..]));
            } else {
                 track.sort_title = Some(track.title.clone());
            }
        }

        Ok(track)
    }

    // Helper for Python compatibility (to_dict)
    fn to_dict(&self, py: Python<'_>) -> PyResult<HashMap<String, PyObject>> {
        let mut dict = HashMap::new();

        macro_rules! insert {
            ($key:expr, $val:expr) => {
                if let Ok(obj) = $val.clone().into_pyobject(py) {
                     dict.insert($key.to_string(), obj.into_any().unbind());
                }
            };
        }

        macro_rules! insert_opt {
             ($key:expr, $val:expr) => {
                 if let Some(v) = &$val {
                     if let Ok(obj) = v.clone().into_pyobject(py) {
                         dict.insert($key.to_string(), obj.into_any().unbind());
                     } else {
                         dict.insert($key.to_string(), py.None());
                     }
                 } else {
                     dict.insert($key.to_string(), py.None());
                 }
             };
        }

        insert!("title", self.title);
        insert!("raw_title", self.raw_title);
        insert!("display_title", self.display_title);
        insert!("artist_name", self.artist_name);
        insert!("album_title", self.album_title);

        insert_opt!("edition", self.edition);
        insert_opt!("sort_title", self.sort_title);
        insert_opt!("artist_sort_name", self.artist_sort_name);
        insert_opt!("album_sort_title", self.album_sort_title);
        insert_opt!("album_type", self.album_type);
        insert_opt!("album_release_group_id", self.album_release_group_id);

        insert_opt!("duration", self.duration);
        insert_opt!("track_number", self.track_number);
        insert_opt!("disc_number", self.disc_number);
        insert_opt!("bitrate", self.bitrate);
        insert_opt!("file_path", self.file_path);
        insert_opt!("file_format", self.file_format);
        insert_opt!("release_year", self.release_year);
        insert_opt!("added_at", self.added_at);
        insert_opt!("sample_rate", self.sample_rate);
        insert_opt!("bit_depth", self.bit_depth);
        insert_opt!("file_size_bytes", self.file_size_bytes);
        insert_opt!("musicbrainz_id", self.musicbrainz_id);
        insert_opt!("isrc", self.isrc);
        insert_opt!("acoustid_id", self.acoustid_id);
        insert_opt!("mb_release_id", self.mb_release_id);
        insert_opt!("original_release_date", self.original_release_date);
        insert_opt!("fingerprint", self.fingerprint);
        insert_opt!("quality_tags", self.quality_tags);

        // Manual HashMap handling
        let ids_dict = PyDict::new(py);
        for (k, v) in &self.identifiers {
            ids_dict.set_item(k, v)?;
        }
        dict.insert("identifiers".to_string(), ids_dict.into());

        Ok(dict)
    }
}
