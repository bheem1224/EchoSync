"""
Soulseek ProviderAdapter implementation.

Provides search and download enqueue operations, attaches ProviderRef using
the slskd download ID and updates download_status for canonical Tracks.

Adapters NEVER own data; all operations go through MusicDatabase.
"""

import asyncio
from typing import List, Optional
from utils.logging_config import get_logger
from plugins.provider_adapter import ProviderAdapter
from core.models import ProviderType, Track
from sdk.storage_service import get_storage_service

logger = get_logger("soulseek_adapter")

class SoulseekAdapter(ProviderAdapter):
    def __init__(self, soulseek_client=None):
        storage = get_storage_service()
        db = storage.get_music_database()
        super().__init__(db=db, provider_type=ProviderType.SOULSEEK)
        self.soulseek = soulseek_client

    # Field contracts
    def get_provides_fields(self) -> List[str]:
        return [
            "download_status",
            "file_path",
            "file_format",
            "bitrate",
        ]

    def get_consumes_fields(self) -> List[str]:
        return ["title", "artists"]

    def requires_auth(self) -> bool:
        return True

    async def _search_best_candidate(self, query: str):
        """Async helper: perform search and select best candidate using quality profile."""
        tracks, _albums = await self.soulseek.search(query)
        if not tracks:
            return None
        try:
            candidates = self.soulseek.filter_results_by_quality_preference(tracks)
            return candidates[0] if candidates else None
        except Exception as e:
            logger.error(f"Error selecting best candidate: {e}")
            return None

    async def _enqueue_download(self, username: str, filename: str, size: int) -> Optional[str]:
        try:
            return await self.soulseek.download(username, filename, size)
        except Exception as e:
            logger.error(f"Error enqueuing download: {e}")
            return None

    def enqueue_best_for_track(self, track_id: str) -> Optional[Track]:
        """Search Soulseek for the best candidate for a canonical Track and enqueue download."""
        if not self.soulseek:
            logger.warning("Soulseek client not provided; cannot enqueue download")
            return None
        track = self.db.get_track(track_id)
        if not track or not track.title or not track.artists:
            logger.warning("Track missing title/artists for Soulseek search")
            return None
        query = f"{track.artists[0]} - {track.title}"
        candidate = asyncio.run(self._search_best_candidate(query))
        if not candidate:
            logger.info("No suitable Soulseek candidate found")
            return None
        download_id = asyncio.run(self._enqueue_download(candidate.username, candidate.filename, candidate.size))
        if not download_id:
            logger.warning("Failed to enqueue Soulseek download")
            return None
        # Attach provider ref and update status to queued
        self.attach_provider_ref(
            track_id,
            provider_id=str(download_id),
            metadata={
                "username": candidate.username,
                "filename": candidate.filename,
                "size": candidate.size,
            },
        )
        updated = self.update_download_status(track_id, status="queued")
        return updated

    def search_and_enqueue(self, query: str) -> Optional[Track]:
        """Search by freeform query and create a Track stub for enqueued download."""
        if not self.soulseek:
            logger.warning("Soulseek client not provided; cannot search/enqueue")
            return None
        candidate = asyncio.run(self._search_best_candidate(query))
        if not candidate:
            return None
        download_id = asyncio.run(self._enqueue_download(candidate.username, candidate.filename, candidate.size))
        if not download_id:
            return None
        # Create a stub from candidate metadata
        initial = {
            "title": getattr(candidate, "title", None),
            "artists": [getattr(candidate, "artist", None)] if getattr(candidate, "artist", None) else [],
            "album": getattr(candidate, "album", None),
            "duration_ms": (getattr(candidate, "duration", None) or 0) * 1000,
            "file_format": getattr(candidate, "quality", None),
            "bitrate": getattr(candidate, "bitrate", None),
        }
        track_id = self.create_stub(provider_id=str(download_id), **initial)
        self.attach_provider_ref(
            track_id,
            provider_id=str(download_id),
            metadata={
                "username": candidate.username,
                "filename": candidate.filename,
                "size": candidate.size,
            },
        )
        updated = self.update_download_status(track_id, status="queued")
        return updated

# Register adapter in plugin system (declaration only; instance created by services)
try:
    from plugins.plugin_system import PluginType, PluginScope, PluginDeclaration, register_plugin
    decl = PluginDeclaration(
        name="soulseek_adapter",
        plugin_type=PluginType.DOWNLOAD_CLIENT,
        provides_fields=["download_status", "file_path", "file_format", "bitrate"],
        consumes_fields=["title", "artists"],
        requires_auth=True,
        supports_streaming=False,
        supports_downloads=True,
        supports_library_scan=False,
        supports_cover_art=False,
        supports_lyrics=False,
        # Legacy capabilities for compatibility
        provides=[
            "download.p2p",
            "search.tracks",
            "track.title",
            "track.artist",
        ],
        consumes=["auth.credentials"],
        scope=[PluginScope.DOWNLOAD, PluginScope.SEARCH],
        version="1.0.0",
        description="Soulseek Adapter for search and download enqueue",
        author="SoulSync",
        priority=80,
    )
    register_plugin(decl)
except Exception as e:
    logger.debug(f"Plugin declaration for soulseek_adapter deferred: {e}")
