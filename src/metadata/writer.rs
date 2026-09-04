use lofty::config::{ParseOptions, ParsingMode, WriteOptions};
use lofty::file::{AudioFile, FileType, TaggedFileExt};
use lofty::probe::Probe;
use lofty::tag::{Accessor, ItemKey, ItemValue, Tag, TagItem, TagType};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::path::Path;

pub struct MetadataWriter;

fn populate_tag_items(tag: &mut Tag, tags: &HashMap<String, String>) {
    let version_str = tags
        .get("version")
        .or_else(|| tags.get("subtitle"))
        .or_else(|| tags.get("edition"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());

    // Extract and set title with version injection
    if let Some(title_val) = tags.get("title") {
        let st = title_val.trim();
        if !st.is_empty() {
            let final_title = if let Some(ver) = version_str {
                if !st.to_lowercase().contains(&ver.to_lowercase()) {
                    format!("{} ({})", st, ver)
                } else {
                    st.to_string()
                }
            } else {
                st.to_string()
            };
            tag.insert_text(ItemKey::TrackTitle, final_title);
        }
    }

    // Set version in container-specific tags (TIT3 for ID3v2, SUBTITLE / VERSION for Vorbis, freeform for MP4)
    if let Some(ver) = version_str {
        tag.insert_text(ItemKey::TrackSubtitle, ver.to_string());
        let version_key = if tag.tag_type() == TagType::Mp4Ilst {
            "----:com.apple.iTunes:VERSION".to_string()
        } else {
            "VERSION".to_string()
        };
        tag.insert_unchecked(TagItem::new(
            ItemKey::Unknown(version_key),
            ItemValue::Text(ver.to_string()),
        ));
    }

    // Extract and set artist / artist_name
    let artist_val = tags
        .get("artist")
        .or_else(|| tags.get("artist_name"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(st) = artist_val {
        tag.insert_text(ItemKey::TrackArtist, st.to_string());
    }

    // Extract and set album / album_title
    let album_val = tags
        .get("album")
        .or_else(|| tags.get("album_title"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(st) = album_val {
        tag.insert_text(ItemKey::AlbumTitle, st.to_string());
    }

    // Extract and set album_artist
    let album_artist_val = tags
        .get("album_artist")
        .or_else(|| tags.get("albumartist"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(st) = album_artist_val {
        tag.insert_text(ItemKey::AlbumArtist, st.to_string());
    }

    // Extract and set track number
    let track_val = tags
        .get("track_number")
        .or_else(|| tags.get("track_no"))
        .or_else(|| tags.get("track"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(s) = track_val {
        let clean_s = s.split('/').next().unwrap_or(s).trim();
        if let Ok(num) = clean_s.parse::<u32>() {
            tag.set_track(num);
        } else {
            tag.insert_text(ItemKey::TrackNumber, clean_s.to_string());
        }
    }

    // Extract and set disc number
    let disc_val = tags
        .get("disc_number")
        .or_else(|| tags.get("disc_no"))
        .or_else(|| tags.get("disc"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(s) = disc_val {
        let clean_s = s.split('/').next().unwrap_or(s).trim();
        if let Ok(num) = clean_s.parse::<u32>() {
            tag.set_disk(num);
        } else {
            tag.insert_text(ItemKey::DiscNumber, clean_s.to_string());
        }
    }

    // Extract and set year / date / release_year
    let year_val = tags
        .get("year")
        .or_else(|| tags.get("release_year"))
        .or_else(|| tags.get("date"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(s) = year_val {
        let year_4 = if s.len() >= 4 && s[..4].chars().all(|c| c.is_ascii_digit()) {
            &s[..4]
        } else {
            s
        };
        if let Ok(num) = year_4.parse::<u32>() {
            tag.set_year(num);
        } else {
            tag.insert_text(ItemKey::RecordingDate, s.to_string());
        }
    }

    // Extract and set genre
    if let Some(g_val) = tags
        .get("genre")
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
    {
        tag.set_genre(g_val.to_string());
    }

    // Extract and set ISRC
    if let Some(isrc_val) = tags.get("isrc").map(|s| s.trim()).filter(|s| !s.is_empty()) {
        tag.insert_text(ItemKey::Isrc, isrc_val.to_string());
    }

    // Extract and set MusicBrainz recording / track ID
    let mbid_val = tags
        .get("musicbrainz_track_id")
        .or_else(|| tags.get("musicbrainz_id"))
        .or_else(|| tags.get("mbid"))
        .or_else(|| tags.get("musicbrainz_trackid"))
        .or_else(|| tags.get("recording_id"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(s) = mbid_val {
        tag.insert_text(ItemKey::MusicBrainzTrackId, s.to_string());
    }

    // Extract and set MusicBrainz release ID
    let mb_album_val = tags
        .get("musicbrainz_album_id")
        .or_else(|| tags.get("mb_release_id"))
        .or_else(|| tags.get("musicbrainz_releasegroupid"))
        .or_else(|| tags.get("release_id"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(s) = mb_album_val {
        tag.insert_text(ItemKey::MusicBrainzReleaseId, s.to_string());
    }

    // Extract and set Repack Source (compilation name for realigned studio tracks)
    if let Some(r_source) = tags
        .get("repack_source")
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
    {
        let key_str = if tag.tag_type() == TagType::Mp4Ilst {
            "----:com.apple.iTunes:REPACK_SOURCE".to_string()
        } else {
            "REPACK_SOURCE".to_string()
        };
        tag.insert_unchecked(TagItem::new(
            ItemKey::Unknown(key_str),
            ItemValue::Text(r_source.to_string()),
        ));
    }

    // Extract and set Repack Release MBID (compilation release MBID for realigned tracks)
    if let Some(r_mbid) = tags
        .get("repack_release_mbid")
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
    {
        let key_str = if tag.tag_type() == TagType::Mp4Ilst {
            "----:com.apple.iTunes:REPACK_RELEASE_MBID".to_string()
        } else {
            "REPACK_RELEASE_MBID".to_string()
        };
        tag.insert_unchecked(TagItem::new(
            ItemKey::Unknown(key_str),
            ItemValue::Text(r_mbid.to_string()),
        ));
    }

    // Extract and set MusicBrainz Release Group ID
    let rgid_val = tags
        .get("musicbrainz_release_group_id")
        .or_else(|| tags.get("release_group_id"))
        .or_else(|| tags.get("musicbrainz_releasegroupid"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(s) = rgid_val {
        tag.insert_text(ItemKey::MusicBrainzReleaseGroupId, s.to_string());
        if tag.tag_type() != TagType::Mp4Ilst {
            tag.insert_unchecked(TagItem::new(
                ItemKey::Unknown("MUSICBRAINZ_RELEASEGROUPID".to_string()),
                ItemValue::Text(s.to_string()),
            ));
        }
    }
}

fn populate_riff_items(tag: &mut Tag, tags: &HashMap<String, String>) {
    let version_str = tags
        .get("version")
        .or_else(|| tags.get("subtitle"))
        .or_else(|| tags.get("edition"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());

    if let Some(title_val) = tags.get("title") {
        let st = title_val.trim();
        if !st.is_empty() {
            let final_title = if let Some(ver) = version_str {
                if !st.to_lowercase().contains(&ver.to_lowercase()) {
                    format!("{} ({})", st, ver)
                } else {
                    st.to_string()
                }
            } else {
                st.to_string()
            };
            tag.insert_text(ItemKey::TrackTitle, final_title);
        }
    }

    let artist_val = tags
        .get("artist")
        .or_else(|| tags.get("artist_name"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(st) = artist_val {
        tag.insert_text(ItemKey::TrackArtist, st.to_string());
    }

    let album_val = tags
        .get("album")
        .or_else(|| tags.get("album_title"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(st) = album_val {
        tag.insert_text(ItemKey::AlbumTitle, st.to_string());
    }

    let track_val = tags
        .get("track_number")
        .or_else(|| tags.get("track_no"))
        .or_else(|| tags.get("track"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(s) = track_val {
        let clean_s = s.split('/').next().unwrap_or(s).trim();
        if let Ok(num) = clean_s.parse::<u32>() {
            tag.set_track(num);
        }
    }

    let year_val = tags
        .get("year")
        .or_else(|| tags.get("release_year"))
        .or_else(|| tags.get("date"))
        .map(|s| s.trim())
        .filter(|s| !s.is_empty());
    if let Some(s) = year_val {
        let year_4 = if s.len() >= 4 && s[..4].chars().all(|c| c.is_ascii_digit()) {
            &s[..4]
        } else {
            s
        };
        if let Ok(num) = year_4.parse::<u32>() {
            tag.set_year(num);
        }
    }

    if let Some(g_val) = tags
        .get("genre")
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
    {
        tag.set_genre(g_val.to_string());
    }
}

fn open_probe<P: AsRef<Path>>(path: P) -> Result<Probe<std::io::BufReader<std::fs::File>>, String> {
    let p = path.as_ref();
    let file =
        std::fs::File::open(p).map_err(|e| format!("Failed to open {}: {}", p.display(), e))?;
    let reader = std::io::BufReader::new(file);
    let probe = Probe::new(reader);
    let mut probe = match probe.guess_file_type() {
        Ok(pr) => pr,
        Err(_) => Probe::new(std::io::BufReader::new(
            std::fs::File::open(p)
                .map_err(|e| format!("Failed to reopen {}: {}", p.display(), e))?,
        )),
    };
    if probe.file_type().is_none() {
        if let Ok(ext_probe) = Probe::open(p) {
            if let Some(ft) = ext_probe.file_type() {
                probe = probe.set_file_type(ft);
            }
        }
    }
    Ok(probe)
}

pub fn write_tags_to_file(path_str: &str, tags: &HashMap<String, String>) -> Result<(), String> {
    let path = Path::new(path_str);
    if !path.exists() {
        return Err(format!("File does not exist: {}", path.display()));
    }

    let parse_opts = ParseOptions::new()
        .read_properties(false)
        .parsing_mode(ParsingMode::Relaxed);

    let mut tagged_file = match open_probe(path).and_then(|probe| {
        probe
            .options(parse_opts)
            .read()
            .map_err(|e| format!("Failed to read {}: {}", path.display(), e))
    }) {
        Ok(tf) => tf,
        Err(_) => {
            let no_tags_opts = ParseOptions::new()
                .read_properties(false)
                .read_tags(false)
                .parsing_mode(ParsingMode::Relaxed);
            open_probe(path)?
                .options(no_tags_opts)
                .read()
                .map_err(|e| format!("Failed to read {}: {}", path.display(), e))?
        }
    };

    if tagged_file.file_type() == FileType::Wav {
        let mut id3_tag = Tag::new(TagType::Id3v2);
        let mut riff_tag = Tag::new(TagType::RiffInfo);
        populate_tag_items(&mut id3_tag, tags);
        populate_riff_items(&mut riff_tag, tags);
        tagged_file.insert_tag(id3_tag);
        tagged_file.insert_tag(riff_tag);
    } else {
        let tag_type = match tagged_file.file_type() {
            FileType::Mpeg | FileType::Aiff => TagType::Id3v2,
            FileType::Mp4 | FileType::Aac => TagType::Mp4Ilst,
            FileType::Flac | FileType::Opus | FileType::Vorbis | FileType::Speex => {
                TagType::VorbisComments
            }
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
    pub fn write_map<P: AsRef<Path>>(
        path: P,
        tags: &HashMap<String, String>,
    ) -> Result<(), String> {
        let path_str = path.as_ref().to_string_lossy().to_string();
        write_tags_to_file(&path_str, tags)
    }

    pub fn write<P: AsRef<Path>>(path: P, tags: &Bound<'_, PyDict>) -> Result<(), String> {
        let path_str = path.as_ref().to_string_lossy().to_string();
        let mut map = HashMap::new();
        for (k, v) in tags.iter() {
            if let (Ok(key), Ok(val)) = (k.extract::<String>(), v.extract::<String>()) {
                map.insert(key.to_lowercase(), val);
            }
        }
        write_tags_to_file(&path_str, &map)
    }
}
