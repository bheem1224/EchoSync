"""
core/file_handling/tagging_io.py — Audio tag read / write

Single-responsibility module for all Mutagen-based metadata operations.

Public API
----------
read_tags(path)              — read tags from a physical audio file; returns
                               a normalised dict with canonical field names.
write_tags(path, metadata)   — write a metadata dict to a physical audio file.

Canonical field names emitted / accepted
-----------------------------------------
  title, artist_name, album, date, year, track_number, disc_number,
  isrc, musicbrainz_id, recording_id, artist_id, release_id,
  acoustid_id, duration (ms), bitrate_kbps, sample_rate_hz,
  channels, file_format.

Security + Concurrency
-----------------------
Both functions validate the path against the FileJail and hold the per-file
Lock from the shared LockManager before touching disk.  This guarantees that
no Mutagen operation races with a concurrent safe_move or safe_delete.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from core.tiered_logger import get_logger
from .jail import file_jail, lock_manager
from .base_io import resolve_path

logger = get_logger("core.file_handling.tagging_io")

# ── Optional Mutagen ──────────────────────────────────────────────────────────
try:
    import mutagen
    from mutagen.id3 import (
        ID3, TXXX, TIT2, TPE1, TALB, TDRC, TRCK, TPOS, TSRC,
    )
    from mutagen.flac import FLAC
    from mutagen.wave import WAVE
    try:
        from mutagen._riff import RiffFile
    except Exception:
        RiffFile = None
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    RiffFile = None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def read_tags(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Securely read audio tags from *path*.

    Validates the path against the FileJail, acquires the file lock, then
    delegates to ``_read_tags_impl``.

    Returns:
        Normalised tag dict with canonical field names (see module docstring).
    """
    resolved = resolve_path(path)
    file_jail.validate(resolved)
    with lock_manager.lock_for(resolved):
        return _read_tags_impl(resolved)


def write_tags(path: Union[str, Path], metadata: Dict[str, Any]) -> None:
    """
    Securely write *metadata* tags to the audio file at *path*.

    Validates the path against the FileJail, acquires the file lock, then
    delegates to ``_write_tags_impl``.

    Accepts both canonical alias forms:
      • ``artist_name`` or ``artist``
      • ``musicbrainz_id`` or ``recording_id``
    """
    resolved = resolve_path(path)
    file_jail.validate(resolved)
    with lock_manager.lock_for(resolved):
        _write_tags_impl(resolved, metadata)


# ─────────────────────────────────────────────────────────────────────────────
# Implementation — read
# ─────────────────────────────────────────────────────────────────────────────

def _read_tags_impl(file_path: Path) -> Dict[str, Any]:
    if not MUTAGEN_AVAILABLE:
        return {}

    metadata: Dict[str, Any] = {
        "file_format": file_path.suffix.lower().lstrip("."),
    }

    try:
        easy_audio = mutagen.File(str(file_path), easy=True)
        metadata = _merge(metadata, _extract_easy_tags(easy_audio))
        metadata = _merge(metadata, _extract_audio_info(easy_audio))
    except Exception as exc:
        logger.debug("Easy tag read failed for %s: %s", file_path.name, exc)

    try:
        detailed_audio = mutagen.File(str(file_path))
        metadata = _merge(metadata, _extract_detailed_tags(detailed_audio))
        metadata = _merge(metadata, _extract_audio_info(detailed_audio))
    except Exception as exc:
        logger.debug("Detailed tag read failed for %s: %s", file_path.name, exc)

    if file_path.suffix.lower() == ".wav":
        metadata = _merge(metadata, _read_wav_tags(file_path))

    # Derive year from date
    if not metadata.get("year") and metadata.get("date"):
        date_val = str(metadata["date"]).strip()
        if len(date_val) >= 4 and date_val[:4].isdigit():
            metadata["year"] = date_val[:4]

    # ── Track artist vs Album artist resolution ──────────────────────────────
    # Rule: TPE1 / ARTIST (track artist) always wins over TPE2 / ALBUMARTIST
    # (album artist).  We only fall back to album_artist when the track artist
    # tag is completely absent — never the other way around.  This prevents
    # compilation / OST albums that use 'Various Artists' as the album artist
    # from incorrectly overwriting the specific performer stored in TPE1.

    # We EXPLICITLY grab TPE1/ARTIST as our track artist, and TPE2/ALBUMARTIST
    # as our album artist. If track_artist is a generic compilation artist
    # (e.g. "Various Artists") but album_artist is the specific performer
    # (some taggers swap them), we should NOT swap them back. TPE1 ALWAYS wins.
    track_artist = metadata.get("artist")
    album_artist = metadata.get("album_artist")

    # If TPE1 is completely missing, and TPE2 is available, fallback to TPE2.
    if not track_artist and album_artist:
        # TPE1 absent but TPE2 present — use album artist as last-resort fallback
        metadata["artist"] = album_artist
    # Keep album_artist in the dict so callers can distinguish the two fields if they need to.

    # Canonical field aliases
    # artist_name is the primary semantic name; keep 'artist' for back-compat
    if metadata.get("artist") and not metadata.get("artist_name"):
        metadata["artist_name"] = metadata["artist"]
    elif metadata.get("artist_name") and not metadata.get("artist"):
        metadata["artist"] = metadata["artist_name"]

    # duration in milliseconds derived from duration_seconds
    if metadata.get("duration_seconds") and not metadata.get("duration"):
        metadata["duration"] = int(metadata["duration_seconds"]) * 1000

    # musicbrainz_id canonical alias from recording_id
    if metadata.get("recording_id") and not metadata.get("musicbrainz_id"):
        metadata["musicbrainz_id"] = metadata["recording_id"]

    return {k: v for k, v in metadata.items() if v not in (None, "", [], {})}


# ─────────────────────────────────────────────────────────────────────────────
# Implementation — write
# ─────────────────────────────────────────────────────────────────────────────

def _write_tags_impl(file_path: Path, metadata: Dict[str, Any]) -> None:
    if not MUTAGEN_AVAILABLE:
        logger.warning("Mutagen not available — tag write skipped for %s", file_path.name)
        return

    # Accept both artist_name and artist
    normalised = dict(metadata)
    if normalised.get("artist_name") and not normalised.get("artist"):
        normalised["artist"] = normalised["artist_name"]

    try:
        ext = file_path.suffix.lower()
        if ext == ".mp3":
            _tag_mp3(file_path, normalised)
        elif ext == ".flac":
            _tag_flac(file_path, normalised)
        else:
            logger.debug(
                "write_tags: unsupported format '%s', skipping %s", ext, file_path.name
            )
            return
        logger.info("Tagged: %s", file_path.name)
    except Exception as exc:
        logger.error("Failed to write tags to %s: %s", file_path, exc)


# ─────────────────────────────────────────────────────────────────────────────
# Internal extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

def _merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in (update or {}).items():
        if value not in (None, "", [], {}):
            merged[str(key)] = value
    return merged


def _extract_audio_info(audio: Any) -> Dict[str, Any]:
    info = getattr(audio, "info", None)
    if not info:
        return {}
    result: Dict[str, Any] = {}
    if getattr(info, "length", None) is not None:
        result["duration_seconds"] = int(info.length)
    if getattr(info, "bitrate", None) is not None:
        result["bitrate_kbps"] = int(info.bitrate / 1000)
    if getattr(info, "sample_rate", None) is not None:
        result["sample_rate_hz"] = int(info.sample_rate)
    if getattr(info, "channels", None) is not None:
        result["channels"] = int(info.channels)
    return result


def _extract_easy_tags(audio: Any) -> Dict[str, Any]:
    return _map_simple_tags(getattr(audio, "tags", None) or {})


def _extract_detailed_tags(audio: Any) -> Dict[str, Any]:
    tags = getattr(audio, "tags", None)
    if not tags:
        return {}

    if hasattr(tags, "getall"):
        # ID3 frame-based format (MP3)
        # TPE1 = Track/Performer artist  (the specific singer/band for this track)
        # TPE2 = Album/Band artist field (often 'Various Artists' on compilations)
        # We store BOTH so the caller can prefer the track artist over the band tag.
        metadata: Dict[str, Any] = {
            "title":        _id3_text(tags, "TIT2"),
            "artist":       _id3_text(tags, "TPE1"),
            "album_artist": _id3_text(tags, "TPE2"),
            "album":        _id3_text(tags, "TALB"),
            "date":         _id3_text(tags, "TDRC"),
            "track_number": _id3_text(tags, "TRCK"),
            "disc_number":  _id3_text(tags, "TPOS"),
            "isrc":         _id3_text(tags, "TSRC"),
            "comments":     _id3_text(tags, "COMM"),
        }
        for frame in tags.getall("TXXX"):
            desc = str(getattr(frame, "desc", "") or "").strip().lower()
            text = _frame_text(frame)
            if desc == "musicbrainz track id":
                metadata["recording_id"] = text
                metadata["musicbrainz_id"] = text
            elif desc == "musicbrainz artist id":
                metadata["artist_id"] = text
            elif desc == "musicbrainz release id":
                metadata["release_id"] = text
            elif desc in ("acoustid id", "acoustid_id"):
                metadata["acoustid_id"] = text

        if not metadata.get("musicbrainz_id") and metadata.get("recording_id"):
            metadata["musicbrainz_id"] = metadata["recording_id"]

        return {k: v for k, v in metadata.items() if v not in (None, "", [], {})}

    return _map_simple_tags(tags)


def _map_simple_tags(tags: Any) -> Dict[str, Any]:
    if not hasattr(tags, "items"):
        return {}
    lowered = {str(k).lower(): v for k, v in tags.items()}
    result: Dict[str, Any] = {
        "title":        _first(lowered, "title",       "inam"),
        # Track artist (ARTIST vorbis / TPE1 in ID3 via easy) — the specific performer
        "artist":       _first(lowered, "artist",      "iart"),
        # Album artist (ALBUMARTIST vorbis / TPE2 in ID3 via easy) — often 'Various Artists'
        "album_artist": _first(lowered, "albumartist", "album artist"),
        "album":        _first(lowered, "album",       "iprd"),
        "date":         _first(lowered, "date",        "year",  "icrd"),
        "track_number": _first(lowered, "tracknumber", "track_number", "trck", "itrk"),
        "disc_number":  _first(lowered, "discnumber",  "disc_number",  "tpos"),
        "isrc":         _first(lowered, "isrc",        "tsrc"),
        "comments":     _first(lowered, "comment",     "comments",     "comm", "icmt"),
        "acoustid_id":  _first(lowered, "acoustid id", "acoustid_id"),
    }
    recording_id = _first(
        lowered,
        "musicbrainz_trackid", "musicbrainz track id",
        "recording_id",        "musicbrainz_id",
    )
    result["recording_id"]  = recording_id
    result["musicbrainz_id"] = recording_id
    result["artist_id"]  = _first(lowered, "musicbrainz_artistid",  "musicbrainz artist id", "artist_id")
    result["release_id"] = _first(lowered, "musicbrainz_albumid",   "musicbrainz release id", "release_id")
    return {k: v for k, v in result.items() if v not in (None, "", [], {})}


def _first(mapping: Dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        if key not in mapping:
            continue
        value = _coerce(mapping[key])
        if value not in (None, ""):
            return value
    return None


def _coerce(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            result = _coerce(item)
            if result not in (None, ""):
                return result
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").replace("\x00", "").strip() or None
    text = getattr(value, "text", None)
    if text is not None:
        return _coerce(text)
    return str(value).replace("\x00", "").strip() or None


def _frame_text(frame: Any) -> Optional[str]:
    return _coerce(frame)


def _id3_text(tags: Any, frame_id: str) -> Optional[str]:
    frames = tags.getall(frame_id)
    return _frame_text(frames[0]) if frames else None


def _read_wav_tags(file_path: Path) -> Dict[str, Any]:
    """Read tags from a WAV file including RIFF INFO chunks."""
    metadata: Dict[str, Any] = {}
    try:
        audio = WAVE(str(file_path))
        metadata = _merge(metadata, _extract_audio_info(audio))
        metadata = _merge(metadata, _extract_detailed_tags(audio))
        metadata = _merge(metadata, _map_simple_tags(getattr(audio, "tags", None) or {}))
    except Exception as exc:
        logger.debug("WAVE tag read failed for %s: %s", file_path.name, exc)

    if RiffFile is None:
        return metadata

    try:
        with file_path.open("rb") as handle:
            riff = RiffFile(handle)
            info_chunk = None
            for chunk in riff.root.subchunks():
                if (
                    getattr(chunk, "id", None) == "LIST"
                    and getattr(chunk, "name", None) == "INFO"
                ):
                    info_chunk = chunk
                    break
            if info_chunk is not None:
                riff_tags: Dict[str, Any] = {}
                for chunk in info_chunk.subchunks():
                    chunk_id = str(getattr(chunk, "id", "") or "").lower()
                    if chunk_id:
                        riff_tags[chunk_id] = chunk.read()
                metadata = _merge(metadata, _map_simple_tags(riff_tags))
    except Exception as exc:
        logger.debug("RIFF INFO tag read failed for %s: %s", file_path.name, exc)

    return metadata


# ─────────────────────────────────────────────────────────────────────────────
# Internal write helpers
# ─────────────────────────────────────────────────────────────────────────────

def _tag_mp3(file_path: Path, metadata: Dict[str, Any]) -> None:
    """Write ID3v2.4 tags to an MP3 file."""
    try:
        try:
            audio = ID3(str(file_path))
        except Exception:
            audio = ID3()

        if metadata.get("title"):
            audio.add(TIT2(encoding=3, text=metadata["title"]))
        if metadata.get("artist"):
            audio.add(TPE1(encoding=3, text=metadata["artist"]))
        if metadata.get("album"):
            audio.add(TALB(encoding=3, text=metadata["album"]))
        if metadata.get("date"):
            audio.add(TDRC(encoding=3, text=metadata["date"]))
        if metadata.get("track_number"):
            audio.add(TRCK(encoding=3, text=str(metadata["track_number"])))
        if metadata.get("disc_number"):
            audio.add(TPOS(encoding=3, text=str(metadata["disc_number"])))
        if metadata.get("isrc"):
            audio.add(TSRC(encoding=3, text=metadata["isrc"]))
        if metadata.get("recording_id") or metadata.get("musicbrainz_id"):
            mbid = metadata.get("recording_id") or metadata["musicbrainz_id"]
            audio.add(TXXX(encoding=3, desc="MusicBrainz Track Id", text=mbid))
        if metadata.get("artist_id"):
            audio.add(TXXX(encoding=3, desc="MusicBrainz Artist Id", text=metadata["artist_id"]))
        if metadata.get("release_id"):
            audio.add(TXXX(encoding=3, desc="MusicBrainz Release Id", text=metadata["release_id"]))
        if metadata.get("acoustid_id"):
            audio.add(TXXX(encoding=3, desc="AcoustID Id", text=metadata["acoustid_id"]))

        audio.save(str(file_path), v2_version=4)
    except Exception as exc:
        logger.error("Error tagging MP3 %s: %s", file_path.name, exc)


def _tag_flac(file_path: Path, metadata: Dict[str, Any]) -> None:
    """Write Vorbis Comment tags to a FLAC file."""
    try:
        audio = FLAC(str(file_path))

        if metadata.get("title"):
            audio["TITLE"] = metadata["title"]
        if metadata.get("artist"):
            audio["ARTIST"] = metadata["artist"]
        if metadata.get("album"):
            audio["ALBUM"] = metadata["album"]
        if metadata.get("date"):
            audio["DATE"] = metadata["date"]
        if metadata.get("track_number"):
            audio["TRACKNUMBER"] = str(metadata["track_number"])
        if metadata.get("disc_number"):
            audio["DISCNUMBER"] = str(metadata["disc_number"])
        if metadata.get("isrc"):
            audio["ISRC"] = metadata["isrc"]
        if metadata.get("recording_id") or metadata.get("musicbrainz_id"):
            audio["MUSICBRAINZ_TRACKID"] = (
                metadata.get("recording_id") or metadata["musicbrainz_id"]
            )
        if metadata.get("artist_id"):
            audio["MUSICBRAINZ_ARTISTID"] = metadata["artist_id"]
        if metadata.get("release_id"):
            audio["MUSICBRAINZ_ALBUMID"] = metadata["release_id"]
        if metadata.get("acoustid_id"):
            audio["ACOUSTID_ID"] = metadata["acoustid_id"]

        audio.save()
    except Exception as exc:
        logger.error("Error tagging FLAC %s: %s", file_path.name, exc)
