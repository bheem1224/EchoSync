use lofty::file::{AudioFile, TaggedFileExt};
use lofty::probe::Probe;
use lofty::tag::{Accessor, ItemKey, Tag, TagType};
use std::path::Path;

#[cfg(unix)]
use std::os::unix::fs::MetadataExt;

/// Pure Rust struct storing audiophile metadata and technical audio stream properties.
#[derive(Debug, Clone, Default)]
pub struct TrackMetadata {
    pub title: Option<String>,
    pub artist: Option<String>,
    pub album_artist: Option<String>,
    pub album: Option<String>,
    pub track_no: Option<u32>,
    pub disc_no: Option<u32>,
    pub year: Option<u32>,
    pub genre: Option<String>,
    pub mbid: Option<String>,
    pub codec: String,
    pub bit_depth: Option<u8>,
    pub sample_rate: Option<u32>,
    pub channels: Option<u8>,
    pub bitrate: Option<u32>,
    pub duration_ms: u64,
    pub file_path: String,
    pub file_size_bytes: u64,
    pub mtime: Option<f64>,
    pub inode: Option<u64>,
}

fn extract_from_tag(
    t: &Tag,
    title: &mut Option<String>,
    artist: &mut Option<String>,
    album_artist: &mut Option<String>,
    album: &mut Option<String>,
    track_no: &mut Option<u32>,
    disc_no: &mut Option<u32>,
    year: &mut Option<u32>,
    genre: &mut Option<String>,
    mbid: &mut Option<String>,
) {
    if title.is_none() {
        let t_val = t
            .title()
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .or_else(|| {
                t.get(&ItemKey::TrackTitle)
                    .and_then(|item| item.value().text())
                    .map(|s| s.trim().to_string())
                    .filter(|s| !s.is_empty())
            });
        if t_val.is_some() {
            *title = t_val;
        }
    }
    if artist.is_none() {
        let a_val = t
            .artist()
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .or_else(|| {
                t.get(&ItemKey::TrackArtist)
                    .and_then(|item| item.value().text())
                    .map(|s| s.trim().to_string())
                    .filter(|s| !s.is_empty())
            });
        if a_val.is_some() {
            *artist = a_val;
        }
    }
    if album.is_none() {
        let alb_val = t
            .album()
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .or_else(|| {
                t.get(&ItemKey::AlbumTitle)
                    .and_then(|item| item.value().text())
                    .map(|s| s.trim().to_string())
                    .filter(|s| !s.is_empty())
            });
        if alb_val.is_some() {
            *album = alb_val;
        }
    }
    if track_no.is_none() {
        *track_no = t.track();
    }
    if disc_no.is_none() {
        *disc_no = t.disk();
    }
    if year.is_none() {
        *year = t.year();
    }
    if genre.is_none() {
        let g_val = t
            .genre()
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .or_else(|| {
                t.get(&ItemKey::Genre)
                    .and_then(|item| item.value().text())
                    .map(|s| s.trim().to_string())
                    .filter(|s| !s.is_empty())
            });
        if g_val.is_some() {
            *genre = g_val;
        }
    }
    if album_artist.is_none() {
        if let Some(aa_item) = t.get(&ItemKey::AlbumArtist) {
            if let Some(s) = aa_item.value().text() {
                let st = s.trim();
                if !st.is_empty() {
                    *album_artist = Some(st.to_string());
                }
            }
        }
    }
    if mbid.is_none() {
        if let Some(mbid_item) = t.get(&ItemKey::MusicBrainzTrackId) {
            if let Some(s) = mbid_item.value().text() {
                let st = s.trim();
                if !st.is_empty() {
                    *mbid = Some(st.to_string());
                }
            }
        }
    }
}

pub struct MetadataExtractor;

impl MetadataExtractor {
    /// Parse audio file using lofty crate and extract audiophile tags & technical telemetry.
    pub fn extract<P: AsRef<Path>>(path: P) -> Result<TrackMetadata, String> {
        let p = path.as_ref();
        let path_str = p.to_string_lossy().to_string();

        let mut file_size_bytes = 0;
        let mut mtime = None;
        let mut inode = None;

        if let Ok(m) = std::fs::metadata(p) {
            file_size_bytes = m.len();
            if let Ok(modified) = m.modified() {
                if let Ok(dur) = modified.duration_since(std::time::UNIX_EPOCH) {
                    mtime = Some(dur.as_secs_f64());
                }
            }
            #[cfg(unix)]
            {
                inode = Some(m.ino());
            }
            #[cfg(windows)]
            {
                // m.file_index() is nightly-only (windows_by_handle), so we fallback to None
                let _ = &m;
                inode = None;
            }
        }

        let parse_opts = lofty::config::ParseOptions::new()
            .parsing_mode(lofty::config::ParsingMode::Relaxed);

        let tagged_file_opt = match Probe::open(p).and_then(|probe| probe.options(parse_opts).read()) {
            Ok(tf) => Some(tf),
            Err(_) => {
                let tag_only_opts = lofty::config::ParseOptions::new()
                    .read_properties(false)
                    .parsing_mode(lofty::config::ParsingMode::Relaxed);
                match Probe::open(p).and_then(|probe| probe.options(tag_only_opts).read()) {
                    Ok(tf) => Some(tf),
                    Err(_) => {
                        // Try reading only stream properties if tags are corrupt
                        let props_only_opts = lofty::config::ParseOptions::new()
                            .read_tags(false)
                            .parsing_mode(lofty::config::ParsingMode::Relaxed);
                        Probe::open(p).and_then(|probe| probe.options(props_only_opts).read()).ok()
                    }
                }
            }
        };

        let tagged_file = match tagged_file_opt {
            Some(tf) => tf,
            None => {
                return Ok(TrackMetadata {
                    codec: "CORRUPT".to_string(),
                    file_path: path_str,
                    file_size_bytes,
                    mtime,
                    inode,
                    ..Default::default()
                });
            }
        };

        let properties = tagged_file.properties();
        let duration_ms = properties.duration().as_millis() as u64;
        let sample_rate = properties.sample_rate();
        let channels = properties.channels();
        let bit_depth = properties.bit_depth();
        let bitrate = properties.audio_bitrate();

        let file_type = tagged_file.file_type();
        let codec = format!("{:?}", file_type).to_uppercase();

        let mut title = None;
        let mut artist = None;
        let mut album_artist = None;
        let mut album = None;
        let mut track_no = None;
        let mut disc_no = None;
        let mut year = None;
        let mut genre = None;
        let mut mbid = None;

        // Container-specific preferred and fallback tag search
        let mut candidate_tags: Vec<&Tag> = Vec::new();

        if let Some(t) = tagged_file.primary_tag() {
            candidate_tags.push(t);
        }
        if let Some(t) = tagged_file.tag(TagType::Id3v2) {
            candidate_tags.push(t);
        }
        if let Some(t) = tagged_file.tag(TagType::RiffInfo) {
            candidate_tags.push(t);
        }
        if let Some(t) = tagged_file.tag(TagType::Mp4Ilst) {
            candidate_tags.push(t);
        }
        if let Some(t) = tagged_file.tag(TagType::VorbisComments) {
            candidate_tags.push(t);
        }
        if let Some(t) = tagged_file.tag(TagType::Ape) {
            candidate_tags.push(t);
        }
        if let Some(t) = tagged_file.first_tag() {
            candidate_tags.push(t);
        }
        for t in tagged_file.tags() {
            candidate_tags.push(t);
        }

        for t in candidate_tags {
            extract_from_tag(
                t,
                &mut title,
                &mut artist,
                &mut album_artist,
                &mut album,
                &mut track_no,
                &mut disc_no,
                &mut year,
                &mut genre,
                &mut mbid,
            );
        }

        Ok(TrackMetadata {
            title,
            artist,
            album_artist,
            album,
            track_no,
            disc_no,
            year,
            genre,
            mbid,
            codec,
            bit_depth,
            sample_rate,
            channels,
            bitrate,
            duration_ms,
            file_path: path_str,
            file_size_bytes,
            mtime,
            inode,
        })
    }
}
