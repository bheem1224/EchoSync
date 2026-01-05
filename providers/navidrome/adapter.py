"""
Navidrome ProviderAdapter implementation.

Creates Track stubs from Navidrome library traversal (artists→albums→tracks),
attaches ProviderRef, and enriches basic metadata. Navidrome does not provide
local file paths, so download status remains unchanged.

Adapters NEVER own data; all operations go through MusicDatabase.
"""

from typing import List, Optional
from utils.logging_config import get_logger
from plugins.provider_adapter import ProviderAdapter
from core.models import ProviderType, Track
from sdk.storage_service import get_storage_service

logger = get_logger("navidrome_adapter")

class NavidromeAdapter(ProviderAdapter):
    def __init__(self, navidrome_client=None):
        storage = get_storage_service()
        db = storage.get_music_database()
        super().__init__(db=db, provider_type=ProviderType.NAVIDROME)
        self.navidrome = navidrome_client

    # Field contracts
    def get_provides_fields(self) -> List[str]:
        return [
            "title",
            "artists",
            "album",
            "duration_ms",
            "track_number",
            "release_year",
        ]

    def get_consumes_fields(self) -> List[str]:
        # Library ingestion does not require prior fields
        return []

    def requires_auth(self) -> bool:
        return True

    def ingest_library(self, limit: Optional[int] = None) -> List[Track]:
        """Traverse Navidrome library and create Track stubs.

        Iterates artists → albums → tracks for reasonable coverage.
        """
        created: List[Track] = []
        if not self.navidrome:
            logger.warning("Navidrome client not provided; cannot ingest library")
            return created

        try:
            artists = self.navidrome.get_all_artists() or []
            count = 0
            for artist in artists:
                albums = self.navidrome.get_albums_for_artist(getattr(artist, "ratingKey", "")) or []
                for album in albums:
                    tracks = self.navidrome.get_tracks_for_album(getattr(album, "ratingKey", "")) or []
                    for item in tracks:
                        provider_id = str(getattr(item, "ratingKey", getattr(item, "id", "")))
                        title = getattr(item, "title", None)
                        # Resolve artist/album names via helpers
                        artist_obj = None
                        album_obj = None
                        try:
                            artist_obj = item.artist()
                        except Exception:
                            artist_obj = None
                        try:
                            album_obj = item.album()
                        except Exception:
                            album_obj = None
                        artists_list = []
                        if artist_obj and getattr(artist_obj, "title", None):
                            artists_list = [getattr(artist_obj, "title")]
                        album_title = getattr(album_obj, "title", None) if album_obj else None
                        duration_ms = getattr(item, "duration", None)
                        track_number = getattr(item, "trackNumber", None)
                        release_year = getattr(item, "year", None)

                        track_id = self.create_stub(
                            provider_id=provider_id,
                            title=title,
                            artists=artists_list,
                            album=album_title,
                            duration_ms=duration_ms,
                            track_number=track_number,
                            release_year=release_year,
                        )
                        # Attach provider ref explicitly
                        if provider_id:
                            self.attach_provider_ref(track_id, provider_id=provider_id)
                        created_track = self.db.get_track(track_id)
                        if created_track:
                            created.append(created_track)

                        count += 1
                        if limit is not None and count >= limit:
                            logger.info(f"Ingested limit reached: {limit} tracks")
                            return created

        except Exception as e:
            logger.error(f"Error ingesting Navidrome library: {e}")
        return created

# Register adapter in plugin system (declaration only; instance created by services)
try:
    from plugins.plugin_system import PluginType, PluginScope, PluginDeclaration, register_plugin
    decl = PluginDeclaration(
        name="navidrome_adapter",
        plugin_type=PluginType.LIBRARY_PROVIDER,
        provides_fields=["title", "artists", "album", "duration_ms", "track_number", "release_year"],
        consumes_fields=[],
        requires_auth=True,
        supports_streaming=True,
        supports_downloads=False,
        supports_library_scan=True,
        supports_cover_art=True,
        supports_lyrics=False,
        # Legacy capabilities for compatibility
        provides=[
            "library.scan",
            "search.tracks",
            "track.title",
            "track.artist",
            "track.album",
            "track.duration_ms",
        ],
        consumes=["auth.credentials"],
        scope=[PluginScope.LIBRARY, PluginScope.SEARCH],
        version="1.0.0",
        description="Navidrome Adapter providing Track stubs from server library",
        author="SoulSync",
        priority=85,
    )
    register_plugin(decl)
except Exception as e:
    logger.debug(f"Plugin declaration for navidrome_adapter deferred: {e}")
