use lofty::config::WriteOptions;
use lofty::file::{FileType, TaggedFileExt};
use lofty::probe::Probe;
use lofty::tag::{Accessor, ItemKey, Tag, TagExt, TagType};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::path::Path;

pub struct MetadataWriter;

impl MetadataWriter {
    pub fn write<P: AsRef<Path>>(path: P, tags: &Bound<'_, PyDict>) -> Result<(), String> {
        let p = path.as_ref();
        if !p.exists() {
            return Err(format!("File does not exist: {}", p.display()));
        }

        let mut tagged_file = Probe::open(p)
            .map_err(|e| format!("Failed to open audio probe for {}: {}", p.display(), e))?
            .read()
            .map_err(|e| format!("Failed to read audio metadata for {}: {}", p.display(), e))?;

        let tag_type = match tagged_file.file_type() {
            FileType::Wav | FileType::Mpeg | FileType::Aiff => TagType::Id3v2,
            FileType::Flac | FileType::Opus | FileType::Vorbis | FileType::Speex => TagType::VorbisComments,
            FileType::Mp4 => TagType::Mp4Ilst,
            _ => tagged_file.primary_tag_type(),
        };

        let tag = match tagged_file.tag_mut(tag_type) {
            Some(t) => t,
            None => {
                tagged_file.insert_tag(Tag::new(tag_type));
                tagged_file
                    .tag_mut(tag_type)
                    .ok_or_else(|| format!("Failed to initialize tag of type {:?} for {}", tag_type, p.display()))?
            }
        };

        // Extract and set title
        if let Ok(Some(val)) = tags.get_item("title") {
            if let Ok(s) = val.extract::<String>() {
                if !s.is_empty() {
                    tag.insert_text(ItemKey::TrackTitle, s);
                }
            }
        }

        // Extract and set artist / artist_name
        let artist_val = tags
            .get_item("artist")
            .ok()
            .flatten()
            .or_else(|| tags.get_item("artist_name").ok().flatten());
        if let Some(val) = artist_val {
            if let Ok(s) = val.extract::<String>() {
                if !s.is_empty() {
                    tag.insert_text(ItemKey::TrackArtist, s);
                }
            }
        }

        // Extract and set album / album_title
        let album_val = tags
            .get_item("album")
            .ok()
            .flatten()
            .or_else(|| tags.get_item("album_title").ok().flatten());
        if let Some(val) = album_val {
            if let Ok(s) = val.extract::<String>() {
                if !s.is_empty() {
                    tag.insert_text(ItemKey::AlbumTitle, s);
                }
            }
        }

        // Extract and set album_artist
        if let Ok(Some(val)) = tags.get_item("album_artist") {
            if let Ok(s) = val.extract::<String>() {
                if !s.is_empty() {
                    tag.insert_text(ItemKey::AlbumArtist, s);
                }
            }
        }

        // Extract and set track number
        let track_val = tags
            .get_item("track_number")
            .ok()
            .flatten()
            .or_else(|| tags.get_item("track_no").ok().flatten())
            .or_else(|| tags.get_item("track").ok().flatten());
        if let Some(val) = track_val {
            if let Ok(num) = val.extract::<u32>() {
                tag.set_track(num);
            } else if let Ok(s) = val.extract::<String>() {
                if let Ok(num) = s.parse::<u32>() {
                    tag.set_track(num);
                } else if !s.is_empty() {
                    tag.insert_text(ItemKey::TrackNumber, s);
                }
            }
        }

        // Extract and set disc number
        let disc_val = tags
            .get_item("disc_number")
            .ok()
            .flatten()
            .or_else(|| tags.get_item("disc_no").ok().flatten())
            .or_else(|| tags.get_item("disc").ok().flatten());
        if let Some(val) = disc_val {
            if let Ok(num) = val.extract::<u32>() {
                tag.set_disk(num);
            } else if let Ok(s) = val.extract::<String>() {
                if let Ok(num) = s.parse::<u32>() {
                    tag.set_disk(num);
                } else if !s.is_empty() {
                    tag.insert_text(ItemKey::DiscNumber, s);
                }
            }
        }

        // Extract and set year / date / recording date
        let year_val = tags
            .get_item("year")
            .ok()
            .flatten()
            .or_else(|| tags.get_item("release_year").ok().flatten())
            .or_else(|| tags.get_item("date").ok().flatten());
        if let Some(val) = year_val {
            if let Ok(num) = val.extract::<u32>() {
                tag.set_year(num);
            } else if let Ok(s) = val.extract::<String>() {
                if let Ok(num) = s.parse::<u32>() {
                    tag.set_year(num);
                } else if !s.is_empty() {
                    tag.insert_text(ItemKey::RecordingDate, s);
                }
            }
        }

        // Extract and set genre
        if let Ok(Some(val)) = tags.get_item("genre") {
            if let Ok(s) = val.extract::<String>() {
                if !s.is_empty() {
                    tag.set_genre(s);
                }
            }
        }

        // Extract and set ISRC
        if let Ok(Some(val)) = tags.get_item("isrc") {
            if let Ok(s) = val.extract::<String>() {
                if !s.is_empty() {
                    tag.insert_text(ItemKey::Isrc, s);
                }
            }
        }

        // Extract and set MusicBrainz recording / track ID
        let mbid_val = tags
            .get_item("musicbrainz_id")
            .ok()
            .flatten()
            .or_else(|| tags.get_item("mbid").ok().flatten())
            .or_else(|| tags.get_item("musicbrainz_trackid").ok().flatten());
        if let Some(val) = mbid_val {
            if let Ok(s) = val.extract::<String>() {
                if !s.is_empty() {
                    tag.insert_text(ItemKey::MusicBrainzTrackId, s);
                }
            }
        }

        // Extract and set MusicBrainz release ID
        if let Ok(Some(val)) = tags.get_item("mb_release_id") {
            if let Ok(s) = val.extract::<String>() {
                if !s.is_empty() {
                    tag.insert_text(ItemKey::MusicBrainzReleaseId, s);
                }
            }
        }

        // Save tags directly to path using lofty
        tag.save_to_path(p, WriteOptions::default())
            .map_err(|e| format!("Failed to save tags to {}: {}", p.display(), e))?;

        Ok(())
    }
}
