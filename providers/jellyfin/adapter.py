"""
Jellyfin ProviderAdapter implementation.

Populates library-related Track fields (file_path, file_format, bitrate, duration_ms)
and attaches Jellyfin ProviderRef. Adheres to Track-centric architecture.
"""

from typing import List, Optional, Dict, Any
from utils.logging_config import get_logger
from plugins.provider_adapter import ProviderAdapter
from core.models import ProviderType, Track
from sdk.storage_service import get_storage_service

logger = get_logger("jellyfin_adapter")

class JellyfinAdapter(ProviderAdapter):
    def __init__(self, jellyfin_client=None):
        storage = get_storage_service()
        db = storage.get_music_database()
        super().__init__(db=db, provider_type=ProviderType.JELLYFIN)
        self.jellyfin = jellyfin_client

    def get_provides_fields(self) -> List[str]:
        return [
            "file_path",
            "file_format",
            "bitrate",
            "duration_ms",
            "title",
            "artists",
            "album",
        ]

    def get_consumes_fields(self) -> List[str]:
        return []

    def requires_auth(self) -> bool:
        return True

    def attach_file_metadata(self, track_id: str, file_path: str, file_format: Optional[str] = None,
                             bitrate: Optional[int] = None, duration_ms: Optional[int] = None) -> Track:
        """Attach local file metadata to an existing Track and mark status as verified if present."""
        track = self.db.get_track(track_id)
        if not track:
            raise ValueError(f"Track {track_id} not found")
        # Enrich metadata
        updates: Dict[str, Any] = {
            "file_path": file_path,
            "file_format": file_format,
            "bitrate": bitrate,
            "duration_ms": duration_ms,
        }
        updates = {k: v for k, v in updates.items() if v is not None}
        track = self.enrich_track(track_id, **updates)
        try:
            from core.models import DownloadStatus
            status = DownloadStatus.VERIFIED.value if file_path else DownloadStatus.COMPLETE.value
            track = self.update_download_status(track_id, status=status)
        except Exception:
            pass
        return track

    def ingest_library(self, limit: Optional[int] = None) -> List[Track]:
        """Scan Jellyfin music library and populate canonical tracks."""
        created: List[Track] = []
        if not self.jellyfin:
            logger.warning("Jellyfin client not provided; cannot ingest library")
            return created
        getter = getattr(self.jellyfin, "get_all_tracks", None)
        if not getter:
            logger.warning("Jellyfin client missing get_all_tracks")
            return created
        try:
            items = self.jellyfin.get_all_tracks() or []
            if limit is not None:
                items = items[:limit]
            for item in items:
                provider_id = str(getattr(item, "id", getattr(item, "Id", "")))
                title = getattr(item, "title", getattr(item, "Name", None))
                artists = getattr(item, "artists", []) or ([getattr(item, "AlbumArtist", None)] if getattr(item, "AlbumArtist", None) else [])
                album = getattr(item, "album", getattr(item, "Album", None))
                duration_ms = getattr(item, "duration", getattr(item, "RunTimeTicks", None))
                # Create stub and attach ref
                track_id = self.create_stub(provider_id=provider_id, title=title, artists=artists, album=album, duration_ms=duration_ms)
                # File metadata
                file_path = getattr(item, "Path", None)
                file_format = getattr(item, "Container", None)
                bitrate = getattr(item, "Bitrate", None)
                self.enrich_track(track_id, file_path=file_path, file_format=file_format, bitrate=bitrate)
                if provider_id:
                    self.attach_provider_ref(track_id, provider_id=provider_id)
                updated = self.update_download_status(track_id, status="verified")
                if updated:
                    created.append(updated)
        except Exception as e:
            logger.error(f"Error ingesting Jellyfin library: {e}")
        return created

# Register adapter in plugin system
try:
    from plugins.plugin_system import PluginType, PluginScope, PluginDeclaration, register_plugin
    decl = PluginDeclaration(
        name="jellyfin_adapter",
        plugin_type=PluginType.LIBRARY_PROVIDER,
        provides_fields=["file_path", "file_format", "bitrate", "duration_ms", "title", "artists", "album"],
        consumes_fields=[],
        requires_auth=True,
        supports_streaming=True,
        supports_downloads=False,
        supports_library_scan=True,
        supports_cover_art=True,
        supports_lyrics=False,
        provides=["library.scan", "library.tag_write", "track.title", "track.artist", "track.album", "track.duration_ms"],
        consumes=["auth.credentials"],
        scope=[PluginScope.LIBRARY],
        version="1.0.0",
        description="Jellyfin adapter populating local file metadata for canonical tracks",
        author="SoulSync",
        priority=90,
    )
    register_plugin(decl)
except Exception as e:
    logger.debug(f"Plugin declaration for jellyfin_adapter deferred: {e}")
