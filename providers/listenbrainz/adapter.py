"""
ListenBrainz ProviderAdapter implementation.

Ingests playlists by MusicBrainz playlist MBID, creates Track stubs from
recording entries, and enriches with MusicBrainz recording IDs.

Adapters NEVER own data; all operations go through MusicDatabase.
"""

from typing import List
from core.tiered_logger import get_logger
from core.models import ProviderType, Track
from core.storage import get_storage_service

logger = get_logger("listenbrainz_adapter")

# ListenBrainzAdapter class deprecated - use convert_listenbrainz_track_to_soulsync instead
class ListenBrainzAdapter:
    def __init__(self, listenbrainz_client=None):
        storage = get_storage_service()
        db = storage.get_music_database()
        # Use MUSICBRAINZ provider type for recording references
        super().__init__(db=db, provider_type=ProviderType.MUSICBRAINZ)
        self.lb = listenbrainz_client

    def get_provides_fields(self) -> List[str]:
        return [
            "title",
            "artists",
            "album",
            "duration_ms",
            "musicbrainz_recording_id",
        ]

    def get_consumes_fields(self) -> List[str]:
        # Playlist ingestion does not require prior fields
        return []

    def requires_auth(self) -> bool:
        try:
            return bool(self.lb and self.lb.is_authenticated())
        except Exception:
            return False

    def ingest_playlist(self, playlist_mbid: str) -> List[Track]:
        """Create Track stubs from a ListenBrainz playlist by MBID."""
        created: List[Track] = []
        if not self.lb:
            logger.warning("ListenBrainz client not provided; cannot ingest playlist")
            return created
        data = self.lb.get_playlist_details(playlist_mbid, fetch_metadata=True)
        if not data:
            return created
        playlist = data.get("playlist", {})
        tracks = playlist.get("track", [])
        for entry in tracks:
            try:
                # Common fields in ListenBrainz recording entries
                recording_mbid = entry.get("recording_mbid") or entry.get("mbid") or ""
                title = entry.get("title") or entry.get("recording_name")
                artist_name = entry.get("artist_name") or entry.get("artist")
                album_name = entry.get("release_name") or entry.get("release")
                duration_ms = entry.get("duration_ms") or entry.get("duration")

                initial = {
                    "title": title,
                    "artists": [artist_name] if artist_name else [],
                    "album": album_name,
                    "duration_ms": duration_ms,
                    "musicbrainz_recording_id": recording_mbid or None,
                }
                provider_id = recording_mbid or title or ""
                track_id = self.create_stub(provider_id=provider_id, **initial)
                if recording_mbid:
                    # Attach MUSICBRAINZ provider reference using recording MBID
                    self.attach_provider_ref(track_id, provider_id=recording_mbid)
                created_track = self.db.get_track(track_id)
                if created_track:
                    created.append(created_track)
            except Exception as e:
                logger.debug(f"Skipping entry due to error: {e}")
        logger.info(f"Ingested {len(created)} tracks from ListenBrainz playlist {playlist_mbid}")
        return created

# Register adapter in plugin system (declaration only; instance created by services)
try:
    from plugins.plugin_system import PluginType, PluginScope, PluginDeclaration, register_plugin
    decl = PluginDeclaration(
        name="listenbrainz_adapter",
        plugin_type=PluginType.PLAYLIST_PROVIDER,
        provides_fields=["title", "artists", "album", "duration_ms", "musicbrainz_recording_id"],
        consumes_fields=[],
        requires_auth=False,
        supports_streaming=False,
        supports_downloads=False,
        supports_library_scan=False,
        supports_cover_art=False,
        supports_lyrics=False,
        # Legacy capabilities for compatibility
        provides=[
            "playlist.read",
            "search.playlists",
            "track.title",
            "track.artist",
            "track.album",
        ],
        consumes=[],
        scope=[PluginScope.SYNC, PluginScope.SEARCH],
        version="1.0.0",
        description="ListenBrainz Adapter ingesting playlists and enriching MBIDs",
        author="SoulSync",
        priority=70,
    )
    register_plugin(decl)
except Exception as e:
    logger.debug(f"Plugin declaration for listenbrainz_adapter deferred: {e}")
