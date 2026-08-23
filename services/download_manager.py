"""
DownloadQueue Manager Service - Central Orchestrator for DownloadQueues

This service acts as the "Source of Truth" for all downloads in Echosync.
It manages the download lifecycle:
1. Queueing: Accepts EchosyncTrack objects
2. Selection: Uses SlskdProvider (Atomic Search) + Matching Engine (Selection)
3. Execution: Triggers download on Slskd
4. Monitoring: Polls for status and updates DB
5. Persistence: Stores state in 'downloads' table

Design Principle: "Central Control"
- Consumers (UI, SyncService) ask this manager to download.
- This manager tells the Dumb Provider what to do.
"""

import asyncio
from dataclasses import dataclass
import inspect
from core.enums import Capability
from core.hook_manager import hook_manager
import logging
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from core.db.echo_sync_track import EchosyncTrack
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_DOWNLOAD_SEARCH
from core.matching_engine.track_parser import TrackParser
from core.matching_engine.text_utils import (
    normalize_artist,
    normalize_title,
    extract_version_info,
    extract_edition,
    split_artist_collaborators,
    sanitize_query_for_wire,
)
from core.settings import config_manager
from time_utils import utc_now
from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
from core.nexus_framework.plugin_SDK import PluginBase
from database.music_database import get_database, Track, Artist, Album
from database.working_database import get_working_database, DownloadQueue

logger = logging.getLogger("download_manager")

@dataclass
class SearchStrategyIntent:
    id: str
    name: str
    strategy_type: str
    wire_query: str
    filter_expression: Optional[str] = None
    includes: Optional[List[str]] = None
    excludes: Optional[List[str]] = None
    required_capability: Optional[Capability] = None
    target_duration_ms: Optional[int] = None
    duration_tolerance_ms: int = 3000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "strategy_type": self.strategy_type,
            "query": self.wire_query,
            "wire_query": self.wire_query,
            "filter_expression": self.filter_expression,
            "includes": self.includes,
            "excludes": self.excludes,
            "required_capability": self.required_capability,
            "duration_tolerance_ms": self.duration_tolerance_ms,
            "target_duration_ms": self.target_duration_ms,
        }

    def __getitem__(self, key: str) -> Any:
        if key == "query":
            return self.wire_query
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "query":
            return self.wire_query
        return getattr(self, key, default)


def _provider_supports_capability(provider: Any, capability: Optional[Capability]) -> bool:
    """Check if provider advertises the required capability."""
    if capability is None:
        return True
    caps = getattr(provider, 'capabilities', None)
    if hasattr(caps, 'to_enum_list') and callable(getattr(caps, 'to_enum_list')):
        enum_list = caps.to_enum_list()
        if isinstance(enum_list, list):
            return capability in enum_list
    if isinstance(caps, list):
        return capability in caps
    if hasattr(provider, 'supports_capability') and callable(getattr(provider, 'supports_capability')):
        res = provider.supports_capability(capability)
        if isinstance(res, bool):
            return res
    if capability == Capability.CLIENT_PREFILTER:
        sup = getattr(provider, 'supports_pre_filtering', None)
        if sup is not None and isinstance(sup, bool):
            return sup
        caps_sup = getattr(getattr(provider, 'capabilities', None), 'supports_pre_filtering', None)
        if caps_sup is not None and isinstance(caps_sup, bool):
            return caps_sup
    if capability == Capability.FETCH_BY_ISRC:
        sup = getattr(provider, 'supports_isrc', None)
        if sup is not None and isinstance(sup, bool):
            return sup
        caps_sup = getattr(getattr(provider, 'capabilities', None), 'supports_isrc_lookup', None)
        if caps_sup is not None and isinstance(caps_sup, bool):
            return caps_sup
    return False



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
        self._stop_requested = False
        self._loop_task = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._provider: Optional[PluginBase] = None
        self._active_providers: Dict[str, PluginBase] = {}
        self._quality_profile_cache = None

        from core.event_bus import event_bus
        event_bus.subscribe("DOWNLOAD_INTENT", self._on_download_intent)
        event_bus.subscribe("TRACK_IMPORTED", self._on_track_imported)

    def _on_track_imported(self, payload: dict) -> None:
        """
        Handle a TRACK_IMPORTED event by cancelling active/pending downloads
        matching the imported track's signature.
        """
        try:
            track_data = payload.get("track")
            if not track_data:
                logger.warning("TRACK_IMPORTED received with no track data; ignoring")
                return

            track = EchosyncTrack.from_dict(track_data)
            logger.info(f"TRACK_IMPORTED: {track.artist_name} - {track.title}. Checking queue for duplicates.")

            target_sig = self._normalize_track_signature(track.to_dict())
            if not any(target_sig):
                logger.warning("Cannot build signature for imported track")
                return

            active_states = {"queued", "searching", "downloading"}
            cancelled_count = 0

            with self.work_db.session_scope() as session:
                offset = 0
                batch_size = 25
                while True:
                    items = (
                        session.query(DownloadQueue)
                        .filter(DownloadQueue.status.in_(active_states))
                        .order_by(DownloadQueue.id.asc())
                        .offset(offset)
                        .limit(batch_size)
                        .all()
                    )
                    if not items:
                        break

                    for item in items:
                        item_sig = self._normalize_track_signature(item.echo_sync_track or {})
                        # Match on ISRC if present
                        target_isrc = track.isrc
                        item_isrc = (item.echo_sync_track or {}).get("isrc")

                        is_match = False
                        if target_isrc and item_isrc and target_isrc == item_isrc:
                            is_match = True
                        elif target_sig[0] and item_sig[0] and target_sig[1] and item_sig[1]:
                            if target_sig[0] == item_sig[0] and target_sig[1] == item_sig[1]:
                                if target_sig[3] is not None and item_sig[3] is not None:
                                    if abs(int(target_sig[3]) - int(item_sig[3])) <= 2000:
                                        is_match = True
                                else:
                                    is_match = True

                        if is_match:
                            logger.info(f"Purging download {item.id} matching imported track '{track.title}'")

                            if item.status == 'downloading' and item.provider_id:
                                providers = self._get_active_download_providers()
                                for p in providers:
                                    try:
                                        if hasattr(p, 'cancel_download'):
                                            p.cancel_download(item.provider_id)
                                        elif hasattr(p, '_async_cancel_download'):
                                            loop = asyncio.get_running_loop()
                                            loop.create_task(p._async_cancel_download(item.provider_id))
                                    except Exception as ce:
                                        logger.debug(f"Failed to cancel remote transfer {item.provider_id}: {ce}")

                            session.delete(item)
                            cancelled_count += 1
                    offset += batch_size

            if cancelled_count > 0:
                logger.info(f"Cancelled {cancelled_count} queued downloads for newly imported track.")

        except Exception as e:
            logger.error(f"Error handling TRACK_IMPORTED: {e}", exc_info=True)

    def _on_download_intent(self, payload: dict) -> None:
        """Handle a DOWNLOAD_INTENT event by queueing the described track."""
        try:
            track_data = payload.get("track") or payload.get("fallback_metadata")
            if not track_data:
                logger.warning("DOWNLOAD_INTENT received with no track data; ignoring")
                return
            track = EchosyncTrack.from_dict(track_data)
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
    async def _invoke_provider_search(
        self,
        provider: PluginBase,
        query: str,
        strategy_filters: Dict[str, Any],
        quality_profile: Optional[Dict[str, Any]],
        target_track: Optional[EchosyncTrack] = None,
        strategy_name: str = "",
        perfect_match_threshold: int = 90,
        includes: Optional[List[str]] = None,
        excludes: Optional[List[str]] = None,
    ) -> Tuple[List[EchosyncTrack], bool]:
        """Search a single provider for one strategy query, expanding via hooks.

        Returns ``(results, sniper_hit)`` where ``sniper_hit=True`` means a
        candidate scoring >= *perfect_match_threshold* was found during variant
        iteration and all remaining query variants were short-circuited.
        The caller should break its own strategy loop when ``sniper_hit`` is True.
        """
        query_or_queries = hook_manager.apply_filters(
            'pre_provider_search',
            query,
            strategy_name=strategy_name,
            artist_name=getattr(target_track, 'artist_name', "") or "",
            title=getattr(target_track, 'title', "") or "",
        )
        queries = query_or_queries if isinstance(query_or_queries, list) else [query_or_queries]

        # dict.fromkeys: order-preserving deduplication — respects the CJK priority matrix
        ordered_queries = list(dict.fromkeys(
            q for q in queries if isinstance(q, str) and q.strip()
        ))

        accumulated: List[EchosyncTrack] = []
        for q in ordered_queries:
            batch = await self._invoke_provider_search_single(
                provider, q, strategy_filters, quality_profile,
                includes=includes, excludes=excludes,
            )
            if not batch:
                continue

            # Evaluation-driven short-circuit: score this batch immediately.
            # If a qualifying candidate is found, skip all remaining variants.
            if target_track is not None:
                hit = self._evaluate_search_batch(
                    batch, target_track, quality_profile, perfect_match_threshold
                )
                if hit is not None:
                    remaining = len(ordered_queries) - ordered_queries.index(q) - 1
                    if remaining > 0:
                        logger.info(
                            "\u26a1 Sniper hit on variant %r (score\u2265%d) "
                            "\u2014 skipping %d remaining variant(s).",
                            q, perfect_match_threshold, remaining,
                        )
                    return [hit], True

            accumulated.extend(batch)
        return accumulated, False

    def _enrich_candidate_metadata(self, candidate: EchosyncTrack) -> EchosyncTrack:
        """Centralized Path & Metadata Enrichment for raw candidates.
        
        Extracts structured artist, title, album, version, and edition metadata
        from candidate media file path, raw_title, or identifiers using TrackParser
        and text utilities.
        """
        if not candidate:
            return candidate

        # Determine path or filename to parse
        file_path = None
        if getattr(candidate, 'media', None) and len(candidate.media) > 0 and getattr(candidate.media[0], 'file_path', None):
            file_path = candidate.media[0].file_path
        elif candidate.identifiers and candidate.identifiers.get('plugin_item_id'):
            file_path = candidate.identifiers.get('plugin_item_id')
        elif candidate.identifiers and candidate.identifiers.get('provider_item_id'):
            file_path = candidate.identifiers.get('provider_item_id')
        elif candidate.raw_title:
            file_path = candidate.raw_title

        if file_path:
            if not hasattr(self, '_track_parser') or self._track_parser is None:
                self._track_parser = TrackParser()
            parsed = self._track_parser.parse_filename(file_path)
            if parsed:
                parsed_artist = getattr(parsed, 'artist_name', None) or getattr(parsed, 'artist', None)
                parsed_title = getattr(parsed, 'title', None) or getattr(parsed, 'raw_title', None)
                parsed_album = getattr(parsed, 'album_title', None) or getattr(parsed, 'album', None)

                if parsed_artist and (not candidate.artist_name or candidate.artist_name == "Unknown Artist"):
                    candidate.artist_name = parsed_artist
                if parsed_title:
                    candidate.title = parsed_title
                    candidate.raw_title = parsed_title
                if parsed_album and not getattr(candidate, 'album_title', None):
                    candidate.album_title = parsed_album
                if getattr(parsed, 'release_year', None) and not getattr(candidate, 'release_year', None):
                    candidate.release_year = parsed.release_year
                if getattr(parsed, 'track_number', None) and not getattr(candidate, 'track_number', None):
                    candidate.track_number = parsed.track_number
                if getattr(parsed, 'disc_number', None) and not getattr(candidate, 'disc_number', None):
                    candidate.disc_number = parsed.disc_number

        # Version and edition extraction from title / raw_title / file_path
        title_for_version = candidate.raw_title or candidate.title or file_path or ""
        
        # Version info (e.g. Remix, Acoustic)
        clean_v_title, version_str = extract_version_info(title_for_version)
        if version_str:
            candidate.version = version_str
            if not getattr(candidate, 'edition', None):
                candidate.edition = version_str

        # Edition info (e.g. Remastered, Deluxe, Live)
        clean_e_title, edition_str = extract_edition(title_for_version)
        if edition_str:
            candidate.edition = edition_str
            if not getattr(candidate, 'version', None):
                candidate.version = edition_str

        return candidate

    def _evaluate_search_batch(
        self,
        batch: List[EchosyncTrack],
        target_track: EchosyncTrack,
        quality_profile: Optional[Dict[str, Any]],
        threshold: float,
    ) -> Optional[EchosyncTrack]:
        """Run tier filtering + matching on a raw result batch.

        Returns the best candidate if ``confidence_score >= threshold``, else
        ``None``.  Used by the evaluation-driven short-circuit so that
        remaining query variants are skipped as soon as a perfect match is
        found within the current variant's result set.
        """
        enriched_batch = [self._enrich_candidate_metadata(c) for c in batch]
        priority_tiers = self._get_priority_tiers(quality_profile)
        matcher = self._get_matching_engine(quality_profile)
        for _priority_num, priority_formats in priority_tiers:
            tier_candidates = self._filter_by_formats(enriched_batch, priority_formats)
            if not tier_candidates:
                continue
            candidate = matcher.select_best_download_candidate(target_track, tier_candidates)
            if candidate:
                match_result = matcher.calculate_match(target_track, candidate)
                if match_result.confidence_score >= threshold:
                    return candidate
        return None

    async def _invoke_provider_search_single(
        self,
        provider: PluginBase,
        query: str,
        strategy_filters: Dict[str, Any],
        quality_profile: Optional[Dict[str, Any]],
        includes: Optional[List[str]] = None,
        excludes: Optional[List[str]] = None,
    ) -> List[EchosyncTrack]:
        """Invoke provider search while passing quality_profile when supported."""

        if hasattr(provider, '_async_search'):
            async_search = getattr(provider, '_async_search')
            try:
                sig = inspect.signature(async_search)
                kwargs: Dict[str, Any] = {}
                if 'quality_profile' in sig.parameters:
                    kwargs['quality_profile'] = quality_profile
                if 'includes' in sig.parameters:
                    kwargs['includes'] = includes
                if 'excludes' in sig.parameters:
                    kwargs['excludes'] = excludes
                return await async_search(query, strategy_filters, **kwargs)
            except (TypeError, ValueError):
                pass
            return await async_search(query, strategy_filters)

        loop = asyncio.get_running_loop()
        search_fn = provider.search
        try:
            sig = inspect.signature(search_fn)
            call_kwargs: Dict[str, Any] = {'basic_filters': strategy_filters}
            if 'quality_profile' in sig.parameters:
                call_kwargs['quality_profile'] = quality_profile
            if 'includes' in sig.parameters:
                call_kwargs['includes'] = includes
            if 'excludes' in sig.parameters:
                call_kwargs['excludes'] = excludes
            return await loop.run_in_executor(
                None,
                lambda: search_fn(query, **call_kwargs),
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

    def _get_active_download_providers(self) -> List[PluginBase]:
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
            available_providers = PluginRegistry.get_download_clients()
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
                from core.nexus_framework.plugin_loader import generate_plugin_id
                # Add providers in user priority order (only if available)
                for provider_name in user_priority:
                    # Convert string from config into int ID
                    p_id = generate_plugin_id(provider_name.lower())
                    if p_id in available_providers:
                        sorted_names.append(p_id)
                
                # Add remaining providers not in user list
                for provider_id in available_providers:
                    if provider_id not in sorted_names:
                        sorted_names.append(provider_id)
            else:
                # No user priority defined, use registry order
                sorted_names = available_providers
            
            logger.info(f"DownloadQueue provider search order: {sorted_names}")
            
            # Instantiate providers in sorted order
            instances = []
            for provider_id in sorted_names:
                try:
                    if provider_id not in self._active_providers:
                        self._active_providers[provider_id] = PluginRegistry.create_instance(provider_id)
                    instances.append(self._active_providers[provider_id])
                except Exception as e:
                    logger.warning(f"Failed to instantiate provider '{provider_id}': {e}")
            
            if not instances:
                logger.error("No download providers could be instantiated")
                return []
            
            logger.info(f"Instantiated {len(instances)} download providers in priority order")
            return instances
            
        except Exception as e:
            logger.error(f"Error getting active download providers: {e}", exc_info=True)
            return []

    def queue_download(self, track: EchosyncTrack, quality_profile_id: Optional[str] = None) -> int:
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

            download = DownloadQueue(
                sync_id=track.sync_id,
                echo_sync_track=track_json,
                status="queued",
                created_at=utc_now(),
                updated_at=utc_now()
            )
            session.add(download)
            session.flush() # Populate ID

            logger.info(f"DownloadQueue queued with ID: {download.id}")
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
                "DownloadQueue Manager: no running event loop — auto-start skipped. "
                "The job queue will drive download processing via process_downloads_now()."
            )
            return

        self._loop = loop
        self._loop_task = loop.create_task(self._process_loop())
        logger.info("DownloadQueue Manager background task started (shared async loop)")

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
        logger.info("DownloadQueue Manager background task stopped")

    async def _recover_stuck_items(self):
        """Reset items stuck in 'searching' or 'downloading' state back to 'queued' on startup."""
        with self.work_db.session_scope() as session:
            stuck_items = (
                session.query(DownloadQueue)
                .filter(DownloadQueue.status.in_(["searching", "downloading", "SEARCHING", "DOWNLOADING"]))
                .all()
            )
            if stuck_items:
                logger.warning(f"Found {len(stuck_items)} stuck downloads (searching/downloading). Resetting to 'queued'.")
                for item in stuck_items:
                    item.status = "queued"
                    item.provider_id = None
                    item.updated_at = utc_now()

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

                # 2. Check Active DownloadQueues
                await self._check_active_downloads()

                # 3. Sleep
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in DownloadManager loop: {e}", exc_info=True)
                await asyncio.sleep(10) # Backoff on error

    async def _process_queued_items(self):
        """Pick up queued items and attempt to find/start them using waterfall provider strategy"""
        if not hasattr(self, '_processing_queue_lock') or self._processing_queue_lock is None:
            self._processing_queue_lock = asyncio.Lock()

        if self._processing_queue_lock.locked():
            logger.debug("Queue processing already in progress; skipping duplicate run.")
            return

        async with self._processing_queue_lock:
            providers = self._get_active_download_providers()
            if not providers:
                logger.debug("Skipping queue processing: No active download providers.")
                return

            # Fetch queued items from DB
            queued_ids = []
            with self.work_db.session_scope() as session:
                # Get up to 30 queued items to enable concurrent searches
                items = (
                    session.query(DownloadQueue)
                    .filter(DownloadQueue.status.ilike("queued"))
                    .order_by(
                        DownloadQueue.retry_count.asc().nullsfirst(),
                        DownloadQueue.created_at.desc()
                    )
                    .limit(30)
                    .all()
                )

                if items:
                    logger.info(f"Found {len(items)} queued items for processing.")

                for item in items:
                    track_dict = item.echo_sync_track or {}
                    artist = normalize_artist(track_dict.get("artist_name") or track_dict.get("artist") or "")
                    title = normalize_title(track_dict.get("title") or track_dict.get("raw_title") or "")
                    album = track_dict.get("album_title") or track_dict.get("album")
                    duration = track_dict.get("duration") or track_dict.get("duration_ms")

                    # JIT check: if track already in library, mark completed and bypass search
                    if artist and title and self._track_exists_in_library(artist, title, album=album, duration=duration):
                        logger.info(f"JIT Check: Track '{artist} - {title}' already exists in library. Transitioning status to 'completed'.")
                        item.status = "completed"
                        item.updated_at = utc_now()
                        continue

                    # Mark as processing so other workers (if any) don't grab it
                    item.status = "searching"
                    item.updated_at = utc_now()
                    queued_ids.append(item.id)

            if not queued_ids:
                return

            # Determine concurrency dynamically from active provider capabilities
            if providers:
                provider = providers[0]
                concurrency = getattr(provider.capabilities, 'max_concurrency', 3) if hasattr(provider, 'capabilities') else 3
            else:
                concurrency = 3
            semaphore = asyncio.Semaphore(concurrency)

            async def _throttled_download(download_id):
                async with semaphore:
                    return await self._execute_waterfall_search_and_download(download_id, providers)

            # Dispatch tasks via asyncio.gather with concurrency throttling
            tasks = [asyncio.create_task(_throttled_download(did)) for did in queued_ids]
            
            # Wait for all searches to complete
            if tasks:
                logger.info(f"Started {len(tasks)} search tasks (throttled to {concurrency} concurrent) with {len(providers)} providers in waterfall priority order")
                results = await asyncio.gather(*tasks, return_exceptions=True)
                failed = sum(1 for r in results if isinstance(r, Exception))
                if failed > 0:
                    logger.warning(f"Completed {len(tasks)} searches with {failed} errors")

    async def _execute_waterfall_search_and_download(self, download_id: int, providers: List[PluginBase]):
        """
        Perform Waterfall Search -> Match -> DownloadQueue for a single item.
        
        Algorithm:
        1. For each provider in priority order:
           - Search with all strategies
           - Get matching engine candidates
           - If perfect match (score >= 90), break and download
           - Otherwise, track best candidate and continue
        2. DownloadQueue the best candidate found across all providers
        """
        target_track = None

        # Reload fresh state and reconstruct EchosyncTrack from queue payload
        # This ensures no metadata (ISRC, Album, etc) is lost
        with self.work_db.session_scope() as session:
            download = session.query(DownloadQueue).get(download_id)
            if not download:
                logger.error(f"DownloadQueue ID {download_id} not found in DB.")
                return
            # Reconstruct from stored JSON to preserve all metadata
            target_track = EchosyncTrack.from_dict(download.echo_sync_track)
            raw_track_dict = download.echo_sync_track if isinstance(download.echo_sync_track, dict) else {}
            blacklisted_candidates = set(raw_track_dict.get('blacklisted_candidates') or [])

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
            logger.info(f"JIT Check: Track '{target_track.artist_name} - {target_track.title}' already present in library. Transitioning status to 'completed'.")
            self._update_status(download_id, "completed")
            return

        # Keep provider query broad; matching engine handles duration scoring/gating.
        target_duration_ms = target_track.duration if target_track.duration else None

        try:
            logger.info(f"Starting waterfall search for: {target_track.artist_name} - {target_track.title}")

            # 1. Get quality profile from config to determine allowed formats
            requested_profile_id = (
                (download.echo_sync_track.get("identifiers") or {}).get("quality_profile_id")
                if isinstance(download.echo_sync_track, dict)
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
            scored_candidates: List[Tuple[EchosyncTrack, float, PluginBase]] = []
            perfect_match_threshold = 90  # Score >= 90 triggers immediate break

            # Iterate through providers in priority order
            for provider_idx, provider in enumerate(providers, 1):
                logger.info(f"\n=== Provider {provider_idx}/{len(providers)}: {provider.name} ===")
                provider_candidates = []

                # Filter strategy ladder against this provider's capabilities
                provider_strategies = [
                    s for s in strategies
                    if _provider_supports_capability(
                        provider,
                        getattr(s, 'required_capability', None) if not isinstance(s, dict) else s.get('required_capability')
                    )
                ]
                logger.info(f"Provider {provider.name} supports {len(provider_strategies)}/{len(strategies)} strategies")
                if not provider_strategies:
                    logger.info(f"Provider {provider.name} supports none of the requested strategies, skipping...")
                    continue

                matcher = self._get_matching_engine(quality_profile)

                # Try all supported strategies for this provider
                sniper_winner: Optional[EchosyncTrack] = None
                for strategy_idx, strategy in enumerate(provider_strategies, 1):
                    # Cooperative Cancellation Check: terminate early if requested
                    try:
                        from core.task_manager.supervisor import supervisor as _sup
                        is_cancelled = _sup.is_process_cancelled(reg_id) if _sup else False
                    except Exception:
                        is_cancelled = False
                    if is_cancelled or getattr(self, '_stop_requested', False) or getattr(self, '_shutdown', False):
                        logger.info(f"Download {download_id} aborted by cancellation request.")
                        self._update_status(download_id, "failed")
                        return

                    query = getattr(strategy, 'wire_query', None) or (strategy["query"] if isinstance(strategy, dict) else "")
                    strategy_tolerance = getattr(strategy, 'duration_tolerance_ms', None) or (strategy["duration_tolerance_ms"] if isinstance(strategy, dict) else duration_tolerance_ms)
                    strategy_name = getattr(strategy, 'name', None) or (strategy["name"] if isinstance(strategy, dict) else "")
                    strategy_includes = getattr(strategy, 'includes', None) or (strategy.get("includes") if isinstance(strategy, dict) else None)
                    strategy_excludes = getattr(strategy, 'excludes', None) or (strategy.get("excludes") if isinstance(strategy, dict) else None)
                    strategy_filter_expr = getattr(strategy, 'filter_expression', None) or (strategy.get("filter_expression") if isinstance(strategy, dict) else None)

                    strategy_filters = dict(basic_filters)
                    strategy_filters["duration_tolerance_ms"] = strategy_tolerance
                    if strategy_filter_expr:
                        strategy_filters["filter_expression"] = strategy_filter_expr

                    logger.info(
                        f"  Strategy {strategy_idx}/{len(provider_strategies)} [{strategy_name}] "
                        f"via {provider.name}: query='{query}'"
                    )

                    # Call provider search (evaluation-driven short-circuit)
                    search_results: List[EchosyncTrack] = []
                    sniper_hit = False
                    try:
                        logger.debug(f"    Invoking search on {provider.name} with quality profile")
                        search_results, sniper_hit = await self._invoke_provider_search(
                            provider,
                            query,
                            strategy_filters,
                            quality_profile,
                            target_track=target_track,
                            strategy_name=strategy_name,
                            perfect_match_threshold=perfect_match_threshold,
                            includes=strategy_includes,
                            excludes=strategy_excludes,
                        )
                    except Exception as e:
                        logger.warning(
                            f"    Strategy {strategy_idx} [{strategy_name}] failed on {provider.name}: {e}. "
                            f"Advancing to Strategy {strategy_idx + 1}"
                        )
                        continue

                    if not search_results:
                        logger.info(
                            f"    Strategy {strategy_idx} returned 0 candidates, advancing to Strategy {strategy_idx + 1}"
                        )
                        continue

                    logger.info(f"    Strategy {strategy_idx} returned {len(search_results)} candidates")

                    if sniper_hit and search_results:
                        first_cand = search_results[0]
                        pid = first_cand.identifiers.get('plugin_item_id') or first_cand.identifiers.get('provider_item_id')
                        username = first_cand.identifiers.get('username')
                        comp_id = f"{username}|{pid}" if username and pid else None
                        if (pid and pid in blacklisted_candidates) or (comp_id and comp_id in blacklisted_candidates):
                            logger.info(f"    Sniper hit candidate '{pid}' is blacklisted; ignoring sniper bypass.")
                            sniper_hit = False
                        else:
                            logger.info(
                                f"  ⚡ SNIPER HIT at strategy {strategy_idx} [{strategy_name}] "
                                f"— short-circuiting remaining strategies."
                            )
                            sniper_winner = self._enrich_candidate_metadata(first_cand)
                            break

                    if search_results:
                        valid_results = []
                        for c in search_results:
                            pid = c.identifiers.get('plugin_item_id') or c.identifiers.get('provider_item_id')
                            username = c.identifiers.get('username')
                            comp_id = f"{username}|{pid}" if username and pid else None
                            if (pid and pid in blacklisted_candidates) or (comp_id and comp_id in blacklisted_candidates):
                                logger.info(f"    Skipping blacklisted candidate '{pid}' from user '{username}'")
                                continue
                            c.identifiers['discovery_strategy'] = getattr(strategy, 'strategy_type', None) or (strategy.get('strategy_type') if isinstance(strategy, dict) else None) or strategy_name
                            c.identifiers['strategy_name'] = strategy_name
                            valid_results.append(c)
                        enriched_results = [self._enrich_candidate_metadata(c) for c in valid_results]
                        provider_candidates.extend(enriched_results)

                        # Check early short-circuit conditions on candidate pool
                        viable_matches = 0
                        has_snipe_match = False
                        for cand in enriched_results:
                            # Only count candidates whose audio format is allowed by the quality profile
                            cand_format = None
                            if getattr(cand, 'media', None) and len(cand.media) > 0 and getattr(cand.media[0], 'file_format', None):
                                cand_format = cand.media[0].file_format.lower()
                            if allowed_formats and (not cand_format or cand_format not in allowed_formats):
                                continue

                            match_res = matcher.calculate_match(target_track, cand, context="download")
                            raw_score = match_res.confidence_score
                            if raw_score >= perfect_match_threshold:
                                has_snipe_match = True
                            if raw_score >= 75.0:
                                viable_matches += 1

                        if has_snipe_match or viable_matches >= 3:
                            logger.info(
                                f"  ⚡ Early short-circuit: Strategy {strategy_idx} yielded viable candidates "
                                f"(has_snipe={has_snipe_match}, viable_matches={viable_matches}) "
                                f"— skipping remaining strategies on {provider.name}."
                            )
                            break

                matcher = self._get_matching_engine(quality_profile)

                # ── Fast-path: sniper winner bypasses full dedup + scoring ────────────
                if sniper_winner is not None:
                    match_result = matcher.calculate_match(
                        target_track, sniper_winner, context="download"
                    )
                    raw_score = match_result.confidence_score
                    strat = sniper_winner.identifiers.get('discovery_strategy') or sniper_winner.identifiers.get('strategy_name') or 'strict_metadata'
                    logger.info(
                        f"  Sniper winner confirmed: raw_score={raw_score:.1f} "
                        f"from {provider.name} (strategy={strat})"
                    )
                    if raw_score >= 70.0:
                        scored_candidates.append((sniper_winner, raw_score, provider))
                        scored_candidates.sort(key=lambda x: (x[1], x[0].identifiers.get('free_upload_slots', 0)), reverse=True)
                        scored_candidates = scored_candidates[:3]
                    if raw_score >= perfect_match_threshold:
                        break  # Exit provider loop — perfect match secured
                    continue

                # ── Slow-path: deduplicate + full priority-tier scoring ────────────────
                # Deduplicate candidates for this provider
                provider_candidates = self._deduplicate_candidates(provider_candidates)
                logger.info(f"  Total candidates from {provider.name}: {len(provider_candidates)}")

                if not provider_candidates:
                    logger.info(f"  No candidates found on {provider.name}, trying next provider...")
                    continue

                # Run matching engine on this provider's candidates across priority tiers
                priority_tiers = self._get_priority_tiers(quality_profile)
                found_in_tier = False

                for priority_num, priority_formats in priority_tiers:
                    # Filter by priority formats
                    tier_candidates = self._filter_by_formats(provider_candidates, priority_formats)
                    logger.debug(f"    Priority {priority_num}: {len(tier_candidates)} candidates match formats")
                    
                    if not tier_candidates:
                        continue

                    # Score candidates via WeightedMatchingEngine on pure raw match merit
                    for candidate in tier_candidates:
                        match_result = matcher.calculate_match(target_track, candidate, context="download")
                        raw_score = match_result.confidence_score

                        if raw_score >= 70.0:
                            scored_candidates.append((candidate, raw_score, provider))
                            found_in_tier = True

                    # Keep only Top-3 scoring candidates globally to bound memory utilization
                    if scored_candidates:
                        scored_candidates.sort(key=lambda x: (x[1], x[0].identifiers.get('free_upload_slots', 0)), reverse=True)
                        scored_candidates = scored_candidates[:3]

                    if found_in_tier:
                        best_tier_score = scored_candidates[0][1]
                        logger.info(
                            f"    Got matching candidate(s) in priority {priority_num} "
                            f"(best score: {best_tier_score:.1f})"
                        )
                        break  # Found matches in highest available quality tier

                # Release raw provider candidate payloads immediately
                provider_candidates.clear()

                if scored_candidates:
                    best_provider_score = scored_candidates[0][1]
                    logger.info(f"  Current best match: score={best_provider_score:.1f}")

                    # Check if this is a perfect match (>= 90)
                    if best_provider_score >= perfect_match_threshold:
                        logger.info(
                            f"  ✓ PERFECT MATCH from {provider.name} "
                            f"(score {best_provider_score:.1f} >= {perfect_match_threshold})"
                        )
                        break  # Exit provider loop - perfect match secured
                else:
                    logger.info(f"  No acceptable match from {provider.name}")
                    continue

            # ============================================================================
            # DOWNLOAD CANDIDATE (WITH PEER ENQUEUE FALLBACK RESILIENCE)
            # ============================================================================
            # Deduplicate scored_candidates by (provider.name, filename) and retain Top-3
            unique_candidates: List[Tuple[EchosyncTrack, float, PluginBase]] = []
            seen_cand_keys = set()
            for cand, score, prov in sorted(scored_candidates, key=lambda x: x[1], reverse=True):
                fname = cand.identifiers.get('provider_item_id') or cand.identifiers.get('plugin_item_id')
                ckey = (prov.name, fname)
                if ckey not in seen_cand_keys:
                    seen_cand_keys.add(ckey)
                    unique_candidates.append((cand, score, prov))

            unique_candidates = unique_candidates[:3]

            if not unique_candidates:
                logger.warning(f"No suitable candidate matched across all {len(providers)} providers (min score: 70%)")
                self._update_status(download_id, "failed")
                return

            logger.info(
                f"**PROCEEDING WITH DOWNLOAD EVALUATION** "
                f"({len(unique_candidates)} qualifying Top candidate(s) >= 70%)"
            )

            download_started = False
            for cand_idx, (candidate, score, download_provider) in enumerate(unique_candidates):
                username = candidate.identifiers.get('username') or "unknown"
                filename = candidate.identifiers.get('provider_item_id') or candidate.identifiers.get('plugin_item_id')
                size = candidate.identifiers.get('size') or 0
                compound_id = f"{username}|{filename}"

                if (filename and filename in blacklisted_candidates) or (compound_id in blacklisted_candidates):
                    logger.info(f"Skipping blacklisted candidate {cand_idx + 1} from user '{username}': {filename}")
                    continue

                logger.info(
                    f"\nAttempting download (candidate {cand_idx + 1}/{len(unique_candidates)}):\n"
                    f"  Track: {target_track.artist_name} - {target_track.title}\n"
                    f"  Provider: {download_provider.name} | User: {username}\n"
                    f"  Match Score: {score:.1f}"
                )

                if not filename:
                    logger.warning(
                        f"Candidate {cand_idx + 1} from user '{username}' has no filename in candidate identifiers. "
                        f"Falling back to next best candidate."
                    )
                    continue

                provider_id = None
                try:
                    from core.hook_manager import hook_manager
                    plugin_decision = hook_manager.apply_filters(
                        'BEFORE_DOWNLOAD_START',
                        None,
                        target_track=target_track.to_dict(),
                        candidate=candidate.to_dict(),
                        provider=download_provider.name
                    )
                    if plugin_decision == "ABORT":
                        logger.warning(
                            f"Plugin aborted download for: {candidate.title} on {download_provider.name}. "
                            f"Falling back to next best candidate."
                        )
                        continue

                    if hasattr(download_provider, '_async_download'):
                        provider_id = await download_provider._async_download(username, filename, size)
                    else:
                        loop = asyncio.get_running_loop()
                        provider_id = await loop.run_in_executor(
                            None, download_provider.download, username, filename, size
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to enqueue candidate from user '{username}': {e}. "
                        f"Falling back to next best candidate."
                    )
                    continue

                if provider_id:
                    logger.info(f"DownloadQueue started: {provider_id}")
                    self._update_status(download_id, "downloading", provider_id)
                    download_started = True
                    break
                else:
                    logger.warning(
                        f"Failed to enqueue candidate from user '{username}'. "
                        f"Falling back to next best candidate."
                    )

            if not download_started:
                logger.error(f"All candidate download attempts failed for download {download_id}")
                self._update_status(download_id, "failed")

        except Exception as e:
            logger.error(f"Error executing waterfall search and download {download_id}: {e}", exc_info=True)
            self._update_status(download_id, "failed")

    async def _check_active_downloads(self):
        """Poll providers for status of active downloads using waterfall strategy"""
        providers = self._get_active_download_providers()
        if not providers:
            return

        active_downloads = []
        with self.work_db.session_scope() as session:
            # Find items marked 'downloading'
            items = session.query(DownloadQueue).filter(DownloadQueue.status.ilike("downloading")).all()
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
                    progress_pct = status.get('progress', 0)

                    try:
                        from core.hook_manager import hook_manager
                        # Use a persistent dict on the class to track last announced progress
                        if not hasattr(self, '_last_progress_event'):
                            self._last_progress_event = {}

                        last_pct = self._last_progress_event.get(db_id, -100)
                        if abs(progress_pct - last_pct) >= 5 or progress_pct >= 100:
                            hook_manager.apply_filters('ON_DOWNLOAD_PROGRESS', None, download_id=db_id, provider_id=provider_id, progress=progress_pct, state=remote_state)
                            self._last_progress_event[db_id] = progress_pct
                    except Exception as e:
                        logger.error(f"Error in ON_DOWNLOAD_PROGRESS hook: {e}")

                    new_status = "downloading"
                    if remote_state == "complete":
                        new_status = "completed"
                    elif remote_state == "failed":
                        new_status = "failed"
                    elif remote_state == "queued":
                        new_status = "downloading"

                    # Extract speed and progress (0-100)
                    speed = status.get('speed', 0.0) # bytes/s
                    progress = status.get('progress', 0.0) # 0.0 to 100.0

                    if new_status == "completed":
                        try:
                            from core.hook_manager import hook_manager
                            hook_manager.apply_filters('ON_DOWNLOAD_COMPLETED', None, download_id=db_id, provider_id=provider_id)
                        except Exception as e:
                            logger.error(f"Error in ON_DOWNLOAD_COMPLETED hook: {e}")

                        logger.info(f"Download {db_id} completed via {found_provider}. Auto-pruning record from database.")
                        self._remove_from_queue(db_id)
                    elif new_status == "failed":
                        logger.warning(
                            f"Download {db_id} transfer errored/rejected on {found_provider or 'provider'} "
                            f"(ID: {provider_id}). Cancelling remote transfer and falling back to next candidate."
                        )
                        # Cancel remote transfer
                        active_prov = next((p for p in providers if p.name == found_provider), providers[0])
                        if hasattr(active_prov, '_async_cancel_download'):
                            try:
                                await active_prov._async_cancel_download(provider_id)
                            except Exception as ce:
                                logger.debug(f"Failed to cancel remote transfer {provider_id}: {ce}")

                        with self.work_db.session_scope() as session:
                            item = session.query(DownloadQueue).filter(DownloadQueue.id == db_id).first()
                            if item:
                                track_dict = dict(item.echo_sync_track or {})
                                blacklist = list(track_dict.get('blacklisted_candidates') or [])
                                if provider_id and provider_id not in blacklist:
                                    blacklist.append(provider_id)
                                    if '|' in provider_id:
                                        _, fname = provider_id.split('|', 1)
                                        if fname not in blacklist:
                                            blacklist.append(fname)
                                track_dict['blacklisted_candidates'] = blacklist
                                item.echo_sync_track = track_dict
                                item.status = "searching"
                                item.provider_id = None
                                item.updated_at = utc_now()
                                session.commit()

                        asyncio.create_task(self._execute_waterfall_search_and_download(db_id, providers))
                    else:
                        self._update_status(db_id, new_status, provider_id, speed, progress)
                        if new_status != "downloading":
                            logger.info(f"DownloadQueue {db_id} (Provider {found_provider}, ID {provider_id}) finished with status: {new_status}")
                else:
                    logger.warning(
                        f"DownloadQueue {db_id} not found in active transfers (disappeared) - "
                        f"treating as failed, cleaning remote state, and falling back to next candidate."
                    )
                    for prov in providers:
                        if hasattr(prov, '_async_cancel_download'):
                            try:
                                await prov._async_cancel_download(provider_id)
                            except Exception:
                                pass

                    with self.work_db.session_scope() as session:
                        item = session.query(DownloadQueue).filter(DownloadQueue.id == db_id).first()
                        if item:
                            track_dict = dict(item.echo_sync_track or {})
                            blacklist = list(track_dict.get('blacklisted_candidates') or [])
                            if provider_id and provider_id not in blacklist:
                                blacklist.append(provider_id)
                                if '|' in provider_id:
                                    _, fname = provider_id.split('|', 1)
                                    if fname not in blacklist:
                                        blacklist.append(fname)
                            track_dict['blacklisted_candidates'] = blacklist
                            item.echo_sync_track = track_dict
                            item.status = "searching"
                            item.provider_id = None
                            item.updated_at = utc_now()
                            session.commit()

                    asyncio.create_task(self._execute_waterfall_search_and_download(db_id, providers))

            except Exception as e:
                logger.error(f"Error checking status for {db_id}: {e}")

    def _generate_search_strategies(self, track: EchosyncTrack, base_duration_tolerance_ms: int) -> List[SearchStrategyIntent]:
        """Generate ordered search fallback strategies with per-strategy duration tolerance.

        Progressive Strategy Ladder:
        1. ISRC Lookup (Requires Capability.FETCH_BY_ISRC)
        2. Strict Artist + Title (Universal Baseline)
        3. Broad Artist + Filter Title (Requires Capability.CLIENT_PREFILTER)
        4. Title + Filter Artist (Requires Capability.CLIENT_PREFILTER)
        5. Collaborator + Filter Title (Requires Capability.CLIENT_PREFILTER)
        6. Strict Album + Title (Universal Baseline)
        7. Title + Strict Duration Window (Universal Baseline)
        """
        strategies: List[SearchStrategyIntent] = []

        # Build a core title for provider search by stripping bracketed/parenthetical
        # qualifiers, then applying standard normalization.
        search_title = self._build_core_search_title(track.title)
        if search_title != track.title:
            logger.info(f"Normalized title for search: '{track.title}' -> '{search_title}'")

        primary_artist, collaborators = split_artist_collaborators(track.artist_name)
        wire_primary_artist = sanitize_query_for_wire(primary_artist or track.artist_name or "")
        wire_search_title = sanitize_query_for_wire(search_title)
        target_dur = track.duration if track.duration else None

        # Strategy 1 (ISRC / Strict GUID if available - requires Capability.FETCH_BY_ISRC)
        if getattr(track, "isrc", None):
            strategies.append(SearchStrategyIntent(
                id="isrc",
                name="isrc",
                strategy_type="isrc",
                wire_query=str(track.isrc).strip().upper(),
                required_capability=Capability.FETCH_BY_ISRC,
                target_duration_ms=target_dur,
                duration_tolerance_ms=int(base_duration_tolerance_ms),
            ))

        # Strategy 2: Artist + Title (Strict Metadata - Universal Baseline)
        if wire_primary_artist and wire_search_title:
            strategies.append(SearchStrategyIntent(
                id="artist+title",
                name="artist+title",
                strategy_type="strict_metadata",
                wire_query=f"{wire_primary_artist} {wire_search_title}".strip(),
                required_capability=None,
                target_duration_ms=target_dur,
                duration_tolerance_ms=int(base_duration_tolerance_ms),
            ))

        # Strategy 3: Artist broad + client-side title filter (Requires Capability.CLIENT_PREFILTER)
        if wire_primary_artist and search_title:
            strategies.append(SearchStrategyIntent(
                id="artist+broad+filter",
                name="artist+broad+filter",
                strategy_type="fuzzy_artist_title",
                wire_query=wire_primary_artist,
                filter_expression=search_title,
                includes=[search_title],
                required_capability=Capability.CLIENT_PREFILTER,
                target_duration_ms=target_dur,
                duration_tolerance_ms=int(base_duration_tolerance_ms),
            ))

        # Strategy 4: Title + client-side artist filter (Requires Capability.CLIENT_PREFILTER)
        if wire_search_title and wire_primary_artist:
            strategies.append(SearchStrategyIntent(
                id="title+filter_artist",
                name="title+filter_artist",
                strategy_type="fuzzy_artist_title",
                wire_query=wire_search_title,
                filter_expression=wire_primary_artist,
                includes=[wire_primary_artist],
                required_capability=Capability.CLIENT_PREFILTER,
                target_duration_ms=target_dur,
                duration_tolerance_ms=int(base_duration_tolerance_ms),
            ))

        # Strategy 5: Collaborator + client-side title filter (Requires Capability.CLIENT_PREFILTER)
        for idx, collab in enumerate(collaborators, 1):
            wire_collab = sanitize_query_for_wire(collab)
            if wire_collab and search_title:
                strategies.append(SearchStrategyIntent(
                    id=f"collab+filter_title_{idx}",
                    name="collab+filter_title",
                    strategy_type="fuzzy_artist_title",
                    wire_query=wire_collab,
                    filter_expression=search_title,
                    includes=[search_title],
                    required_capability=Capability.CLIENT_PREFILTER,
                    target_duration_ms=target_dur,
                    duration_tolerance_ms=int(base_duration_tolerance_ms),
                ))

        # Strategy 6: Album + Title (Strict Metadata - Universal Baseline)
        if track.album_title and wire_search_title:
            from core.matching_engine.text_utils import normalize_album
            normalized_album = normalize_album(track.album_title)
            wire_album = sanitize_query_for_wire(normalized_album)
            if wire_album and wire_album.lower() != wire_search_title.lower():
                strategies.append(SearchStrategyIntent(
                    id="album+title",
                    name="album+title",
                    strategy_type="strict_metadata",
                    wire_query=f"{wire_album} {wire_search_title}".strip(),
                    required_capability=None,
                    target_duration_ms=target_dur,
                    duration_tolerance_ms=int(base_duration_tolerance_ms),
                ))

        # Strategy 7: Title only + stricter duration window (Loose Title + Duration - Universal Baseline)
        if wire_search_title:
            stricter_tolerance = max(1000, int(base_duration_tolerance_ms * 0.5))
            strategies.append(SearchStrategyIntent(
                id="title+strict-duration",
                name="title+strict-duration",
                strategy_type="loose_title_duration",
                wire_query=wire_search_title,
                required_capability=None,
                target_duration_ms=target_dur,
                duration_tolerance_ms=stricter_tolerance,
            ))

        # De-duplicate by (normalized query, required_capability, strategy_name) while preserving order
        unique: List[SearchStrategyIntent] = []
        seen_keys = set()
        for strategy in strategies:
            query_str = getattr(strategy, 'wire_query', None) or (strategy.get("query") if isinstance(strategy, dict) else "")
            req_cap = getattr(strategy, 'required_capability', None) if not isinstance(strategy, dict) else strategy.get('required_capability')
            strat_name = getattr(strategy, 'name', None) if not isinstance(strategy, dict) else strategy.get('name')
            key = ((query_str or "").strip().lower(), req_cap, strat_name)
            if key and key not in seen_keys:
                unique.append(strategy)
                seen_keys.add(key)

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

    def _deduplicate_candidates(self, candidates: List[EchosyncTrack]) -> List[EchosyncTrack]:
        """Deduplicate candidates collected from multiple fallback strategies.

        Only removes true duplicates (same peer, same file path, and same core
        technical metadata). This preserves meaningful variants of the same track
        that may differ by bitrate/size/sample-rate/bit-depth.
        """
        unique: List[EchosyncTrack] = []
        seen = set()

        for candidate in candidates:
            identifiers = getattr(candidate, 'identifiers', None) or {}
            username = identifiers.get('username') if isinstance(identifiers, dict) else None
            plugin_item_id = identifiers.get('plugin_item_id') if isinstance(identifiers, dict) else None

            # Include quality-relevant fields from media[0] so we only collapse exact duplicate
            # observations of the same file result across fallback strategies.
            size = identifiers.get('size') if isinstance(identifiers, dict) else None
            bitrate = identifiers.get('bitrate') if isinstance(identifiers, dict) else None
            duration = getattr(candidate, 'duration', None)

            first_media = candidate.media[0] if getattr(candidate, 'media', None) else None
            file_format = first_media.file_format if first_media else None
            sample_rate = first_media.sample_rate if first_media else None
            bit_depth = first_media.bit_depth if first_media else None
            if size is None and first_media and first_media.file_size_bytes:
                size = first_media.file_size_bytes
            if bitrate is None and first_media and first_media.bitrate:
                bitrate = first_media.bitrate

            dedupe_key = (
                username,
                plugin_item_id,
                size,
                bitrate,
                duration,
                file_format,
                sample_rate,
                bit_depth,
            )

            if plugin_item_id and username and dedupe_key in seen:
                continue

            if plugin_item_id and username:
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
            custom_weights['tie_breaker'] = quality_profile.get('tie_breaker', 'MAX_QUALITY')
            has_custom_settings = True
        
        if has_custom_settings:
            # Create custom profile with updated weights
            from core.matching_engine.scoring_profile import ScoringProfile, ScoringWeights
            custom_profile = ScoringProfile()
            custom_profile.weights = ScoringWeights(**custom_weights)
            logger.info(f"Using custom matching profile: duration_tolerance={custom_weights.get('duration_tolerance_ms')}ms, tie_breaker={custom_weights.get('tie_breaker')}")
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
    
    def _filter_by_formats(self, candidates: List[EchosyncTrack], formats: List[str]) -> List[EchosyncTrack]:
        """Filter candidates by format and apply quality profile constraints."""
        quality_profile = self._get_quality_profile()
        if not quality_profile:
            # Fallback: just filter by format
            filtered = []
            for track in candidates:
                if not getattr(track, 'media', None):
                    continue
                media = track.media[0]
                if media.file_format and media.file_format.lower() in formats:
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
            if not getattr(track, 'media', None):
                continue
            media = track.media[0]
            if not media.file_format:
                continue
            
            format_type = media.file_format.lower()
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
            
            if media.file_size_bytes:
                size_mb = media.file_size_bytes / (1024 * 1024)
                if min_size_mb > 0 and size_mb < min_size_mb:
                    continue
                if max_size_mb > 0 and size_mb > max_size_mb:
                    continue
            
            # For lossless formats (FLAC, WAV, DSD), check bit depth and sample rate
            if format_type in ['flac', 'wav', 'dsd']:
                bit_depths = fmt_config.get('bit_depths', [])
                sample_rates = fmt_config.get('sample_rates', [])
                
                # Only enforce bit depth if profile has it configured and media has it
                if bit_depths and media.bit_depth is not None:
                    allowed_bd = [str(b).strip() for b in bit_depths]
                    if str(media.bit_depth) not in allowed_bd:
                        continue
                
                # Only enforce sample rate if profile has it configured and media has it
                if sample_rates and media.sample_rate is not None:
                    sr_val = media.sample_rate
                    sr_khz = f"{sr_val / 1000:.1f}".rstrip('0').rstrip('.')
                    sr_hz = str(int(sr_val))
                    allowed_sr = [str(s).strip().lower() for s in sample_rates]
                    if sr_khz not in allowed_sr and sr_hz not in allowed_sr and str(sr_val) not in allowed_sr:
                        continue
            
            # For lossy formats (MP3, AAC, OGG, etc.), check bitrate
            elif format_type in ['mp3', 'aac', 'ogg', 'm4a', 'opus', 'vorbis']:
                min_bitrate_kbps = fmt_config.get('min_bitrate', 0)
                max_bitrate_kbps = fmt_config.get('max_bitrate', 999999)
                
                # Extract bitrate from media or identifiers
                bitrate_kbps = media.bitrate or 0
                if not bitrate_kbps and track.identifiers and 'bitrate' in track.identifiers:
                    bitrate_kbps = track.identifiers.get('bitrate', 0) or 0
                
                # Convert to kbps if in bps
                if bitrate_kbps > 10000:
                    bitrate_kbps = bitrate_kbps // 1000
                
                if min_bitrate_kbps > 0 and bitrate_kbps > 0 and bitrate_kbps < min_bitrate_kbps:
                    logger.debug(f"Rejecting {format_type} ({bitrate_kbps}kbps) - below minimum {min_bitrate_kbps}kbps")
                    continue
                
                if max_bitrate_kbps > 0 and bitrate_kbps > 0 and bitrate_kbps > max_bitrate_kbps:
                    logger.debug(f"Rejecting {format_type} ({bitrate_kbps}kbps) - above maximum {max_bitrate_kbps}kbps")
                    continue
            
            filtered.append(track)
        
        # Sort by size (prefer larger files for better quality)
        filtered.sort(
            key=lambda t: (t.media[0].file_size_bytes if (getattr(t, 'media', None) and t.media and t.media[0].file_size_bytes) else 0),
            reverse=True
        )
        
        return filtered

    def _remove_from_queue(self, download_id: int):
        """CLEANUP TASK 1: Remove a download from the queue after successful completion."""
        try:
            with self.work_db.session_scope() as session:
                download = session.query(DownloadQueue).get(download_id)
                if download:
                    session.delete(download)
                    logger.info(f"Removed completed download {download_id} from queue")
        except Exception as e:
            logger.warning(f"Failed to remove download {download_id} from queue: {e}")
    
    def _update_status(self, download_id: int, status: str, provider_id: Optional[str] = None, speed: float = 0.0, progress: float = 0.0):
        """Helper to update DB status, speed, and progress"""
        with self.work_db.session_scope() as session:
            download = session.query(DownloadQueue).get(download_id)
            if download:
                download.status = (status or "").lower()
                
                # Store progress/speed in the JSON blob instead of invented columns
                track_json = dict(download.echo_sync_track or {})
                track_json["current_speed"] = speed
                track_json["progress_percent"] = progress
                download.echo_sync_track = track_json
                
                download.updated_at = utc_now()
                if provider_id:
                    download.provider_id = provider_id

    def _find_existing_download(self, track_json: Dict[str, Any]) -> Optional[Tuple[int, str]]:
        """Return an existing active download (id, status) matching the normalized track signature."""
        signature = self._normalize_track_signature(track_json)
        if not any(signature):
            return None

        active_states = {"queued", "searching", "downloading"}
        with self.work_db.session_scope() as session:
            offset = 0
            batch_size = 25
            while True:
                items = (
                    session.query(DownloadQueue)
                    .filter(DownloadQueue.status.in_(active_states))
                    .order_by(DownloadQueue.id.asc())
                    .offset(offset)
                    .limit(batch_size)
                    .all()
                )
                if not items:
                    break
                for item in items:
                    other_sig = self._normalize_track_signature(item.echo_sync_track or {})
                    if signature == other_sig:
                        return item.id, item.status
                offset += batch_size
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
            download = session.query(DownloadQueue).get(download_id)
            if download:
                return {
                    "id": download.id,
                    "status": download.status,
                    "track": download.echo_sync_track,
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
                offset = 0
                batch_size = 25
                removed_count = 0
                while True:
                    queued_items = (
                        session.query(DownloadQueue)
                        .filter(DownloadQueue.status.in_(['queued', 'searching', 'failed_no_match', 'failed']))
                        .order_by(DownloadQueue.id.asc())
                        .offset(offset)
                        .limit(batch_size)
                        .all()
                    )
                    if not queued_items:
                        break

                    for item in queued_items:
                        try:
                            track_data = item.echo_sync_track
                            if not track_data:
                                continue

                            artist = track_data.get('artist_name') or track_data.get('artist')
                            title = track_data.get('title')
                            album = track_data.get('album_title') or track_data.get('album')
                            duration = track_data.get('duration') or track_data.get('duration_ms')

                            if not artist or not title:
                                continue

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

                    offset += batch_size

                if removed_count > 0:
                    logger.info(f"Startup purge removed {removed_count} redundant items from download queue")

        except Exception as e:
            logger.error(f"Error purging existing tracks from queue: {e}")

    def process_downloads_now(self):
        """Run one processing cycle. Safe to call from any sync or async context.

        When the background worker loop is actively running (self._loop_task),
        scheduled job triggers delegate to it to prevent concurrent queue consumption races.
        """
        # If the background processing loop is already running, delegate directly to the existing worker loop
        if self._loop_task and not self._loop_task.done() and self._loop and self._loop.is_running():
            logger.info("DownloadManager: background processing loop is active; delegating queue consumption to existing worker loop.")
            return

        async def _cycle():
            requeued = self._requeue_retryable_failed_items(limit=50)
            if requeued > 0:
                logger.info(f"Manual run: re-queued {requeued} retryable failed items")
            await self._recover_stuck_items()
            self._purge_existing_tracks_from_queue()
            await self._process_queued_items()
            await self._check_active_downloads()
            logger.info("DownloadQueue processing cycle complete")

        # 1. Background daemon loop is running on a dedicated thread:
        if self._loop and self._loop.is_running():
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop is self._loop:
                return self._loop.create_task(_cycle())
            else:
                asyncio.run_coroutine_threadsafe(_cycle(), self._loop)
                logger.info("DownloadQueue processing triggered on background event loop")
                return

        # 2. Called from within an active running event loop (e.g. async FastAPI route):
        try:
            current_loop = asyncio.get_running_loop()
            if current_loop and current_loop.is_running():
                logger.info("DownloadQueue processing scheduled on current running event loop")
                return current_loop.create_task(_cycle())
        except RuntimeError:
            pass

        # 3. Non-async / sync thread context with no active loop:
        try:
            asyncio.run(_cycle())
        except Exception as e:
            logger.error(f"DownloadQueue processing cycle failed: {e}", exc_info=True)

    def process_single_download(self, download_id: int):
        """Run acquisition strictly for a single download ID without global queue sweeps."""
        async def _run_single():
            providers = self._get_active_download_providers()
            if not providers:
                logger.warning("No active download providers available for single-item retry.")
                return
            await self._execute_waterfall_search_and_download(download_id, providers)

        # 1. Background daemon loop active:
        if self._loop and self._loop.is_running():
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop is self._loop:
                return self._loop.create_task(_run_single())
            else:
                return asyncio.run_coroutine_threadsafe(_run_single(), self._loop)

        # 2. Inside active FastAPI event loop:
        try:
            current_loop = asyncio.get_running_loop()
            if current_loop and current_loop.is_running():
                return current_loop.create_task(_run_single())
        except RuntimeError:
            pass

        # 3. Synchronous context:
        try:
            asyncio.run(_run_single())
        except Exception as e:
            logger.error(f"Single download execution failed: {e}", exc_info=True)

    def _requeue_retryable_failed_items(self, limit: int = 50) -> int:
        """Move retryable failed items back to queued so manual runs can re-attempt them.
        
        Prioritizes NEWEST tracks first (DESC by created_at) so most recent failures are retried first.
        Caps automatic re-queuing at retry_count < 5. Tracks with >= 5 retries require manual user intervention.
        Enforces exponential backoff: delay >= (2 ** retry_count) * 60s.
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
        now = utc_now()
        with self.work_db.session_scope() as session:
            items = (
                session.query(DownloadQueue)
                .filter(
                    DownloadQueue.status.in_(retryable_statuses),
                    (DownloadQueue.retry_count < 5) | (DownloadQueue.retry_count.is_(None))
                )
                .order_by(DownloadQueue.created_at.desc())  # Newest first
                .limit(limit)
                .all()
            )

            for item in items:
                retry_c = item.retry_count or 0
                required_delay = (2 ** retry_c) * 60
                last_time = item.updated_at or item.created_at or now
                elapsed = (now - last_time).total_seconds()
                if elapsed < required_delay:
                    continue

                item.status = "queued"
                item.provider_id = None
                item.retry_count = retry_c + 1
                item.updated_at = now
                requeued += 1

        if requeued > 0:
            logger.info(f"Re-queued {requeued} failed items for retry (capped at retry_count < 5 with backoff)")
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
    
    def process_downloads(force_run: bool = False, **kwargs):
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
        tags=["echosync", "downloads"],
        max_retries=3
    )

    logger.info(
        f"DownloadQueue manager job registered (name: download_manager, interval: {interval_seconds}s, first run after startup: {interval_seconds}s)"
    )
