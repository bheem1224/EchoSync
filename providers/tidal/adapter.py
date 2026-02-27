"""
TIDAL ProviderAdapter implementation.

Creates Track stubs from TIDAL playlists and favorites,
attaches ProviderRef, and progressively enriches available fields.

Adapters NEVER own data; all operations go through MusicDatabase.
"""

from typing import List, Optional
from core.tiered_logger import get_logger
from core.models import ProviderType, Track
from core.storage import get_storage_service

logger = get_logger("tidal_adapter")

# TidalAdapter class deprecated - use convert_tidal_track_to_soulsync instead
class TidalAdapter:
    def __init__(self, tidal_client=None):
        storage = get_storage_service()
        db = storage.get_music_database()
        super().__init__(db=db, provider_type=ProviderType.TIDAL)
        self.tidal = tidal_client

    # Field contracts
    def get_provides_fields(self) -> List[str]:
        return [
            "title",
            "artists",
            "album",
            "duration_ms",
            "isrc",
        ]

    def get_consumes_fields(self) -> List[str]:
        # Playlist ingestion does not require prior fields
        return []

    def requires_auth(self) -> bool:
        return True

    # High-level operations
    def ingest_playlist(self, playlist_id: str) -> List[Track]:
        """Create Track stubs for each TIDAL track in a playlist."""
        if not self.tidal:
            logger.warning("Tidal client not provided; cannot ingest playlist")
            return []
        playlist = getattr(self.tidal, "get_playlist_by_id", None)
        if not playlist:
            logger.warning("Tidal client missing get_playlist_by_id")
            return []
        playlist = self.tidal.get_playlist_by_id(playlist_id)
        if not playlist:
            return []
        created: List[Track] = []
        for td_track in getattr(playlist, "tracks", []):
            initial = {
                "title": getattr(td_track, "name", None),
                "artists": getattr(td_track, "artists", []),
                "album": getattr(td_track, "album", None),
                "duration_ms": getattr(td_track, "duration_ms", None),
            }
            provider_id = str(getattr(td_track, "id", ""))
            track_id = self.create_stub(provider_id=provider_id, **initial)
            # Try to enrich with ISRC if available
            isrc = None
            try:
                details = getattr(self.tidal, "get_track_details", None)
                if details:
                    info = self.tidal.get_track_details(provider_id)
                    raw = (info or {}).get("raw_data") or {}
                    isrc = raw.get("isrc")
            except Exception:
                isrc = None
            if isrc:
                self.enrich_track(track_id, isrc=isrc)
            created_track = self.db.get_track(track_id)
            if created_track:
                created.append(created_track)
        logger.info(f"Ingested {len(created)} tracks from TIDAL playlist {playlist_id}")
        return created

    def ingest_favorites(self, limit: Optional[int] = None) -> List[Track]:
        """Create Track stubs from user's TIDAL favorites/saved tracks."""
        if not self.tidal:
            logger.warning("Tidal client not provided; cannot ingest favorites")
            return []
        getter = getattr(self.tidal, "get_saved_tracks", None)
        if not getter:
            logger.warning("Tidal client missing get_saved_tracks")
            return []
        saved = self.tidal.get_saved_tracks() or []
        if limit is not None:
            saved = saved[:limit]
        created: List[Track] = []
        for td_track in saved:
            initial = {
                "title": getattr(td_track, "name", None),
                "artists": getattr(td_track, "artists", []),
                "album": getattr(td_track, "album", None),
                "duration_ms": getattr(td_track, "duration_ms", None),
            }
            provider_id = str(getattr(td_track, "id", ""))
            track_id = self.create_stub(provider_id=provider_id, **initial)
            isrc = None
            try:
                details = getattr(self.tidal, "get_track_details", None)
                if details:
                    info = self.tidal.get_track_details(provider_id)
                    raw = (info or {}).get("raw_data") or {}
                    isrc = raw.get("isrc")
            except Exception:
                isrc = None
            if isrc:
                self.enrich_track(track_id, isrc=isrc)
            created_track = self.db.get_track(track_id)
            if created_track:
                created.append(created_track)
        logger.info(f"Ingested {len(created)} favorite tracks from TIDAL")
        return created

# Register adapter in plugin system (declaration only; instance created by services)
try:
    from plugins.plugin_system import PluginType, PluginScope, PluginDeclaration, register_plugin
    decl = PluginDeclaration(
        name="tidal_adapter",
        plugin_type=PluginType.PLAYLIST_PROVIDER,
        provides_fields=["title", "artists", "album", "duration_ms", "isrc"],
        consumes_fields=[],
        requires_auth=True,
        supports_streaming=True,
        supports_downloads=False,
        supports_library_scan=False,
        supports_cover_art=True,
        supports_lyrics=False,
        # Legacy capabilities for compatibility
        provides=[
            "playlist.read",
            "search.tracks",
            "track.title",
            "track.artist",
            "track.album",
            "track.duration_ms",
        ],
        consumes=["auth.credentials"],
        scope=[PluginScope.SYNC, PluginScope.SEARCH],
        version="1.0.0",
        description="TIDAL Adapter providing Track stubs and enrichment",
        author="SoulSync",
        priority=90,
    )
    register_plugin(decl)
except Exception as e:
    logger.debug(f"Plugin declaration for tidal_adapter deferred: {e}")
