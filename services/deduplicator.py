"""Canonical Deduplication Service for EchoSync (Stage 4).

Handles:
1. 1:N Relational Duplicates (Multiple LocalMedia files associated with a single Track).
2. Cross-Track Acoustic Duplicates (Matching Chromaprint fingerprints across distinct Tracks).
3. Reactive Ingestion Gating (Listens to TRACK_IMPORTED and evaluates duplicate candidates immediately).
4. Staging inferior duplicates to SuggestionStagingQueue under HYGIENE_DUPLICATION intent.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from database.music_database import (
    get_database,
    Track,
    LocalMedia,
    AudioFingerprint,
    Artist,
    Album,
)
from core.settings import config_manager
from core.tiered_logger import get_logger
from core.event_bus import event_bus
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_DUPLICATE_DETECTION
from core.db.echo_sync_track import EchosyncTrack

logger = get_logger("services.deduplicator")


class DeduplicationService:
    def __init__(self):
        self.db = get_database()
        self._subscribed = False
        self._subscribe_events()

    def _subscribe_events(self) -> None:
        if self._subscribed:
            return
        try:
            event_bus.subscribe("TRACK_IMPORTED", self._on_track_imported)
            self._subscribed = True
            logger.info("DeduplicationService successfully subscribed to TRACK_IMPORTED")
        except Exception as e:
            logger.warning(f"Failed to subscribe deduplication events: {e}")

    def _on_track_imported(self, payload: dict) -> None:
        """Reactive Ingestion Interceptor: evaluate duplicate candidates immediately upon import."""
        try:
            track_data = payload.get("track")
            if not track_data or not isinstance(track_data, dict):
                return

            file_path = track_data.get("file_path")
            if not file_path:
                return

            logger.info(f"Reactive Ingestion Gate: Evaluating imported file {file_path}")
            self.evaluate_incoming_file(file_path)
        except Exception as e:
            logger.error(f"Error in deduplication reactive ingestion gate: {e}", exc_info=True)

    def evaluate_incoming_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract fingerprint for an incoming file, persist AudioFingerprint, and check for duplicates."""
        canon_path = str(Path(file_path).resolve())
        fp, duration = FingerprintGenerator.generate_with_duration(canon_path)
        if not fp:
            logger.debug(f"Could not generate fingerprint for incoming file {canon_path}")
            return None

        with self.db.session_scope() as session:
            media = (
                session.query(LocalMedia)
                .options(joinedload(LocalMedia.track))
                .filter(LocalMedia.file_path == canon_path)
                .first()
            )
            if not media:
                logger.debug(f"LocalMedia record not yet committed for {canon_path}")
                return None

            # 1. Upsert AudioFingerprint record
            existing_fp = (
                session.query(AudioFingerprint)
                .filter(AudioFingerprint.media_id == media.media_id)
                .first()
            )
            if not existing_fp:
                new_fp = AudioFingerprint(
                    media_id=media.media_id,
                    chromaprint=fp,
                )
                session.add(new_fp)
                session.flush()

            # 2. Check for 1:N Relational Duplicates on the same Track
            if media.track and len(media.track.media_files) > 1:
                logger.info(
                    f"1:N Relational Duplicate detected for Track {media.track.id} ({len(media.track.media_files)} files)"
                )
                return self.resolve_relational_duplicates(media.track.id)

            # 3. Check for Cross-Track Acoustic Duplicates with matching Chromaprint
            matching_fps = (
                session.query(AudioFingerprint)
                .options(joinedload(AudioFingerprint.media).joinedload(LocalMedia.track))
                .filter(AudioFingerprint.chromaprint == fp)
                .all()
            )

            distinct_track_ids = {
                mfp.media.track_id
                for mfp in matching_fps
                if mfp.media and mfp.media.track_id
            }

            if len(distinct_track_ids) > 1:
                logger.info(
                    f"Cross-Track Acoustic Duplicates detected across {len(distinct_track_ids)} tracks"
                )
                return self.resolve_acoustic_duplicate_group(list(distinct_track_ids), fp)

        return None

    def resolve_relational_duplicates(self, track_id: int) -> Optional[Dict[str, Any]]:
        """Evaluate multiple LocalMedia rows for a single Track and stage inferior media for deletion."""
        with self.db.session_scope() as session:
            track = (
                session.query(Track)
                .options(selectinload(Track.media_files), joinedload(Track.artist))
                .filter(Track.id == track_id)
                .first()
            )
            if not track or len(track.media_files) < 2:
                return None

            media_candidates = list(track.media_files)
            winner, losers = self._rank_media_candidates(media_candidates)

            br_str = str(winner.bitrate or 0)
            reason_str = f"1:N Duplicate Media for '{track.title}': keeping best quality media {winner.media_id} ({br_str}kbps), pruning {len(losers)} inferior copies."

            payload = {
                "event": "system_duplicate",
                "event_type": "system_duplicate",
                "subtype": "relational_duplicate",
                "track_id": track.id,
                "sync_id": track.sync_id,
                "title": track.title,
                "artist": track.artist.name if track.artist else "Unknown Artist",
                "keep_media_id": winner.media_id,
                "delete_media_ids": [m.media_id for m in losers],
                "confidence_score": 100.0,
                "requires_manual_review": False,
                "reason": reason_str,
            }

            event_bus.publish(payload)
            event_bus.publish({
                "event": "DUPLICATE_MEDIA_DETECTED",
                "track_id": track.id,
                "sync_id": track.sync_id,
                "keep_media_id": winner.media_id,
                "delete_media_ids": [m.media_id for m in losers],
                "subtype": "relational_duplicate",
            })
            return payload

    def resolve_acoustic_duplicate_group(
        self, track_ids: List[int], chromaprint: str
    ) -> Optional[Dict[str, Any]]:
        """Evaluate cross-track acoustic duplicates and stage inferior tracks for deletion."""
        with self.db.session_scope() as session:
            tracks = (
                session.query(Track)
                .options(
                    joinedload(Track.artist),
                    joinedload(Track.album),
                    selectinload(Track.media_files),
                )
                .filter(Track.id.in_(track_ids))
                .all()
            )

            if len(tracks) < 2:
                return None

            # Rank tracks by quality profile
            winner, losers = self._rank_track_candidates(tracks)

            engine = WeightedMatchingEngine(PROFILE_DUPLICATE_DETECTION)
            source_et = EchosyncTrack(
                raw_title=winner.title,
                artist_name=winner.artist.name if winner.artist else "",
                album_title=winner.album.title if winner.album else "",
                duration=winner.duration,
                fingerprint=chromaprint,
            )

            min_confidence = 100.0
            reasoning_parts = []
            for loser in losers:
                candidate_et = EchosyncTrack(
                    raw_title=loser.title,
                    artist_name=loser.artist.name if loser.artist else "",
                    album_title=loser.album.title if loser.album else "",
                    duration=loser.duration,
                    fingerprint=chromaprint,
                )
                match_res = engine.calculate_match(source_et, candidate_et)
                min_confidence = min(min_confidence, match_res.confidence_score)
                score_str = f"{match_res.confidence_score:.1f}"
                reasoning_parts.append(f"T{loser.id} score: {score_str}%")

            requires_manual_review = min_confidence < 95.0
            score_formatted = f"{min_confidence:.1f}"
            details_str = ", ".join(reasoning_parts)
            reason_str = f"Acoustic duplicate for '{winner.title}'. Confidence: {score_formatted}%. Details: {details_str}"

            payload = {
                "event": "system_duplicate",
                "event_type": "system_duplicate",
                "subtype": "acoustic_duplicate",
                "keep_id": winner.id,
                "sync_id": winner.sync_id,
                "delete_ids": [t.id for t in losers],
                "confidence_score": min_confidence,
                "requires_manual_review": requires_manual_review,
                "reason": reason_str,
            }

            event_bus.publish(payload)
            event_bus.publish({
                "event": "DUPLICATE_MEDIA_DETECTED",
                "keep_id": winner.id,
                "sync_id": winner.sync_id,
                "delete_ids": [t.id for t in losers],
                "subtype": "acoustic_duplicate",
                "confidence_score": min_confidence,
            })
            return payload

    def scan_library_duplicates(self) -> Dict[str, Any]:
        """Full scan of music database for both 1:N relational duplicates and cross-track acoustic duplicates."""
        results = {
            "relational_duplicates": [],
            "acoustic_duplicates": [],
        }

        with self.db.session_scope() as session:
            # 1. 1:N Relational Scan: Tracks with count(local_media) > 1
            relational_tracks = (
                session.query(Track.id)
                .join(LocalMedia)
                .group_by(Track.id)
                .having(func.count(LocalMedia.id) > 1)
                .all()
            )
            for (t_id,) in relational_tracks:
                action = self.resolve_relational_duplicates(t_id)
                if action:
                    results["relational_duplicates"].append(action)

            # 2. Acoustic Scan: Chromaprints matching multiple tracks
            subquery = (
                session.query(AudioFingerprint.chromaprint)
                .group_by(AudioFingerprint.chromaprint)
                .having(func.count(AudioFingerprint.id) > 1)
            )
            duplicate_hashes = [row[0] for row in subquery.all()]

            for fp_hash in duplicate_hashes:
                fps = (
                    session.query(AudioFingerprint)
                    .options(joinedload(AudioFingerprint.media))
                    .filter(AudioFingerprint.chromaprint == fp_hash)
                    .all()
                )
                t_ids = list({fp.media.track_id for fp in fps if fp.media and fp.media.track_id})
                if len(t_ids) > 1:
                    action = self.resolve_acoustic_duplicate_group(t_ids, fp_hash)
                    if action:
                        results["acoustic_duplicates"].append(action)

        return results

    def _rank_media_candidates(
        self, candidates: List[LocalMedia]
    ) -> Tuple[LocalMedia, List[LocalMedia]]:
        """Rank LocalMedia candidates based on lossless codecs, bitrate, sample rate, and bit depth."""
        def media_score(m: LocalMedia) -> Tuple[int, int, int, int]:
            fmt = (m.file_format or "").lower()
            is_lossless = 1 if fmt in {"flac", "alac", "wav", "aiff"} else 0
            bitrate = m.bitrate or 0
            bit_depth = m.bit_depth or 16
            sample_rate = m.sample_rate or 44100
            return (is_lossless, bit_depth, bitrate, sample_rate)

        sorted_candidates = sorted(candidates, key=media_score, reverse=True)
        return sorted_candidates[0], sorted_candidates[1:]

    def _rank_track_candidates(
        self, candidates: List[Track]
    ) -> Tuple[Track, List[Track]]:
        """Rank Track candidates based on highest quality media attached."""
        def track_score(t: Track) -> Tuple[int, int, int, int]:
            if not t.media_files:
                return (0, 0, 0, 0)
            best_m, _ = self._rank_media_candidates(list(t.media_files))
            fmt = (best_m.file_format or "").lower()
            is_lossless = 1 if fmt in {"flac", "alac", "wav", "aiff"} else 0
            bitrate = best_m.bitrate or 0
            bit_depth = best_m.bit_depth or 16
            sample_rate = best_m.sample_rate or 44100
            return (is_lossless, bit_depth, bitrate, sample_rate)

        sorted_tracks = sorted(candidates, key=track_score, reverse=True)
        return sorted_tracks[0], sorted_tracks[1:]


_deduplicator_instance: Optional[DeduplicationService] = None


def get_deduplicator() -> DeduplicationService:
    global _deduplicator_instance
    if _deduplicator_instance is None:
        _deduplicator_instance = DeduplicationService()
    return _deduplicator_instance
