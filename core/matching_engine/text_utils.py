"""
Text normalization and parsing utilities for track metadata.

These functions are provider-agnostic and reused by all providers
to normalize track data before creating SoulSyncTrack objects.
"""

import re
from typing import Optional, Tuple


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
    
    # Convert to lowercase
    text = text.lower().strip()
    
    # Normalize unicode characters (é -> e, ñ -> n, etc.)
    text = remove_accents(text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text


def remove_accents(text: str) -> str:
    """Remove diacritical marks from text."""
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def normalize_title(title: Optional[str]) -> str:
    """
    Normalize track title for matching.
    
    - Lowercase
    - Remove accents
    - Remove extra spaces
    - Keep alphanumeric + common punctuation
    """
    if not title:
        return ""
    
    normalized = normalize_text(title)
    # Keep alphanumeric, spaces, hyphens, parentheses, quotes
    normalized = re.sub(r'[^\w\s\-\(\)\'\"]', '', normalized)
    
    return normalized.strip()


def normalize_artist(artist: Optional[str]) -> str:
    """
    Normalize artist name for matching.
    
    - Lowercase
    - Remove accents
    - Remove "feat.", "ft.", "featuring" markers (keep artist names)
    - Remove extra spaces
    """
    if not artist:
        return ""
    
    normalized = normalize_text(artist)
    
    # Remove common feat/ft markers and everything after
    # e.g., "Artist feat. Another" -> "Artist"
    normalized = re.sub(r'\s*(?:feat\.|featuring|ft\.?|with).*$', '', normalized, flags=re.IGNORECASE)
    
    return normalized.strip()


def normalize_album(album: Optional[str]) -> str:
    """
    Normalize album name for matching.
    
    - Lowercase
    - Remove accents
    - Remove "deluxe", "remaster", edition markers
    - Remove extra spaces
    """
    if not album:
        return ""
    
    normalized = normalize_text(album)
    
    # Remove edition markers like "Deluxe Edition", "(Remastered)", etc.
    # But keep them for matching purposes - just normalize the format
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
        
    Args:
        title: Track title potentially containing version info
        
    Returns:
        Tuple of (clean_title, version_string or None)
    """
    if not title:
        return "", None
    
    VERSION_PATTERNS = [
        (r'\s*\(([^)]*(?:remix|version|edit|live|acoustic|instrumental|remaster)[^)]*)\)', 1),
        (r'\s*\[([^\]]*(?:remix|version|edit|live|acoustic|instrumental|remaster)[^\]]*)\]', 1),
        (r'\s*-\s*([^-]*(?:remix|version|edit|live|acoustic|instrumental|remaster)[^-]*)$', 1),
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
