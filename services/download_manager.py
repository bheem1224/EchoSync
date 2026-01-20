"""
Download Manager Service - Central Orchestrator for Downloads

This service acts as the "Source of Truth" for all downloads in SoulSync.
It manages the download lifecycle:
1. Queueing: Accepts SoulSyncTrack objects
2. Selection: Uses SlskdProvider (Atomic Search) + Matching Engine (Selection)
3. Execution: Triggers download on Slskd
4. Monitoring: Polls for status and updates DB
5. Persistence: Stores state in 'downloads' table

Design Principle: "Central Control"
- Consumers (UI, SyncService) ask this manager to download.
- This manager tells the Dumb Provider what to do.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_DOWNLOAD_SEARCH
from core.settings import config_manager
from core.provider import ProviderRegistry
from core.provider_base import ProviderBase
from database.music_database import get_database, Download

logger = logging.getLogger("download_manager")

class DownloadManager:
    """
    Central orchestrator for managing the download queue and provider interactions.
    """

    _instance = None

    def __init__(self):
        self.db = get_database()
        self.matcher = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)
        self._shutdown = False
        self._loop_task = None
        self._provider: Optional[ProviderBase] = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DownloadManager()
        return cls._instance

    def _get_provider(self) -> Optional[ProviderBase]:
        """Lazy load the active download provider"""
        if self._provider:
            return self._provider

        try:
            # Get active client from config
            active_client = config_manager.get_active_download_client()
            if not active_client:
                logger.warning("No active download client configured")
                return None

            # Check if provider is enabled and registered
            if ProviderRegistry.is_provider_disabled(active_client):
                logger.warning(f"Active download provider '{active_client}' is disabled")
                return None

            self._provider = ProviderRegistry.create_instance(active_client)
            return self._provider
        except Exception as e:
            logger.error(f"Failed to load download provider: {e}")
            return None

    def queue_download(self, track: SoulSyncTrack) -> int:
        """
        Add a track to the download queue.
        Returns the database ID of the new download record.
        """
        logger.info(f"Queueing download: {track.artist_name} - {track.title}")

        with self.db.session_scope() as session:
            # Serialize track to JSON for storage
            track_json = track.to_dict()

            download = Download(
                soul_sync_track=track_json,
                status="queued",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(download)
            session.flush() # Populate ID

            logger.info(f"Download queued with ID: {download.id}")
            return download.id

    async def start_background_task(self):
        """Start the background processing loop"""
        if self._loop_task:
            return

        self._shutdown = False
        self._loop_task = asyncio.create_task(self._process_loop())
        logger.info("Download Manager background task started")

    async def stop_background_task(self):
        """Stop the background processing loop"""
        self._shutdown = True
        if self._loop_task:
            await self._loop_task
            self._loop_task = None
        logger.info("Download Manager background task stopped")

    async def _recover_stuck_items(self):
        """Reset items stuck in 'searching' state back to 'queued' on startup."""
        with self.db.session_scope() as session:
            stuck_items = session.query(Download).filter(Download.status == "searching").all()
            if stuck_items:
                logger.warning(f"Found {len(stuck_items)} stuck downloads. Resetting to 'queued'.")
                for item in stuck_items:
                    item.status = "queued"
                    item.updated_at = datetime.utcnow()

    async def _process_loop(self):
        """Main control loop: Process Queue -> Check Active"""
        # 0. Recover stuck items on startup
        await self._recover_stuck_items()

        while not self._shutdown:
            try:
                # 1. Process Queued Items
                await self._process_queued_items()

                # 2. Check Active Downloads
                await self._check_active_downloads()

                # 3. Sleep
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in DownloadManager loop: {e}", exc_info=True)
                await asyncio.sleep(10) # Backoff on error

    async def _process_queued_items(self):
        """Pick up queued items and attempt to find/start them"""
        provider = self._get_provider()
        if not provider:
            return

        # Fetch queued items from DB
        # We need to do this carefully to avoid holding the DB lock too long
        # or sharing SA objects across threads if async is involved (though we are in async loop)
        # Note: SQLAlchemy async support is not used here, so we use sync calls wrapped or directly.
        # Since this loop effectively blocks, we should be careful.
        # But given Python's GIL and standard threading, simple sync DB access is usually fine for low throughput.

        queued_ids = []
        with self.db.session_scope() as session:
            # Get up to 5 queued items
            items = session.query(Download).filter(Download.status == "queued").limit(5).all()
            for item in items:
                # Mark as processing so other workers (if any) don't grab it
                item.status = "searching"
                item.updated_at = datetime.utcnow()
                queued_ids.append(item.id)

        if not queued_ids:
            return

        for download_id in queued_ids:
            await self._execute_search_and_download(download_id, provider)

    async def _execute_search_and_download(self, download_id: int, provider: ProviderBase):
        """Perform Search -> Match -> Download for a single item"""
        target_track = None

        # Reload fresh state
        with self.db.session_scope() as session:
            download = session.query(Download).get(download_id)
            if not download:
                return
            target_track = SoulSyncTrack.from_dict(download.soul_sync_track)

        if not target_track:
            logger.error(f"Failed to deserialize track for download {download_id}")
            self._update_status(download_id, "failed")
            return

        try:
            logger.info(f"Searching for: {target_track.artist_name} - {target_track.title}")

            # 1. Search (Atomic)
            # Use basic filters for coarse rejection
            basic_filters = {
                "allowed_extensions": ['mp3', 'flac', 'ogg', 'wav', 'm4a'],
                "min_bitrate": 128
            }

            # Construct query
            query = f"{target_track.artist_name} {target_track.title}"

            # Call provider search (synchronous wrapper usually, but we are in async)
            # SlskdProvider.search is the wrapper. We should use _async_search if possible
            # or run the wrapper in executor to avoid blocking loop.
            # But the SlskdProvider.search wrapper creates its own loop which is bad inside a loop.
            # We should call the async method directly if we cast the type.

            candidates = []
            if hasattr(provider, '_async_search'):
                candidates = await provider._async_search(query, basic_filters)
            else:
                # Fallback to sync call in executor
                loop = asyncio.get_running_loop()
                candidates = await loop.run_in_executor(None, provider.search, query, basic_filters)

            if not candidates:
                logger.warning(f"No results found for {query}")
                self._update_status(download_id, "failed_no_results")
                return

            # 2. Match (Selection)
            best_candidate = self.matcher.select_best_download_candidate(target_track, candidates)

            if not best_candidate:
                logger.warning(f"No suitable candidate matched for {query}")
                self._update_status(download_id, "failed_no_match")
                return

            # 3. Download
            logger.info(f"Starting download for {best_candidate.identifiers.get('provider_item_id')}")

            # Extract params
            username = best_candidate.identifiers.get('username')
            filename = best_candidate.identifiers.get('provider_item_id')
            size = best_candidate.identifiers.get('size')

            provider_id = None
            if hasattr(provider, '_async_download'):
                provider_id = await provider._async_download(username, filename, size)
            else:
                loop = asyncio.get_running_loop()
                provider_id = await loop.run_in_executor(None, provider.download, username, filename, size)

            if provider_id:
                self._update_status(download_id, "downloading", provider_id)
            else:
                self._update_status(download_id, "failed_start_download")

        except Exception as e:
            logger.error(f"Error executing download {download_id}: {e}")
            self._update_status(download_id, "failed_error")

    async def _check_active_downloads(self):
        """Poll provider for status of active downloads"""
        provider = self._get_provider()
        if not provider:
            return

        active_downloads = []
        with self.db.session_scope() as session:
            # Find items marked 'downloading'
            items = session.query(Download).filter(Download.status == "downloading").all()
            for item in items:
                active_downloads.append((item.id, item.provider_id))

        if not active_downloads:
            return

        for db_id, provider_id in active_downloads:
            if not provider_id:
                continue

            try:
                # Get status
                status = None
                if hasattr(provider, '_async_get_download_status'):
                    status = await provider._async_get_download_status(provider_id)
                else:
                    loop = asyncio.get_running_loop()
                    status = await loop.run_in_executor(None, provider.get_download_status, provider_id)

                if status:
                    # Map provider status to DB status
                    # Slskd returns: queued, downloading, complete, failed
                    remote_state = status.get('status', '').lower()

                    new_status = "downloading" # default
                    if remote_state == "complete":
                        new_status = "completed"
                    elif remote_state == "failed":
                        new_status = "failed"
                    elif remote_state == "queued":
                        new_status = "downloading" # We treat remote queue as active downloading phase

                    if new_status != "downloading":
                        logger.info(f"Download {db_id} (Provider {provider_id}) finished with status: {new_status}")
                        self._update_status(db_id, new_status)

                        # Trigger Post-Processor if complete? (Future Scope)

            except Exception as e:
                logger.error(f"Error checking status for {db_id}: {e}")

    def _update_status(self, download_id: int, status: str, provider_id: str = None):
        """Helper to update DB status"""
        with self.db.session_scope() as session:
            download = session.query(Download).get(download_id)
            if download:
                download.status = status
                download.updated_at = datetime.utcnow()
                if provider_id:
                    download.provider_id = provider_id

    def get_status(self, download_id: int) -> Optional[Dict]:
        """Get status for UI"""
        with self.db.session_scope() as session:
            download = session.query(Download).get(download_id)
            if download:
                return {
                    "id": download.id,
                    "status": download.status,
                    "track": download.soul_sync_track,
                    "provider_id": download.provider_id,
                    "updated_at": download.updated_at.isoformat()
                }
        return None

# Global Accessor
def get_download_manager():
    return DownloadManager.get_instance()
