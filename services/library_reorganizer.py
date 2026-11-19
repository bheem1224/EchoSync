import os
from pathlib import Path
from typing import Any

from core.event_bus import event_bus
from core.io_gatekeeper import Gatekeeper
from core.path_formatter import (
    build_destination_path,
    get_library_preferences,
    get_prefer_canonical_studio_album,
    get_singles_pattern,
)
from core.tiered_logger import get_logger
from database import music_database as _music_db_module
from database.music_database import Track
from database.music_database import get_database as _orig_get_database
from services.metadata_enhancer import (
    MetadataEnhancerService,
    normalize_singles_metadata,
)

get_database = _orig_get_database

logger = get_logger("services.library_reorganizer")


def _resolve_music_database():
    """Resolve active MusicDatabase, honoring monkeypatches on either module."""
    if get_database is not _orig_get_database:
        return get_database()
    return _music_db_module.get_database()


class LibraryReorganizerService:
    def __init__(self, db=None):
        self.db = db if db is not None else _resolve_music_database()
        pref_lib, _ = get_library_preferences()
        self.library_root = Path(pref_lib) if pref_lib else None
        self.enhancer = MetadataEnhancerService()

    def _sanitize(self, filename: str) -> str:
        """Sanitize filename components"""
        import re

        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", filename).strip()

    def reorganize_library(self, track_ids: list[int] | None = None, progress_callback=None):
        pref_lib, pattern = get_library_preferences()
        if not self.library_root and pref_lib:
            self.library_root = Path(pref_lib)

        if not self.library_root:
            logger.error("Cannot reorganize library: library_dir is not configured.")
            return

        singles_pattern = get_singles_pattern()
        prefer_canonical_studio = get_prefer_canonical_studio_album()

        if track_ids:
            target_track_ids = list(track_ids)
        else:
            with self.db.session_scope() as session:
                target_track_ids = [
                    row[0] for row in session.query(Track.id).order_by(Track.id.asc()).all()
                ]

        total_tracks = len(target_track_ids)
        from services.library_watcher import suppress_path

        for index, tid in enumerate(target_track_ids):
            if progress_callback:
                progress_callback(index + 1, total_tracks, "Reorganizing library tracks...")

            try:
                with self.db.session_scope() as session:
                    track = session.query(Track).filter(Track.id == tid).first()
                    if not track:
                        continue

                    for media in list(track.media_files):
                        if not media.file_path or not os.path.exists(media.file_path):
                            logger.warning(
                                f"Skipping media {media.id} for track {track.id}: file missing at {media.file_path}"
                            )
                            continue

                        raw_artist = track.artist.name if track.artist else "Unknown Artist"
                        raw_album = track.album.title if track.album else "Unknown Album"

                        # ----------------------------------------------------
                        # Orphan Review Check: Missing core metadata
                        # Established library tracks must NEVER be ejected to /data/downloads.
                        # ----------------------------------------------------
                        if raw_artist.lower() == "unknown artist" or raw_album.lower() == "unknown album":
                            logger.warning(
                                f"Library track {track.id} (media {media.id}) missing core metadata: {media.file_path}. "
                                "Enrolling in ReviewTask(action='RESOLVE_LIBRARY_ORPHAN') without destructive ejection."
                            )
                            from database.repositories.task_repository import TaskRepository

                            TaskRepository.create_review_task(
                                file_path=media.file_path,
                                action="RESOLVE_LIBRARY_ORPHAN",
                                track_id=track.id,
                                media_id=media.id,
                                track_data={
                                    "action": "RESOLVE_LIBRARY_ORPHAN",
                                    "title": track.title,
                                    "artist": raw_artist,
                                    "album": raw_album,
                                    "track_id": track.id,
                                    "media_id": media.id,
                                },
                            )
                            continue

                        current_path = Path(media.file_path)
                        ext = current_path.suffix.lower().lstrip(".")

                        # Build track metadata dictionary for normalization & path computation
                        album_artist = ""
                        if track.album and track.album.artist:
                            album_artist = track.album.artist.name
                        elif track.artist and track.artist.parent_artist:
                            album_artist = track.artist.parent_artist.name
                        elif track.artist:
                            album_artist = track.artist.name

                        track_meta: dict[str, Any] = {
                            "title": track.title,
                            "artist": track.artist.name if track.artist else "",
                            "album": track.album.title if track.album else "",
                            "album_artist": album_artist,
                            "albumartist": album_artist,
                            "track_number": track.track_number,
                            "disc_number": track.disc_number,
                            "year": str(track.album.release_date)[:4]
                            if (track.album and track.album.release_date)
                            else "",
                            "release_year": str(track.album.release_date)[:4]
                            if (track.album and track.album.release_date)
                            else "",
                            "isrc": track.isrc or "",
                            "musicbrainz_track_id": track.musicbrainz_id or "",
                            "musicbrainz_album_id": track.album.mb_release_id if track.album else "",
                            "musicbrainz_release_group_id": track.album.release_group_id if track.album else "",
                            "release_type": track.release_type or "album",
                        }

                        # Read tags from physical file if present to catch existing repack_source or tags
                        file_tags = {}
                        try:
                            import echosync_core

                            if hasattr(echosync_core, "read_metadata"):
                                file_tags = echosync_core.read_metadata(str(current_path)) or {}
                            else:
                                file_tags = echosync_core.extract_metadata(str(current_path)) or {}
                        except Exception:
                            pass

                        if file_tags.get("repack_source"):
                            track_meta["repack_source"] = file_tags["repack_source"]
                        if file_tags.get("repack_release_mbid"):
                            track_meta["repack_release_mbid"] = file_tags["repack_release_mbid"]

                        from database.config_database import get_config_database

                        group_singles = bool(
                            get_config_database().get_system_setting(
                                "metadata_enhancement.group_standalone_singles", True
                            )
                        )

                        # Singles normalization
                        track_meta = normalize_singles_metadata(
                            track_meta, group_standalone_singles=group_singles
                        )
                        if track_meta.get("is_single"):
                            track.release_type = "single"

                        # Repack realignment if enabled and track is from a compilation repack
                        realigned = False
                        if prefer_canonical_studio and track_meta.get("repack_source"):
                            realigned = True
                            if track_meta.get("album") and track.album:
                                track.album.title = track_meta["album"]
                            if track_meta.get("musicbrainz_album_id") and track.album:
                                track.album.mb_release_id = track_meta["musicbrainz_album_id"]
                            if track_meta.get("musicbrainz_release_group_id") and track.album:
                                track.album.release_group_id = track_meta["musicbrainz_release_group_id"]

                        # Compute ideal path using canonical path formatter
                        ideal_absolute_path = build_destination_path(
                            base_library_path=str(self.library_root),
                            pattern=pattern,
                            meta=track_meta,
                            ext=ext,
                            singles_pattern=singles_pattern,
                        )

                        # If already in the ideal path and not realigned, skip
                        if current_path.resolve() == ideal_absolute_path.resolve() and not realigned:
                            continue

                        # If metadata was altered or realigned, re-tag audio file with roundtrip verification before moving
                        if realigned or track_meta.get("is_single"):
                            try:
                                with suppress_path(str(current_path)):
                                    self.enhancer.tag_file_verified(current_path, track_meta)
                            except Exception as tag_err:
                                logger.warning(
                                    f"tag_file_verified failed during reorganizing {current_path.name}: {tag_err}"
                                )

                        # The Move & Collision Handle
                        dest_path = ideal_absolute_path
                        parent = dest_path.parent
                        parent.mkdir(parents=True, exist_ok=True)

                        collision_occurred = False
                        if self._reorg_collides(session, dest_path, current_path, media.id):
                            collision_occurred = True
                            counter = 1
                            stem = dest_path.stem
                            ext_with_dot = dest_path.suffix

                            while self._reorg_collides(session, dest_path, current_path, media.id):
                                dest_path = parent / f"{stem} ({counter}){ext_with_dot}"
                                counter += 1

                        if dest_path.resolve() != current_path.resolve():
                            try:
                                with suppress_path(str(current_path)), suppress_path(str(dest_path)):
                                    Gatekeeper.authorize_and_execute(
                                        {
                                            "operation": "safe_move",
                                            "src": str(current_path),
                                            "dst": str(dest_path),
                                        }
                                    )
                                logger.info(f"Reorganized: {current_path} -> {dest_path}")
                            except Exception as e:
                                logger.error(f"Failed to move {current_path} to {dest_path}: {e}")
                                continue

                            # Database Update (committed per track upon exiting session_scope)
                            media.file_path = str(dest_path)
                            try:
                                st = dest_path.stat()
                                media.mtime = st.st_mtime
                                media.file_size_bytes = st.st_size
                            except OSError:
                                pass

                            # Cleanup old directory
                            self._cleanup_empty_directories(current_path.parent)

                        session.add(media)
                        session.add(track)

                        if collision_occurred:
                            event_bus.publish(
                                "duplicate_file_staged",
                                {
                                    "track_id": track.id,
                                    "media_id": media.id,
                                    "file_path": str(dest_path),
                                    "original_path": str(current_path),
                                    "reason": "Collision during library reorganization.",
                                },
                            )
            except Exception as track_err:
                logger.error(
                    f"Failed reorganizing track {tid}: {track_err}", exc_info=True
                )

    @staticmethod
    def _reorg_collides(session, candidate: Path, current_path: Path, media_id: int) -> bool:
        """Check disk and LocalMedia DB collisions without triggering autoflush."""
        from sqlalchemy import or_

        from database import _canonicalize_path
        from database.music_database import LocalMedia

        if candidate.exists() and candidate.resolve() != current_path.resolve():
            return True
        with session.no_autoflush:
            canon = _canonicalize_path(str(candidate))
            return (
                session.query(LocalMedia)
                .filter(
                    LocalMedia.id != media_id,
                    or_(
                        LocalMedia.file_path == canon,
                        LocalMedia.file_path == str(candidate),
                    ),
                )
                .first()
                is not None
            )

    def _cleanup_empty_directories(self, directory: Path):
        """Recursively remove empty directories."""
        try:
            if not directory.exists() or not directory.is_dir():
                return
            if self.library_root and directory.resolve() == self.library_root.resolve():
                return
            if not any(directory.iterdir()):
                directory.rmdir()
                self._cleanup_empty_directories(directory.parent)
        except Exception as e:
            logger.debug(f"Could not remove empty directory {directory}: {e}")
