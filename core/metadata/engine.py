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
from core.matching_engine.trust_gate import (
    clean_title_from_filename,
    is_cross_script,
    is_generic_title,
    sanitize_title_from_filename,
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
        year = (
            getattr(meta, "year", None)
            or getattr(meta, "release_year", None)
            or fallback_year
        )
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
        rec_id = (
            recording_id
            or meta.get("recording_id")
            or meta.get("id")
            or meta.get("musicbrainz_track_id")
        )
        releases = meta.get("releases") or []
        target_rel_id = meta.get("release_id") or meta.get("musicbrainz_release_id")

        target_releases = [
            r for r in releases if isinstance(r, dict) and r.get("id") == target_rel_id
        ]
        candidate_releases = (
            target_releases if target_releases else [r for r in releases if isinstance(r, dict)]
        )

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


class MetadataResolutionEngine:
    """Authoritative metadata resolution engine ensuring uniform behavior across

    Auto-Importer, Retroactive Enhancer, and Manual Review.
    """

    def __init__(
        self,
        acoustid_provider: Any | None = None,
        metadata_provider: Any | None = None,
        hook_manager: Any | None = None,
    ) -> None:
        self._acoustid_provider = acoustid_provider
        self._metadata_provider = metadata_provider
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

        # Check by plugin id
        plugin = PluginRegistry.get_plugin(generate_plugin_id("EchoSync.acoustid"))
        if plugin:
            return plugin

        # Check by capability
        plugins = PluginRegistry.get_plugins_with_capability(
            Capability.RESOLVE_FINGERPRINT
        )
        for p in plugins:
            caps = getattr(p, "capabilities", None)
            if caps:
                algos = getattr(caps, "fingerprint_algorithms", []) or []
                if "chromaprint" in algos or getattr(
                    caps, "supports_fingerprinting", False
                ):
                    return p
        return None

    def _get_mb_plugin(self) -> Any | None:
        if self._metadata_provider is not None:
            return self._metadata_provider

        # Check by plugin id
        plugin = PluginRegistry.get_plugin(generate_plugin_id("EchoSync.musicbrainz"))
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
        cand_dur = (
            candidate.get("length")
            or candidate.get("duration_ms")
            or candidate.get("duration")
        )
        cand_dur_ms: int | None = None
        if cand_dur:
            try:
                cand_dur_val = float(cand_dur)
                if 0 < cand_dur_val < 10000:
                    cand_dur_val *= 1000.0
                cand_dur_ms = int(cand_dur_val)
                delta = abs(cand_dur_val - file_duration_ms)
                if delta > 2000:
                    return 0.0  # Outside strict AcoustID duration window
            except (ValueError, TypeError):
                pass

        c_title = str(candidate.get("title") or "")
        c_artist = str(candidate.get("artist") or candidate.get("artist_name") or "")
        c_album = str(candidate.get("album") or candidate.get("album_title") or "")

        # Candidate title MUST match the filename stem or baseline title with confidence >= 0.70
        clean_file_title = clean_title_from_filename(filename) if filename else ""
        title_similarities = []
        if baseline_title and baseline_title.strip():
            sim_b = difflib.SequenceMatcher(
                None, c_title.lower().strip(), baseline_title.lower().strip()
            ).ratio()
            title_similarities.append(sim_b)
        if clean_file_title and not is_generic_title(clean_file_title):
            sim_f = difflib.SequenceMatcher(
                None, c_title.lower().strip(), clean_file_title.lower().strip()
            ).ratio()
            title_similarities.append(sim_f)

        if title_similarities and max(title_similarities) < 0.70:
            return 0.0

        query_track = EchosyncTrack(
            raw_title=baseline_title or clean_file_title,
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
        score = match_res.confidence_score if match_res else 0.0

        # Preference for canonical studio release groups
        release_group = (
            candidate.get("release_group") or candidate.get("release-group") or {}
        )
        if not release_group and candidate.get("releases"):
            for r in candidate.get("releases") or []:
                if isinstance(r, dict):
                    rg = r.get("release-group") or r.get("release_group") or {}
                    if (
                        rg.get("primary_type") == "Album"
                        or rg.get("primary-type") == "Album"
                    ):
                        release_group = rg
                        break

        p_type = release_group.get("primary_type") or release_group.get("primary-type")
        if p_type == "Album":
            score += 5.0

        return max(score, 0.0)

    def resolve_track(self, request: ResolutionRequest) -> ResolutionResult:
        """Resolve track metadata through the authoritative 6-stage resolution waterfall."""
        result = self._execute_waterfall(request)

        # ── Stage 6: Entity Alias Resolution ──────────────────────────────────
        result.alias_proposals = self._resolve_aliases(request, result)
        return result

    def _resolve_aliases(
        self, request: ResolutionRequest, result: ResolutionResult
    ) -> list[EntityAliasProposal]:
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
            hook_results = self.hook_manager.execute_hook(
                "resolve_entity_aliases", context
            )
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
            logger.warning(
                f"[metadata_engine] Error resolving entity aliases for sync_id={result.sync_id}: {e}"
            )
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
                duration_ms = (
                    round(d_sec * 1000) if d_sec < 10000 else round(d_sec)
                )
            except (ValueError, TypeError):
                duration_ms = 0

        # Invariant: Multi-channel audio (>2 channels) must skip fingerprinting until native downmixing
        chromaprint: str | None = None
        if channels > 2:
            logger.info(
                "[resolution_engine] Multi-channel audio detected (%d channels) for %s; skipping Chromaprint extraction.",
                channels,
                file_path.name,
            )
        else:
            try:
                chromaprint, fp_dur = FingerprintGenerator.generate_with_duration(
                    str(file_path)
                )
                if fp_dur and (duration_ms <= 0):
                    duration_ms = round(float(fp_dur) * 1000)
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
        baseline_artist = (
            request.baseline_artist
            or (str(tag_artist).strip() if tag_artist else None)
            or ""
        )
        baseline_album = (
            request.baseline_album
            or (str(tag_album).strip() if tag_album else None)
            or ""
        )

        # Extract clean title directly from physical filename
        sanitized_file_title = clean_title_from_filename(file_path.name)
        filename_is_identifiable = bool(
            sanitized_file_title and not is_generic_title(sanitized_file_title)
        )

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
        sig_tag = raw_tags.get("echosync_signature")
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
        if embedded_mbid and not request.ignore_embedded_mbid:
            mb_plugin = self._get_mb_plugin()
            if mb_plugin and hasattr(mb_plugin, "get_metadata"):
                try:
                    meta = mb_plugin.get_metadata(str(embedded_mbid).strip())
                    if meta:
                        c_title = (
                            meta.get("title")
                            if isinstance(meta, dict)
                            else getattr(meta, "title", None)
                        )
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

                        if not c_title or contradicts_filename or not verify_title_trust_gate(
                            candidate_title=c_title,
                            baseline_title=baseline_check,
                            filename=file_path.name,
                            tag_title=tag_title,
                            min_similarity=0.60,
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
                                else (
                                    getattr(meta, "artist_name", None)
                                    or getattr(meta, "artist", None)
                                )
                            )
                            c_album = (
                                (meta.get("album") or meta.get("album_title"))
                                if isinstance(meta, dict)
                                else (
                                    getattr(meta, "album_title", None)
                                    or getattr(meta, "album", None)
                                )
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
                    logger.debug(
                        "[resolution_engine] Embedded MBID lookup failed: %s", e_mb
                    )

        # ── Stage 2: Local Chromaprint Cache ──────────────────────────────────
        if chromaprint and not request.ignore_cache:
            cached_meta = self._check_local_chromaprint_cache(
                chromaprint, sync_id=request.sync_id
            )
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

                if cand_title and not contradicts_filename and verify_title_trust_gate(
                    candidate_title=cand_title,
                    baseline_title=request.baseline_title or baseline_title,
                    filename=file_path.name,
                    tag_title=tag_title,
                    min_similarity=0.60,
                ):
                    logger.info(
                        "[resolution_engine] Stage 2 HIT (local chromaprint cache): %s → MBID %s",
                        file_path.name,
                        cached_meta.get("musicbrainz_id"),
                    )
                    c_year, c_track, c_disc = _extract_release_details(
                        cached_meta,
                        recording_id=cached_meta.get("musicbrainz_id")
                        or cached_meta.get("musicbrainz_track_id"),
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
            )
            if acoustid_res:
                logger.info(
                    "[resolution_engine] Stage 3 HIT (AcoustID): %s → MBID %s (score: %.1f)",
                    file_path.name,
                    acoustid_res["musicbrainz_track_id"],
                    acoustid_res["candidate_score"],
                )
                return ResolutionResult(
                    media_id=request.media_id,
                    sync_id=request.sync_id,
                    title=acoustid_res["title"],
                    artist=acoustid_res["artist"],
                    album=acoustid_res.get("album") or baseline_album,
                    year=acoustid_res.get("year")
                    if acoustid_res.get("year") is not None
                    else parsed_year,
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

    def _check_local_chromaprint_cache(
        self, chromaprint: str, sync_id: str | None = None
    ) -> dict[str, Any] | None:
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
                release_mbid = (
                    peer_track.album.mb_release_id if peer_track.album else None
                )

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
            logger.debug(
                "[resolution_engine] Local chromaprint DB lookup failed: %s", exc
            )
            return None

    def _resolve_acoustid(
        self,
        chromaprint: str,
        file_duration_ms: int,
        baseline_title: str,
        filename: str,
        tag_title: str | None,
        baseline_artist: str | None = None,
        baseline_album: str | None = None,
    ) -> dict[str, Any] | None:
        """Query AcoustID, pre-filter candidate recordings, and pick the highest scoring candidate."""
        acoustid_plugin = self._get_acoustid_plugin()
        mb_plugin = self._get_mb_plugin()
        if not acoustid_plugin or not mb_plugin:
            return None

        duration_sec = round(file_duration_ms / 1000.0)
        try:
            details = acoustid_plugin.resolve_fingerprint_details(
                chromaprint, duration_sec
            )
            if not isinstance(details, dict):
                return None
            acoustid_id = details.get("acoustid_id")
            candidate_mbids = details.get("mbids") or []
            recordings = details.get("recordings") or []
            if not candidate_mbids and not recordings:
                return None

            # Map recordings by MBID for pre-filtering
            rec_by_mbid: dict[str, dict[str, Any]] = {}
            for r in recordings:
                if isinstance(r, dict) and r.get("id"):
                    rec_by_mbid[str(r["id"]).strip()] = r

            # Collect unique MBIDs
            all_mbid_candidates = list(candidate_mbids)
            for r_id in rec_by_mbid:
                if r_id not in all_mbid_candidates:
                    all_mbid_candidates.append(r_id)

            def _is_artist_unrelated(cand_artist_str: str) -> bool:
                if not cand_artist_str or not cand_artist_str.strip():
                    return False
                c_art = cand_artist_str.lower().strip()

                if baseline_artist and str(baseline_artist).strip():
                    b_art = str(baseline_artist).lower().strip()
                    if b_art not in ("unknown", "unknown artist", "various artists", "va"):
                        if c_art in b_art or b_art in c_art:
                            return False
                        b_tokens = {w for w in re.findall(r"\w+", b_art) if len(w) > 2}
                        c_tokens = {w for w in re.findall(r"\w+", c_art) if len(w) > 2}
                        if b_tokens and c_tokens and (b_tokens & c_tokens):
                            return False
                        sim = difflib.SequenceMatcher(None, b_art, c_art).ratio()
                        if sim >= 0.50:
                            return False
                        if filename:
                            fn_clean = filename.lower()
                            if c_art in fn_clean:
                                return False
                        return True

                if filename:
                    fn_clean = filename.lower()
                    parts = re.split(r"[\-_]", Path(filename).stem)
                    if len(parts) >= 2:
                        fn_artist_guess = parts[0].lower().strip()
                        if len(fn_artist_guess) > 2 and not fn_artist_guess.isdigit():
                            if c_art in fn_artist_guess or fn_artist_guess in c_art:
                                return False
                            sim = difflib.SequenceMatcher(None, fn_artist_guess, c_art).ratio()
                            return sim < 0.50
                return False

            viable_candidates: list[tuple[str, float]] = []
            for mbid in all_mbid_candidates:
                mbid_str = str(mbid).strip()
                if not mbid_str:
                    continue

                rec_meta = rec_by_mbid.get(mbid_str) or {}
                cand_artist = rec_meta.get("artist")
                if cand_artist and _is_artist_unrelated(cand_artist):
                    logger.debug(
                        "[resolution_engine] Pre-filter discarded AcoustID candidate MBID %s by unrelated artist '%s' (baseline: '%s')",
                        mbid_str,
                        cand_artist,
                        baseline_artist,
                    )
                    continue

                rec_dur = rec_meta.get("duration")
                if rec_dur is not None:
                    try:
                        rec_dur_val = float(rec_dur)
                        if 0 < rec_dur_val < 10000:
                            rec_dur_val *= 1000.0
                        dur_delta = abs(rec_dur_val - file_duration_ms)
                    except (ValueError, TypeError):
                        dur_delta = 999999.0
                else:
                    dur_delta = 999999.0

                viable_candidates.append((mbid_str, dur_delta))

            # Sort by duration proximity (closest match first)
            viable_candidates.sort(key=lambda x: x[1])

            # Cap MusicBrainz candidate detail fetches to maximum of top 3
            top_candidates = [item[0] for item in viable_candidates[:3]]

            best_candidate: dict[str, Any] | None = None
            best_mbid: str | None = None
            best_score = 0.0

            for mbid_str in top_candidates:
                cand_meta = mb_plugin.get_metadata(mbid_str)
                if not isinstance(cand_meta, dict):
                    continue

                cand_title = cand_meta.get("title")
                # Trust Gate Title Verification
                if cand_title and not verify_title_trust_gate(
                    candidate_title=cand_title,
                    baseline_title=baseline_title,
                    filename=filename,
                    tag_title=tag_title,
                    min_similarity=0.60,
                ):
                    continue

                cand_score = self.score_candidate(
                    candidate=cand_meta,
                    baseline_title=baseline_title,
                    file_duration_ms=file_duration_ms,
                    baseline_artist=baseline_artist,
                    baseline_album=baseline_album,
                    filename=filename,
                )
                if cand_score > 0 and cand_score > best_score:
                    best_score = cand_score
                    best_candidate = cand_meta
                    best_mbid = mbid_str

            if best_candidate and best_mbid:
                cand_year, cand_track, cand_disc = _extract_release_details(
                    best_candidate,
                    recording_id=best_mbid,
                )

                return {
                    "title": best_candidate.get("title") or baseline_title,
                    "artist": best_candidate.get("artist")
                    or best_candidate.get("artist_name")
                    or "",
                    "album": best_candidate.get("album")
                    or best_candidate.get("album_title")
                    or "",
                    "year": cand_year,
                    "track_number": cand_track,
                    "disc_number": cand_disc,
                    "musicbrainz_track_id": best_mbid,
                    "musicbrainz_release_id": best_candidate.get("release_id"),
                    "acoustid_id": acoustid_id,
                    "isrc": best_candidate.get("isrc"),
                    "candidate_score": best_score,
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
    ) -> dict[str, Any] | None:
        """Scoped text search waterfall with prefix sanitization and strict recording: + artist: matching.

        Blocks artist-only discography leaks ([] fallback).
        """
        if not baseline_title or not baseline_artist:
            return None

        # Sanitize track prefixes (e.g., "01 - Title", "01. Title")
        sanitized_title = re.sub(
            r"^(?:(?:\d{1,2}[.-])?\d{1,3}[\s\-_.]{1,3}\s*)+", "", str(baseline_title)
        ).strip()
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
            results = (
                mb_client.search_metadata(query_track, limit=5)
                if hasattr(mb_client, "search_metadata")
                else None
            )
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
                        mbid = item.identifiers.get(
                            "musicbrainz_recording_id"
                        ) or item.identifiers.get("mbid")
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

                match_res = matcher.calculate_match(query_track, cand)
                score = match_res.confidence_score if match_res else 0.0
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
                    (
                        meta.get("title")
                        if isinstance(meta, dict)
                        else getattr(meta, "title", None)
                    )
                    or best_cand.title
                    or sanitized_title
                )
                final_artist = (
                    (
                        (meta.get("artist") or meta.get("artist_name"))
                        if isinstance(meta, dict)
                        else (
                            getattr(meta, "artist_name", None)
                            or getattr(meta, "artist", None)
                        )
                    )
                    or best_cand.artist_name
                    or baseline_artist
                )
                final_album = (
                    (
                        (meta.get("album") or meta.get("album_title"))
                        if isinstance(meta, dict)
                        else (
                            getattr(meta, "album_title", None)
                            or getattr(meta, "album", None)
                        )
                    )
                    or best_cand.album_title
                    or baseline_album
                )
                final_release_id = (
                    meta.get("release_id")
                    if isinstance(meta, dict)
                    else getattr(meta, "mb_release_id", None)
                )

                final_year, final_track, final_disc = _extract_release_details(
                    meta,
                    recording_id=best_mbid,
                    fallback_year=getattr(best_cand, "release_year", None),
                    fallback_track=getattr(best_cand, "track_number", None),
                    fallback_disc=getattr(best_cand, "disc_number", None),
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
                    "confidence_score": best_score / 100.0,
                }
        except Exception as exc:
            logger.warning("[resolution_engine] Scoped text waterfall error: %s", exc)

        return None
