import os
from typing import Any

from sqlalchemy import func

from core.db.echo_sync_track import EchosyncTrack
from core.settings import config_manager
from core.tiered_logger import get_logger
from database.music_database import (
    Artist,
    AudioFingerprint,
    LocalMedia,
    Track,
    get_database,
)
from services.download_manager import get_download_manager

logger = get_logger("services.library_hygiene")


class DuplicateHygieneService:
    def __init__(self, db: Any | None = None):
        self.db = db or get_database()

    def _get_track_arrangement_family(self, track: Track) -> str:
        """
        Extract canonical version / arrangement family (e.g. 'live', 'piano'/'acoustic',
        'remaster', 'remix', 'instrumental', 'deluxe', 'studio_original').
        Checks explicit track.edition first, then falls back to parsing title keywords.
        """
        from core.matching_engine.matching_engine import get_version_family

        if track.edition:
            fam = get_version_family(track.edition)
            if fam:
                return fam
        et = EchosyncTrack(
            raw_title=track.title or "",
            artist_name=track.artist.name if track.artist else "",
            album_title=track.album.title if track.album else "",
        )
        if et.edition:
            fam = get_version_family(et.edition)
            if fam:
                return fam
        return "studio_original"

    def backfill_missing_fingerprints(
        self,
        batch_size: int = 50,
        progress_callback: Any | None = None,
        max_items: int | None = None,
    ) -> int:
        """
        Scan LocalMedia records that lack an AudioFingerprint record.
        Generate Chromaprint fingerprints for files present on disk in batches and persist them.
        Reports percentage progress via progress_callback and event_bus to prevent HTTP gateway timeouts.
        Returns the count of newly generated fingerprints.
        """
        from core.event_bus import event_bus
        from core.matching_engine.fingerprinting import FingerprintGenerator
        from core.utils import PathMapper

        generated_count = 0
        try:
            with self.db.session_scope() as session:
                unfingerprinted_ids = [
                    row[0]
                    for row in session.query(LocalMedia.id)
                    .outerjoin(
                        AudioFingerprint,
                        LocalMedia.media_id == AudioFingerprint.media_id,
                    )
                    .filter(AudioFingerprint.id.is_(None))
                    .all()
                ]

            if not unfingerprinted_ids:
                return 0

            if max_items:
                unfingerprinted_ids = unfingerprinted_ids[:max_items]

            total = len(unfingerprinted_ids)
            logger.info(
                "Duplicate Scan: Found %d media file(s) missing audio fingerprints. Backfilling in batches...",
                total,
            )

            processed = 0
            for i in range(0, total, batch_size):
                batch_ids = unfingerprinted_ids[i : i + batch_size]
                with self.db.session_scope() as session:
                    media_batch = (
                        session.query(LocalMedia)
                        .filter(LocalMedia.id.in_(batch_ids))
                        .all()
                    )
                    for media in media_batch:
                        fpath = media.file_path
                        if not fpath:
                            continue
                        if not os.path.exists(fpath):
                            mapped = PathMapper.to_local(fpath)
                            if mapped and os.path.exists(mapped):
                                fpath = mapped
                            else:
                                continue

                        try:
                            fp, _ = FingerprintGenerator.generate_with_duration(fpath)
                            if fp:
                                afp = AudioFingerprint(
                                    media_id=media.media_id,
                                    chromaprint=fp,
                                )
                                session.add(afp)
                                generated_count += 1
                        except Exception as e:
                            logger.debug("Could not fingerprint %s: %s", fpath, e)

                    session.commit()

                processed += len(batch_ids)
                status_msg = f"Fingerprinted {processed}/{total} audio files ({round((processed / total) * 100, 1)}%)"
                if progress_callback:
                    try:
                        progress_callback(processed, total, status_msg)
                    except Exception:
                        pass
                event_bus.publish(
                    "job_progress",
                    {
                        "job_name": "duplicate_scan_job",
                        "current": processed,
                        "total": total,
                        "status": status_msg,
                        "percentage": round((processed / total) * 100, 1)
                        if total > 0
                        else 0,
                    },
                )

            if generated_count:
                logger.info(
                    "Duplicate Scan: Successfully generated and saved %d audio fingerprint(s).",
                    generated_count,
                )
        except Exception as e:
            logger.warning("Error during fingerprint backfill: %s", e, exc_info=True)

        return generated_count

    def find_duplicates(
        self, backfill: bool = False, progress_callback: Any | None = None
    ) -> dict[str, list[dict]]:
        """
        Identify duplicate tracks across three tiers:
        1. Relational 1:N Duplicates (Single Track with multiple LocalMedia files).
        2. Acoustic Duplicates (Matching Chromaprints in AudioFingerprint across distinct Tracks).
        3. Metadata & ISRC Collisions (Tracks sharing identical ISRC or identical Artist + Title).

        Returns a dictionary with 'auto_resolve' and 'manual_review' lists.
        """
        results: dict[str, list[dict]] = {"auto_resolve": [], "manual_review": []}
        seen_track_ids: set[int] = set()

        # Phase 0: Optional backfill for background jobs (disabled for fast, non-blocking HTTP requests)
        if backfill:
            self.backfill_missing_fingerprints(progress_callback=progress_callback)

        try:
            from services.deduplicator import get_deduplicator
            from sqlalchemy.orm import joinedload, selectinload

            dedup = get_deduplicator()

            with self.db.session_scope() as session:
                # ── Phase 1: 1:N Relational Duplicates ──────────────────────────
                relational_track_ids = [
                    row[0]
                    for row in session.query(Track.id)
                    .join(LocalMedia, Track.id == LocalMedia.track_id)
                    .group_by(Track.id)
                    .having(func.count(LocalMedia.id) > 1)
                    .all()
                ]

                for t_id in relational_track_ids:
                    rel_scenario = dedup.resolve_relational_duplicates(t_id)
                    if rel_scenario:
                        track = (
                            session.query(Track)
                            .options(
                                joinedload(Track.artist),
                                selectinload(Track.media_files),
                            )
                            .filter(Track.id == t_id)
                            .first()
                        )
                        if track:
                            rel_scenario["type"] = "Duplicate Resolution"
                            rel_scenario["title"] = track.title
                            rel_scenario["artist"] = (
                                track.artist.name if track.artist else "Unknown Artist"
                            )
                            rel_scenario["sync_id"] = track.sync_id
                            if (
                                "tracks" not in rel_scenario
                                or not rel_scenario["tracks"]
                            ):
                                rel_scenario["tracks"] = [self._serialize_track(track)]
                            results["auto_resolve"].append(rel_scenario)
                            seen_track_ids.add(t_id)

                # ── Phase 2: Acoustic Duplicates (Matching Chromaprints) ─────────
                subquery = (
                    session.query(AudioFingerprint.chromaprint)
                    .group_by(AudioFingerprint.chromaprint)
                    .having(func.count(AudioFingerprint.id) > 1)
                )
                duplicate_hashes = [row[0] for row in subquery.yield_per(1000)]

                for fp_hash in duplicate_hashes:
                    fps = (
                        session.query(AudioFingerprint)
                        .options(joinedload(AudioFingerprint.media))
                        .filter(AudioFingerprint.chromaprint == fp_hash)
                        .all()
                    )
                    t_ids = list(
                        {
                            fp.media.track_id
                            for fp in fps
                            if fp.media and fp.media.track_id
                        }
                    )
                    if len(t_ids) < 2:
                        continue

                    tracks = (
                        session.query(Track)
                        .options(
                            joinedload(Track.artist),
                            joinedload(Track.album),
                            selectinload(Track.media_files),
                        )
                        .join(Artist)
                        .filter(Track.id.in_(t_ids))
                        .all()
                    )
                    if len(tracks) < 2:
                        continue

                    scenario = self._analyze_group(tracks, fp_hash)
                    if not scenario:
                        continue

                    for t in tracks:
                        seen_track_ids.add(t.id)

                    if scenario["confidence_score"] >= 90.0:
                        results["auto_resolve"].append(scenario)
                    else:
                        results["manual_review"].append(scenario)

                # ── Phase 3: Metadata & ISRC Collisions ─────────────────────────
                # 3a. Matching ISRC across distinct tracks
                isrc_rows = [
                    row[0]
                    for row in session.query(Track.isrc)
                    .filter(Track.isrc.isnot(None), Track.isrc != "")
                    .group_by(Track.isrc)
                    .having(func.count(Track.id) > 1)
                    .all()
                ]
                for isrc_val in isrc_rows:
                    isrc_tracks = (
                        session.query(Track)
                        .options(
                            joinedload(Track.artist),
                            joinedload(Track.album),
                            selectinload(Track.media_files),
                        )
                        .filter(Track.isrc == isrc_val)
                        .all()
                    )
                    unseen_tracks = [
                        t for t in isrc_tracks if t.id not in seen_track_ids
                    ]
                    if len(unseen_tracks) >= 2:
                        scenario = self._analyze_metadata_group(
                            unseen_tracks, reason_prefix=f"Matching ISRC ({isrc_val})"
                        )
                        if scenario:
                            for t in unseen_tracks:
                                seen_track_ids.add(t.id)
                            if scenario["confidence_score"] >= 90.0:
                                results["auto_resolve"].append(scenario)
                            else:
                                results["manual_review"].append(scenario)

                # 3b. Matching Artist + Title (case-insensitive)
                meta_dups = (
                    session.query(Track.artist_id, func.lower(Track.title))
                    .filter(Track.title.isnot(None), Track.title != "")
                    .group_by(Track.artist_id, func.lower(Track.title))
                    .having(func.count(Track.id) > 1)
                    .all()
                )
                for a_id, lower_title in meta_dups:
                    cand_tracks = (
                        session.query(Track)
                        .options(
                            joinedload(Track.artist),
                            joinedload(Track.album),
                            selectinload(Track.media_files),
                        )
                        .filter(
                            Track.artist_id == a_id,
                            func.lower(Track.title) == lower_title,
                        )
                        .all()
                    )
                    unseen_tracks = [
                        t for t in cand_tracks if t.id not in seen_track_ids
                    ]
                    if len(unseen_tracks) < 2:
                        continue

                    # Partition by version/arrangement family (e.g. 'live', 'piano'/'acoustic', 'remaster', 'studio_original')
                    family_map: dict[str, list[Track]] = {}
                    for t in unseen_tracks:
                        fam = self._get_track_arrangement_family(t)
                        family_map.setdefault(fam, []).append(t)

                    for fam, fam_tracks in family_map.items():
                        if len(fam_tracks) >= 2:
                            scenario = self._analyze_metadata_group(
                                fam_tracks,
                                reason_prefix=f"Identical Artist & Title [{fam}]",
                            )
                            if scenario:
                                for t in fam_tracks:
                                    seen_track_ids.add(t.id)
                                if (
                                    scenario["confidence_score"] >= 90.0
                                    and not scenario["requires_manual_review"]
                                ):
                                    results["auto_resolve"].append(scenario)
                                else:
                                    results["manual_review"].append(scenario)

        except Exception as e:
            logger.error(f"Error finding duplicates: {e}", exc_info=True)

        return results

    def _analyze_group(self, tracks: list[Track], chromaprint: str) -> dict | None:
        """
        Analyze a group of duplicate tracks to determine if they can be auto-resolved
        using quality profile ranking and WeightedMatchingEngine for confidence scoring.
        """
        from core.matching_engine.matching_engine import WeightedMatchingEngine
        from core.matching_engine.scoring_profile import PROFILE_DUPLICATE_DETECTION
        from core.utils import PathMapper

        if len(tracks) < 2:
            return None

        # JIT File Check (optional warning if missing, but doesn't abort)
        for track in tracks:
            fpath = track.file_path
            if fpath and not os.path.exists(fpath):
                mapped = PathMapper.to_local(fpath)
                if not mapped or not os.path.exists(mapped):
                    logger.debug(
                        "JIT Check: Track %s file not found locally: %s",
                        track.id,
                        fpath,
                    )

        # Fetch Quality Profile Enforcer max bitrate
        max_bitrate = float("inf")
        manager_config = config_manager.get("manager", {}) or {}
        profile_id = manager_config.get("upgrade_quality_profile_id")

        if profile_id:
            from database.models import QualityProfile

            try:
                with self.db.session_scope() as sess:
                    profile = (
                        sess.query(QualityProfile).filter_by(id=profile_id).first()
                    )
                    if profile:
                        for step in profile.steps:
                            rules = step.rules or {}
                            if isinstance(rules, dict):
                                for fmt_rules in rules.values():
                                    if (
                                        isinstance(fmt_rules, dict)
                                        and "max_bitrate" in fmt_rules
                                    ):
                                        max_bitrate = min(
                                            max_bitrate, fmt_rules["max_bitrate"]
                                        )
            except Exception as e:
                logger.warning(f"Could not load quality profile {profile_id}: {e}")

        def sort_key(t):
            media_list = list(t.media_files) if t.media_files else []
            br = max([m.bitrate for m in media_list if m.bitrate] or [0])
            sample_rate = max(
                [m.sample_rate for m in media_list if m.sample_rate] or [0]
            )
            file_size = max(
                [m.file_size_bytes for m in media_list if m.file_size_bytes] or [0]
            )
            _LOSSLESS = {"flac", "alac", "wav", "dsd", "dsf", "dff", "ape"}
            is_lossless = (
                1
                if any((m.file_format or "").lower() in _LOSSLESS for m in media_list)
                else 0
            )
            effective_br = br if br <= max_bitrate else -br
            return (is_lossless, effective_br, sample_rate, file_size)

        sorted_tracks = sorted(tracks, key=sort_key, reverse=True)
        winner = sorted_tracks[0]
        losers = sorted_tracks[1:]

        # 2. Matching Engine Integration
        engine = WeightedMatchingEngine(PROFILE_DUPLICATE_DETECTION)

        source_et = EchosyncTrack(
            raw_title=winner.title or "",
            artist_name=winner.artist.name if winner.artist else "",
            album_title=winner.album.title if winner.album else "",
            duration=winner.duration,
            fingerprint=chromaprint,
        )

        # 3. Confidence Scoring
        min_confidence = 100.0
        reasoning_parts = []
        for loser in losers:
            candidate_et = EchosyncTrack(
                raw_title=loser.title or "",
                artist_name=loser.artist.name if loser.artist else "",
                album_title=loser.album.title if loser.album else "",
                duration=loser.duration,
                fingerprint=chromaprint,
            )
            match_res = engine.calculate_match(source_et, candidate_et)
            min_confidence = min(min_confidence, match_res.confidence_score)
            reasoning_parts.append(
                f"T{loser.id} score: {match_res.confidence_score:.1f}%"
            )

        final_score = min_confidence

        if 80.0 <= final_score < 95.0:
            from core.nexus_framework.plugin_loader import PluginRegistry

            try:
                mb_plugin = PluginRegistry.create_instance("musicbrainz")
                if mb_plugin:
                    mbids = [
                        getattr(t, "musicbrainz_id", None)
                        for t in tracks
                        if getattr(t, "musicbrainz_id", None)
                    ]
                    if mbids:
                        mb_data = mb_plugin.get_metadata_batch(mbids)
                        if mb_data:
                            from rapidfuzz import fuzz

                            best_alignment = 0
                            for t in tracks:
                                mb_record = mb_data.get(
                                    getattr(t, "musicbrainz_id", "")
                                )
                                if mb_record:
                                    mb_title = mb_record.get("title") or ""
                                    mb_album = mb_record.get("album") or ""
                                    loc_title = t.title or ""
                                    loc_album = t.album.title if t.album else ""
                                    score = (
                                        fuzz.ratio(mb_title.lower(), loc_title.lower())
                                        + fuzz.ratio(
                                            mb_album.lower(), loc_album.lower()
                                        )
                                    ) / 2
                                    best_alignment = max(best_alignment, score)

                            if best_alignment > 85.0:
                                final_score += 5.0
                                reasoning_parts.append(
                                    "MusicBrainz sanity check added +5.0 confidence."
                                )
            except Exception:
                pass

        requires_manual_review = final_score < 90.0

        # 4. Payload Generation
        return {
            "type": "Duplicate Resolution",
            "event_type": "system_duplicate",
            "subtype": "acoustic_duplicate",
            "title": winner.title,
            "artist": winner.artist.name if winner.artist else "Unknown Artist",
            "sync_id": winner.sync_id,
            "keep_id": winner.id,
            "delete_ids": [t.id for t in losers],
            "confidence_score": final_score,
            "requires_manual_review": requires_manual_review,
            "reason": f"Acoustic duplicate for '{winner.title}'. Confidence: {final_score:.1f}%. Details: {', '.join(reasoning_parts)}",
            "tracks": [self._serialize_track(t) for t in tracks],
        }

    def _analyze_metadata_group(
        self, tracks: list[Track], reason_prefix: str
    ) -> dict | None:
        """Analyze a group of duplicate tracks identified via matching metadata or ISRC."""
        from core.matching_engine.matching_engine import WeightedMatchingEngine
        from core.matching_engine.scoring_profile import PROFILE_DUPLICATE_DETECTION

        if len(tracks) < 2:
            return None

        # Sort tracks by quality
        def sort_key(t):
            media_list = list(t.media_files) if t.media_files else []
            br = max([m.bitrate for m in media_list if m.bitrate] or [0])
            sample_rate = max(
                [m.sample_rate for m in media_list if m.sample_rate] or [0]
            )
            file_size = max(
                [m.file_size_bytes for m in media_list if m.file_size_bytes] or [0]
            )
            _LOSSLESS = {"flac", "alac", "wav", "dsd", "dsf", "dff", "ape"}
            is_lossless = (
                1
                if any((m.file_format or "").lower() in _LOSSLESS for m in media_list)
                else 0
            )
            return (is_lossless, br, sample_rate, file_size)

        sorted_tracks = sorted(tracks, key=sort_key, reverse=True)
        winner = sorted_tracks[0]
        losers = sorted_tracks[1:]

        engine = WeightedMatchingEngine(PROFILE_DUPLICATE_DETECTION)
        source_et = EchosyncTrack(
            raw_title=winner.title or "",
            artist_name=winner.artist.name if winner.artist else "",
            album_title=winner.album.title if winner.album else "",
            duration=winner.duration,
            isrc=winner.isrc,
            edition=getattr(winner, "edition", None),
        )

        winner_fps = {
            fp.chromaprint
            for m in (winner.media_files or [])
            for fp in (m.audio_fingerprints or [])
            if fp.chromaprint
        }

        min_confidence = 100.0
        reasoning_parts = []
        has_acoustic_conflict = False
        has_edition_conflict = False

        for loser in losers:
            loser_fps = {
                fp.chromaprint
                for m in (loser.media_files or [])
                for fp in (m.audio_fingerprints or [])
                if fp.chromaprint
            }

            candidate_et = EchosyncTrack(
                raw_title=loser.title or "",
                artist_name=loser.artist.name if loser.artist else "",
                album_title=loser.album.title if loser.album else "",
                duration=loser.duration,
                isrc=loser.isrc,
                edition=getattr(loser, "edition", None),
            )
            match_res = engine.calculate_match(source_et, candidate_et)
            score = match_res.confidence_score

            # 1. Acoustic fingerprint verification: if both have fingerprints but they differ
            if winner_fps and loser_fps and winner_fps.isdisjoint(loser_fps):
                has_acoustic_conflict = True
                score = min(score, 50.0)
                reasoning_parts.append(
                    f"T{loser.id} acoustic fingerprints differ from T{winner.id} (distinct audio takes/recordings)"
                )

            # 2. Arrangement / edition verification
            w_fam = self._get_track_arrangement_family(winner)
            l_fam = self._get_track_arrangement_family(loser)
            if w_fam != l_fam:
                has_edition_conflict = True
                score = min(score, 55.0)
                reasoning_parts.append(
                    f"T{loser.id} arrangement '{l_fam}' differs from T{winner.id} '{w_fam}'"
                )

            min_confidence = min(min_confidence, score)
            reasoning_parts.append(f"T{loser.id} score: {score:.1f}%")

        requires_manual_review = (
            min_confidence < 90.0 or has_acoustic_conflict or has_edition_conflict
        )

        return {
            "type": "Duplicate Resolution",
            "event_type": "system_duplicate",
            "subtype": "metadata_duplicate",
            "title": winner.title,
            "artist": winner.artist.name if winner.artist else "Unknown Artist",
            "sync_id": winner.sync_id,
            "keep_id": winner.id,
            "delete_ids": [t.id for t in losers],
            "confidence_score": min_confidence,
            "requires_manual_review": requires_manual_review,
            "reason": f"{reason_prefix} for '{winner.title}'. Confidence: {min_confidence:.1f}%. Details: {', '.join(reasoning_parts)}",
            "tracks": [self._serialize_track(t) for t in tracks],
        }

    def _serialize_track(self, track: Track) -> dict:
        return {
            "id": track.id,
            "title": track.title,
            "artist": track.artist.name if track.artist else "Unknown Artist",
            "album": track.album.title if track.album else "",
            "bitrate": track.bitrate,
            "sample_rate": track.sample_rate,
            "file_size": track.file_size_bytes,
            "path": track.file_path,
            "format": track.file_format,
        }

    def resolve_conflict(self, keep_id: int, delete_ids: list[int]) -> dict[str, Any]:
        """
        Constructs and returns a proposed action dictionary for resolving a conflict,
        without executing physical file deletions.
        """
        actual_delete_ids = [tid for tid in delete_ids if tid != keep_id]

        return {
            "event_type": "system_duplicate",
            "keep_id": keep_id,
            "delete_ids": actual_delete_ids,
            "reason": "Auto-resolved system duplicate based on quality profile.",
        }

    def run_prune_job(self) -> dict[str, Any]:
        """
        Execute the auto-deletion logic. (Now returns proposed actions without deleting)
        """
        duplicates = self.find_duplicates()
        auto_resolve_groups = duplicates["auto_resolve"]

        logger.info(
            f"Starting Prune Job. Found {len(auto_resolve_groups)} groups to auto-resolve."
        )

        count = 0
        details = []

        for action in auto_resolve_groups:
            if action and action.get("delete_ids"):
                count += len(action["delete_ids"])
                details.append(
                    {
                        "kept_id": action["keep_id"],
                        "deleted_count": len(action["delete_ids"]),
                        "proposed_action": action,
                    }
                )
                # AutoImporter emits to event_bus natively; here we'd optionally emit
                # event_bus.publish("system_duplicate", action)

        logger.info(f"Prune Job Completed. Staged {count} tracks for deletion.")
        return {"deleted_count": count, "details": details}

    def analyze_single_track(self, track_id: int) -> dict | None:
        """
        Targeted scan for a single track's duplicate group, querying properly through LocalMedia.
        """
        try:
            from database.music_database import LocalMedia
            from services.deduplicator import get_deduplicator

            dedup = get_deduplicator()
            with self.db.session_scope() as session:
                # 1. Check if the track itself has 1:N relational duplicates
                media_count = (
                    session.query(LocalMedia)
                    .filter(LocalMedia.track_id == track_id)
                    .count()
                )
                if media_count > 1:
                    return dedup.resolve_relational_duplicates(track_id)

                # 2. Check for acoustic duplicates by querying through LocalMedia
                fps = (
                    session.query(AudioFingerprint)
                    .join(LocalMedia, AudioFingerprint.media_id == LocalMedia.media_id)
                    .filter(LocalMedia.track_id == track_id)
                    .all()
                )
                if not fps:
                    return None

                for fp in fps:
                    if not fp.chromaprint:
                        continue
                    matching_fps = (
                        session.query(AudioFingerprint)
                        .options(joinedload(AudioFingerprint.media))
                        .filter(AudioFingerprint.chromaprint == fp.chromaprint)
                        .all()
                    )
                    peer_track_ids = list(
                        {
                            f.media.track_id
                            for f in matching_fps
                            if f.media and f.media.track_id
                        }
                    )
                    if len(peer_track_ids) > 1:
                        return dedup.resolve_acoustic_duplicate_group(
                            peer_track_ids, fp.chromaprint
                        )

                return None
        except Exception as e:
            logger.error(f"Error analyzing single track {track_id}: {e}", exc_info=True)
            return None

    def _resolve_track_by_sync_id(self, sync_id: str) -> Track | None:
        """Resolve a DB track from deterministic sync_id formats."""
        base_sync_id = str(sync_id or "")

        with self.db.session_scope() as session:
            return session.query(Track).filter_by(sync_id=base_sync_id).first()

    def queue_quality_upgrade_for_sync_id(
        self,
        sync_id: str,
        upgrade_quality_profile_id: str | None = None,
    ) -> int:
        """Queue a quality replacement download for a staged lifecycle track.

        If profile ID is not provided, this reads manager.upgrade_quality_profile_id.
        """
        track = self._resolve_track_by_sync_id(sync_id)
        if not track or not track.artist:
            logger.warning(f"Could not resolve track for upgrade sync_id: {sync_id}")
            return 0

        if upgrade_quality_profile_id is None:
            manager_config = config_manager.get("manager", {}) or {}
            upgrade_quality_profile_id = manager_config.get(
                "upgrade_quality_profile_id"
            )

        echo_track = EchosyncTrack(
            raw_title=track.title,
            artist_name=track.artist.name,
            album_title=track.album.title if track.album else "",
            duration=track.duration,
            bitrate=track.bitrate,
            file_format=track.file_format,
            sample_rate=track.sample_rate,
            bit_depth=track.bit_depth,
            file_size_bytes=track.file_size_bytes,
            musicbrainz_id=track.musicbrainz_id,
            identifiers={},
        )

        dm = get_download_manager()
        return dm.queue_download(
            echo_track, quality_profile_id=upgrade_quality_profile_id
        )

    def is_track_trending(
        self,
        provider_item_id: str,
        days: int = 30,
        threshold: int = 2,
    ) -> bool:
        """
        Return True if ``provider_item_id`` has been played at least ``threshold``
        times in the last ``days`` days across all users.

        Uses a single COUNT query against ``PlaybackHistory`` in working.db.
        """
        from datetime import timedelta

        from database.working_database import PlaybackHistory, get_working_database
        from time_utils import utc_now

        cutoff = utc_now() - timedelta(days=days)
        working_db = get_working_database()
        with working_db.session_scope() as session:
            play_count = (
                session.query(func.count(PlaybackHistory.id))
                .filter(
                    PlaybackHistory.provider_item_id == provider_item_id,
                    PlaybackHistory.listened_at >= cutoff,
                )
                .scalar()
                or 0
            )
        return play_count >= threshold

    def scan_for_stale_tracks(self, inactive_days: int = 90) -> dict[str, Any]:
        """
        Scan for tracks with > 0 all-time listens but 0 listens in the last X days.
        Updates their UserTrackState lifecycle_action to 'STALE'.
        """
        from core.suggestion_engine.analytics import PlaybackAnalytics
        from database.music_database import ExternalIdentifier
        from database.working_database import UserTrackState, get_working_database
        from time_utils import utc_now

        logger.info(f"Starting stale track scan (inactive_days={inactive_days})")

        stale_provider_ids = PlaybackAnalytics.get_stale_provider_ids(
            inactive_days=inactive_days
        )
        if not stale_provider_ids:
            return {"status": "no_stale_tracks", "count": 0}

        working_db = get_working_database()
        now = utc_now()
        updated_count = 0

        with self.db.session_scope() as music_session:
            with working_db.session_scope() as work_session:
                # Find corresponding track IDs
                from sqlalchemy.orm import joinedload

                ext_idents = (
                    music_session.query(ExternalIdentifier, Track)
                    .options(joinedload(Track.artist))
                    .join(Track, ExternalIdentifier.track_id == Track.id)
                    .filter(ExternalIdentifier.provider_item_id.in_(stale_provider_ids))
                    .yield_per(1000)
                )

                for ext, track in ext_idents:
                    # Resolve to sync_id
                    sync_id = track.sync_id

                    states = (
                        work_session.query(UserTrackState)
                        .filter(UserTrackState.sync_id == sync_id)
                        .yield_per(1000)
                    )

                    for state in states:
                        # Only mark stale if it's not already staged for deletion/upgrade or exempt
                        if (
                            not state.lifecycle_action
                            and not state.admin_exempt_deletion
                        ):
                            state.lifecycle_action = "STALE"
                            state.lifecycle_queued_at = now
                            updated_count += 1
                            logger.info(
                                f"Marked track '{track.title}' (sync_id: {sync_id}) as STALE."
                            )

        logger.info(
            f"Stale track scan completed. Marked {updated_count} states as STALE."
        )
        return {"status": "success", "count": updated_count}
