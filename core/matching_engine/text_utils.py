"""
Text normalization and parsing utilities for track metadata.

These functions are provider-agnostic and reused by all providers
to normalize track data before creating SoulSyncTrack objects.
"""

import re
from typing import Optional, Tuple
import base64



def normalize_chars(text: Optional[str]) -> str:
    """
    Normalize Unicode character variants to their plain ASCII canonical equivalents.

    This is a lightweight, case-preserving, structure-preserving pass — no lowercasing,
    no accent removal, no word removal.  It is safe to apply to display-facing strings
    and is called from SoulSyncTrack.__post_init__ so that EVERY track (whether created
    from a streaming provider or from a raw DB row) carries consistent characters before
    entering the matching engine or SQL search layer.

    Covered categories
    ------------------
    Apostrophes / single-quote variants → plain apostrophe (U+0027)
        U+2018  LEFT SINGLE QUOTATION MARK       '
        U+2019  RIGHT SINGLE QUOTATION MARK      '
        U+02BC  MODIFIER LETTER APOSTROPHE       ʼ
        U+02BB  MODIFIER LETTER TURNED COMMA     ʻ
        U+2032  PRIME                            ′
        U+0060  GRAVE ACCENT                     `
        U+00B4  ACUTE ACCENT                     ´
        U+FF07  FULLWIDTH APOSTROPHE             ＇

    Dashes / hyphens → standard hyphen-minus (U+002D)
        U+2010  HYPHEN                           ‐
        U+2011  NON-BREAKING HYPHEN              ‑
        U+2012  FIGURE DASH                      ‒
        U+2013  EN DASH                          –
        U+2014  EM DASH                          —
        U+2015  HORIZONTAL BAR                   ―
        U+2212  MINUS SIGN                       −
        U+FE63  SMALL HYPHEN-MINUS               ﹣
        U+FF0D  FULLWIDTH HYPHEN-MINUS           －
        U+2043  HYPHEN BULLET                    ⁃

    Double quotes → plain double quote (U+0022)
        U+201C  LEFT DOUBLE QUOTATION MARK       "
        U+201D  RIGHT DOUBLE QUOTATION MARK      "
        U+201E  DOUBLE LOW-9 QUOTATION MARK      „
        U+201F  DOUBLE HIGH-REVERSED-9 Q. MARK   ‟
        U+2033  DOUBLE PRIME                     ″

    Whitespace variants → regular space (U+0020)
        U+00A0  NO-BREAK SPACE
        U+202F  NARROW NO-BREAK SPACE
        U+2009  THIN SPACE
        U+2008  PUNCTUATION SPACE
        U+2007  FIGURE SPACE
        U+2006  SIX-PER-EM SPACE
        U+2005  FOUR-PER-EM SPACE
        U+2004  THREE-PER-EM SPACE
        U+2003  EM SPACE
        U+2002  EN SPACE

    Ellipsis
        U+2026  HORIZONTAL ELLIPSIS → '...'
    """
    if not text:
        return text or ""

    # Apostrophe / single-quote variants → plain apostrophe
    text = re.sub(r"[\u2018\u2019\u02bc\u02bb\u2032\u0060\u00b4\uff07]", "'", text)

    # Dash / hyphen variants → standard hyphen-minus
    text = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe63\uff0d\u2043]", "-", text)

    # Double quote variants → plain double quote
    text = re.sub(r"[\u201c\u201d\u201e\u201f\u2033]", '"', text)

    # Whitespace variants → regular space
    text = re.sub(r"[\u00a0\u202f\u2009\u2008\u2007\u2006\u2005\u2004\u2003\u2002]", " ", text)

    # Ellipsis → three dots
    text = text.replace("\u2026", "...")

    return text


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

    # Allow plugins (e.g. CJK Language Pack) to transliterate non-Latin scripts
    # into their Latin-script equivalents *before* the ASCII-folding pass below.
    # If no plugin registers this hook the text is returned unchanged.
    from core.hook_manager import hook_manager
    text = hook_manager.apply_filters('pre_normalize_text', text)

    # Standardize all Unicode character variants (smart quotes, fancy dashes, etc.)
    text = normalize_chars(text)

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