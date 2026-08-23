use lofty::config::{ParseOptions, ParsingMode, WriteOptions};
use lofty::file::{AudioFile, FileType, TaggedFileExt};
use lofty::probe::Probe;
use lofty::tag::{Accessor, ItemKey, Tag, TagExt, TagType};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::path::Path;

pub struct MetadataWriter;

fn populate_tag_items(tag: &mut Tag, tags: &Bound<'_, PyDict>) {
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
}

impl MetadataWriter {
    pub fn write<P: AsRef<Path>>(path: P, tags: &Bound<'_, PyDict>) -> Result<(), String> {
        let p = path.as_ref();
        if !p.exists() {
            return Err(format!("File does not exist: {}", p.display()));
        }

        let ext = p
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_lowercase();
        let fallback_tag_type = match ext.as_str() {
            "wav" => TagType::RiffInfo,
            "mp3" | "aiff" | "aif" | "dsf" => TagType::Id3v2,
            "flac" | "opus" | "ogg" | "oga" | "spx" => TagType::VorbisComments,
            "m4a" | "mp4" | "aac" | "alac" => TagType::Mp4Ilst,
            "ape" => TagType::Ape,
            _ => TagType::Id3v2,
        };

        let parse_opts = ParseOptions::new()
            .read_properties(false)
            .parsing_mode(ParsingMode::Relaxed);

        let tagged_file_opt = Probe::open(p)
            .ok()
            .and_then(|probe| probe.options(parse_opts).read().ok());

        if let Some(mut tf) = tagged_file_opt {
            let file_type = tf.file_type();
            let tag_type = match file_type {
                FileType::Wav => TagType::RiffInfo,
                FileType::Mpeg | FileType::Aiff => TagType::Id3v2,
                FileType::Mp4 | FileType::Aac => TagType::Mp4Ilst,
                FileType::Flac | FileType::Opus | FileType::Vorbis | FileType::Speex => TagType::VorbisComments,
                FileType::Ape => TagType::Ape,
                _ => tf.primary_tag_type(),
            };

            if tf.tag(tag_type).is_none() {
                tf.insert_tag(Tag::new(tag_type));
            }
            if let Some(t) = tf.tag_mut(tag_type) {
                populate_tag_items(t, tags);
            }

            if file_type == FileType::Wav {
                // Also attempt inserting an ID3v2 chunk into the WAV container if supported
                if tf.tag(TagType::Id3v2).is_none() {
                    tf.insert_tag(Tag::new(TagType::Id3v2));
                }
                if let Some(id3_tag) = tf.tag_mut(TagType::Id3v2) {
                    populate_tag_items(id3_tag, tags);
                }
            }

            // Save tagged_file using lofty
            tf.save_to_path(p, WriteOptions::default())
                .map_err(|e| format!("Failed to save tags to {}: {}", p.display(), e))?;
        } else {
            let mut direct_tag = Tag::new(fallback_tag_type);
            populate_tag_items(&mut direct_tag, tags);
            direct_tag
                .save_to_path(p, WriteOptions::default())
                .map_err(|e| format!("Failed to save direct tags to {}: {}", p.display(), e))?;
        }

        Ok(())
    }
}
