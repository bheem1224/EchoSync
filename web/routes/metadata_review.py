from dataclasses import replace
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.db.echo_sync_track import EchosyncTrack
from core.db.schemas import (
    ApproveMatchRequest,
    IgnoreTaskRequest,
    ManualSearchRequest,
    QueueDetailResponse,
    QueueItemDetailSchema,
    QueueItemSchema,
    QueueListResponse,
    SuccessResponse,
)
from core.enums import Capability
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.nexus_framework import plugin_loader
from core.nexus_framework.plugin_loader import get_plugin_by_capability
from core.settings import config_manager
from core.tiered_logger import get_logger
from database import _canonicalize_path, get_database
from database.working_database import ReviewTask, get_working_database
from services.metadata_enhancer import get_metadata_enhancer
from web.auth import require_auth

logger = get_logger("metadata_review_route")
router = APIRouter(prefix="/api/v1/core/metadata_review", tags=["Metadata Review"])
review_tasks_router = APIRouter(prefix="/api/v1/review/tasks", tags=["Metadata Review Tasks"])
metadata_router = APIRouter(prefix="/api/v1/core/metadata", tags=["Metadata"])
v1_metadata_router = APIRouter(prefix="/api/v1/metadata", tags=["Metadata"])


class CreateReviewTaskRequest(BaseModel):
    media_id: str | None = None
    file_path: str | None = None
    track_data: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    confidence_score: float | None = 0.0


class UpdateReviewQueueRequest(BaseModel):
    media_id: str | None = None
    metadata: dict[str, Any] | None = None
    track_data: dict[str, Any] | None = None


class ApproveReviewQueueRequest(BaseModel):
    metadata: dict[str, Any] | None = None
    detected_metadata: dict[str, Any] | None = None


class MusicBrainzLookupRequest(BaseModel):
    metadata: dict[str, Any] | None = None


class ISRCLookupRequest(BaseModel):
    isrc: str | None = None
    metadata: dict[str, Any] | None = None


_MEDIA_NANOID_RE = re.compile(r"^[A-Za-z0-9_-]{3,64}$")


def _is_integer_like_id(value: str) -> bool:
    if not value:
        return True
    if value.isdigit():
        return True
    if value[0] in ("+", "-") and value[1:].isdigit():
        return True
    return False


def _is_valid_nanoid_media_id(raw_media_id: Any) -> bool:
    if raw_media_id is None or isinstance(raw_media_id, (bool, int, float)):
        return False
    cleaned = str(raw_media_id).strip().split("?")[0].strip()
    if not cleaned or _is_integer_like_id(cleaned):
        return False
    if "/" in cleaned or "\\" in cleaned or ":" in cleaned or ".." in cleaned:
        return False
    return bool(_MEDIA_NANOID_RE.fullmatch(cleaned))


def _validate_media_id(raw_media_id: Any) -> str:
    """Validate that a supplied media_id is a NanoID string (not an int PK or path string)."""
    if isinstance(raw_media_id, (bool, int, float)):
        raise HTTPException(
            status_code=400,
            detail="Integer primary keys are not allowed. Provide a valid string NanoID media_id.",
        )
    cleaned = str(raw_media_id or "").strip().split("?")[0].strip()
    if not cleaned or _is_integer_like_id(cleaned):
        raise HTTPException(
            status_code=400,
            detail="Integer primary keys are not allowed. Provide a valid string NanoID media_id.",
        )
    if (
        "/" in cleaned
        or "\\" in cleaned
        or ":" in cleaned
        or ".." in cleaned
        or not _MEDIA_NANOID_RE.fullmatch(cleaned)
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid media_id format. Path strings are not allowed; provide a valid string NanoID media_id.",
        )
    return cleaned


def _mark_review_task_failed(working_db: Any, task_id: int, error_message: str) -> None:
    """Persist background approval failure state and error details onto ReviewTask."""
    try:
        from sqlalchemy.orm.attributes import flag_modified

        with working_db.session_scope() as w_session:
            task_row = w_session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task_row:
                return
            task_row.status = "failed"
            updated_data = dict(task_row.track_data or {})
            updated_data["error"] = error_message
            task_row.track_data = updated_data
            flag_modified(task_row, "track_data")
    except Exception as persist_err:
        logger.error(f"Failed to persist error state for review task {task_id}: {persist_err}", exc_info=True)


def _get_media_file_path(media_id: str) -> str | None:
    if not _is_valid_nanoid_media_id(media_id):
        return None
    cleaned_media_id = str(media_id).strip().split("?")[0].strip()
    from database.music_database import LocalMedia

    db = get_database()
    try:
        with db.session_scope() as session:
            media = session.query(LocalMedia).filter(LocalMedia.media_id == cleaned_media_id).first()
            return media.file_path if media else None
    except Exception as exc:
        logger.error(f"Failed to lookup media path for {cleaned_media_id}: {exc}")
    return None


_PARSER_FALLBACK_CONFIDENCE = 0.35
_LOW_CONFIDENCE_THRESHOLD = 0.6


def _coerce_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(round(float(value)))
    except Exception:
        return None


def _extract_payload_metadata(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        payload_dict = cast(dict[str, Any], payload)
        metadata = payload_dict.get("metadata")
        detected_metadata = payload_dict.get("detected_metadata")
        if isinstance(metadata, dict):
            return cast(dict[str, Any], metadata)
        if isinstance(detected_metadata, dict):
            return cast(dict[str, Any], detected_metadata)
        return payload_dict
    return None


def _normalize_detected_metadata(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    value_dict = cast(dict[Any, Any], value)
    return {str(k): v for k, v in value_dict.items()}


def _resolve_task_file(task: ReviewTask) -> Path | None:
    from core.settings import config_manager
    from core.utils import PathMapper

    media_path = task.file_path
    if not media_path:
        return None

    resolved = None
    # 1. Try direct path
    try:
        candidate = Path(media_path).expanduser().resolve()
        if candidate.exists() and candidate.is_file():
            resolved = candidate
    except Exception:
        pass

    # 2. Try PathMapper mapped path
    if not resolved:
        try:
            mapped = PathMapper.to_local(media_path)
            if mapped:
                candidate = Path(mapped).expanduser().resolve()
                if candidate.exists() and candidate.is_file():
                    resolved = candidate
        except Exception:
            pass

    # 3. Try download_dir and library_dir filename fallback (in case file was ejected or staged)
    if not resolved:
        dl_dir = config_manager.get("storage.download_dir") or config_manager.get("download_dir")
        lib_dir = config_manager.get("storage.library_dir") or config_manager.get("library_dir")
        filename = Path(media_path).name
        for base_dir in (dl_dir, lib_dir):
            if base_dir:
                candidate = Path(base_dir).resolve() / filename
                if candidate.exists() and candidate.is_file():
                    resolved = candidate
                    try:
                        task.file_path = str(candidate)
                    except Exception:
                        pass
                    break

    if not resolved or not resolved.exists() or not resolved.is_file():
        return None

    # Jail / LFI protection
    allowed_dirs = []
    _lib = config_manager.get("storage.library_dir") or config_manager.get("library_dir")
    _dl = config_manager.get("storage.download_dir") or config_manager.get("download_dir")
    _poor = config_manager.get("storage.poor_metadata_dir")
    if _lib:
        allowed_dirs.append(Path(_lib).resolve())
    if _dl:
        allowed_dirs.append(Path(_dl).resolve())
    if _poor:
        allowed_dirs.append(Path(_poor).resolve())

    is_safe = False
    for allowed in allowed_dirs:
        try:
            if resolved.is_relative_to(allowed):
                is_safe = True
                break
        except Exception:
            pass

    if not is_safe:
        return None

    return resolved


def _get_fingerprint_provider():
    """Resolve fingerprint provider bound by capability, preferring chromaprint."""
    try:
        from core.nexus_framework.plugin_loader import PluginRegistry

        plugins = PluginRegistry.get_plugins_with_capability(Capability.RESOLVE_FINGERPRINT)
        for p in plugins:
            caps = getattr(p, "capabilities", None)
            if caps:
                algos = getattr(caps, "fingerprint_algorithms", []) or []
                if "chromaprint" in algos or getattr(caps, "supports_fingerprinting", False):
                    return p
        if plugins:
            return plugins[0]
    except Exception:
        pass
    return get_plugin_by_capability(Capability.RESOLVE_FINGERPRINT)


def _get_metadata_provider():
    """Resolve metadata provider bound by capability."""
    return get_plugin_by_capability(Capability.FETCH_METADATA)


def _get_spotify_provider():
    """Resolve Spotify provider bound by capability or plugin name."""
    try:
        from core.nexus_framework import plugin_loader

        return plugin_loader.get_plugin("EchoSync.spotify") or plugin_loader.get_plugin("spotify")
    except Exception:
        return None


def _read_current_metadata(task: ReviewTask) -> dict[str, Any]:
    resolved_file = _resolve_task_file(task)
    if not resolved_file:
        return {}

    try:
        import echosync_core

        metadata = echosync_core.extract_metadata(str(resolved_file))

        # Remove raw cover data from the general metadata dict to keep JSON response light
        clean_metadata = {str(key): value for key, value in metadata.items() if not str(key).startswith("_cover_")}
        # Add a flag if cover is present
        if "_cover_data" in metadata:
            clean_metadata["_has_embedded_cover"] = True

        return clean_metadata
    except Exception as exc:
        media_path = task.file_path
        logger.debug(f"Failed to read current metadata for {media_path}: {exc}")
    return {}


def _serialize_task(
    task: ReviewTask,
    detected_metadata: dict[str, Any] | None = None,
    current_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    track_data = task.track_data or {}

    artist_val = (
        (detected_metadata.get("artist") if isinstance(detected_metadata, dict) else None)
        or track_data.get("artist_name")
        or track_data.get("artist")
    )
    title_val = (
        (detected_metadata.get("title") if isinstance(detected_metadata, dict) else None)
        or track_data.get("title")
        or track_data.get("raw_title")
        or track_data.get("display_title")
    )
    edition_val = (
        (detected_metadata.get("edition") if isinstance(detected_metadata, dict) else None)
        or (detected_metadata.get("version") if isinstance(detected_metadata, dict) else None)
        or track_data.get("edition")
        or track_data.get("version")
    )
    album_val = (
        (detected_metadata.get("album") if isinstance(detected_metadata, dict) else None)
        or track_data.get("album_title")
        or track_data.get("album")
    )

    detected = (
        detected_metadata
        if detected_metadata is not None
        else {
            "title": title_val,
            "edition": edition_val,
            "artist": artist_val,
            "album": album_val,
            "year": track_data.get("release_year") or track_data.get("year"),
            "track_number": track_data.get("track_number"),
            "disc_number": track_data.get("disc_number"),
            "musicbrainz_id": track_data.get("mbid") or track_data.get("musicbrainz_id"),
            "isrc": track_data.get("isrc"),
            "acoustid_id": track_data.get("acoustid") or track_data.get("acoustid_id"),
            "mb_release_id": track_data.get("mb_release_id"),
            "fingerprint": track_data.get("fingerprint"),
        }
    )
    if isinstance(detected, dict):
        if not detected.get("artist") and artist_val:
            detected["artist"] = artist_val
        if not detected.get("title") and title_val:
            detected["title"] = title_val
        if not detected.get("edition") and edition_val:
            detected["edition"] = edition_val
        if not detected.get("album") and album_val:
            detected["album"] = album_val

    media_id_val = None
    raw_task_mid = getattr(task, "media_id", None)
    if raw_task_mid and _is_valid_nanoid_media_id(raw_task_mid):
        media_id_val = str(raw_task_mid).strip()
    elif isinstance(task.track_data, dict) and task.track_data.get("media_id"):
        td_mid = task.track_data.get("media_id")
        if _is_valid_nanoid_media_id(td_mid):
            media_id_val = str(td_mid).strip()

    if not media_id_val and task.file_path:
        db = get_database()
        try:
            with db.session_scope() as session:
                from database.music_database import LocalMedia

                media = session.query(LocalMedia).filter(LocalMedia.file_path == task.file_path).first()
                if media:
                    media_id_val = media.media_id
        except Exception:
            pass

    return {
        "id": task.id,
        "file_path": task.file_path,
        "media_id": media_id_val,
        "status": getattr(task, "status", None),
        "error": track_data.get("error") if isinstance(track_data, dict) else None,
        "detected_metadata": detected,
        "proposed_metadata": detected,
        "current_metadata": current_metadata if current_metadata is not None else _read_current_metadata(task),
        "proposed_artist": artist_val or "Unknown Artist",
        "proposed_title": title_val or "Unknown Title",
        "confidence_score": task.confidence_score,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


def _is_missing_or_low_confidence(metadata: dict[str, Any] | None, confidence_score: float) -> bool:
    if not metadata:
        return True
    if confidence_score < _LOW_CONFIDENCE_THRESHOLD:
        return True
    if not str(metadata.get("artist") or "").strip():
        return True
    if not str(metadata.get("title") or "").strip():
        return True
    return False


def _merge_metadata(base: dict[str, Any] | None, update: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base or {})
    for key, value in (update or {}).items():
        if value is not None and value != "":
            merged[str(key)] = value
    return merged


def _musicbrainz_text_search(metadata_provider, track: Any) -> EchosyncTrack | None:
    # Ensure artist and title are available, otherwise return None
    if isinstance(track, dict) or hasattr(track, "get"):
        artist = track.get("artist_name") or track.get("artist")
        title = track.get("title") or track.get("raw_title")
    else:
        artist = getattr(track, "artist_name", getattr(track, "artist", None))
        title = getattr(track, "title", getattr(track, "raw_title", None))

    logger.debug(f"[MusicBrainz Search] Starting text search: artist='{artist}', title='{title}'")
    if not artist or not title:
        logger.debug("[MusicBrainz Search] Missing artist or title, search aborted")
        return None

    if hasattr(metadata_provider, "search_metadata"):
        try:
            logger.debug(
                f"[MusicBrainz Search] Calling search_metadata on provider '{getattr(metadata_provider, 'name', type(metadata_provider).__name__)}' with track={track}"
            )
            # Assume search_metadata can now take EchosyncTrack (per architecture directives)
            enriched_track = metadata_provider.search_metadata(track=track)
            logger.debug(f"[MusicBrainz Search] search_metadata returned: {enriched_track}")
            if isinstance(enriched_track, EchosyncTrack):
                if enriched_track.musicbrainz_id:
                    logger.debug(
                        f"[MusicBrainz Search] Found valid EchosyncTrack with musicbrainz_id: '{enriched_track.musicbrainz_id}'"
                    )
                    return enriched_track
                else:
                    logger.debug("[MusicBrainz Search] enriched_track has empty musicbrainz_id")
            elif isinstance(enriched_track, list) and len(enriched_track) > 0:
                first_match = enriched_track[0]
                if isinstance(first_match, dict):
                    mb_id = first_match.get("id") or first_match.get("musicbrainz_id")
                    if mb_id:
                        ret_track = EchosyncTrack(
                            raw_title=first_match.get("title") or title,
                            artist_name=first_match.get("artist") or artist,
                            album_title=first_match.get("album", ""),
                            identifiers={"musicbrainz": mb_id},
                            musicbrainz_id=mb_id,
                        )
                        logger.debug(f"[MusicBrainz Search] Converted dict to EchosyncTrack with mb_id: '{mb_id}'")
                        return ret_track
            else:
                logger.debug(
                    f"[MusicBrainz Search] enriched_track is not EchosyncTrack instance (type: {type(enriched_track).__name__})"
                )
        except Exception:
            logger.error("Error calling search_metadata directly with track", exc_info=True)

    logger.debug("[MusicBrainz Search] Returning None (search failed or not implemented)")
    return None

    # Fallback to direct MusicBrainz WS/2 query using provider HTTP client.
    try:
        query = f'artist:"{artist}" AND recording:"{title}"'
        response = metadata_provider.http.get(
            "https://musicbrainz.org/ws/2/recording",
            params={"fmt": "json", "query": query, "limit": 5},
        )
        if response.status_code != 200:
            return None

        payload = response.json() or {}
        recordings = payload.get("recordings") or []
        if not recordings:
            return None

        recording = recordings[0]
        mbid = recording.get("id")
        if mbid and hasattr(metadata_provider, "get_metadata"):
            metadata = metadata_provider.get_metadata(mbid)
            if isinstance(metadata, dict):
                return metadata

        artist_name = ""
        for credit in recording.get("artist-credit") or []:
            if isinstance(credit, dict):
                artist_name += str(credit.get("name") or "")
                artist_name += str(credit.get("joinphrase") or "")

        return {
            "title": recording.get("title"),
            "artist": artist_name.strip(),
            "recording_id": recording.get("id"),
            "source": "musicbrainz_text_lookup",
        }
    except Exception:
        return None


def _build_track_from_metadata(file_path: Path, metadata: dict[str, Any]):
    title = metadata.get("title") or file_path.stem
    artist = metadata.get("artist") or "Unknown Artist"
    album = metadata.get("album") or ""

    source = metadata.get("source") or "manual_review"
    provider_id = metadata.get("provider_item_id") or metadata.get("rating_key")

    release_year = _coerce_int(metadata.get("year"))
    if release_year is None and metadata.get("date"):
        date_value = str(metadata.get("date"))
        if len(date_value) >= 4 and date_value[:4].isdigit():
            release_year = int(date_value[:4])

    from core.db.echo_sync_track import EchosyncMedia

    media_item = EchosyncMedia(
        file_path=str(file_path),
        file_format=file_path.suffix.lower().lstrip("."),
        bitrate=_coerce_int(metadata.get("bitrate") or metadata.get("bitrate_kbps")),
    )
    track = EchosyncTrack(
        raw_title=title,
        artist_name=artist,
        album_title=album,
        edition=cast(str | None, metadata.get("edition") or metadata.get("version")),
        duration_ms=_coerce_int(metadata.get("duration_ms") or metadata.get("duration")),
        isrc=cast(str | None, metadata.get("isrc")),
        musicbrainz_id=cast(
            str | None,
            metadata.get("recording_id") or metadata.get("musicbrainz_id") or metadata.get("mbid"),
        ),
        mb_release_id=cast(
            str | None,
            metadata.get("release_id") or metadata.get("musicbrainz_album_id") or metadata.get("mb_release_id"),
        ),
        release_year=release_year,
        track_number=_coerce_int(metadata.get("track_number")),
        disc_number=_coerce_int(metadata.get("disc_number")),
        media=[media_item],
        identifiers={source: str(provider_id)} if provider_id else {},
        fingerprint=(
            metadata.get("fingerprint") or metadata.get("chromaprint") or metadata.get("acoustid_fingerprint")
        ),
        acoustid_id=metadata.get("acoustid_id") or metadata.get("acoustid"),
    )
    return track


def _import_single_file(
    file_path: Path,
    metadata: dict[str, Any],
    old_file_path: Path | None = None,
    media_id: str | None = None,
) -> int:
    db = get_database()
    from core.database.repositories.track_repo import TrackRepository
    from database import _canonicalize_path
    from database.music_database import AudioFingerprint, LocalMedia, Track

    canonical_new_path = _canonicalize_path(str(file_path))
    paths_to_check = [canonical_new_path]
    if old_file_path:
        paths_to_check.append(_canonicalize_path(str(old_file_path)))

    track_dto = _build_track_from_metadata(file_path, metadata)

    with db.session_scope() as session:
        # Check if this physical file was already indexed in music_library.db under media_id or paths
        target_media_id = media_id or metadata.get("media_id")
        existing_lm = None
        if target_media_id:
            cleaned_mid = str(target_media_id).strip().split("?")[0]
            existing_lm = session.query(LocalMedia).filter(LocalMedia.media_id == cleaned_mid).first()
        if not existing_lm:
            existing_lm = session.query(LocalMedia).filter(LocalMedia.file_path.in_(paths_to_check)).first()

        if existing_lm:
            # Prevent premature autoflush during preliminary queries
            session.autoflush = False

            # 1. Prevent LocalMedia.file_path unique constraint collision
            conflicting_lm = (
                session.query(LocalMedia)
                .filter(LocalMedia.file_path == canonical_new_path, LocalMedia.id != existing_lm.id)
                .first()
            )

            if conflicting_lm:
                # Case A: True duplicate file
                is_true_dup = False
                lm_sz = existing_lm.file_size_bytes or (file_path.stat().st_size if file_path.exists() else None)
                conf_sz = conflicting_lm.file_size_bytes or (
                    Path(conflicting_lm.file_path).stat().st_size if Path(conflicting_lm.file_path).exists() else None
                )
                if lm_sz and conf_sz and lm_sz == conf_sz:
                    is_true_dup = True

                if not is_true_dup and track_dto.fingerprint:
                    conf_fp = session.query(AudioFingerprint).filter_by(media_id=conflicting_lm.media_id).first()
                    if conf_fp and conf_fp.chromaprint:
                        from core.matching_engine.fingerprinting import FingerprintMatcher

                        if FingerprintMatcher.get_confidence_score(track_dto.fingerprint, conf_fp.chromaprint) >= 0.95:
                            is_true_dup = True

                if is_true_dup:
                    logger.info(
                        "Merging redundant LocalMedia %s into existing conflicting LocalMedia %s for path %s",
                        existing_lm.id,
                        conflicting_lm.id,
                        canonical_new_path,
                    )
                    old_tr_id = existing_lm.track_id
                    session.delete(existing_lm)
                    session.flush()
                    if old_tr_id:
                        from core.metadata.adapter import ResolutionAdapter

                        ResolutionAdapter().prune_orphaned_track_if_empty(session, old_tr_id)
                    return 1
                else:
                    # Case B: Distinct Audio Edition / Different Master
                    from core.path_formatter import build_disambiguated_destination_path

                    disambiguated = build_disambiguated_destination_path(
                        metadata,
                        session=session,
                        current_file=file_path,
                        existing_media_id=existing_lm.id,
                    )
                    disambiguated_str = _canonicalize_path(str(disambiguated))
                    if file_path.exists() and str(file_path.resolve()) != str(disambiguated.resolve()):
                        from core.io_gatekeeper import Gatekeeper

                        Gatekeeper.authorize_and_execute(
                            operation="move",
                            source=str(file_path),
                            destination=str(disambiguated),
                        )
                    canonical_new_path = disambiguated_str
                    existing_lm.file_path = canonical_new_path
            else:
                existing_lm.file_path = canonical_new_path

            session.autoflush = True

            # Resolve artists and albums for track_dto
            TrackRepository.resolve_artists_and_albums(session, [track_dto])
            existing_track = session.get(Track, existing_lm.track_id) if existing_lm.track_id else None

            # 2. Check for Track Entity Reconsolidation (collapse identical tracks in album)
            target_album_id = track_dto.album_id or (existing_track.album_id if existing_track else None)
            from core.matching_engine.text_utils import normalize_title

            clean_normalized_title = normalize_title(
                track_dto.title or track_dto.raw_title or (existing_track.title if existing_track else "")
            )
            final_edition = (track_dto.edition or "").strip() or None

            target_canonical_track = None
            if target_album_id and clean_normalized_title:
                from sqlalchemy import or_

                edition_filter = (
                    Track.edition == final_edition
                    if final_edition
                    else or_(Track.edition.is_(None), Track.edition == "")
                )
                cand_q = session.query(Track).filter(
                    Track.album_id == target_album_id,
                    Track.normalized_title == clean_normalized_title,
                    edition_filter,
                )
                if existing_track:
                    cand_q = cand_q.filter(Track.id != existing_track.id)
                target_canonical_track = cand_q.first()

            if target_canonical_track:
                logger.info(
                    "Reconsolidating LocalMedia %s into existing canonical Track %s in Album %s",
                    existing_lm.id,
                    target_canonical_track.id,
                    target_album_id,
                )
                from sqlalchemy import or_

                # 3. Deduplicate sibling LocalMedia records under target_canonical_track
                ghosts = (
                    session.query(LocalMedia)
                    .filter(
                        LocalMedia.track_id == target_canonical_track.id,
                        LocalMedia.id != existing_lm.id,
                        or_(
                            LocalMedia.file_path == canonical_new_path,
                            (LocalMedia.media_id == existing_lm.media_id) if existing_lm.media_id else False,
                        ),
                    )
                    .all()
                )
                for g in ghosts:
                    logger.info("Pruning duplicate ghost LocalMedia %s under Track %s", g.id, target_canonical_track.id)
                    session.delete(g)

                old_track_id = existing_lm.track_id
                existing_lm.track_id = target_canonical_track.id
                existing_lm.track = target_canonical_track
                session.flush()

                if old_track_id and old_track_id != target_canonical_track.id:
                    from core.metadata.adapter import ResolutionAdapter

                    ResolutionAdapter().prune_orphaned_track_if_empty(session, old_track_id)

                # Sync multi-artist associations
                associations = getattr(track_dto, "_resolved_artist_associations", None)
                if not associations and track_dto.artist_id:
                    associations = [(track_dto.artist_id, "primary", 0)]
                if associations:
                    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
                    from database.music_database import TrackArtist

                    for a_id, role, pos in associations:
                        ta_stmt = sqlite_insert(TrackArtist).values(
                            {
                                "track_id": target_canonical_track.id,
                                "artist_id": a_id,
                                "role": role,
                                "position": pos,
                            }
                        )
                        ta_upsert = ta_stmt.on_conflict_do_update(
                            index_elements=["track_id", "artist_id", "role"],
                            set_={"position": ta_stmt.excluded.position},
                        )
                        session.execute(ta_upsert)

                if track_dto.fingerprint:
                    existing_fp = session.query(AudioFingerprint).filter_by(media_id=existing_lm.media_id).first()
                    if existing_fp:
                        existing_fp.chromaprint = track_dto.fingerprint
                        if track_dto.acoustid_id:
                            existing_fp.acoustid_id = track_dto.acoustid_id
                    else:
                        session.add(
                            AudioFingerprint(
                                media_id=existing_lm.media_id,
                                chromaprint=track_dto.fingerprint,
                                acoustid_id=track_dto.acoustid_id,
                            )
                        )
                session.flush()
                return 1

            if existing_lm.track_id:
                if existing_track:
                    from sqlalchemy import or_

                    # Deduplicate sibling LocalMedia records under existing_track
                    ghosts = (
                        session.query(LocalMedia)
                        .filter(
                            LocalMedia.track_id == existing_track.id,
                            LocalMedia.id != existing_lm.id,
                            or_(
                                LocalMedia.file_path == canonical_new_path,
                                (LocalMedia.media_id == existing_lm.media_id) if existing_lm.media_id else False,
                            ),
                        )
                        .all()
                    )
                    for g in ghosts:
                        logger.info("Pruning duplicate ghost LocalMedia %s under Track %s", g.id, existing_track.id)
                        session.delete(g)
                    session.flush()

                    # Check for sibling media under the same track
                    siblings = (
                        session.query(LocalMedia)
                        .filter(LocalMedia.track_id == existing_track.id, LocalMedia.id != existing_lm.id)
                        .all()
                    )
                    sibling_count = len(siblings)

                    diverges = False
                    sibling_diverges = False
                    if sibling_count > 0:
                        dto_title = (track_dto.title or track_dto.raw_title or "").strip().lower()
                        cur_title = (existing_track.title or "").strip().lower()
                        if dto_title and cur_title and dto_title != cur_title:
                            diverges = True

                        dto_edition = (track_dto.edition or "").strip().lower()
                        cur_edition = (existing_track.edition or "").strip().lower()
                        if (dto_edition or cur_edition) and dto_edition != cur_edition:
                            diverges = True

                        dto_artist = (track_dto.artist_name or getattr(track_dto, "artist", None) or "").strip().lower()
                        cur_artist = (existing_track.artist.name if existing_track.artist else "").strip().lower()
                        if dto_artist and cur_artist and dto_artist != cur_artist:
                            diverges = True

                        dto_album = (track_dto.album_title or getattr(track_dto, "album", None) or "").strip().lower()
                        cur_album = (existing_track.album.title if existing_track.album else "").strip().lower()
                        if dto_album and cur_album and dto_album != cur_album:
                            diverges = True

                        dto_mbid = (track_dto.musicbrainz_id or "").strip()
                        cur_mbid = (existing_track.musicbrainz_id or "").strip()
                        if dto_mbid and cur_mbid and dto_mbid != cur_mbid:
                            diverges = True

                        dto_isrc = (track_dto.isrc or "").strip()
                        cur_isrc = (existing_track.isrc or "").strip()
                        if dto_isrc and cur_isrc and dto_isrc != cur_isrc:
                            diverges = True

                        # Also check if any sibling media tags/stem diverge from track_dto
                        from core.matching_engine.text_utils import extract_version_info, normalize_title

                        dto_norm_title = normalize_title(track_dto.title or track_dto.raw_title or "")
                        for s in siblings:
                            s_path = s.file_path or ""
                            s_title = None
                            if s_path and Path(s_path).exists():
                                try:
                                    import echosync_core

                                    s_meta = echosync_core.read_metadata(s_path)
                                    if s_meta and isinstance(s_meta, dict) and s_meta.get("title"):
                                        s_title = str(s_meta["title"]).strip()
                                except Exception:
                                    pass
                            if not s_title and s_path:
                                stem = Path(s_path).stem
                                clean_stem = re.sub(r"^\d+[\s.-]+", "", stem).strip()
                                clean_stem_no_ver, _ = extract_version_info(clean_stem)
                                s_title = clean_stem_no_ver or clean_stem
                            if s_title and normalize_title(s_title) != dto_norm_title:
                                sibling_diverges = True
                                break

                    if sibling_count > 0 and diverges:
                        logger.info(
                            "Decoupling LocalMedia %s (%s) from Track %s (%s) due to divergent metadata",
                            existing_lm.id,
                            existing_lm.file_path,
                            existing_track.id,
                            existing_track.title,
                        )
                        from core.metadata.adapter import ResolutionAdapter

                        adapter = ResolutionAdapter()
                        reconciled = adapter.reconcile_media_assignment(
                            session=session,
                            media=existing_lm,
                            enhanced_dto=track_dto,
                            current_chromaprint=track_dto.fingerprint,
                        )

                        # Sync multi-artist associations
                        associations = getattr(track_dto, "_resolved_artist_associations", None)
                        if not associations and track_dto.artist_id:
                            associations = [(track_dto.artist_id, "primary", 0)]
                        if associations and reconciled:
                            from sqlalchemy.dialects.sqlite import insert as sqlite_insert

                            from database.music_database import TrackArtist

                            for a_id, role, pos in associations:
                                ta_stmt = sqlite_insert(TrackArtist).values(
                                    {
                                        "track_id": reconciled.id,
                                        "artist_id": a_id,
                                        "role": role,
                                        "position": pos,
                                    }
                                )
                                ta_upsert = ta_stmt.on_conflict_do_update(
                                    index_elements=["track_id", "artist_id", "role"],
                                    set_={"position": ta_stmt.excluded.position},
                                )
                                session.execute(ta_upsert)

                        # If fingerprint exists, attach or update AudioFingerprint
                        if track_dto.fingerprint:
                            existing_fp = (
                                session.query(AudioFingerprint).filter_by(media_id=existing_lm.media_id).first()
                            )
                            if existing_fp:
                                existing_fp.chromaprint = track_dto.fingerprint
                                if track_dto.acoustid_id:
                                    existing_fp.acoustid_id = track_dto.acoustid_id
                            else:
                                session.add(
                                    AudioFingerprint(
                                        media_id=existing_lm.media_id,
                                        chromaprint=track_dto.fingerprint,
                                        acoustid_id=track_dto.acoustid_id,
                                    )
                                )

                        session.flush()
                        return 1

                    # No siblings or not diverging: update existing Track in place
                    from core.metadata.adapter import ResolutionAdapter

                    adapter = ResolutionAdapter()
                    existing_track = adapter.hydrate_track(track_dto, session, existing_track)

                    # We still resolve album since adapter only does artist & scalars
                    TrackRepository.resolve_artists_and_albums(session, [track_dto])
                    if track_dto.album_id is not None:
                        existing_track.album_id = track_dto.album_id
                    if track_dto.sort_title:
                        existing_track.sort_title = track_dto.sort_title
                    if track_dto.musicbrainz_id:
                        existing_track.musicbrainz_id = track_dto.musicbrainz_id
                    if track_dto.isrc:
                        existing_track.isrc = track_dto.isrc
                    if track_dto.duration_ms and track_dto.duration_ms > 0:
                        existing_track.duration = round(track_dto.duration_ms / 1000.0)
                        existing_lm.duration_ms = int(track_dto.duration_ms)
                    active_dur_ms = _coerce_int(metadata.get("active_duration_ms"))
                    if active_dur_ms and active_dur_ms > 0:
                        existing_lm.active_duration_ms = active_dur_ms

                    # Sync multi-artist associations
                    associations = getattr(track_dto, "_resolved_artist_associations", None)
                    if not associations and track_dto.artist_id:
                        associations = [(track_dto.artist_id, "primary", 0)]
                    if associations:
                        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

                        from database.music_database import TrackArtist

                        for a_id, role, pos in associations:
                            ta_stmt = sqlite_insert(TrackArtist).values(
                                {
                                    "track_id": existing_track.id,
                                    "artist_id": a_id,
                                    "role": role,
                                    "position": pos,
                                }
                            )
                            ta_upsert = ta_stmt.on_conflict_do_update(
                                index_elements=["track_id", "artist_id", "role"],
                                set_={"position": ta_stmt.excluded.position},
                            )
                            session.execute(ta_upsert)

                    # If fingerprint exists, attach or update AudioFingerprint
                    if track_dto.fingerprint:
                        existing_fp = session.query(AudioFingerprint).filter_by(media_id=existing_lm.media_id).first()
                        if existing_fp:
                            existing_fp.chromaprint = track_dto.fingerprint
                            if track_dto.acoustid_id:
                                existing_fp.acoustid_id = track_dto.acoustid_id
                        else:
                            session.add(
                                AudioFingerprint(
                                    media_id=existing_lm.media_id,
                                    chromaprint=track_dto.fingerprint,
                                    acoustid_id=track_dto.acoustid_id,
                                )
                            )

                    if sibling_count > 0 and sibling_diverges:
                        TrackRepository.decouple_collapsed_media(session)

                    session.flush()
                    return 1

        # Fallback: file is brand new to the library -> bulk upsert
        upsert_res = TrackRepository.bulk_upsert_tracks(session, [track_dto])
        if track_dto.fingerprint:
            new_lm = session.query(LocalMedia).filter(LocalMedia.file_path == canonical_new_path).first()
            if new_lm:
                existing_fp = session.query(AudioFingerprint).filter_by(media_id=new_lm.media_id).first()
                if existing_fp:
                    existing_fp.chromaprint = track_dto.fingerprint
                    if track_dto.acoustid_id:
                        existing_fp.acoustid_id = track_dto.acoustid_id
                else:
                    session.add(
                        AudioFingerprint(
                            media_id=new_lm.media_id,
                            chromaprint=track_dto.fingerprint,
                            acoustid_id=track_dto.acoustid_id,
                        )
                    )
                session.flush()
        return upsert_res


def _normalize_duration_seconds(metadata: dict[str, Any], file_path: Path) -> int | None:
    duration = _coerce_int(metadata.get("duration"))
    if duration and duration > 0:
        if duration > 10000:
            return max(1, int(round(duration / 1000.0)))
        return duration

    duration_ms = _coerce_int(metadata.get("duration_ms"))
    if duration_ms and duration_ms > 0:
        return max(1, int(round(duration_ms / 1000.0)))

    enhancer = get_metadata_enhancer()
    if hasattr(enhancer, "_get_audio_duration"):
        try:
            detected = enhancer._get_audio_duration(file_path)
            duration_detected = _coerce_int(detected)
            if duration_detected and duration_detected > 0:
                if duration_detected > 10000:
                    return max(1, int(round(duration_detected / 1000.0)))
                return duration_detected
        except Exception:
            pass

    return None


def _submit_acoustid_contribution_async(fingerprint: str, duration: int, mbid: str) -> None:
    try:
        fingerprint_provider = get_plugin_by_capability(Capability.RESOLVE_FINGERPRINT)
        if not fingerprint_provider:
            logger.debug("Skipping AcoustID contribution: no submit-capable fingerprint provider")
            return

        if hasattr(fingerprint_provider, "queue_fingerprint_submission"):
            fingerprint_provider.queue_fingerprint_submission(fingerprint=fingerprint, duration=duration, mbid=mbid)
        elif hasattr(fingerprint_provider, "submit_fingerprint"):
            fingerprint_provider.submit_fingerprint(fingerprint=fingerprint, duration=duration, mbid=mbid)
    except Exception as exc:
        logger.debug(f"AcoustID background contribution failed: {exc}")


@router.get("")
def get_review_queue():
    """Return pending metadata review tasks sorted newest-first."""
    db = get_working_database()
    try:
        with db.session_scope() as session:
            tasks = (
                session.query(ReviewTask)
                .filter(ReviewTask.status == "pending")
                .order_by(ReviewTask.created_at.desc())
                .all()
            )
            serialized_tasks: list[dict[str, Any]] = []
            for task in tasks:
                detected_metadata = _normalize_detected_metadata(getattr(task, "detected_metadata", None))
                current_metadata = _read_current_metadata(task)

                serialized_tasks.append(
                    _serialize_task(
                        task,
                        detected_metadata=detected_metadata,
                        current_metadata=current_metadata,
                    )
                )
            return {"tasks": serialized_tasks}
    except Exception as e:
        logger.error(f"Failed to fetch review queue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch review queue")


@router.post("")
@router.post("/tasks")
@review_tasks_router.post("")
def create_review_task(
    payload: CreateReviewTaskRequest | None = None,
    media_id: str | None = None,
    _=Depends(require_auth),
):
    """Initialize a new ReviewTask referencing the targeted physical file via media_id."""
    req_media_id = None
    file_path_str = None
    track_dict = {}
    conf_score = 0.0

    if payload:
        req_media_id = payload.media_id
        file_path_str = payload.file_path
        track_dict = payload.track_data or {}
        if payload.metadata:
            track_dict = _merge_metadata(track_dict, payload.metadata)
        if payload.confidence_score is not None:
            conf_score = payload.confidence_score

    if not req_media_id and media_id is not None:
        req_media_id = media_id

    if isinstance(track_dict, dict) and "media_id" in track_dict and track_dict["media_id"] is not None:
        validated_dict_mid = _validate_media_id(track_dict["media_id"])
        track_dict["media_id"] = validated_dict_mid
        if req_media_id is None:
            req_media_id = validated_dict_mid

    if req_media_id is not None:
        req_media_id = _validate_media_id(req_media_id)

    db = get_database()
    if req_media_id:
        with db.session_scope() as session:
            from database.music_database import LocalMedia

            media = session.query(LocalMedia).filter(LocalMedia.media_id == req_media_id).first()
            if not media:
                raise HTTPException(status_code=404, detail=f"LocalMedia with media_id '{req_media_id}' not found")
            file_path_str = media.file_path
            track_dict["media_id"] = req_media_id
            if media.track:
                track_dict["sync_id"] = media.track.sync_id
                if not track_dict.get("title"):
                    track_dict["title"] = media.track.title
                if not track_dict.get("artist") and media.track.artist:
                    track_dict["artist"] = media.track.artist.name
                if not track_dict.get("album") and media.track.album:
                    track_dict["album"] = media.track.album.title

    if not file_path_str:
        raise HTTPException(status_code=400, detail="Either media_id or file_path must be provided")

    working_db = get_working_database()
    with working_db.session_scope() as session:
        task = session.query(ReviewTask).filter(ReviewTask.file_path == file_path_str).first()
        if not task:
            task = ReviewTask(
                file_path=file_path_str,
                status="pending",
                confidence_score=conf_score,
                track_data=track_dict,
            )
            if req_media_id:
                task.media_id = req_media_id
            session.add(task)
            session.flush()
        else:
            task.track_data = _merge_metadata(task.track_data, track_dict)
            if req_media_id:
                task.media_id = req_media_id
            session.flush()

        serialized = _serialize_task(task)
        return {"success": True, "id": task.id, "task": serialized}


@router.patch("/{task_id}/save")
@router.put("/{task_id}")
def update_review_queue_item(task_id: int, payload: UpdateReviewQueueRequest, _=Depends(require_auth)):
    """Update track_data JSON blob or save progress incrementally for a review task."""
    metadata = payload.metadata
    if metadata is None:
        metadata = payload.track_data
    if metadata is None:
        metadata = payload.model_dump(exclude_unset=True)

    if metadata is None:
        metadata = {}

    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="Invalid metadata payload")

    validated_payload_media_id: str | None = None
    if payload.media_id is not None:
        validated_payload_media_id = _validate_media_id(payload.media_id)
    if "media_id" in metadata and metadata["media_id"] is not None:
        validated_meta_mid = _validate_media_id(metadata["media_id"])
        metadata = dict(metadata)
        metadata["media_id"] = validated_meta_mid
        if validated_payload_media_id is None:
            validated_payload_media_id = validated_meta_mid

    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            if validated_payload_media_id is not None:
                task.media_id = validated_payload_media_id

            # Update/Merge into track_data blob incrementally
            if not task.track_data:
                task.track_data = {}
            for k, v in metadata.items():
                task.track_data[k] = v

            # Standardize properties through detected_metadata setter (backward compatibility)
            if any(
                k in metadata
                for k in [
                    "title",
                    "artist",
                    "album",
                    "edition",
                    "version",
                    "year",
                    "musicbrainz_id",
                    "mbid",
                    "acoustid",
                    "acoustid_id",
                ]
            ):
                task.detected_metadata = metadata

            return {"success": True, "id": task.id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update review task")


@router.post("/{task_id}/approve")
def approve_review_queue_item(
    task_id: int,
    payload: ApproveReviewQueueRequest | None = None,
    _=Depends(require_auth),
):
    """Approve a review task: write tags, relocate file, import file, mark approved."""
    final_metadata = (
        (payload.metadata or payload.detected_metadata or payload.model_dump(exclude_unset=True))
        if payload is not None
        else {}
    )

    if not isinstance(final_metadata, dict):
        raise HTTPException(status_code=400, detail="Invalid metadata payload")

    if "media_id" in final_metadata and final_metadata["media_id"] is not None:
        final_metadata = dict(final_metadata)
        final_metadata["media_id"] = _validate_media_id(final_metadata["media_id"])

    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            if not task.file_path:
                raise HTTPException(status_code=404, detail="File path not found")

            file_path = Path(task.file_path)
            if not file_path.exists() or not file_path.is_file():
                raise HTTPException(status_code=404, detail="File does not exist")

            from core.task_manager.task_queue import job_queue

            def _background_approval_task():
                working_db = get_working_database()
                try:
                    from core.db.echo_sync_track import EchosyncTrack

                    # 1. Resolve task details in fresh working DB session
                    file_path_str = None
                    task_media_id = None
                    track_dict = None
                    with working_db.session_scope() as w_session:
                        task_row = w_session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
                        if not task_row:
                            logger.error(f"Task {task_id} not found in working DB")
                            return
                        file_path_str = task_row.file_path
                        task_media_id = getattr(task_row, "media_id", None)
                        track_dict = task_row.track_data or {}
                        if not track_dict and task_row.detected_metadata:
                            track_dict = task_row.detected_metadata

                    if not file_path_str:
                        msg = f"Task {task_id} has no file_path"
                        logger.error(msg)
                        _mark_review_task_failed(working_db, task_id, msg)
                        return

                    file_path_obj = Path(file_path_str)
                    if not file_path_obj.exists() or not file_path_obj.is_file():
                        msg = f"Physical file does not exist: {file_path_str}"
                        logger.error(msg)
                        _mark_review_task_failed(working_db, task_id, msg)
                        return

                    # Construct EchosyncTrack object from staging track_data
                    staged_track = EchosyncTrack.from_dict(track_dict)

                    # Physical audio metrics are invariant and derived purely from native DSP inspection
                    _PHYSICAL_FORM_FIELDS = {
                        "duration",
                        "duration_ms",
                        "bitrate",
                        "sample_rate",
                        "channels",
                        "media_id",
                    }

                    # Update staged_track properties with any modifications from final_metadata (stripping physical fields)
                    staged_updates: dict[str, Any] = {}
                    if final_metadata:
                        if final_metadata.get("title"):
                            staged_updates["raw_title"] = final_metadata["title"]
                            staged_updates["title"] = final_metadata["title"]
                            staged_updates["display_title"] = final_metadata["title"]
                        if "edition" in final_metadata:
                            staged_updates["edition"] = final_metadata["edition"]
                        elif "version" in final_metadata:
                            staged_updates["edition"] = final_metadata["version"]
                        if final_metadata.get("artist"):
                            staged_updates["artist_name"] = final_metadata["artist"]
                        if final_metadata.get("album"):
                            staged_updates["album_title"] = final_metadata["album"]
                        if final_metadata.get("year"):
                            try:
                                staged_updates["release_year"] = int(final_metadata["year"])
                            except Exception:
                                pass
                        if final_metadata.get("track_number"):
                            try:
                                staged_updates["track_number"] = int(final_metadata["track_number"])
                            except Exception:
                                pass
                        if final_metadata.get("disc_number"):
                            try:
                                staged_updates["disc_number"] = int(final_metadata["disc_number"])
                            except Exception:
                                pass
                        mbid_val = final_metadata.get("musicbrainz_id") or final_metadata.get("mbid")
                        if mbid_val:
                            staged_updates["musicbrainz_id"] = str(mbid_val).strip()
                        if final_metadata.get("isrc"):
                            staged_updates["isrc"] = final_metadata["isrc"]
                        acoustid_val = final_metadata.get("acoustid_id") or final_metadata.get("acoustid")
                        if acoustid_val:
                            staged_updates["acoustid_id"] = str(acoustid_val).strip()
                        fp_val = (
                            final_metadata.get("fingerprint")
                            or final_metadata.get("chromaprint")
                            or final_metadata.get("acoustid_fingerprint")
                        )
                        if fp_val:
                            staged_updates["fingerprint"] = str(fp_val).strip()

                    # Derive physical properties purely from DSP inspection of container
                    import echosync_core

                    native_props = echosync_core.extract_metadata(str(file_path_obj)) or {}
                    native_dur = native_props.get("duration_ms")
                    if native_dur is not None:
                        staged_updates["duration_ms"] = int(native_dur)
                    elif native_props.get("duration") is not None:
                        staged_updates["duration_ms"] = int(round(float(native_props["duration"]) * 1000))

                    active_duration_ms = None
                    try:
                        fp_res = echosync_core.fingerprint_and_hash_audio(str(file_path_obj), True)
                        if isinstance(fp_res, tuple) and len(fp_res) >= 2:
                            if fp_res[0] and not staged_updates.get("fingerprint") and not staged_track.fingerprint:
                                staged_updates["fingerprint"] = fp_res[0]
                            if fp_res[1]:
                                active_duration_ms = int(round(float(fp_res[1]) * 1000))
                    except Exception as fp_err:
                        logger.debug(f"Active duration extraction skipped during approval for {file_path_obj}: {fp_err}")

                    if staged_updates:
                        staged_track = replace(staged_track, **staged_updates)

                    # Merge the finalized metadata back to dict for tagging
                    metadata_to_tag = {
                        "title": staged_track.title,
                        "edition": staged_track.edition,
                        "artist": staged_track.artist_name,
                        "album": staged_track.album_title,
                        "year": str(staged_track.release_year) if staged_track.release_year else None,
                        "track_number": str(staged_track.track_number) if staged_track.track_number else None,
                        "disc_number": str(staged_track.disc_number) if staged_track.disc_number else None,
                        "musicbrainz_id": staged_track.musicbrainz_id,
                        "isrc": staged_track.isrc,
                        "acoustid_id": staged_track.acoustid_id,
                        "mb_release_id": staged_track.mb_release_id,
                        "fingerprint": staged_track.fingerprint,
                        "duration_ms": staged_track.duration_ms,
                        "active_duration_ms": active_duration_ms,
                    }

                    # 2. Tag and verify the physical file
                    enhancer = get_metadata_enhancer()
                    from services.metadata_enhancer import (
                        MetadataWriteVerificationError,
                    )

                    try:
                        enhancer.tag_file_verified(file_path_obj, metadata_to_tag)
                    except MetadataWriteVerificationError as e:
                        logger.error(f"Tag verification failed for {file_path_obj}; aborting library import: {e}")
                        raise RuntimeError(f"Failed to verify written tags on disk: {e}") from e
                    except Exception as e:
                        logger.error(f"Unexpected error during tag verification for {file_path_obj}: {e}")
                        raise RuntimeError(f"Failed to verify written tags on disk: {e}") from e

                    # 3. Calculate target relocation path using build_destination_path
                    from core.path_formatter import build_disambiguated_destination_path

                    music_db = get_database()
                    with music_db.session_scope() as m_session:
                        destination_path = build_disambiguated_destination_path(
                            metadata_to_tag,
                            session=m_session,
                            current_file=file_path_obj,
                        )

                    from core.io_gatekeeper import Gatekeeper
                    from services.library_watcher import suppress_path

                    with suppress_path(str(destination_path)):
                        # 4. Relocate file physically if path changes
                        if destination_path.resolve() != file_path_obj.resolve():
                            destination_path.parent.mkdir(parents=True, exist_ok=True)
                            Gatekeeper.authorize_and_execute(
                                operation="move",
                                source=str(file_path_obj),
                                destination=str(destination_path),
                            )
                            logger.info(f"Relocated file: {file_path_obj} -> {destination_path}")

                            # Prune empty source parent directories halting at download_dir
                            from core.utils.file_utils import (
                                prune_empty_parent_directories,
                            )

                            dl_dir = config_manager.get("storage.download_dir") or config_manager.get("download_dir")
                            stop_roots = {Path(dl_dir).resolve()} if dl_dir else set()
                            prune_empty_parent_directories(file_path_obj, stop_at_roots=stop_roots)

                        # 5. Community Contribution (AcoustID)
                        auto_contrib_enabled = config_manager.get(
                            "metadata_enhancement.enable_acoustid_auto_submission",
                            False,
                        ) or config_manager.get("metadata_enhancement.contribute_metadata", False)

                        fingerprint_provider = get_plugin_by_capability(Capability.RESOLVE_FINGERPRINT)
                        plugin_auto_contrib = False
                        if fingerprint_provider and hasattr(fingerprint_provider, "config"):
                            p_cfg = fingerprint_provider.config.get("auto_contribute")
                            plugin_auto_contrib = p_cfg == "true" or p_cfg is True

                        should_contribute = auto_contrib_enabled or plugin_auto_contrib
                        acoustid_fingerprint = str(staged_track.fingerprint or "").strip()
                        musicbrainz_id = str(staged_track.musicbrainz_id or "").strip()

                        import uuid

                        is_valid_mbid = False
                        if musicbrainz_id:
                            try:
                                uuid.UUID(musicbrainz_id)
                                is_valid_mbid = True
                            except ValueError:
                                is_valid_mbid = False

                        if should_contribute and acoustid_fingerprint and is_valid_mbid:
                            duration_seconds = _normalize_duration_seconds(metadata_to_tag, destination_path)
                            if duration_seconds and duration_seconds > 0:
                                _submit_acoustid_contribution_async(
                                    fingerprint=acoustid_fingerprint,
                                    duration=duration_seconds,
                                    mbid=musicbrainz_id,
                                )

                        # 6. Create or update the final LocalMedia and Track rows in music_library.db (atomic import)
                        _import_single_file(
                            destination_path,
                            metadata_to_tag,
                            old_file_path=file_path_obj,
                            media_id=task_media_id,
                        )

                    # 7. Deletion of the ReviewTask from working.db
                    with working_db.session_scope() as w_session:
                        task_row = w_session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
                        if task_row:
                            w_session.delete(task_row)
                            w_session.commit()
                            logger.info(f"Successfully deleted review task {task_id}")

                except Exception as e:
                    logger.error(f"Background approval failed for task {task_id}: {e}", exc_info=True)
                    _mark_review_task_failed(
                        working_db,
                        task_id,
                        str(e) or type(e).__name__,
                    )

            # Register and run the task as a one-off background job
            job_name = f"approve_metadata_{task_id}"
            job_queue.register_job(job_name, _background_approval_task, interval_seconds=None)
            job_queue.execute_job_now(job_name)

            return {"success": True, "id": task.id, "status": "approved_queued"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to approve review task")


@router.post("/{task_id}/reject")
@router.post("/tasks/{task_id}/reject")
@router.delete("/{task_id}")
@router.delete("/tasks/{task_id}")
def reject_and_delete_review_queue_item(task_id: int, _=Depends(require_auth)):
    """
    Reject a review task, securely delete the physical unverified file from disk,
    update the ReviewTask status to 'rejected', and emit REVIEW_TASK_REJECTED event.
    """
    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            # Validate jail / storage containment
            file_path_str = task.file_path
            resolved_file = None
            if file_path_str:
                resolved_file = _resolve_task_file(task)
                if not resolved_file:
                    try:
                        p = Path(file_path_str).expanduser().resolve()
                        dl_dir = config_manager.get("storage.download_dir") or config_manager.get("download_dir")
                        lib_dir = config_manager.get("storage.library_dir") or config_manager.get("library_dir")
                        poor_dir = config_manager.get("storage.poor_metadata_dir")

                        allowed = []
                        if dl_dir:
                            allowed.append(Path(dl_dir).resolve())
                        if lib_dir:
                            allowed.append(Path(lib_dir).resolve())
                        if poor_dir:
                            allowed.append(Path(poor_dir).resolve())

                        for a in allowed:
                            try:
                                if p.is_relative_to(a):
                                    resolved_file = p
                                    break
                            except Exception:
                                pass
                    except Exception:
                        pass

                # Delete the physical file if it exists and is within allowed directory
                if resolved_file and resolved_file.exists() and resolved_file.is_file():
                    try:
                        from core.io_gatekeeper import Gatekeeper

                        dl_dir = config_manager.get("storage.download_dir") or config_manager.get("download_dir")
                        lib_dir = config_manager.get("storage.library_dir") or config_manager.get("library_dir")
                        poor_dir = config_manager.get("storage.poor_metadata_dir")

                        in_default_roots = any(
                            d and resolved_file.is_relative_to(Path(d).resolve())
                            for d in (dl_dir, lib_dir)
                        )
                        if not in_default_roots and poor_dir and resolved_file.is_relative_to(Path(poor_dir).resolve()):
                            allowed_roots = [
                                Path(d).resolve() for d in (dl_dir, lib_dir, poor_dir) if d
                            ]
                            Gatekeeper(allowed_roots=allowed_roots).authorize_and_execute(
                                operation="delete_file",
                                target_uri=str(resolved_file),
                            )
                        else:
                            Gatekeeper.authorize_and_execute(
                                operation="delete_file",
                                target_uri=str(resolved_file),
                            )
                        logger.info(f"Deleted physical file for rejected task {task_id}: {resolved_file}")
                    except Exception as del_err:
                        logger.warning(f"Failed to delete file {resolved_file} for task {task_id}: {del_err}")

            # Update status to rejected
            task.status = "rejected"
            file_path_copy = task.file_path

            # Emit event via event_bus
            try:
                from core.event_bus import event_bus

                event_bus.publish(
                    "REVIEW_TASK_REJECTED",
                    {
                        "event": "REVIEW_TASK_REJECTED",
                        "task_id": task.id,
                        "file_path": file_path_copy,
                    },
                )
            except Exception as eb_err:
                logger.warning(f"Failed to publish REVIEW_TASK_REJECTED event: {eb_err}")

            return {"success": True, "id": task.id, "status": "rejected"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reject review task")


@router.get("/{task_id}/stream")
def stream_review_queue_item(task_id: int):
    """Stream raw audio file for a review task with Range support."""
    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            file_path = _resolve_task_file(task)
            if not file_path:
                raise HTTPException(status_code=404, detail="File does not exist")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stream review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to stream review file")

    return FileResponse(
        path=str(file_path),
        media_type="audio/mpeg" if file_path.suffix.lower() == ".mp3" else "audio/flac",
        filename=file_path.name,
    )


@router.get("/{task_id}/cover")
def get_review_queue_item_cover(task_id: int):
    """Stream embedded cover art for a review task."""
    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            file_path = _resolve_task_file(task)
            if not file_path:
                raise HTTPException(status_code=404, detail="File does not exist")

            from core.file_handling.tagging_io import read_tags

            metadata = read_tags(file_path)

            cover_data = metadata.get("_cover_data")
            cover_mime = metadata.get("_cover_mime") or "image/jpeg"

            if not cover_data:
                raise HTTPException(status_code=404, detail="No embedded cover found")

            from fastapi.responses import Response

            return Response(content=cover_data, media_type=cover_mime)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch cover for review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch cover")


@router.post("/{task_id}/lookup/acoustid")
def lookup_review_queue_item_acoustid(task_id: int, _=Depends(require_auth)):
    """Run AcoustID fingerprint lookup and update detected metadata.

    Flow
    ----
    1. Generate fingerprint + duration from fpcalc in a single pass.
    2. Persist the raw fingerprint in the task immediately so it is always
       available for later AcoustID / MusicBrainz submission even if the
       lookup API returns no match.
    3. Call AcoustID API.  If a match is found, populate acoustid_id and MBID
       and enrich from MusicBrainz.
    4. If no match exists yet (track not in the AcoustID library), return 200
       with the stored fingerprint + duration so the UI can present the user
       with a "submit to AcoustID" option rather than a hard error.
    """
    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            file_path = _resolve_task_file(task)
            if not file_path:
                raise HTTPException(status_code=404, detail="File does not exist")

            from sqlalchemy.orm.attributes import flag_modified

            from core.matching_engine.text_utils import normalize_title
            from core.matching_engine.track_parser import TrackParser
            from core.matching_engine.trust_gate import is_generic_title
            from core.metadata.engine import MetadataResolutionEngine, extract_filename_title
            from core.metadata.schemas import ResolutionRequest
            from core.task_manager.task_queue import db_write_lease

            track_obj = EchosyncTrack.from_dict(task.track_data or {})

            # 1. Sanitize filename stem: route through normalize_title and track parser cleansing
            target_title = None
            try:
                parsed_track = TrackParser.parse_filename(file_path.name)
                if parsed_track and parsed_track.title and not is_generic_title(parsed_track.title):
                    target_title = re.sub(r"\s*[\(\[]\d+[\)\]]$", "", parsed_track.title).strip()
            except Exception:
                pass

            if not target_title:
                norm_fn = normalize_title(file_path.name)
                try:
                    norm_parsed = TrackParser.parse_filename(norm_fn)
                    if norm_parsed and norm_parsed.title and not is_generic_title(norm_parsed.title):
                        target_title = norm_parsed.title.strip()
                except Exception:
                    pass

            if not target_title:
                target_title = extract_filename_title(file_path.name)

            if target_title:
                target_title = re.sub(r"\s*[\(\[]\d+[\)\]]$", "", target_title).strip()

            # 2. Inspect existing chromaprint string from task or DB and invalidate stale (>1400 chars)
            existing_chromaprint = (
                (task.track_data or {}).get("fingerprint")
                or (task.track_data or {}).get("chromaprint")
                or (task.detected_metadata or {}).get("fingerprint")
                or (task.detected_metadata or {}).get("chromaprint")
            )

            canonical_path = _canonicalize_path(str(file_path))
            main_db = get_database()
            media_record = None
            try:
                with main_db.session_scope() as main_session:
                    from database.music_database import AudioFingerprint, LocalMedia

                    media_record = main_session.query(LocalMedia).filter(LocalMedia.file_path == canonical_path).first()
                    if media_record:
                        af = (
                            main_session.query(AudioFingerprint)
                            .filter(AudioFingerprint.media_id == media_record.media_id)
                            .first()
                        )
                        if af and af.chromaprint and not existing_chromaprint:
                            existing_chromaprint = af.chromaprint
            except Exception as exc:
                logger.debug(f"Failed to probe AudioFingerprint in main database: {exc}")

            clamped_fingerprint = existing_chromaprint
            if existing_chromaprint and len(existing_chromaprint) > 4000:
                logger.warning(
                    f"Task {task_id}: stale bloated chromaprint detected (len={len(existing_chromaprint)} > 4000); "
                    f"forcing regeneration via clamped Rust DSP engine: {file_path.name}"
                )
                clamped_fingerprint = None
                try:
                    import echosync_core

                    native_res = echosync_core.fingerprint_and_hash_audio(str(file_path), False)
                    if isinstance(native_res, tuple) and len(native_res) >= 2:
                        clamped_fingerprint = native_res[0]
                    elif isinstance(native_res, str):
                        clamped_fingerprint = native_res
                except Exception as dsp_err:
                    logger.error(f"Failed to regenerate clamped fingerprint for task {task_id}: {dsp_err}")

                if clamped_fingerprint:
                    if not task.track_data:
                        task.track_data = {}
                    task.track_data["fingerprint"] = clamped_fingerprint
                    track_obj = replace(track_obj, fingerprint=clamped_fingerprint)
                    flag_modified(task, "track_data")

                    # Update database record wrapped inside db_write_lease
                    if media_record:
                        try:
                            with db_write_lease("metadata_review_update_stale_fingerprint"):
                                with main_db.session_scope() as main_session:
                                    from database.music_database import AudioFingerprint

                                    af = (
                                        main_session.query(AudioFingerprint)
                                        .filter(AudioFingerprint.media_id == media_record.media_id)
                                        .first()
                                    )
                                    if af:
                                        af.chromaprint = clamped_fingerprint
                                        main_session.flush()
                        except Exception as db_err:
                            logger.error(f"Failed to update clamped fingerprint in main db: {db_err}")

            duration_ms = _coerce_int(track_obj.duration_ms)
            duration_sec = duration_ms / 1000.0 if (duration_ms and duration_ms > 0) else None

            engine = MetadataResolutionEngine(
                acoustid_provider=_get_fingerprint_provider(),
                metadata_provider=_get_metadata_provider(),
                spotify_provider=_get_spotify_provider(),
            )
            req = ResolutionRequest(
                media_id=str(task.id),
                sync_id=track_obj.sync_id if hasattr(track_obj, "sync_id") else None,
                file_path=Path(file_path),
                baseline_title=target_title,
                baseline_artist=None,  # Zero-trust: audio proof determines true artist without dirty baseline bias
                baseline_album=None,
                chromaprint=clamped_fingerprint,
                duration=duration_sec,
                duration_ms=duration_ms,
                ignore_embedded_mbid=True,
                ignore_cache=True,
            )
            res = engine.resolve_track(req, enabled_stages=["acoustid"])

            if res.chromaprint:
                track_obj = replace(track_obj, fingerprint=res.chromaprint)

            if not res or res.confidence_score <= 0.0:
                # Persist fingerprint even on miss so user can submit to AcoustID
                if res and res.chromaprint:
                    task.track_data = track_obj.to_dict()
                    flag_modified(task, "track_data")
                    if media_record:
                        try:
                            with db_write_lease("metadata_review_fingerprint_miss"):
                                with main_db.session_scope() as main_session:
                                    from database.music_database import AudioFingerprint

                                    af = (
                                        main_session.query(AudioFingerprint)
                                        .filter(AudioFingerprint.media_id == media_record.media_id)
                                        .first()
                                    )
                                    if af and af.chromaprint != res.chromaprint:
                                        af.chromaprint = res.chromaprint
                                        main_session.flush()
                        except Exception as db_err:
                            logger.debug(f"Failed to update fingerprint in main db on miss: {db_err}")
                logger.warning(
                    f"AcoustID scan for task {task_id}: no verified match found "
                    f"(score={res.confidence_score if res else 0.0}, fingerprint_len={len(res.chromaprint or '') if res else 0})"
                )
                raise HTTPException(
                    status_code=404,
                    detail="AcoustID found no verified matching recording for this acoustic fingerprint.",
                )

            # Match found
            updates: dict[str, Any] = {
                "edition": res.edition,
                "identifiers": {**(track_obj.identifiers or {}), "source": "acoustid_lookup"},
            }
            if res.acoustid_id:
                updates["acoustid_id"] = res.acoustid_id
            if res.musicbrainz_track_id:
                updates["musicbrainz_id"] = res.musicbrainz_track_id
            if res.musicbrainz_release_id:
                updates["mb_release_id"] = res.musicbrainz_release_id
            if res.title:
                updates["title"] = res.title
                updates["raw_title"] = res.title
                updates["display_title"] = res.title
            if res.artist:
                updates["artist_name"] = res.artist
            if res.album:
                updates["album_title"] = res.album
            if res.year:
                updates["release_year"] = res.year
            if res.track_number is not None:
                updates["track_number"] = res.track_number
            if res.disc_number is not None:
                updates["disc_number"] = res.disc_number
            if res.isrc:
                updates["isrc"] = res.isrc
            if res.chromaprint:
                updates["fingerprint"] = res.chromaprint
            track_obj = replace(track_obj, **updates)
            res_dict = res.to_dict()
            res_dict["edition"] = res.edition
            if res.chromaprint:
                res_dict["fingerprint"] = res.chromaprint
                res_dict["chromaprint"] = res.chromaprint
            task.track_data = track_obj.to_dict()
            task.detected_metadata = res_dict
            task.proposed_metadata = res_dict
            task.confidence_score = res.confidence_score
            flag_modified(task, "track_data")

            if media_record and (res.chromaprint or res.acoustid_id):
                try:
                    with db_write_lease("metadata_review_fingerprint_match"):
                        with main_db.session_scope() as main_session:
                            from database.music_database import AudioFingerprint

                            af = (
                                main_session.query(AudioFingerprint)
                                .filter(AudioFingerprint.media_id == media_record.media_id)
                                .first()
                            )
                            if af:
                                if res.chromaprint:
                                    af.chromaprint = res.chromaprint
                                if res.acoustid_id:
                                    af.acoustid_id = res.acoustid_id
                                main_session.flush()
                except Exception as db_err:
                    logger.debug(f"Failed to update fingerprint in main db on match: {db_err}")

            updated_fields = []
            if track_obj.title or track_obj.raw_title:
                updated_fields.append("title")
            if track_obj.edition:
                updated_fields.append("edition")
            if track_obj.artist_name:
                updated_fields.append("artist")
            if track_obj.album_title:
                updated_fields.append("album")
            if track_obj.release_year:
                updated_fields.append("year")
            if track_obj.track_number is not None:
                updated_fields.append("track_number")
            if track_obj.disc_number is not None:
                updated_fields.append("disc_number")
            if track_obj.musicbrainz_id:
                updated_fields.append("musicbrainz_id")
            if track_obj.mb_release_id:
                updated_fields.append("musicbrainz_release_id")
            if track_obj.acoustid_id:
                updated_fields.append("acoustid")
            if track_obj.isrc:
                updated_fields.append("isrc")

            serialized = _serialize_task(task, detected_metadata=task.detected_metadata)
            return {
                "success": True,
                "status": "success",
                "match_found": True,
                "acoustid_match": bool(res.acoustid_id),
                "updated_fields": list(dict.fromkeys(updated_fields)),
                "metadata": serialized["detected_metadata"],
                "message": "Match found",
                "task": serialized,
                "data": serialized,
                "resolution_result": res.to_dict(),
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed acoustid lookup for review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AcoustID lookup failed")


@router.post("/{task_id}/lookup/musicbrainz")
def lookup_review_queue_item_musicbrainz(task_id: int, payload: MusicBrainzLookupRequest, _=Depends(require_auth)):
    """Run MusicBrainz text-waterfall lookup via the unified MetadataResolutionEngine."""
    payload_data = payload.metadata or payload.model_dump(exclude_unset=True)
    logger.debug(f"[MusicBrainz Route] POST request received for task_id={task_id}, payload={payload_data}")

    db = get_working_database()
    try:
        from sqlalchemy.orm.attributes import flag_modified

        from core.metadata.engine import MetadataResolutionEngine
        from core.metadata.schemas import ResolutionRequest

        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            current = _normalize_detected_metadata(task.detected_metadata) or {}
            artist = str(payload_data.get("artist") or current.get("artist") or "").strip()
            title = str(payload_data.get("title") or current.get("title") or "").strip()
            album = str(payload_data.get("album") or current.get("album") or "").strip()
            file_path = _resolve_task_file(task) or (Path(task.file_path) if task.file_path else Path("unknown.mp3"))

            if not artist and not title and not file_path.exists():
                raise HTTPException(status_code=400, detail="artist and title are required")

            track_obj = EchosyncTrack.from_dict(task.track_data or {})
            engine = MetadataResolutionEngine(
                acoustid_provider=_get_fingerprint_provider(),
                metadata_provider=_get_metadata_provider(),
                spotify_provider=_get_spotify_provider(),
            )
            req = ResolutionRequest(
                media_id=str(getattr(task, "media_id", None) or task.id),
                sync_id=track_obj.sync_id if hasattr(track_obj, "sync_id") else None,
                file_path=file_path,
                baseline_title=title or None,
                baseline_artist=artist or None,
                baseline_album=album or None,
                duration_ms=_coerce_int(track_obj.duration_ms),
                ignore_embedded_mbid=True,
                ignore_cache=True,
            )
            found_track = engine.resolve_track(req, enabled_stages=["text_waterfall"])

            if not found_track or found_track.confidence_score <= 0.0 or not (found_track.title or found_track.raw_title):
                serialized = _serialize_task(task)
                return {
                    "success": True,
                    "match_found": False,
                    "updated_fields": [],
                    "metadata": serialized["detected_metadata"],
                    "message": "No matching record found in database",
                    "task": serialized,
                }

            found_track = replace(
                found_track,
                identifiers={**(track_obj.identifiers or {}), **(found_track.identifiers or {}), "source": "musicbrainz_text_lookup"},
            )
            task.track_data = found_track.to_dict()
            flag_modified(task, "track_data")
            task.confidence_score = max(float(task.confidence_score or 0.0), float(found_track.confidence_score or 0.85))

            updated_fields = []
            if found_track.title or found_track.raw_title:
                updated_fields.append("title")
            if found_track.edition:
                updated_fields.append("edition")
            if found_track.artist_name:
                updated_fields.append("artist")
            if found_track.album_title:
                updated_fields.append("album")
            if found_track.release_year:
                updated_fields.append("year")
            if found_track.musicbrainz_id:
                updated_fields.append("musicbrainz_id")
            if found_track.isrc:
                updated_fields.append("isrc")
            if found_track.track_number:
                updated_fields.append("track_number")
            if found_track.disc_number:
                updated_fields.append("disc_number")

            serialized = _serialize_task(task)
            return {
                "success": True,
                "match_found": True,
                "updated_fields": list(dict.fromkeys(updated_fields)),
                "metadata": serialized["detected_metadata"],
                "message": "Match found",
                "task": serialized,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed musicbrainz lookup for review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="MusicBrainz lookup failed")


@router.post("/{task_id}/lookup/isrc")
def lookup_review_queue_item_isrc(task_id: int, payload: ISRCLookupRequest | None = None, _=Depends(require_auth)):
    """Run ISRC-based lookup via the unified MetadataResolutionEngine Stage 4."""
    payload_data = payload.model_dump(exclude_unset=True) if payload else {}
    isrc_code = str(payload_data.get("isrc") or "").strip()

    db = get_working_database()
    try:
        from sqlalchemy.orm.attributes import flag_modified

        from core.metadata.engine import MetadataResolutionEngine
        from core.metadata.schemas import ResolutionRequest
        from services.isrc_lookup_service import _normalise_isrc

        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            if not isrc_code:
                current = _normalize_detected_metadata(task.detected_metadata) or {}
                isrc_code = str(current.get("isrc") or (task.track_data or {}).get("isrc") or "").strip()

            if not isrc_code:
                raise HTTPException(status_code=400, detail="ISRC code is required")

            canonical = _normalise_isrc(isrc_code)
            if canonical is None:
                raise HTTPException(status_code=400, detail=f"Invalid ISRC format: {isrc_code}")

            track_obj = EchosyncTrack.from_dict(task.track_data or {})
            file_path = _resolve_task_file(task) or (Path(task.file_path) if task.file_path else Path("unknown.mp3"))

            engine = MetadataResolutionEngine(
                acoustid_provider=_get_fingerprint_provider(),
                metadata_provider=_get_metadata_provider(),
                spotify_provider=_get_spotify_provider(),
            )
            req = ResolutionRequest(
                media_id=str(getattr(task, "media_id", None) or task.id),
                sync_id=track_obj.sync_id if hasattr(track_obj, "sync_id") else None,
                file_path=file_path,
                baseline_title=track_obj.title or track_obj.raw_title,
                baseline_artist=track_obj.artist_name,
                baseline_album=track_obj.album_title,
                baseline_isrc=canonical,
                duration_ms=_coerce_int(track_obj.duration_ms),
                ignore_embedded_mbid=True,
                ignore_cache=True,
            )
            track = engine.resolve_track(req, enabled_stages=["isrc"])
            if not track or track.confidence_score <= 0.0 or not (track.title or track.raw_title):
                serialized = _serialize_task(task)
                return {
                    "success": True,
                    "match_found": False,
                    "updated_fields": [],
                    "metadata": None,
                    "message": "No matching record found across configured providers",
                    "task": serialized,
                }

            merged_track = replace(
                track,
                isrc=canonical,
                identifiers={**(track_obj.identifiers or {}), **(track.identifiers or {}), "source": "isrc_lookup"},
            )
            task.track_data = merged_track.to_dict()
            flag_modified(task, "track_data")
            task.confidence_score = max(float(task.confidence_score or 0.0), float(merged_track.confidence_score or 0.90))

            updated_fields = []
            if merged_track.title or merged_track.raw_title:
                updated_fields.append("title")
            if merged_track.edition:
                updated_fields.append("edition")
            if merged_track.artist_name:
                updated_fields.append("artist")
            if merged_track.album_title:
                updated_fields.append("album")
            if merged_track.release_year:
                updated_fields.append("year")
            if merged_track.musicbrainz_id:
                updated_fields.append("musicbrainz_id")
            if merged_track.isrc:
                updated_fields.append("isrc")
            if merged_track.duration_ms:
                updated_fields.append("duration")

            serialized = _serialize_task(task)
            src_label = (
                merged_track.identifiers.get("source")
                if hasattr(merged_track, "identifiers") and isinstance(merged_track.identifiers, dict)
                else None
            ) or "ISRC lookup"
            return {
                "success": True,
                "match_found": True,
                "updated_fields": list(dict.fromkeys(updated_fields)),
                "metadata": serialized["detected_metadata"],
                "message": f"Match found via {src_label}",
                "task": serialized,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed ISRC lookup for review task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="ISRC lookup failed")


@router.post("/{task_id}/simulate-pipeline")
@review_tasks_router.post("/{task_id}/simulate-pipeline")
def simulate_review_pipeline(task_id: int, _=Depends(require_auth)):
    """Run full read-only metadata resolution waterfall simulation with stage trace diagnostics."""
    db = get_working_database()
    try:
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            resolved_file = _resolve_task_file(task)
            if not resolved_file or not resolved_file.exists():
                raise HTTPException(status_code=404, detail=f"Physical file for task {task_id} not found on disk")

            # Extract current baseline tags
            current_meta = _read_current_metadata(task) or {}
            detected_meta = _normalize_detected_metadata(task.detected_metadata) or {}
            track_data = task.track_data if isinstance(task.track_data, dict) else {}

            from core.metadata.engine import extract_physical_tags

            raw_tags = extract_physical_tags(resolved_file) or {}

            # Duration extraction
            duration_sec = _normalize_duration_seconds(raw_tags, resolved_file)
            duration_ms = int(duration_sec * 1000) if duration_sec else 0
            if not duration_ms and raw_tags.get("duration_ms"):
                try:
                    duration_ms = int(raw_tags["duration_ms"])
                except Exception:
                    pass

            # Chromaprint & active duration extraction
            chromaprint = (
                raw_tags.get("chromaprint") or track_data.get("fingerprint") or detected_meta.get("chromaprint")
            )
            active_duration_ms = None
            if not chromaprint:
                try:
                    import echosync_core

                    res_fp = echosync_core.fingerprint_and_hash_audio(str(resolved_file), True)
                    if isinstance(res_fp, tuple) and len(res_fp) >= 1:
                        chromaprint = res_fp[0]
                        if len(res_fp) >= 2 and res_fp[1]:
                            active_duration_ms = int(round(float(res_fp[1]) * 1000))
                    elif isinstance(res_fp, str):
                        chromaprint = res_fp
                except Exception as fp_err:
                    logger.debug(f"Chromaprint extraction in simulation fallback: {fp_err}")

            baseline_title = (
                current_meta.get("title")
                or track_data.get("title")
                or detected_meta.get("title")
                or raw_tags.get("title")
            )
            baseline_artist = (
                current_meta.get("artist")
                or track_data.get("artist")
                or detected_meta.get("artist")
                or raw_tags.get("artist")
            )
            baseline_album = (
                current_meta.get("album")
                or track_data.get("album")
                or detected_meta.get("album")
                or raw_tags.get("album")
            )
            baseline_isrc = (
                current_meta.get("isrc") or track_data.get("isrc") or detected_meta.get("isrc") or raw_tags.get("isrc")
            )

            prefer_studio = bool(config_manager.get("metadata.prefer_canonical_studio_album", True))

            from core.metadata.engine import MetadataResolutionEngine
            from core.metadata.schemas import ResolutionRequest

            res_req = ResolutionRequest(
                media_id=str(getattr(task, "media_id", None) or task.id),
                file_path=resolved_file,
                baseline_title=baseline_title,
                baseline_artist=baseline_artist,
                baseline_album=baseline_album,
                baseline_isrc=baseline_isrc,
                chromaprint=chromaprint,
                duration_ms=duration_ms,
                prefer_studio_album=prefer_studio,
                ignore_cache=True,
                force_mode=True,
                force_recheck=True,
                dry_run=True,
            )

            engine = MetadataResolutionEngine()
            result = engine.resolve_track(res_req)

            resolved_metadata = {
                "title": result.title or result.raw_title,
                "artist": result.artist_name or result.artist,
                "album": result.album_title or result.album,
                "edition": result.edition,
                "year": result.release_year,
                "musicbrainz_id": result.musicbrainz_id,
                "isrc": result.isrc,
                "confidence_score": result.confidence_score,
                "duration_ms": duration_ms or None,
                "active_duration_ms": active_duration_ms,
            }

            return {
                "status": "success",
                "winning_stage": result.resolution_stage,
                "resolved_metadata": resolved_metadata,
                "diagnostics": result.diagnostics or [],
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed pipeline simulation for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline simulation failed: {str(e)}")


def _get_plugin(capability: Capability):
    """Get the first available plugin with the given capability."""
    return get_plugin_by_capability(capability)


def _extract_source_metadata(file_path: Path) -> dict[str, Any]:
    """Extract best-effort source metadata from local file tags/audio headers using echosync_core."""
    import echosync_core

    try:
        meta = echosync_core.extract_metadata(str(file_path))
        dur_ms = meta.get("duration_ms")
        return {
            "title": meta.get("title"),
            "artist": meta.get("artist_name") or meta.get("artist"),
            "album": meta.get("album_title") or meta.get("album"),
            "duration_seconds": (dur_ms // 1000) if dur_ms else None,
            "bitrate_kbps": meta.get("bitrate"),
            "sample_rate": meta.get("sample_rate"),
            "codec": meta.get("codec"),
            "source": "echosync_core",
        }
    except Exception as e:
        logger.warning(f"Failed to inspect file {file_path}: {e}")
        return {
            "title": None,
            "artist": None,
            "album": None,
            "duration_seconds": None,
            "bitrate_kbps": None,
            "sample_rate_hz": None,
            "channels": None,
            "file_format": file_path.suffix.lower().lstrip("."),
        }


@metadata_router.get("/queue", response_model=QueueListResponse)
@v1_metadata_router.get("/queue", response_model=QueueListResponse)
def get_queue():
    """Get items in the review queue."""
    try:
        db = get_working_database()
        queue = []
        with db.session_scope() as session:
            try:
                tasks = (
                    session.query(ReviewTask)
                    .filter(ReviewTask.status == "pending")
                    .all()
                )
            except Exception as e:
                if "no such table" in str(e).lower():
                    logger.info("Review tasks table not found, returning empty queue.")
                    return QueueListResponse(queue=[])
                raise e

            for task in tasks:
                media_path = _get_media_file_path(task.media_id) or getattr(task, "file_path", None) or ""
                queue.append(
                    QueueItemSchema(
                        id=task.id,
                        file_path=media_path,
                        filename=Path(media_path).name if media_path else "",
                        detected_metadata=task.detected_metadata,
                        confidence_score=task.confidence_score,
                        created_at=task.created_at.isoformat() if task.created_at else None,
                    )
                )
        return QueueListResponse(queue=queue)
    except Exception as e:
        logger.error(f"Error getting queue: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue: {e!s}")


@metadata_router.get("/queue/{task_id}", response_model=QueueDetailResponse)
@v1_metadata_router.get("/queue/{task_id}", response_model=QueueDetailResponse)
def get_queue_item(task_id: int):
    """Get full details for one review queue item, including source metadata."""
    try:
        db = get_working_database()
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task or task.status != "pending":
                raise HTTPException(status_code=404, detail="Task not found")

            media_path = _get_media_file_path(task.media_id) or getattr(task, "file_path", None) or ""
            file_path = Path(media_path) if media_path else Path("")
            source_metadata = (
                _extract_source_metadata(file_path)
                if media_path and file_path.exists()
                else None
            )

            item = QueueItemDetailSchema(
                id=task.id,
                file_path=media_path,
                filename=file_path.name if media_path else "",
                detected_metadata=task.detected_metadata,
                confidence_score=task.confidence_score,
                created_at=task.created_at.isoformat() if task.created_at else None,
                source_metadata=source_metadata,
                file_exists=file_path.exists() if media_path else False,
            )
            return QueueDetailResponse(item=item)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting queue item {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue item: {e!s}")


@metadata_router.get("/queue/{task_id}/audio")
@v1_metadata_router.get("/queue/{task_id}/audio")
def stream_queue_audio(task_id: int):
    """Stream audio file for a review queue item."""
    try:
        db = get_working_database()
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
            if not task or task.status != "pending":
                raise HTTPException(status_code=404, detail="Task not found")
            media_path = _get_media_file_path(task.media_id) or getattr(task, "file_path", None) or ""
            if not media_path:
                raise HTTPException(status_code=404, detail="Media path not found")
            file_path = Path(media_path)

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File no longer exists")

        guessed_type, _ = mimetypes.guess_type(str(file_path))
        return FileResponse(
            path=str(file_path), media_type=guessed_type or "application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming queue audio for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to stream audio")


@metadata_router.post("/queue/approve", response_model=SuccessResponse)
@v1_metadata_router.post("/queue/approve", response_model=SuccessResponse)
def approve_match(payload: ApproveMatchRequest):
    """Approve a match and process the file."""
    try:
        db = get_working_database()
        enhancer = get_metadata_enhancer()
        file_path = None

        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == payload.id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            media_path = _get_media_file_path(task.media_id) or getattr(task, "file_path", None) or ""
            if not media_path:
                raise HTTPException(status_code=404, detail="Media path not found")
            file_path = Path(media_path)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File no longer exists")

        try:
            enhancer.approve_match(file_path, payload.metadata)
        except Exception as e:
            logger.error(f"Approve failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        return SuccessResponse(success=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving match: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@metadata_router.post("/queue/manual-search")
@v1_metadata_router.post("/queue/manual-search")
def manual_search(payload: ManualSearchRequest):
    """Search for metadata manually."""
    try:
        provider = _get_plugin(Capability.FETCH_METADATA)
        if not provider:
            raise HTTPException(status_code=503, detail="No metadata provider available")

        results = provider.search_metadata(payload.query)
        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching metadata: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@metadata_router.delete("/queue/ignore", response_model=SuccessResponse)
@v1_metadata_router.delete("/queue/ignore", response_model=SuccessResponse)
def ignore_task(payload: IgnoreTaskRequest):
    """Ignore/Remove item from queue."""
    try:
        db = get_working_database()
        with db.session_scope() as session:
            task = session.query(ReviewTask).filter(ReviewTask.id == payload.id).first()
            if task:
                task.status = "ignored"
            else:
                raise HTTPException(status_code=404, detail="Task not found")

        return SuccessResponse(success=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ignoring task: {e}")
        raise HTTPException(status_code=500, detail="Failed to ignore task")


@metadata_router.get("/isrc/{isrc}")
@v1_metadata_router.get("/isrc/{isrc}")
def lookup_isrc(isrc: str):
    """Resolve track metadata from an ISRC code using a capability-based plugin lookup."""
    provider = get_plugin_by_capability(Capability.FETCH_BY_ISRC)
    if not provider:
        raise HTTPException(status_code=503, detail="No plugin available for ISRC lookups")

    try:
        from services.isrc_lookup_service import _normalise_isrc, _track_to_dict

        canonical = _normalise_isrc(isrc)
        if canonical is None:
            raise HTTPException(status_code=400, detail=f"Invalid ISRC format: {isrc}")

        track = provider.search_by_isrc(canonical)
        if not track:
            raise HTTPException(status_code=404, detail="Not found")

        if isinstance(track, EchosyncTrack):
            result = _track_to_dict(track, getattr(provider, "name", "plugin"))
        else:
            result = track

        return {
            "isrc": canonical,
            "result": result,
            "tried": [getattr(provider, "name", repr(provider))],
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "ISRC lookup error via plugin %s: %s",
            getattr(provider, "name", "plugin"),
            exc,
        )
        raise HTTPException(status_code=500, detail="ISRC lookup execution failed")


@metadata_router.get("/cover-art")
@v1_metadata_router.get("/cover-art")
def get_cover_art(path: str = Query(..., description="absolute path to audio file")):
    """Extract embedded cover art from an audio file."""
    try:
        candidate_roots = [
            config_manager.get("storage.library_dir"),
            config_manager.get("library_dir"),
            config_manager.get("download_dir"),
            config_manager.get("storage.download_dir"),
            config_manager.get("data_dir"),
            ".",
        ]
        allowed_roots = [
            os.path.abspath(os.path.realpath(str(r))) for r in candidate_roots if r
        ]

        target_abs = os.path.abspath(os.path.realpath(os.path.normpath(str(path))))
        matched_root = None
        for root_abs in allowed_roots:
            if target_abs.startswith(root_abs + os.sep) or target_abs == root_abs:
                matched_root = root_abs
                break

        if not matched_root:
            raise HTTPException(status_code=403, detail="Security violation: Access denied")

        if not os.path.isfile(target_abs):
            raise HTTPException(status_code=404, detail="File not found")

        parent_dir = os.path.dirname(target_abs)
        for name in ["cover.jpg", "folder.jpg", "cover.png", "folder.png"]:
            safe_name = os.path.basename(name)
            fallback = os.path.abspath(os.path.join(parent_dir, safe_name))
            if (fallback.startswith(matched_root + os.sep) or fallback == matched_root) and os.path.isfile(fallback):
                return FileResponse(path=fallback)

        raise HTTPException(status_code=404, detail="No cover art found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting cover art for {path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to extract cover art")
