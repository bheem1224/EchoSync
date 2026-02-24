from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy import func
from database.music_database import get_database, Track, AudioFingerprint, Artist
from core.tiered_logger import get_logger
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
                # subquery: select fingerprint_hash from audio_fingerprints group by fingerprint_hash having count(*) > 1

                subquery = (
                    session.query(AudioFingerprint.fingerprint_hash)
                    .group_by(AudioFingerprint.fingerprint_hash)
                    .having(func.count(AudioFingerprint.id) > 1)
                )

                # Get the fingerprints
                duplicate_hashes = [row[0] for row in subquery.all()]

                for fp_hash in duplicate_hashes:
                    # Get all tracks for this fingerprint
                    fingerprints = (
                        session.query(AudioFingerprint)
                        .filter(AudioFingerprint.fingerprint_hash == fp_hash)
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

    def _analyze_group(self, tracks: List[Track], fingerprint_hash: str) -> Dict:
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
                "fingerprint_hash": fingerprint_hash,
                "keep": self._serialize_track(winner),
                "delete": [self._serialize_track(t) for t in losers]
            }
        else:
            # Scenario B: Manual Review
            return {
                "type": "manual_review",
                "fingerprint_hash": fingerprint_hash,
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
                        logger.error(f"Failed to delete file {track.file_path}: {e}")
                        # If file deletion fails, we proceed to remove from DB?
                        # This avoids "ghost" tracks.
                        pass

                # Delete from DB
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
