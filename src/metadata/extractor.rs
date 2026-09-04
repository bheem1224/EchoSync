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
    pub version: Option<String>,
    pub isrc: Option<String>,
    pub musicbrainz_track_id: Option<String>,
    pub musicbrainz_album_id: Option<String>,
    pub repack_source: Option<String>,
    pub repack_release_mbid: Option<String>,
    pub release_group_id: Option<String>,
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

fn get_unknown_or_text(t: &Tag, target_key: &str) -> Option<String> {
    let lower_target = target_key.to_lowercase();
    let suffix = format!(":{}", lower_target);
    for item in t.items() {
        if let ItemKey::Unknown(ref k) = item.key() {
            let lower_k = k.to_lowercase();
            if lower_k == lower_target || lower_k.ends_with(&suffix) {
                if let Some(s) = item.value().text() {
                    let st = s.trim();
                    if !st.is_empty() {
                        return Some(st.to_string());
                    }
                }
            }
        }
    }
    None
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
    version: &mut Option<String>,
    isrc: &mut Option<String>,
    musicbrainz_track_id: &mut Option<String>,
    musicbrainz_album_id: &mut Option<String>,
    repack_source: &mut Option<String>,
    repack_release_mbid: &mut Option<String>,
    release_group_id: &mut Option<String>,
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
    if version.is_none() {
        let v_val = t
            .get(&ItemKey::TrackSubtitle)
            .and_then(|item| item.value().text())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .or_else(|| get_unknown_or_text(t, "VERSION"))
            .or_else(|| get_unknown_or_text(t, "SUBTITLE"));
        if v_val.is_some() {
            *version = v_val;
        }
    }
    if isrc.is_none() {
        let i_val = t
            .get(&ItemKey::Isrc)
            .and_then(|item| item.value().text())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .or_else(|| get_unknown_or_text(t, "ISRC"));
        if i_val.is_some() {
            *isrc = i_val;
        }
    }
    if musicbrainz_track_id.is_none() {
        let m_val = t
            .get(&ItemKey::MusicBrainzTrackId)
            .and_then(|item| item.value().text())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .or_else(|| get_unknown_or_text(t, "MUSICBRAINZ_TRACKID"))
            .or_else(|| get_unknown_or_text(t, "MUSICBRAINZ_TRACK_ID"));
        if m_val.is_some() {
            *musicbrainz_track_id = m_val;
        }
    }
    if musicbrainz_album_id.is_none() {
        let ma_val = t
            .get(&ItemKey::MusicBrainzReleaseId)
            .and_then(|item| item.value().text())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .or_else(|| get_unknown_or_text(t, "MUSICBRAINZ_ALBUMID"))
            .or_else(|| get_unknown_or_text(t, "MUSICBRAINZ_ALBUM_ID"))
            .or_else(|| get_unknown_or_text(t, "MUSICBRAINZ_RELEASEID"));
        if ma_val.is_some() {
            *musicbrainz_album_id = ma_val;
        }
    }
    if repack_source.is_none() {
        *repack_source = get_unknown_or_text(t, "REPACK_SOURCE");
    }
    if repack_release_mbid.is_none() {
        *repack_release_mbid = get_unknown_or_text(t, "REPACK_RELEASE_MBID");
    }
    if release_group_id.is_none() {
        let rg_val = t
            .get(&ItemKey::MusicBrainzReleaseGroupId)
            .and_then(|item| item.value().text())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .or_else(|| get_unknown_or_text(t, "MUSICBRAINZ_RELEASEGROUPID"))
            .or_else(|| get_unknown_or_text(t, "MUSICBRAINZ_RELEASE_GROUP_ID"));
        if rg_val.is_some() {
            *release_group_id = rg_val;
        }
    }
    if mbid.is_none() {
        if let Some(ref mid) = musicbrainz_track_id {
            *mbid = Some(mid.clone());
        }
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

        let parse_opts =
            lofty::config::ParseOptions::new().parsing_mode(lofty::config::ParsingMode::Relaxed);

        let tagged_file_opt = match open_probe(p)
            .and_then(|probe| probe.options(parse_opts).read().map_err(|e| e.to_string()))
        {
            Ok(tf) => Some(tf),
            Err(_) => {
                let tag_only_opts = lofty::config::ParseOptions::new()
                    .read_properties(false)
                    .parsing_mode(lofty::config::ParsingMode::Relaxed);
                match open_probe(p).and_then(|probe| {
                    probe
                        .options(tag_only_opts)
                        .read()
                        .map_err(|e| e.to_string())
                }) {
                    Ok(tf) => Some(tf),
                    Err(_) => {
                        // Try reading only stream properties if tags are corrupt
                        let props_only_opts = lofty::config::ParseOptions::new()
                            .read_tags(false)
                            .parsing_mode(lofty::config::ParsingMode::Relaxed);
                        open_probe(p)
                            .and_then(|probe| {
                                probe
                                    .options(props_only_opts)
                                    .read()
                                    .map_err(|e| e.to_string())
                            })
                            .ok()
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
        let mut version = None;
        let mut isrc = None;
        let mut musicbrainz_track_id = None;
        let mut musicbrainz_album_id = None;
        let mut repack_source = None;
        let mut repack_release_mbid = None;
        let mut release_group_id = None;

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
                &mut version,
                &mut isrc,
                &mut musicbrainz_track_id,
                &mut musicbrainz_album_id,
                &mut repack_source,
                &mut repack_release_mbid,
                &mut release_group_id,
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
            version,
            isrc,
            musicbrainz_track_id,
            musicbrainz_album_id,
            repack_source,
            repack_release_mbid,
            release_group_id,
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
