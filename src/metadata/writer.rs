use lofty::config::{ParseOptions, ParsingMode, WriteOptions};
use lofty::file::{AudioFile, FileType, TaggedFileExt};
use lofty::probe::Probe;
use lofty::tag::{Accessor, ItemKey, Tag, TagType};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::path::Path;

pub struct MetadataWriter;

fn populate_tag_items(tag: &mut Tag, tags: &Bound<'_, PyDict>) {
    // Extract and set title
    if let Ok(Some(val)) = tags.get_item("title") {
        if let Ok(s) = val.extract::<String>() {
            let st = s.trim();
            if !st.is_empty() {
                tag.insert_text(ItemKey::TrackTitle, st.to_string());
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
            let st = s.trim();
            if !st.is_empty() {
                tag.insert_text(ItemKey::TrackArtist, st.to_string());
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
            let st = s.trim();
            if !st.is_empty() {
                tag.insert_text(ItemKey::AlbumTitle, st.to_string());
            }
        }
    }

    // Extract and set album_artist
    if let Ok(Some(val)) = tags.get_item("album_artist") {
        if let Ok(s) = val.extract::<String>() {
            let st = s.trim();
            if !st.is_empty() {
                tag.insert_text(ItemKey::AlbumArtist, st.to_string());
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
            let st = s.trim();
            if !st.is_empty() {
                tag.set_genre(st.to_string());
            }
        }
    }

    // Extract and set ISRC
    if let Ok(Some(val)) = tags.get_item("isrc") {
        if let Ok(s) = val.extract::<String>() {
            let st = s.trim();
            if !st.is_empty() {
                tag.insert_text(ItemKey::Isrc, st.to_string());
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
            let st = s.trim();
            if !st.is_empty() {
                tag.insert_text(ItemKey::MusicBrainzTrackId, st.to_string());
            }
        }
    }

    // Extract and set MusicBrainz release ID
    if let Ok(Some(val)) = tags.get_item("mb_release_id") {
        if let Ok(s) = val.extract::<String>() {
            let st = s.trim();
            if !st.is_empty() {
                tag.insert_text(ItemKey::MusicBrainzReleaseId, st.to_string());
            }
        }
    }
}

pub fn write_tags_to_file(path_str: &str, tags: &Bound<'_, PyDict>) -> Result<(), String> {
    let path = Path::new(path_str);
    if !path.exists() {
        return Err(format!("File does not exist: {}", path.display()));
    }

    let parse_opts = ParseOptions::new()
        .read_properties(false)
        .parsing_mode(ParsingMode::Relaxed);

    let mut tagged_file = Probe::open(path)
        .map_err(|e| format!("Failed to open {}: {}", path.display(), e))?
        .options(parse_opts)
        .read()
        .map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;

    if tagged_file.file_type() == FileType::Wav {
        let mut id3_tag = Tag::new(TagType::Id3v2);
        let mut riff_tag = Tag::new(TagType::RiffInfo);
        populate_tag_items(&mut id3_tag, tags);
        populate_tag_items(&mut riff_tag, tags);
        tagged_file.insert_tag(id3_tag);
        tagged_file.insert_tag(riff_tag);
    } else {
        let tag_type = match tagged_file.file_type() {
            FileType::Mpeg | FileType::Aiff => TagType::Id3v2,
            FileType::Mp4 | FileType::Aac => TagType::Mp4Ilst,
            FileType::Flac | FileType::Opus | FileType::Vorbis | FileType::Speex => TagType::VorbisComments,
            FileType::Ape => TagType::Ape,
            _ => tagged_file.primary_tag_type(),
        };
        let mut tag = Tag::new(tag_type);
        populate_tag_items(&mut tag, tags);
        tagged_file.insert_tag(tag);
    }

    tagged_file
        .save_to_path(path, WriteOptions::default())
        .map_err(|e| format!("Failed to save tags to {}: {}", path.display(), e))?;

    Ok(())
}

impl MetadataWriter {
    pub fn write<P: AsRef<Path>>(path: P, tags: &Bound<'_, PyDict>) -> Result<(), String> {
        let path_str = path.as_ref().to_string_lossy().to_string();
        write_tags_to_file(&path_str, tags)
    }
}
