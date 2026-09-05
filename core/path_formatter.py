"""
EchoSync Path Formatter Engine.

Handles dynamic user-defined library path interpolation, filename token expansion,
filesystem character sanitization, version injection, and configuration resolution from config.db.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

DEFAULT_LIBRARY_ROOT = "/data/library"
DEFAULT_RENAMING_PATTERN = "{Artist}/{Album}/{Track} - {Title}.{ext}"
DEFAULT_SINGLES_PATTERN = "{Artist}/Singles/{Track} - {Title}.{ext}"


def sanitize_path_segment(segment: str) -> str:
    """
    Sanitize a single path component (folder name or filename) for OS filesystem safety.
    Removes invalid characters: \\ / * ? : " < > |
    Also trims leading and trailing dots and whitespace.
    """
    if not segment:
        return ""
    # Strip illegal characters across Windows and POSIX filesystems
    cleaned = re.sub(r'[\\/*?:"<>|]', "", str(segment))
    # Strip leading/trailing dots and spaces which are illegal/problematic on Windows
    cleaned = cleaned.strip(". ")
    return cleaned


def get_singles_pattern() -> str:
    """Query active singles path pattern preference."""
    try:
        from database.config_database import get_config_database
        db = get_config_database()
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT value FROM system_settings WHERE key = 'library_import.singles_pattern'")
            row = c.fetchone()
            if row and row[0]:
                val = row[0]
                if isinstance(val, str) and val.startswith('"') and val.endswith('"'):
                    import json
                    try:
                        val = json.loads(val)
                    except Exception:
                        pass
                return str(val)
        val = db.get_system_setting("library_import.singles_pattern")
        if val:
            return str(val)
    except Exception:
        pass

    try:
        from core.settings import config_manager
        val = config_manager.get("library_import.singles_pattern")
        if val:
            return str(val)
    except Exception:
        pass

    return DEFAULT_SINGLES_PATTERN


def get_prefer_canonical_studio_album() -> bool:
    """Query preference for realigning compilation tracks to canonical studio albums."""
    try:
        from database.config_database import get_config_database
        db = get_config_database()
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT value FROM system_settings WHERE key = 'metadata_enhancement.prefer_canonical_studio_album'")
            row = c.fetchone()
            if row and row[0]:
                val = str(row[0]).strip().lower()
                return val in ("1", "true", "yes", "on")
        val = db.get_system_setting("metadata_enhancement.prefer_canonical_studio_album")
        if val is not None:
            if isinstance(val, bool):
                return val
            return str(val).strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        pass

    try:
        from core.settings import config_manager
        val = config_manager.get("metadata_enhancement.prefer_canonical_studio_album")
        if val is not None:
            if isinstance(val, bool):
                return val
            return str(val).strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        pass

    return True


def get_library_preferences() -> Tuple[str, str]:
    """
    Query active library root and renaming pattern preferences.
    Priority:
    1. config.db system_settings table:
       - 'storage_locations.library'
       - 'library_import.renaming_pattern'
    2. config_manager / config.json:
       - 'storage_locations.library' or 'storage.library_dir'
       - 'library_import.renaming_pattern' or 'metadata_enhancement.naming_template'
    3. Fallback defaults:
       - library_root: /data/library
       - renaming_pattern: {Artist}/{Album}/{Track} - {Title}.{ext}
    """
    library_root: Optional[str] = None
    renaming_pattern: Optional[str] = None

    # Step 1: Try reading from config.db (system_settings)
    try:
        from database.config_database import get_config_database
        db = get_config_database()
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT key, value FROM system_settings WHERE key IN ('storage_locations.library', 'library_import.renaming_pattern')")
            rows = dict(c.fetchall())
            if rows.get("storage_locations.library"):
                val = rows["storage_locations.library"]
                if isinstance(val, str) and val.startswith('"') and val.endswith('"'):
                    import json
                    try:
                        val = json.loads(val)
                    except Exception:
                        pass
                library_root = str(val)
            if rows.get("library_import.renaming_pattern"):
                val = rows["library_import.renaming_pattern"]
                if isinstance(val, str) and val.startswith('"') and val.endswith('"'):
                    import json
                    try:
                        val = json.loads(val)
                    except Exception:
                        pass
                renaming_pattern = str(val)
        lib_val = db.get_system_setting("storage_locations.library")
        if lib_val:
            library_root = str(lib_val)
        pat_val = db.get_system_setting("library_import.renaming_pattern")
        if pat_val:
            renaming_pattern = str(pat_val)
    except Exception:
        pass

    # Step 2: Fallback to config_manager
    try:
        from core.settings import config_manager
        if not library_root:
            library_root = (
                config_manager.get("storage_locations.library")
                or config_manager.get("storage.library_dir")
            )
        if not renaming_pattern:
            renaming_pattern = (
                config_manager.get("library_import.renaming_pattern")
                or config_manager.get("metadata_enhancement.naming_template")
            )
    except Exception:
        pass

    # Step 3: Default fallbacks
    if not library_root:
        library_root = DEFAULT_LIBRARY_ROOT
    if not renaming_pattern:
        renaming_pattern = DEFAULT_RENAMING_PATTERN

    return str(library_root), str(renaming_pattern)


def extract_year_token(meta: Dict[str, Any]) -> str:
    """Extract 4-digit release year from metadata."""
    raw_year = meta.get("year") or meta.get("release_year") or meta.get("date") or meta.get("release_date")
    if not raw_year:
        return ""
    m = re.search(r"\b(19\d\d|20\d\d)\b", str(raw_year))
    if m:
        return m.group(1)
    s = str(raw_year).strip()
    return s[:4] if len(s) >= 4 and s[:4].isdigit() else s


def extract_track_token(meta: Dict[str, Any]) -> str:
    """Extract zero-padded track number, or empty string if absent."""
    raw_track = meta.get("track_number") or meta.get("track_no") or meta.get("track")
    if raw_track is None:
        return ""
    s = str(raw_track).split("/")[0].strip()
    if not s:
        return ""
    try:
        val = int(s)
        return str(val).zfill(2)
    except ValueError:
        return s


def build_destination_path(
    base_library_path: str,
    pattern: str,
    meta: Dict[str, Any],
    ext: str,
    singles_pattern: Optional[str] = None
) -> Path:
    """
    Interpolate dynamic tokens into destination library path.

    Supported tokens:
    - {Artist}: meta['album_artist'] or meta['artist'] (default: 'Unknown Artist')
    - {Album}: meta['album'] (default: 'Singles')
    - {Title}: Track title, with version injected if present and not already formatted
    - {Track}: Zero-padded track number ('01'). If empty, cleans separator hyphens/dots.
    - {Year}: 4-digit release year
    - {Format} / {ext}: Clean extension without leading dot (e.g. 'flac')
    """
    ext_clean = ext.lstrip(".").lower()

    # Resolve artist
    raw_artist = meta.get("album_artist") or meta.get("artist") or "Unknown Artist"
    artist = sanitize_path_segment(raw_artist) or "Unknown Artist"

    # Detect if track is a single or standalone recording
    raw_album = str(meta.get("album") or "").strip()
    raw_album_lower = raw_album.lower()
    is_single = (
        meta.get("release_type") in ("single", "standalone")
        or bool(meta.get("is_single"))
        or raw_album_lower in (
            "[standalone recordings]",
            "[non-album tracks]",
            "standalone recordings",
            "non-album tracks",
            "unknown album",
            "singles",
            ""
        )
    )

    if is_single:
        album = "Singles"
        working_pattern = singles_pattern or get_singles_pattern()
    else:
        album = sanitize_path_segment(raw_album) if raw_album else "Singles"
        if not album:
            album = "Singles"
        working_pattern = pattern

    # Resolve title and version injection
    raw_title = meta.get("title") or "Unknown Track"
    version = meta.get("version") or meta.get("subtitle") or meta.get("edition")
    if version:
        version_clean = str(version).strip()
        if version_clean and version_clean.lower() not in raw_title.lower():
            raw_title = f"{raw_title} ({version_clean})"

    title = sanitize_path_segment(raw_title) or "Unknown Track"

    # Resolve track & year
    track_num = extract_track_token(meta)
    if is_single and track_num in ("00", "0"):
        track_num = ""
    year = extract_year_token(meta)
    if not track_num:
        working_pattern = re.sub(r"\{Track\}\s*[-_.]\s*", "", working_pattern)
        working_pattern = working_pattern.replace("{Track}", "")

    if not year:
        working_pattern = re.sub(r"\(\s*\{Year\}\s*\)", "", working_pattern)
        working_pattern = re.sub(r"\[\s*\{Year\}\s*\]", "", working_pattern)
        working_pattern = re.sub(r"\{Year\}\s*[-_.]\s*", "", working_pattern)
        working_pattern = working_pattern.replace("{Year}", "")

    rel_path_str = working_pattern.format(
        Artist=artist,
        Album=album,
        Title=title,
        Track=track_num,
        Year=year,
        Format=ext_clean,
        ext=ext_clean
    )

    segments = re.split(r"[\\/]+", rel_path_str.strip("\\/"))
    cleaned_segments = []
    for seg in segments:
        s = sanitize_path_segment(seg)
        s = re.sub(r"^[-_.]\s*", "", s).strip()
        if s:
            cleaned_segments.append(s)

    if not cleaned_segments:
        cleaned_segments = [f"{title}.{ext_clean}"]

    filename = cleaned_segments[-1]
    if not filename.lower().endswith(f".{ext_clean}"):
        cleaned_segments[-1] = f"{filename}.{ext_clean}"

    return Path(base_library_path).joinpath(*cleaned_segments)
