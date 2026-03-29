from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy import func
from database.music_database import get_database, Track, AudioFingerprint, Artist
from core.tiered_logger import get_logger
from core.matching_engine.soul_sync_track import SoulSyncTrack
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
                duplicate_hashes = [row[0] for row in subquery.all()]

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
                    tracks = (
                        session.query(Track)
                        .join(Artist)
                        .filter(Track.id.in_(track_ids))
                        .all()
                    )

                    if len(tracks) < 2:
                        continue

                    # Analyze the group
                    scenario = self._analyze_group(tracks, fp_hash)

                    if scenario['type'] == 'auto_resolve':
                        results['auto_resolve'].append(scenario)
                    elif scenario['type'] == 'manual_review':
                        results['manual_review'].append(scenario)

        except Exception as e:
            logger.error(f"Error finding duplicates: {e}", exc_info=True)

        return results

    def _analyze_group(self, tracks: List[Track], chromaprint: str) -> Dict:
        """
        Analyze a group of duplicate tracks to determine if they can be auto-resolved.
        """
        # Check metadata consistency (Artist & Title)
        first_track = tracks[0]
        consistent_metadata = True

        # Helper to normalize strings
        def normalize(s): return (s or "").strip().lower()

        target_artist = normalize(first_track.artist.name)
        target_title = normalize(first_track.title)

        for track in tracks[1:]:
            track_artist = normalize(track.artist.name)
            track_title = normalize(track.title)

            # Simple fuzzy match or strict? Prompt said "Artist/Title match (case-insensitive)"
            if track_artist != target_artist or track_title != target_title:
                consistent_metadata = False
                break

        serialized_tracks = [self._serialize_track(t) for t in tracks]

        if consistent_metadata:
            # Scenario A: Auto-Resolve
            # Find the best quality track to keep

            # Sort tracks by quality (descending)
            # Criteria: Bitrate -> Sample Rate -> File Size
            sorted_tracks = sorted(tracks, key=lambda t: (
                t.bitrate or 0,
                t.sample_rate or 0,
                t.file_size_bytes or 0
            ), reverse=True)

            winner = sorted_tracks[0]
            losers = sorted_tracks[1:]

            return {
                "type": "auto_resolve",
                "chromaprint": chromaprint,
                "keep": self._serialize_track(winner),
                "delete": [self._serialize_track(t) for t in losers]
            }
        else:
            # Scenario B: Manual Review
            return {
                "type": "manual_review",
                "chromaprint": chromaprint,
                "tracks": serialized_tracks
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

    def resolve_conflict(self, keep_id: int, delete_ids: List[int]) -> bool:
        """
        Manually resolve a conflict by deleting specified tracks.
        """
        success = True
        for track_id in delete_ids:
            # Ensure we don't delete the keep_id (sanity check)
            if track_id == keep_id:
                logger.warning(f"Attempted to delete keep_id {keep_id}. Skipping.")
                continue

            if not self._delete_track(track_id):
                success = False
        return success

    def _delete_track(self, track_id: int) -> bool:
        """
        Delete track from DB and Filesystem.
        """
        try:
            with self.db.session_scope() as session:
                track = session.query(Track).filter(Track.id == track_id).first()
                if not track:
                    return False

                # Delete file
                if track.file_path and os.path.exists(track.file_path):
                    try:
                        os.remove(track.file_path)
                        logger.info(f"Deleted file: {track.file_path}")
                    except OSError as e:
                        logger.critical(
                            "Failed to delete physical file '%s': %s — "
                            "aborting DB removal to prevent ghost track.",
                            track.file_path,
                            e,
                        )
                        return False

                # Delete from DB — only reached when the file is confirmed deleted
                session.delete(track)
                logger.info(f"Deleted track ID {track_id} from database")
                return True
        except Exception as e:
            logger.error(f"Error deleting track {track_id}: {e}")
            return False

    def run_prune_job(self) -> Dict[str, Any]:
        """
        Execute the auto-deletion logic.
        """
        duplicates = self.find_duplicates()
        auto_resolve_groups = duplicates['auto_resolve']

        logger.info(f"Starting Prune Job. Found {len(auto_resolve_groups)} groups to auto-resolve.")

        count = 0
        details = []

        for group in auto_resolve_groups:
            # Keep the winner, delete losers
            delete_candidates = group['delete']
            delete_ids = [t['id'] for t in delete_candidates]
            keep_track = group['keep']

            logger.info(f"Pruning group: Keeping '{keep_track['title']}' (ID: {keep_track['id']}), Deleting {len(delete_ids)} duplicates.")

            if self.resolve_conflict(keep_track['id'], delete_ids):
                count += len(delete_ids)
                details.append({
                    "kept": keep_track['title'],
                    "deleted_count": len(delete_ids)
                })

        logger.info(f"Prune Job Completed. Deleted {count} tracks.")
        return {"deleted_count": count, "details": details}

    def _resolve_track_by_sync_id(self, sync_id: str) -> Optional[Track]:
        """Resolve a DB track from deterministic sync_id formats."""
        base_sync_id = (sync_id or "").split("?")[0]

        with self.db.session_scope() as session:
            if base_sync_id.startswith("ss:track:mbid:"):
                mbid = base_sync_id.split("ss:track:mbid:", 1)[1]
                if not mbid:
                    return None
                return session.query(Track).filter(Track.musicbrainz_id == mbid).first()

            if base_sync_id.startswith("ss:track:meta:"):
                encoded = base_sync_id.split("ss:track:meta:", 1)[1]
                if not encoded:
                    return None
                try:
                    decoded = base64.b64decode(encoded.encode("ascii")).decode("utf-8")
                    artist_name, title = decoded.split("|", 1)
                except Exception:
                    return None

                return (
                    session.query(Track)
                    .join(Artist, Track.artist_id == Artist.id)
                    .filter(
                        func.lower(Artist.name) == artist_name.lower(),
                        func.lower(Track.title) == title.lower(),
                    )
                    .first()
                )

        return None

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

        soul_track = SoulSyncTrack(
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
        return dm.queue_download(soul_track, quality_profile_id=upgrade_quality_profile_id)

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
                ext_idents = music_session.query(ExternalIdentifier, Track).join(
                    Track, ExternalIdentifier.track_id == Track.id
                ).filter(
                    ExternalIdentifier.provider_item_id.in_(stale_provider_ids)
                ).all()

                for ext, track in ext_idents:
                    # Resolve to sync_id
                    from core.matching_engine.text_utils import generate_deterministic_id
                    sync_id = f"ss:track:meta:{generate_deterministic_id(track.artist.name, track.title)}"

                    states = work_session.query(UserTrackState).filter(
                        UserTrackState.sync_id == sync_id
                    ).all()

                    for state in states:
                        # Only mark stale if it's not already staged for deletion/upgrade or exempt
                        if not state.lifecycle_action and not state.admin_exempt_deletion:
                            state.lifecycle_action = 'STALE'
                            state.lifecycle_queued_at = now
                            updated_count += 1
                            logger.info(f"Marked track '{track.title}' (sync_id: {sync_id}) as STALE.")

        logger.info(f"Stale track scan completed. Marked {updated_count} states as STALE.")
        return {"status": "success", "count": updated_count}
