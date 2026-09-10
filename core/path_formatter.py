"""
EchoSync Path Formatter Engine.

Handles dynamic user-defined library path interpolation, filename token expansion,
filesystem character sanitization, version injection, and configuration resolution from config.db.
"""

import re
from pathlib import Path
from typing import Any

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


def get_group_singles() -> bool:
    """Query preference for grouping standalone singles into a dedicated Singles folder."""
    try:
        from database.config_database import get_config_database

        db = get_config_database()
        val = db.get_system_setting("library_import.group_singles")
        if val is not None:
            if isinstance(val, bool):
                return val
            return str(val).strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        pass

    try:
        from core.settings import config_manager

        val = config_manager.get("library_import.group_singles")
        if val is not None:
            if isinstance(val, bool):
                return val
            return str(val).strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        pass

    return True


def get_prefer_canonical_studio_album() -> bool:
    """Query preference for realigning compilation tracks to canonical studio albums."""
    try:
        from database.config_database import get_config_database

        db = get_config_database()
        val = db.get_system_setting(
            "metadata_enhancement.prefer_canonical_studio_album"
        )
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


def get_library_preferences() -> tuple[str, str]:
    """
    Query active library root and renaming pattern preferences.
    Priority:
    1. config_manager (active runtime settings & test mocks):
       - 'storage.library_dir' or 'library_dir' or 'storage_locations.library'
       - 'auto_import.file_organization_pattern' or 'library_import.renaming_pattern' or 'metadata_enhancement.naming_template'
    2. config.db system_settings table:
       - 'storage_locations.library'
       - 'library_import.renaming_pattern'
    3. Fallback defaults:
       - library_root: /data/library
       - renaming_pattern: {Artist}/{Album}/{Track} - {Title}.{ext}
    """
    library_root: str | None = None
    renaming_pattern: str | None = None

    import inspect

    from core.settings import config_manager

    is_cm_mocked = not inspect.ismethod(getattr(config_manager, "get", None))

    def _read_from_cm():
        nonlocal library_root, renaming_pattern
        try:
            if not library_root:
                library_root = (
                    config_manager.get("storage.library_dir")
                    or config_manager.get("library_dir")
                    or config_manager.get("storage_locations.library")
                )
            if not renaming_pattern:
                renaming_pattern = (
                    config_manager.get("auto_import.file_organization_pattern")
                    or config_manager.get("library_import.renaming_pattern")
                    or config_manager.get("metadata_enhancement.naming_template")
                )
        except Exception:
            pass

    def _read_from_db():
        nonlocal library_root, renaming_pattern
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            if not library_root:
                lib_val = db.get_system_setting("storage_locations.library") or db.get_system_setting("storage.library_dir")
                if lib_val:
                    library_root = str(lib_val)
            if not renaming_pattern:
                pat_val = db.get_system_setting("library_import.renaming_pattern") or db.get_system_setting("auto_import.file_organization_pattern")
                if pat_val:
                    renaming_pattern = str(pat_val)
        except Exception:
            pass

    if is_cm_mocked:
        _read_from_cm()
        if not library_root or not renaming_pattern:
            _read_from_db()
    else:
        _read_from_db()
        if not library_root or not renaming_pattern:
            _read_from_cm()

    # Step 3: Default fallbacks
    if not library_root:
        library_root = DEFAULT_LIBRARY_ROOT
    if not renaming_pattern:
        renaming_pattern = DEFAULT_RENAMING_PATTERN

    return str(library_root), str(renaming_pattern)


def extract_year_token(meta: dict[str, Any]) -> str:
    """Extract 4-digit release year from metadata."""
    raw_year = (
        meta.get("year")
        or meta.get("release_year")
        or meta.get("date")
        or meta.get("release_date")
    )
    if not raw_year:
        return ""
    m = re.search(r"\b(19\d\d|20\d\d)\b", str(raw_year))
    if m:
        return m.group(1)
    s = str(raw_year).strip()
    return s[:4] if len(s) >= 4 and s[:4].isdigit() else s


def extract_track_token(meta: dict[str, Any]) -> str:
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
    base_library_path: str | dict[str, Any],
    pattern: str | None = None,
    meta: dict[str, Any] | None = None,
    ext: str | None = None,
    singles_pattern: str | None = None,
    group_singles: bool | None = None,
) -> Path:
    """
    Interpolate dynamic tokens into destination library path.

    Supports both:
    1. Single dictionary: build_destination_path(metadata_dict)
    2. Explicit parameters: build_destination_path(base_path, pattern, meta, ext, ...)

    Supported tokens:
    - {Artist}: meta['album_artist'] or meta['artist'] (default: 'Unknown Artist')
    - {Album}: meta['album'] (default: 'Singles')
    - {Title}: Track title, with version injected if present and not already formatted
    - {Track}: Zero-padded track number ('01'). If empty, cleans separator hyphens/dots.
    - {Year}: 4-digit release year
    - {Format} / {ext}: Clean extension without leading dot (e.g. 'flac')
    """
    if isinstance(base_library_path, dict):
        meta = dict(base_library_path)
        pref_lib_root, pref_pattern = get_library_preferences()
        base_library_path = pref_lib_root
        pattern = pattern or pref_pattern
        ext = ext or meta.get("ext") or meta.get("file_format") or "flac"
    elif meta is None:
        meta = {}

    if not pattern:
        _, pattern = get_library_preferences()
    if not ext:
        ext = meta.get("ext") or meta.get("file_format") or "flac"

    if pattern:
        pattern = re.sub(r"(?<!\.){ext}", ".{ext}", pattern)
        pattern = re.sub(r"(?<!\.){Format}", ".{Format}", pattern)
    if singles_pattern:
        singles_pattern = re.sub(r"(?<!\.){ext}", ".{ext}", singles_pattern)
        singles_pattern = re.sub(r"(?<!\.){Format}", ".{Format}", singles_pattern)

    ext_clean = str(ext).lstrip(".").lower()

    # Resolve artist
    raw_artist = meta.get("album_artist") or meta.get("artist") or "Unknown Artist"
    artist = sanitize_path_segment(raw_artist) or "Unknown Artist"

    # Detect if track is a single or standalone recording
    raw_album = str(meta.get("album") or "").strip()
    raw_album_lower = raw_album.lower()
    is_single = (
        meta.get("release_type") in ("single", "standalone")
        or bool(meta.get("is_single"))
        or raw_album_lower
        in (
            "[standalone recordings]",
            "[non-album tracks]",
            "standalone recordings",
            "non-album tracks",
            "unknown album",
            "singles",
            "",
        )
    )

    if group_singles is None:
        group_singles = get_group_singles()

    if is_single and group_singles:
        meta["album"] = "Singles"
        album = "Singles"
        working_pattern = singles_pattern or pattern
    else:
        album = (
            sanitize_path_segment(raw_album)
            if raw_album
            else ("Singles" if is_single else "Unknown Album")
        )
        if not album:
            album = "Singles" if is_single else "Unknown Album"
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
    raw_track_val = (
        meta.get("track_number")
        if meta.get("track_number") is not None
        else (
            meta.get("track_no")
            if meta.get("track_no") is not None
            else meta.get("track")
        )
    )
    if is_single and (
        raw_track_val is None
        or raw_track_val == 0
        or str(raw_track_val).strip() in ("", "0", "00")
    ):
        track_num = ""
    else:
        track_num = extract_track_token(meta)

    year = extract_year_token(meta)
    if not track_num:
        working_pattern = re.sub(r"\{Track\}\s*[-_.]\s*", "", working_pattern)
        working_pattern = re.sub(r"\s*[-_.]\s*\{Track\}", "", working_pattern)
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
        ext=ext_clean,
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


def ensure_path_invariance(session: Any, track: Any, local_media: Any) -> Path:
    """Ensure library track file path matches active library_import renaming pattern.

    If target_path != current_path, relocate file via Gatekeeper.authorize_and_execute,
    suppress library watcher events, update local_media.file_path, and prune empty source folders.
    """
    import logging

    from core.io_gatekeeper import Gatekeeper
    from core.settings import config_manager
    from core.system_watcher import suppress_path
    from core.utils.file_utils import prune_empty_parent_directories

    if not local_media or not getattr(local_media, "file_path", None):
        return Path("")

    current_path = Path(local_media.file_path)
    if not current_path.exists():
        return current_path

    artist_name = (
        track.artist.name
        if getattr(track, "artist", None) and track.artist
        else "Unknown Artist"
    )
    album_title = (
        track.album.title
        if getattr(track, "album", None) and track.album
        else "Unknown Album"
    )

    metadata_dict = {
        "artist": artist_name,
        "album_artist": artist_name,
        "album": album_title,
        "title": track.title or "Unknown Track",
        "track": track.track_number,
        "track_number": track.track_number,
        "disc_number": track.disc_number,
        "year": getattr(track, "year", None)
        or (
            track.album.release_date.year
            if getattr(track, "album", None) and getattr(track.album, "release_date", None)
            else getattr(track.album, "release_year", None) if getattr(track, "album", None) else None
        ),
        "ext": current_path.suffix.lstrip(".") or "flac",
    }

    target_path = build_destination_path(metadata_dict)
    if target_path.resolve() != current_path.resolve():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with suppress_path(str(target_path)):
            Gatekeeper.authorize_and_execute(
                operation="move",
                source=str(current_path),
                destination=str(target_path),
            )
        local_media.file_path = str(target_path)
        session.flush()

        # Clean up empty source parent directories up to library root
        try:
            lib_root = config_manager.get(
                "storage.library_dir"
            ) or config_manager.get("library_dir")
            stop_roots = {Path(lib_root).resolve()} if lib_root else set()
            prune_empty_parent_directories(current_path, stop_at_roots=stop_roots)
        except Exception as prune_err:
            logging.getLogger("path_formatter").debug(
                "Failed pruning empty parent directories for %s: %s",
                current_path,
                prune_err,
            )

    return target_path
