"""Library adapter for summarizing library servers and canonical tracks."""

from typing import Dict, List
import os
from pathlib import Path
from core.settings import config_manager
from core.provider import ProviderRegistry, get_provider_capabilities, MetadataRichness
from database.music_database import get_database
from core.tiered_logger import get_logger

logger = get_logger("library_service")


def _metadata_completeness(richness: str) -> str:
    mapping = {
        'LOW': 'partial',
        'MEDIUM': 'standard',
        'HIGH': 'complete',
    }
    return mapping.get(richness, 'unknown')


def _get_database_size_mb() -> float:
    """Get the size of the Echosync music database in MB."""
    try:
        db_path = config_manager.get('media_database_path') or Path(__file__).parent.parent.parent / 'config' / 'media_library.db'
        if isinstance(db_path, str):
            db_path = Path(db_path)
        if db_path.exists():
            size_bytes = db_path.stat().st_size
            return round(size_bytes / (1024 * 1024), 2)
    except Exception as e:
        logger.warning(f"Could not get database size: {e}")
    return 0.0


class LibraryAdapter:
    def overview(self) -> Dict:
        """Summarize available library servers and canonical tracks.

        Returns:
            dict: servers, stats, tracks, artists, albums
        """
        servers: List[Dict] = []
        provider_artists = 0
        provider_albums = 0
        provider_tracks = 0
        
        # Get the active media server
        active_server = config_manager.get('active_media_server', 'plex')
        
        # Get all media server providers
        provider_names = ProviderRegistry.list_providers()
        
        for provider_name in provider_names:
            # skip disabled providers entirely; they shouldn't count toward
            # servers or be instantiated for stats
            if ProviderRegistry.is_provider_disabled(provider_name):
                logger.debug(f"Skipping disabled provider in library overview: {provider_name}")
                continue

            try:
                caps = get_provider_capabilities(provider_name)
                
                # Skip if not a library/media server provider
                if not caps.supports_library_scan:
                    continue
                
                richness = caps.metadata.name
                is_active = (provider_name == active_server)
                
                # Try to get library stats from the provider if it's active
                track_count = 0
                artist_count = 0
                album_count = 0
                
                if is_active:
                    try:
                        # only instantiate active provider (and it's not disabled)
                        provider = ProviderRegistry.create_instance(provider_name)
                        if provider and hasattr(provider, 'ensure_connection') and hasattr(provider, 'get_library_stats'):
                            if provider.ensure_connection():
                                stats = provider.get_library_stats()
                                track_count = stats.get('tracks', 0)
                                artist_count = stats.get('artists', 0)
                                album_count = stats.get('albums', 0)
                                
                                # Store provider stats separately
                                provider_tracks = track_count
                                provider_artists = artist_count
                                provider_albums = album_count
                    except Exception as e:
                        logger.error(f"Error getting stats from {provider_name}: {e}")
                
                servers.append({
                    "name": provider_name,
                    "type": "media_server",
                    "metadata_richness": richness,
                    "track_count": track_count,
                    "artist_count": artist_count,
                    "album_count": album_count,
                    "is_active": is_active,
                })
                
            except Exception as e:
                logger.error(f"Error processing provider {provider_name}: {e}")
                continue

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

            logger.debug(f"Database stats retrieved: {db_tracks} tracks, {db_artists} artists, {db_albums} albums")
        except Exception as e:
            logger.error(f"Error getting database stats: {e}", exc_info=True)
            db_artists = 0
            db_albums = 0
            db_tracks = 0

        tracks = []
        artists = []
        albums = []
        
        # Stats should reflect what's actually in the Echosync database
        stats = {
            "synced_tracks": db_tracks,
            "synced_artists": db_artists,
            "synced_albums": db_albums,
            "total_tracks": provider_tracks,  # Available in source provider
            "total_artists": provider_artists,
            "total_albums": provider_albums,
            "database_size_mb": db_size_mb,
        }

        return {
            "servers": servers,
            "stats": stats,
            "tracks": tracks,
            "artists": artists,
            "albums": albums,
        }

