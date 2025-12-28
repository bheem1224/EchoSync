"""
Spotify ProviderAdapter implementation.

Creates Track stubs from Spotify playlists and saved tracks,
attaches ProviderRef, and progressively enriches available fields.

Adapters NEVER own data; all operations go through MusicDatabase.
"""

from typing import List, Optional, Dict, Any
from utils.logging_config import get_logger
from core.provider_adapter import ProviderAdapter
from core.models import ProviderType, Track
from database.music_database import get_database

logger = get_logger("spotify_adapter")

class SpotifyAdapter(ProviderAdapter):
    def __init__(self, spotify_client=None):
        db = get_database()
        super().__init__(db=db, provider_type=ProviderType.SPOTIFY)
        self.spotify = spotify_client

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
        """Create Track stubs for each Spotify track in a playlist."""
        if not self.spotify:
            logger.warning("Spotify client not provided; cannot ingest playlist")
            return []
        playlist = self.spotify.get_playlist_by_id(playlist_id)
        if not playlist:
            return []
        created: List[Track] = []
        for sp_track in playlist.tracks:
            initial = {
                "title": sp_track.name,
                "artists": sp_track.artists,
                "album": sp_track.album,
                "duration_ms": sp_track.duration_ms,
            }
            track_id = self.create_stub(provider_id=sp_track.id, **initial)
            # Try to enrich with ISRC from detailed track info
            details = self.spotify.get_track_details(sp_track.id)
            isrc = None
            try:
                if details and details.get("raw_data"):
                    isrc = details["raw_data"].get("external_ids", {}).get("isrc")
            except Exception:
                isrc = None
            if isrc:
                self.enrich_track(track_id, isrc=isrc)
            created_track = self.db.get_track(track_id)
            if created_track:
                created.append(created_track)
        logger.info(f"Ingested {len(created)} tracks from Spotify playlist {playlist_id}")
        return created

    def ingest_saved_tracks(self, limit: Optional[int] = None) -> List[Track]:
        """Create Track stubs from user's saved tracks."""
        if not self.spotify:
            logger.warning("Spotify client not provided; cannot ingest saved tracks")
            return []
        saved = self.spotify.get_saved_tracks()
        if limit is not None:
            saved = saved[:limit]
        created: List[Track] = []
        for sp_track in saved:
            initial = {
                "title": sp_track.name,
                "artists": sp_track.artists,
                "album": sp_track.album,
                "duration_ms": sp_track.duration_ms,
            }
            track_id = self.create_stub(provider_id=sp_track.id, **initial)
            details = self.spotify.get_track_details(sp_track.id)
            isrc = None
            try:
                if details and details.get("raw_data"):
                    isrc = details["raw_data"].get("external_ids", {}).get("isrc")
            except Exception:
                isrc = None
            if isrc:
                self.enrich_track(track_id, isrc=isrc)
            created_track = self.db.get_track(track_id)
            if created_track:
                created.append(created_track)
        logger.info(f"Ingested {len(created)} saved tracks from Spotify")
        return created

# Register adapter in plugin system (declaration only; instance created by services)
try:
    from core.plugin_system import PluginType, PluginScope, PluginDeclaration, register_plugin
    decl = PluginDeclaration(
        name="spotify_adapter",
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
        description="Spotify Adapter providing Track stubs and enrichment",
        author="SoulSync",
        priority=100,
    )
    register_plugin(decl)
except Exception as e:
    logger.debug(f"Plugin declaration for spotify_adapter deferred: {e}")
