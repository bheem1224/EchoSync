"""
Text normalization and parsing utilities for track metadata.

These functions are provider-agnostic and reused by all providers
to normalize track data before creating SoulSyncTrack objects.
"""

import re
from typing import Optional, Tuple
import base64



def normalize_text(text: Optional[str]) -> str:
    """
    Normalize text for comparison: lowercase, remove extra spaces, standardize characters.
    
    Args:
        text: Text to normalize (can be None)
        
    Returns:
        Normalized text string
    """
    if not text:
        return ""
    
    # Standardize smart quotes and dashes
    text = re.sub(r'[‘’´`]', "'", text)
    text = re.sub(r'[‐—–]', "-", text)

    # Convert to lowercase
    text = text.lower().strip()
    
    # Normalize unicode characters (é -> e, ñ -> n, etc.)
    text = remove_accents(text)

    # Unify featured-artist separators so "feat/ft/featuring/x" become "&"
    # and compare consistently against strings that already use '&'.
    text = re.sub(r'\b(feat\.?|ft\.?|featuring|x)\b', '&', text, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text


def remove_accents(text: str) -> str:
    """Remove diacritical marks from text."""
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFKD', text)
        if unicodedata.category(c) != 'Mn'
    )


def normalize_title(title: Optional[str]) -> str:
    """
    Normalize track title for matching.
    
    - Replace underscores and periods with spaces
    - Strip technical audio terms (flac, mp3, kbps, hz, bit depth, etc.)
    - Lowercase
    - Remove accents
    - Remove extra spaces
    - Strip OST/Soundtrack/Movie metadata
    - Strip trailing/parenthetical featured-artist markers (feat./featuring/with)
    - Keep alphanumeric + common punctuation
    """
    if not title:
        return ""
    
    # STEP 1: Replace underscores and periods with spaces BEFORE other normalization
    # This helps with filenames like "Artist_Name-Song.Title.mp3"
    title = title.replace('_', ' ').replace('.', ' ')
    
    normalized = normalize_text(title)
    
    # STEP 2: Strip technical audio terms that pollute fuzzy matching
    # Pattern covers: flac, mp3, aac, ogg, wav, m4a, 320kbps, 192kbps, 44.1khz, 96khz, 16bit, 24bit, etc.
    audio_terms_pattern = r'\b(?:flac|mp3|aac|ogg|wav|m4a|opus|alac|ape|dsd|dsf|dff|wma|' \
                          r'\d+kbps|\d+k|' \
                          r'\d+(?:\.\d+)?k?hz|' \
                          r'\d+bit|' \
                          r'\d+b)\b'
    normalized = re.sub(audio_terms_pattern, '', normalized, flags=re.IGNORECASE)
    
    # Remove OST/Soundtrack/Movie metadata (must be done before other cleanup)
    # Patterns cover: (From "Movie"), [From Movie], - from "X", (OST), (Original Motion Picture Soundtrack), etc.
    ost_patterns = [
        r'\s*-\s*from\s+"[^"]*"',  # - from "Movie Name" (dash-based suffix)
        r'\s*-\s*from\s+[\w\s]+$',  # - from Movie Name (dash-based suffix without quotes)
        r'\s*[\(\[]\s*original\s+motion\s+picture\s+soundtrack\s*[\)\]]',  # (Original Motion Picture Soundtrack)
        r'\s*[\(\[]\s*motion\s+picture\s+soundtrack\s*[\)\]]',  # (Motion Picture Soundtrack)
        r'\s*[\(\[]\s*from\s+"[^"]*"\s*[\)\]]',  # (From "Movie Name")
        r'\s*[\(\[]\s*from\s+[^\)\]]+[\)\]]',  # [From Movie Name] or (From Movie)
        r'\s*[\(\[]\s*ost\s+[^\)\]]*[\)\]]',  # (OST ...) or [OST ...]
        r'\s*[\(\[]\s*ost\s*[\)\]]',  # (OST) or [OST]
        r'\s*[\(\[]\s*soundtrack\s*[\)\]]',  # [Soundtrack] or (Soundtrack)
    ]
    for pattern in ost_patterns:
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
    
    # Remove parenthetical/bracketed featured artist clauses
    normalized = re.sub(r"\s*[\(\[\{]\s*(feat\.?|featuring|with)\b[^\)\]\}]*[\)\]\}]", "", normalized, flags=re.IGNORECASE)
    # Remove trailing feat/with clauses
    normalized = re.sub(r"\s+(feat\.?|featuring|with)\b.*$", "", normalized, flags=re.IGNORECASE)
    
    # Keep alphanumeric, spaces, hyphens, parentheses, quotes
    normalized = re.sub(r'[^\w\s\-\(\)\'\"]', '', normalized)
    
    # STEP 3: Compress multiple consecutive spaces into single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()


def normalize_artist(artist: Optional[str]) -> str:
    """
    Normalize artist name for matching.
    
    - Lowercase
    - Remove accents
    - Standardize featured artist connectors to '&'
    - Remove extra spaces
    """
    if not artist:
        return ""
    
    normalized = normalize_text(artist)
    
    # normalize_text already unifies feat/ft/featuring/x to '&'.
    # Keep collaborator names so forms like "Artist feat. Guest" and
    # "Artist & Guest" normalize to the same canonical string.
    normalized = re.sub(r'\s*&\s*', ' & ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()


def normalize_album(album: Optional[str]) -> str:
    """
    Normalize album name for matching.
    
    - Lowercase
    - Remove accents
    - Remove OST/Soundtrack metadata
    - Remove "deluxe", "remaster", edition markers
    - Remove extra spaces
    """
    if not album:
        return ""
    
    normalized = normalize_text(album)
    
    # Remove OST/Soundtrack metadata (same patterns as normalize_title)
    ost_patterns = [
        r'\s*[\(\[]\s*original\s+motion\s+picture\s+soundtrack\s*[\)\]]',
        r'\s*[\(\[]\s*motion\s+picture\s+soundtrack\s*[\)\]]',
        r'\s*[\(\[]\s*from\s+"[^"]*"\s*[\)\]]',
        r'\s*[\(\[]\s*from\s+[^\)\]]+[\)\]]',
        r'\s*[\(\[]\s*ost\s+[^\)\]]*[\)\]]',
        r'\s*[\(\[]\s*ost\s*[\)\]]',
        r'\s*[\(\[]\s*soundtrack\s*[\)\]]',
    ]
    for pattern in ost_patterns:
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
    
    # Remove edition markers like "Deluxe Edition", "(Remastered)", etc.
    normalized = re.sub(r'\s*\(?(?:deluxe|standard|explicit|clean|remaster|remastered|edition|ed\.)\)?', '', normalized, flags=re.IGNORECASE)
    
    return normalized.strip()


def parse_duration_to_ms(duration: Optional[int]) -> Optional[int]:
    """
    Parse duration to milliseconds.
    
    Args:
        duration: Duration value (could be ms or seconds depending on source)
        
    Returns:
        Duration in milliseconds, or None if invalid
    """
    if not duration:
        return None
    
    if duration < 0:
        return None
    
    # If duration looks like it's in seconds (< 3600 seconds = 1 hour max)
    # Spotify uses ms, Plex uses ms, but some providers might use seconds
    # Heuristic: if value is < 3600000ms (1 hour), assume it's correct
    if duration < 3600000:
        # Could be either. Check if < 3600 (1 hour in seconds)
        if duration < 3600:
            # Likely seconds, convert to ms
            return duration * 1000
    
    return duration


def extract_version_info(title: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Extract version info from title.
    
    Examples:
        "Song (Remix)" -> ("Song", "Remix")
        "Song - Live Version" -> ("Song", "Live")
        "Song [Radio Edit]" -> ("Song", "Radio Edit")
        "Song - Live at SiriusXM" -> ("Song", "Live at SiriusXM")
        "Song - Gabry Ponte Ice Pop Radio" -> ("Song", "Gabry Ponte Ice Pop Radio")
        
    Args:
        title: Track title potentially containing version info
        
    Returns:
        Tuple of (clean_title, version_string or None)
    """
    if not title:
        return "", None
    
    VERSION_PATTERNS = [
        # Parentheses with version keywords
        (r'\s*\(([^)]*(?:remix|version|edit|live|acoustic|instrumental|remaster|radio|mix|club)[^)]*)\)', 1),
        # Square brackets with version keywords  
        (r'\s*\[([^\]]*(?:remix|version|edit|live|acoustic|instrumental|remaster|radio|mix|club)[^\]]*)\]', 1),
        # Dash followed by version keywords (including "Live at X", "Radio", remixer names)
        (r'\s*-\s*([^-]*(?:remix|version|edit|live at|live|acoustic|instrumental|remaster|radio|mix|club)[^-]*)$', 1),
        # Dash followed by remixer/producer name + "Radio/Edit/Mix/Remix" pattern (e.g., "- Gabry Ponte Ice Pop Radio")
        (r'\s*-\s*((?:[A-Z][a-z]+\s+)*(?:Radio|Edit|Mix|Remix|Version)[^-]*)$', 1),
    ]
    
    for pattern, group in VERSION_PATTERNS:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            version = match.group(group).strip()
            clean_title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()
            return clean_title, version
    
    return title, None


# ---------------------------------------------------------------------------
# Base-String Helpers (Dual-Pass matching support)
# ---------------------------------------------------------------------------

# Keywords that indicate a *different recording* and must NOT be silently
# stripped when computing a simplified base string for fuzzy matching.
# If any of these appear inside parentheticals or after a hyphen, the original
# title/artist string is returned *unchanged* to prevent false-positive matches
# such as "Song (Remix)" falsely collapsing to "Song".
_BASE_STRIP_VERSION_KEYWORDS: frozenset = frozenset({
    'remix', 'mix', 'edit', 'extended', 'live', 'acoustic', 'vip', 'instrumental',
})

_PAREN_CONTENT_RE = re.compile(r'[\(\[](.*?)[\)\]]')
_HYPHEN_SUFFIX_RE = re.compile(r'\s*-\s*(.+)$')


def generate_base_string(text: str) -> str:
    """
    Return a simplified 'base string' for Dual-Pass fuzzy matching by stripping
    parentheticals and hyphen suffixes — but ONLY when none of the stripped
    content contains version keywords (remix, mix, edit, extended, live,
    acoustic, vip, instrumental).

    If ANY version keyword is found in a parenthetical or hyphen suffix, the
    *original* string is returned unchanged.  This prevents "Song (Remix)"
    from collapsing to "Song" and creating a false positive match against the
    original recording.

    Examples that ARE safely stripped:
        "Sunflower (Spider-Man: Into the Spider-Verse)" → "Sunflower"
        "Song - From 'Movie'"                           → "Song"
        "Song (2015 Remaster)"                          → "Song"

    Examples that are PRESERVED (keyword guard triggers):
        "Song (Remix)"          → "Song (Remix)"
        "Song - Extended Mix"   → "Song - Extended Mix"
        "Song - Radio Edit"     → "Song - Radio Edit"
        "Song (Live)"           → "Song (Live)"
        "Song - VIP Mix"        → "Song - VIP Mix"
    """
    if not text:
        return ""

    # ── Phase 1: check all parenthetical / bracket groups ────────────────────
    for m in _PAREN_CONTENT_RE.finditer(text):
        content_lower = m.group(1).lower()
        if any(kw in content_lower for kw in _BASE_STRIP_VERSION_KEYWORDS):
            return text  # version keyword detected – preserve original

    # Strip parentheticals (confirmed safe: none contained a version keyword)
    stripped = _PAREN_CONTENT_RE.sub('', text).strip()

    # ── Phase 2: check the hyphen suffix on the now-stripped result ───────────
    hyphen_match = _HYPHEN_SUFFIX_RE.search(stripped)
    if hyphen_match:
        suffix_lower = hyphen_match.group(1).lower()
        if any(kw in suffix_lower for kw in _BASE_STRIP_VERSION_KEYWORDS):
            return text  # version keyword in hyphen suffix – preserve original

    # Strip hyphen suffix (confirmed safe)
    stripped = _HYPHEN_SUFFIX_RE.sub('', stripped).strip()

    # Guard: never return an empty string (degenerate input)
    return stripped if stripped else text


def detect_quality_tags(bitrate: Optional[int], file_format: Optional[str]) -> list:
    """
    Detect quality tags from bitrate and format.
    
    Args:
        bitrate: Bitrate in kbps
        file_format: File format (mp3, flac, m4a, etc.)
        
    Returns:
        List of quality tags
    """
    tags = []
    
    if not file_format:
        return tags
    
    file_format = file_format.lower()
    
    # Format-based detection
    if file_format == 'flac':
        tags.append('FLAC')
        tags.append('Lossless')
    elif file_format == 'm4a' or file_format == 'aac':
        tags.append('AAC')
    elif file_format == 'mp3':
        tags.append('MP3')
        if bitrate and bitrate >= 320:
            tags.append('320kbps')
        elif bitrate and bitrate >= 256:
            tags.append('256kbps')
        elif bitrate and bitrate >= 192:
            tags.append('192kbps')
        elif bitrate:
            tags.append(f'{bitrate}kbps')
    elif file_format == 'ogg' or file_format == 'oga':
        tags.append('OGG Vorbis')
    elif file_format == 'opus':
        tags.append('Opus')
    elif file_format == 'alac':
        tags.append('ALAC')
    elif file_format == 'wma':
        tags.append('WMA')
    
    return tags


def clean_guid_id(guid_id: str) -> Optional[str]:
    """
    Extract clean ID from Plex guid format.
    
    Examples:
        "com.plexapp.agents.isrc://USRC12345678" -> "USRC12345678"
        "musicbrainz://recording/12345678-1234-1234-1234-123456789012" -> "12345678-1234-1234-1234-123456789012"
        
    Args:
        guid_id: Full guid ID string
        
    Returns:
        Clean ID without prefix, or None if invalid
    """
    if not guid_id or '://' not in guid_id:
        return None
    
    try:
        _, identifier = guid_id.split('://', 1)
        return identifier.strip() if identifier else None
    except (ValueError, IndexError):
        return None


def extract_edition(title: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Extract edition information from track/album title.

    Detects edition keywords like: remaster, remastered, live, remix, deluxe,
    acoustic, original, explicit, clean, extended, radio edit, instrumental, etc.

    Args:
        title: Track or album title potentially containing edition info

    Returns:
        Tuple of (cleaned_title, edition_string)
        - cleaned_title: Title with edition keywords removed
        - edition_string: Detected edition (e.g., "Remastered", "Live", "Deluxe") or None

    Examples:
        "Song Title (Remastered 2015)" -> ("Song Title", "Remastered")
        "Live at Wembley" -> ("at Wembley", "Live")
        "Deluxe Edition" -> ("", "Deluxe")
        "Acoustic Version" -> ("", "Acoustic")
        "Song - Radio Edit" -> ("Song", "Radio Edit")
    """
    if not title:
        return ("", None)

    # Edition keywords to detect (case-insensitive)
    EDITION_PATTERNS = [
        # Remaster variants
        (r'\b(remaster(?:ed)?)\b', 'Remastered'),
        (r'\b(remastering)\b', 'Remastered'),

        # Live variants
        (r'\b(live)\b', 'Live'),

        # Remix variants
        (r'\b(remix(?:ed)?)\b', 'Remix'),
        (r'\b(rmx)\b', 'Remix'),

        # Album editions
        (r'\b(deluxe)\s*(?:edition)?\b', 'Deluxe'),
        (r'\b(standard)\s*(?:edition)?\b', 'Standard'),
        (r'\b(expanded)\s*(?:edition)?\b', 'Expanded'),
        (r'\b(limited)\s*(?:edition)?\b', 'Limited'),
        (r'\b(special)\s*(?:edition)?\b', 'Special'),
        (r'\b(anniversary)\s*(?:edition)?\b', 'Anniversary'),
        (r'\b(collector\'?s?)\s*(?:edition)?\b', 'Collectors'),

        # Content type
        (r'\b(explicit)\b', 'Explicit'),
        (r'\b(clean)\b', 'Clean'),
        (r'\b(instrumental)\b', 'Instrumental'),
        (r'\b(acapella|a\s*cappella)\b', 'Acapella'),
        (r'\b(acoustic)\b', 'Acoustic'),
        (r'\b(unplugged)\b', 'Unplugged'),

        # Version types
        (r'\b(original)\s*(?:version|mix)?\b', 'Original'),
        (r'\b(radio)\s*(?:edit|version|mix)?\b', 'Radio Edit'),
        (r'\b(extended)\s*(?:version|mix)?\b', 'Extended'),
        (r'\b(club)\s*(?:version|mix)?\b', 'Club Mix'),
        (r'\b(album)\s*(?:version)?\b', 'Album Version'),
        (r'\b(single)\s*(?:version)?\b', 'Single Version'),

        # Quality indicators
        (r'\b(24\s*bit)\b', '24-bit'),
        (r'\b(16\s*bit)\b', '16-bit'),
        (r'\b(hi\s*res|high\s*resolution)\b', 'Hi-Res'),
    ]

    title_lower = title.lower()
    detected_editions = []
    cleaned_title = title

    # Check each pattern
    for pattern, edition_name in EDITION_PATTERNS:
        match = re.search(pattern, title_lower, re.IGNORECASE)
        if match:
            detected_editions.append(edition_name)
            # Remove the matched text from title (case-insensitive)
            cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE)

    # Clean up the title: remove extra spaces, parentheses, brackets, dashes
    cleaned_title = re.sub(r'\s*[\(\[\{]\s*[\)\]\}]\s*', ' ', cleaned_title)  # Empty brackets
    cleaned_title = re.sub(r'\s*[-–—]\s*$', '', cleaned_title)  # Trailing dashes
    cleaned_title = re.sub(r'^\s*[-–—]\s*', '', cleaned_title)  # Leading dashes
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()

    # Return cleaned title and first detected edition (prioritize first match)
    edition = detected_editions[0] if detected_editions else None

    return (cleaned_title, edition)

def generate_deterministic_id(artist: Optional[str], title: Optional[str]) -> str:
    """
    Generate a deterministic, base64-encoded cache ID for a track.
    
    Utilizes advanced text normalization to ensure consistent cache hits 
    despite 'feat', '&', or special character variations.
    """
    # Use the existing robust normalization
    norm_artist = normalize_artist(artist)
    norm_title = normalize_title(title)
    
    # Fallbacks in case normalization returns empty strings
    safe_artist = norm_artist if norm_artist else "unknown"
    safe_title = norm_title if norm_title else "unknown"
    
    # Format string matching the cache_manager requirement
    raw_id = f"{safe_artist}|{safe_title}"
    return base64.b64encode(raw_id.encode('utf-8')).decode('utf-8')