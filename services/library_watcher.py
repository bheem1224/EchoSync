"""
Library Watcher Service — Real-time file-system monitoring for the local library.

Architecture
============
This service bridges the OS file-system notification layer (watchdog) with the
Echosync event bus so new audio files added directly to the local library land
in the database and trigger TRACK_IMPORTED *immediately*, without waiting for
the next scheduled scan.

Flow
----
  OS FS event (inotify / FSEvents / ReadDirectoryChangesW) on library_dir
      ↓  watchdog Observer thread
  _AudioEventHandler.on_created / on_moved
      ↓  per-path debounce timer (threading.Timer, 1.5 s)
  _process_new_file(path)
      ├─ echosync_core.extract_metadata()   → extract title / artist / isrc / …
      ├─ TrackRepository.bulk_upsert_tracks() + deduplicate/re-parent (no_autoflush)
      └─ event_bus.publish({"event": "TRACK_IMPORTED", …})
             ↓
         DownloadManager._on_track_imported → cancel redundant queue entries
         (any other subscriber)

Design notes
------------
Scope Invariant:
  LibraryWatcherService exclusively monitors ``library_dir``.  ``download_dir``
  is exclusively monitored by ``AutoImportService`` (5.0 s debounce), avoiding
  any 1.5 s vs 5.0 s race condition on incoming downloads.

Debounce (1.5 s):
  Many tools write a file by creating a temporary name and then renaming it
  into place.  Others write in small chunks, each triggering a new event.
  A short timer that resets on every event for the same path ensures we only
  run tag-extraction once the write is complete.

Thread safety:
  The Observer runs in its own daemon thread.  _process_new_file() is called
  from that thread via the timer callback.  All DB access goes through SQLAlchemy
  session management with db_write_lease().  The event bus dispatch is thread-safe
  (locked internally).

Minimum file size guard (64 KB):
  Rejects stub / zero-byte files that are sometimes created before the actual
  content arrives.  This is a heuristic — the debounce timer is the primary
  protection against reading partial files.
"""

import os
import re
import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import echosync_core
from sqlalchemy import or_
from watchdog.events import (  # type: ignore[import-untyped]
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer  # type: ignore[import-untyped]

from core.db.echo_sync_track import EchosyncMedia, EchosyncTrack
from core.event_bus import event_bus
from core.settings import config_manager
from core.task_manager.task_queue import db_write_lease
from core.tiered_logger import get_logger
from database import _canonicalize_path
from database import music_database as _music_db_module
from database.music_database import LocalMedia, Track, TrackArtist
from database.music_database import get_database as _orig_get_database

get_database = _orig_get_database

logger = get_logger("library_watcher")

# Audio extensions that the watcher responds to.
# Must stay in sync with LocalServerProvider.get_library_tracks() and
# web/routes/local_server.py format sets.
_AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".flac",
        ".mp3",
        ".ogg",
        ".m4a",
        ".aac",
        ".alac",
        ".ape",
        ".wav",
        ".dsf",
        ".dff",
        ".wma",
    }
)

# Minimum on-disk size before tag extraction is attempted.
# Prevents reading half-written files created by download managers.
_MIN_FILE_BYTES: int = 64 * 1024  # 64 KB

# Settling delay.  Timer resets if the same path fires another event within
# this window, guaranteeing tags are read only after the write is complete.
_DEBOUNCE_SECONDS: float = 1.5

# ── In-Flight Transfer Lock Suppression Registry ──────────────────────────────
_in_flight_transfers: dict[str, int] = {}
_transfer_lock = threading.Lock()


def _resolve_music_database() -> Any:
    """Resolve active MusicDatabase, honoring monkeypatches on either module."""
    if get_database is not _orig_get_database:
        return get_database()
    return _music_db_module.get_database()


def is_path_suppressed(path: str) -> bool:
    """Check if a path is currently registered as an in-flight transfer."""
    norm = str(Path(path).resolve()).lower()
    with _transfer_lock:
        return _in_flight_transfers.get(norm, 0) > 0


@contextmanager
def suppress_path(path: str) -> Generator[None, None, None]:
    """Context manager to suppress library watcher events during atomic moves."""
    norm = str(Path(path).resolve()).lower()
    with _transfer_lock:
        _in_flight_transfers[norm] = _in_flight_transfers.get(norm, 0) + 1
    try:
        yield
    finally:
        with _transfer_lock:
            count = _in_flight_transfers.get(norm, 0)
            if count <= 1:
                _in_flight_transfers.pop(norm, None)
            else:
                _in_flight_transfers[norm] = count - 1


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, str):
            raw = value.strip().split("/")[0].strip()
            if not raw:
                return None
            return int(float(raw))
        return int(value)
    except (ValueError, TypeError):
        return None


def build_edition_quality_tag(
    metadata: dict[str, Any] | None = None,
    ext: str = "",
) -> str:
    """Build an audio edition tag such as '[FLAC-24-96]' or '[MP3-320]'."""
    meta = metadata or {}
    raw_fmt = (
        meta.get("file_format")
        or meta.get("codec")
        or meta.get("format")
        or ext
        or ""
    )
    fmt = str(raw_fmt).strip().lstrip(".").upper()
    bd = _coerce_optional_int(meta.get("bit_depth"))
    sr = _coerce_optional_int(meta.get("sample_rate"))
    br = _coerce_optional_int(meta.get("bitrate"))

    sr_khz: int | None = None
    if sr and sr > 0:
        sr_khz = int(round(sr / 1000.0)) if sr >= 1000 else sr

    br_kbps: int | None = None
    if br and br > 0:
        br_kbps = int(round(br / 1000.0)) if br >= 10000 else br

    if fmt and bd and bd > 0 and sr_khz and sr_khz > 0:
        return f"[{fmt}-{bd}-{sr_khz}]"
    if fmt and br_kbps and br_kbps > 0:
        return f"[{fmt}-{br_kbps}]"
    if fmt:
        return f"[{fmt}]"
    return ""


def resolve_collision_safe_edition_path(
    base_dest: Path,
    metadata: dict[str, Any] | None = None,
    session: Any = None,
    current_file: Path | None = None,
    existing_media_id: int | None = None,
) -> Path:
    """Resolve a collision-safe destination path with edition tags (e.g. '04 - Title [FLAC-24-96].flac').

    All database collision checks execute inside ``with session.no_autoflush:`` so pending
    ORM mutations never trigger premature autoflush IntegrityErrors.
    """
    edition_tag = build_edition_quality_tag(metadata, ext=base_dest.suffix)
    stem = base_dest.stem
    ext = base_dest.suffix
    parent = base_dest.parent

    def _is_colliding(candidate: Path) -> bool:
        exists_on_disk = False
        try:
            if candidate.exists():
                if current_file and current_file.exists():
                    exists_on_disk = candidate.resolve() != current_file.resolve()
                elif current_file is not None:
                    exists_on_disk = candidate.resolve() != current_file.resolve()
                else:
                    exists_on_disk = True
        except Exception:
            exists_on_disk = False

        exists_in_db = False
        if session is not None:
            with session.no_autoflush:
                canon_str = _canonicalize_path(str(candidate))
                query = session.query(LocalMedia).filter(
                    or_(
                        LocalMedia.file_path == canon_str,
                        LocalMedia.file_path == str(candidate),
                    )
                )
                if existing_media_id is not None:
                    query = query.filter(LocalMedia.id != existing_media_id)
                exists_in_db = query.first() is not None
                if not exists_in_db:
                    cand_paths = {canon_str, str(candidate)}
                    deleted_set = getattr(session, "deleted", ())
                    for obj in (*getattr(session, "new", ()), *getattr(session, "dirty", ())):
                        if isinstance(obj, LocalMedia) and obj not in deleted_set:
                            if existing_media_id is not None and obj.id == existing_media_id:
                                continue
                            if getattr(obj, "file_path", None) in cand_paths:
                                exists_in_db = True
                                break

        return exists_on_disk or exists_in_db

    if not _is_colliding(base_dest):
        return base_dest

    if edition_tag and edition_tag not in stem:
        tagged_stem = f"{stem} {edition_tag}"
        tagged_candidate = parent / f"{tagged_stem}{ext}"
        if not _is_colliding(tagged_candidate):
            return tagged_candidate
    else:
        tagged_stem = stem

    counter = 1
    while True:
        numbered_candidate = parent / f"{tagged_stem} ({counter}){ext}"
        if not _is_colliding(numbered_candidate):
            return numbered_candidate
        counter += 1


def deduplicate_and_reparent_track(
    session: Any,
    media_path: Path | str,
    track_dto: EchosyncTrack | None = None,
    metadata: dict[str, Any] | None = None,
) -> Track | None:
    """Deduplicate and re-parent LocalMedia onto a canonical Track inside ``session.no_autoflush``.

    Matches canonical Tracks by MBID -> ISRC (same edition) -> (normalized_title, artist_id,
    edition) within +-5000ms duration tolerance, deletes ghost duplicate LocalMedia rows, and
    prunes orphaned duplicate Track rows without deleting physical files.
    """
    from core.matching_engine.text_utils import normalize_title

    meta = metadata or {}
    path_str = str(media_path)
    canon_str = _canonicalize_path(path_str)
    resolved_str = str(Path(path_str).resolve())

    with session.no_autoflush:
        media = (
            session.query(LocalMedia)
            .filter(
                or_(
                    LocalMedia.file_path == canon_str,
                    LocalMedia.file_path == path_str,
                    LocalMedia.file_path == resolved_str,
                )
            )
            .first()
        )
        if media is None:
            return None

        current_track = session.get(Track, media.track_id) if media.track_id else None
        exclude_id = current_track.id if current_track else None

        mbid = (
            getattr(track_dto, "musicbrainz_id", None)
            or getattr(track_dto, "musicbrainz_track_id", None)
            or meta.get("musicbrainz_track_id")
            or meta.get("musicbrainz_id")
            or meta.get("mbid")
            or (current_track.musicbrainz_id if current_track else None)
        )
        if mbid == "NOT_FOUND":
            mbid = None

        isrc = (
            getattr(track_dto, "isrc", None)
            or meta.get("isrc")
            or (current_track.isrc if current_track else None)
        )
        if isrc:
            isrc = str(isrc).strip().upper() or None

        raw_edition = (
            getattr(track_dto, "edition", None)
            or meta.get("edition")
            or meta.get("version")
            or (current_track.edition if current_track else None)
            or ""
        )
        edition = str(raw_edition).strip() or None
        norm_edition = (edition or "").lower()

        raw_title = (
            getattr(track_dto, "title", None)
            or getattr(track_dto, "raw_title", None)
            or meta.get("title")
            or (current_track.title if current_track else "")
            or ""
        )
        norm_title = (
            getattr(track_dto, "normalized_title", None)
            or (normalize_title(raw_title) if raw_title else "")
            or (current_track.normalized_title if current_track else "")
        )

        artist_id = getattr(track_dto, "artist_id", None) or (
            current_track.artist_id if current_track else None
        )
        duration_ms = (
            getattr(track_dto, "duration_ms", None)
            or _coerce_optional_int(meta.get("duration_ms"))
            or (current_track.duration if current_track else None)
        )

        canonical_track: Track | None = None

        # 1. Match by MusicBrainz recording/track ID
        if mbid:
            mb_q = session.query(Track).filter(Track.musicbrainz_id == mbid)
            if exclude_id is not None:
                mb_q = mb_q.filter(Track.id != exclude_id)
            for cand in mb_q.order_by(Track.id.asc()).all():
                cand_ed = (cand.edition or "").strip().lower()
                if (cand_ed or norm_edition) and cand_ed != norm_edition:
                    continue
                canonical_track = cand
                break

        # 2. Match by ISRC (matching edition)
        if canonical_track is None and isrc:
            isrc_q = session.query(Track).filter(Track.isrc == isrc)
            if exclude_id is not None:
                isrc_q = isrc_q.filter(Track.id != exclude_id)
            for cand in isrc_q.order_by(Track.id.asc()).all():
                cand_ed = (cand.edition or "").strip().lower()
                if cand_ed == norm_edition:
                    canonical_track = cand
                    break

        # 3. Match by (normalized_title, artist_id, edition) + duration tolerance
        if canonical_track is None and norm_title and artist_id:
            ed_filter = (
                Track.edition == edition
                if edition
                else or_(Track.edition.is_(None), Track.edition == "")
            )
            title_q = session.query(Track).filter(
                Track.normalized_title == norm_title,
                Track.artist_id == artist_id,
                ed_filter,
            )
            if exclude_id is not None:
                title_q = title_q.filter(Track.id != exclude_id)
            for cand in title_q.order_by(Track.id.asc()).all():
                if (
                    duration_ms is not None
                    and cand.duration is not None
                    and abs(int(cand.duration) - int(duration_ms)) > 5000
                ):
                    continue
                canonical_track = cand
                break

        target_track = canonical_track or current_track

        # Remove ghost duplicate LocalMedia rows under target_track
        if target_track is not None:
            ghost_filters = [LocalMedia.file_path == media.file_path]
            if media.media_id:
                ghost_filters.append(LocalMedia.media_id == media.media_id)
            ghosts = (
                session.query(LocalMedia)
                .filter(
                    LocalMedia.track_id == target_track.id,
                    LocalMedia.id != media.id,
                    or_(*ghost_filters),
                )
                .all()
            )
            for ghost in ghosts:
                session.delete(ghost)

        # Re-parent media onto canonical_track and prune orphaned source track
        if canonical_track is not None and canonical_track.id != exclude_id:
            logger.info(
                "Deduplicating/re-parenting LocalMedia %s (%s) from Track %s -> canonical Track %s",
                media.id,
                media.file_path,
                exclude_id,
                canonical_track.id,
            )
            media.track = canonical_track
            media.track_id = canonical_track.id

            if isrc and not canonical_track.isrc:
                canonical_track.isrc = isrc
            if mbid and not canonical_track.musicbrainz_id:
                canonical_track.musicbrainz_id = mbid
            if current_track is not None:
                if current_track.track_number and not canonical_track.track_number:
                    canonical_track.track_number = current_track.track_number
                if current_track.disc_number and not canonical_track.disc_number:
                    canonical_track.disc_number = current_track.disc_number
                if current_track.album_id and not canonical_track.album_id:
                    canonical_track.album_id = current_track.album_id

                remaining_siblings = (
                    session.query(LocalMedia)
                    .filter(
                        LocalMedia.track_id == current_track.id,
                        LocalMedia.id != media.id,
                    )
                    .count()
                )
                if remaining_siblings == 0:
                    session.query(TrackArtist).filter_by(track_id=current_track.id).delete()
                    session.delete(current_track)

        return target_track


_TEMP_EXTENSIONS: tuple[str, ...] = (".tmp", ".part", ".crdownload")


def _is_path_ignored(file_path: str, ignored_directories: set[str] | None = None) -> bool:
    """Check if a file path belongs to an ignored directory or temp pattern."""
    if ignored_directories is None:
        ignored_directories = {"poor_metadata", "incomplete"}
    try:
        p = Path(str(file_path).replace("\\", "/"))
        parts_lower = {part.lower().strip("/\\") for part in p.parts}
        if bool(parts_lower.intersection(ignored_directories)):
            return True
        name_lower = p.name.lower()
        if name_lower.endswith(_TEMP_EXTENSIONS) or any(part.lower().endswith(_TEMP_EXTENSIONS) for part in p.parts):
            return True
    except Exception:
        pass
    return False


class _AudioEventHandler(FileSystemEventHandler):
    """Watchdog event handler that debounces and processes new audio files."""

    def __init__(self) -> None:
        super().__init__()
        # Maps abs path → active threading.Timer awaiting expiry
        self._pending: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    # ── Public watchdog callbacks ──────────────────────────────────────────

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(os.fsdecode(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        # on_moved fires when a download manager renames a .tmp → .flac etc.
        # We care about the *destination* path.
        if event.is_directory:
            return
        dest = getattr(event, "dest_path", event.src_path)
        self._schedule(os.fsdecode(dest))

    # ── Internal helpers ───────────────────────────────────────────────────

    def _schedule(self, raw_path: str) -> None:
        """(Re-)schedule processing for a path after the debounce window."""
        if _is_path_ignored(raw_path):
            return

        path = Path(raw_path)
        if path.suffix.lower() not in _AUDIO_EXTENSIONS:
            return

        abs_path = str(path.resolve())
        if is_path_suppressed(abs_path):
            logger.debug("Watcher: skipping suppressed in-flight path: %s", path.name)
            return

        with self._lock:
            existing = self._pending.pop(abs_path, None)
            if existing is not None:
                existing.cancel()

            timer = threading.Timer(
                _DEBOUNCE_SECONDS,
                self._fire,
                args=(abs_path,),
            )
            timer.daemon = True
            self._pending[abs_path] = timer
            timer.start()

    def _fire(self, abs_path: str) -> None:
        """Called by the timer once the debounce window has elapsed."""
        with self._lock:
            self._pending.pop(abs_path, None)

        if is_path_suppressed(abs_path):
            logger.debug("Watcher: skipping suppressed path at fire time: %s", abs_path)
            return

        _process_new_file(Path(abs_path))

    def cancel_all(self) -> None:
        """Cancel all pending timers (called on service stop)."""
        with self._lock:
            for timer in self._pending.values():
                timer.cancel()
            self._pending.clear()


# ── File processing ────────────────────────────────────────────────────────────


def _process_new_file(path: Path) -> None:
    """
    Extract tags, upsert/deduplicate the track into the database, and emit TRACK_IMPORTED.

    Any exception is caught and logged so a single bad file never crashes the
    watcher thread.
    """
    try:
        if not path.exists():
            logger.debug("Watcher: file vanished before processing: %s", path)
            return

        stat_info = path.stat()
        if stat_info.st_size < _MIN_FILE_BYTES:
            logger.debug(
                "Watcher: skipping small file (%d bytes): %s",
                stat_info.st_size,
                path,
            )
            return

        logger.info("Watcher: new audio file detected: %s", path.name)

        # ── 1. Extract tags ────────────────────────────────────────────────
        tags: dict[str, Any] = {}
        try:
            tags = echosync_core.extract_metadata(str(path)) or {}
        except Exception as tag_err:
            logger.warning("Watcher: tag extraction failed for %s: %s", path.name, tag_err)

        fallback_stem = re.sub(
            r"\s*\[(?:FLAC|MP3|ALAC|WAV|AAC|OGG|APE|DSD|DSF|DFF)(?:-\d+)*\]\s*$",
            "",
            path.stem,
            flags=re.IGNORECASE,
        ).strip() or path.stem

        title: str = tags.get("title") or fallback_stem
        artist_name: str = tags.get("artist") or tags.get("artist_name") or "Unknown Artist"
        isrc: str | None = tags.get("isrc") or None
        album_title: str | None = tags.get("album") or tags.get("album_title") or None
        mbid: str | None = (
            tags.get("musicbrainz_track_id")
            or tags.get("musicbrainz_id")
            or tags.get("mbid")
            or None
        )
        edition: str | None = tags.get("edition") or tags.get("version") or None
        track_number: int | None = _coerce_optional_int(
            tags.get("track_number") if tags.get("track_number") is not None else tags.get("track_no")
        )
        disc_number: int | None = _coerce_optional_int(
            tags.get("disc_number") if tags.get("disc_number") is not None else tags.get("disc_no")
        )
        duration_ms: int | None = None

        raw_duration = tags.get("duration_ms")
        if raw_duration is None:
            raw_duration = tags.get("duration")
            if raw_duration is not None:
                try:
                    raw_duration = int(float(raw_duration))
                except (ValueError, TypeError):
                    raw_duration = None
        if raw_duration is not None:
            try:
                duration_ms = int(raw_duration)
            except (ValueError, TypeError):
                duration_ms = None

        file_format = (
            str(tags.get("file_format") or tags.get("codec") or path.suffix)
            .lstrip(".")
            .lower()
            or None
        )

        # ── 2. Upsert into the music database ─────────────────────────────
        # Build an EchosyncTrack so TrackRepository upsert + deduplication handles
        # Artist / Album / Track creation and re-parenting inside session.no_autoflush.
        from core.matching_engine.track_parser import normalize_track_dto

        media_obj = EchosyncMedia(
            file_path=str(path),
            file_format=file_format,
            bitrate=_coerce_optional_int(tags.get("bitrate")),
            sample_rate=_coerce_optional_int(tags.get("sample_rate")),
            bit_depth=_coerce_optional_int(tags.get("bit_depth")),
            channels=_coerce_optional_int(tags.get("channels")),
            duration_ms=duration_ms,
            file_size_bytes=_coerce_optional_int(tags.get("file_size_bytes")) or stat_info.st_size,
            inode=_coerce_optional_int(tags.get("inode")) or getattr(stat_info, "st_ino", None),
            mtime=tags.get("mtime") if tags.get("mtime") is not None else getattr(stat_info, "st_mtime", None),
        )
        track_obj = normalize_track_dto(EchosyncTrack(
            raw_title=title,
            title=title,
            artist_name=artist_name,
            album_title=album_title or "",
            edition=edition,
            duration_ms=duration_ms,
            track_number=track_number,
            disc_number=disc_number,
            musicbrainz_id=mbid,
            isrc=isrc,
            media=[media_obj],
        ))

        try:
            from core.database.repositories.track_repo import TrackRepository

            db = _resolve_music_database()
            with db.session_factory() as session:
                with session.no_autoflush:
                    repo = TrackRepository(session)
                    repo.bulk_upsert_tracks([track_obj])
                    canon_str = _canonicalize_path(str(path))
                    existing_lm = (
                        session.query(LocalMedia)
                        .filter(
                            or_(
                                LocalMedia.file_path == canon_str,
                                LocalMedia.file_path == str(path),
                            )
                        )
                        .first()
                    )
                    resolve_collision_safe_edition_path(
                        path,
                        metadata=tags,
                        session=session,
                        current_file=path,
                        existing_media_id=existing_lm.id if existing_lm else None,
                    )
                    deduplicate_and_reparent_track(
                        session=session,
                        media_path=path,
                        track_dto=track_obj,
                        metadata=tags,
                    )
                with db_write_lease(task_name="library_watcher"):
                    session.commit()
            logger.info("Watcher: DB upsert complete for '%s' by '%s'", title, artist_name)
        except Exception as db_err:
            logger.error("Watcher: DB upsert failed for %s: %s", path.name, db_err)

        # ── 3. Emit TRACK_IMPORTED via the event bus ───────────────────────
        # The DownloadManager listens for this event and will silently cancel
        # any queued downloads whose ISRC matches the newly arrived file.
        payload: dict[str, Any] = {
            "event": "TRACK_IMPORTED",
            "track": {
                "title": title,
                "artist_name": artist_name,
                "album_title": album_title,
                "duration_ms": duration_ms,
                "isrc": isrc,
                "file_path": str(path),
                "source": "local_server",
            },
        }
        event_bus.publish(payload)  # type: ignore[union-attr]
        logger.info(
            "Watcher: emitted TRACK_IMPORTED for '%s' by '%s' (ISRC: %s)",
            title,
            artist_name,
            isrc or "n/a",
        )

    except Exception as exc:
        logger.error(
            "Watcher: unexpected error processing %s: %s",
            path,
            exc,
            exc_info=True,
        )


# ── Service class ──────────────────────────────────────────────────────────────


class LibraryWatcherService:
    """
    Manages the watchdog Observer lifecycle.

    Usage:
        watcher = LibraryWatcherService()
        watcher.start()          # non-blocking; observer runs in a daemon thread
        …
        watcher.stop()           # graceful shutdown
    """

    def __init__(self) -> None:
        self._observer: Any = None  # watchdog Observer — no PEP 484 stubs shipped
        self._handler: _AudioEventHandler | None = None
        self._started = False

    def start(self) -> None:
        """
        Resolve the local music library directory from config and start the OS watcher.

        Architectural Invariant:
        library_watcher must exclusively monitor the local music library directory
        (/data/library), NEVER the intake/downloads directory (/data/downloads).
        The intake/downloads directory is monitored exclusively by AutoImportService
        (5.0s debounce) so both watchers never race on incoming downloads.
        """
        if self._started:
            logger.warning("LibraryWatcherService.start() called more than once — ignoring")
            return

        library_path = config_manager.get_library_dir()
        if not library_path:
            logger.warning("LibraryWatcherService: library directory is not configured — watcher disabled")
            return

        try:
            library_path.mkdir(parents=True, exist_ok=True)
        except Exception as mk_err:
            logger.warning(
                "LibraryWatcherService: failed to create library directory (%s): %s — watcher disabled",
                library_path,
                mk_err,
            )
            return

        self._handler = _AudioEventHandler()
        self._observer = Observer()
        assert self._observer is not None
        self._observer.schedule(
            self._handler,
            str(library_path),
            recursive=True,
        )
        self._observer.start()
        self._started = True
        try:
            from core.task_manager.models import (
                OwnerType,
                ProcessCategory,
                ProcessOwner,
            )
            from core.task_manager.supervisor import supervisor

            self._reg_id = supervisor.register_process(
                ProcessOwner(
                    owner_id="core.library_watcher",
                    owner_type=OwnerType.CORE,
                    task_name="Library File Watcher",
                    category=ProcessCategory.WORKER_THREAD,
                    is_killable=True,
                    thread_id=getattr(self._observer, "ident", None),
                )
            )
        except Exception:
            pass
        logger.info(
            "LibraryWatcherService started — monitoring library directory '%s' (recursive)",
            library_path,
        )

    def stop(self) -> None:
        """Gracefully stop the observer thread and cancel pending debounce timers."""
        if not self._started:
            return

        if getattr(self, "_reg_id", None):
            try:
                from core.task_manager.supervisor import supervisor

                supervisor.unregister_process(self._reg_id)
                self._reg_id = None
            except Exception:
                pass

        if self._handler is not None:
            self._handler.cancel_all()

        if self._observer is not None:
            self._observer.stop()
            try:
                self._observer.join(timeout=5)
            except Exception as exc:
                logger.warning("LibraryWatcherService: error joining observer thread: %s", exc)

        self._started = False
        logger.info("LibraryWatcherService stopped")


# ── Module-level singleton ─────────────────────────────────────────────────────

_watcher_instance: LibraryWatcherService | None = None
_watcher_lock = threading.Lock()


def get_library_watcher() -> LibraryWatcherService:
    """Return the process-wide LibraryWatcherService singleton (lazy-init)."""
    global _watcher_instance
    if _watcher_instance is None:
        with _watcher_lock:
            if _watcher_instance is None:
                _watcher_instance = LibraryWatcherService()
    return _watcher_instance
