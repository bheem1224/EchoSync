use regex::Regex;
use once_cell::sync::Lazy;
use std::collections::HashSet;

// --- Regex Constants ---

// Artist - Title format (most common)
// Added anchor `$` to ensure we match the end or version group at the end
static PATTERN_ARTIST_TITLE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)^(?P<artist>[^-]+?)\s*[-–]\s*(?P<title>.+?)(?:\s*\((?P<version>[^)]+)\))?$").unwrap()
});

// Artist - Album - Title
static PATTERN_ARTIST_ALBUM_TITLE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)^(?P<artist>[^-]+?)\s*[-–]\s*(?P<album>[^-]+?)\s*[-–]\s*(?P<title>.+?)(?:\s*\((?P<version>[^)]+)\))?$").unwrap()
});

// Title (feat. Artist)
static PATTERN_FEAT_ARTIST: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)(?P<title>.+?)\s+(?:feat\.?|ft\.?|featuring)\s+(?P<feat_artist>.+?)(?:\s*\((?P<version>[^)]+)\))?$").unwrap()
});

// Version/Remix detection
#[allow(dead_code)]
static PATTERN_VERSION: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)\b(?:remix|rmx|mix|version|ver\.?|edit|extended|instrumental|acapella|bootleg|cover|remaster|remastered|original|club|radio|house|deep|progressive)\b").unwrap()
});

// Edition extraction (from original struct)
static EDITION_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)(?:[\(\[]| - )\s*(.*?(?:Remix|Mix|Live|Demo|Remaster|Deluxe|Edit|Version|Acoustic|Instrumental|Bonus|Extended|Original).*?)(?:[\)\]]|$)").unwrap()
});

// Quality Patterns
static PATTERN_QUALITY_FLAC: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?i)\bFLAC\b|\b(?:24[-_]?bit|16[-_]?bit|lossless)\b").unwrap());
static PATTERN_QUALITY_MP3_320: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?i)\b(?:320|MP3[-_]?320|320kbps|320k)\b").unwrap());
static PATTERN_QUALITY_MP3_256: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?i)\b(?:256|MP3[-_]?256|256kbps|256k)\b").unwrap());
static PATTERN_QUALITY_MP3_192: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?i)\b(?:192|MP3[-_]?192|192kbps|192k)\b").unwrap());
static PATTERN_QUALITY_AAC: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?i)\b(?:AAC|M4A|iTunes|256 AAC|AAC[-_]?256)\b").unwrap());
static PATTERN_QUALITY_ALAC: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?i)\bALAC\b").unwrap());
static PATTERN_QUALITY_OGG: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?i)\b(?:OGG|Vorbis|OGG[-_]?V)\b").unwrap());
static PATTERN_QUALITY_OPUS: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?i)\bOpus\b").unwrap());
#[allow(dead_code)]
static PATTERN_QUALITY_WMA: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?i)\bWMA\b").unwrap());

// Junk Patterns
// Added matching for empty brackets/parens which might result from other cleanups
static PATTERN_JUNK: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)\b(?:www\d+|320|192|256|FLAC|MP3|AAC|OGG|WAV|m4a|flac|mp3|aac|ogg|wav)[\.\s]*$|^\[.*?\]|\{.*?\}|<.*?>|_+|~.*?~|\[\s*\]|\(\s*\)").unwrap()
});

static PATTERN_TRACK_NUMBER: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)^(?:(?P<disc>\d+)[.-])?(?P<track>\d{1,2})[\s.-]").unwrap()
});

static PATTERN_YEAR: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)\((?P<year>19\d{2}|20\d{2})\)|\[(?P<year_bracket>19\d{2}|20\d{2})\]").unwrap()
});

// Parenthetical content
#[allow(dead_code)]
static PATTERN_PARENTHETICAL: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)\s*\(([^)]+)\)\s*").unwrap()
});


#[derive(Debug, Clone, Default)]
pub struct ParsedMetadata {
    pub title: String,
    pub artist: String,
    pub album: Option<String>,
    pub edition: Option<String>,
    pub quality_tags: Vec<String>,
    #[allow(dead_code)]
    pub track_number: Option<i32>,
    #[allow(dead_code)]
    pub disc_number: Option<i32>,
    #[allow(dead_code)]
    pub release_year: Option<i32>,
}

pub struct TrackParser;

impl TrackParser {

    /// Main entry point for cleaning metadata for SoulSyncTrack::new
    pub fn clean_metadata(
        raw_title: &str,
        artist_name: &str,
        album_title: &str
    ) -> ParsedMetadata {

        let mut clean_title = raw_title.to_string();

        // 1. Remove Junk (Pass 1)
        clean_title = Self::remove_junk(&clean_title);

        // 2. Extract Quality Tags
        let quality_tags = Self::extract_quality_tags(&clean_title);
        clean_title = Self::remove_quality_markers(&clean_title);

        // 3. Extract Edition
        let mut edition = None;
        if let Some((extracted_edition, cleaned)) = Self::extract_edition(&clean_title) {
            edition = Some(extracted_edition);
            clean_title = cleaned;
        }

        // 4. Remove Junk (Pass 2 - cleanup empty brackets from quality/edition removal)
        clean_title = Self::remove_junk(&clean_title);

        // 5. Balanced Quote Stripping
        clean_title = Self::strip_quotes(&clean_title);

        // 6. Normalization
        clean_title = Self::normalize_text(&clean_title);
        let clean_artist = Self::normalize_text(artist_name);
        let clean_album = Self::normalize_text(album_title);

        ParsedMetadata {
            title: clean_title,
            artist: clean_artist,
            album: if clean_album.is_empty() { None } else { Some(clean_album) },
            edition,
            quality_tags,
            track_number: None, // Not extracted from title usually
            disc_number: None,
            release_year: None,
        }
    }

    /// Parse a raw filename string (e.g. "Artist - Title")
    pub fn parse_filename(filename: &str) -> ParsedMetadata {
        let mut working_string = filename.trim().to_string();

        // 0. Remove extensions FIRST to avoid junk regex matching inside extension
        let extension_regex = Regex::new(r"(?i)\.(mp3|flac|m4a|aac|ogg|wav|wma)$").unwrap();
        working_string = extension_regex.replace(&working_string, "").to_string();
        working_string = working_string.trim().to_string();

        // Extract year
        let year = Self::extract_year(&working_string);

        // Extract track numbers
        let (track_num, disc_num) = Self::extract_track_numbers(&working_string);

        // Remove junk
        working_string = Self::remove_junk(&working_string);

        // Extract quality
        let quality_tags = Self::extract_quality_tags(&working_string);
        working_string = Self::remove_quality_markers(&working_string);

        // Remove junk again (Pass 2) to clean empty brackets from quality markers
        working_string = Self::remove_junk(&working_string);

        // Parse Patterns
        let (mut raw_title, artist, album, mut edition) = if let Some(caps) = PATTERN_ARTIST_ALBUM_TITLE.captures(&working_string) {
             (
                caps.name("title").map(|m| m.as_str()).unwrap_or("").to_string(),
                caps.name("artist").map(|m| m.as_str()).unwrap_or("").to_string(),
                caps.name("album").map(|m| m.as_str()).map(|s| s.to_string()),
                caps.name("version").map(|m| m.as_str().to_string())
             )
        } else if let Some(caps) = PATTERN_ARTIST_TITLE.captures(&working_string) {
             (
                caps.name("title").map(|m| m.as_str()).unwrap_or("").to_string(),
                caps.name("artist").map(|m| m.as_str()).unwrap_or("").to_string(),
                None,
                caps.name("version").map(|m| m.as_str().to_string())
             )
        } else if let Some(caps) = PATTERN_FEAT_ARTIST.captures(&working_string) {
             (
                caps.name("title").map(|m| m.as_str()).unwrap_or("").to_string(),
                String::new(),
                None,
                caps.name("version").map(|m| m.as_str().to_string())
             )
        } else {
            // Fallback
            (
                working_string.clone(),
                "Unknown".to_string(),
                Some("Unknown".to_string()),
                None
            )
        };

        if raw_title.is_empty() {
             // If title empty even after fallback (empty string input?), use placeholder
             raw_title = "Unknown Track".to_string();
        }

        // If edition not captured by regex pattern, try to extract from title
        if edition.is_none() {
            if let Some((extracted_edition, cleaned)) = Self::extract_edition(&raw_title) {
                edition = Some(extracted_edition);
                raw_title = cleaned;
            }
        }

        // Clean up title
        raw_title = Self::strip_quotes(&raw_title);
        raw_title = Self::normalize_text(&raw_title);

        ParsedMetadata {
            title: raw_title,
            artist: Self::normalize_text(&artist),
            album: album.map(|a| Self::normalize_text(&a)),
            edition: edition.map(|e| Self::normalize_text(&e)),
            quality_tags,
            track_number: track_num,
            disc_number: disc_num,
            release_year: year,
        }
    }

    pub fn extract_edition(text: &str) -> Option<(String, String)> {
        // Use the legacy regex logic
        // Find first match
        if let Some(caps) = EDITION_REGEX.captures(text) {
             let extracted_edition = caps.get(1).map(|m| m.as_str().trim().to_string())?;

             // Remove match from text
             if let Some(whole_match) = caps.get(0) {
                 let start = whole_match.start();
                 let end = whole_match.end();
                 let mut cleaned = text.to_string();
                 cleaned.replace_range(start..end, "");
                 return Some((extracted_edition, cleaned.trim().to_string()));
             }
        }
        None
    }

    pub fn remove_junk(text: &str) -> String {
        let mut s = PATTERN_JUNK.replace_all(text, "").to_string();
        // Clean up whitespace
        s = s.split_whitespace().collect::<Vec<_>>().join(" ");
        s
    }

    pub fn extract_quality_tags(text: &str) -> Vec<String> {
        let mut tags = Vec::new();
        if PATTERN_QUALITY_FLAC.is_match(text) {
             if Regex::new(r"(?i)\b24[-_]?bit\b").unwrap().is_match(text) {
                 tags.push("FLAC_24BIT".to_string());
             } else {
                 tags.push("FLAC_16BIT".to_string());
             }
        }
        if PATTERN_QUALITY_MP3_320.is_match(text) { tags.push("MP3_320KBPS".to_string()); }
        if PATTERN_QUALITY_MP3_256.is_match(text) { tags.push("MP3_256KBPS".to_string()); }
        if PATTERN_QUALITY_MP3_192.is_match(text) { tags.push("MP3_192KBPS".to_string()); }
        if PATTERN_QUALITY_AAC.is_match(text) { tags.push("AAC".to_string()); }
        if PATTERN_QUALITY_ALAC.is_match(text) { tags.push("ALAC".to_string()); }
        if PATTERN_QUALITY_OGG.is_match(text) { tags.push("OGG_VORBIS".to_string()); }
        if PATTERN_QUALITY_OPUS.is_match(text) { tags.push("OPUS".to_string()); }

        tags
    }

    pub fn remove_quality_markers(text: &str) -> String {
        let p1 = Regex::new(r"(?i)\b(?:FLAC|MP3|AAC|OGG|ALAC|Opus|WMA)\b").unwrap();
        let p2 = Regex::new(r"(?i)\b(?:24[-_]?bit|16[-_]?bit|lossless|320kbps|256kbps|192kbps|320k|256k|192k)\b").unwrap();
        let s = p1.replace_all(text, "");
        let s = p2.replace_all(&s, "");
        s.trim().to_string()
    }

    pub fn strip_quotes(text: &str) -> String {
        let s = text.trim();
        if s.len() >= 2 {
            let bytes = s.as_bytes();
            let first = bytes[0];
            let last = bytes[s.len() - 1];
            if (first == b'"' && last == b'"') || (first == b'\'' && last == b'\'') {
                return s[1..s.len()-1].to_string();
            }
        }
        s.to_string()
    }

    pub fn normalize_text(text: &str) -> String {
        text.trim().to_string()
    }

    pub fn extract_year(text: &str) -> Option<i32> {
        PATTERN_YEAR.captures(text).and_then(|caps| {
            caps.name("year")
                .or_else(|| caps.name("year_bracket"))
                .and_then(|m| m.as_str().parse::<i32>().ok())
        })
    }

    pub fn extract_track_numbers(text: &str) -> (Option<i32>, Option<i32>) {
        if let Some(caps) = PATTERN_TRACK_NUMBER.captures(text) {
             let track = caps.name("track").and_then(|m| m.as_str().parse::<i32>().ok());
             let disc = caps.name("disc").and_then(|m| m.as_str().parse::<i32>().ok());
             (track, disc)
        } else {
            (None, None)
        }
    }
}
