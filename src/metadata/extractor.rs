use lofty::file::{AudioFile, TaggedFileExt};
use lofty::probe::Probe;
use lofty::tag::{Accessor, ItemKey};
use std::path::Path;

#[cfg(unix)]
use std::os::unix::fs::MetadataExt;
#[cfg(windows)]
use std::os::windows::fs::MetadataExt;

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
                inode = None;
            }
        }

        let parse_opts = lofty::config::ParseOptions::new()
            .parsing_mode(lofty::config::ParsingMode::Relaxed);

        let tagged_file = match Probe::open(p).and_then(|probe| probe.options(parse_opts).read()) {
            Ok(tf) => tf,
            Err(_) => {
                let tag_only_opts = lofty::config::ParseOptions::new()
                    .read_properties(false)
                    .parsing_mode(lofty::config::ParsingMode::Relaxed);
                match Probe::open(p).and_then(|probe| probe.options(tag_only_opts).read()) {
                    Ok(tf) => tf,
                    Err(_) => {
                        return Ok(TrackMetadata {
                            codec: "CORRUPT".to_string(),
                            file_path: path_str,
                            file_size_bytes,
                            mtime,
                            inode,
                            ..Default::default()
                        });
                    }
                }
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

        let tag = tagged_file.primary_tag().or_else(|| tagged_file.first_tag());

        let mut title = None;
        let mut artist = None;
        let mut album_artist = None;
        let mut album = None;
        let mut track_no = None;
        let mut disc_no = None;
        let mut year = None;
        let mut genre = None;
        let mut mbid = None;

        if let Some(t) = tag {
            title = t.title().as_deref().map(|s| s.to_string());
            artist = t.artist().as_deref().map(|s| s.to_string());
            album = t.album().as_deref().map(|s| s.to_string());
            track_no = t.track();
            disc_no = t.disk();
            year = t.year();
            genre = t.genre().as_deref().map(|s| s.to_string());

            if let Some(aa_item) = t.get(&ItemKey::AlbumArtist) {
                album_artist = aa_item.value().text().map(|s| s.to_string());
            }

            if let Some(mbid_item) = t.get(&ItemKey::MusicBrainzTrackId) {
                mbid = mbid_item.value().text().map(|s| s.to_string());
            }
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
