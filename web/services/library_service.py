"""Library adapter for summarizing library servers and canonical tracks."""

from pathlib import Path

from core.settings import config_manager
from core.tiered_logger import get_logger
from database.music_database import get_database

logger = get_logger("library_service")


def _get_database_size_mb() -> float:
    """Get the size of the Echosync music database in MB."""
    try:
        db_path = (
            config_manager.get("media_database_path")
            or Path(__file__).parent.parent.parent / "config" / "media_library.db"
        )
        if isinstance(db_path, str):
            db_path = Path(db_path)
        if db_path.exists():
            size_bytes = db_path.stat().st_size
            return round(size_bytes / (1024 * 1024), 2)
    except Exception as e:
        logger.warning(f"Could not get database size: {e}")
    return 0.0


class LibraryAdapter:
    def overview(self) -> dict:
        """Summarize available library servers and canonical tracks.

        Returns:
            dict: servers, stats, tracks, artists, albums
        """
        # Get actual database stats (what's been synced to Echosync database)
        db_tracks = 0
        db_artists = 0
        db_albums = 0
        db_size_mb = _get_database_size_mb()

        try:
            # Force fresh database counts
            db = get_database()
            # Explicitly log to verify query execution
            logger.debug("Fetching fresh database stats...")

            db_artists = db.count_artists()
            db_albums = db.count_albums()
            db_tracks = db.count_tracks()

            logger.debug(
                f"Database stats retrieved: {db_tracks} tracks, {db_artists} artists, {db_albums} albums"
            )
        except Exception as e:
            logger.error(f"Error getting database stats: {e}", exc_info=True)

        active_server = config_manager.get("active_media_server", "plex")

        servers = [
            {
                "name": active_server,
                "type": "media_server",
                "metadata_richness": "standard",
                "track_count": db_tracks,
                "artist_count": db_artists,
                "album_count": db_albums,
                "is_active": True,
            }
        ]

        tracks = []
        artists = []
        albums = []

        # Stats reflect what's actually in the Echosync database
        stats = {
            "synced_tracks": db_tracks,
            "synced_artists": db_artists,
            "synced_albums": db_albums,
            "total_tracks": db_tracks,
            "total_artists": db_artists,
            "total_albums": db_albums,
            "database_size_mb": db_size_mb,
        }

        return {
            "servers": servers,
            "stats": stats,
            "tracks": tracks,
            "artists": artists,
            "albums": albums,
        }
