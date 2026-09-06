from core.nexus_framework.plugin_loader import generate_plugin_id

"""
Metadata Enhancer Service - Service for identifying and tagging audio.

This service focuses on:
1. Fingerprinting audio (AcoustID)
2. Fetching metadata (MusicBrainz)
3. Tagging files (echosync_core)
4. Managing the Review Queue (Database)

It does NOT move files or scan directories (see AutoImportService).
"""

import datetime
import re
from pathlib import Path
from typing import Any

import echosync_core  # pyright: ignore[reportMissingImports]
from sqlalchemy.exc import OperationalError  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm.attributes import (  # pyright: ignore[reportMissingImports]
    flag_modified,  # pyright: ignore[reportMissingImports]
)

from core.db.echo_sync_track import EchosyncTrack
from core.enums import Capability
from core.hook_manager import hook_manager
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_EXACT_SYNC
from core.matching_engine.text_utils import (
    extract_version_info,
    normalize_track_comparison_fields,
)
from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
from core.tiered_logger import get_logger
from database.working_database import ReviewTask, get_working_database

logger = get_logger("services.metadata_enhancer")


class MetadataWriteVerificationError(Exception):
    """Raised when audio tag write-and-verify roundtrip fails."""


# ── DIAGNOSTIC FLAG ────────────────────────────────────────────────────────────
# Set True to bypass ALL network calls (Steps 2.5 / 3 / 4 / 5).
# Only MBIDs already embedded in file tags are saved.  Tracks with no embedded
# MBID have their plugin-required keys stamped and are left with musicbrainz_id
# = NULL so real processing can run later.  Flips back to False for production.
_NETWORK_DISABLED = False
# ───────────────────────────────────────────────────────────────────────────────


def _title_similarity(a: str, b: str) -> float:
    """Jaccard word-set similarity for comparing track titles (case-insensitive)."""
    if a == b:
        return 1.0
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _track_entry_to_metadata(track: dict[str, Any]) -> dict[str, Any]:
    """Convert an album_cache track entry to the standard identify_file return format."""
    return {
        "title": track.get("title"),
        "recording_id": track.get("recording_id"),
        "artist": track.get("artist"),
        "artist_id": "",
        "album": track.get("album"),
        "release_id": track.get("release_id"),
        "date": track.get("date"),
        "track_number": track.get("track_number"),
        "disc_number": track.get("disc_number"),
        "cover_art_url": track.get("cover_art_url"),
        "isrc": track.get("isrc"),
    }


def _match_from_album_cache(
    file_path: Path,
    album_cache: dict[str, Any],
) -> "tuple[dict[str, Any] | None, float] | None":
    """Try to match *file_path* against any release stored in *album_cache*.

    Matching priority:
    1. ID3 ``track_number`` (+ disc_number) exact match → confidence 0.90
    2. Title Jaccard word-set similarity ≥ 0.85     → confidence 0.88

    Returns a ``(metadata, confidence)`` tuple on a hit, or ``None``.
    """
    try:
        tags = echosync_core.extract_metadata(str(file_path))
    except Exception:
        return None

    tag_title = str(tags.get("title") or "").strip().lower()
    raw_track_num = tags.get("track_number") or tags.get("tracknumber")
    raw_disc_num = tags.get("disc_number") or tags.get("discnumber") or "1"
    try:
        tag_track_num: int | None = int(str(raw_track_num).split("/")[0].strip())
    except (TypeError, ValueError):
        tag_track_num = None
    try:
        tag_disc_num = int(str(raw_disc_num).split("/")[0].strip())
    except (TypeError, ValueError):
        tag_disc_num = 1

    for _release_id, release_data in album_cache.items():
        tracks = release_data.get("tracks") or []

        # Priority 1: exact track number + disc number
        if tag_track_num is not None:
            for t in tracks:
                if (
                    t.get("track_number") == tag_track_num
                    and (t.get("disc_number") or 1) == tag_disc_num
                ):
                    logger.info(
                        "Album cache HIT (disc %d, track %d): %s → %s",
                        tag_disc_num,
                        tag_track_num,
                        file_path.name,
                        t.get("title"),
                    )
                    return _track_entry_to_metadata(t), 0.90

        # Priority 2: title word-set similarity
        if tag_title:
            for t in tracks:
                cache_title = str(t.get("title") or "").strip().lower()
                if cache_title and _title_similarity(tag_title, cache_title) >= 0.85:
                    logger.info(
                        "Album cache HIT (title match): %s → %s",
                        file_path.name,
                        t.get("title"),
                    )
                    return _track_entry_to_metadata(t), 0.88

    return None


def _tagging_write(file_path: Any, tags: dict[str, Any]) -> None:
    """
    Write physical audio tags to a file via echosync_core.
    If PyO3 bindings for physical tag writing are not exposed for a specific format,
    fails gracefully.
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning("_tagging_write: file does not exist at %s", path)
        return

    tags_dict = {str(k): str(v) for k, v in tags.items() if v not in (None, "")}
    if not tags_dict:
        return

    try:
        if hasattr(echosync_core, "write_metadata"):
            echosync_core.write_metadata(str(path), tags_dict)
            logger.debug(
                "_tagging_write: wrote tags to %s via echosync_core", path.name
            )
        elif hasattr(echosync_core, "write_tags"):
            echosync_core.write_tags(str(path), tags_dict)
            logger.debug(
                "_tagging_write: wrote tags to %s via echosync_core", path.name
            )
        else:
            logger.debug(
                "_tagging_write: physical tag writing not yet exposed in echosync_core for %s",
                path.name,
            )
    except Exception as e:
        logger.warning(
            "_tagging_write: failed writing tags to %s via echosync_core: %s",
            path.name,
            e,
        )


def build_native_tag_payload(track: dict[str, Any]) -> dict[str, Any]:
    """
    Construct standardized downstream physical tag payload for audio writers.

    Ensures:
    - Primary TITLE receives display_title (including clean edition/version string).
    - Sort title TSOT receives clean canonical title.
    - SUBTITLE / VERSION / TIT3 receives extracted edition/version string.
    - MBID, ISRC, AcoustID, track/disc numbers, artist, album, date are populated.
    """
    version = track.get("version") or track.get("edition")
    raw_title = track.get("title", "") or ""

    # Construct display title if version exists and is not already present
    if version and str(version).lower() not in raw_title.lower():
        display_title = f"{raw_title} ({version})"
    else:
        display_title = track.get("display_title") or raw_title

    mbid = (
        track.get("musicbrainz_track_id")
        or track.get("musicbrainz_trackid")
        or track.get("mbid")
        or track.get("musicbrainz_id")
        or track.get("recording_id")
    )
    year_val = track.get("release_year") or track.get("year") or track.get("date")

    payload = {
        "title": display_title,
        "display_title": display_title,
        "sort_title": raw_title,
        "subtitle": str(version) if version else "",
        "version": str(version) if version else "",
        "artist": track.get("artist") or track.get("artist_name") or "",
        "album": track.get("album_title") or track.get("album") or "",
        "album_artist": track.get("album_artist") or track.get("albumartist") or "",
        "albumartist": track.get("album_artist") or track.get("albumartist") or "",
        "date": str(year_val) if year_val is not None else "",
        "year": str(year_val) if year_val is not None else "",
        "track_number": str(track.get("track_number"))
        if track.get("track_number") is not None
        else "",
        "disc_number": str(track.get("disc_number"))
        if track.get("disc_number") is not None
        else "",
        "genre": track.get("genre") or "",
        "isrc": track.get("isrc") or "",
        "musicbrainz_track_id": mbid or "",
        "musicbrainz_trackid": mbid or "",
        "musicbrainz_id": mbid or "",
        "recording_id": mbid or "",
        "musicbrainz_album_id": track.get("musicbrainz_album_id")
        or track.get("mb_release_id")
        or track.get("release_id")
        or "",
        "repack_source": track.get("repack_source") or "",
        "repack_release_mbid": track.get("repack_release_mbid") or "",
        "musicbrainz_release_group_id": track.get("musicbrainz_release_group_id")
        or track.get("release_group_id")
        or "",
        "acoustid_id": track.get("acoustid_id") or "",
        "cover_art_url": track.get("cover_art_url") or "",
    }
    return payload


def normalize_singles_metadata(track: Any) -> Any:
    """
    Normalizes metadata for single releases and standalone recordings:
    Intercepts placeholders '[standalone recordings]', '[non-album tracks]', or empty album,
    and normalizes album to 'Singles' and release_type to 'single'.
    Supports dict and object interfaces.
    """
    is_dict = isinstance(track, dict)
    album_val = (
        (track.get("album") or track.get("album_title") or "")
        if is_dict
        else (
            getattr(track, "album", None) or getattr(track, "album_title", None) or ""
        )
    )
    album_str = str(album_val).strip()
    album_lower = album_str.lower()
    rel_type = (
        (track.get("release_type") or "")
        if is_dict
        else (getattr(track, "release_type", None) or "")
    )

    is_single_or_standalone = rel_type in ("single", "standalone") or album_lower in (
        "[standalone recordings]",
        "[non-album tracks]",
        "standalone recordings",
        "non-album tracks",
        "unknown album",
        "singles",
        "",
    )

    if is_single_or_standalone:
        if is_dict:
            track["album"] = "Singles"
            track["album_title"] = "Singles"
            track["release_type"] = "single"
            track["is_single"] = True
        else:
            if hasattr(track, "album"):
                track.album = "Singles"
            if hasattr(track, "album_title"):
                track.album_title = "Singles"
            if hasattr(track, "release_type"):
                track.release_type = "single"
            if hasattr(track, "is_single"):
                track.is_single = True

    return track


def realign_repack_metadata(track: Any, studio_release_data: dict[str, Any]) -> Any:
    """
    Realigns compilation/repack tracks to their canonical studio album while preserving
    compilation provenance in repack_source and repack_release_mbid.
    """
    if not studio_release_data:
        return track

    is_dict = isinstance(track, dict)
    current_album = (
        (track.get("album") or track.get("album_title") or "")
        if is_dict
        else (
            getattr(track, "album", None) or getattr(track, "album_title", None) or ""
        )
    )
    current_mbid = (
        (track.get("musicbrainz_album_id") or track.get("release_id") or "")
        if is_dict
        else (
            getattr(track, "musicbrainz_album_id", None)
            or getattr(track, "mb_release_id", None)
            or ""
        )
    )

    canonical_album = studio_release_data.get("canonical_studio_album")
    canonical_mbid = studio_release_data.get("canonical_studio_release_mbid")
    canonical_rgid = studio_release_data.get("canonical_studio_release_group_mbid")
    canonical_year = studio_release_data.get("canonical_year")

    if is_dict:
        track["repack_source"] = str(current_album)
        track["repack_release_mbid"] = str(current_mbid)
        if canonical_album:
            track["album"] = canonical_album
            track["album_title"] = canonical_album
        if canonical_mbid:
            track["musicbrainz_album_id"] = canonical_mbid
        if canonical_rgid:
            track["musicbrainz_release_group_id"] = canonical_rgid
            track["release_group_id"] = canonical_rgid
        if canonical_year:
            track["year"] = canonical_year
            track["release_year"] = canonical_year
            track["date"] = str(canonical_year)
    else:
        if hasattr(track, "repack_source"):
            track.repack_source = str(current_album)
        if hasattr(track, "repack_release_mbid"):
            track.repack_release_mbid = str(current_mbid)
        if canonical_album:
            if hasattr(track, "album"):
                track.album = canonical_album
            if hasattr(track, "album_title"):
                track.album_title = canonical_album
        if canonical_mbid and hasattr(track, "musicbrainz_album_id"):
            track.musicbrainz_album_id = canonical_mbid
        if canonical_rgid:
            if hasattr(track, "release_group_id"):
                track.release_group_id = canonical_rgid
        if canonical_year:
            if hasattr(track, "release_year"):
                track.release_year = canonical_year
            if hasattr(track, "year"):
                track.year = canonical_year

    return track


def apply_ensemble_disambiguation(track: Any, parent_ensemble_name: str) -> Any:
    """
    Sets album_artist to the parent ensemble (e.g. ATEEZ, Wu-Tang Clan) while preserving
    the performing member on artist / track_artist.
    """
    if not parent_ensemble_name:
        return track

    is_dict = isinstance(track, dict)
    if is_dict:
        track["album_artist"] = parent_ensemble_name
        track["albumartist"] = parent_ensemble_name
    else:
        if hasattr(track, "album_artist"):
            track.album_artist = parent_ensemble_name
        if hasattr(track, "albumartist"):
            track.albumartist = parent_ensemble_name

    return track


class RetroactiveEnhancer:
    """Background service for library-wide batch metadata enhancement."""

    def __init__(self):
        self._local_chromaprint_cache: dict[str, dict[str, Any]] = {}

    def backfill_missing_fingerprints(
        self,
        batch_size: int = 50,
        progress_callback: Any | None = None,
        max_items: int | None = None,
    ) -> int:
        """Scan LocalMedia records lacking an AudioFingerprint and backfill using fast-path native Rust fingerprinting.

        Commits in batches of 50 to avoid SQLite lock contention and reports progress over event_bus.
        """
        import os
        import uuid
        from core.event_bus import event_bus
        from core.matching_engine.fingerprinting import FingerprintGenerator
        from core.utils import PathMapper
        from database.music_database import AudioFingerprint, LocalMedia, get_database

        db = get_database()
        generated_count = 0

        try:
            with db.session_scope() as session:
                unfingerprinted_ids = [
                    row[0]
                    for row in session.query(LocalMedia.id)
                    .outerjoin(
                        AudioFingerprint,
                        LocalMedia.media_id == AudioFingerprint.media_id,
                    )
                    .filter(
                        (AudioFingerprint.id.is_(None))
                        | (AudioFingerprint.chromaprint.is_(None))
                        | (AudioFingerprint.chromaprint == "")
                    )
                    .all()
                ]

            if not unfingerprinted_ids:
                return 0

            if max_items:
                unfingerprinted_ids = unfingerprinted_ids[:max_items]

            total = len(unfingerprinted_ids)
            logger.info(
                "[enhancer] Native Fingerprinting Pre-Pass: Found %d media file(s) missing fingerprints. Computing in batches of %d...",
                total,
                batch_size,
            )

            processed = 0
            for i in range(0, total, batch_size):
                batch_ids = unfingerprinted_ids[i : i + batch_size]
                with db.session_scope() as session:
                    media_batch = (
                        session.query(LocalMedia)
                        .filter(LocalMedia.id.in_(batch_ids))
                        .all()
                    )
                    for media in media_batch:
                        fpath = media.file_path
                        if not fpath:
                            continue
                        local_path = (
                            PathMapper.to_local(fpath)
                            if (os.path.isabs(fpath) or not os.path.exists(fpath))
                            else fpath
                        )
                        if not os.path.exists(local_path):
                            local_path = PathMapper.to_local(fpath)
                        if not local_path or not os.path.exists(local_path):
                            continue

                        fp = None
                        # Fast-path: native Rust audio fingerprinting (~10ms per track)
                        try:
                            import echosync_core

                            if hasattr(echosync_core, "fingerprint_audio"):
                                res = echosync_core.fingerprint_audio(
                                    str(local_path), trim_silence=True
                                )
                                if res:
                                    fp = (
                                        res[0]
                                        if isinstance(res, (tuple, list))
                                        else res
                                    )
                        except Exception as rust_err:
                            logger.debug(
                                "Native fingerprint_audio failed for %s: %s",
                                local_path,
                                rust_err,
                            )

                        # Fallback to FingerprintGenerator if native Rust extension threw or returned None
                        if not fp:
                            try:
                                fp = FingerprintGenerator.generate(str(local_path))
                            except Exception as fp_err:
                                logger.debug(
                                    "Fallback FingerprintGenerator failed for %s: %s",
                                    local_path,
                                    fp_err,
                                )

                        if fp:
                            if not media.media_id:
                                media.media_id = f"med_{uuid.uuid4().hex[:12]}"

                            existing_afp = (
                                session.query(AudioFingerprint)
                                .filter_by(media_id=media.media_id)
                                .first()
                            )
                            if existing_afp:
                                existing_afp.chromaprint = fp
                            else:
                                session.add(
                                    AudioFingerprint(
                                        media_id=media.media_id,
                                        chromaprint=fp,
                                    )
                                )
                            generated_count += 1

                processed += len(batch_ids)
                status_msg = f"Fingerprinted {processed}/{total} audio files ({round((processed / total) * 100, 1)}%)"
                if progress_callback:
                    try:
                        progress_callback(processed, total, status_msg)
                    except Exception:
                        pass
                try:
                    event_bus.publish(
                        "job_progress",
                        {
                            "job_name": "retroactive_metadata_enhancement",
                            "phase": "fingerprinting",
                            "current": processed,
                            "total": total,
                            "status": status_msg,
                            "percentage": (
                                round((processed / total) * 100, 1) if total > 0 else 0
                            ),
                        },
                    )
                except Exception as eb_err:
                    logger.debug("Failed to publish job_progress: %s", eb_err)

            logger.info(
                "[enhancer] Native fingerprinting pre-pass complete: backfilled %d fingerprints.",
                generated_count,
            )
            return generated_count
        except Exception as e:
            logger.error(
                "[enhancer] Error during native fingerprinting pre-pass: %s",
                e,
                exc_info=True,
            )
            return generated_count

    def resolve_canonical_from_chromaprint(
        self,
        session: Any | None = None,
        chromaprint: str = "",
        current_track_id: int | None = None,
        exclude_track_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Inspect in-memory cache and query music.db for peer tracks sharing the exact chromaprint.

        Adopts canonical metadata from already-enhanced tracks with valid MusicBrainz IDs to short-circuit
        external network requests.
        """
        # Handle parameter flexibility: resolve_canonical_from_chromaprint(session, chromaprint, current_track_id)
        # or resolve_canonical_from_chromaprint(chromaprint, exclude_track_id=...)
        if isinstance(session, str):
            chromaprint = session
            session = None

        if not chromaprint:
            return None

        target_track_id = (
            current_track_id if current_track_id is not None else exclude_track_id
        )

        # 1. Check in-memory session cache first
        if chromaprint in self._local_chromaprint_cache:
            cached = self._local_chromaprint_cache[chromaprint]
            logger.info(
                "[enhancer] Metadata resolved via local chromaprint cache for track %s",
                target_track_id,
            )
            return cached

        from database.music_database import (
            AudioFingerprint,
            LocalMedia,
            Track,
            get_database,
        )

        def _do_lookup(sess):
            query = (
                sess.query(Track)
                .join(LocalMedia, LocalMedia.track_id == Track.id)
                .join(
                    AudioFingerprint, AudioFingerprint.media_id == LocalMedia.media_id
                )
                .filter(
                    AudioFingerprint.chromaprint == chromaprint,
                    Track.musicbrainz_id.isnot(None),
                    Track.musicbrainz_id != "",
                    Track.musicbrainz_id != "NOT_FOUND",
                )
            )
            if target_track_id is not None:
                query = query.filter(Track.id != target_track_id)

            # Prefer tracks with non-empty titles
            query = query.filter(Track.title.isnot(None), Track.title != "")
            return query.first()

        def _extract_meta(peer_track):
            if not peer_track:
                return None
            artist_name = peer_track.artist.name if peer_track.artist else None
            album_title = peer_track.album.title if peer_track.album else None
            release_mbid = peer_track.album.mb_release_id if peer_track.album else None
            year = peer_track.year

            return {
                "title": peer_track.title,
                "artist": artist_name,
                "artist_name": artist_name,
                "album": album_title,
                "album_title": album_title,
                "year": year,
                "isrc": peer_track.isrc,
                "musicbrainz_id": peer_track.musicbrainz_id,
                "musicbrainz_track_id": peer_track.musicbrainz_id,
                "recording_id": peer_track.musicbrainz_id,
                "release_mbid": release_mbid,
                "track_number": peer_track.track_number,
                "disc_number": peer_track.disc_number,
                "duration": peer_track.duration,
            }

        result = None
        if session is not None:
            peer_track = _do_lookup(session)
            result = _extract_meta(peer_track)
        else:
            db = get_database()
            with db.session_scope() as sess:
                peer_track = _do_lookup(sess)
                result = _extract_meta(peer_track)

        if result:
            logger.info(
                "[enhancer] Metadata resolved via local chromaprint cache for track %s",
                target_track_id,
            )
            self._local_chromaprint_cache[chromaprint] = result
            return result

        return None

    def generate_preview_path(
        self, template: str, sample_data: dict[str, Any] | None = None
    ) -> str:
        """Preview file destination path based on template and sample/default metadata."""
        from core.path_formatter import build_destination_path

        data = sample_data or {
            "artist": "Daft Punk",
            "album": "Random Access Memories",
            "title": "Get Lucky",
            "track_number": "01",
            "year": "2013",
            "version": "",
        }
        dest = build_destination_path("/Music", template, data, "flac")
        return dest.as_posix()

    def _get_plugin(
        self, capability: Capability, required_algorithm: str | None = None
    ):

        plugins = PluginRegistry.get_plugins_with_capability(capability)
        for p in plugins:
            if not required_algorithm:
                return p

            # Check algorithm support if required
            caps = getattr(p, "capabilities", None)
            if caps and capability == Capability.RESOLVE_FINGERPRINT:
                algorithms = getattr(caps, "fingerprint_algorithms", []) or []
                if not algorithms and getattr(caps, "supports_fingerprinting", False):
                    algorithms = ["chromaprint"]  # Default legacy
                if required_algorithm in algorithms:
                    return p

        return None

    def _get_mb_plugin(self):
        from core.nexus_framework.plugin_loader import (
            PluginRegistry,
            generate_plugin_id,
        )

        return (
            PluginRegistry.get_plugin(generate_plugin_id("EchoSync.musicbrainz"))
            or PluginRegistry.get_plugin("EchoSync.musicbrainz")
            or PluginRegistry.get_plugin("musicbrainz")
            or self._get_plugin(Capability.FETCH_METADATA)
        )

    def _get_spotify_plugin(self):
        from core.nexus_framework.plugin_loader import (
            PluginRegistry,
            generate_plugin_id,
        )

        return (
            PluginRegistry.get_plugin(generate_plugin_id("EchoSync.spotify"))
            or PluginRegistry.get_plugin("EchoSync.spotify")
            or PluginRegistry.get_plugin("spotify")
        )

    def identify_file(self, file_path: Path) -> tuple[dict[str, Any] | None, float]:
        """
        Identify a file using Fingerprinting and/or Metadata Search.
        Returns (metadata, confidence_score).

        On failure: Returns (None, 0.0) - file will be marked for manual review.
        """
        fingerprint_provider = self._get_plugin(
            Capability.RESOLVE_FINGERPRINT, required_algorithm="chromaprint"
        )
        metadata_provider = self._get_plugin(Capability.FETCH_METADATA)

        metadata = None
        confidence = 0.0

        try:
            # Step 1: Extract native file tags via echosync_core
            track_obj = None
            raw_tags = {}
            duration_ms = None
            duration_sec = None

            try:
                import echosync_core  # pyright: ignore[reportMissingImports]

                raw_tags = echosync_core.extract_metadata(str(file_path)) or {}

                # Support both echosync_core native keys and legacy fallback keys
                raw_dur_ms = raw_tags.get("duration_ms")
                if raw_dur_ms is not None:
                    duration_ms = int(raw_dur_ms)
                    duration_sec = duration_ms / 1000.0
                elif raw_tags.get("duration") is not None:
                    duration_sec = float(raw_tags["duration"])
                    duration_ms = int(duration_sec * 1000)

                mbid = (
                    raw_tags.get("mbid")
                    or raw_tags.get("musicbrainz_id")
                    or raw_tags.get("musicbrainz_trackid")
                )

                raw_t = raw_tags.get("title") or ""
                raw_a = raw_tags.get("artist") or raw_tags.get("artist_name") or ""
                raw_alb = raw_tags.get("album") or raw_tags.get("album_title") or ""

                from core.db.echo_sync_track import EchosyncMedia

                media_item = EchosyncMedia(
                    file_path=str(file_path),
                    file_format=raw_tags.get("file_format")
                    or file_path.suffix.lstrip(".").lower(),
                    bitrate=raw_tags.get("bitrate"),
                    sample_rate=raw_tags.get("sample_rate"),
                    bit_depth=raw_tags.get("bit_depth"),
                    channels=raw_tags.get("channels"),
                )

                track_obj = EchosyncTrack(
                    raw_title=raw_t,
                    artist_name=raw_a,
                    album_title=raw_alb,
                    media=[media_item],
                )
                if duration_ms:
                    track_obj.duration = int(duration_ms)
                if raw_tags.get("track_number") or raw_tags.get("track_no"):
                    try:
                        track_obj.track_number = int(
                            str(
                                raw_tags.get("track_number") or raw_tags.get("track_no")
                            ).split("/")[0]
                        )
                    except:
                        pass
                if raw_tags.get("disc_number") or raw_tags.get("disc_no"):
                    try:
                        track_obj.disc_number = int(
                            str(
                                raw_tags.get("disc_number") or raw_tags.get("disc_no")
                            ).split("/")[0]
                        )
                    except:
                        pass
                if raw_tags.get("year") or raw_tags.get("date"):
                    try:
                        val = str(raw_tags.get("year") or raw_tags.get("date"))
                        track_obj.release_year = int(val[:4])
                    except:
                        pass
                if mbid:
                    track_obj.musicbrainz_id = mbid
                if raw_tags.get("isrc"):
                    track_obj.isrc = raw_tags["isrc"]
            except Exception as e:
                logger.warning(
                    f"Failed to read native tags via echosync_core for {file_path.name}: {e}"
                )

            if not track_obj:
                track_obj = EchosyncTrack(raw_title="", artist_name="", album_title="")

            # Filename fallback for files lacking embedded tags (common in raw WAV downloads)
            if not track_obj.artist_name or not (
                track_obj.title or track_obj.raw_title
            ):
                try:
                    from core.matching_engine.track_parser import TrackParser

                    parsed = TrackParser.parse_filename(file_path.name)
                    if parsed:
                        if (
                            getattr(parsed, "artist_name", None)
                            and not track_obj.artist_name
                        ):
                            track_obj.artist_name = parsed.artist_name
                        if getattr(parsed, "title", None) and not (
                            track_obj.title or track_obj.raw_title
                        ):
                            track_obj.title = parsed.title
                            track_obj.raw_title = parsed.title
                        if (
                            getattr(parsed, "display_title", None)
                            and not track_obj.display_title
                        ):
                            track_obj.display_title = parsed.display_title
                        if (
                            getattr(parsed, "album_title", None)
                            and not track_obj.album_title
                        ):
                            track_obj.album_title = parsed.album_title
                except Exception as tp_err:
                    logger.debug(
                        f"TrackParser filename fallback error for {file_path.name}: {tp_err}"
                    )

            # Priority 1: Fast path: Check if tags contain an embedded MBID
            if track_obj and track_obj.musicbrainz_id and metadata_provider:
                logger.info(
                    f"Found MBID {track_obj.musicbrainz_id} in local_metadata tags for {file_path.name}"
                )
                try:
                    metadata = metadata_provider.get_metadata(track_obj.musicbrainz_id)
                    if metadata:
                        return metadata, 0.99
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch metadata for tag MBID {track_obj.musicbrainz_id}: {e}"
                    )

            # Priority 2: First-Class AcoustID Fingerprinting Ingestion
            # Generate Chromaprint fingerprint for unverified ingested files
            fingerprint = None
            try:
                fingerprint = FingerprintGenerator.generate(str(file_path))
            except Exception as fp_err:
                logger.debug(
                    f"Fingerprint generation failed for {file_path.name}: {fp_err}"
                )

            # Local Chromaprint cache check before outbound network requests
            if fingerprint:
                cached = self.resolve_canonical_from_chromaprint(
                    chromaprint=fingerprint
                )
                if cached:
                    logger.info(
                        f"[enhancer] Metadata resolved via local chromaprint cache: {file_path.name} → MBID: {cached.get('musicbrainz_id')}"
                    )
                    return cached, 0.95

            if fingerprint and duration_sec and fingerprint_provider:
                duration_sec_int = int(round(float(duration_sec)))
                logger.debug(
                    f"→ AcoustID Lookup: {file_path.name}\n"
                    f"  Duration: {duration_sec_int}s | Fingerprint: {len(fingerprint)} chars"
                )
                try:
                    acoustid_id = None
                    mbids = []
                    score = None
                    if hasattr(fingerprint_provider, "resolve_fingerprint_details"):  # type: ignore[attr-defined]
                        details = fingerprint_provider.resolve_fingerprint_details(
                            fingerprint, duration_sec_int
                        )  # type: ignore[attr-defined]
                        if isinstance(details, dict):
                            acoustid_id = details.get("acoustid_id")
                            mbids = details.get("mbids") or []
                            score = details.get("score")
                    elif hasattr(fingerprint_provider, "resolve_fingerprint"):  # type: ignore[attr-defined]
                        mbids = (
                            fingerprint_provider.resolve_fingerprint(
                                fingerprint, duration_sec_int
                            )
                            or []
                        )

                    if mbids and metadata_provider:
                        top_mbid = mbids[0]
                        logger.info(
                            f"✓ AcoustID identified: {file_path.name} → MBID: {top_mbid}"
                        )
                        try:
                            fetched = metadata_provider.get_metadata(top_mbid)
                            if fetched:
                                # Check duration delta between file and MusicBrainz recording
                                mb_dur = (
                                    fetched.get("length")
                                    or fetched.get("duration_ms")
                                    or fetched.get("duration")
                                )
                                if mb_dur:
                                    mb_dur_ms = (
                                        int(float(mb_dur) * 1000)
                                        if float(mb_dur) < 10000
                                        else int(mb_dur)
                                    )
                                    dur_delta = (
                                        abs(int(duration_ms) - mb_dur_ms)
                                        if duration_ms
                                        else 0
                                    )
                                else:
                                    dur_delta = 0

                                # Confirmed MBID with duration delta <= 2000ms gets confidence >= 0.90
                                if dur_delta <= 2000:
                                    confidence = 0.95
                                else:
                                    confidence = 0.88

                                if acoustid_id:
                                    fetched["acoustid_id"] = acoustid_id
                                fetched["musicbrainz_id"] = top_mbid
                                fetched["recording_id"] = top_mbid

                                # Normalize artist credits and extract version/edition info
                                raw_t = fetched.get("title") or ""
                                raw_a = fetched.get("artist") or ""
                                clean_t, clean_a = normalize_track_comparison_fields(
                                    raw_t, raw_a
                                )
                                _, ver_info = extract_version_info(raw_t)
                                if ver_info and not fetched.get("version"):
                                    fetched["version"] = ver_info

                                logger.info(
                                    f"  ✓ AcoustID metadata fetched: '{clean_t}' by '{clean_a}' "
                                    f"(duration delta: {dur_delta}ms, confidence: {confidence:.2f})"
                                )
                                return fetched, confidence
                        except Exception as e:
                            logger.warning(
                                f"Failed to fetch metadata for MBID {top_mbid}: {e}"
                            )
                    else:
                        logger.debug(
                            f"✗ No MBID found from AcoustID for {file_path.name}"
                        )
                except Exception as e:
                    logger.warning(f"AcoustID check failed: {e}")

            # Priority 3: ISRC Waterfall Resolution (if file tags contain an ISRC)
            isrc_val = (
                raw_tags.get("isrc") if isinstance(raw_tags, dict) else None
            ) or (track_obj.isrc if track_obj else None)
            if isrc_val:
                try:
                    from services.isrc_lookup_service import dispatch_isrc_lookup

                    isrc_track = dispatch_isrc_lookup(str(isrc_val).strip())
                    if isrc_track:
                        src_name = (
                            isrc_track.identifiers.get("source")
                            if isinstance(isrc_track.identifiers, dict)
                            else None
                        ) or "ISRC"
                        logger.info(
                            f"Identified file via ISRC waterfall from provider: {src_name}"
                        )
                        return {
                            "title": isrc_track.title,
                            "raw_title": getattr(isrc_track, "raw_title", None)
                            or getattr(isrc_track, "title", None)
                            or isrc_track.title,
                            "artist": isrc_track.artist_name,
                            "album": isrc_track.album_title,
                            "recording_id": isrc_track.identifiers.get(
                                "musicbrainz_id", ""
                            )
                            if isrc_track.identifiers
                            else "",
                            "release_id": isrc_track.identifiers.get(
                                "musicbrainz_release_group_id", ""
                            )
                            if isrc_track.identifiers
                            else "",
                            "track_number": isrc_track.track_number,
                            "isrc": isrc_track.isrc,
                            "date": isrc_track.release_year,
                        }, 0.92
                except Exception as isrc_err:
                    logger.warning(
                        f"ISRC waterfall lookup error for {file_path.name}: {isrc_err}"
                    )

            # Priority 4: Local metadata text search fallback
            if (
                track_obj
                and track_obj.title
                and track_obj.artist_name
                and metadata_provider
            ):
                logger.debug(
                    f"Attempting search fallback using local_metadata tags for {file_path.name}"
                )
                try:
                    # Sanitize noise in artist/title before querying/matching
                    clean_t, clean_a = normalize_track_comparison_fields(
                        track_obj.title, track_obj.artist_name
                    )
                    search_query_track = EchosyncTrack(
                        raw_title=clean_t,
                        artist_name=clean_a,
                        album_title=track_obj.album_title,
                        duration=track_obj.duration,
                    )
                    results = metadata_provider.search_metadata(
                        search_query_track, limit=10
                    )  # type: ignore[attr-defined]
                    if results:
                        if isinstance(results, EchosyncTrack):
                            results_list = [results]
                        elif isinstance(results, (list, tuple)):
                            results_list = list(results)
                        else:
                            results_list = [results]

                        candidate_tracks = []
                        for result in results_list:
                            if isinstance(result, EchosyncTrack):
                                candidate = result
                                mbid = result.musicbrainz_id
                                if not mbid and isinstance(result.identifiers, dict):
                                    mbid = result.identifiers.get(
                                        "musicbrainz_recording_id"
                                    ) or result.identifiers.get("mbid")
                            elif isinstance(result, dict):
                                candidate = self._search_result_to_track(result)
                                mbid = result.get("mbid") or result.get("recording_id")
                            else:
                                candidate = None
                                mbid = None

                            if candidate:
                                candidate_tracks.append((candidate, mbid))

                        if candidate_tracks:
                            from core.matching_engine.matching_engine import (
                                WeightedMatchingEngine,
                            )
                            from core.matching_engine.scoring_profile import (
                                PROFILE_EXACT_SYNC,
                            )

                            engine_cls = (
                                ServiceRegistry.resolve("matching_engine")
                                or WeightedMatchingEngine
                            )
                            matcher = engine_cls(PROFILE_EXACT_SYNC)
                            best_score = 0.0
                            best_mbid = None
                            best_candidate = None

                            for candidate, mbid in candidate_tracks:
                                match_result = matcher.calculate_match(
                                    search_query_track, candidate
                                )
                                score = (
                                    match_result.confidence_score
                                    if match_result
                                    else 0.0
                                )
                                if score > best_score:
                                    best_score = score
                                    best_mbid = mbid
                                    best_candidate = candidate

                            if best_score >= 85.0:
                                logger.info(
                                    f"✓ Matched '{file_path.name}' via local_metadata text search (score: {best_score:.1f}%)"
                                )
                                if best_mbid:
                                    metadata = metadata_provider.get_metadata(best_mbid)
                                    if metadata:
                                        return metadata, best_score / 100.0
                                if best_candidate:
                                    return best_candidate, best_score / 100.0
                    else:
                        logger.debug(
                            "No search results for fallback query using local_metadata"
                        )
                except Exception as e:
                    logger.warning(
                        f"Fallback search using local_metadata failed: {e}",
                        exc_info=True,
                    )

            # If all methods failed, return None, 0.0 for manual review
            logger.warning(
                f"All metadata identification methods failed for {file_path.name}. File will be queued for manual review."
            )
            return None, 0.0

        except Exception as e:
            logger.error(
                f"Unexpected error identifying {file_path}: {e}", exc_info=True
            )
            return None, 0.0

        return metadata, confidence

    def identify_batch(self, file_paths: list[str]) -> dict:
        results = {}
        for path_str in file_paths:
            metadata = None
            confidence = 0.0
            try:
                metadata, confidence = self.identify_file(Path(path_str))
            except Exception as e:
                logger.error(f"Error identifying {path_str}: {e}")
            results[path_str] = (metadata, confidence)

        return results

    def read_tags(self, file_path: Path) -> dict[str, Any]:
        """Read tags from a file using the internal tagging helper."""
        return echosync_core.extract_metadata(str(file_path))

    def tag_file_verified(self, file_path: Path, metadata: Any) -> dict[str, Any]:
        """Write metadata to physical audio file and verify roundtrip via readback.

        Raises MetadataWriteVerificationError if the written tags do not match
        the expected title/artist metadata.
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise MetadataWriteVerificationError(
                f"Cannot tag non-existent file: {path}"
            )

        meta_dict = (
            metadata
            if isinstance(metadata, dict)
            else (
                metadata.to_dict() if hasattr(metadata, "to_dict") else vars(metadata)
            )
        )
        payload = build_native_tag_payload(meta_dict)
        tags_to_write = {k: v for k, v in payload.items() if v not in (None, "")}

        if not tags_to_write:
            raise MetadataWriteVerificationError(
                f"No writable tags provided for {path.name}"
            )

        # Attempt to ensure write permissions on file and parent directory before native write
        try:
            current_mode = path.stat().st_mode
            if not (current_mode & 0o200):  # missing owner write permission
                path.chmod(current_mode | 0o664)
        except Exception:
            pass

        try:
            parent_dir = path.parent
            if parent_dir.exists():
                p_mode = parent_dir.stat().st_mode
                if not (p_mode & 0o200):
                    parent_dir.chmod(p_mode | 0o775)
        except Exception:
            pass

        try:
            if hasattr(echosync_core, "write_metadata"):
                echosync_core.write_metadata(str(path), tags_to_write)
            elif hasattr(echosync_core, "write_tags"):
                echosync_core.write_tags(str(path), tags_to_write)
            else:
                raise MetadataWriteVerificationError(
                    "No write_metadata implementation available in echosync_core"
                )
        except Exception as exc:
            raise MetadataWriteVerificationError(
                f"Native tag write failed for {path.name}: {exc}"
            ) from exc

        # Immediate readback verification
        try:
            if hasattr(echosync_core, "read_metadata"):
                verified_tags = echosync_core.read_metadata(str(path))
            else:
                verified_tags = echosync_core.extract_metadata(str(path))
        except Exception as exc:
            raise MetadataWriteVerificationError(
                f"Post-write tag extraction failed for {path.name}: {exc}"
            ) from exc

        if not isinstance(verified_tags, dict):
            raise MetadataWriteVerificationError(
                f"Extracted metadata is not a dictionary for {path.name}"
            )

        exp_t = (
            tags_to_write.get("title")
            or meta_dict.get("title")
            or getattr(metadata, "title", None)
            or ""
        )
        exp_a = (
            tags_to_write.get("artist")
            or meta_dict.get("artist")
            or getattr(metadata, "artist", None)
            or ""
        )
        exp_isrc = (
            tags_to_write.get("isrc")
            or meta_dict.get("isrc")
            or getattr(metadata, "isrc", None)
            or ""
        )

        read_title = (verified_tags.get("title") or "").strip().lower()
        expected_title = str(exp_t).strip().lower()
        read_artist = (
            (verified_tags.get("artist") or verified_tags.get("artist_name") or "")
            .strip()
            .lower()
        )
        expected_artist = str(exp_a).strip().lower()
        read_isrc = (verified_tags.get("isrc") or "").strip().lower()
        expected_isrc = str(exp_isrc).strip().lower()

        def _titles_match(t1: str, t2: str) -> bool:
            if not t1 or not t2:
                return True
            if t1 == t2:
                return True
            aliases_1 = re.findall(
                r"[\(\[\{（【《「『]([^()\[\]{}（）】》」「』]+)[\)\]\}）】》」「』]",
                t1,
            )
            aliases_2 = re.findall(
                r"[\(\[\{（【《「『]([^()\[\]{}（）】》」「』]+)[\)\]\}）】》」「』]",
                t2,
            )
            base_1 = re.sub(
                r"[\(\[\{（【《「『][^()\[\]{}（）】》」「』]+[\)\]\}）】》」「』]",
                "",
                t1,
            ).strip()
            base_2 = re.sub(
                r"[\(\[\{（【《「『][^()\[\]{}（）】》」「』]+[\)\]\}）】》」「』]",
                "",
                t2,
            ).strip()

            variants_1 = [v.strip() for v in [t1, base_1] + aliases_1 if v.strip()]
            variants_2 = [v.strip() for v in [t2, base_2] + aliases_2 if v.strip()]

            for v1 in variants_1:
                for v2 in variants_2:
                    if v1 == v2:
                        return True
                    if len(v1) >= 3 and len(v2) >= 3 and (v1 in v2 or v2 in v1):
                        return True
            return False

        def _artists_match(a1: str, a2: str) -> bool:
            if not a1 or not a2:
                return True
            if a1 == a2:
                return True
            if a1 in a2 or a2 in a1:
                return True
            return False

        if (expected_title and not _titles_match(read_title, expected_title)) or (
            expected_artist and not _artists_match(read_artist, expected_artist)
        ):
            raise MetadataWriteVerificationError(
                f"Tag verification failed for {path.name}: "
                f"title ('{read_title}' vs '{expected_title}'), "
                f"artist ('{read_artist}' vs '{expected_artist}')"
            )

        if expected_isrc and read_isrc != expected_isrc:
            raise MetadataWriteVerificationError(
                f"Tag verification failed for {path.name}: "
                f"isrc ('{read_isrc}' vs '{expected_isrc}')"
            )

        logger.info(
            "tag_file_verified: successfully verified tags for %s (title='%s', artist='%s', isrc='%s')",
            path.name,
            read_title,
            read_artist,
            read_isrc,
        )
        return verified_tags

    def tag_file(
        self, file_path: Path, metadata: dict[str, Any], verify: bool = True
    ) -> None:
        """Write *metadata* to the physical audio file at *file_path*.

        Translates the flat metadata dict produced by ``identify_file`` /
        ``auto_importer`` into the tag keys understood by ``_tagging_write``,
        then writes them via echosync_core. When verify=True, strictly validates the write
        with an immediate readback check; if verification fails, MetadataWriteVerificationError
        is raised and the operation is aborted.
        """
        if verify:
            self.tag_file_verified(file_path, metadata)
            return

        payload = build_native_tag_payload(metadata)
        tags_to_write = {k: v for k, v in payload.items() if v not in (None, "")}

        if not tags_to_write:
            logger.debug(
                "tag_file: no writable tags for %s — skipping write.", file_path.name
            )
            return

        try:
            _tagging_write(file_path, tags_to_write)
            logger.info(
                "tag_file: wrote %d tag(s) to %s", len(tags_to_write), file_path.name
            )
        except Exception as exc:
            logger.warning(
                "tag_file: failed to write tags for %s: %s", file_path.name, exc
            )
            raise

    def create_or_update_review_task(
        self,
        file_path: Any,
        decision: Any = None,
        match_data: Any = None,
        confidence_score: float = 0.0,
        status: str = "pending",
    ) -> None:
        try:
            file_path_str = str(file_path)

            # Positional argument compatibility normalization
            if isinstance(decision, dict) and (
                isinstance(match_data, (float, int)) or match_data is None
            ):
                confidence_score = float(match_data) if match_data is not None else 1.0
                match_data = decision
                decision = "Approved match"

            if not confidence_score and isinstance(match_data, (float, int)):
                confidence_score = float(match_data)
                match_data = None

            # 1. Check if the task already exists by file_path
            db = get_working_database()
            with db.session_scope() as session:
                existing = (
                    session.query(ReviewTask)
                    .filter(ReviewTask.file_path == file_path_str)
                    .first()
                )

                # 2. Get/Create EchosyncTrack
                from core.db.echo_sync_track import EchosyncTrack
                from core.matching_engine.fingerprinting import FingerprintGenerator

                track = None
                try:
                    import echosync_core  # pyright: ignore[reportMissingImports]

                    raw_tags = echosync_core.extract_metadata(file_path_str) or {}
                    # Support both echosync_core native keys and legacy fallback keys
                    raw_dur_ms = raw_tags.get("duration_ms")
                    if raw_dur_ms is not None:
                        duration_ms = int(raw_dur_ms)
                        duration_sec = duration_ms / 1000.0
                    elif raw_tags.get("duration") is not None:
                        duration_sec = float(raw_tags["duration"])
                        duration_ms = int(duration_sec * 1000)
                    else:
                        duration_ms = None
                        duration_sec = None

                    mbid = (
                        raw_tags.get("mbid")
                        or raw_tags.get("musicbrainz_id")
                        or raw_tags.get("musicbrainz_trackid")
                    )
                    track = EchosyncTrack(
                        raw_title=raw_tags.get("title") or "",
                        artist_name=raw_tags.get("artist")
                        or raw_tags.get("artist_name")
                        or "",
                        album_title=raw_tags.get("album")
                        or raw_tags.get("album_title")
                        or "",
                    )
                    if duration_ms:
                        track.duration = int(duration_ms)
                    if raw_tags.get("track_number") or raw_tags.get("track_no"):
                        try:
                            track.track_number = int(
                                str(
                                    raw_tags.get("track_number")
                                    or raw_tags.get("track_no")
                                ).split("/")[0]
                            )
                        except:
                            pass
                    if raw_tags.get("disc_number") or raw_tags.get("disc_no"):
                        try:
                            track.disc_number = int(
                                str(
                                    raw_tags.get("disc_number")
                                    or raw_tags.get("disc_no")
                                ).split("/")[0]
                            )
                        except:
                            pass
                    if raw_tags.get("year") or raw_tags.get("date"):
                        try:
                            val = str(raw_tags.get("year") or raw_tags.get("date"))
                            track.release_year = int(val[:4])
                        except:
                            pass
                    if mbid:
                        track.musicbrainz_id = mbid
                    if raw_tags.get("isrc"):
                        track.isrc = raw_tags["isrc"]
                except Exception as parse_err:
                    logger.warning(
                        f"Failed to get track from file via echosync_core: {parse_err}"
                    )

                if not track:
                    track = EchosyncTrack(raw_title="", artist_name="", album_title="")

                # Local heuristic fallback when tags are absent/empty
                if not track.artist_name or not (track.title or track.raw_title):
                    try:
                        from core.matching_engine.track_parser import TrackParser

                        parsed_meta = TrackParser.parse_filename(file_path_str)
                        if parsed_meta:
                            parsed_artist = getattr(
                                parsed_meta, "artist", None
                            ) or getattr(parsed_meta, "artist_name", None)
                            parsed_title = getattr(
                                parsed_meta, "title", None
                            ) or getattr(parsed_meta, "raw_title", None)
                            if parsed_artist and not track.artist_name:
                                track.artist_name = parsed_artist
                            if parsed_title and not (track.title or track.raw_title):
                                track.title = parsed_title
                                track.raw_title = parsed_title
                            if (
                                getattr(parsed_meta, "display_title", None)
                                and not track.display_title
                            ):
                                track.display_title = parsed_meta.display_title
                            if (
                                getattr(parsed_meta, "album_title", None)
                                and not track.album_title
                            ):
                                track.album_title = parsed_meta.album_title
                    except Exception as tp_err:
                        logger.debug(
                            f"TrackParser filename fallback error for {file_path_str}: {tp_err}"
                        )

                from core.io_gatekeeper import Gatekeeper

                file_exists = False
                try:
                    Gatekeeper().authorize_and_execute(
                        {"operation": "validate_only", "target": file_path_str}
                    )
                    file_exists = Path(file_path_str).is_file()
                except Exception:
                    pass
                if file_exists and not track.fingerprint:
                    try:
                        fingerprint = FingerprintGenerator.generate(file_path_str)
                        if fingerprint:
                            track.fingerprint = fingerprint
                            track.fingerprint_confidence = 1.0  # type: ignore[attr-defined]
                    except Exception as fp_err:
                        logger.warning(
                            f"Failed to generate fingerprint for review task: {fp_err}"
                        )

                # 3. Merge incoming match_data (metadata suggestion) if present
                if isinstance(match_data, dict):
                    if match_data.get("title"):
                        track.raw_title = match_data["title"]
                        track.title = match_data["title"]
                        track.display_title = match_data["title"]
                    if match_data.get("artist"):
                        track.artist_name = match_data["artist"]
                    if match_data.get("album"):
                        track.album_title = match_data["album"]
                    if match_data.get("year"):
                        try:
                            track.release_year = int(match_data["year"])
                        except Exception:
                            pass
                    if match_data.get("track_number"):
                        try:
                            track.track_number = int(match_data["track_number"])
                        except Exception:
                            pass
                    if match_data.get("disc_number"):
                        try:
                            track.disc_number = int(match_data["disc_number"])
                        except Exception:
                            pass
                    if match_data.get("musicbrainz_id"):
                        track.musicbrainz_id = match_data["musicbrainz_id"]
                    if match_data.get("isrc"):
                        track.isrc = match_data["isrc"]
                    if match_data.get("duration"):
                        try:
                            track.duration = int(match_data["duration"])
                        except Exception:
                            pass

                track_dict = track.to_dict()

                # Ensure track_data dictionary contains structured artist_name, title, display_title, album_title
                # using TrackParser fallback if still missing
                if (
                    not track_dict.get("artist_name")
                    and not track_dict.get("artist")
                    or not track_dict.get("title")
                ):
                    try:
                        from core.matching_engine.track_parser import TrackParser

                        parsed_meta = TrackParser.parse_filename(file_path_str)
                        if parsed_meta:
                            parsed_artist = getattr(
                                parsed_meta, "artist", None
                            ) or getattr(parsed_meta, "artist_name", None)
                            parsed_title = getattr(
                                parsed_meta, "title", None
                            ) or getattr(parsed_meta, "raw_title", None)
                            if parsed_artist:
                                track_dict["artist_name"] = parsed_artist
                                track_dict["artist"] = parsed_artist
                            if parsed_title:
                                track_dict["title"] = parsed_title
                                track_dict["raw_title"] = parsed_title
                            if getattr(parsed_meta, "display_title", None):
                                track_dict["display_title"] = parsed_meta.display_title
                            if getattr(parsed_meta, "album_title", None):
                                track_dict["album_title"] = parsed_meta.album_title
                    except Exception as tp_err:
                        logger.debug(
                            f"TrackParser fallback dictionary error for {file_path_str}: {tp_err}"
                        )
                else:
                    if track_dict.get("artist") and not track_dict.get("artist_name"):
                        track_dict["artist_name"] = track_dict["artist"]
                    elif track_dict.get("artist_name") and not track_dict.get("artist"):
                        track_dict["artist"] = track_dict["artist_name"]

                if existing:
                    existing.track_data = track_dict
                    existing.status = status
                    existing.confidence_score = confidence_score
                    existing.created_at = datetime.datetime.now(datetime.UTC)
                else:
                    task = ReviewTask(
                        file_path=file_path_str,
                        status=status,
                        track_data=track_dict,
                        confidence_score=confidence_score,
                    )
                    session.add(task)
            logger.info(
                f"Review Task pending/updated: {file_path_str} (status={status})"
            )
        except Exception as e:
            logger.error(f"Failed to update review task: {e}", exc_info=True)

    def approve_match(self, file_path: Path, metadata: dict[str, Any]):
        """
        Approve a match manually.
        Delegates to AutoImportService to finalize (Tag & Move).
        """
        from services.auto_importer import get_auto_importer

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        auto_importer = get_auto_importer()
        auto_importer.finalize_import(file_path, metadata)

    def search_metadata_waterfall(self, track: EchosyncTrack) -> Any | None:
        """
        Execute a cascading text-based metadata search waterfall across MusicBrainz and Spotify
        for tracks where acoustic fingerprinting returned zero matches.
        """
        if not track:
            return None

        # Resolve track title and artist name (handling both attribute conventions)
        title = track.title or getattr(track, "raw_title", None)
        artist = track.artist or getattr(track, "artist_name", None)

        if not title or not artist:
            return None

        clean_t, clean_a = normalize_track_comparison_fields(title, artist)
        search_query_track = EchosyncTrack(
            raw_title=clean_t,
            artist_name=clean_a,
            album_title=track.album_title
            if hasattr(track, "album_title") and track.album_title
            else "",
            duration=track.duration if hasattr(track, "duration") else None,
        )

        from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry

        engine_cls = (
            ServiceRegistry.resolve("matching_engine") or WeightedMatchingEngine
        )
        matcher = engine_cls(PROFILE_EXACT_SYNC)

        # Stage 1: MusicBrainz Text Search
        mb_client = self._get_mb_plugin()
        if mb_client and hasattr(mb_client, "search_metadata"):
            try:
                results = mb_client.search_metadata(search_query_track, limit=10)  # type: ignore[attr-defined]
                if results:
                    results_list = (
                        results if isinstance(results, (list, tuple)) else [results]
                    )
                    candidate_tracks = []
                    for result in results_list:
                        if isinstance(result, EchosyncTrack):
                            mbid = result.musicbrainz_id
                            if not mbid and isinstance(result.identifiers, dict):
                                mbid = result.identifiers.get(
                                    "musicbrainz_recording_id"
                                ) or result.identifiers.get("mbid")
                            candidate_tracks.append((result, mbid))
                        elif isinstance(result, dict):
                            cand = self._search_result_to_track(result)
                            mbid = result.get("mbid") or result.get("recording_id")
                            if cand:
                                candidate_tracks.append((cand, mbid))

                    best_score = 0.0
                    best_mbid = None
                    best_candidate = None

                    for candidate, mbid in candidate_tracks:
                        match_result = matcher.calculate_match(
                            search_query_track, candidate
                        )
                        score = match_result.confidence_score if match_result else 0.0
                        if score > best_score:
                            best_score = score
                            best_mbid = mbid
                            best_candidate = candidate

                    if best_score >= 85.0:
                        logger.info(
                            "Waterfall Stage 1 (MusicBrainz) match for '%s' (score: %.1f%%)",
                            title,
                            best_score,
                        )
                        if best_mbid:
                            try:
                                meta = mb_client.get_metadata(best_mbid)
                                if meta:
                                    return meta
                            except Exception:
                                pass
                        if best_candidate:
                            return best_candidate
            except Exception as mb_err:
                logger.warning(
                    "Waterfall Stage 1 (MusicBrainz) error for '%s': %s", title, mb_err
                )

        # Stage 2: Spotify Text Search Fallback
        spotify_client = self._get_spotify_plugin()
        if spotify_client and hasattr(spotify_client, "search"):
            try:
                query = f"track:{clean_t} artist:{clean_a}"
                spotify_results = spotify_client.search(
                    query=query, type="track", limit=10
                )
                if not spotify_results:
                    query = f"{clean_a} {clean_t}"
                    spotify_results = spotify_client.search(
                        query=query, type="track", limit=10
                    )

                if spotify_results:
                    best_score = 0.0
                    best_spotify_cand = None

                    for cand in spotify_results:
                        match_result = matcher.calculate_match(search_query_track, cand)
                        score = match_result.confidence_score if match_result else 0.0
                        if score > best_score:
                            best_score = score
                            best_spotify_cand = cand

                    if best_score >= 85.0 and best_spotify_cand:
                        logger.info(
                            "Waterfall Stage 2 (Spotify) match for '%s' (score: %.1f%%)",
                            title,
                            best_score,
                        )
                        if best_spotify_cand.isrc:
                            try:
                                from services.isrc_lookup_service import (
                                    dispatch_isrc_lookup,
                                )

                                isrc_track = dispatch_isrc_lookup(
                                    best_spotify_cand.isrc
                                )
                                if isrc_track:
                                    return isrc_track
                            except Exception as isrc_err:
                                logger.debug(
                                    "ISRC resolution error for Spotify match: %s",
                                    isrc_err,
                                )
                        return best_spotify_cand
            except Exception as spot_err:
                logger.warning(
                    "Waterfall Stage 2 (Spotify) error for '%s': %s", title, spot_err
                )

        return None

    def _search_result_to_track(self, result: dict[str, Any]) -> EchosyncTrack | None:
        """Convert MusicBrainz search result to EchosyncTrack using provider_base helper."""
        from core.nexus_framework.plugin_SDK import PluginBase

        try:
            return PluginBase.create_echo_sync_track(
                title=result.get("title", ""),
                artist=result.get("artist", ""),
                album=result.get("album", ""),
                duration_ms=result.get("duration"),  # MusicBrainz returns ms
                isrc=result.get("isrc"),
                musicbrainz_id=result.get("mbid", ""),
                provider_id=result.get("mbid", ""),
                source="musicbrainz",
            )
        except Exception as e:
            logger.warning(f"Failed to convert search result to track: {e}")
            return None

    def _sanitize(self, filename: str) -> str:
        """Sanitize filename components."""
        import re

        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", filename).strip()

    def enhance_library_metadata(
        self, batch_size=50, check_all_files: bool = False, limit: int | None = None
    ) -> None:
        """Retroactive metadata enhancer following a Local-First, highly efficient 5-Step Pipeline.

        Loops through batches until no more tracks require enhancement or limit is reached. Each batch is
        committed in its own session so memory stays flat even on large libraries.
        Adheres strictly to the canonical EchosyncTrack model with nested EchosyncMedia objects.
        """
        from pathlib import Path

        from core.db.echo_sync_track import EchosyncTrack
        from core.matching_engine.fingerprinting import FingerprintGenerator
        from core.nexus_framework.plugin_loader import PluginRegistry
        from core.utils import PathMapper
        from database.music_database import (
            AudioFingerprint,
            Track,
            get_database,
        )

        MAX_REATTEMPTS = 5

        db = get_database()

        fingerprint_provider = self._get_plugin(
            Capability.RESOLVE_FINGERPRINT, required_algorithm="chromaprint"
        )
        metadata_provider = self._get_plugin(Capability.FETCH_METADATA)

        total_processed = 0
        MAX_ITERATIONS = (
            500  # safety cap — prevents infinite loops on persistent failures
        )

        required_keys = hook_manager.apply_filters("register_metadata_requirements", [])
        for _iteration in range(MAX_ITERATIONS):
            if limit is not None and total_processed >= limit:
                logger.info(
                    "Reached target enhancement limit of %d tracks. Halting.", limit
                )
                break

            current_batch_size = (
                min(batch_size, limit - total_processed)
                if limit is not None
                else batch_size
            )
            if current_batch_size <= 0:
                break

            # Step 1: Select tracks that still need work in a short session
            track_items = []

            with db.session_scope() as session:
                try:
                    from core.database.repositories.track_repo import TrackRepository

                    tracks_to_process = TrackRepository.get_tracks_for_enhancement(
                        session, current_batch_size, check_all_files
                    )
                except OperationalError as _oe:
                    if "database is locked" in str(_oe).lower():
                        logger.critical(
                            "EMERGENCY ABORT: Database is locked by an external process. "
                            "Halting job to prevent corruption."
                        )
                    raise

                if not tracks_to_process:
                    if total_processed > 0:
                        logger.info(
                            "Enhancement complete. Total tracks processed: %d",
                            total_processed,
                        )
                    else:
                        logger.info("No tracks require metadata enhancement.")
                    return

                logger.info(
                    "Enhancement pass %d: processing %d tracks (total so far: %d, limit: %s).",
                    _iteration + 1,
                    len(tracks_to_process),
                    total_processed,
                    str(limit) if limit is not None else "None",
                )

                # Extract into canonical EchosyncTrack domain objects
                for track in tracks_to_process:
                    echosync_track = EchosyncTrack.from_orm(track)
                    if not echosync_track.media:
                        continue

                    # Collect existing fingerprint records for each media_id
                    media_ids = [m.media_id for m in echosync_track.media if m.media_id]
                    fps_map = {}
                    if media_ids:
                        fp_rows = (
                            session.query(AudioFingerprint)
                            .filter(AudioFingerprint.media_id.in_(media_ids))
                            .all()
                        )
                        for fp in fp_rows:
                            fps_map[fp.media_id] = {
                                "chromaprint": fp.chromaprint,
                                "acoustid_id": fp.acoustid_id,
                            }

                    track_items.append(
                        {
                            "id": track.id,
                            "track": echosync_track,
                            "metadata_status": dict(track.metadata_status or {}),
                            "fingerprints": fps_map,
                            "new_fingerprints": {},  # media_id -> {'chromaprint': ..., 'acoustid_id': ...}
                            "metadata_changed": False,
                        }
                    )

            # Process tracks outside DB session
            results_to_commit = []

            # ── Chunked Processing with Absolute Trust Waterfall ──
            mb_client = self._get_mb_plugin()
            CHUNK_SIZE = 50

            for chunk_start in range(0, len(track_items), CHUNK_SIZE):
                chunk = track_items[chunk_start : chunk_start + CHUNK_SIZE]

                # Buckets
                bucket_trust = []  # MBID found locally, all required tags present
                bucket_target = []  # MBID found locally, missing some tags
                bucket_heavy = []  # No MBID found locally

                for item in chunk:
                    t_track = item["track"]

                    # Inspect every associated local media file
                    all_file_tags = []
                    found_mbid = t_track.musicbrainz_id
                    found_isrc = t_track.isrc

                    valid_media_paths = []
                    for media in t_track.media:
                        if not media.file_path:
                            continue
                        local_path_str = PathMapper.to_local(media.file_path)
                        if not local_path_str or local_path_str == ".":
                            continue
                        local_path = Path(local_path_str)
                        if not local_path.exists():
                            continue
                        valid_media_paths.append((media, local_path))

                    if not valid_media_paths:
                        logger.warning(
                            "Enhancer skipping track ID %d: No valid local media files found.",
                            item["id"],
                        )
                        t_track.musicbrainz_id = "NOT_FOUND"
                        item["metadata_status"]["enhancement_attempts"] = (
                            item["metadata_status"].get("enhancement_attempts", 0) + 1
                        )
                        results_to_commit.append(item)
                        continue

                    # Step 1: Read Local Tags across associated files
                    for media, local_path in valid_media_paths:
                        try:
                            file_tags = (
                                echosync_core.extract_metadata(str(local_path)) or {}
                            )
                        except Exception as e:
                            logger.warning(
                                "Failed to read tags from %s: %s", local_path.name, e
                            )
                            file_tags = {}
                        all_file_tags.append((media, local_path, file_tags))

                        tag_mbid = (
                            file_tags.get("mbid")
                            or file_tags.get("musicbrainz_id")
                            or file_tags.get("recording_id")
                        )
                        if tag_mbid and not found_mbid:
                            found_mbid = tag_mbid
                        tag_isrc = file_tags.get("isrc")
                        if tag_isrc and not found_isrc:
                            found_isrc = tag_isrc

                        # Extract artist if missing, unknown, or Various Artists
                        tag_artist = file_tags.get("artist")
                        if (
                            tag_artist
                            and tag_artist.strip()
                            and not tag_artist.strip().lower().startswith("unknown")
                        ):
                            if (
                                not t_track.artist_name
                                or t_track.artist_name.strip()
                                .lower()
                                .startswith(("unknown", "various artist"))
                            ):
                                t_track.artist_name = tag_artist.strip()
                                item["metadata_status"]["artist_fixed_from_tags"] = True
                                item["metadata_changed"] = True

                        # Extract album if missing or unknown
                        tag_album = file_tags.get("album")
                        if (
                            tag_album
                            and tag_album.strip()
                            and not tag_album.strip().lower().startswith("unknown")
                        ):
                            if (
                                not t_track.album_title
                                or t_track.album_title.strip()
                                .lower()
                                .startswith("unknown")
                            ):
                                t_track.album_title = tag_album.strip()
                                item["metadata_status"]["album_fixed_from_tags"] = True
                                item["metadata_changed"] = True

                        # Extract title if missing or unknown
                        tag_title = file_tags.get("title")
                        if (
                            tag_title
                            and tag_title.strip()
                            and not tag_title.strip().lower().startswith("unknown")
                        ):
                            if (
                                not t_track.title
                                or t_track.title.strip().lower().startswith("unknown")
                            ):
                                t_track.title = tag_title.strip()
                                item["metadata_status"]["title_fixed_from_tags"] = True
                                item["metadata_changed"] = True

                        # Fallback to Directory Path Structure if artist or album is still unknown
                        # e.g. /data/library/{Artist}/{Album}/{Track}.flac
                        if (
                            not t_track.artist_name
                            or t_track.artist_name.strip().lower().startswith("unknown")
                        ) or (
                            not t_track.album_title
                            or t_track.album_title.strip().lower().startswith("unknown")
                        ):
                            parts = local_path.parts
                            if len(parts) >= 3:
                                parent_album = local_path.parent.name
                                parent_artist = local_path.parent.parent.name
                                non_artist_names = {
                                    "library",
                                    "music",
                                    "downloads",
                                    "unknown artist",
                                    "unknown",
                                    "media",
                                    "data",
                                    "music_library",
                                }
                                if (
                                    parent_artist
                                    and parent_artist.lower() not in non_artist_names
                                ):
                                    if (
                                        not t_track.artist_name
                                        or t_track.artist_name.strip()
                                        .lower()
                                        .startswith("unknown")
                                    ):
                                        t_track.artist_name = parent_artist
                                        item["metadata_status"][
                                            "artist_fixed_from_path"
                                        ] = True
                                        item["metadata_changed"] = True
                                if (
                                    parent_album
                                    and parent_album.lower() not in non_artist_names
                                ):
                                    if (
                                        not t_track.album_title
                                        or t_track.album_title.strip()
                                        .lower()
                                        .startswith("unknown")
                                    ):
                                        t_track.album_title = parent_album
                                        item["metadata_status"][
                                            "album_fixed_from_path"
                                        ] = True
                                        item["metadata_changed"] = True

                    if found_mbid:
                        t_track.musicbrainz_id = found_mbid
                    if found_isrc:
                        t_track.isrc = found_isrc

                    # Determine whether track has bad metadata that requires enhancement
                    is_bad_metadata = (
                        not t_track.artist_name
                        or t_track.artist_name.strip().lower().startswith("unknown")
                        or not t_track.album_title
                        or t_track.album_title.strip().lower().startswith("unknown")
                        or not t_track.title
                        or t_track.title.strip().lower().startswith("unknown")
                    )

                    # Determine missing fields
                    missing_fields = [
                        key
                        for key in required_keys
                        if not item["metadata_status"].get(key)
                    ]

                    if t_track.musicbrainz_id and t_track.musicbrainz_id != "NOT_FOUND":
                        if (
                            not missing_fields
                            and not is_bad_metadata
                            and not item.get("metadata_changed")
                        ):
                            bucket_trust.append(
                                (item, valid_media_paths, all_file_tags)
                            )
                        else:
                            bucket_target.append(
                                (item, valid_media_paths, all_file_tags)
                            )
                    else:
                        bucket_heavy.append((item, valid_media_paths, all_file_tags))

                # Step 2: Absolute Trust Gate
                for item, valid_media_paths, all_file_tags in bucket_trust:
                    t_track = item["track"]
                    logger.info("Absolute Trust Gate Passed: %s", t_track.title)
                    item["metadata_status"]["enhanced"] = True
                    results_to_commit.append(item)

                # Step 3: Targeted Fetch
                if bucket_target:
                    if mb_client:
                        mbids_to_fetch = [
                            it[0]["track"].musicbrainz_id
                            for it in bucket_target
                            if it[0]["track"].musicbrainz_id
                        ]
                        logger.info("Targeted Fetch for %d tracks", len(bucket_target))
                        batch_metadata = (
                            mb_client.get_metadata_batch(mbids_to_fetch)
                            if getattr(
                                mb_client.capabilities, "supports_batching", False
                            )
                            else {}
                        )

                        for item, valid_media_paths, all_file_tags in bucket_target:
                            t_track = item["track"]
                            mbid = t_track.musicbrainz_id
                            meta = batch_metadata.get(mbid)
                            if not meta and not batch_metadata:
                                try:
                                    meta = mb_client.get_metadata(mbid)
                                except Exception:
                                    pass

                            if meta:
                                if meta.get("title"):
                                    t_track.title = meta["title"]
                                if meta.get("artist"):
                                    t_track.artist_name = meta["artist"]
                                if meta.get("album"):
                                    t_track.album_title = meta["album"]
                                if meta.get("year"):
                                    try:
                                        t_track.release_year = int(meta["year"])
                                    except Exception:
                                        pass
                                if not t_track.isrc and meta.get("isrc"):
                                    t_track.isrc = meta.get("isrc")

                                update_tags = {
                                    "musicbrainz_id": mbid,
                                    "recording_id": mbid,
                                }
                                if t_track.title:
                                    update_tags["title"] = t_track.title
                                if t_track.artist_name:
                                    update_tags["artist"] = t_track.artist_name
                                if t_track.album_title:
                                    update_tags["album"] = t_track.album_title
                                if t_track.isrc:
                                    update_tags["isrc"] = t_track.isrc
                                if t_track.release_year:
                                    update_tags["year"] = str(t_track.release_year)
                                    update_tags["date"] = str(t_track.release_year)

                                # Write tags to EVERY associated media file via tag_file_verified
                                for media, local_path in valid_media_paths:
                                    try:
                                        self.tag_file_verified(local_path, update_tags)
                                    except Exception as write_err:
                                        logger.warning(
                                            f"tag_file_verified failed for {local_path.name}: {write_err}; falling back to direct write"
                                        )
                                        try:
                                            _tagging_write(local_path, update_tags)
                                        except Exception:
                                            pass

                                item["metadata_status"]["enhanced"] = True
                                for key in required_keys:
                                    item["metadata_status"][key] = True
                                item["metadata_changed"] = True
                                results_to_commit.append(item)
                            else:
                                # MBID targeted fetch returned nothing, route to heavyweight fingerprint + waterfall discovery
                                bucket_heavy.append(
                                    (item, valid_media_paths, all_file_tags)
                                )
                    else:
                        for item, valid_media_paths, all_file_tags in bucket_target:
                            bucket_heavy.append(
                                (item, valid_media_paths, all_file_tags)
                            )

                # Step 4: Heavyweight Fingerprint Discovery & Text Waterfall Fallback
                for item, valid_media_paths, all_file_tags in bucket_heavy:
                    t_track = item["track"]
                    new_musicbrainz_id = None
                    duration = t_track.duration

                    # Ensure every media file has a chromaprint
                    for media, local_path in valid_media_paths:
                        mid = media.media_id
                        existing_fp = (
                            item["fingerprints"].get(mid, {}).get("chromaprint")
                        )
                        if not existing_fp:
                            try:
                                cp = FingerprintGenerator.generate(str(local_path))
                                if cp:
                                    item["new_fingerprints"][mid] = {
                                        "chromaprint": cp,
                                        "acoustid_id": None,
                                    }
                                    if not t_track.fingerprint:
                                        t_track.fingerprint = cp
                            except Exception as fp_err:
                                logger.debug(
                                    f"Fingerprint generation failed for {local_path.name}: {fp_err}"
                                )
                        else:
                            if not t_track.fingerprint:
                                t_track.fingerprint = existing_fp

                    # 0. Local Chromaprint Cache Resolution (Fast-Path Short-Circuit)
                    target_cp = t_track.fingerprint
                    if not target_cp:
                        for mid, fp_info in item.get("fingerprints", {}).items():
                            if fp_info.get("chromaprint"):
                                target_cp = fp_info["chromaprint"]
                                break
                    if not target_cp:
                        for mid, fp_info in item.get("new_fingerprints", {}).items():
                            if fp_info.get("chromaprint"):
                                target_cp = fp_info["chromaprint"]
                                break

                    resolved_from_cache = False
                    if target_cp:
                        cached_meta = self.resolve_canonical_from_chromaprint(
                            chromaprint=target_cp, current_track_id=item["id"]
                        )
                        if cached_meta:
                            new_musicbrainz_id = cached_meta.get(
                                "musicbrainz_id"
                            ) or cached_meta.get("musicbrainz_track_id")
                            if cached_meta.get("title"):
                                t_track.title = cached_meta["title"]
                            if cached_meta.get("artist") or cached_meta.get(
                                "artist_name"
                            ):
                                t_track.artist_name = cached_meta.get(
                                    "artist"
                                ) or cached_meta.get("artist_name")
                            if cached_meta.get("album") or cached_meta.get(
                                "album_title"
                            ):
                                t_track.album_title = cached_meta.get(
                                    "album"
                                ) or cached_meta.get("album_title")
                            if cached_meta.get("year"):
                                t_track.release_year = cached_meta["year"]
                            if cached_meta.get("isrc") and not t_track.isrc:
                                t_track.isrc = cached_meta["isrc"]
                            if cached_meta.get("acoustid_id"):
                                t_track.acoustid_id = cached_meta["acoustid_id"]
                                for mid, fp_val in item["new_fingerprints"].items():
                                    fp_val["acoustid_id"] = cached_meta["acoustid_id"]
                            resolved_from_cache = True

                    # 1. Acoustic Fingerprint Resolution
                    if (
                        not new_musicbrainz_id
                        and fingerprint_provider
                        and t_track.fingerprint
                        and duration
                    ):
                        try:
                            duration_secs = (
                                int(duration / 1000) if duration > 10000 else duration
                            )
                            details = fingerprint_provider.resolve_fingerprint_details(
                                t_track.fingerprint, duration_secs
                            )  # type: ignore[attr-defined]
                            if details.get("mbids"):
                                new_musicbrainz_id = details["mbids"][0]
                            if details.get("acoustid_id"):
                                t_track.acoustid_id = details["acoustid_id"]
                                for mid, fp_val in item["new_fingerprints"].items():
                                    fp_val["acoustid_id"] = details["acoustid_id"]
                        except Exception as res_err:
                            logger.debug(
                                f"Fingerprint resolution error for {t_track.title}: {res_err}"
                            )

                    # 2. Text-Based Search Waterfall Fallback if AcoustID yields no matches
                    resolved_meta = None
                    if (
                        not new_musicbrainz_id
                        and (t_track.title or getattr(t_track, "raw_title", None))
                        and (t_track.artist or getattr(t_track, "artist_name", None))
                    ):
                        try:
                            logger.info(
                                "AcoustID returned no matches for '%s' by '%s'; executing text waterfall search.",
                                t_track.title,
                                t_track.artist_name,
                            )
                            resolved_meta = self.search_metadata_waterfall(t_track)
                            if resolved_meta:
                                if isinstance(resolved_meta, EchosyncTrack):
                                    new_musicbrainz_id = resolved_meta.musicbrainz_id
                                    if not t_track.isrc and resolved_meta.isrc:
                                        t_track.isrc = resolved_meta.isrc
                                    if resolved_meta.title:
                                        t_track.title = resolved_meta.title
                                    if resolved_meta.artist:
                                        t_track.artist_name = resolved_meta.artist
                                    if resolved_meta.album:
                                        t_track.album_title = resolved_meta.album
                                elif isinstance(resolved_meta, dict):
                                    new_musicbrainz_id = (
                                        resolved_meta.get("musicbrainz_id")
                                        or resolved_meta.get("mbid")
                                        or resolved_meta.get("recording_id")
                                    )
                                    if not t_track.isrc and resolved_meta.get("isrc"):
                                        t_track.isrc = resolved_meta.get("isrc")
                                    if resolved_meta.get("title"):
                                        t_track.title = resolved_meta.get("title")
                                    if resolved_meta.get("artist"):
                                        t_track.artist_name = resolved_meta.get(
                                            "artist"
                                        )
                                    if resolved_meta.get("album"):
                                        t_track.album_title = resolved_meta.get("album")
                        except Exception as waterfall_err:
                            logger.warning(
                                f"Text waterfall fallback failed for {t_track.title}: {waterfall_err}"
                            )

                    if new_musicbrainz_id:
                        t_track.musicbrainz_id = new_musicbrainz_id
                        logger.info(
                            "Metadata Discovery Success: %s -> %s",
                            t_track.title,
                            new_musicbrainz_id,
                        )
                        if mb_client and not resolved_meta and not resolved_from_cache:
                            try:
                                meta = mb_client.get_metadata(new_musicbrainz_id)
                                if meta and not t_track.isrc and meta.get("isrc"):
                                    t_track.isrc = meta.get("isrc")
                            except Exception:
                                pass

                        if target_cp and not resolved_from_cache:
                            self._local_chromaprint_cache[target_cp] = {
                                "title": t_track.title,
                                "artist": t_track.artist_name,
                                "artist_name": t_track.artist_name,
                                "album": t_track.album_title,
                                "album_title": t_track.album_title,
                                "year": t_track.release_year,
                                "isrc": t_track.isrc,
                                "musicbrainz_id": new_musicbrainz_id,
                                "musicbrainz_track_id": new_musicbrainz_id,
                                "recording_id": new_musicbrainz_id,
                                "acoustid_id": t_track.acoustid_id,
                            }

                        update_tags = {
                            "musicbrainz_id": new_musicbrainz_id,
                            "recording_id": new_musicbrainz_id,
                        }
                        if t_track.title:
                            update_tags["title"] = t_track.title
                        if t_track.artist_name:
                            update_tags["artist"] = t_track.artist_name
                        if t_track.album_title:
                            update_tags["album"] = t_track.album_title
                        if t_track.isrc:
                            update_tags["isrc"] = t_track.isrc

                        # Write tags to EVERY associated media file via tag_file_verified
                        for media, local_path in valid_media_paths:
                            try:
                                self.tag_file_verified(local_path, update_tags)
                            except Exception as write_err:
                                logger.warning(
                                    f"tag_file_verified failed for {local_path.name}: {write_err}; falling back to direct write"
                                )
                                try:
                                    _tagging_write(local_path, update_tags)
                                except Exception:
                                    pass

                        item["metadata_status"]["enhanced"] = True
                        for key in required_keys:
                            item["metadata_status"][key] = True
                        item["metadata_changed"] = True
                    else:
                        logger.info(
                            "Metadata discovery returned no matches for: %s",
                            t_track.title,
                        )
                        t_track.musicbrainz_id = "NOT_FOUND"
                        item["metadata_status"]["enhancement_attempts"] = (
                            item["metadata_status"].get("enhancement_attempts", 0) + 1
                        )

                    results_to_commit.append(item)

            # Step 6: Commit the batch updates in a new short session
            with db.session_scope() as session:
                from core.database.repositories.track_repo import TrackRepository
                from core.matching_engine.text_utils import normalize_title

                changed_tracks = [
                    res["track"]
                    for res in results_to_commit
                    if res.get("metadata_changed")
                ]
                if changed_tracks:
                    TrackRepository.resolve_artists_and_albums(session, changed_tracks)

                for res in results_to_commit:
                    track = session.get(Track, res["id"])
                    if not track:
                        continue

                    t_track = res["track"]
                    if t_track.musicbrainz_id and t_track.musicbrainz_id != "NOT_FOUND":
                        track.musicbrainz_id = t_track.musicbrainz_id
                    else:
                        track.musicbrainz_id = "NOT_FOUND"

                    if t_track.isrc:
                        track.isrc = t_track.isrc

                    if res.get("metadata_changed"):
                        if t_track.title:
                            track.title = t_track.title
                            track.normalized_title = normalize_title(t_track.title)
                        if getattr(t_track, "artist_id", None):
                            track.artist_id = t_track.artist_id
                        if getattr(t_track, "album_id", None):
                            track.album_id = t_track.album_id

                    track.metadata_status = res["metadata_status"]
                    flag_modified(track, "metadata_status")

                    # Save new fingerprints or update existing acoustid_ids for all associated media rows
                    if track.media_files:
                        media_ids = [
                            m.media_id for m in track.media_files if m.media_id
                        ]
                        existing_fp_records = (
                            {
                                fp.media_id: fp
                                for fp in session.query(AudioFingerprint)
                                .filter(AudioFingerprint.media_id.in_(media_ids))
                                .all()
                            }
                            if media_ids
                            else {}
                        )

                        # 1. Insert new fingerprints generated during this run
                        for mid, fp_data in res.get("new_fingerprints", {}).items():
                            cp_val = fp_data["chromaprint"]
                            existing_fp_by_cp = (
                                session.query(AudioFingerprint)
                                .filter(AudioFingerprint.chromaprint == cp_val)
                                .first()
                            )
                            if mid not in existing_fp_records and not existing_fp_by_cp:
                                new_fp = AudioFingerprint(
                                    media_id=mid,
                                    chromaprint=cp_val,
                                    acoustid_id=fp_data.get("acoustid_id")
                                    or t_track.acoustid_id,
                                )
                                session.add(new_fp)
                                existing_fp_records[mid] = new_fp
                            elif (
                                existing_fp_by_cp
                                and fp_data.get("acoustid_id")
                                and not existing_fp_by_cp.acoustid_id
                            ):
                                existing_fp_by_cp.acoustid_id = fp_data["acoustid_id"]
                            elif (
                                mid in existing_fp_records
                                and fp_data.get("acoustid_id")
                                and not existing_fp_records[mid].acoustid_id
                            ):
                                existing_fp_records[mid].acoustid_id = fp_data[
                                    "acoustid_id"
                                ]

                        # 2. Update acoustid_id on existing fingerprints if resolved
                        if t_track.acoustid_id:
                            for media in track.media_files:
                                if (
                                    media.media_id in existing_fp_records
                                    and not existing_fp_records[
                                        media.media_id
                                    ].acoustid_id
                                ):
                                    existing_fp_records[
                                        media.media_id
                                    ].acoustid_id = t_track.acoustid_id

                    # Always apply post-metadata enrichment hooks so that the cjk_restored stamp is set and aliases are persisted
                    track = hook_manager.apply_filters(
                        "post_metadata_enrichment", track
                    )
                    flag_modified(track, "metadata_status")
                    total_processed += 1


class MetadataEnhancerService(RetroactiveEnhancer):
    _instance = None

    def __init__(self):
        super().__init__()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MetadataEnhancerService()
        return cls._instance


def get_metadata_enhancer():
    return MetadataEnhancerService.get_instance()


def register_metadata_enhancer_service():
    """Kept for compatibility, though it no longer registers background jobs."""
    get_metadata_enhancer()
    logger.info("Metadata Enhancer Service initialized")


def run_retroactive_enhancement(
    batch_size: int = 100,
    check_all_files: bool = False,
    limit: int | None = None,
    progress_callback: Any | None = None,
) -> None:
    """Execute full retroactive metadata enhancement with fast-path native Rust fingerprinting."""
    enhancer = RetroactiveEnhancer()
    enhancer.backfill_missing_fingerprints(
        batch_size=50, progress_callback=progress_callback
    )
    enhancer.enhance_library_metadata(
        batch_size=batch_size,
        check_all_files=check_all_files,
        limit=limit,
    )
