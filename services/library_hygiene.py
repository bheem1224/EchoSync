from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy import func
from database.music_database import get_database, Track, AudioFingerprint, Artist
from core.tiered_logger import get_logger
from core.matching_engine.echo_sync_track import EchosyncTrack
from core.settings import config_manager
from services.download_manager import get_download_manager
import base64
import os

logger = get_logger("services.library_hygiene")

class DuplicateHygieneService:
    def __init__(self):
        self.db = get_database()

    def find_duplicates(self) -> Dict[str, List[Dict]]:
        """
        Identify duplicate tracks based on AcoustID fingerprints.
        Returns a dictionary with 'auto_resolve' and 'manual_review' lists.
        """
        results = {
            "auto_resolve": [],
            "manual_review": []
        }

        try:
            with self.db.session_scope() as session:
                # 1. Find fingerprints with multiple tracks
                # subquery: select chromaprint from audio_fingerprints group by chromaprint having count(*) > 1

                subquery = (
                    session.query(AudioFingerprint.chromaprint)
                    .group_by(AudioFingerprint.chromaprint)
                    .having(func.count(AudioFingerprint.id) > 1)
                )

                # Get the fingerprints
                duplicate_hashes = [row[0] for row in subquery.yield_per(1000)]

                for fp_hash in duplicate_hashes:
                    # Get all tracks for this fingerprint
                    fingerprints = (
                        session.query(AudioFingerprint)
                        .filter(AudioFingerprint.chromaprint == fp_hash)
                        .all()
                    )

                    track_ids = [fp.track_id for fp in fingerprints]
                    # Fetch tracks eagerly with Artist to avoid N+1 inside loop
                    # Actually session is open, so lazy load is fine, but better to be efficient if possible.
                    from sqlalchemy.orm import joinedload
                    tracks = (
                        session.query(Track)
                        .options(joinedload(Track.artist), joinedload(Track.album))
                        .join(Artist)
                        .filter(Track.id.in_(track_ids))
                        .all()
                    )

                    if len(tracks) < 2:
                        continue

                    scenario = self._analyze_group(tracks, fp_hash)
                    if not scenario:
                        continue

                    if scenario['confidence_score'] >= 90.0:
                        results['auto_resolve'].append(scenario)
                    else:
                        results['manual_review'].append(scenario)

        except Exception as e:
            logger.error(f"Error finding duplicates: {e}", exc_info=True)

        return results

    def _analyze_group(self, tracks: List[Track], chromaprint: str) -> Optional[Dict]:
        """
        Analyze a group of duplicate tracks to determine if they can be auto-resolved
        using JIT file verification and WeightedMatchingEngine for confidence scoring.
        """
        import os
        from core.matching_engine.fingerprinting import FingerprintGenerator
        from core.matching_engine.matching_engine import WeightedMatchingEngine
        from core.matching_engine.scoring_profile import ScoringWeights, ConfigurableProfile
        
        # 1. JIT File Verification
        verified_tracks = []
        for track in tracks:
            if not track.file_path or not os.path.exists(track.file_path):
                logger.warning(f"JIT Check Failed: Track {track.id} file missing at {track.file_path}")
                continue
                
            try:
                live_chromaprint = FingerprintGenerator.generate(str(track.file_path))
            except Exception as e:
                logger.error(f"JIT Check Failed: Could not generate fingerprint for {track.file_path}: {e}")
                continue
                
            if live_chromaprint != chromaprint:
                logger.warning(f"JIT Check Failed: Track {track.id} live fingerprint does not match database")
                continue
                
            verified_tracks.append(track)

        if len(verified_tracks) < 2:
            return None

        # Fetch Quality Profile Enforcer max bitrate
        max_bitrate = float('inf')
        manager_config = config_manager.get("manager", {}) or {}
        profile_id = manager_config.get("upgrade_quality_profile_id")
        
        if profile_id:
            from database.models import QualityProfile
            try:
                with self.db.session_scope() as sess:
                    profile = sess.query(QualityProfile).filter_by(id=profile_id).first()
                    if profile:
                        for step in profile.steps:
                            rules = step.rules or {}
                            if isinstance(rules, dict):
                                for fmt_rules in rules.values():
                                    if isinstance(fmt_rules, dict) and "max_bitrate" in fmt_rules:
                                        max_bitrate = min(max_bitrate, fmt_rules["max_bitrate"])
            except Exception as e:
                logger.warning(f"Could not load quality profile {profile_id}: {e}")

        def sort_key(t):
            br = t.bitrate or 0
            effective_br = br if br <= max_bitrate else -br
            return (
                effective_br,
                t.sample_rate or 0,
                t.file_size_bytes or 0
            )

        sorted_tracks = sorted(verified_tracks, key=sort_key, reverse=True)
        winner = sorted_tracks[0]
        losers = sorted_tracks[1:]
        
        # 2. Matching Engine Integration
        from core.matching_engine.scoring_profile import PROFILE_DUPLICATE_DETECTION
        engine = WeightedMatchingEngine(PROFILE_DUPLICATE_DETECTION)
        
        source_et = EchosyncTrack(
            raw_title=winner.title,
            title=winner.title,
            artist_name=winner.artist.name if winner.artist else None,
            album_title=winner.album.title if winner.album else None,
            duration=winner.duration,
            fingerprint=chromaprint
        )
        
        # 3. Confidence Scoring
        min_confidence = 100.0
        reasoning_parts = []
        for loser in losers:
            candidate_et = EchosyncTrack(
                raw_title=loser.title,
                title=loser.title,
                artist_name=loser.artist.name if loser.artist else None,
                album_title=loser.album.title if loser.album else None,
                duration=loser.duration,
                fingerprint=chromaprint
            )
            match_res = engine.calculate_match(source_et, candidate_et)
            if match_res.confidence_score < min_confidence:
                min_confidence = match_res.confidence_score
            reasoning_parts.append(f"T{loser.id} score: {match_res.confidence_score:.1f}%")

        final_score = min_confidence

        if 80.0 <= final_score < 95.0:
            # The Grey Area Check
            from core.nexus_framework.plugin_loader import PluginRegistry
            mb_plugin = PluginRegistry.create_instance('musicbrainz')
            if mb_plugin:
                mbids = []
                for t in verified_tracks:
                    if getattr(t, 'musicbrainz_id', None):
                        mbids.append(t.musicbrainz_id)
                
                if mbids:
                    mb_data = mb_plugin.get_metadata_batch(mbids)
                    if mb_data:
                        from rapidfuzz import fuzz
                        best_alignment = 0
                        for t in verified_tracks:
                            mb_record = mb_data.get(getattr(t, 'musicbrainz_id', ''))
                            if mb_record:
                                mb_title = mb_record.get('title') or ''
                                mb_album = mb_record.get('album') or ''
                                loc_title = t.title or ''
                                loc_album = t.album.title if t.album else ''
                                score = (fuzz.ratio(mb_title.lower(), loc_title.lower()) + fuzz.ratio(mb_album.lower(), loc_album.lower())) / 2
                                if score > best_alignment:
                                    best_alignment = score
                        
                        if best_alignment > 85.0:
                            final_score += 5.0
                            reasoning_parts.append("MusicBrainz sanity check added +5.0 confidence.")

        requires_manual_review = False
        if final_score < 95.0:
            requires_manual_review = True

        # 4. Payload Generation
        return {
            'event_type': 'system_duplicate',
            'keep_id': winner.id,
            'delete_ids': [t.id for t in losers],
            'confidence_score': final_score,
            'requires_manual_review': requires_manual_review,
            'reason': f"Auto-resolved system duplicate. Confidence: {final_score:.1f}%. Details: {', '.join(reasoning_parts)}"
        }

    def _serialize_track(self, track: Track) -> Dict:
        return {
            "id": track.id,
            "title": track.title,
            "artist": track.artist.name,
            "album": track.album.title if track.album else "",
            "bitrate": track.bitrate,
            "sample_rate": track.sample_rate,
            "file_size": track.file_size_bytes,
            "path": track.file_path,
            "format": track.file_format
        }

    def resolve_conflict(self, keep_id: int, delete_ids: List[int]) -> Dict[str, Any]:
        """
        Constructs and returns a proposed action dictionary for resolving a conflict,
        without executing physical file deletions.
        """
        actual_delete_ids = [tid for tid in delete_ids if tid != keep_id]
        
        return {
            'event_type': 'system_duplicate',
            'keep_id': keep_id,
            'delete_ids': actual_delete_ids,
            'reason': 'Auto-resolved system duplicate based on quality profile.'
        }

    def run_prune_job(self) -> Dict[str, Any]:
        """
        Execute the auto-deletion logic. (Now returns proposed actions without deleting)
        """
        duplicates = self.find_duplicates()
        auto_resolve_groups = duplicates['auto_resolve']

        logger.info(f"Starting Prune Job. Found {len(auto_resolve_groups)} groups to auto-resolve.")

        count = 0
        details = []

        for action in auto_resolve_groups:
            if action and action.get('delete_ids'):
                count += len(action['delete_ids'])
                details.append({
                    "kept_id": action['keep_id'],
                    "deleted_count": len(action['delete_ids']),
                    "proposed_action": action
                })
                # AutoImporter emits to event_bus natively; here we'd optionally emit
                # event_bus.publish("system_duplicate", action)

        logger.info(f"Prune Job Completed. Staged {count} tracks for deletion.")
        return {"deleted_count": count, "details": details}

    def analyze_single_track(self, track_id: int) -> Optional[Dict]:
        """
        Targeted scan for a single track's duplicate group.
        """
        try:
            with self.db.session_scope() as session:
                fp = session.query(AudioFingerprint).filter_by(track_id=track_id).first()
                if not fp or not fp.chromaprint:
                    return None

                fingerprints = session.query(AudioFingerprint).filter_by(chromaprint=fp.chromaprint).all()
                if len(fingerprints) < 2:
                    return None

                peer_track_ids = [f.track_id for f in fingerprints]
                
                from sqlalchemy.orm import joinedload
                tracks = (
                    session.query(Track)
                    .options(joinedload(Track.artist), joinedload(Track.album))
                    .join(Artist)
                    .filter(Track.id.in_(peer_track_ids))
                    .all()
                )

                if len(tracks) < 2:
                    return None

                return self._analyze_group(tracks, fp.chromaprint)
        except Exception as e:
            logger.error(f"Error analyzing single track {track_id}: {e}", exc_info=True)
            return None

    def _resolve_track_by_sync_id(self, sync_id: str) -> Optional[Track]:
        """Resolve a DB track from deterministic sync_id formats."""
        base_sync_id = (sync_id or "").split("?")[0]

        with self.db.session_scope() as session:
            return session.query(Track).filter_by(sync_id=base_sync_id).first()

    def queue_quality_upgrade_for_sync_id(
        self,
        sync_id: str,
        upgrade_quality_profile_id: Optional[str] = None,
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
            upgrade_quality_profile_id = manager_config.get("upgrade_quality_profile_id")

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
        return dm.queue_download(echo_track, quality_profile_id=upgrade_quality_profile_id)

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
        from database.working_database import get_working_database, PlaybackHistory
        from time_utils import utc_now
        from datetime import timedelta

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

    def scan_for_stale_tracks(self, inactive_days: int = 90) -> Dict[str, Any]:
        """
        Scan for tracks with > 0 all-time listens but 0 listens in the last X days.
        Updates their UserTrackState lifecycle_action to 'STALE'.
        """
        from core.suggestion_engine.analytics import PlaybackAnalytics
        from database.working_database import get_working_database, UserTrackState
        from database.music_database import ExternalIdentifier
        from time_utils import utc_now

        logger.info(f"Starting stale track scan (inactive_days={inactive_days})")

        stale_provider_ids = PlaybackAnalytics.get_stale_provider_ids(inactive_days=inactive_days)
        if not stale_provider_ids:
            return {"status": "no_stale_tracks", "count": 0}

        working_db = get_working_database()
        now = utc_now()
        updated_count = 0

        with self.db.session_scope() as music_session:
            with working_db.session_scope() as work_session:
                # Find corresponding track IDs
                from sqlalchemy.orm import joinedload
                ext_idents = music_session.query(ExternalIdentifier, Track).options(
                    joinedload(Track.artist)
                ).join(
                    Track, ExternalIdentifier.track_id == Track.id
                ).filter(
                    ExternalIdentifier.provider_item_id.in_(stale_provider_ids)
                ).yield_per(1000)

                for ext, track in ext_idents:
                    # Resolve to sync_id
                    sync_id = track.sync_id

                    states = work_session.query(UserTrackState).filter(
                        UserTrackState.sync_id == sync_id
                    ).yield_per(1000)

                    for state in states:
                        # Only mark stale if it's not already staged for deletion/upgrade or exempt
                        if not state.lifecycle_action and not state.admin_exempt_deletion:
                            state.lifecycle_action = 'STALE'
                            state.lifecycle_queued_at = now
                            updated_count += 1
                            logger.info(f"Marked track '{track.title}' (sync_id: {sync_id}) as STALE.")

        logger.info(f"Stale track scan completed. Marked {updated_count} states as STALE.")
        return {"status": "success", "count": updated_count}
