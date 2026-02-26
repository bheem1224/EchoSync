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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_DOWNLOAD_SEARCH
from core.matching_engine.text_utils import normalize_artist, normalize_title
from core.settings import config_manager
from core.provider import ProviderRegistry
from core.provider_base import ProviderBase
from database.music_database import get_database, Download, Track, Artist

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
        self._quality_profile_cache = None

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

        # Check if track already exists in library
        if self._track_exists_in_library(track.artist_name, track.title):
            logger.info(f"Skipping download: Track '{track.title}' by '{track.artist_name}' already exists in library")
            return 0  # 0 indicates no download created

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
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
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
                    item.updated_at = datetime.now(timezone.utc)
            
            # Also clean up legacy downloads with invalid provider_id format
            # These are from before the compound ID (username|filename) format was implemented
            legacy_items = session.query(Download).filter(
                Download.status == "downloading",
                Download.provider_id.isnot(None)
            ).all()
            
            cleaned = 0
            for item in legacy_items:
                if item.provider_id and '|' not in item.provider_id:
                    # Legacy format without username prefix - mark as failed
                    logger.debug(f"Cleaning up legacy download entry: {item.id}")
                    item.status = "failed_legacy_format"
                    item.updated_at = datetime.now(timezone.utc)
                    cleaned += 1
            
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} legacy download entries with invalid provider_id format")

    async def _process_loop(self):
        """Main control loop: Process Queue -> Check Active"""
        # 0. Recover stuck items and clean up queue on startup
        await self._recover_stuck_items()
        self._purge_existing_tracks_from_queue()
        logger.info("DownloadManager processing loop started.")

        while not self._shutdown:
            try:
                # 0. Periodic Cleanup: Ensure we aren't downloading things already in library
                # This prevents "ghost loops" where we keep trying to download something that was imported
                self._purge_existing_tracks_from_queue()

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

        # Fetch queued items from DB
        # We need to do this carefully to avoid holding the DB lock too long
        # or sharing SA objects across threads if async is involved (though we are in async loop)
        # Note: SQLAlchemy async support is not used here, so we use sync calls wrapped or directly.
        # Since this loop effectively blocks, we should be careful.
        # But given Python's GIL and standard threading, simple sync DB access is usually fine for low throughput.

        queued_ids = []
        with self.db.session_scope() as session:
            # Get up to 30 queued items to enable 10 concurrent searches
            # Note: SlskdProvider internally limits to 5 concurrent searches (Soulseek IP ban protection)
            # Download manager can scale to 10 if other clients (e.g., non-Soulseek) are added later
            items = session.query(Download).filter(Download.status == "queued").limit(30).all()
            if items:
                logger.info(f"Found {len(items)} queued items for processing.")

            for item in items:
                # Mark as processing so other workers (if any) don't grab it
                item.status = "searching"
                item.updated_at = datetime.now(timezone.utc)
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
            
            # Get duration tolerance from quality profile (default 5 seconds)
            duration_tolerance_ms = 5000
            if quality_profile and 'advanced_filters' in quality_profile:
                filters = quality_profile['advanced_filters']
                if 'duration_tolerance_seconds' in filters:
                    duration_tolerance_ms = int(filters['duration_tolerance_seconds'] * 1000)
            
            # Use basic filters for coarse rejection based on quality profile
            # Include duration filtering to weed out remixes/live versions
            basic_filters = {
                "allowed_extensions": allowed_formats,
                "min_bitrate": self._get_min_bitrate(quality_profile),
                "target_duration_ms": target_track.duration if target_track.duration else None,
                "duration_tolerance_ms": duration_tolerance_ms  # Read from quality profile
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

            # 1.5. Quality Profile Cascading - Try each priority tier until one succeeds
            best_candidate = None
            
            # Get priority tiers from quality profile (sorted by priority)
            priority_tiers = self._get_priority_tiers(quality_profile)
            
            for priority_num, priority_formats in priority_tiers:
                logger.info(f"Trying quality profile priority {priority_num}: {priority_formats}")
                
                # Filter candidates by this priority tier
                tier_candidates = self._filter_by_formats(candidates, priority_formats)
                logger.info(f"Found {len(tier_candidates)} candidates matching priority {priority_num}")
                
                if not tier_candidates:
                    continue
                
                # Try to match with this tier
                logger.debug(f"Running matching engine on priority {priority_num} candidates...")
                matcher = self._get_matching_engine()
                best_candidate = matcher.select_best_download_candidate(target_track, tier_candidates)
                
                if best_candidate:
                    logger.info(f"Successfully matched with priority {priority_num} format")
                    break
                else:
                    logger.warning(f"Priority {priority_num} yielded {len(tier_candidates)} candidates but all failed matching")
            
            if not best_candidate:
                logger.warning(f"No suitable candidate matched across all quality priorities (tried {len(queries)} strategies, got {len(candidates)} candidates)")
                self._update_status(download_id, "failed_no_match")
                return

            # 3. Download
            logger.info(f"Starting download for {best_candidate.identifiers.get('provider_item_id')}")

            # Extract params - username is the peer who has the file
            username = best_candidate.identifiers.get('username')
            filename = best_candidate.identifiers.get('provider_item_id')
            size = best_candidate.identifiers.get('size')
            
            if not username:
                logger.error("Cannot download: no username in candidate identifiers")
                self._update_status(download_id, "failed_no_username")
                return
            
            if not filename:
                logger.error("Cannot download: no filename in candidate identifiers")
                self._update_status(download_id, "failed_no_filename")
                return

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
                # Ghost item with no provider ID? Fail it.
                self._update_status(db_id, "failed_no_id")
                continue

            try:
                # Get status
                status = None
                if hasattr(provider, '_async_get_download_status'):
                    status = await provider._async_get_download_status(provider_id)
                else:
                    loop = asyncio.get_running_loop()
                    status = await loop.run_in_executor(None, provider.get_download_status, provider_id)

                # If status is None, it means the provider can't find it anymore.
                # This could be because it was removed, or failed silently.
                # We should NOT keep polling forever.
                if status is None:
                    logger.warning(f"Download {db_id} (Provider {provider_id}) not found by provider. Marking as failed/missing.")
                    self._update_status(db_id, "failed_not_found")
                    continue

                # Map provider status to DB status
                # Slskd/Provider returns: queued, downloading, complete, failed, aborted, etc.
                remote_state = status.get('status', '').lower()

                new_status = "downloading" # default
                is_terminal = False

                if remote_state in ["complete", "completed", "succeeded", "finished"]:
                    new_status = "completed"
                    is_terminal = True
                elif remote_state in ["failed", "error", "aborted", "cancelled", "not_found"]:
                    new_status = "failed"
                    is_terminal = True
                elif remote_state in ["queued", "initializing", "downloading", "transferring"]:
                    new_status = "downloading" # Still active
                else:
                    logger.warning(f"Unknown remote state '{remote_state}' for {db_id}, treating as active")
                    new_status = "downloading"

                # Update DB if status changed OR if it's terminal (to trigger cleanup)
                if new_status != "downloading" or is_terminal:
                    logger.info(f"Download {db_id} (Provider {provider_id}) finished/terminal with status: {new_status} (Remote: {remote_state})")
                    self._update_status(db_id, new_status)

                    # CLEANUP TASK: Remove from queue/DB if completed (or optionally failed, depending on policy)
                    # For now, we only remove 'completed' to keep history of failures visible if needed,
                    # OR we can remove everything terminal. The requirement says:
                    # "If ... completed, failed, aborted ... DownloadManager MUST explicitly pop/remove ... from active polling loop"
                    # By updating status to non-"downloading", it is effectively removed from the next _check_active_downloads query.

                    if new_status == "completed":
                        logger.info(f"Download completed successfully, removing {db_id} from queue")
                        self._remove_from_queue(db_id)
                        # Trigger any post-processing hooks here if needed

            except Exception as e:
                logger.error(f"Error checking status for {db_id}: {e}")

    def _generate_search_queries(self, track: SoulSyncTrack) -> List[str]:
        """
        Generate multiple search query variations for fallback strategies.
        Returns queries in priority order (most specific to most generic).
        
        Uses matching engine's normalize_title() which handles:
        - OST/Soundtrack/Movie metadata removal
        - Featured artist cleanup
        - Text normalization
        """
        queries = []
        
        # Use matching engine's normalize_title which strips OST/featured artists/etc.
        # This ensures consistency with how the matching engine will compare results
        search_title = normalize_title(track.title) if track.title else track.title
        
        if search_title != track.title:
            logger.info(f"Normalized title for search: '{track.title}' -> '{search_title}'")
        
        # Strategy 1: Artist + Title (most specific)
        # Also normalize artist name for consistency
        if track.artist_name and search_title:
            normalized_artist = normalize_artist(track.artist_name)
            queries.append(f"{normalized_artist} {search_title}")
        
        # Strategy 2: Album + Title (useful when artist has multiple versions)
        # Normalize album title to remove OST metadata
        if track.album_title and search_title:
            from core.matching_engine.text_utils import normalize_album
            normalized_album = normalize_album(track.album_title)
            # Only add if album name is different from title (avoid duplicates)
            if normalized_album and normalized_album != search_title:
                queries.append(f"{normalized_album} {search_title}")
        
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
    
    def _get_matching_engine(self) -> WeightedMatchingEngine:
        """
        Get or create the matching engine with settings from quality profile.
        If quality profile has custom settings, create a custom profile.
        Otherwise use the default PROFILE_DOWNLOAD_SEARCH.
        """
        quality_profile = self._get_quality_profile()
        if not quality_profile:
            return WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)
        
        # Check for custom matching settings in quality profile
        has_custom_settings = False
        custom_weights = dict(vars(PROFILE_DOWNLOAD_SEARCH.get_weights()))
        
        # Read custom duration tolerance if specified
        if 'advanced_filters' in quality_profile:
            filters = quality_profile['advanced_filters']
            if 'enforce_duration_match' in filters:
                custom_weights['enforce_duration_match'] = filters['enforce_duration_match']
                has_custom_settings = True
            if 'duration_tolerance_seconds' in filters:
                tolerance_s = filters['duration_tolerance_seconds']
                custom_weights['duration_tolerance_ms'] = int(tolerance_s * 1000)
                has_custom_settings = True
        
        # Read prefer larger files if specified
        if 'prefer_larger_files' in quality_profile:
            custom_weights['prefer_max_quality'] = quality_profile['prefer_larger_files']
            has_custom_settings = True
        
        if has_custom_settings:
            # Create custom profile with updated weights
            from core.matching_engine.scoring_profile import ScoringProfile, ScoringWeights
            custom_profile = ScoringProfile()
            custom_profile.weights = ScoringWeights(**custom_weights)
            logger.info(f"Using custom matching profile: duration_tolerance={custom_weights.get('duration_tolerance_ms')}ms, prefer_max_quality={custom_weights.get('prefer_max_quality')}")
            return WeightedMatchingEngine(custom_profile)
        
        return WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)

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

    def _get_priority_tiers(self, quality_profile: Dict[str, Any]) -> List[Tuple[int, List[str]]]:
        """
        Extract priority tiers from quality profile.
        Returns list of (priority_number, [format_list]) sorted by priority.
        """
        formats = quality_profile.get('formats', [])
        if not formats:
            return []
        
        # Group formats by priority
        priority_map = {}
        for fmt in formats:
            priority = fmt.get('priority', 999)
            format_type = fmt.get('type', '').lower()
            
            if priority not in priority_map:
                priority_map[priority] = []
            priority_map[priority].append(format_type)
        
        # Sort by priority (lower number = higher priority)
        sorted_tiers = sorted(priority_map.items(), key=lambda x: x[0])
        return sorted_tiers
    
    def _filter_by_formats(self, candidates: List[SoulSyncTrack], formats: List[str]) -> List[SoulSyncTrack]:
        """Filter candidates by format and apply quality profile constraints."""
        quality_profile = self._get_quality_profile()
        if not quality_profile:
            # Fallback: just filter by format
            filtered = []
            for track in candidates:
                if track.file_format and track.file_format.lower() in formats:
                    filtered.append(track)
            return filtered
        
        # Get format configs for the requested formats
        format_configs = {}
        for fmt in quality_profile.get('formats', []):
            format_type = fmt.get('type', '').lower()
            if format_type in formats:
                format_configs[format_type] = fmt
        
        filtered = []
        for track in candidates:
            if not track.file_format:
                continue
            
            format_type = track.file_format.lower()
            if format_type not in formats:
                continue
            
            # Get format config
            fmt_config = format_configs.get(format_type)
            if not fmt_config:
                filtered.append(track)
                continue
            
            # Apply size constraints
            min_size_mb = fmt_config.get('min_size_mb', 0)
            max_size_mb = fmt_config.get('max_size_mb', 0)
            
            if track.file_size_bytes:
                size_mb = track.file_size_bytes / (1024 * 1024)
                if min_size_mb > 0 and size_mb < min_size_mb:
                    continue
                if max_size_mb > 0 and size_mb > max_size_mb:
                    continue
            
            # For lossless formats (FLAC, WAV, DSD), check bit depth and sample rate
            if format_type in ['flac', 'wav', 'dsd']:
                bit_depths = fmt_config.get('bit_depths', [])
                sample_rates = fmt_config.get('sample_rates', [])
                
                if bit_depths and track.bit_depth:
                    if str(track.bit_depth) not in bit_depths:
                        continue
                
                if sample_rates and track.sample_rate:
                    sample_rate_khz = str(int(track.sample_rate / 1000))
                    if sample_rate_khz not in sample_rates:
                        continue
            
            # For lossy formats (MP3, AAC, OGG, etc.), check bitrate
            elif format_type in ['mp3', 'aac', 'ogg', 'm4a', 'opus', 'vorbis']:
                min_bitrate_kbps = fmt_config.get('min_bitrate', 0)
                max_bitrate_kbps = fmt_config.get('max_bitrate', 999999)
                
                # Extract bitrate from identifiers or track metadata
                bitrate_kbps = 0
                if track.identifiers and 'bitrate' in track.identifiers:
                    bitrate_kbps = track.identifiers.get('bitrate', 0) or 0
                    # Convert to kbps if in different unit
                    if bitrate_kbps > 10000:  # Likely in bps
                        bitrate_kbps = bitrate_kbps // 1000
                
                if min_bitrate_kbps > 0 and bitrate_kbps > 0 and bitrate_kbps < min_bitrate_kbps:
                    logger.debug(f"Rejecting {format_type} ({bitrate_kbps}kbps) - below minimum {min_bitrate_kbps}kbps")
                    continue
                
                if max_bitrate_kbps > 0 and bitrate_kbps > 0 and bitrate_kbps > max_bitrate_kbps:
                    logger.debug(f"Rejecting {format_type} ({bitrate_kbps}kbps) - above maximum {max_bitrate_kbps}kbps")
                    continue
            
            filtered.append(track)
        
        # Sort by size (prefer larger files for better quality)
        filtered.sort(key=lambda t: t.file_size_bytes or 0, reverse=True)
        
        return filtered

    def _remove_from_queue(self, download_id: int):
        """CLEANUP TASK 1: Remove a download from the queue after successful completion."""
        try:
            with self.db.session_scope() as session:
                download = session.query(Download).get(download_id)
                if download:
                    session.delete(download)
                    logger.info(f"Removed completed download {download_id} from queue")
        except Exception as e:
            logger.warning(f"Failed to remove download {download_id} from queue: {e}")
    
    def _cleanup_queue_against_library(self):
        """
        CLEANUP TASK 2: Periodic job to remove items from download queue that are already in the library.
        Detects if items were added via other means (auto-import, manual import, etc.)
        """
        try:
            with self.db.session_scope() as session:
                # Get all queued items
                queued_items = session.query(Download).filter(
                    Download.status.in_(['queued', 'searching', 'downloading', 'failed_no_match'])
                ).all()
                
                if not queued_items:
                    return
                
                logger.info(f"Running library cleanup: checking {len(queued_items)} queued items against library")
                removed_count = 0
                
                for item in queued_items:
                    try:
                        track_data = item.soul_sync_track
                        if not track_data:
                            continue
                        
                        # Get track info
                        artist = track_data.get('artist_name', '')
                        title = track_data.get('title', '')
                        
                        # Check if track exists in library
                        from database.music_database import Track
                        existing = session.query(Track).filter(
                            Track.artist.ilike(f'%{artist}%'),
                            Track.title.ilike(f'%{title}%')
                        ).first()
                        
                        if existing:
                            logger.info(f"Track '{artist} - {title}' already in library, removing from queue")
                            session.delete(item)
                            removed_count += 1
                    except Exception as e:
                        logger.debug(f"Error checking library for queued item: {e}")
                
                if removed_count > 0:
                    logger.info(f"Library cleanup removed {removed_count} items from download queue")
        except Exception as e:
            logger.warning(f"Library cleanup job failed: {e}")

    def _update_status(self, download_id: int, status: str, provider_id: Optional[str] = None):
        """Helper to update DB status"""
        with self.db.session_scope() as session:
            download = session.query(Download).get(download_id)
            if download:
                download.status = status
                download.updated_at = datetime.now(timezone.utc)
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

    def _track_exists_in_library(self, artist_name: str, title: str) -> bool:
        """
        Check if a track already exists in the library (database).

        Args:
            artist_name: Artist name
            title: Track title

        Returns:
            True if track exists, False otherwise
        """
        if not artist_name or not title:
            return False

        try:
            with self.db.session_scope() as session:
                # Perform strict match on title and artist
                # We join Track and Artist tables
                exists = session.query(
                    session.query(Track).join(Artist).filter(
                        Artist.name.ilike(artist_name.strip()),
                        Track.title.ilike(title.strip())
                    ).exists()
                ).scalar()
                return bool(exists)
        except Exception as e:
            logger.error(f"Error checking library for {artist_name} - {title}: {e}")
            return False

    def _purge_existing_tracks_from_queue(self):
        """
        Startup Check: Remove items from the download queue that are already in the library.
        Prevents re-downloading tracks that were imported while the queue was active/stalled.
        """
        try:
            with self.db.session_scope() as session:
                # Get all queued items
                queued_items = session.query(Download).filter(
                    Download.status.in_(['queued', 'searching', 'failed_no_match'])
                ).all()

                if not queued_items:
                    return

                logger.info(f"Startup check: Verifying {len(queued_items)} queued items against library...")
                removed_count = 0

                for item in queued_items:
                    try:
                        track_data = item.soul_sync_track
                        if not track_data:
                            continue

                        artist = track_data.get('artist_name') or track_data.get('artist')
                        title = track_data.get('title')

                        if not artist or not title:
                            continue

                        # Check existence using the same logic as _track_exists_in_library
                        # Re-implement inline to reuse session
                        exists = session.query(
                            session.query(Track).join(Artist).filter(
                                Artist.name.ilike(artist.strip()),
                                Track.title.ilike(title.strip())
                            ).exists()
                        ).scalar()

                        if exists:
                            logger.info(f"Removing redundant download {item.id}: '{title}' by '{artist}' is already in library")
                            session.delete(item)
                            removed_count += 1
                    except Exception as e:
                        logger.warning(f"Error checking queued item {item.id}: {e}")

                if removed_count > 0:
                    logger.info(f"Startup purge removed {removed_count} redundant items from download queue")

        except Exception as e:
            logger.error(f"Error purging existing tracks from queue: {e}")

# Global Accessor
def get_download_manager():
    return DownloadManager.get_instance()


def register_download_manager_job(interval_seconds: int | None = None):
    """
    Register download manager processing as a periodic job with the global job_queue.
    Note: The download manager already runs a continuous processing loop when started.
    This job is mainly for visibility in the jobs UI.
    
    Args:
        interval_seconds: How often the status job should appear to run. If
            ``None`` the value will be looked up from configuration (download.status_interval_seconds)
            and if still unset defaults to six hours (21600 seconds). The job is
            registered *disabled* by default since the continuous processing loop
            handles real work.
    """
    from core.job_queue import job_queue
    
    def process_downloads():
        """Status check placeholder for job visibility"""
        logger.debug("Download manager status check (continuous processing active)")
    
    if interval_seconds is None:
        # allow the administrator to override via config without touching code
        interval_seconds = config_manager.get('download', {}).get('status_interval_seconds')
        if interval_seconds is None:
            interval_seconds = 6 * 3600  # six hours

    job_queue.register_job(
        name="download_manager_status",
        func=process_downloads,
        interval_seconds=interval_seconds,
        enabled=False,  # Disabled by default since _process_loop runs continuously
        tags=["soulsync", "downloads"],
        max_retries=3
    )
    
    logger.info(
        f"Download manager status job registered (interval: {interval_seconds}s, disabled by default)"
    )
