"""
Plex ProviderAdapter implementation.

Populates library-related Track fields (file_path, file_format, bitrate, duration_ms)
and attaches Plex ProviderRef. Adheres to Track-centric architecture.
"""

from typing import List, Optional, Dict, Any
from utils.logging_config import get_logger
from core.provider_adapter import ProviderAdapter
from core.models import ProviderType, Track
from database.music_database import get_database

logger = get_logger("plex_adapter")

class PlexAdapter(ProviderAdapter):
    def __init__(self, plex_client=None):
        db = get_database()
        super().__init__(db=db, provider_type=ProviderType.PLEX)
        self.plex = plex_client

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
        # Remove None values
        updates = {k: v for k, v in updates.items() if v is not None}
        track = self.enrich_track(track_id, **updates)
        # If file_path present, set download status to verified
        try:
            from core.models import DownloadStatus
            status = DownloadStatus.VERIFIED.value if file_path else DownloadStatus.COMPLETE.value
            track = self.update_download_status(track_id, status=status)
        except Exception:
            pass
        return track

    def ingest_library(self, limit: Optional[int] = None) -> List[Track]:
        """Scan Plex music library and populate canonical tracks."""
        created: List[Track] = []
        if not self.plex:
            logger.warning("Plex client not provided; cannot ingest library")
            return created
        getter = getattr(self.plex, "get_all_tracks", None)
        if not getter:
            logger.warning("Plex client missing get_all_tracks")
            return created
        try:
            items = self.plex.get_all_tracks() or []
            if limit is not None:
                items = items[:limit]
            for item in items:
                # Extract metadata defensively
                provider_id = str(getattr(item, "id", getattr(item, "ratingKey", "")))
                title = getattr(item, "title", None)
                artists = getattr(item, "artists", []) or ([getattr(item, "grandparentTitle", None)] if getattr(item, "grandparentTitle", None) else [])
                album = getattr(item, "album", getattr(item, "parentTitle", None))
                duration_ms = getattr(item, "duration", None)
                # Create stub and attach provider ref
                track_id = self.create_stub(provider_id=provider_id, title=title, artists=artists, album=album, duration_ms=duration_ms)
                # File metadata
                file_path = getattr(item, "mediaPath", None)
                file_format = getattr(item, "container", None)
                bitrate = getattr(item, "bitrate", None)
                # Enrich and mark verified if file present
                self.enrich_track(track_id, file_path=file_path, file_format=file_format, bitrate=bitrate)
                if provider_id:
                    self.attach_provider_ref(track_id, provider_id=provider_id)
                updated = self.update_download_status(track_id, status="verified")
                if updated:
                    created.append(updated)
        except Exception as e:
            logger.error(f"Error ingesting Plex library: {e}")
        return created

# Register adapter in plugin system
try:
    from core.plugin_system import PluginType, PluginScope, PluginDeclaration, register_plugin
    decl = PluginDeclaration(
        name="plex_adapter",
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
        description="Plex adapter populating local file metadata for canonical tracks",
        author="SoulSync",
        priority=100,
    )
    register_plugin(decl)
except Exception as e:
    logger.debug(f"Plugin declaration for plex_adapter deferred: {e}")
