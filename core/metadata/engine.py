"""Authoritative Metadata Resolution Engine for EchoSync.

Unifies the 5-stage resolution waterfall:
1. Physical DSP (probe channel count > 2 to skip Chromaprint; extract duration + chromaprint)
2. Local Chromaprint Cache (short-circuit via music_library.db peer tracks with title trust gate)
3. AcoustID Resolution with Picard Disambiguation (filter/penalize remixes, boost studio albums, enforce ±2000ms duration window)
4. ISRC Resolution (provider-agnostic ISRC lookup if Stage 3 misses)
5. Scoped Text Waterfall (sanitized title prefix, strict recording: + artist: search, block artist-only discography leaks)
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any

from core.db.echo_sync_track import EchosyncTrack
from core.enums import Capability
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_EXACT_SYNC
from core.matching_engine.text_utils import normalize_title
from core.matching_engine.trust_gate import (
    clean_title_from_filename,
    is_cross_script,
    is_generic_title,
    sanitize_title_from_filename,
    should_bypass_filename_trust_gate,
    verify_title_trust_gate,
)
from core.metadata.schemas import (
    AliasResolutionContext,
    EntityAliasProposal,
    ResolutionRequest,
    ResolutionResult,
)
from core.nexus_framework.plugin_loader import PluginRegistry, generate_plugin_id
from core.tiered_logger import get_logger

logger = get_logger("core.metadata.engine")


def _extract_release_details(
    meta: Any,
    recording_id: str | None = None,
    fallback_year: int | None = None,
    fallback_track: int | None = None,
    fallback_disc: int | None = None,
) -> tuple[int | None, int | None, int | None]:
    """Extract (year, track_number, disc_number) from canonical release metadata."""
    if not meta:
        return fallback_year, fallback_track, fallback_disc

    if not isinstance(meta, dict):
        year = getattr(meta, "year", None) or getattr(meta, "release_year", None) or fallback_year
        track_num = getattr(meta, "track_number", None) or fallback_track
        disc_num = getattr(meta, "disc_number", None) or fallback_disc
        return year, track_num, disc_num

    # 1. Year Extraction
    extracted_year: int | None = None
    raw_year = (
        meta.get("year")
        or meta.get("canonical_year")
        or meta.get("date")
        or meta.get("first-release-date")
        or meta.get("first_release_date")
        or meta.get("release_date")
    )
    if raw_year:
        try:
            m = re.search(r"\b(19\d\d|20\d\d)\b", str(raw_year))
            if m:
                extracted_year = int(m.group(1))
            else:
                extracted_year = int(str(raw_year)[:4])
        except (ValueError, TypeError):
            extracted_year = None

    if extracted_year is None:
        extracted_year = fallback_year

    # 2. Track & Disc Number Extraction
    extracted_track: int | None = None
    extracted_disc: int | None = None

    raw_track = meta.get("track_number") or meta.get("track")
    if raw_track is not None:
        try:
            extracted_track = int(str(raw_track).split("/")[0].strip())
        except (ValueError, TypeError):
            extracted_track = None

    raw_disc = meta.get("disc_number") or meta.get("disc")
    if raw_disc is not None:
        try:
            extracted_disc = int(str(raw_disc).split("/")[0].strip())
        except (ValueError, TypeError):
            extracted_disc = None

    # If track or disc is missing, inspect nested releases and media
    if extracted_track is None or extracted_disc is None:
        rec_id = recording_id or meta.get("recording_id") or meta.get("id") or meta.get("musicbrainz_track_id")
        releases = meta.get("releases") or []
        target_rel_id = meta.get("release_id") or meta.get("musicbrainz_release_id")

        target_releases = [r for r in releases if isinstance(r, dict) and r.get("id") == target_rel_id]
        candidate_releases = target_releases if target_releases else [r for r in releases if isinstance(r, dict)]

        for rel in candidate_releases:
            if extracted_year is None and rel.get("date"):
                m = re.search(r"\b(19\d\d|20\d\d)\b", str(rel.get("date")))
                if m:
                    extracted_year = int(m.group(1))

            media = rel.get("media") or []
            for medium in media:
                if not isinstance(medium, dict):
                    continue
                med_pos = medium.get("position") or 1
                try:
                    disc_val = int(med_pos)
                except (ValueError, TypeError):
                    disc_val = 1

                for track in medium.get("tracks") or []:
                    if not isinstance(track, dict):
                        continue
                    t_rec = track.get("recording") or {}
                    t_rec_id = t_rec.get("id") if isinstance(t_rec, dict) else None
                    if rec_id and t_rec_id == rec_id:
                        raw_pos = track.get("number") or track.get("position")
                        try:
                            extracted_track = int(str(raw_pos).split("/")[0].strip())
                        except (ValueError, TypeError):
                            pass
                        extracted_disc = disc_val
                        break
                if extracted_track is not None:
                    break
            if extracted_track is not None:
                break

    final_track = extracted_track if extracted_track is not None else fallback_track
    final_disc = extracted_disc if extracted_disc is not None else fallback_disc

    return extracted_year, final_track, final_disc


def calculate_acoustid_duration_weight(track_duration: float, candidate_duration: float) -> float:
    delta = abs(track_duration - candidate_duration)
    if delta > 2.0:
        return 0.0
    # Progressive parabolic curve: 1.0 at 0s, 0.75 at 1s, 0.0 at 2s
    return max(0.0, 1.0 - (delta / 2.0) ** 2)


def calculate_text_duration_weight(track_duration: float, candidate_duration: float) -> float:
    delta = abs(track_duration - candidate_duration)
    if delta > 8.0:
        return 0.0
    return max(0.0, 1.0 - (delta / 8.0))


def extract_filename_title(file_path: str) -> str:
    """Derive a clean title string from a file path by stripping extension and leading
    disc/track-number prefixes.

    Examples:
        "01 - There's Nothing Holdin' Me Back.flac" -> "There's Nothing Holdin' Me Back"
        "02_Closer.mp3"                              -> "Closer"
        "cd1-03 Yellow.flac"                         -> "Yellow"
        "Track 07 - Hello.mp3"                       -> "Hello"
    """
    import os as _os

    base = _os.path.splitext(_os.path.basename(file_path))[0]
    # Strip leading disc/track number tokens: "01 - ", "02.", "cd1-03 ", "[07] ", "1_", etc.
    cleaned = re.sub(
        r"^(\d+[\-_]\d+|\d+|\[\d+\]|cd\d+[\-_]?\d*)[\s.\-_]+",
        "",
        base,
        flags=re.IGNORECASE,
    ).strip()
    return cleaned or base


class MetadataResolutionEngine:
    """Authoritative metadata resolution engine ensuring uniform behavior across

    Auto-Importer, Retroactive Enhancer, and Manual Review.
    """

    def __init__(
        self,
        acoustid_provider: Any | None = None,
        metadata_provider: Any | None = None,
        spotify_provider: Any | None = None,
        hook_manager: Any | None = None,
    ) -> None:
        self._acoustid_provider = acoustid_provider
        self._metadata_provider = metadata_provider
        self._spotify_provider = spotify_provider
        self._hook_manager = hook_manager
        self._chromaprint_cache: dict[str, dict[str, Any]] = {}
        self.matcher = WeightedMatchingEngine(PROFILE_EXACT_SYNC)

    def invalidate_cache(self, chromaprint: str | None = None) -> None:
        """Invalidate in-memory chromaprint cache entry or entire cache."""
        if chromaprint:
            self._chromaprint_cache.pop(chromaprint, None)
        else:
            self._chromaprint_cache.clear()

    @property
    def hook_manager(self) -> Any:
        if self._hook_manager is not None:
            return self._hook_manager
        from core.hook_manager import hook_manager

        return hook_manager

    def _get_acoustid_plugin(self) -> Any | None:
        if self._acoustid_provider is not None:
            return self._acoustid_provider

        # Check by plugin id / alias
        plugin = (
            PluginRegistry.get_plugin(generate_plugin_id("EchoSync.acoustid"))
            or PluginRegistry.get_plugin("EchoSync.acoustid")
            or PluginRegistry.get_plugin("acoustid")
        )
        if plugin:
            return plugin

        # Check by capability
        plugins = PluginRegistry.get_plugins_with_capability(Capability.RESOLVE_FINGERPRINT)
        for p in plugins:
            caps = getattr(p, "capabilities", None)
            if caps:
                algos = getattr(caps, "fingerprint_algorithms", []) or []
                if "chromaprint" in algos or getattr(caps, "supports_fingerprinting", False):
                    return p
        return plugins[0] if plugins else None

    def _get_mb_plugin(self) -> Any | None:
        if self._metadata_provider is not None:
            return self._metadata_provider

        # Check by plugin id / alias
        plugin = (
            PluginRegistry.get_plugin(generate_plugin_id("EchoSync.musicbrainz"))
            or PluginRegistry.get_plugin("EchoSync.musicbrainz")
            or PluginRegistry.get_plugin("musicbrainz")
        )
        if plugin:
            return plugin

        # Fallback to general metadata capability
        plugins = PluginRegistry.get_plugins_with_capability(Capability.FETCH_METADATA)
        return plugins[0] if plugins else None

    def score_candidate(
        self,
        candidate: dict[str, Any],
        baseline_title: str,
        file_duration_ms: int,
        baseline_artist: str | None = None,
        baseline_album: str | None = None,
        filename: str | None = None,
    ) -> float:
        """Score AcoustID recording candidate by duration proximity, variant disambiguation penalties,
        and canonical studio release weighting using WeightedMatchingEngine(PROFILE_EXACT_SYNC).
        """
        cand_dur = candidate.get("length") or candidate.get("duration_ms") or candidate.get("duration")
        cand_dur_ms: int | None = None
        duration_weight = 1.0
        delta_sec = 0.0
        if cand_dur:
            try:
                cand_dur_val = float(cand_dur)
                if 0 < cand_dur_val < 10000:
                    cand_dur_val *= 1000.0
                cand_dur_ms = int(cand_dur_val)
                if file_duration_ms > 0:
                    track_dur_sec = file_duration_ms / 1000.0
                    cand_dur_sec = cand_dur_ms / 1000.0
                    delta_sec = abs(track_dur_sec - cand_dur_sec)
                    duration_weight = calculate_acoustid_duration_weight(track_dur_sec, cand_dur_sec)
                    if duration_weight <= 0.0 or delta_sec > 2.0:
                        return 0.0  # Hard AcoustID duration gate (reject delta > 2.0s)
            except (ValueError, TypeError):
                pass

        c_title = str(candidate.get("title") or "")
        c_artist = str(candidate.get("artist") or candidate.get("artist_name") or "")
        c_album = str(candidate.get("album") or candidate.get("album_title") or "")

        clean_file_title = clean_title_from_filename(filename) if filename else ""
        query_title = (
            clean_file_title if (clean_file_title and not is_generic_title(clean_file_title)) else baseline_title
        )

        query_track = EchosyncTrack(
            raw_title=query_title or c_title,
            artist_name=baseline_artist or c_artist,
            album_title=baseline_album or c_album,
            duration=file_duration_ms if file_duration_ms > 0 else None,
        )
        cand_track = EchosyncTrack(
            raw_title=c_title,
            artist_name=c_artist,
            album_title=c_album,
            duration=cand_dur_ms,
            version=candidate.get("disambiguation") or candidate.get("version"),
        )
        match_res = self.matcher.calculate_match(query_track, cand_track)
        matcher_score = match_res.confidence_score if match_res else 0.0

        # Preference for canonical studio release groups
        release_group = candidate.get("release_group") or candidate.get("release-group") or {}
        if not release_group and candidate.get("releases"):
            for r in candidate.get("releases") or []:
                if isinstance(r, dict):
                    rg = r.get("release-group") or r.get("release_group") or {}
                    if rg.get("primary_type") == "Album" or rg.get("primary-type") == "Album":
                        release_group = rg
                        break

        p_type = release_group.get("primary_type") or release_group.get("primary-type")
        album_bonus = 5.0 if p_type == "Album" else 0.0

        # Base physical acoustic evidence grants high confidence when tags are corrupted
        base_score = matcher_score if matcher_score > 0.0 else 80.0
        score = base_score + album_bonus

        # Progressive Duration Multiplier:
        # If delta <= 1.0s, duration weight yields maximum weight (dominates candidate ranking
        # and preserves canonical release group advantages).
        # Beyond 1.0s, steep progressive parabolic decay applies.
        if delta_sec <= 1.0:
            score = score * (0.95 + 0.05 * duration_weight)
        else:
            score = score * duration_weight

        return max(score, 0.0)

    def resolve_track(
        self,
        request: ResolutionRequest,
        enabled_stages: list[str] | None = None,
    ) -> ResolutionResult:
        """Resolve track metadata through the authoritative 6-stage resolution waterfall.

        When ``enabled_stages`` is provided, only the listed stages are executed.
        Currently supports ``["acoustid"]`` for strict manual fingerprint lookups that
        must not leak into ISRC or text-waterfall fallback stages.
        """
        # ── Acoustid-only isolated path ────────────────────────────────────────
        if enabled_stages and enabled_stages == ["acoustid"]:
            return self._resolve_acoustid_isolated(request)

        # ── Standard full waterfall ────────────────────────────────────────────
        result = self._execute_waterfall(request)

        # ── Stage 6: Entity Alias Resolution ──────────────────────────────────
        result.alias_proposals = self._resolve_aliases(request, result)
        return result

    def _resolve_acoustid_isolated(self, request: ResolutionRequest) -> ResolutionResult:
        """Execute Stage 3 (AcoustID) in strict isolation.

        Performs the minimum physical inspection required to obtain a chromaprint and
        duration, then calls AcoustID directly.  If no match is found the method returns
        a zero-confidence stub with the generated fingerprint preserved so the caller
        can save it and present a 'submit to AcoustID' option without corrupting metadata.

        Stages that are intentionally skipped:
          Stage 0 — ECHOSYNC_SIGNATURE verification
          Fast-path — Embedded MBID lookup
          Stage 2 — Local chromaprint cache
          Stage 4 — ISRC resolution
          Stage 5 — Scoped text waterfall
        """
        file_path = Path(request.file_path)

        # ── Minimal physical inspection ────────────────────────────────────────
        raw_tags: dict[str, Any] = {}
        try:
            import echosync_core

            raw_tags = echosync_core.extract_metadata(str(file_path)) or {}
        except Exception as exc:
            logger.debug(
                "[resolution_engine] [acoustid-isolated] Tag extraction failed for %s: %s",
                file_path.name,
                exc,
            )

        # Duration from header tags or fingerprint generator
        duration_ms = 0
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

        # Channel check: skip fingerprinting for multi-channel audio
        channels = 2
        try:
            raw_ch = raw_tags.get("channels")
            if raw_ch is not None:
                channels = int(raw_ch)
        except (ValueError, TypeError):
            channels = 2

        if request.duration_ms and duration_ms <= 0:
            duration_ms = request.duration_ms
        elif request.duration and duration_ms <= 0:
            d_val = float(request.duration)
            duration_ms = round(d_val * 1000) if d_val < 10000 else round(d_val)

        chromaprint: str | None = request.chromaprint
        if not chromaprint:
            if channels > 2:
                logger.info(
                    "[resolution_engine] [acoustid-isolated] Multi-channel audio (%d ch) on %s; skipping Chromaprint.",
                    channels,
                    file_path.name,
                )
            else:
                try:
                    chromaprint, fp_dur = FingerprintGenerator.generate_with_duration(str(file_path))
                    if fp_dur and duration_ms <= 0:
                        duration_ms = round(float(fp_dur) * 1000)
                    if chromaprint:
                        request.chromaprint = chromaprint
                except Exception as fp_err:
                    logger.warning(
                        "[resolution_engine] [acoustid-isolated] Fingerprint generation failed for %s: %s",
                        file_path.name,
                        fp_err,
                    )

        # ── Stage 3: AcoustID (isolated) ─────────────────────────────────────
        acoustid_res: dict[str, Any] | None = None
        if chromaprint and duration_ms > 0:
            logger.info(
                "[resolution_engine] [acoustid-isolated] Running Stage 3 for %s (fingerprint_len=%d, duration_ms=%d)",
                file_path.name,
                len(chromaprint),
                duration_ms,
            )
            baseline_title = request.baseline_title or ""
            baseline_artist = request.baseline_artist or ""
            baseline_album = request.baseline_album or ""
            tag_title = raw_tags.get("title")
            acoustid_res = self._resolve_acoustid(
                chromaprint=chromaprint,
                file_duration_ms=duration_ms,
                baseline_title=baseline_title,
                filename=file_path.name,
                tag_title=tag_title,
                baseline_artist=baseline_artist or None,
                baseline_album=baseline_album or None,
                request=request,
            )

        # ── Result assembly ────────────────────────────────────────────────────
        if acoustid_res and acoustid_res.get("candidate_score", 0.0) >= 60.0:
            logger.info(
                "[resolution_engine] [acoustid-isolated] HIT: %s → MBID %s (score=%.1f)",
                file_path.name,
                acoustid_res["musicbrainz_track_id"],
                acoustid_res["candidate_score"],
            )
            tag_isrc = raw_tags.get("isrc") or request.baseline_isrc
            return ResolutionResult(
                media_id=request.media_id,
                sync_id=request.sync_id,
                title=acoustid_res["title"],
                artist=acoustid_res["artist"],
                album=acoustid_res.get("album") or baseline_album,
                year=acoustid_res.get("year"),
                track_number=acoustid_res.get("track_number"),
                disc_number=acoustid_res.get("disc_number"),
                musicbrainz_track_id=acoustid_res["musicbrainz_track_id"],
                musicbrainz_release_id=acoustid_res.get("musicbrainz_release_id"),
                acoustid_id=acoustid_res.get("acoustid_id"),
                chromaprint=chromaprint,
                duration_ms=duration_ms,
                isrc=acoustid_res.get("isrc") or tag_isrc,
                confidence_score=0.95,
                resolution_method="acoustid",
            )

        # ── Zero-confidence stub: preserve fingerprint, no metadata contamination ─
        logger.warning(
            "[resolution_engine] [acoustid-isolated] MISS for %s — no AcoustID match "
            "(chromaprint_len=%s, duration_ms=%d). Returning stub.",
            file_path.name,
            len(chromaprint) if chromaprint else "None",
            duration_ms,
        )
        return ResolutionResult(
            media_id=request.media_id,
            sync_id=request.sync_id,
            title="",
            artist="",
            chromaprint=chromaprint,
            duration_ms=duration_ms,
            confidence_score=0.0,
            resolution_method="acoustid",
        )

    def _resolve_aliases(self, request: ResolutionRequest, result: ResolutionResult) -> list[EntityAliasProposal]:
        """Stage 6: Query active language packs and plugins for entity alias proposals."""
        if not result.sync_id and request.sync_id:
            result.sync_id = request.sync_id

        if not result.sync_id:
            return []

        artist_mbids: list[str] = []
        if getattr(result, "musicbrainz_artist_id", None):
            artist_mbids.append(result.musicbrainz_artist_id)
        if result.extra_metadata and "artist_mbid" in result.extra_metadata:
            mb = result.extra_metadata["artist_mbid"]
            if mb and mb not in artist_mbids:
                artist_mbids.append(mb)

        context = AliasResolutionContext(
            sync_id=result.sync_id,
            media_id=result.media_id,
            title=result.title,
            artist=result.artist,
            album=result.album,
            musicbrainz_track_id=result.musicbrainz_track_id,
            artist_mbids=artist_mbids,
            track_artist_ids=getattr(result, "track_artist_ids", []) or [],
        )

        try:
            hook_results = self.hook_manager.execute_hook("resolve_entity_aliases", context)
            valid_proposals: list[EntityAliasProposal] = []
            for prop in hook_results:
                try:
                    if isinstance(prop, EntityAliasProposal):
                        valid_proposals.append(prop)
                    elif isinstance(prop, dict):
                        valid_proposals.append(EntityAliasProposal(**prop))
                    else:
                        logger.warning(
                            "[metadata_engine] Dropping invalid alias proposal type: %s",
                            type(prop),
                        )
                except Exception as item_err:
                    logger.warning(
                        "[metadata_engine] Dropping malformed alias proposal: %s (%s)",
                        prop,
                        item_err,
                    )
            return valid_proposals
        except Exception as e:
            logger.warning(f"[metadata_engine] Error resolving entity aliases for sync_id={result.sync_id}: {e}")
            return []

    def _execute_waterfall(self, request: ResolutionRequest) -> ResolutionResult:
        """Execute stages 1-5 of the resolution waterfall."""
        file_path = Path(request.file_path)

        # ── Stage 1: Physical Inspection ──────────────────────────────────────
        raw_tags: dict[str, Any] = {}
        try:
            import echosync_core

            raw_tags = echosync_core.extract_metadata(str(file_path)) or {}
        except Exception as exc:
            logger.debug(
                "[resolution_engine] Failed to extract header tags from %s: %s",
                file_path.name,
                exc,
            )

        if not file_path.exists() and not raw_tags and not request.baseline_title:
            logger.warning(
                "[resolution_engine] File not found on disk and no metadata: %s",
                request.file_path,
            )
            return ResolutionResult(
                media_id=request.media_id,
                sync_id=request.sync_id,
                title=request.baseline_title or file_path.stem,
                artist=request.baseline_artist or "Unknown Artist",
                album=request.baseline_album,
                confidence_score=0.0,
                resolution_method="text_waterfall",
            )

        # Determine channel count: probe header tags or assume stereo
        channels = 2
        try:
            raw_ch = raw_tags.get("channels")
            if raw_ch is not None:
                channels = int(raw_ch)
        except (ValueError, TypeError):
            channels = 2

        # Extract duration from physical header if present
        duration_ms = 0
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

        if request.duration_ms and duration_ms <= 0:
            duration_ms = request.duration_ms
        elif request.duration and duration_ms <= 0:
            d_val = float(request.duration)
            duration_ms = round(d_val * 1000) if d_val < 10000 else round(d_val)

        # Invariant: Multi-channel audio (>2 channels) must skip fingerprinting until native downmixing
        chromaprint: str | None = request.chromaprint
        if not chromaprint:
            if channels > 2:
                logger.info(
                    "[resolution_engine] Multi-channel audio detected (%d channels) for %s; skipping Chromaprint extraction.",
                    channels,
                    file_path.name,
                )
            else:
                try:
                    chromaprint, fp_dur = FingerprintGenerator.generate_with_duration(str(file_path))
                    if fp_dur and (duration_ms <= 0):
                        duration_ms = round(float(fp_dur) * 1000)
                    if chromaprint:
                        request.chromaprint = chromaprint
                except Exception as fp_err:
                    logger.warning(
                        "[resolution_engine] Fingerprint generation failed for %s: %s",
                        file_path.name,
                        fp_err,
                    )
                    chromaprint = None

        tag_title = raw_tags.get("title")
        tag_artist = raw_tags.get("artist") or raw_tags.get("artist_name")
        tag_album = raw_tags.get("album") or raw_tags.get("album_title")
        tag_isrc = raw_tags.get("isrc") or request.baseline_isrc
        tag_track_num = raw_tags.get("track_number") or raw_tags.get("tracknumber")
        tag_disc_num = raw_tags.get("disc_number") or raw_tags.get("discnumber")
        tag_year = raw_tags.get("year") or raw_tags.get("date")

        parsed_track_num: int | None = None
        if tag_track_num:
            try:
                parsed_track_num = int(str(tag_track_num).split("/")[0].strip())
            except (ValueError, TypeError):
                parsed_track_num = None

        parsed_disc_num: int | None = None
        if tag_disc_num:
            try:
                parsed_disc_num = int(str(tag_disc_num).split("/")[0].strip())
            except (ValueError, TypeError):
                parsed_disc_num = None

        parsed_year: int | None = None
        if tag_year:
            try:
                parsed_year = int(str(tag_year)[:4])
            except (ValueError, TypeError):
                parsed_year = None

        # Determine effective baseline text
        baseline_title = (
            request.baseline_title
            or (str(tag_title).strip() if tag_title else None)
            or sanitize_title_from_filename(file_path.name)
        )
        baseline_artist = request.baseline_artist or (str(tag_artist).strip() if tag_artist else None) or ""
        baseline_album = request.baseline_album or (str(tag_album).strip() if tag_album else None) or ""

        # Extract clean title directly from physical filename
        sanitized_file_title = clean_title_from_filename(file_path.name)
        filename_is_identifiable = bool(sanitized_file_title and not is_generic_title(sanitized_file_title))

        # Check if physical filename stem contradicts the requested baseline_title
        filename_contradicts_baseline = False
        if (
            filename_is_identifiable
            and request.baseline_title
            and not is_cross_script(request.baseline_title, sanitized_file_title)
        ):
            base_file_sim = difflib.SequenceMatcher(
                None,
                request.baseline_title.lower().strip(),
                sanitized_file_title.lower().strip(),
            ).ratio()
            if base_file_sim < 0.60:
                filename_contradicts_baseline = True

        # ── Stage 0: Zero-Trust Signature Gate (ECHOSYNC_SIGNATURE) ───────────
        sig_tag = raw_tags.get("echosync_signature") or raw_tags.get("ECHOSYNC_SIGNATURE")
        if sig_tag and not request.ignore_cache and baseline_title and baseline_artist:
            try:
                import echosync_core

                if hasattr(echosync_core, "verify_audio_signature"):
                    if echosync_core.verify_audio_signature(
                        str(file_path), baseline_title, baseline_artist, str(sig_tag).strip()
                    ):
                        logger.info(
                            "[resolution_engine] Stage 0 HIT (Verified ECHOSYNC_SIGNATURE): %s",
                            file_path.name,
                        )
                        return ResolutionResult(
                            media_id=request.media_id,
                            sync_id=request.sync_id,
                            title=baseline_title,
                            artist=baseline_artist,
                            album=baseline_album or None,
                            year=parsed_year,
                            track_number=parsed_track_num,
                            disc_number=parsed_disc_num,
                            musicbrainz_track_id=raw_tags.get("musicbrainz_track_id")
                            or raw_tags.get("musicbrainz_id")
                            or raw_tags.get("mbid")
                            or raw_tags.get("recording_id"),
                            musicbrainz_release_id=raw_tags.get("musicbrainz_album_id")
                            or raw_tags.get("musicbrainz_release_id"),
                            acoustid_id=raw_tags.get("acoustid_id"),
                            chromaprint=chromaprint,
                            duration_ms=duration_ms,
                            isrc=tag_isrc,
                            confidence_score=1.0,
                            resolution_method="signature_verified",
                        )
                    else:
                        logger.warning(
                            "[resolution_engine] Stage 0 FAILED: ECHOSYNC_SIGNATURE mismatch/tampering detected on %s",
                            file_path.name,
                        )
            except Exception as sig_err:
                logger.debug(
                    "[resolution_engine] Stage 0 signature verification error: %s",
                    sig_err,
                )

        # ── Fast-Path: Embedded MusicBrainz ID in Tags ─────────────────────────
        embedded_mbid = (
            raw_tags.get("musicbrainz_id")
            or raw_tags.get("mbid")
            or raw_tags.get("recording_id")
            or raw_tags.get("musicbrainz_trackid")
        )
        has_identifiable_tags = bool(
            (tag_title and not is_generic_title(str(tag_title)))
            and (tag_artist and not str(tag_artist).lower().strip().startswith("unknown"))
        )
        if embedded_mbid and not request.ignore_embedded_mbid:
            if not has_identifiable_tags:
                logger.info(
                    "[resolution_engine] Skipping embedded MBID %s (tags missing/unknown); dropping straight to Chromaprint/AcoustID",
                    embedded_mbid,
                )
            else:
                mb_plugin = self._get_mb_plugin()
                if mb_plugin and hasattr(mb_plugin, "get_metadata"):
                    try:
                        meta = mb_plugin.get_metadata(str(embedded_mbid).strip())
                        if meta:
                            c_title = meta.get("title") if isinstance(meta, dict) else getattr(meta, "title", None)
                            baseline_check = request.baseline_title or baseline_title

                            contradicts_filename = False
                            if c_title and filename_contradicts_baseline:
                                sim = difflib.SequenceMatcher(
                                    None,
                                    str(c_title).lower().strip(),
                                    sanitized_file_title.lower().strip(),
                                ).ratio()
                                if sim < 0.60:
                                    contradicts_filename = True
                                    logger.warning(
                                        f"[resolution_engine] Candidate '{c_title}' contradicts physical filename "
                                        f"'{sanitized_file_title}' (similarity={sim:.2f}). Rejecting embedded hit."
                                    )

                            if (
                                not c_title
                                or contradicts_filename
                                or not verify_title_trust_gate(
                                    candidate_title=c_title,
                                    baseline_title=baseline_check,
                                    filename=file_path.name,
                                    tag_title=tag_title,
                                    min_similarity=0.60,
                                )
                            ):
                                logger.warning(
                                    f"[resolution_engine] Embedded MBID {embedded_mbid} rejected by Trust Gate "
                                    f"(Candidate: '{c_title or ''}' vs Baseline: '{request.baseline_title}'). "
                                    "Falling through to AcoustID."
                                )
                            else:
                                c_artist = (
                                    (meta.get("artist") or meta.get("artist_name"))
                                    if isinstance(meta, dict)
                                    else (getattr(meta, "artist_name", None) or getattr(meta, "artist", None))
                                )
                                c_album = (
                                    (meta.get("album") or meta.get("album_title"))
                                    if isinstance(meta, dict)
                                    else (getattr(meta, "album_title", None) or getattr(meta, "album", None))
                                )
                                c_rel_id = (
                                    meta.get("release_id")
                                    if isinstance(meta, dict)
                                    else getattr(meta, "mb_release_id", None)
                                )
                                c_year, c_track, c_disc = _extract_release_details(
                                    meta,
                                    recording_id=str(embedded_mbid).strip(),
                                    fallback_year=parsed_year,
                                    fallback_track=parsed_track_num,
                                    fallback_disc=parsed_disc_num,
                                )
                                logger.info(
                                    "[resolution_engine] Embedded MBID fast-path verified: %s → %s",
                                    file_path.name,
                                    embedded_mbid,
                                )
                                return ResolutionResult(
                                    media_id=request.media_id,
                                    sync_id=request.sync_id,
                                    title=c_title or baseline_title,
                                    artist=c_artist or baseline_artist,
                                    album=c_album or baseline_album,
                                    year=c_year,
                                    track_number=c_track,
                                    disc_number=c_disc,
                                    musicbrainz_track_id=str(embedded_mbid).strip(),
                                    musicbrainz_release_id=c_rel_id,
                                    acoustid_id=raw_tags.get("acoustid_id"),
                                    chromaprint=chromaprint,
                                    duration_ms=duration_ms,
                                    isrc=tag_isrc,
                                    confidence_score=0.99,
                                    resolution_method="embedded_mbid",
                                )
                    except Exception as e_mb:
                        logger.debug("[resolution_engine] Embedded MBID lookup failed: %s", e_mb)

        # ── Stage 2: Local Chromaprint Cache ──────────────────────────────────
        if chromaprint and not request.ignore_cache:
            cached_meta = self._check_local_chromaprint_cache(chromaprint, sync_id=request.sync_id)
            if cached_meta:
                cand_title = cached_meta.get("title")

                contradicts_filename = False
                if cand_title and filename_contradicts_baseline:
                    sim = difflib.SequenceMatcher(
                        None,
                        str(cand_title).lower().strip(),
                        sanitized_file_title.lower().strip(),
                    ).ratio()
                    if sim < 0.60:
                        contradicts_filename = True
                        logger.warning(
                            f"[resolution_engine] Candidate '{cand_title}' contradicts physical filename "
                            f"'{sanitized_file_title}' (similarity={sim:.2f}). Rejecting cached hit and invalidating cache."
                        )
                        self.invalidate_cache(chromaprint)

                if (
                    cand_title
                    and not contradicts_filename
                    and verify_title_trust_gate(
                        candidate_title=cand_title,
                        baseline_title=request.baseline_title or baseline_title,
                        filename=file_path.name,
                        tag_title=tag_title,
                        min_similarity=0.60,
                    )
                ):
                    logger.info(
                        "[resolution_engine] Stage 2 HIT (local chromaprint cache): %s → MBID %s",
                        file_path.name,
                        cached_meta.get("musicbrainz_id"),
                    )
                    c_year, c_track, c_disc = _extract_release_details(
                        cached_meta,
                        recording_id=cached_meta.get("musicbrainz_id") or cached_meta.get("musicbrainz_track_id"),
                        fallback_year=parsed_year,
                        fallback_track=parsed_track_num,
                        fallback_disc=parsed_disc_num,
                    )
                    return ResolutionResult(
                        media_id=request.media_id,
                        sync_id=request.sync_id,
                        title=cached_meta.get("title") or baseline_title,
                        artist=cached_meta.get("artist") or baseline_artist,
                        album=cached_meta.get("album") or baseline_album,
                        year=c_year,
                        track_number=c_track,
                        disc_number=c_disc,
                        musicbrainz_track_id=cached_meta.get("musicbrainz_id")
                        or cached_meta.get("musicbrainz_track_id"),
                        musicbrainz_release_id=cached_meta.get("release_mbid")
                        or cached_meta.get("musicbrainz_release_id"),
                        acoustid_id=cached_meta.get("acoustid_id"),
                        chromaprint=chromaprint,
                        duration_ms=cached_meta.get("duration_ms") or duration_ms,
                        isrc=cached_meta.get("isrc") or tag_isrc,
                        confidence_score=0.95,
                        resolution_method="local_cache",
                    )

        # ── Stage 3: AcoustID Resolution with Picard Disambiguation ───────────
        if chromaprint and duration_ms > 0:
            acoustid_res = self._resolve_acoustid(
                chromaprint=chromaprint,
                file_duration_ms=duration_ms,
                baseline_title=baseline_title,
                filename=file_path.name,
                tag_title=tag_title,
                baseline_artist=baseline_artist,
                baseline_album=baseline_album,
                request=request,
                has_signature=bool(sig_tag),
                has_identifiable_tags=has_identifiable_tags,
            )
            if acoustid_res:
                # Rule B: Check for signed file divergence
                if bool(sig_tag):
                    cand_t = str(acoustid_res.get("title") or "").strip().lower()
                    base_t = str(baseline_title or "").strip().lower()
                    title_sim = difflib.SequenceMatcher(None, base_t, cand_t).ratio() if base_t and cand_t else 1.0
                    if title_sim < 0.85:
                        logger.warning(
                            "[resolution_engine] Signed file %s diverged from AcoustID candidate "
                            "('%s' vs '%s', sim=%.2f). Staging ReviewTask and preserving signed tags.",
                            file_path.name,
                            baseline_title,
                            acoustid_res.get("title"),
                            title_sim,
                        )
                        try:
                            from database.repositories.task_repository import TaskRepository

                            TaskRepository.create_review_task(
                                file_path=str(file_path),
                                action="RESOLVE_METADATA_CONFLICT",
                                track_id=request.media_id,
                                confidence_score=0.95,
                                track_data={
                                    "action": "RESOLVE_METADATA_CONFLICT",
                                    "reason": "SIGNED_METADATA_DIVERGENCE",
                                    "current_title": baseline_title,
                                    "current_artist": baseline_artist,
                                    "current_album": baseline_album,
                                    "proposed_title": acoustid_res.get("title"),
                                    "proposed_artist": acoustid_res.get("artist"),
                                    "proposed_album": acoustid_res.get("album"),
                                    "musicbrainz_track_id": acoustid_res.get("musicbrainz_track_id"),
                                    "acoustid_id": acoustid_res.get("acoustid_id"),
                                },
                            )
                        except Exception as e_task:
                            logger.warning(
                                "[resolution_engine] Failed to stage signed metadata divergence: %s",
                                e_task,
                            )

                        return ResolutionResult(
                            media_id=request.media_id,
                            sync_id=request.sync_id,
                            title=baseline_title,
                            artist=baseline_artist,
                            album=baseline_album or None,
                            year=parsed_year,
                            track_number=parsed_track_num,
                            disc_number=parsed_disc_num,
                            musicbrainz_track_id=raw_tags.get("musicbrainz_track_id")
                            or raw_tags.get("musicbrainz_id")
                            or raw_tags.get("mbid")
                            or raw_tags.get("recording_id"),
                            musicbrainz_release_id=raw_tags.get("musicbrainz_album_id")
                            or raw_tags.get("musicbrainz_release_id"),
                            acoustid_id=raw_tags.get("acoustid_id"),
                            chromaprint=chromaprint,
                            duration_ms=duration_ms,
                            isrc=tag_isrc,
                            confidence_score=1.0,
                            resolution_method="signature_verified",
                        )

            if acoustid_res:
                logger.info(
                    "[resolution_engine] Stage 3 HIT (AcoustID): %s → MBID %s (score: %.1f, veto=%s)",
                    file_path.name,
                    acoustid_res["musicbrainz_track_id"],
                    acoustid_res["candidate_score"],
                    acoustid_res.get("veto_applied", False),
                )
                return ResolutionResult(
                    media_id=request.media_id,
                    sync_id=request.sync_id,
                    title=acoustid_res["title"],
                    artist=acoustid_res["artist"],
                    album=acoustid_res.get("album") or baseline_album,
                    year=acoustid_res.get("year") if acoustid_res.get("year") is not None else parsed_year,
                    track_number=acoustid_res.get("track_number")
                    if acoustid_res.get("track_number") is not None
                    else parsed_track_num,
                    disc_number=acoustid_res.get("disc_number")
                    if acoustid_res.get("disc_number") is not None
                    else parsed_disc_num,
                    musicbrainz_track_id=acoustid_res["musicbrainz_track_id"],
                    musicbrainz_release_id=acoustid_res.get("musicbrainz_release_id"),
                    acoustid_id=acoustid_res.get("acoustid_id"),
                    chromaprint=chromaprint,
                    duration_ms=duration_ms,
                    isrc=acoustid_res.get("isrc") or tag_isrc,
                    confidence_score=0.95,
                    resolution_method="acoustid",
                )

        # ── Stage 4: ISRC Resolution ──────────────────────────────────────────
        if tag_isrc:
            isrc_res = self._resolve_isrc(
                isrc=tag_isrc,
                baseline_title=baseline_title,
                filename=file_path.name,
                tag_title=tag_title,
            )
            if isrc_res:
                logger.info(
                    "[resolution_engine] Stage 4 HIT (ISRC): %s → %s",
                    file_path.name,
                    tag_isrc,
                )
                return ResolutionResult(
                    media_id=request.media_id,
                    sync_id=request.sync_id,
                    title=isrc_res["title"],
                    artist=isrc_res["artist"],
                    album=isrc_res.get("album") or baseline_album,
                    year=isrc_res.get("year") or parsed_year,
                    track_number=isrc_res.get("track_number") or parsed_track_num,
                    disc_number=isrc_res.get("disc_number") or parsed_disc_num,
                    musicbrainz_track_id=isrc_res.get("musicbrainz_track_id"),
                    musicbrainz_release_id=isrc_res.get("musicbrainz_release_id"),
                    acoustid_id=None,
                    chromaprint=chromaprint,
                    duration_ms=isrc_res.get("duration_ms") or duration_ms,
                    isrc=tag_isrc,
                    confidence_score=0.92,
                    resolution_method="isrc",
                )

        # ── Stage 5: Scoped Text Waterfall ────────────────────────────────────
        text_res = self._resolve_text_waterfall(
            baseline_title=baseline_title,
            baseline_artist=baseline_artist,
            baseline_album=baseline_album,
            file_duration_ms=duration_ms,
            filename=file_path.name,
            tag_title=tag_title,
            baseline_isrc=tag_isrc or request.baseline_isrc,
        )
        if text_res:
            logger.info(
                "[resolution_engine] Stage 5 HIT (Scoped Text Waterfall): %s → MBID %s (confidence: %.2f)",
                file_path.name,
                text_res.get("musicbrainz_track_id"),
                text_res["confidence_score"],
            )
            return ResolutionResult(
                media_id=request.media_id,
                sync_id=request.sync_id,
                title=text_res["title"],
                artist=text_res["artist"],
                album=text_res.get("album") or baseline_album,
                year=text_res.get("year") or parsed_year,
                track_number=text_res.get("track_number") or parsed_track_num,
                disc_number=text_res.get("disc_number") or parsed_disc_num,
                musicbrainz_track_id=text_res.get("musicbrainz_track_id"),
                musicbrainz_release_id=text_res.get("musicbrainz_release_id"),
                acoustid_id=None,
                chromaprint=chromaprint,
                duration_ms=duration_ms,
                isrc=text_res.get("isrc") or tag_isrc,
                confidence_score=text_res["confidence_score"],
                resolution_method="text_waterfall",
            )

        # ── Unresolved Fallback ───────────────────────────────────────────────
        logger.info(
            "[resolution_engine] All resolution stages exhausted for %s. Marking for manual review.",
            file_path.name,
        )
        return ResolutionResult(
            media_id=request.media_id,
            sync_id=request.sync_id,
            title=baseline_title or file_path.stem,
            artist=baseline_artist or "Unknown Artist",
            album=baseline_album or None,
            year=parsed_year,
            track_number=parsed_track_num,
            disc_number=parsed_disc_num,
            musicbrainz_track_id=None,
            musicbrainz_release_id=None,
            acoustid_id=None,
            chromaprint=chromaprint,
            duration_ms=duration_ms,
            isrc=tag_isrc,
            confidence_score=0.0,
            resolution_method="text_waterfall",
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _check_local_chromaprint_cache(self, chromaprint: str, sync_id: str | None = None) -> dict[str, Any] | None:
        """Inspect in-memory cache and query music_library.db for peer tracks sharing the chromaprint."""
        if not chromaprint or len(chromaprint.strip()) < 50:
            return None

        if chromaprint in self._chromaprint_cache:
            return self._chromaprint_cache[chromaprint]

        try:
            from database.music_database import (
                AudioFingerprint,
                LocalMedia,
                Track,
                get_database,
            )

            db = get_database()
            with db.session_scope() as session:
                query = (
                    session.query(Track)
                    .join(LocalMedia, LocalMedia.track_id == Track.id)
                    .join(
                        AudioFingerprint,
                        AudioFingerprint.media_id == LocalMedia.media_id,
                    )
                    .filter(
                        AudioFingerprint.chromaprint == chromaprint,
                        Track.musicbrainz_id.isnot(None),
                        Track.musicbrainz_id != "",
                        Track.musicbrainz_id != "NOT_FOUND",
                        Track.title.isnot(None),
                        Track.title != "",
                    )
                )
                if sync_id:
                    query = query.filter(Track.sync_id != sync_id)

                peer_track = query.first()
                if not peer_track:
                    return None

                artist_name = peer_track.artist.name if peer_track.artist else None
                album_title = peer_track.album.title if peer_track.album else None
                release_mbid = peer_track.album.mb_release_id if peer_track.album else None

                res = {
                    "title": peer_track.title,
                    "artist": artist_name,
                    "album": album_title,
                    "year": peer_track.year,
                    "isrc": peer_track.isrc,
                    "musicbrainz_id": peer_track.musicbrainz_id,
                    "musicbrainz_track_id": peer_track.musicbrainz_id,
                    "release_mbid": release_mbid,
                    "track_number": peer_track.track_number,
                    "disc_number": peer_track.disc_number,
                    "duration_ms": peer_track.duration,
                }
                self._chromaprint_cache[chromaprint] = res
                return res
        except Exception as exc:
            logger.debug("[resolution_engine] Local chromaprint DB lookup failed: %s", exc)
            return None

    def _resolve_acoustid(
        self,
        chromaprint: str | None = None,
        file_duration_ms: int = 0,
        baseline_title: str = "",
        filename: str = "",
        tag_title: str | None = None,
        baseline_artist: str | None = None,
        baseline_album: str | None = None,
        request: ResolutionRequest | None = None,
        has_signature: bool = False,
        has_identifiable_tags: bool = False,
    ) -> dict[str, Any] | None:
        """Query AcoustID, pre-filter candidate recordings before network egress, and pick
        the highest scoring candidate using filename-first zero-trust title semantics.

        Stage 3 invariant: candidate title is compared against the physical filename stem,
        never against baseline_title (which may reflect corrupted embedded tags).
        """
        # ── Engine version signature ──────────────────────────────────────────
        logger.info("[resolution_engine] v2.4-filename-priority active")

        acoustid_plugin = self._get_acoustid_plugin()
        mb_plugin = self._get_mb_plugin()
        if not acoustid_plugin or not mb_plugin:
            return None

        if request is not None:
            if request.chromaprint:
                chromaprint = request.chromaprint
            elif not chromaprint and request.file_path:
                try:
                    chromaprint, fp_dur = FingerprintGenerator.generate_with_duration(str(request.file_path))
                    if fp_dur and file_duration_ms <= 0:
                        file_duration_ms = round(float(fp_dur) * 1000)
                    if chromaprint:
                        request.chromaprint = chromaprint
                except Exception as fp_err:
                    logger.warning("[resolution_engine] Fingerprint generation failed in _resolve_acoustid: %s", fp_err)

            if not filename and request.file_path:
                filename = Path(request.file_path).name
            if not baseline_title and request.baseline_title:
                baseline_title = request.baseline_title
            if not baseline_artist and request.baseline_artist:
                baseline_artist = request.baseline_artist
            if not baseline_album and request.baseline_album:
                baseline_album = request.baseline_album
            if request.duration_ms and file_duration_ms <= 0:
                file_duration_ms = request.duration_ms
            elif request.duration and file_duration_ms <= 0:
                d_val = float(request.duration)
                file_duration_ms = round(d_val * 1000) if d_val < 10000 else round(d_val)

        if not chromaprint:
            return None

        # Derive zero-trust title target from physical filename (ignores embedded tags)
        filename_stem = extract_filename_title(filename) if filename else ""
        logger.info(
            "[resolution_engine] Stage 3 target title derived from filename: '%s'",
            filename_stem,
        )

        file_duration_sec = file_duration_ms / 1000.0 if file_duration_ms > 0 else 0.0
        duration_sec = round(file_duration_sec)

        try:
            try:
                details = acoustid_plugin.resolve_fingerprint_details(fingerprint=chromaprint, duration=duration_sec)
            except TypeError:
                details = acoustid_plugin.resolve_fingerprint_details(chromaprint, duration_sec)
            if not isinstance(details, dict):
                return None
            acoustid_id = details.get("acoustid_id")
            recordings = details.get("recordings") or []
            candidate_mbids = details.get("mbids") or []
            if not recordings and not candidate_mbids:
                return None

            # Build enriched recording map keyed by MBID for O(1) lookup
            rec_by_mbid: dict[str, dict[str, Any]] = {}
            for r in recordings:
                if isinstance(r, dict) and r.get("id"):
                    rec_by_mbid[str(r["id"]).strip()] = r

            # Collect all unique MBIDs (enriched recordings take priority)
            seen_mbids: set[str] = set()
            ordered_mbids: list[str] = []
            for r_id in rec_by_mbid:
                if r_id not in seen_mbids:
                    seen_mbids.add(r_id)
                    ordered_mbids.append(r_id)
            for mbid in candidate_mbids:
                mbid_s = str(mbid).strip()
                if mbid_s and mbid_s not in seen_mbids:
                    seen_mbids.add(mbid_s)
                    ordered_mbids.append(mbid_s)

            # ── Pre-network In-Memory Filtering & Ranking ─────────────────────
            # Fast in-memory filtering against AcoustID candidate metadata:
            # 1. Hard duration gate (<= 2.0s cutoff)
            # 2. Artist token overlap check
            # 3. Filename stem title similarity (prune < 0.40, rank by title + duration)
            has_identifiable_filename = bool(filename_stem and not is_generic_title(filename_stem))
            fn_lower = filename_stem.lower().strip() if has_identifiable_filename else ""
            norm_fn = normalize_title(fn_lower) if fn_lower else ""
            fn_tokens = {w for w in re.findall(r"\w+", fn_lower) if len(w) > 2} if fn_lower else set()

            logger.info(
                "[resolution_engine] Filtering %d AcoustID candidate(s) against filename stem: '%s'",
                len(ordered_mbids),
                filename_stem or "(none)",
            )

            viable_candidates: list[tuple[str, float, float, float]] = []  # (mbid, rank_score, dur_delta, title_sim)

            for mbid_str in ordered_mbids:
                if not mbid_str:
                    continue

                rec_meta = rec_by_mbid.get(mbid_str) or {}

                # Step A: Hard duration gate (pre-network, in seconds)
                cand_dur_raw = rec_meta.get("duration")
                if cand_dur_raw is not None:
                    try:
                        cand_dur_sec = float(cand_dur_raw)
                        # AcoustID durations are in seconds; guard against ms-scale values
                        if cand_dur_sec > 10000:
                            cand_dur_sec /= 1000.0
                        dur_delta_sec = abs(cand_dur_sec - file_duration_sec)
                        if dur_delta_sec > 2.0:
                            logger.debug(
                                "[resolution_engine] Step A DROPPED MBID %s: "
                                "duration delta %.2fs > 2.0s (candidate=%.1fs, file=%.1fs)",
                                mbid_str,
                                dur_delta_sec,
                                cand_dur_sec,
                                file_duration_sec,
                            )
                            continue
                    except (ValueError, TypeError):
                        dur_delta_sec = 0.0  # Unknown duration — pass through
                else:
                    dur_delta_sec = 0.0  # Unknown duration — pass through

                # Candidate AcoustID match score (normalized 0.0 - 1.0)
                raw_score_val = rec_meta.get("score") if rec_meta.get("score") is not None else details.get("score")
                if raw_score_val is None:
                    cand_acoustid_score = 0.0
                else:
                    try:
                        raw_score = float(raw_score_val)
                        cand_acoustid_score = raw_score / 100.0 if raw_score > 1.0 else raw_score
                    except (ValueError, TypeError):
                        cand_acoustid_score = 0.0

                # Veto authority evaluation (Rule A / B)
                veto_applies = should_bypass_filename_trust_gate(
                    acoustid_score=cand_acoustid_score,
                    duration_delta_sec=dur_delta_sec,
                    has_signature=has_signature,
                    has_identifiable_tags=has_identifiable_tags,
                )

                # Step B: Artist token filter (pre-network)
                # Skip filter if baseline_artist is missing, empty, or generic, OR if veto_applies
                cand_artist = rec_meta.get("artist") or ""
                b_art = str(baseline_artist).lower().strip() if baseline_artist else ""
                generic_artists = {
                    "unknown",
                    "unknown artist",
                    "various artists",
                    "va",
                    "various",
                    "soundtrack",
                    "ost",
                    "various artist",
                }
                if (
                    not veto_applies
                    and cand_artist
                    and b_art
                    and b_art not in generic_artists
                    and not is_generic_title(b_art)
                ):
                    c_art = cand_artist.lower().strip()
                    overlap = (
                        c_art in b_art
                        or b_art in c_art
                        or bool(
                            {w for w in re.findall(r"\w+", b_art) if len(w) > 2}
                            & {w for w in re.findall(r"\w+", c_art) if len(w) > 2}
                        )
                        or difflib.SequenceMatcher(None, b_art, c_art).ratio() >= 0.50
                    )
                    if not overlap:
                        logger.debug(
                            "[resolution_engine] Step B DROPPED MBID %s: artist '%s' disjoint from baseline '%s'",
                            mbid_str,
                            cand_artist,
                            baseline_artist,
                        )
                        continue

                # Step C: Fast in-memory title check against filename stem
                cand_title = str(rec_meta.get("title") or "").strip()
                if cand_title and has_identifiable_filename:
                    c_lower = cand_title.lower().strip()
                    sim = difflib.SequenceMatcher(None, fn_lower, c_lower).ratio()
                    norm_c = normalize_title(c_lower)
                    if norm_fn and norm_c:
                        sim = max(sim, difflib.SequenceMatcher(None, norm_fn, norm_c).ratio())
                    c_tokens = {w for w in re.findall(r"\w+", c_lower) if len(w) > 2}
                    if fn_tokens and c_tokens:
                        common_tokens = fn_tokens & c_tokens
                        if not common_tokens:
                            # Disjoint titles sharing no significant words:
                            # If acoustic match has veto authority, give 0.65 floor.
                            if veto_applies:
                                sim = max(sim, 0.65)
                            elif cand_acoustid_score >= 0.95 and dur_delta_sec <= 1.0:
                                sim = max(sim, 0.65)
                            else:
                                sim = min(sim, 0.15)
                        else:
                            token_overlap = len(common_tokens) / max(len(fn_tokens), len(c_tokens))
                            sim = max(sim, token_overlap)
                            if veto_applies:
                                sim = max(sim, 0.65)
                    elif veto_applies:
                        sim = max(sim, 0.65)

                    # Pruning Rule: Discard any candidate where title similarity < 0.35 unless veto applies
                    if sim < 0.35 and not veto_applies:
                        logger.debug(
                            "[resolution_engine] Title pre-filter DROPPED MBID %s '%s': "
                            "title similarity %.2f < 0.35 against filename '%s'",
                            mbid_str,
                            cand_title,
                            sim,
                            filename_stem,
                        )
                        continue

                elif veto_applies:
                    sim = 0.65
                else:
                    sim = 0.50  # Neutral similarity for untagged candidates or generic filenames

                # Ranking score: 80% title similarity + 20% AcoustID cluster score
                pre_rank_score = (sim * 0.8) + (cand_acoustid_score * 0.2)

                viable_candidates.append(
                    (mbid_str, pre_rank_score, dur_delta_sec, sim, cand_acoustid_score, veto_applies)
                )

            # Exit immediately if no candidates match
            if not viable_candidates:
                logger.info(
                    "[resolution_engine] No AcoustID candidate matched filename '%s' with >= 0.35 similarity. "
                    "Skipping MusicBrainz network calls.",
                    filename_stem or "(none)",
                )
                return None

            # Sort descending by composite pre_rank_score
            viable_candidates.sort(key=lambda x: x[1], reverse=True)

            # Cap at top 2 viable candidates for MusicBrainz detail lookup
            top_candidates = viable_candidates[:2]
            top_mbids = [item[0] for item in top_candidates]

            logger.info(
                "[resolution_engine] Stage 3: %d candidate(s) passed pre-network filters; "
                "querying MusicBrainz for top %d: %s",
                len(viable_candidates),
                len(top_mbids),
                top_mbids,
            )

            # ── Step C: MusicBrainz Detail Lookup ─────────────────────────────
            # ── Step D: Filename-First Candidate Scoring via WeightedMatchingEngine ─
            best_candidate: dict[str, Any] | None = None
            best_mbid: str | None = None
            best_score = 0.0
            best_veto_applied = False
            best_acoustid_score = 0.0
            best_dur_delta = 0.0

            for cand_info in top_candidates:
                mbid_str = cand_info[0]
                cand_sim = cand_info[3]
                cand_acoustid_score = cand_info[4]
                veto_applies = cand_info[5]
                cand_meta = mb_plugin.get_metadata(mbid_str)
                if not isinstance(cand_meta, dict):
                    continue

                # Step D: Secondary duration gate on the detailed MB metadata
                mb_dur_raw = cand_meta.get("length") or cand_meta.get("duration_ms") or cand_meta.get("duration")
                mb_dur_sec: float | None = None
                if mb_dur_raw is not None:
                    try:
                        mb_dur_val = float(mb_dur_raw)
                        # Normalize: MB `length` is in ms, raw AcoustID duration in seconds
                        if 0 < mb_dur_val < 10000:
                            mb_dur_val *= 1000.0  # seconds → ms
                        mb_dur_sec = mb_dur_val / 1000.0
                        if abs(mb_dur_sec - file_duration_sec) > 2.0:
                            logger.debug(
                                "[resolution_engine] Step D DROPPED MBID %s: MB duration delta %.2fs > 2.0s",
                                mbid_str,
                                abs(mb_dur_sec - file_duration_sec),
                            )
                            continue
                    except (ValueError, TypeError):
                        mb_dur_sec = None

                # Build query track using filename_stem — baseline_title is explicitly ignored
                c_title = str(cand_meta.get("title") or "")
                c_artist = str(cand_meta.get("artist") or cand_meta.get("artist_name") or "")
                c_album = str(cand_meta.get("album") or cand_meta.get("album_title") or "")
                cand_dur_ms = int(mb_dur_sec * 1000) if mb_dur_sec is not None else None

                # Build query track: when veto applies, acoustic candidate title provides
                # ground truth without passing raw unsanitized file stems into matcher
                query_title = c_title if veto_applies else (filename_stem or c_title)
                query_track = EchosyncTrack(
                    raw_title=query_title,
                    artist_name=baseline_artist or c_artist,
                    album_title=baseline_album or c_album,
                    duration=file_duration_ms if file_duration_ms > 0 else None,
                )
                cand_track = EchosyncTrack(
                    raw_title=c_title,
                    artist_name=c_artist,
                    album_title=c_album,
                    duration=cand_dur_ms,
                    version=cand_meta.get("disambiguation") or cand_meta.get("version"),
                )
                match_res = self.matcher.calculate_match(query_track, cand_track)
                matcher_score = match_res.confidence_score if match_res else 0.0

                # Album type bonus for canonical studio releases
                release_group = cand_meta.get("release_group") or cand_meta.get("release-group") or {}
                if not release_group and cand_meta.get("releases"):
                    for r in cand_meta.get("releases") or []:
                        if isinstance(r, dict):
                            rg = r.get("release-group") or r.get("release_group") or {}
                            if rg.get("primary_type") == "Album" or rg.get("primary-type") == "Album":
                                release_group = rg
                                break
                p_type = release_group.get("primary_type") or release_group.get("primary-type")
                album_bonus = 5.0 if p_type == "Album" else 0.0

                # Duration proximity weight (parabolic)
                if cand_dur_ms is not None and file_duration_ms > 0:
                    dur_weight = calculate_acoustid_duration_weight(file_duration_sec, cand_dur_ms / 1000.0)
                else:
                    dur_weight = 1.0  # Unknown duration — no penalty

                # Final score: candidate scoring combines matcher score (70%), duration weight (30%), and album bonus
                cand_score = (matcher_score * 0.7) + (dur_weight * 30.0) + album_bonus
                if veto_applies:
                    cand_sim = max(cand_sim, 0.65)

                logger.debug(
                    "[resolution_engine] Stage 3 candidate MBID %s '%s': "
                    "matcher=%.1f dur_weight=%.3f album_bonus=%.1f veto=%s => score=%.2f",
                    mbid_str,
                    c_title,
                    matcher_score,
                    dur_weight,
                    album_bonus,
                    veto_applies,
                    cand_score,
                )

                if cand_score > 0 and cand_score > best_score:
                    best_score = cand_score
                    best_candidate = cand_meta
                    best_mbid = mbid_str
                    best_veto_applied = veto_applies
                    best_acoustid_score = cand_acoustid_score
                    best_dur_delta = dur_delta_sec

                # Short-circuit on clear filename match to enforce HTTP request cap (<= 1 on clear match)
                if matcher_score >= 80.0 and cand_sim >= 0.60:
                    logger.info(
                        "[resolution_engine] Clear filename match confirmed for MBID %s '%s' "
                        "(matcher=%.1f, score=%.1f, sim=%.2f). Terminating candidate inspection.",
                        mbid_str,
                        c_title,
                        matcher_score,
                        cand_score,
                        cand_sim,
                    )
                    break

            if best_candidate and best_mbid:
                cand_year, cand_track, cand_disc = _extract_release_details(
                    best_candidate,
                    recording_id=best_mbid,
                )
                logger.info(
                    "[resolution_engine] Stage 3 WINNER MBID %s '%s' (score=%.2f, veto=%s, filename_stem='%s')",
                    best_mbid,
                    best_candidate.get("title"),
                    best_score,
                    best_veto_applied,
                    filename_stem,
                )
                return {
                    "title": best_candidate.get("title") or baseline_title,
                    "artist": best_candidate.get("artist") or best_candidate.get("artist_name") or "",
                    "album": best_candidate.get("album") or best_candidate.get("album_title") or "",
                    "year": cand_year,
                    "track_number": cand_track,
                    "disc_number": cand_disc,
                    "musicbrainz_track_id": best_mbid,
                    "musicbrainz_release_id": best_candidate.get("release_id") or best_candidate.get("mb_release_id"),
                    "acoustid_id": acoustid_id,
                    "isrc": best_candidate.get("isrc"),
                    "candidate_score": best_score,
                    "acoustid_score": best_acoustid_score,
                    "duration_delta_sec": best_dur_delta,
                    "veto_applied": best_veto_applied,
                }
        except Exception as exc:
            logger.warning("[resolution_engine] AcoustID resolution error: %s", exc)

        return None

    def _resolve_isrc(
        self,
        isrc: str,
        baseline_title: str,
        filename: str,
        tag_title: str | None,
    ) -> dict[str, Any] | None:
        """Query ISRC resolution via dispatch_isrc_lookup."""
        try:
            from services.isrc_lookup_service import dispatch_isrc_lookup

            isrc_track = dispatch_isrc_lookup(str(isrc).strip())
            if not isrc_track:
                return None

            cand_title = isrc_track.title
            if cand_title and not verify_title_trust_gate(
                candidate_title=cand_title,
                baseline_title=baseline_title,
                filename=filename,
                tag_title=tag_title,
                min_similarity=0.60,
            ):
                logger.warning(
                    "[resolution_engine] Trust Gate REJECTED ISRC candidate '%s' vs baseline '%s'",
                    cand_title,
                    baseline_title,
                )
                return None

            mbid = (
                isrc_track.identifiers.get("musicbrainz_id")
                if isinstance(isrc_track.identifiers, dict)
                else getattr(isrc_track, "musicbrainz_id", None)
            )
            rel_id = (
                isrc_track.identifiers.get("musicbrainz_release_group_id")
                if isinstance(isrc_track.identifiers, dict)
                else None
            )

            return {
                "title": isrc_track.title,
                "artist": isrc_track.artist_name,
                "album": isrc_track.album_title,
                "year": isrc_track.release_year,
                "track_number": isrc_track.track_number,
                "disc_number": isrc_track.disc_number,
                "musicbrainz_track_id": mbid,
                "musicbrainz_release_id": rel_id,
                "duration_ms": isrc_track.duration,
            }
        except Exception as exc:
            logger.warning("[resolution_engine] ISRC resolution error: %s", exc)
            return None

    def _resolve_text_waterfall(
        self,
        baseline_title: str,
        baseline_artist: str,
        baseline_album: str,
        file_duration_ms: int,
        filename: str,
        tag_title: str | None,
        baseline_isrc: str | None = None,
    ) -> dict[str, Any] | None:
        """Scoped text search waterfall with prefix sanitization and strict recording: + artist: matching.

        Blocks artist-only discography leaks ([] fallback).
        """
        if not baseline_title or not baseline_artist:
            return None

        # Sanitize track prefixes (e.g., "01 - Title", "01. Title")
        sanitized_title = re.sub(r"^(?:(?:\d{1,2}[.-])?\d{1,3}[\s\-_.]{1,3}\s*)+", "", str(baseline_title)).strip()
        if not sanitized_title:
            sanitized_title = baseline_title

        mb_client = self._get_mb_plugin()
        if not mb_client:
            return None

        query_track = EchosyncTrack(
            raw_title=sanitized_title,
            artist_name=baseline_artist,
            album_title=baseline_album,
            duration=file_duration_ms if file_duration_ms > 0 else None,
        )

        try:
            # Strict query via MusicBrainzClient
            results = mb_client.search_metadata(query_track, limit=5) if hasattr(mb_client, "search_metadata") else None
            if not results:
                # Block artist-only discography leaks
                return None

            results_list = results if isinstance(results, (list, tuple)) else [results]
            candidate_tracks = []
            for item in results_list:
                cand_t = None
                mbid = None
                if isinstance(item, EchosyncTrack):
                    cand_t = item
                    mbid = item.musicbrainz_id
                    if not mbid and isinstance(item.identifiers, dict):
                        mbid = item.identifiers.get("musicbrainz_recording_id") or item.identifiers.get("mbid")
                elif isinstance(item, dict):
                    mbid = item.get("recording_id") or item.get("mbid")
                    cand_t = EchosyncTrack(
                        raw_title=item.get("title") or "",
                        artist_name=item.get("artist") or item.get("artist_name") or "",
                        album_title=item.get("album") or item.get("album_title") or "",
                        musicbrainz_id=mbid,
                    )
                if cand_t and mbid:
                    candidate_tracks.append((cand_t, mbid))

            if not candidate_tracks:
                return None

            matcher = self.matcher
            best_score = 0.0
            best_cand = None
            best_mbid = None

            for cand, mbid in candidate_tracks:
                cand_title = cand.title or cand.raw_title
                if not verify_title_trust_gate(
                    candidate_title=cand_title,
                    baseline_title=baseline_title,
                    filename=filename,
                    tag_title=tag_title,
                    min_similarity=0.60,
                ):
                    continue

                # Stage 5 MusicBrainz Text Waterfall Duration Decay Curve
                text_dur_weight = 1.0
                if file_duration_ms > 0 and cand.duration:
                    try:
                        cand_dur_val = float(cand.duration)
                        cand_dur_sec = cand_dur_val / 1000.0 if cand_dur_val > 1000 else cand_dur_val
                        track_dur_sec = file_duration_ms / 1000.0
                        text_dur_weight = calculate_text_duration_weight(track_dur_sec, cand_dur_sec)
                        if text_dur_weight <= 0.0:
                            # Complete failure threshold: delta > 8.0s -> 0.0
                            continue
                    except (ValueError, TypeError):
                        pass

                match_res = matcher.calculate_match(query_track, cand)
                score = match_res.confidence_score if match_res else 0.0
                score = score * text_dur_weight
                if score > best_score:
                    best_score = score
                    best_cand = cand
                    best_mbid = mbid

            if best_score >= 85.0 and best_mbid and best_cand:
                # Retrieve canonical recording metadata if available
                meta = None
                try:
                    meta = mb_client.get_metadata(best_mbid)
                except Exception as meta_err:
                    logger.debug("[resolution_engine] Metadata fetch failed for %s: %s", best_mbid, meta_err)

                final_title = (
                    (meta.get("title") if isinstance(meta, dict) else getattr(meta, "title", None))
                    or best_cand.title
                    or sanitized_title
                )
                final_artist = (
                    (
                        (meta.get("artist") or meta.get("artist_name"))
                        if isinstance(meta, dict)
                        else (getattr(meta, "artist_name", None) or getattr(meta, "artist", None))
                    )
                    or best_cand.artist_name
                    or baseline_artist
                )
                final_album = (
                    (
                        (meta.get("album") or meta.get("album_title"))
                        if isinstance(meta, dict)
                        else (getattr(meta, "album_title", None) or getattr(meta, "album", None))
                    )
                    or best_cand.album_title
                    or baseline_album
                )
                final_release_id = (
                    meta.get("release_id") if isinstance(meta, dict) else getattr(meta, "mb_release_id", None)
                )

                final_year, final_track, final_disc = _extract_release_details(
                    meta,
                    recording_id=best_mbid,
                    fallback_year=getattr(best_cand, "release_year", None),
                    fallback_track=getattr(best_cand, "track_number", None),
                    fallback_disc=getattr(best_cand, "disc_number", None),
                )

                final_isrc = (
                    (meta.get("isrc") if isinstance(meta, dict) else getattr(meta, "isrc", None))
                    or getattr(best_cand, "isrc", None)
                    or baseline_isrc
                )

                return {
                    "title": final_title,
                    "artist": final_artist,
                    "album": final_album,
                    "year": final_year,
                    "track_number": final_track,
                    "disc_number": final_disc,
                    "musicbrainz_track_id": best_mbid,
                    "musicbrainz_release_id": final_release_id,
                    "isrc": final_isrc,
                    "confidence_score": best_score / 100.0,
                }
        except Exception as exc:
            logger.warning("[resolution_engine] Scoped text waterfall error: %s", exc)

        return None
