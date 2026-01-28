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
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_DOWNLOAD_SEARCH
from core.matching_engine.text_utils import normalize_artist, normalize_title
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
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
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
                logger.info("No active download client configured")
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

            # Prevent duplicate queue entries for the same track while it is in-flight
            existing = self._find_existing_download(track_json)
            if existing:
                existing_id, existing_status = existing
                logger.info(
                    f"Duplicate download detected (ID {existing_id}, status {existing_status}); skipping enqueue"
                )
                return existing_id

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

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop:
            self._loop = loop
            self._loop_task = loop.create_task(self._process_loop())
            logger.info("Download Manager background task started (shared loop)")
            return

        # No running event loop (common for Flask/WSGI). Start a dedicated loop thread.
        self._start_dedicated_loop()

    async def stop_background_task(self):
        """Stop the background processing loop"""
        self._shutdown = True
        if self._loop_task:
            if self._loop and self._loop.is_running() and self._loop is not asyncio.get_running_loop():
                # Wake the loop so it can notice shutdown
                self._loop.call_soon_threadsafe(lambda: None)
                if self._loop_thread:
                    self._loop_thread.join(timeout=5)
            else:
                await self._loop_task
            self._loop_task = None
        self._loop = None
        logger.info("Download Manager background task stopped")

    def ensure_background_task(self):
        """Start background processing when called from sync contexts."""
        if self._loop_task:
            return
        self._shutdown = False
        self._start_dedicated_loop()

    def _start_dedicated_loop(self):
        """Spin up a dedicated asyncio loop in a daemon thread for download processing."""
        if self._loop_task or (self._loop_thread and self._loop_thread.is_alive()):
            return

        def _runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            self._loop_task = loop.create_task(self._process_loop())
            try:
                loop.run_until_complete(self._loop_task)
            finally:
                loop.close()

        self._loop_thread = threading.Thread(target=_runner, daemon=True)
        self._loop_thread.start()
        logger.info("Download Manager background task started (dedicated loop)")

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
        logger.info("DownloadManager processing loop started.")

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
            logger.debug("Skipping queue processing: No active provider.")
            return

        queued_ids = []
        with self.db.session_scope() as session:
            # Get up to 3 queued items
            items = session.query(Download).filter(Download.status == "queued").limit(3).all()
            if items:
                logger.info(f"Found {len(items)} queued items for processing.")

            for item in items:
                # Mark as processing so other workers (if any) don't grab it
                item.status = "searching"
                item.updated_at = datetime.utcnow()
                queued_ids.append(item.id)

        if not queued_ids:
            return

        # Create all search tasks concurrently (don't await sequentially)
        # Slskd will throttle to 5 concurrent via semaphore
        tasks = []
        for download_id in queued_ids:
            logger.debug(f"Queuing download for processing: {download_id}")
            task = asyncio.create_task(self._execute_search_and_download(download_id, provider))
            tasks.append(task)
        
        # Wait for all searches to complete (with semaphore limiting concurrent execution)
        if tasks:
            logger.info(f"Started {len(tasks)} search tasks (Slskd will limit to 5 concurrent)")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            failed = sum(1 for r in results if isinstance(r, Exception))
            if failed > 0:
                logger.warning(f"Completed {len(tasks)} searches with {failed} errors")

    async def _execute_search_and_download(self, download_id: int, provider: ProviderBase):
        """Perform Search -> Match -> Download for a single item"""
        target_track = None

        # Reload fresh state
        with self.db.session_scope() as session:
            download = session.query(Download).get(download_id)
            if not download:
                logger.error(f"Download ID {download_id} not found in DB.")
                return
            target_track = SoulSyncTrack.from_dict(download.soul_sync_track)

        if not target_track:
            logger.error(f"Failed to deserialize track for download {download_id}")
            self._update_status(download_id, "failed")
            return

        try:
            logger.info(f"Searching for: {target_track.artist_name} - {target_track.title} via {provider.name}")

            # 1. Get quality profile from config to determine allowed formats
            quality_profile = self._get_quality_profile()
            allowed_formats = self._extract_allowed_formats(quality_profile)
            
            # Use basic filters for coarse rejection based on quality profile
            basic_filters = {
                "allowed_extensions": allowed_formats,
                "min_bitrate": self._get_min_bitrate(quality_profile)
            }
            
            logger.info(f"Quality profile allows: {allowed_formats}")

            # Generate multiple query variations (fallback strategies)
            queries = self._generate_search_queries(target_track)
            logger.info(f"Generated {len(queries)} search query variations")

            candidates = []
            for idx, query in enumerate(queries, 1):
                logger.info(f"Trying search strategy {idx}/{len(queries)}: '{query}'")
                
                # Call provider search
                search_results = []
                if hasattr(provider, '_async_search'):
                    logger.debug(f"Invoking _async_search on {provider.name}")
                    search_results = await provider._async_search(query, basic_filters)
                else:
                    logger.debug(f"Invoking sync search on {provider.name}")
                    # Fallback to sync call in executor
                    loop = asyncio.get_running_loop()
                    search_results = await loop.run_in_executor(None, provider.search, query, basic_filters)

                logger.info(f"Strategy {idx} returned {len(search_results)} candidates")
                
                if search_results:
                    candidates.extend(search_results)
                    # If we got good results, we can stop trying more strategies
                    if len(candidates) >= 20:
                        logger.info(f"Found sufficient candidates ({len(candidates)}), stopping search strategies")
                        break

            logger.info(f"Total candidates from all strategies: {len(candidates)}")

            if not candidates:
                logger.warning("No results found for any search strategy")
                self._update_status(download_id, "failed_no_results")
                return

            # 1.5. Apply quality profile filtering to candidates
            filtered_candidates = self._filter_by_quality_profile(candidates, quality_profile)
            logger.info(f"After quality profile filtering: {len(filtered_candidates)} candidates remain")
            
            if not filtered_candidates:
                logger.warning(f"No candidates matched quality profile (had {len(candidates)} before filtering)")
                self._update_status(download_id, "failed_quality_filter")
                return

            # 2. Match (Selection)
            logger.debug("Running matching engine selection...")
            best_candidate = self.matcher.select_best_download_candidate(target_track, filtered_candidates)

            if not best_candidate:
                logger.warning(f"No suitable candidate matched (tried {len(queries)} strategies, got {len(candidates)} candidates)")
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

        logger.debug(f"Checking status for {len(active_downloads)} active downloads...")

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

                        if new_status == "completed":
                            # Future Scope: Trigger Post-Processor
                            logger.info(f"Download {db_id} completed. TODO: Trigger Auto Import/Post-Processing.")

            except Exception as e:
                logger.error(f"Error checking status for {db_id}: {e}")

    def _generate_search_queries(self, track: SoulSyncTrack) -> List[str]:
        """
        Generate multiple search query variations for fallback strategies.
        Returns queries in priority order (most specific to most generic).
        """
        from core.matching_engine.text_utils import extract_version_info
        
        queries = []
        
        # Strip version/remix info from title to search for original version
        clean_title, version_info = extract_version_info(track.title) if track.title else (track.title, None)
        
        if version_info:
            logger.info(f"Stripped version info from title: '{track.title}' -> '{clean_title}' (removed: '{version_info}')")
        
        # Use clean title without version info for searches
        search_title = clean_title if clean_title else track.title
        
        # Strategy 1: Artist + Title (most specific)
        if track.artist_name and search_title:
            queries.append(f"{track.artist_name} {search_title}")
        
        # Strategy 2: Album + Title (useful when artist has multiple versions)
        if track.album_title and search_title and track.album_title != search_title:
            queries.append(f"{track.album_title} {search_title}")
        
        # Strategy 3: Title only (broadest search)
        if search_title:
            queries.append(search_title)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            q_lower = q.lower().strip()
            if q_lower and q_lower not in seen:
                unique_queries.append(q)
                seen.add(q_lower)
        
        return unique_queries

    def _get_quality_profile(self) -> Optional[Dict[str, Any]]:
        """Get the active quality profile from config."""
        try:
            profiles = config_manager.get_quality_profiles()
            if profiles and len(profiles) > 0:
                # Use first profile (could be enhanced to support multiple/selection)
                return profiles[0]
        except Exception as e:
            logger.warning(f"Failed to load quality profile: {e}")
        return None

    def _extract_allowed_formats(self, quality_profile: Optional[Dict[str, Any]]) -> List[str]:
        """Extract allowed file formats from quality profile."""
        if not quality_profile:
            # Default fallback if no profile configured
            return ['mp3', 'flac', 'ogg', 'wav', 'm4a', 'aac']
        
        formats = quality_profile.get('formats', [])
        allowed = []
        
        for fmt in formats:
            format_type = fmt.get('type', '').lower()
            if format_type:
                allowed.append(format_type)
        
        if not allowed:
            # Fallback if profile exists but has no formats
            logger.warning("Quality profile has no formats defined, using defaults")
            return ['flac', 'wav', 'dsd']  # Conservative default
        
        return allowed

    def _get_min_bitrate(self, quality_profile: Optional[Dict[str, Any]]) -> int:
        """Get minimum bitrate from quality profile."""
        if not quality_profile:
            return 128
        
        # Find the minimum bitrate across all format rules
        formats = quality_profile.get('formats', [])
        min_bitrate = 9999
        
        for fmt in formats:
            fmt_min = fmt.get('min_bitrate', 0)
            if fmt_min > 0 and fmt_min < min_bitrate:
                min_bitrate = fmt_min
        
        return min_bitrate if min_bitrate < 9999 else 128

    def _filter_by_quality_profile(self, candidates: List[SoulSyncTrack], quality_profile: Optional[Dict[str, Any]]) -> List[SoulSyncTrack]:
        """Filter candidates using the quality profile rules."""
        if not quality_profile or not candidates:
            return candidates
        
        formats = quality_profile.get('formats', [])
        if not formats:
            return candidates
        
        # Sort formats by priority (lower number = higher priority)
        sorted_formats = sorted(formats, key=lambda x: x.get('priority', 999))
        
        # Try each format priority in order
        for fmt in sorted_formats:
            format_type = fmt.get('type', '').lower()
            min_size_mb = fmt.get('min_size_mb', 0)
            max_size_mb = fmt.get('max_size_mb', 0)
            
            matching = []
            for track in candidates:
                # Check format match
                if track.file_format and track.file_format.lower() != format_type:
                    continue
                
                # Check size constraints
                if track.file_size_bytes:
                    size_mb = track.file_size_bytes / (1024 * 1024)
                    if min_size_mb > 0 and size_mb < min_size_mb:
                        continue
                    if max_size_mb > 0 and size_mb > max_size_mb:
                        continue
                
                # Check additional constraints based on format type
                if format_type == 'flac' or format_type == 'wav':
                    bit_depths = fmt.get('bit_depths', [])
                    sample_rates = fmt.get('sample_rates', [])
                    
                    if bit_depths and track.bit_depth:
                        if str(track.bit_depth) not in bit_depths:
                            continue
                    
                    if sample_rates and track.sample_rate:
                        # Convert to kHz string for comparison
                        sample_rate_khz = str(int(track.sample_rate / 1000))
                        if sample_rate_khz not in sample_rates:
                            continue
                
                matching.append(track)
            
            if matching:
                logger.info(f"Found {len(matching)} candidates matching format priority {fmt.get('priority')}: {format_type}")
                return matching
        
        logger.debug("No candidates matched any quality profile format")
        return []

    def _update_status(self, download_id: int, status: str, provider_id: Optional[str] = None):
        """Helper to update DB status"""
        with self.db.session_scope() as session:
            download = session.query(Download).get(download_id)
            if download:
                download.status = status
                download.updated_at = datetime.utcnow()
                if provider_id:
                    download.provider_id = provider_id

    def _find_existing_download(self, track_json: Dict[str, Any]) -> Optional[Tuple[int, str]]:
        """Return an existing active download (id, status) matching the normalized track signature."""
        signature = self._normalize_track_signature(track_json)
        if not any(signature):
            return None

        active_states = {"queued", "searching", "downloading"}
        with self.db.session_scope() as session:
            items = session.query(Download).filter(Download.status.in_(active_states)).all()
            for item in items:
                other_sig = self._normalize_track_signature(item.soul_sync_track or {})
                if signature == other_sig:
                    return item.id, item.status
        return None

    def _normalize_track_signature(self, track_json: Dict[str, Any]) -> Tuple[str, str, Optional[int]]:
        """Build a normalized signature for duplicate detection."""
        artist = normalize_artist(track_json.get("artist_name") or track_json.get("artist") or "")
        title = normalize_title(track_json.get("title") or track_json.get("raw_title") or "")

        duration = track_json.get("duration")
        if duration is None:
            duration = track_json.get("duration_ms")
        if isinstance(duration, float):
            duration = int(duration)

        return artist or "", title or "", duration

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

    def _trigger_auto_import(self, download_id: int):
        """Trigger auto-import if enabled in config."""
        auto_import_enabled = config_manager.get("auto_import.enabled", False)
        if not auto_import_enabled:
            logger.info("Auto-import is disabled in config. Skipping.")
            return

        logger.info(f"Triggering auto-import for download ID: {download_id}")
        # Placeholder for actual auto-import logic
        # This could involve calling another service or running a script
        pass

# Global Accessor
def get_download_manager():
    return DownloadManager.get_instance()


def register_download_manager_job(interval_seconds: int = 300):
    """
    Register download manager processing as a periodic job with the global job_queue.
    Note: The download manager already runs a continuous processing loop when started.
    This job is mainly for visibility in the jobs UI.
    
    Args:
        interval_seconds: Interval placeholder (default 5 minutes = 300s)
    """
    from core.job_queue import job_queue
    
    def process_downloads():
        """Status check placeholder for job visibility"""
        logger.debug("Download manager status check (continuous processing active)")
    
    job_queue.register_job(
        name="download_manager_status",
        func=process_downloads,
        interval_seconds=interval_seconds,
        enabled=False,  # Disabled by default since _process_loop runs continuously
        tags=["soulsync", "downloads"],
        max_retries=3
    )
    
    logger.info(f"Download manager status job registered (interval: {interval_seconds}s, disabled by default)")
