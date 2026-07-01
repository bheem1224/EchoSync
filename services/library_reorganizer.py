import os
import shutil
from pathlib import Path
from typing import List, Optional

from database.music_database import get_database, Track
from core.settings import config_manager
from core.tiered_logger import get_logger
from core.file_handling.path_mapper import extract_primary_artist
from core.event_bus import event_bus

logger = get_logger("services.library_reorganizer")

class LibraryReorganizerService:
    def __init__(self):
        self.db = get_database()
        _lib = config_manager.get('storage.library_dir') or config_manager.get('library_dir')
        if _lib:
            self.library_root = Path(_lib)
        else:
            self.library_root = None

    def _sanitize(self, filename: str) -> str:
        """Sanitize filename components"""
        import re
        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename).strip()

    def reorganize_library(self, track_ids: Optional[List[int]] = None, progress_callback=None):
        if not self.library_root:
            logger.error("Cannot reorganize library: library_dir is not configured.")
            return

        meta_config = config_manager.get('metadata_enhancement') or {}
        template = meta_config.get('naming_template', "{Artist}/{Album}/{Track} - {Title}.{ext}")

        with self.db.session_scope() as session:
            query = session.query(Track)
            if track_ids:
                query = query.filter(Track.id.in_(track_ids))

            tracks = query.all()
            total_tracks = len(tracks)

            for index, track in enumerate(tracks):
                if progress_callback:
                    progress_callback(index + 1, total_tracks, "Moving files...")

                for media in track.media_files:
                    if not media.file_path or not os.path.exists(media.file_path):
                        logger.warning(f"Skipping media {media.id} for track {track.id}: file missing at {media.file_path}")
                        continue

                    raw_artist = track.artist.name if track.artist else "Unknown Artist"
                    raw_album = track.album.title if track.album else "Unknown Album"

                    # ----------------------------------------------------
                    # Quarantine Check: Missing core metadata
                    # ----------------------------------------------------
                    if raw_artist.lower() == "unknown artist" or raw_album.lower() == "unknown album":
                        quarantine_dir = Path("/data/downloads/poor_metadata")
                        os.makedirs(quarantine_dir, exist_ok=True)
                        target_path = quarantine_dir / os.path.basename(media.file_path)

                        shutil.move(media.file_path, target_path)
                        logger.warning(f"Ejected media {media.id} to quarantine staging due to missing tags: {media.file_path}")

                        session.delete(media)
                        continue

                    # Prepare tokens
                    raw_artist = track.artist.name if track.artist else "Unknown Artist"
                    primary_artist = extract_primary_artist(raw_artist)
                    artist = self._sanitize(primary_artist)

                    album = self._sanitize(track.album.title if track.album else "Unknown Album")
                    title = self._sanitize(track.title or Path(media.file_path).stem)

                    track_num = track.track_number
                    track_padded = "00"
                    if track_num is not None:
                        try:
                            _t = str(track_num).split('/')[0].strip()
                            track_padded = f"{int(_t):02d}"
                        except ValueError:
                            track_padded = "00"

                    year_str = str(track.album.release_date)[:4] if track.album and track.album.release_date else "0000"
                    
                    ext = Path(media.file_path).suffix.lower().lstrip('.')

                    # Replace tokens
                    new_name = template.replace("{Artist}", artist)\
                                       .replace("{Album}", album)\
                                       .replace("{Track}", track_padded)\
                                       .replace("{Title}", title)\
                                       .replace("{Year}", year_str)\
                                       .replace("{Format}", ext)\
                                       .replace("{ext}", ext)

                    rel_path = Path(new_name)
                    ideal_absolute_path = self.library_root / rel_path

                    current_path = Path(media.file_path)
                    if current_path.resolve() == ideal_absolute_path.resolve():
                        continue

                    # The Move & Collision Handle
                    dest_path = ideal_absolute_path
                    parent = dest_path.parent
                    parent.mkdir(parents=True, exist_ok=True)

                    collision_occurred = False
                    if dest_path.exists() and dest_path.resolve() != current_path.resolve():
                        collision_occurred = True
                        counter = 1
                        stem = dest_path.stem
                        ext_with_dot = dest_path.suffix

                        while dest_path.exists() and dest_path.resolve() != current_path.resolve():
                            dest_path = parent / f"{stem} ({counter}){ext_with_dot}"
                            counter += 1

                    try:
                        shutil.move(str(current_path), str(dest_path))
                        logger.info(f"Reorganized: {current_path} -> {dest_path}")
                    except Exception as e:
                        logger.error(f"Failed to move {current_path} to {dest_path}: {e}")
                        continue

                    # Database Update
                    media.file_path = str(dest_path)
                    session.add(media)

                    if collision_occurred:
                        event_bus.publish("duplicate_file_staged", {
                            "track_id": track.id,
                            "media_id": media.id,
                            "file_path": str(dest_path),
                            "original_path": str(current_path),
                            "reason": "Collision during library reorganization."
                        })

                    # Cleanup old directory
                    self._cleanup_empty_directories(current_path.parent)

    def _cleanup_empty_directories(self, directory: Path):
        """Recursively remove empty directories."""
        try:
            if not directory.exists() or not directory.is_dir():
                return
            if directory.resolve() == self.library_root.resolve():
                return
            if not any(directory.iterdir()):
                directory.rmdir()
                self._cleanup_empty_directories(directory.parent)
        except Exception as e:
            logger.debug(f"Could not remove empty directory {directory}: {e}")
