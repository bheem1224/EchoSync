"""
core/file_handling/audio_inspector.py — Centralised audio file inspection

Single authoritative entry-point for reading metadata from local audio files.
All other modules (plugins, services, web routes) MUST delegate to this module
instead of importing mutagen, tinytag, or taglib directly.

Public API
----------
inspect_audio_file(file_path)
    Read an audio file and return a rich InspectedAudio dataclass.

SUPPORTED_AUDIO_EXTENSIONS
    Canonical set of audio file extensions understood by this inspector.

Design
------
- Fail-open: every field is Optional; a parse failure in one field never
  prevents the caller receiving a partial result for the others.
- Artist Resolver Hierarchy (in priority order):
    1. TPE1 / ARTIST tag (track artist) — if non-empty and not generic.
    2. TPE2 / ALBUMARTIST tag           — if non-empty and not generic.
    3. Path/filename heuristic          — e.g. <Artist>/<Album>/<track> or
                                          <Artist> - <Title>.<ext>.
    4. Hard default: "Various Artists".
- Duration is always returned as integer milliseconds (ms).
- track_number / disc_number always returned as Optional[int] via
  text_utils.parse_int_safe, handling '2/9', '02', list values, etc.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from core.tiered_logger import get_logger
from core.matching_engine import text_utils

logger = get_logger("core.file_handling.audio_inspector")

# ─────────────────────────────────────────────────────────────────────────────
# Master supported-extension set  (single source of truth for the codebase)
# ─────────────────────────────────────────────────────────────────────────────

SUPPORTED_AUDIO_EXTENSIONS: frozenset[str] = frozenset({
    '.mp3',  '.flac', '.ogg',  '.oga',  '.aac',
    '.alac', '.m4a',  '.ape',  '.wav',  '.wave',
    '.dsf',  '.dff',  '.wv',   '.tta',  '.aiff',
    '.aif',  '.opus', '.wma',  '.ac3',  '.dts',
})

# Generic artist names that should NOT be trusted as a real performer.
GENERIC_ARTIST_NAMES: frozenset[str] = frozenset({
    "various artists",
    "various",
    "unknown artist",
    "unknown",
    "va",
    "",
})


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class InspectedAudio:
    """
    Rich metadata record produced by inspect_audio_file().

    All fields are Optional except file_path (which is the resolved Path).
    duration_ms is always integer milliseconds when present.
    """
    file_path: Path

    # ── Core tags ──────────────────────────────────────────────────────────
    title:          Optional[str] = None
    artist:         Optional[str] = None   # Resolved performer (see hierarchy)
    album_artist:   Optional[str] = None   # Raw TPE2 / ALBUMARTIST tag
    album:          Optional[str] = None

    # ── Numeric / temporal ────────────────────────────────────────────────
    duration_ms:    Optional[int] = None   # Always integer ms
    track_number:   Optional[int] = None   # parse_int_safe applied
    disc_number:    Optional[int] = None   # parse_int_safe applied
    year:           Optional[str] = None

    # ── Technical / codec ─────────────────────────────────────────────────
    file_format:    Optional[str] = None   # lowercase extension without dot
    bitrate_kbps:   Optional[int] = None
    sample_rate_hz: Optional[int] = None
    channels:       Optional[int] = None
    bit_depth:      Optional[int] = None
    file_size_bytes: Optional[int] = None

    # ── Identifiers ───────────────────────────────────────────────────────
    musicbrainz_id: Optional[str] = None   # Recording MBID (TXXX / UFID)
    isrc:           Optional[str] = None
    acoustid_id:    Optional[str] = None
    release_id:     Optional[str] = None   # MusicBrainz Release MBID

    # ── Cover art (raw bytes) — populated lazily on request ───────────────
    cover_data:     Optional[bytes] = None
    cover_mime:     Optional[str]  = None

    # ── Internal: artist resolution provenance ────────────────────────────
    artist_source:  str = "fallback"       # 'tpe1' | 'tpe2' | 'path' | 'fallback'

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict compatible with the legacy tag dict format."""
        return {
            "title":          self.title,
            "artist":         self.artist,
            "artist_name":    self.artist,
            "album_artist":   self.album_artist,
            "album":          self.album,
            "duration":       self.duration_ms,
            "duration_ms":    self.duration_ms,
            "track_number":   self.track_number,
            "disc_number":    self.disc_number,
            "year":           self.year,
            "file_format":    self.file_format,
            "bitrate_kbps":   self.bitrate_kbps,
            "sample_rate_hz": self.sample_rate_hz,
            "channels":       self.channels,
            "bit_depth":      self.bit_depth,
            "file_size_bytes": self.file_size_bytes,
            "musicbrainz_id": self.musicbrainz_id,
            "recording_id":   self.musicbrainz_id,
            "isrc":           self.isrc,
            "acoustid_id":    self.acoustid_id,
            "release_id":     self.release_id,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Artist resolver hierarchy
# ─────────────────────────────────────────────────────────────────────────────

# Matches common path patterns:
#   /Music/<Artist>/<Album>/<NN - Title>.<ext>   → group 1 = Artist
#   /Music/<Artist> - <Title>.<ext>              → group 1 = Artist
_PATH_ARTIST_RE = re.compile(
    r"[\\/]([^\\/]+)[\\/][^\\/]+[\\/][^\\/]+\.[a-zA-Z0-9]{2,5}$"
)


def _resolve_artist(
    tpe1: Optional[str],
    tpe2: Optional[str],
    file_path: Path,
) -> tuple[str, str]:
    """
    Apply the four-tier artist resolution hierarchy.

    Returns (artist_name, source) where source is one of:
        'tpe1' | 'tpe2' | 'path' | 'fallback'
    """
    def _clean(val: Optional[str]) -> str:
        return (val or "").strip()

    def _is_useful(val: str) -> bool:
        return bool(val) and val.lower() not in GENERIC_ARTIST_NAMES

    # Tier 1 — TPE1 / ARTIST
    t1 = _clean(tpe1)
    if _is_useful(t1):
        return t1, "tpe1"

    # Tier 2 — TPE2 / ALBUMARTIST
    t2 = _clean(tpe2)
    if _is_useful(t2):
        logger.debug("artist fallback tpe2: '%s' → '%s'", t1 or "<empty>", t2)
        return t2, "tpe2"

    # Tier 3 — Path heuristic
    m = _PATH_ARTIST_RE.search(str(file_path))
    if m:
        path_artist = m.group(1).strip()
        if _is_useful(path_artist):
            logger.debug("artist fallback path: '%s'", path_artist)
            return path_artist, "path"

    # Tier 4 — Hard default
    logger.debug("artist fallback default for: %s", file_path.name)
    return "Various Artists", "fallback"


# ─────────────────────────────────────────────────────────────────────────────
# Duration normalisation
# ─────────────────────────────────────────────────────────────────────────────

def _to_ms(raw: Any) -> Optional[int]:
    """
    Convert any duration representation to integer milliseconds.

    Handles:
    - float/int seconds (from mutagen info.length, e.g. 235.7)
    - integer milliseconds already (e.g. 235700)
    - integer microseconds (e.g. 235700000 — divide by 1000)
    - None / unparseable → None
    """
    if raw is None:
        return None
    try:
        v = float(raw)
    except (ValueError, TypeError):
        return None

    if v <= 0:
        return None

    # Heuristic: mutagen info.length is in fractional seconds (<= 86400 for 24h)
    if v <= 86_400:            # treat as seconds → multiply by 1000
        return int(v * 1000)

    # Already milliseconds (typical DB value, < 36_000_000 ms = 10 hours)
    if v <= 36_000_000:
        return int(v)

    # Microseconds (old DB artefact) — divide by 1000
    return int(v / 1000)


# ─────────────────────────────────────────────────────────────────────────────
# Core public function
# ─────────────────────────────────────────────────────────────────────────────

def inspect_audio_file(file_path: Path) -> InspectedAudio:
    """
    Inspect an audio file and return an InspectedAudio dataclass.

    This is the single authoritative entry-point for reading audio metadata.
    All tag extraction is delegated to core.file_handling.tagging_io (which
    holds the mutagen dependency and the FileJail / LockManager guards).

    Never raises — on any failure a partial InspectedAudio is returned with
    as many fields populated as possible, and the artist falls back through
    the four-tier hierarchy.

    Parameters
    ----------
    file_path : Path
        Absolute or relative path to the audio file.

    Returns
    -------
    InspectedAudio
    """
    file_path = Path(file_path)

    result = InspectedAudio(
        file_path=file_path,
        file_format=file_path.suffix.lower().lstrip(".") or None,
    )

    # ── File stat ─────────────────────────────────────────────────────────
    try:
        stat = file_path.stat()
        result.file_size_bytes = stat.st_size
    except OSError:
        pass

    # ── Tag extraction via tagging_io ─────────────────────────────────────
    tags: Dict[str, Any] = {}
    try:
        from core.file_handling.tagging_io import read_tags
        tags = read_tags(file_path) or {}
    except Exception as exc:
        logger.warning("Tag read failed for '%s': %s", file_path.name, exc)

    # ── Scalar string fields ───────────────────────────────────────────────
    result.title  = tags.get("title") or file_path.stem or None
    result.album  = tags.get("album") or None
    result.year   = str(tags.get("year") or tags.get("date") or "").strip() or None

    # ── IDs ───────────────────────────────────────────────────────────────
    result.musicbrainz_id = (
        tags.get("musicbrainz_id") or tags.get("recording_id") or None
    )
    result.isrc        = tags.get("isrc") or None
    result.acoustid_id = tags.get("acoustid_id") or None
    result.release_id  = (
        tags.get("release_id") or tags.get("musicbrainz_albumid") or None
    )

    # ── Technical metadata ────────────────────────────────────────────────
    result.bitrate_kbps   = _safe_int(tags.get("bitrate_kbps") or tags.get("bitrate"))
    result.sample_rate_hz = _safe_int(tags.get("sample_rate_hz") or tags.get("sample_rate"))
    result.channels       = _safe_int(tags.get("channels"))
    result.bit_depth      = _safe_int(tags.get("bit_depth"))

    # ── Duration (normalise to ms) ─────────────────────────────────────────
    raw_dur = (
        tags.get("duration")
        or tags.get("duration_ms")
        or tags.get("duration_seconds")
    )
    result.duration_ms = _to_ms(raw_dur)

    # ── Track / disc numbers ──────────────────────────────────────────────
    result.track_number = text_utils.parse_int_safe(
        tags.get("track_number") or tags.get("tracknumber")
    )
    result.disc_number = text_utils.parse_int_safe(
        tags.get("disc_number") or tags.get("discnumber")
    )

    # ── Album artist (raw, before hierarchy resolution) ────────────────────
    raw_album_artist = (tags.get("album_artist") or "").strip() or None
    result.album_artist = raw_album_artist

    # ── Artist hierarchy resolution ───────────────────────────────────────
    tpe1 = tags.get("artist") or tags.get("artist_name") or None
    result.artist, result.artist_source = _resolve_artist(tpe1, raw_album_artist, file_path)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_int(val: Any) -> Optional[int]:
    """Coerce val to int, return None on failure."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def is_supported_audio(file_path: Path) -> bool:
    """Return True if the file extension is in SUPPORTED_AUDIO_EXTENSIONS."""
    return file_path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
