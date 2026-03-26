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
import inspect
import logging
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_DOWNLOAD_SEARCH
from core.matching_engine.text_utils import normalize_artist, normalize_title
from core.settings import config_manager
from time_utils import utc_now
from core.provider import ProviderRegistry
from core.provider_base import ProviderBase
from database.music_database import get_database, Track, Artist, Album
from database.working_database import get_working_database, Download

logger = logging.getLogger("download_manager")

class DownloadManager:
    """
    Central orchestrator for managing the download queue and provider interactions.
    """

    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self.db = get_database()
        self.work_db = get_working_database()
        self.matcher = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)
        self._shutdown = False
        self._loop_task = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._provider: Optional[ProviderBase] = None
        self._active_providers: Dict[str, ProviderBase] = {}
        self._quality_profile_cache = None

        from core.event_bus import event_bus
        event_bus.subscribe("DOWNLOAD_INTENT", self._on_download_intent)

    def _on_download_intent(self, payload: dict) -> None:
        """Handle a DOWNLOAD_INTENT event by queueing the described track."""
        try:
            track_data = payload.get("track") or payload.get("fallback_metadata")
            if not track_data:
                logger.warning("DOWNLOAD_INTENT received with no track data; ignoring")
                return
            track = SoulSyncTrack.from_dict(track_data)
            self.queue_download(track)
        except Exception as e:
            logger.error(f"Error handling DOWNLOAD_INTENT: {e}", exc_info=True)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = DownloadManager()
        return cls._instance

    def _get_provider(self) -> Optional[ProviderBase]:
        """Lazy load the active download provider (legacy single-provider support)"""
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

    async def _invoke_provider_search(
        self,
        provider: ProviderBase,
        query: str,
        strategy_filters: Dict[str, Any],
        quality_profile: Optional[Dict[str, Any]],
    ) -> List[SoulSyncTrack]:
        """Invoke provider search while passing quality_profile when supported."""
        if hasattr(provider, '_async_search'):
            async_search = getattr(provider, '_async_search')
            try:
                sig = inspect.signature(async_search)
                if 'quality_profile' in sig.parameters:
                    return await async_search(query, strategy_filters, quality_profile=quality_profile)
            except (TypeError, ValueError):
                pass
            return await async_search(query, strategy_filters)

        loop = asyncio.get_running_loop()
        search_fn = provider.search
        try:
            sig = inspect.signature(search_fn)
            if 'quality_profile' in sig.parameters:
                return await loop.run_in_executor(
                    None,
                    lambda: search_fn(query, basic_filters=strategy_filters, quality_profile=quality_profile),
                )
        except (TypeError, ValueError):
            pass

        try:
            return await loop.run_in_executor(
                None,
                lambda: search_fn(query, basic_filters=strategy_filters),
            )
        except TypeError:
            # Final fallback for providers that do not expose slskd-style search kwargs.
            return await loop.run_in_executor(None, search_fn, query, strategy_filters)

    def _get_active_download_providers(self) -> List[ProviderBase]:
        """
        Get all active download providers sorted by user's defined priority.
        
        Returns list of provider instances in priority order (highest priority first).
        If no user priority is configured, returns all active providers in registry order.
        Automatically filters out disabled providers.
        """
        try:
            from database.config_database import get_config_database
            config_db = get_config_database()
            
            # Get all providers that support downloads
            available_providers = ProviderRegistry.get_download_clients()
            if not available_providers:
                logger.warning("No download providers available in registry")
                return []
            
            logger.debug(f"Available download providers: {available_providers}")
            
            # Get user's defined priority list
            user_priority = config_db.get_download_provider_priority()
            logger.debug(f"User-defined provider priority: {user_priority}")
            
            # Sort providers by user priority (highest priority first)
            # Providers not in user list appear at end in registry order
            sorted_names = []
            
            if user_priority:
                # Add providers in user priority order (only if available)
                for provider_name in user_priority:
                    if provider_name.lower() in [p.lower() for p in available_providers]:
                        sorted_names.append(provider_name.lower())
                
                # Add remaining providers not in user list
                for provider_name in available_providers:
                    if provider_name.lower() not in sorted_names:
                        sorted_names.append(provider_name.lower())
            else:
                # No user priority defined, use registry order
                sorted_names = [p.lower() for p in available_providers]
            
            logger.info(f"Download provider search order: {sorted_names}")
            
            # Instantiate providers in sorted order
            instances = []
            for provider_name in sorted_names:
                try:
                    if provider_name not in self._active_providers:
                        self._active_providers[provider_name] = ProviderRegistry.create_instance(provider_name)
                    instances.append(self._active_providers[provider_name])
                except Exception as e:
                    logger.warning(f"Failed to instantiate provider '{provider_name}': {e}")
            
            if not instances:
                logger.error("No download providers could be instantiated")
                return []
            
            logger.info(f"Instantiated {len(instances)} download providers in priority order")
            return instances
            
        except Exception as e:
            logger.error(f"Error getting active download providers: {e}", exc_info=True)
            return []

    def queue_download(self, track: SoulSyncTrack, quality_profile_id: Optional[str] = None) -> int:
        """
        Add a track to the download queue.
        Returns the database ID of the new download record.
        """
        logger.info(f"Queueing download: {track.artist_name} - {track.title}")

        # Check if track already exists in library (use album + duration when available)
        album_name = getattr(track, 'album_title', None) or getattr(track, 'album', None)
        duration_ms = getattr(track, 'duration', None) or getattr(track, 'duration_ms', None)
        if self._track_exists_in_library(track.artist_name, track.title, album=album_name, duration=duration_ms):
            logger.info(f"Skipping download: Track '{track.title}' by '{track.artist_name}' already exists in library")
            return 0  # 0 indicates no download created

        with self.work_db.session_scope() as session:
            # Serialize track to JSON for storage
            track_json = track.to_dict()
            if quality_profile_id:
                identifiers = track_json.setdefault("identifiers", {})
                identifiers["quality_profile_id"] = str(quality_profile_id)

            # Prevent duplicate queue entries for the same track while it is in-flight
            existing = self._find_existing_download(track_json)
            if existing:
                existing_id, existing_status = existing
                logger.info(
                    f"Duplicate download detected (ID {existing_id}, status {existing_status}); skipping enqueue"
                )
                return existing_id

            download = Download(
                sync_id=track.sync_id,
                soul_sync_track=track_json,
                status="queued",
                created_at=utc_now(),
                updated_at=utc_now()
            )
            session.add(download)
            session.flush() # Populate ID

            logger.info(f"Download queued with ID: {download.id}")
            return download.id

    async def start_background_task(self):
        """Start the background processing loop (async / auto-start path only).

        Called by backend_services.py when downloads.auto_start is True.  The
        loop runs as an asyncio Task on whatever event loop is already running.
        In the common WSGI/Flask path there is no running event loop; in that
        case the job queue drives processing via process_downloads_now() instead.
        """
        if self._loop_task:
            return
        self._shutdown = False

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.info(
                "Download Manager: no running event loop — auto-start skipped. "
                "The job queue will drive download processing via process_downloads_now()."
            )
            return

        self._loop = loop
        self._loop_task = loop.create_task(self._process_loop())
        logger.info("Download Manager background task started (shared async loop)")

    async def stop_background_task(self):
        """Stop the background processing loop."""
        self._shutdown = True
        if self._loop_task:
            try:
                await self._loop_task
            except Exception:
                pass
            self._loop_task = None
        self._loop = None
        logger.info("Download Manager background task stopped")

    async def _recover_stuck_items(self):
        """Reset items stuck in 'searching' state back to 'queued' on startup."""
        with self.work_db.session_scope() as session:
            stuck_items = session.query(Download).filter(Download.status.ilike("searching")).all()
            if stuck_items:
                logger.warning(f"Found {len(stuck_items)} stuck downloads. Resetting to 'queued'.")
                for item in stuck_items:
                    item.status = "queued"
                    item.updated_at = utc_now()
            
            # Also clean up legacy downloads with invalid provider_id format
            # These are from before the compound ID (username|filename) format was implemented
            legacy_items = session.query(Download).filter(
                Download.status.ilike("downloading"),
                Download.provider_id.isnot(None)
            ).all()
            
            cleaned = 0
            for item in legacy_items:
                if item.provider_id and '|' not in item.provider_id:
                    # Legacy format without username prefix - mark as failed
                    logger.debug(f"Cleaning up legacy download entry: {item.id}")
                    item.status = "failed_legacy_format"
                    item.updated_at = utc_now()
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
        """Pick up queued items and attempt to find/start them using waterfall provider strategy"""
        providers = self._get_active_download_providers()
        if not providers:
            logger.debug("Skipping queue processing: No active download providers.")
            return

        # Fetch queued items from DB
        queued_ids = []
        with self.work_db.session_scope() as session:
            # Get up to 30 queued items to enable concurrent searches
            # Order by created_at DESC to prioritize newer tracks first
            items = session.query(Download).filter(Download.status.ilike("queued")).order_by(Download.created_at.desc()).limit(30).all()
            if items:
                logger.info(f"Found {len(items)} queued items for processing.")

            for item in items:
                # Mark as processing so other workers (if any) don't grab it
                item.status = "searching"
                item.updated_at = utc_now()
                queued_ids.append(item.id)

        if not queued_ids:
            return

        # Create all search tasks concurrently using waterfall provider strategy
        # Each task will try providers in priority order until finding a suitable match
        tasks = []
        for download_id in queued_ids:
            logger.debug(f"Queuing download for processing: {download_id}")
            task = asyncio.create_task(self._execute_waterfall_search_and_download(download_id, providers))
            tasks.append(task)
        
        # Wait for all searches to complete
        if tasks:
            logger.info(f"Started {len(tasks)} search tasks with {len(providers)} providers in waterfall priority order")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            failed = sum(1 for r in results if isinstance(r, Exception))
            if failed > 0:
                logger.warning(f"Completed {len(tasks)} searches with {failed} errors")

    async def _execute_waterfall_search_and_download(self, download_id: int, providers: List[ProviderBase]):
        """
        Perform Waterfall Search -> Match -> Download for a single item.
        
        Algorithm:
        1. For each provider in priority order:
           - Search with all strategies
           - Get matching engine candidates
           - If perfect match (score >= 90), break and download
           - Otherwise, track best candidate and continue
        2. Download the best candidate found across all providers
        """
        target_track = None

        # Reload fresh state and reconstruct SoulSyncTrack from queue payload
        # This ensures no metadata (ISRC, Album, etc) is lost
        with self.work_db.session_scope() as session:
            download = session.query(Download).get(download_id)
            if not download:
                logger.error(f"Download ID {download_id} not found in DB.")
                return
            # Reconstruct from stored JSON to preserve all metadata
            target_track = SoulSyncTrack.from_dict(download.soul_sync_track)

        if not target_track:
            logger.error(f"Failed to deserialize track for download {download_id}")
            self._update_status(download_id, "failed")
            return

        # Re-check library existence immediately before searching. A track can enter the
        # library between enqueue-time and the moment this job fires (e.g. auto-import,
        # manual import, or a previous download cycle completing). Catching it here avoids
        # a redundant provider search and a duplicate file on disk.
        album_name = getattr(target_track, 'album_title', None) or getattr(target_track, 'album', None)
        duration_ms = getattr(target_track, 'duration', None)
        if self._track_exists_in_library(target_track.artist_name, target_track.title,
                                          album=album_name, duration=duration_ms):
            logger.info(
                f"Skipping download {download_id}: '{target_track.artist_name} – {target_track.title}' "
                f"already present in library (detected at search-time)."
            )
            self._update_status(download_id, "skipped_exists")
            return

        # Keep provider query broad; matching engine handles duration scoring/gating.
        target_duration_ms = target_track.duration if target_track.duration else None

        try:
            logger.info(f"Starting waterfall search for: {target_track.artist_name} - {target_track.title}")

            # 1. Get quality profile from config to determine allowed formats
            requested_profile_id = (
                (download.soul_sync_track.get("identifiers") or {}).get("quality_profile_id")
                if isinstance(download.soul_sync_track, dict)
                else None
            )
            quality_profile = self._get_quality_profile(requested_profile_id)
            allowed_formats = self._extract_allowed_formats(quality_profile)
            
            # Get duration tolerance from quality profile (default 5 seconds)
            duration_tolerance_ms = 5000
            if quality_profile and 'advanced_filters' in quality_profile:
                filters = quality_profile['advanced_filters']
                if 'duration_tolerance_seconds' in filters:
                    duration_tolerance_ms = int(filters['duration_tolerance_seconds'] * 1000)
            
            # Use basic filters for coarse rejection based on quality profile
            basic_filters = {
                "allowed_extensions": allowed_formats,
                "min_bitrate": self._get_min_bitrate(quality_profile),
                "target_duration_ms": target_duration_ms,
                "duration_tolerance_ms": duration_tolerance_ms
            }
            
            logger.info(f"Quality profile allows: {allowed_formats}")

            # Generate explicit fallback strategies (artist+title, album+title, title+strict duration)
            strategies = self._generate_search_strategies(target_track, duration_tolerance_ms)
            logger.info(f"Generated {len(strategies)} search strategies")

            # ============================================================================
            # WATERFALL PROVIDER SEARCH
            # ============================================================================
            # Track best candidate across all providers
            best_candidate = None
            best_score = 0.0
            winning_provider_name = None
            perfect_match_threshold = 90  # Score >= 90 triggers immediate break

            # Iterate through providers in priority order
            for provider_idx, provider in enumerate(providers, 1):
                logger.info(f"\n=== Provider {provider_idx}/{len(providers)}: {provider.name} ===")
                provider_candidates = []

                # Try all strategies for this provider
                for strategy_idx, strategy in enumerate(strategies, 1):
                    query = strategy["query"]
                    strategy_tolerance = strategy["duration_tolerance_ms"]
                    strategy_name = strategy["name"]

                    strategy_filters = dict(basic_filters)
                    strategy_filters["duration_tolerance_ms"] = strategy_tolerance

                    logger.info(
                        f"  Strategy {strategy_idx}/{len(strategies)} [{strategy_name}] "
                        f"via {provider.name}: query='{query}'"
                    )
                    
                    # Call provider search
                    search_results = []
                    try:
                        logger.debug(f"    Invoking search on {provider.name} with quality profile")
                        search_results = await self._invoke_provider_search(
                            provider,
                            query,
                            strategy_filters,
                            quality_profile,
                        )
                    except Exception as e:
                        logger.warning(f"    Search failed on {provider.name}: {e}")
                        continue

                    logger.info(f"    Strategy {strategy_idx} returned {len(search_results)} candidates")
                    
                    if search_results:
                        provider_candidates.extend(search_results)

                # Deduplicate candidates for this provider
                provider_candidates = self._deduplicate_candidates(provider_candidates)
                logger.info(f"  Total candidates from {provider.name}: {len(provider_candidates)}")

                if not provider_candidates:
                    logger.info(f"  No candidates found on {provider.name}, trying next provider...")
                    continue

                # Run matching engine on this provider's candidates
                # Quality Profile Cascading - Try each priority tier
                priority_tiers = self._get_priority_tiers(quality_profile)
                provider_best_candidate = None
                provider_best_score = 0.0
                prefer_larger_files = bool(quality_profile and quality_profile.get('prefer_larger_files'))
                
                for priority_num, priority_formats in priority_tiers:
                    # Filter by priority formats
                    tier_candidates = self._filter_by_formats(provider_candidates, priority_formats)
                    logger.debug(f"    Priority {priority_num}: {len(tier_candidates)} candidates match formats")
                    
                    if not tier_candidates:
                        continue

                    if getattr(provider, 'supports_pre_filtering', False):
                        provider_best_candidate = self._select_prefiltered_candidate(
                            tier_candidates,
                            prefer_larger_files,
                        )
                        if provider_best_candidate:
                            provider_best_score = float(perfect_match_threshold)
                            logger.info(
                                f"    Prefilter bypass on {provider.name}: selected candidate from priority {priority_num} without deep matching"
                            )
                            break
                    
                    # Get matching engine and score candidates
                    matcher = self._get_matching_engine(quality_profile)
                    candidate = matcher.select_best_download_candidate(target_track, tier_candidates)
                    
                    if candidate:
                        # We need to get the score from the matching engine
                        # Since select_best_download_candidate doesn't return score,
                        # we calculate it here
                        match_result = matcher.calculate_match(target_track, candidate)
                        provider_best_score = match_result.confidence_score
                        provider_best_candidate = candidate
                        logger.info(f"    Got match on priority {priority_num}: score={provider_best_score:.1f}")
                        break

                if provider_best_candidate and provider_best_score > 0:
                    logger.info(f"  Best match from {provider.name}: score={provider_best_score:.1f}")
                    
                    # Check if this is a perfect match (>= 90)
                    if provider_best_score >= perfect_match_threshold:
                        logger.info(f"  ✓ PERFECT MATCH from {provider.name} (score {provider_best_score:.1f} >= {perfect_match_threshold})")
                        best_candidate = provider_best_candidate
                        best_score = provider_best_score
                        winning_provider_name = provider.name
                        break  # Exit provider loop - we have a perfect match
                    
                    # Track best candidate across all providers for fallback
                    if provider_best_score > best_score:
                        logger.info(f"  New best candidate: {provider.name} (score {provider_best_score:.1f})")
                        best_candidate = provider_best_candidate
                        best_score = provider_best_score
                        winning_provider_name = provider.name
                else:
                    logger.info(f"  No acceptable match from {provider.name}")
                    continue

            # ============================================================================
            # DOWNLOAD BEST CANDIDATE
            # ============================================================================
            if not best_candidate:
                logger.warning(f"No suitable candidate matched across all {len(providers)} providers")
                self._update_status(download_id, "failed_no_match")
                return

            logger.info("**PROCEEDING WITH DOWNLOAD**")
            logger.info(f"  Track: {target_track.artist_name} - {target_track.title}")
            logger.info(f"  Provider: {winning_provider_name}")
            logger.info(f"  Match Score: {best_score:.1f}")

            # Extract download parameters
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

            # Find the provider instance to use for download
            download_provider = None
            for provider in providers:
                if provider.name.lower() == winning_provider_name.lower():
                    download_provider = provider
                    break
            
            if not download_provider:
                logger.error(f"Cannot find provider instance for {winning_provider_name}")
                self._update_status(download_id, "failed_no_provider")
                return

            # Execute download on the winning provider
            provider_id = None
            try:
                if hasattr(download_provider, '_async_download'):
                    provider_id = await download_provider._async_download(username, filename, size)
                else:
                    loop = asyncio.get_running_loop()
                    provider_id = await loop.run_in_executor(None, download_provider.download, username, filename, size)
            except Exception as e:
                logger.error(f"Error initiating download on {winning_provider_name}: {e}")
                self._update_status(download_id, "failed_start_download")
                return

            if provider_id:
                logger.info(f"Download started: {provider_id}")
                self._update_status(download_id, "downloading", provider_id)
            else:
                logger.error(f"Download provider {winning_provider_name} returned no provider_id")
                self._update_status(download_id, "failed_start_download")

        except Exception as e:
            logger.error(f"Error executing waterfall search and download {download_id}: {e}", exc_info=True)
            self._update_status(download_id, "failed_error")

    async def _check_active_downloads(self):
        """Poll providers for status of active downloads using waterfall strategy"""
        providers = self._get_active_download_providers()
        if not providers:
            return

        active_downloads = []
        with self.work_db.session_scope() as session:
            # Find items marked 'downloading'
            items = session.query(Download).filter(Download.status.ilike("downloading")).all()
            for item in items:
                active_downloads.append((item.id, item.provider_id))

        if not active_downloads:
            return

        logger.debug(f"Checking status for {len(active_downloads)} active downloads across {len(providers)} providers...")

        for db_id, provider_id in active_downloads:
            if not provider_id:
                continue

            try:
                # Try to find which provider has this download
                status = None
                found_provider = None

                for provider in providers:
                    if not hasattr(provider, '_async_get_download_status') and not hasattr(provider, 'get_download_status'):
                        continue

                    try:
                        if hasattr(provider, '_async_get_download_status'):
                            status = await provider._async_get_download_status(provider_id)
                        else:
                            loop = asyncio.get_running_loop()
                            status = await loop.run_in_executor(None, provider.get_download_status, provider_id)

                        if status:
                            found_provider = provider.name
                            logger.debug(f"  Found download {db_id} on {provider.name}")
                            break
                    except Exception as e:
                        logger.debug(f"  {provider.name} doesn't have {provider_id}: {e}")
                        continue

                if status and found_provider:
                    # Map provider status to DB status
                    remote_state = status.get('status', '').lower()

                    new_status = "downloading"
                    if remote_state == "complete":
                        new_status = "completed"
                    elif remote_state == "failed":
                        new_status = "failed"
                    elif remote_state == "queued":
                        new_status = "downloading"

                    if new_status != "downloading":
                        logger.info(f"Download {db_id} (Provider {found_provider}, ID {provider_id}) finished with status: {new_status}")
                        self._update_status(db_id, new_status)

                        if new_status == "completed":
                            logger.info(f"Download completed, removing {db_id} from queue")
                            self._remove_from_queue(db_id)
                            logger.info(f"Download {db_id} completed. TODO: Trigger Auto Import/Post-Processing.")
                else:
                    logger.info(f"Download {db_id} not found in any active provider transfers - marking as completed")
                    self._update_status(db_id, "completed")
                    self._remove_from_queue(db_id)

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
        
        # Build a core title for provider search by stripping bracketed/parenthetical
        # qualifiers, then applying standard normalization.
        search_title = self._build_core_search_title(track.title)
        
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

    def _generate_search_strategies(self, track: SoulSyncTrack, base_duration_tolerance_ms: int) -> List[Dict[str, Any]]:
        """Generate ordered search fallback strategies with per-strategy duration tolerance.

        Strategy order:
        1) artist + title
        2) album + title
        3) title only with stricter duration tolerance
        """
        strategies: List[Dict[str, Any]] = []

        # Build a core title for provider search by stripping bracketed/parenthetical
        # qualifiers, then applying standard normalization.
        search_title = self._build_core_search_title(track.title)
        if search_title != track.title:
            logger.info(f"Normalized title for search: '{track.title}' -> '{search_title}'")

        # Strategy 1: Artist + Title
        if track.artist_name and search_title:
            normalized_artist = normalize_artist(track.artist_name)
            strategies.append({
                "name": "artist+title",
                "query": f"{normalized_artist} {search_title}",
                "duration_tolerance_ms": int(base_duration_tolerance_ms),
            })

        # Strategy 2: Album + Title
        if track.album_title and search_title:
            from core.matching_engine.text_utils import normalize_album
            normalized_album = normalize_album(track.album_title)
            if normalized_album and normalized_album != search_title:
                strategies.append({
                    "name": "album+title",
                    "query": f"{normalized_album} {search_title}",
                    "duration_tolerance_ms": int(base_duration_tolerance_ms),
                })

        # Strategy 3: Title only + stricter duration window
        if search_title:
            stricter_tolerance = max(1000, int(base_duration_tolerance_ms * 0.5))
            strategies.append({
                "name": "title+strict-duration",
                "query": search_title,
                "duration_tolerance_ms": stricter_tolerance,
            })

        # De-duplicate by normalized query while preserving order and strategy metadata
        unique: List[Dict[str, Any]] = []
        seen_queries = set()
        for strategy in strategies:
            key = (strategy.get("query") or "").strip().lower()
            if key and key not in seen_queries:
                unique.append(strategy)
                seen_queries.add(key)

        return unique

    def _build_core_search_title(self, title: Optional[str]) -> str:
        """Build core query title by stripping bracketed qualifiers before normalization.

        Example:
            "Song Name (2011 Remaster) [Deluxe]" -> "song name"
        """
        if not title:
            return ""

        # Strip anything in parentheses/brackets before constructing provider query.
        core_title = re.sub(r"\s*[\(\[][^(\)\]]*[\)\]]", "", title)
        core_title = re.sub(r"\s+", " ", core_title).strip()

        # Fall back to original title if stripping removed too much.
        if not core_title:
            core_title = title

        return normalize_title(core_title)

    def _deduplicate_candidates(self, candidates: List[SoulSyncTrack]) -> List[SoulSyncTrack]:
        """Deduplicate candidates collected from multiple fallback strategies.

        Only removes true duplicates (same peer, same file path, and same core
        technical metadata). This preserves meaningful variants of the same track
        that may differ by bitrate/size/sample-rate/bit-depth.
        """
        unique: List[SoulSyncTrack] = []
        seen = set()

        for candidate in candidates:
            identifiers = getattr(candidate, 'identifiers', None) or {}
            username = identifiers.get('username') if isinstance(identifiers, dict) else None
            provider_item_id = identifiers.get('provider_item_id') if isinstance(identifiers, dict) else None

            # Include quality-relevant fields so we only collapse exact duplicate
            # observations of the same file result across fallback strategies.
            size = identifiers.get('size') if isinstance(identifiers, dict) else None
            bitrate = identifiers.get('bitrate') if isinstance(identifiers, dict) else None
            duration = getattr(candidate, 'duration', None)
            file_format = getattr(candidate, 'file_format', None)
            sample_rate = getattr(candidate, 'sample_rate', None)
            bit_depth = getattr(candidate, 'bit_depth', None)

            dedupe_key = (
                username,
                provider_item_id,
                size,
                bitrate,
                duration,
                file_format,
                sample_rate,
                bit_depth,
            )

            if provider_item_id and username and dedupe_key in seen:
                continue

            if provider_item_id and username:
                seen.add(dedupe_key)
            unique.append(candidate)

        return unique

    def _get_quality_profile(self, profile_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the active quality profile from config."""
        try:
            profiles = config_manager.get_quality_profiles()
            if not profiles:
                return None

            if profile_id is not None:
                profile_id_str = str(profile_id)
                for profile in profiles:
                    if str(profile.get("id")) == profile_id_str:
                        return profile
                logger.warning(f"Requested quality profile '{profile_id}' not found; falling back to default")

            # Use first profile by default when no specific profile is requested.
            return profiles[0]
        except Exception as e:
            logger.warning(f"Failed to load quality profile: {e}")
        return None
    
    def _get_matching_engine(self, quality_profile: Optional[Dict[str, Any]] = None) -> WeightedMatchingEngine:
        """
        Get or create the matching engine with settings from quality profile.
        If quality profile has custom settings, create a custom profile.
        Otherwise use the default PROFILE_DOWNLOAD_SEARCH.
        """
        if quality_profile is None:
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
                    
                    # Only enforce bit depth if profile has it configured (non-empty list)
                    if bit_depths:  # Profile has bit depth requirements
                        if not track.bit_depth or str(track.bit_depth) not in bit_depths:
                            # Reject: either no bit depth metadata or not in allowed list
                            continue
                    
                    # Only enforce sample rate if profile has it configured (non-empty list)
                    if sample_rates:  # Profile has sample rate requirements
                        if not track.sample_rate:
                            # Reject: no sample rate metadata
                            continue
                        # Convert to kHz string for comparison
                        sample_rate_khz = str(int(track.sample_rate / 1000))
                        if sample_rate_khz not in sample_rates:
                            # Reject: sample rate not in allowed list
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
                
                # Only enforce bit depth if profile has it configured (non-empty list)
                if bit_depths:  # Profile has bit depth requirements
                    if not track.bit_depth or str(track.bit_depth) not in bit_depths:
                        # Reject: either no bit depth metadata or not in allowed list
                        continue
                
                # Only enforce sample rate if profile has it configured (non-empty list)
                if sample_rates:  # Profile has sample rate requirements
                    if not track.sample_rate:
                        # Reject: no sample rate metadata
                        continue
                    sample_rate_khz = str(int(track.sample_rate / 1000))
                    if sample_rate_khz not in sample_rates:
                        # Reject: sample rate not in allowed list
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

    def _select_prefiltered_candidate(
        self,
        candidates: List[SoulSyncTrack],
        prefer_larger_files: bool,
    ) -> Optional[SoulSyncTrack]:
        """Choose the best candidate using lightweight quality and peer heuristics only."""
        if not candidates:
            return None

        def candidate_key(candidate: SoulSyncTrack) -> Tuple[int, int, int, int, int, int]:
            bitrate = int(candidate.identifiers.get('bitrate', 0) or 0)
            free_slots = int(candidate.identifiers.get('free_upload_slots', 0) or 0)
            upload_speed = int(candidate.identifiers.get('upload_speed', 0) or 0)
            queue_length = int(candidate.identifiers.get('queue_length', 0) or 0)
            size = int(candidate.file_size_bytes or candidate.identifiers.get('size', 0) or 0)
            size_rank = size if prefer_larger_files else -size
            provider_item_id = candidate.identifiers.get('provider_item_id', '') or ''
            return (
                bitrate,
                free_slots,
                upload_speed,
                -queue_length,
                size_rank,
                len(provider_item_id),
            )

        return max(candidates, key=candidate_key)

    def _remove_from_queue(self, download_id: int):
        """CLEANUP TASK 1: Remove a download from the queue after successful completion."""
        try:
            with self.work_db.session_scope() as session:
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
            with self.work_db.session_scope() as session:
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
        with self.work_db.session_scope() as session:
            download = session.query(Download).get(download_id)
            if download:
                download.status = (status or "").lower()
                download.updated_at = utc_now()
                if provider_id:
                    download.provider_id = provider_id

    def _find_existing_download(self, track_json: Dict[str, Any]) -> Optional[Tuple[int, str]]:
        """Return an existing active download (id, status) matching the normalized track signature."""
        signature = self._normalize_track_signature(track_json)
        if not any(signature):
            return None

        active_states = {"queued", "searching", "downloading", "QUEUED", "SEARCHING", "DOWNLOADING"}
        with self.work_db.session_scope() as session:
            items = session.query(Download).filter(Download.status.in_(active_states)).all()
            for item in items:
                other_sig = self._normalize_track_signature(item.soul_sync_track or {})
                if signature == other_sig:
                    return item.id, item.status
        return None

    def _normalize_track_signature(self, track_json: Dict[str, Any]) -> Tuple[str, str, str, Optional[int]]:
        """Build a normalized signature for duplicate detection."""
        artist = normalize_artist(track_json.get("artist_name") or track_json.get("artist") or "")
        title = normalize_title(track_json.get("title") or track_json.get("raw_title") or "")

        # Album may be present under several keys
        album_raw = track_json.get("album_title") or track_json.get("album") or track_json.get("album_title_raw") or ""
        try:
            from core.matching_engine.text_utils import normalize_album
            album = normalize_album(album_raw)
        except Exception:
            album = (album_raw or "").strip()

        duration = track_json.get("duration")
        if duration is None:
            duration = track_json.get("duration_ms")
        if isinstance(duration, float):
            duration = int(duration)

        # Return full signature: artist, title, album, duration
        return artist or "", title or "", album or "", duration

    def get_status(self, download_id: int) -> Optional[Dict]:
        """Get status for UI"""
        with self.work_db.session_scope() as session:
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

    def _track_exists_in_library(self, artist_name: str, title: str, album: Optional[str] = None, duration: Optional[int] = None) -> bool:
        """
        Check if a track already exists in the library (database).
        """
        if not artist_name or not title:
            return False

        try:
            with self.db.session_scope() as session:
                # Base filters: artist + title
                filters = [Artist.name.ilike(artist_name.strip()), Track.title.ilike(title.strip())]

                # If album provided, filter by album title as well
                if album:
                    try:
                        filters.append(Track.album.has(Album.title.ilike(album.strip())))
                    except Exception:
                        # Fallback: ignore album constraint if relationship lookup fails
                        pass

                # If duration provided, allow a small tolerance window (2s) to match
                if duration is not None:
                    try:
                        tol = 2000
                        min_d = int(duration) - tol
                        max_d = int(duration) + tol
                        filters.append(Track.duration.between(min_d, max_d))
                    except Exception:
                        pass

                exists = session.query(
                    session.query(Track).join(Artist).filter(*filters).exists()
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
            with self.work_db.session_scope() as session:
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
                        album = track_data.get('album_title') or track_data.get('album')
                        duration = track_data.get('duration') or track_data.get('duration_ms')

                        if not artist or not title:
                            continue

                        # Check existence using the same logic as _track_exists_in_library (inline to reuse session)
                        filters = [Artist.name.ilike(artist.strip()), Track.title.ilike(title.strip())]
                        if album:
                            try:
                                filters.append(Track.album.has(Album.title.ilike(album.strip())))
                            except Exception:
                                pass
                        if duration is not None:
                            try:
                                tol = 2000
                                min_d = int(duration) - tol
                                max_d = int(duration) + tol
                                filters.append(Track.duration.between(min_d, max_d))
                            except Exception:
                                pass

                        db = get_database()
                        with db.session_scope() as music_session:
                            exists = music_session.query(
                                music_session.query(Track).join(Artist).filter(*filters).exists()
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

    def process_downloads_now(self):
        """Run one processing cycle.  Safe to call from any sync context.

        When the async auto-start loop is active (``self._loop`` set by
        ``start_background_task``), the cycle is submitted to that loop so it
        does not conflict with the running Task.  Otherwise a fresh event loop
        is created via ``asyncio.run()`` — this is the normal path taken by the
        JobQueue and HTTP route triggers.
        """
        if self._loop and self._loop.is_running():
            # Auto-start mode: submit into the existing event loop.
            async def _manual_pass():
                requeued = self._requeue_retryable_failed_items(limit=50)
                if requeued > 0:
                    logger.info(f"Manual run: re-queued {requeued} retryable failed items")
                await self._process_queued_items()
                await self._check_active_downloads()
                logger.info("Manual download processing completed")

            asyncio.run_coroutine_threadsafe(_manual_pass(), self._loop)
            logger.info("Download processing triggered on existing event loop")
            return

        # No persistent loop — run a self-contained one-shot cycle.
        async def _one_pass():
            requeued = self._requeue_retryable_failed_items(limit=50)
            if requeued > 0:
                logger.info(f"Manual run: re-queued {requeued} retryable failed items")
            await self._recover_stuck_items()
            self._purge_existing_tracks_from_queue()
            await self._process_queued_items()
            await self._check_active_downloads()
            logger.info("Download processing cycle complete")

        try:
            asyncio.run(_one_pass())
        except Exception as e:
            logger.error(f"Download processing cycle failed: {e}", exc_info=True)

    def _requeue_retryable_failed_items(self, limit: int = 50) -> int:
        """Move retryable failed items back to queued so manual runs can re-attempt them.
        
        Prioritizes NEWEST tracks first (DESC by created_at) so most recent failures are retried first.
        Also increments retry_count to track retry attempts.
        """
        retryable_statuses = {
            "failed_no_results",
            "failed_no_match",
            "failed_start_download",
            "failed_error",
            "failed_no_username",
            "failed_no_filename",
            "failed",
        }

        requeued = 0
        with self.work_db.session_scope() as session:
            items = (
                session.query(Download)
                .filter(Download.status.in_(retryable_statuses))
                .order_by(Download.created_at.desc())  # Newest first
                .limit(limit)
                .all()
            )

            for item in items:
                item.status = "queued"
                item.provider_id = None
                item.retry_count = (item.retry_count or 0) + 1
                item.updated_at = utc_now()
                requeued += 1

        logger.info(f"Re-queued {requeued} failed items for retry (prioritizing newest first)")
        return requeued

# Global Accessor
def get_download_manager():
    return DownloadManager.get_instance()


def register_download_manager_job(interval_seconds: int = 21600):
    """
    Register download manager processing as a periodic job with the global job_queue.
    The download manager runs a continuous processing loop, but this job allows manual
    triggering from the Jobs UI to process queued downloads immediately.
    
    Args:
        interval_seconds: Interval between automatic job runs (default 6 hours = 21600s)
    """
    from core.job_queue import job_queue, unregister_job
    
    def process_downloads():
        """Run one full download processing cycle driven by the job queue."""
        dm = get_download_manager()
        dm.process_downloads_now()
    
    unregister_job("download_manager_status")

    job_queue.register_job(
        name="download_manager",
        func=process_downloads,
        interval_seconds=interval_seconds,
        start_after=interval_seconds,
        enabled=True,
        tags=["soulsync", "downloads"],
        max_retries=3
    )

    logger.info(
        f"Download manager job registered (name: download_manager, interval: {interval_seconds}s, first run after startup: {interval_seconds}s)"
    )
