from pathlib import Path
from typing import Any
from core.db.echo_sync_track import EchosyncTrack, EchosyncMedia
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.tiered_logger import get_logger

logger = get_logger("core.metadata.dsp")


def _tags_to_echosync_track(
    file_path: Path,
    raw_tags: dict[str, Any],
    duration_ms: int = 0,
    chromaprint: str | None = None,
) -> EchosyncTrack:
    tag_title = raw_tags.get("title")
    tag_artist = raw_tags.get("artist") or raw_tags.get("artist_name") or ""
    tag_album = raw_tags.get("album") or raw_tags.get("album_title") or ""
    raw_title = str(tag_title).strip() if tag_title else file_path.stem

    parsed_track_num: int | None = None
    tag_track = raw_tags.get("track_number") or raw_tags.get("tracknumber")
    if tag_track:
        try:
            parsed_track_num = int(str(tag_track).split("/")[0].strip())
        except (ValueError, TypeError):
            parsed_track_num = None

    parsed_disc_num: int | None = None
    tag_disc = raw_tags.get("disc_number") or raw_tags.get("discnumber")
    if tag_disc:
        try:
            parsed_disc_num = int(str(tag_disc).split("/")[0].strip())
        except (ValueError, TypeError):
            parsed_disc_num = None

    parsed_year: int | None = None
    tag_year = raw_tags.get("year") or raw_tags.get("date")
    if tag_year:
        try:
            parsed_year = int(str(tag_year)[:4])
        except (ValueError, TypeError):
            parsed_year = None

    if duration_ms <= 0:
        raw_dur = raw_tags.get("duration_ms")
        if raw_dur is not None:
            try:
                duration_ms = int(raw_dur)
            except (ValueError, TypeError):
                duration_ms = 0
        elif raw_tags.get("duration") is not None:
            try:
                d_sec = float(raw_tags["duration"])
                duration_ms = round(d_sec * 1000) if d_sec < 10000 else round(d_sec)
            except (ValueError, TypeError):
                duration_ms = 0

    mbid = (
        raw_tags.get("musicbrainz_id")
        or raw_tags.get("mbid")
        or raw_tags.get("recording_id")
        or raw_tags.get("musicbrainz_trackid")
    )
    mb_release_id = (
        raw_tags.get("musicbrainz_release_id") or raw_tags.get("musicbrainz_albumid") or raw_tags.get("release_mbid")
    )

    custom_tags: dict[str, str] = {}
    for k, v in raw_tags.items():
        if isinstance(v, (str, int, float, bool)):
            custom_tags[k] = str(v)

    track = EchosyncTrack(
        raw_title=raw_title,
        artist_name=str(tag_artist).strip() if tag_artist else "",
        album_title=str(tag_album).strip() if tag_album else "",
        duration=duration_ms if duration_ms > 0 else None,
        track_number=parsed_track_num,
        disc_number=parsed_disc_num,
        release_year=parsed_year,
        isrc=raw_tags.get("isrc"),
        musicbrainz_id=str(mbid).strip() if mbid else None,
        mb_release_id=str(mb_release_id).strip() if mb_release_id else None,
        acoustid_id=raw_tags.get("acoustid_id") or raw_tags.get("acoustid"),
        fingerprint=chromaprint,
        custom_tags=custom_tags,
        media=[
            EchosyncMedia(
                file_path=str(file_path),
            )
        ],
    )
    return track


def extract_physical_tags(file_path: Path) -> EchosyncTrack:
    """Extract raw physical header tags from audio file using Rust DSP, returning a baseline EchosyncTrack."""
    raw_tags: dict[str, Any] = {}
    try:
        import echosync_core

        raw_tags = echosync_core.extract_metadata(str(file_path)) or {}
    except Exception as exc:
        logger.debug("[dsp] Failed to extract header tags from %s: %s", file_path.name, exc)

    return _tags_to_echosync_track(file_path, raw_tags)


def probe_physical_audio(
    file_path: Path,
    channels: int = 2,
    duration_ms: int = 0,
    existing_chromaprint: str | None = None,
    log_prefix: str = "[resolution_engine]",
) -> EchosyncTrack:
    """Handles native Rust FFI calls, duration clamping, and channel gating.

    Returns an EchosyncTrack populated with baseline tags, duration, and chromaprint.
    """
    raw_tags: dict[str, Any] = {}
    try:
        import echosync_core

        raw_tags = echosync_core.extract_metadata(str(file_path)) or {}
    except Exception as exc:
        logger.debug("%s Failed to extract header tags from %s: %s", log_prefix, file_path.name, exc)

    # Determine channel count from tags if present
    try:
        raw_ch = raw_tags.get("channels")
        if raw_ch is not None:
            channels = int(raw_ch)
    except (ValueError, TypeError):
        pass

    # Extract duration from physical header if not already provided
    if duration_ms <= 0:
        raw_dur = raw_tags.get("duration_ms")
        if raw_dur is not None:
            try:
                duration_ms = int(raw_dur)
            except (ValueError, TypeError):
                duration_ms = 0
        elif raw_tags.get("duration") is not None:
            try:
                d_sec = float(raw_tags["duration"])
                duration_ms = round(d_sec * 1000) if d_sec < 10000 else round(d_sec)
            except (ValueError, TypeError):
                duration_ms = 0

    chromaprint = existing_chromaprint

    if chromaprint and len(chromaprint) > 4000:
        logger.warning(
            "%s Stale chromaprint detected (len=%d > 4000); "
            "invalidating and regenerating via clamped Rust DSP engine: %s",
            log_prefix,
            len(chromaprint),
            file_path.name,
        )
        chromaprint = None

    if not chromaprint:
        if channels > 2:
            logger.info(
                "%s Multi-channel audio (%d channels) for %s; skipping Chromaprint extraction.",
                log_prefix,
                channels,
                file_path.name,
            )
        else:
            try:
                import echosync_core

                res_fp = echosync_core.fingerprint_and_hash_audio(str(file_path), False)
                if isinstance(res_fp, tuple) and len(res_fp) >= 2:
                    chromaprint = res_fp[0]
                    if duration_ms <= 0 and res_fp[1]:
                        duration_ms = round(float(res_fp[1]) * 1000)
                elif isinstance(res_fp, str):
                    chromaprint = res_fp
            except Exception:
                try:
                    chromaprint, fp_dur = FingerprintGenerator.generate_with_duration(str(file_path))
                    if fp_dur and (duration_ms <= 0):
                        duration_ms = round(float(fp_dur) * 1000)
                except Exception as fp_err:
                    logger.warning(
                        "%s Fingerprint generation failed for %s: %s",
                        log_prefix,
                        file_path.name,
                        fp_err,
                    )
                    chromaprint = None

    track = _tags_to_echosync_track(file_path, raw_tags, duration_ms=duration_ms, chromaprint=chromaprint)
    if track.media:
        track.media[0].channels = channels
    else:
        track.media.append(EchosyncMedia(file_path=str(file_path), channels=channels))
    return track
