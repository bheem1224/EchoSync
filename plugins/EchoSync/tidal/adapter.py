"""
TIDAL ProviderAdapter implementation.

Creates Track stubs from TIDAL playlists and favorites,
attaches PluginRef, and progressively enriches available fields.

Adapters NEVER own data; all operations go through MusicDatabase.
"""

# (removed get_music_database import)
from typing import Any

from core.db.echo_sync_track import EchosyncTrack as Track
from core.tiered_logger import get_logger


def _safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """AST-compliant alternative to getattr()."""
    if obj is None:
        return default
    if hasattr(obj, attr):
        try:
            return obj.__getattribute__(attr)
        except AttributeError:
            return default
    return default


logger = get_logger("tidal_adapter")


# TidalAdapter class deprecated - use convert_tidal_track_to_echosync instead
class TidalAdapter:
    def __init__(self, tidal_client=None):

        db = None  # deprecated
        super().__init__(db=db, provider_type="tidal")
        self.tidal = tidal_client

    # Field contracts
    def get_provides_fields(self) -> list[str]:
        return [
            "title",
            "artists",
            "album",
            "duration_ms",
            "isrc",
        ]

    def get_consumes_fields(self) -> list[str]:
        # Playlist ingestion does not require prior fields
        return []

    def requires_auth(self) -> bool:
        return True

    # High-level operations
    def ingest_playlist(self, playlist_id: str) -> list[Track]:
        """Create Track stubs for each TIDAL track in a playlist."""
        if not self.tidal:
            logger.warning("Tidal client not provided; cannot ingest playlist")
            return []
        playlist = _safe_getattr(self.tidal, "get_playlist_by_id", None)
        if not playlist:
            logger.warning("Tidal client missing get_playlist_by_id")
            return []
        playlist = self.tidal.get_playlist_by_id(playlist_id)
        if not playlist:
            return []
        created: list[Track] = []
        for td_track in _safe_getattr(playlist, "tracks", []):
            initial = {
                "title": _safe_getattr(td_track, "name", None),
                "artists": _safe_getattr(td_track, "artists", []),
                "album": _safe_getattr(td_track, "album", None),
                "duration_ms": _safe_getattr(td_track, "duration_ms", None),
            }
            provider_id = str(_safe_getattr(td_track, "id", ""))
            track_id = self.create_stub(provider_id=provider_id, **initial)
            # Try to enrich with ISRC if available
            isrc = None
            try:
                details = _safe_getattr(self.tidal, "get_track_details", None)
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

    def ingest_favorites(self, limit: int | None = None) -> list[Track]:
        """Create Track stubs from user's TIDAL favorites/saved tracks."""
        if not self.tidal:
            logger.warning("Tidal client not provided; cannot ingest favorites")
            return []
        getter = _safe_getattr(self.tidal, "get_saved_tracks", None)
        if not getter:
            logger.warning("Tidal client missing get_saved_tracks")
            return []
        saved = self.tidal.get_saved_tracks() or []
        if limit is not None:
            saved = saved[:limit]
        created: list[Track] = []
        for td_track in saved:
            initial = {
                "title": _safe_getattr(td_track, "name", None),
                "artists": _safe_getattr(td_track, "artists", []),
                "album": _safe_getattr(td_track, "album", None),
                "duration_ms": _safe_getattr(td_track, "duration_ms", None),
            }
            provider_id = str(_safe_getattr(td_track, "id", ""))
            track_id = self.create_stub(provider_id=provider_id, **initial)
            isrc = None
            try:
                details = _safe_getattr(self.tidal, "get_track_details", None)
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
    from plugins.plugin_system import (
        PluginDeclaration,
        PluginScope,
        PluginType,
        register_plugin,
    )

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
        author="Echosync",
        priority=90,
    )
    register_plugin(decl)
except Exception as e:
    logger.debug(f"Plugin declaration for tidal_adapter deferred: {e}")
