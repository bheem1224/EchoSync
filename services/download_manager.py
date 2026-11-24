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
import inspect
import logging
import re
import threading
from dataclasses import dataclass, is_dataclass, replace
from typing import Any

from core.database.models.working import DownloadIntent, DownloadStatus
from core.database.repositories.download_repo import DownloadRepository
from core.db.echo_sync_track import EchosyncTrack
from core.enums import Capability, TaskCategory, TaskPriority
from core.hook_manager import hook_manager
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_DOWNLOAD_SEARCH
from core.matching_engine.text_utils import (
    extract_edition,
    extract_version_info,
    normalize_artist,
    normalize_title,
    sanitize_query_for_wire,
    split_artist_collaborators,
)
from core.matching_engine.track_parser import TrackParser
from core.nexus_framework.plugin_loader import PluginRegistry
from core.nexus_framework.plugin_SDK import PluginBase
from core.settings import config_manager
from core.task_manager.task_queue import db_write_lease, job_queue
from database.music_database import Album, Artist, Track, get_database
from database.working_database import DownloadQueue, get_working_database
from time_utils import utc_now

logger = logging.getLogger("download_manager")


@dataclass
class SearchStrategyIntent:
    id: str
    name: str
    strategy_type: str
    wire_query: str
    filter_expression: str | None = None
    includes: list[str] | None = None
    excludes: list[str] | None = None
    required_capability: Capability | None = None
    target_duration_ms: int | None = None
    duration_tolerance_ms: int = 3000

    def to_dict(self) -> dict[str, Any]:
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


def _provider_supports_capability(provider: Any, capability: Capability | None) -> bool:
    """Check if provider advertises the required capability."""
    if capability is None:
        return True
    caps = getattr(provider, "capabilities", None)
    if hasattr(caps, "to_enum_list") and callable(caps.to_enum_list):
        enum_list = caps.to_enum_list()
        if isinstance(enum_list, list):
            return capability in enum_list
    if isinstance(caps, list):
        return capability in caps
    if hasattr(provider, "supports_capability") and callable(provider.supports_capability):
        res = provider.supports_capability(capability)
        if isinstance(res, bool):
            return res
    if capability == Capability.CLIENT_PREFILTER:
        sup = getattr(provider, "supports_pre_filtering", None)
        if sup is not None and isinstance(sup, bool):
            return sup
        caps_sup = getattr(getattr(provider, "capabilities", None), "supports_pre_filtering", None)
        if caps_sup is not None and isinstance(caps_sup, bool):
            return caps_sup
    if capability == Capability.FETCH_BY_ISRC:
        sup = getattr(provider, "supports_isrc", None)
        if sup is not None and isinstance(sup, bool):
            return sup
        caps_sup = getattr(getattr(provider, "capabilities", None), "supports_isrc_lookup", None)
        if caps_sup is not None and isinstance(caps_sup, bool):
            return caps_sup
    return False


class DownloadManager:
    """
    Central orchestrator for managing the download queue and provider interactions.
    """

    _instance = None
    _instance_lock = threading.Lock()

    @property
    def repo(self) -> DownloadRepository:
        if (
            not hasattr(self, "_repo_instance")
            or self._repo_instance is None
            or getattr(self._repo_instance, "work_db", None) != self.work_db
        ):
            self._repo_instance = DownloadRepository(work_db=self.work_db)
        return self._repo_instance

    @repo.setter
    def repo(self, value: Any) -> None:
        self._repo_instance = value

    def __init__(self):
        self.db = get_database()
        self.work_db = get_working_database()
        self._repo_instance = None
        self.matcher = self._instantiate_matching_engine(PROFILE_DOWNLOAD_SEARCH)
        self._shutdown = False
        self._stop_requested = False
        self._loop_task = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._provider: PluginBase | None = None
        self._active_providers: dict[str, PluginBase] = {}
        self._quality_profile_cache = None
        # Strictly in-memory flag (no DB column) tracking downloads where a Remaster
        # fallback was intentionally chosen because 0 Originals existed across all strategies.
        self._remaster_fallback_ids: set[int] = set()
        # In-memory progress clock for 5m queued-stall / 2m mid-transfer freeze timeouts
        self._transfer_progress_tracker: dict[int, dict[str, Any]] = {}
        # In-memory set of download IDs currently executing a live search coroutine
        self._active_search_ids: set[int] = set()

        from core.event_bus import event_bus

        event_bus.subscribe("DOWNLOAD_INTENT", self._on_download_intent)
        event_bus.subscribe("TRACK_IMPORTED", self._on_track_imported)

    @staticmethod
    def _instantiate_matching_engine(profile: Any) -> WeightedMatchingEngine:
        """Resolve matching engine class via ServiceRegistry so optional plugins override cleanly."""
        try:
            from core.nexus_framework.plugin_loader import ServiceRegistry

            engine_cls = ServiceRegistry.get("matching_engine")
            if engine_cls is not None and callable(engine_cls):
                return engine_cls(profile)
        except Exception:
            pass
        return WeightedMatchingEngine(profile)

    def is_remaster_fallback_allowed(self, download_id: int) -> bool:
        """Return True if download_id intentionally selected a Remaster fallback in memory."""
        return download_id in getattr(self, "_remaster_fallback_ids", set())

    def _cancel_transfer_sync(self, providers: list[PluginBase], cancel_target: str) -> None:
        """Best-effort synchronous cancellation of an upstream provider transfer."""
        for p in providers:
            try:
                if hasattr(p, "cancel_download"):
                    p.cancel_download(cancel_target)
                elif hasattr(p, "_async_cancel_download"):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(p._async_cancel_download(cancel_target))
                    except RuntimeError:
                        asyncio.run(p._async_cancel_download(cancel_target))
            except Exception as ce:
                logger.debug(f"Failed to cancel remote transfer {cancel_target}: {ce}")

    async def _cancel_transfer_async(self, providers: list[PluginBase], cancel_target: str) -> None:
        """Best-effort asynchronous cancellation of an upstream provider transfer."""
        for prov in providers:
            try:
                if hasattr(prov, "_async_cancel_download"):
                    await prov._async_cancel_download(cancel_target)
                elif hasattr(prov, "cancel_download"):
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, prov.cancel_download, cancel_target)
            except Exception as ce:
                logger.debug(f"Failed to cancel remote transfer {cancel_target}: {ce}")

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

            active_states = {
                DownloadStatus.QUEUED.value,
                DownloadStatus.SEARCHING.value,
                DownloadStatus.DOWNLOADING.value,
                DownloadStatus.VERIFYING.value,
                DownloadStatus.RETRYING.value,
                DownloadStatus.FAILED.value,
            }
            cancelled_count = 0

            with self.work_db.session_scope() as session:
                last_id = 0
                batch_size = 25
                providers: list[PluginBase] | None = None
                while True:
                    items = (
                        session.query(DownloadQueue)
                        .filter(
                            DownloadQueue.status.in_(active_states),
                            DownloadQueue.id > last_id,
                        )
                        .order_by(DownloadQueue.id.asc())
                        .limit(batch_size)
                        .all()
                    )
                    if not items:
                        break
                    last_id = items[-1].id

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

                            cancel_target = item.active_candidate_id or item.provider_id
                            if item.status == DownloadStatus.DOWNLOADING.value and cancel_target:
                                if providers is None:
                                    providers = self._get_active_download_providers()
                                self._cancel_transfer_sync(providers, cancel_target)

                            session.delete(item)
                            cancelled_count += 1

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
        strategy_filters: dict[str, Any],
        quality_profile: dict[str, Any] | None,
        target_track: EchosyncTrack | None = None,
        strategy_name: str = "",
        perfect_match_threshold: int = 90,
        includes: list[str] | None = None,
        excludes: list[str] | None = None,
        blacklisted_candidates: set[str] | None = None,
        fallback_quality_profile: dict[str, Any] | None = None,
        early_stop_evaluator: Any | None = None,
    ) -> tuple[list[EchosyncTrack], bool]:
        """Search a single provider for one strategy query, expanding via hooks.

        Returns ``(results, sniper_hit)`` where ``sniper_hit=True`` means a
        qualifying Preferred Profile pool (3 candidates or perfect match + backups)
        was secured and remaining query variants were short-circuited.
        """
        query_or_queries = hook_manager.apply_filters(
            "pre_provider_search",
            query,
            strategy_name=strategy_name,
            artist_name=getattr(target_track, "artist_name", "") or "",
            title=getattr(target_track, "title", "") or "",
        )
        queries = query_or_queries if isinstance(query_or_queries, list) else [query_or_queries]

        # dict.fromkeys: order-preserving deduplication
        ordered_queries = list(dict.fromkeys(q for q in queries if isinstance(q, str) and q.strip()))

        accumulated: list[EchosyncTrack] = []
        for q in ordered_queries:
            batch = await self._invoke_provider_search_single(
                provider,
                q,
                strategy_filters,
                quality_profile,
                includes=includes,
                excludes=excludes,
                fallback_quality_profile=fallback_quality_profile,
                early_stop_evaluator=early_stop_evaluator,
            )
            if not batch:
                continue

            accumulated.extend(batch)

            # Evaluation-driven short-circuit: score this batch strictly against the
            # Preferred Profile (excluding blacklisted candidates) and return the FULL
            # accumulated batch so candidate_stack keeps Top-3 backup peers.
            if target_track is not None:
                hit = self._evaluate_search_batch(
                    batch,
                    target_track,
                    quality_profile,
                    perfect_match_threshold,
                    blacklisted_candidates=blacklisted_candidates,
                )
                if hit is not None:
                    remaining = len(ordered_queries) - ordered_queries.index(q) - 1
                    if remaining > 0:
                        logger.info(
                            "\u26a1 Sniper hit on variant %r (score\u2265%d) \u2014 skipping %d remaining variant(s).",
                            q,
                            perfect_match_threshold,
                            remaining,
                        )
                    return accumulated, True

        return accumulated, False

    def _enrich_candidate_metadata(self, candidate: EchosyncTrack) -> EchosyncTrack:
        """Centralized Path & Metadata Enrichment for raw candidates.

        Extracts structured artist, title, album, version, and edition metadata
        from candidate media file path, raw_title, or identifiers using TrackParser
        and text utilities without discarding version/edition descriptors.
        """
        if not candidate:
            return candidate

        # Determine path or filename to parse
        file_path = None
        if (
            getattr(candidate, "media", None)
            and len(candidate.media) > 0
            and getattr(candidate.media[0], "file_path", None)
        ):
            file_path = candidate.media[0].file_path
        elif candidate.identifiers and candidate.identifiers.get("plugin_item_id"):
            file_path = candidate.identifiers.get("plugin_item_id")
        elif candidate.identifiers and candidate.identifiers.get("provider_item_id"):
            file_path = candidate.identifiers.get("provider_item_id")
        elif candidate.raw_title:
            file_path = candidate.raw_title

        updates: dict[str, Any] = {}
        if file_path:
            if not hasattr(self, "_track_parser") or self._track_parser is None:
                self._track_parser = TrackParser()
            parsed = self._track_parser.parse_filename(file_path)
            if parsed:
                parsed_artist = getattr(parsed, "artist_name", None) or getattr(parsed, "artist", None)
                parsed_title = getattr(parsed, "title", None) or getattr(parsed, "raw_title", None)
                parsed_album = getattr(parsed, "album_title", None) or getattr(parsed, "album", None)
                parsed_version = getattr(parsed, "version", None)
                parsed_edition = getattr(parsed, "edition", None)

                if parsed_artist and (not candidate.artist_name or candidate.artist_name == "Unknown Artist"):
                    updates["artist_name"] = parsed_artist
                if parsed_title:
                    updates["title"] = parsed_title
                    # Preserve original unstripped raw_title if present so version/edition cues aren't lost
                    if not candidate.raw_title:
                        updates["raw_title"] = parsed_title
                if parsed_album and not getattr(candidate, "album_title", None):
                    updates["album_title"] = parsed_album
                if parsed_version and not getattr(candidate, "version", None):
                    updates["version"] = parsed_version
                if parsed_edition and not getattr(candidate, "edition", None):
                    updates["edition"] = parsed_edition
                if getattr(parsed, "release_year", None) and not getattr(candidate, "release_year", None):
                    updates["release_year"] = parsed.release_year
                if getattr(parsed, "track_number", None) and not getattr(candidate, "track_number", None):
                    updates["track_number"] = parsed.track_number
                if getattr(parsed, "disc_number", None) and not getattr(candidate, "disc_number", None):
                    updates["disc_number"] = parsed.disc_number

        # Fallback version/edition extraction against the unstripped filename/path
        # (never against the already-stripped parsed_title).
        if not updates.get("version") and not updates.get("edition"):
            from pathlib import Path as _Path

            probe_target = ""
            if file_path:
                norm_fp = str(file_path).replace("\\", "/")
                fp_parts = [p for p in norm_fp.split("/") if p]
                stem = _Path(fp_parts[-1]).stem if fp_parts else norm_fp
                parent_dir = fp_parts[-2] if len(fp_parts) >= 2 else ""
                probe_target = stem
            else:
                parent_dir = ""
                probe_target = candidate.raw_title or candidate.title or ""

            _, version_str = extract_version_info(probe_target)
            if version_str:
                updates["version"] = version_str
                if not (updates.get("edition") or getattr(candidate, "edition", None)):
                    updates["edition"] = version_str

            _, edition_str = extract_edition(probe_target)
            if edition_str:
                updates["edition"] = edition_str
                if not (updates.get("version") or getattr(candidate, "version", None)):
                    updates["version"] = edition_str

            # Also check parent album folder for remaster/year qualifiers (e.g. "Album [2011 Remaster]")
            if not updates.get("edition") and not updates.get("version") and parent_dir:
                _, dir_ver = extract_version_info(parent_dir)
                if dir_ver and "remaster" in dir_ver.lower():
                    updates["version"] = dir_ver
                    updates["edition"] = dir_ver

        if updates:
            if is_dataclass(candidate) and not isinstance(candidate, type):
                candidate = replace(candidate, **updates)
            else:
                for k, v in updates.items():
                    setattr(candidate, k, v)

        return candidate

    def _is_candidate_blacklisted(self, candidate: EchosyncTrack, blacklisted_candidates: set[str] | None) -> bool:
        if not blacklisted_candidates:
            return False
        ids = getattr(candidate, "identifiers", None) or {}
        pid = ids.get("plugin_item_id") or ids.get("provider_item_id")
        username = ids.get("username")
        comp_id = f"{username}|{pid}" if username and pid else None
        return bool((pid and pid in blacklisted_candidates) or (comp_id and comp_id in blacklisted_candidates))

    def _evaluate_search_batch(
        self,
        batch: list[EchosyncTrack],
        target_track: EchosyncTrack,
        quality_profile: dict[str, Any] | None,
        threshold: float,
        blacklisted_candidates: set[str] | None = None,
    ) -> EchosyncTrack | None:
        """Run Preferred Profile tier filtering + matching on a raw result batch.

        Excludes blacklisted candidates and evaluates strictly with ``context="download"``
        (so Remaster substitutes never short-circuit when an Original was requested).
        """
        non_blacklisted = [c for c in batch if not self._is_candidate_blacklisted(c, blacklisted_candidates)]
        if not non_blacklisted:
            return None
        enriched_batch = [self._enrich_candidate_metadata(c) for c in non_blacklisted]
        priority_tiers = self._get_priority_tiers(quality_profile)
        matcher = self._get_matching_engine(quality_profile)
        if not priority_tiers:
            # No quality profile configured: score across all allowed defaults
            allowed = self._extract_allowed_formats(quality_profile)
            priority_tiers = [(0, allowed)]

        for priority_num, priority_formats in priority_tiers:
            try:
                tier_candidates = self._filter_by_formats(
                    enriched_batch, priority_formats, quality_profile, priority=priority_num
                )
            except TypeError:
                try:
                    tier_candidates = self._filter_by_formats(enriched_batch, priority_formats, quality_profile)
                except TypeError:
                    tier_candidates = self._filter_by_formats(enriched_batch, priority_formats)
            if not tier_candidates:
                continue
            for cand in tier_candidates:
                match_result = matcher.calculate_match(target_track, cand, context="download")
                if match_result.confidence_score >= threshold:
                    return cand
        return None

    async def _invoke_provider_search_single(
        self,
        provider: PluginBase,
        query: str,
        strategy_filters: dict[str, Any],
        quality_profile: dict[str, Any] | None,
        includes: list[str] | None = None,
        excludes: list[str] | None = None,
        fallback_quality_profile: dict[str, Any] | None = None,
        early_stop_evaluator: Any | None = None,
    ) -> list[EchosyncTrack]:
        """Invoke provider search while passing quality_profile, fallback profile, and early-stop hook when supported."""

        if hasattr(provider, "_async_search"):
            async_search = provider._async_search
            try:
                sig = inspect.signature(async_search)
                kwargs: dict[str, Any] = {}
                if "quality_profile" in sig.parameters:
                    kwargs["quality_profile"] = quality_profile
                if "includes" in sig.parameters:
                    kwargs["includes"] = includes
                if "excludes" in sig.parameters:
                    kwargs["excludes"] = excludes
                if "fallback_quality_profile" in sig.parameters:
                    kwargs["fallback_quality_profile"] = fallback_quality_profile
                if "early_stop_evaluator" in sig.parameters and early_stop_evaluator is not None:
                    kwargs["early_stop_evaluator"] = early_stop_evaluator
                return await async_search(query, strategy_filters, **kwargs)
            except (TypeError, ValueError):
                pass
            return await async_search(query, strategy_filters)

        loop = asyncio.get_running_loop()
        search_fn = provider.search
        try:
            sig = inspect.signature(search_fn)
            call_kwargs: dict[str, Any] = {"basic_filters": strategy_filters}
            if "quality_profile" in sig.parameters:
                call_kwargs["quality_profile"] = quality_profile
            if "includes" in sig.parameters:
                call_kwargs["includes"] = includes
            if "excludes" in sig.parameters:
                call_kwargs["excludes"] = excludes
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

    def _get_active_download_providers(self) -> list[PluginBase]:
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

    def queue_download(
        self,
        track: EchosyncTrack,
        quality_profile_id: str | None = None,
        intent: str | DownloadIntent = DownloadIntent.MANUAL_OMNI,
    ) -> int:
        """Add a track to the download queue.

        Returns the database ID of the new download record.
        """
        track_title = track.title or getattr(track, "raw_title", "") or ""
        logger.info(f"Queueing download: {track.artist_name} - {track_title}")

        intent_val = intent.value if isinstance(intent, DownloadIntent) else str(intent)

        # Check if track already exists in library (use album + duration when available)
        album_name = getattr(track, "album_title", None) or getattr(track, "album", None)
        duration_ms = getattr(track, "duration_ms", None) or getattr(track, "duration", None)
        if self._track_exists_in_library(track.artist_name, track_title, album=album_name, duration=duration_ms):
            logger.info(f"Skipping download: Track '{track_title}' by '{track.artist_name}' already exists in library")
            return 0  # 0 indicates no download created

        with self.work_db.session_scope() as session:
            # Serialize track to JSON for storage
            track_json = track.to_dict()
            if quality_profile_id:
                identifiers = track_json.setdefault("identifiers", {})
                identifiers["quality_profile_id"] = str(quality_profile_id)

            # Prevent duplicate queue entries for the same track
            existing = self._find_existing_download(track_json, include_failed=True)
            if existing:
                existing_id, existing_status = existing
                if existing_status in {
                    DownloadStatus.QUEUED.value,
                    DownloadStatus.SEARCHING.value,
                    DownloadStatus.DOWNLOADING.value,
                    DownloadStatus.VERIFYING.value,
                    DownloadStatus.RETRYING.value,
                    "queued",
                    "searching",
                    "downloading",
                    "in_progress",
                    "paused",
                    "verifying",
                    "retrying",
                }:
                    logger.info(
                        f"Duplicate download detected (ID {existing_id}, status {existing_status}); skipping enqueue"
                    )
                    return existing_id
                else:
                    # Existing item was in failed/error state — reset and reuse instead of inserting a duplicate row
                    existing_item = session.query(DownloadQueue).filter(DownloadQueue.id == existing_id).first()
                    if existing_item:
                        existing_item.status = DownloadStatus.QUEUED.value
                        existing_item.intent = intent_val
                        existing_item.echo_sync_track = track_json
                        existing_item.plugin_id = None
                        existing_item.active_candidate_id = None
                        existing_item.candidate_stack = []
                        existing_item.blacklisted_candidates = []
                        existing_item.retry_count = 0
                        existing_item.error_reason = None
                        existing_item.updated_at = utc_now()
                        with db_write_lease(task_name="queue_download_requeue"):
                            session.commit()
                        logger.info(f"Re-queueing existing failed download record ID {existing_id} for '{track.title}'")
                        return existing_id

            download = DownloadQueue(
                sync_id=track.sync_id,
                intent=intent_val,
                echo_sync_track=track_json,
                status=DownloadStatus.QUEUED.value,
                active_candidate_id=None,
                candidate_stack=[],
                blacklisted_candidates=[],
                retry_count=0,
                error_reason=None,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(download)
            session.flush()  # Populate ID

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
                .filter(DownloadQueue.status.in_([DownloadStatus.SEARCHING.value, DownloadStatus.DOWNLOADING.value]))
                .all()
            )
            if stuck_items:
                logger.warning(
                    f"Found {len(stuck_items)} stuck downloads (searching/downloading). Resetting to 'queued'."
                )
                for item in stuck_items:
                    item.status = "queued"
                    item.provider_id = None
                    item.updated_at = utc_now()

    async def _process_loop(self):
        """Main control loop: Process Queue -> Check Active"""
        # 0. Recover stuck items, deduplicate queue, and clean up queue on startup
        await self._recover_stuck_items()
        self._deduplicate_queue()
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
                await asyncio.sleep(10)  # Backoff on error

    async def _process_queued_items(self):
        """Pick up queued items and attempt to find/start them using waterfall provider strategy"""
        if not hasattr(self, "_processing_queue_lock") or self._processing_queue_lock is None:
            self._processing_queue_lock = asyncio.Lock()

        if self._processing_queue_lock.locked():
            logger.debug("Queue processing already in progress; skipping duplicate run.")
            return

        async with self._processing_queue_lock:
            self._reclaim_orphaned_searching_items()
            self._deduplicate_queue()

            # Fetch queued items from DB
            queued_ids = []
            with self.work_db.session_scope() as session:
                # Get up to 30 actionable items (QUEUED or RETRYING) to enable concurrent searches
                items = (
                    session.query(DownloadQueue)
                    .filter(
                        DownloadQueue.status.in_(
                            [DownloadStatus.QUEUED.value, DownloadStatus.RETRYING.value]
                        )
                    )
                    .order_by(
                        DownloadQueue.retry_count.asc().nullsfirst(),
                        DownloadQueue.created_at.desc(),
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
                    if (
                        artist
                        and title
                        and self._track_exists_in_library(artist, title, album=album, duration=duration)
                    ):
                        logger.info(
                            f"JIT Check: Track '{artist} - {title}' already exists in library. Transitioning status to 'completed'."
                        )
                        item.status = "completed"
                        item.updated_at = utc_now()
                        continue

                    # Mark as processing so other workers (if any) don't grab it
                    item.status = "searching"
                    item.updated_at = utc_now()
                    queued_ids.append(item.id)

            if not queued_ids:
                return

            providers = self._get_active_download_providers()
            if not providers:
                logger.debug("Skipping queue processing: No active download providers.")
                with self.work_db.session_scope() as session:
                    for qid in queued_ids:
                        it = session.get(DownloadQueue, qid)
                        if it and it.status == "searching":
                            it.status = "queued"
                return

            # Determine concurrency dynamically from active provider capabilities
            if providers:
                provider = providers[0]
                concurrency = (
                    getattr(provider.capabilities, "max_concurrency", 3) if hasattr(provider, "capabilities") else 3
                )
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
                logger.info(
                    f"Started {len(tasks)} search tasks (throttled to {concurrency} concurrent) with {len(providers)} providers in waterfall priority order"
                )
                results = await asyncio.gather(*tasks, return_exceptions=True)
                failed = sum(1 for r in results if isinstance(r, Exception))
                if failed > 0:
                    logger.warning(f"Completed {len(tasks)} searches with {failed} errors")

    async def _execute_waterfall_search_and_download(self, download_id: int, providers: list[PluginBase]):
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
        acq_state: dict[str, Any] = {}
        with self.work_db.session_scope() as session:
            download = session.query(DownloadQueue).get(download_id)
            if not download:
                logger.error(f"DownloadQueue ID {download_id} not found in DB.")
                return
            # Reconstruct from stored JSON to preserve all metadata
            target_track = EchosyncTrack.from_dict(download.echo_sync_track)
            raw_track_dict = download.echo_sync_track if isinstance(download.echo_sync_track, dict) else {}
            acq_state = dict(raw_track_dict.get("_acquisition_state") or {})
            blacklisted_candidates = set(raw_track_dict.get("blacklisted_candidates") or [])
            for b in getattr(download, "blacklisted_candidates", None) or []:
                if isinstance(b, dict) and b.get("candidate_id"):
                    blacklisted_candidates.add(b["candidate_id"])
                elif isinstance(b, str):
                    blacklisted_candidates.add(b)

        if not target_track:
            logger.error(f"Failed to deserialize track for download {download_id}")
            self._update_status(download_id, DownloadStatus.FAILED)
            return

        if not hasattr(self, "_active_search_ids"):
            self._active_search_ids = set()
        self._active_search_ids.add(download_id)

        try:
            self.transition_to_searching(download_id)
        except Exception:
            pass

        # Re-check library existence immediately before searching. A track can enter the
        # library between enqueue-time and the moment this job fires (e.g. auto-import,
        # manual import, or a previous download cycle completing). Catching it here avoids
        # a redundant provider search and a duplicate file on disk.
        album_name = getattr(target_track, "album_title", None) or getattr(target_track, "album", None)
        duration_ms = getattr(target_track, "duration_ms", None) or getattr(target_track, "duration", None)
        if self._track_exists_in_library(
            target_track.artist_name,
            target_track.title,
            album=album_name,
            duration=duration_ms,
        ):
            logger.info(
                f"JIT Check: Track '{target_track.artist_name} - {target_track.title}' already present in library. Transitioning status to 'completed'."
            )
            self._update_status(download_id, "completed")
            self._active_search_ids.discard(download_id)
            return

        # Keep provider query broad; matching engine handles duration scoring/gating.
        target_duration_ms = getattr(target_track, "duration_ms", None) or getattr(target_track, "duration", None) or None

        try:
            logger.info(f"Starting waterfall search for: {target_track.artist_name} - {target_track.title}")

            # 1. Get preferred quality profile & optional 1-hop fallback profile
            requested_profile_id = (
                (download.echo_sync_track.get("identifiers") or {}).get("quality_profile_id")
                if isinstance(download.echo_sync_track, dict)
                else None
            )
            quality_profile = self._get_quality_profile(requested_profile_id)
            fallback_profile = self._get_fallback_quality_profile(quality_profile)
            preferred_formats = self._extract_allowed_formats(quality_profile)
            fallback_formats = self._extract_allowed_formats(fallback_profile) if fallback_profile else []
            # Pass union of Preferred + Fallback extensions to provider so fallback promotion
            # requires ZERO extra Soulseek network searches.
            union_formats = list(dict.fromkeys(preferred_formats + fallback_formats))

            # Get duration tolerance from quality profile (default 5 seconds)
            duration_tolerance_ms = 5000
            if quality_profile and "advanced_filters" in quality_profile:
                filters = quality_profile["advanced_filters"]
                if "duration_tolerance_seconds" in filters:
                    duration_tolerance_ms = int(filters["duration_tolerance_seconds"] * 1000)

            # Coarse provider-side duration window: wide enough so WeightedMatchingEngine's
            # deluxe/artist/plugin duration escalations are not prematurely killed at 5.1s.
            coarse_duration_tol_ms = max(duration_tolerance_ms * 2, 12000)

            min_bitrate_pref = self._get_min_bitrate(quality_profile)
            min_bitrate_fb = self._get_min_bitrate(fallback_profile) if fallback_profile else min_bitrate_pref
            basic_filters = {
                "allowed_extensions": union_formats,
                "min_bitrate": min(min_bitrate_pref, min_bitrate_fb),
                "target_duration_ms": target_duration_ms,
                "duration_tolerance_ms": coarse_duration_tol_ms,
            }

            logger.info(
                f"Quality profile allows: {preferred_formats}"
                + (f" (fallback profile: {fallback_formats})" if fallback_profile else "")
            )

            # Generate explicit fallback strategies (artist+title, album+title, title+strict duration)
            strategies = self._generate_search_strategies(target_track, duration_tolerance_ms)
            logger.info(f"Generated {len(strategies)} search strategies")

            # Determine if source requested an unannotated Original (so Remasters go only to fallback pool)
            from core.matching_engine.matching_engine import get_version_family

            src_ver_str = (getattr(target_track, "edition", None) or getattr(target_track, "version", None) or "").strip()
            source_requests_original = get_version_family(src_ver_str) is None

            # ============================================================================
            # WATERFALL PROVIDER SEARCH (SINGLE-PASS DUAL-PROFILE PARTITIONING)
            # ============================================================================
            scored_candidates: list[tuple[EchosyncTrack, float, PluginBase]] = []
            remaster_fallback_candidates: list[tuple[EchosyncTrack, float, PluginBase]] = []
            fallback_profile_candidates: list[tuple[EchosyncTrack, float, PluginBase]] = []
            perfect_match_threshold = 90  # Score >= 90 triggers immediate break once pool filled
            checkpoint_strategy_idx = 0
            checkpoint_total_strategies = len(strategies)
            used_remaster_fallback = False

            # Compact per-item diagnostics (bounded summary — never stores 60-100+ raw candidates)
            diag_strategy_funnel: list[dict[str, Any]] = []
            diag_rejections: dict[str, int] = {
                "version_mismatch": 0,
                "duration_mismatch": 0,
                "low_text_score": 0,
                "format_or_size": 0,
                "blacklisted": 0,
            }

            def _record_rejection(match_res: Any) -> None:
                if match_res is None:
                    return
                if not getattr(match_res, "passed_version_check", True):
                    diag_rejections["version_mismatch"] += 1
                elif getattr(match_res, "duration_match_score", 1.0) == 0.0 and getattr(match_res, "is_near_miss", False):
                    diag_rejections["duration_mismatch"] += 1
                elif getattr(match_res, "fuzzy_text_score", 1.0) < 0.80:
                    diag_rejections["low_text_score"] += 1
                else:
                    diag_rejections["duration_mismatch"] += 1

            def _peer_sort_key(item: tuple[EchosyncTrack, float, PluginBase]):
                cand_obj, sc, _prov = item
                return (
                    round(float(sc), 1),
                    1 if (cand_obj.identifiers.get("free_upload_slots") or 0) > 0 else 0,
                    -(int(cand_obj.identifiers.get("queue_length") or 0)),
                    int(cand_obj.identifiers.get("upload_speed") or 0),
                )

            def _score_candidate(
                matcher_obj: WeightedMatchingEngine,
                cand_obj: EchosyncTrack,
                *,
                context: str = "download",
            ) -> float:
                res = matcher_obj.calculate_match(target_track, cand_obj, context=context)
                score_val = res.confidence_score
                # Strategy 7 (loose_title_duration): allow title+duration fallback when artist metadata differs
                if (
                    score_val < 70.0
                    and context == "download"
                    and cand_obj.identifiers.get("discovery_strategy") == "loose_title_duration"
                    and hasattr(matcher_obj, "calculate_title_duration_match")
                ):
                    td_res = matcher_obj.calculate_title_duration_match(target_track, cand_obj)
                    if td_res.confidence_score > score_val:
                        score_val = td_res.confidence_score
                return score_val

            # Iterate through providers in priority order
            for provider_idx, provider in enumerate(providers, 1):
                logger.info(f"\n=== Provider {provider_idx}/{len(providers)}: {provider.name} ===")
                provider_candidates = []

                # Filter strategy ladder against this provider's capabilities
                provider_strategies = [
                    s
                    for s in strategies
                    if _provider_supports_capability(
                        provider,
                        getattr(s, "required_capability", None)
                        if not isinstance(s, dict)
                        else s.get("required_capability"),
                    )
                ]
                logger.info(
                    f"Provider {provider.name} supports {len(provider_strategies)}/{len(strategies)} strategies"
                )
                if not provider_strategies:
                    logger.info(f"Provider {provider.name} supports none of the requested strategies, skipping...")
                    continue

                matcher = self._get_matching_engine(quality_profile)

                # 10-minute Strategy Checkpoint: resume at last_strategy_idx + 1 when retrying within 600s
                import time

                start_idx = 0
                last_ts = acq_state.get("last_search_ts")
                last_idx = acq_state.get("last_strategy_idx")
                if (
                    isinstance(last_idx, int)
                    and last_idx >= 0
                    and isinstance(last_ts, (int, float))
                    and (time.time() - last_ts) < 600.0
                    and (last_idx + 1) < len(provider_strategies)
                ):
                    start_idx = last_idx + 1
                    logger.info(
                        f"  Resuming search for download {download_id} at strategy {start_idx + 1}/{len(provider_strategies)} "
                        f"(within 10m checkpoint window)"
                    )

                last_executed_strategy_idx = start_idx
                preferred_live_keys: set[tuple[str, str]] = set()

                def _make_live_early_stop(
                    _matcher=matcher,
                    _live_keys=preferred_live_keys,
                ):
                    def _evaluator(delta_tracks: list[EchosyncTrack]) -> bool:
                        for raw_c in delta_tracks:
                            if self._is_candidate_blacklisted(raw_c, blacklisted_candidates):
                                continue
                            enriched_c = self._enrich_candidate_metadata(raw_c)
                            try:
                                pref_ok = self._filter_by_formats([enriched_c], preferred_formats, quality_profile)
                            except TypeError:
                                pref_ok = self._filter_by_formats([enriched_c], preferred_formats)
                            if not pref_ok:
                                continue
                            sc = _matcher.calculate_match(target_track, enriched_c, context="download").confidence_score
                            if sc >= 80.0:
                                uname = str(enriched_c.identifiers.get("username") or "")
                                fname = str(
                                    enriched_c.identifiers.get("plugin_item_id")
                                    or enriched_c.identifiers.get("provider_item_id")
                                    or ""
                                )
                                _live_keys.add((uname, fname))
                                if len(_live_keys) >= 3:
                                    return True
                        return False

                    return _evaluator

                # Try all supported strategies for this provider (starting from checkpoint)
                for strategy_idx in range(start_idx + 1, len(provider_strategies) + 1):
                    strategy = provider_strategies[strategy_idx - 1]
                    last_executed_strategy_idx = strategy_idx - 1
                    checkpoint_strategy_idx = last_executed_strategy_idx
                    checkpoint_total_strategies = len(provider_strategies)
                    # Cooperative Cancellation Check: terminate early if requested
                    try:
                        from core.task_manager.supervisor import supervisor as _sup

                        reg_id = getattr(self, "reg_id", None)
                        is_cancelled = _sup.is_process_cancelled(reg_id) if _sup else False
                    except Exception:
                        is_cancelled = False
                    if is_cancelled or getattr(self, "_stop_requested", False) or getattr(self, "_shutdown", False):
                        logger.info(f"Download {download_id} aborted by cancellation request.")
                        self._update_status(download_id, "failed")
                        return

                    query = getattr(strategy, "wire_query", None) or (
                        strategy["query"] if isinstance(strategy, dict) else ""
                    )
                    strategy_tolerance = getattr(strategy, "duration_tolerance_ms", None) or (
                        strategy["duration_tolerance_ms"] if isinstance(strategy, dict) else duration_tolerance_ms
                    )
                    strategy_name = getattr(strategy, "name", None) or (
                        strategy["name"] if isinstance(strategy, dict) else ""
                    )
                    strategy_includes = getattr(strategy, "includes", None) or (
                        strategy.get("includes") if isinstance(strategy, dict) else None
                    )
                    strategy_excludes = getattr(strategy, "excludes", None) or (
                        strategy.get("excludes") if isinstance(strategy, dict) else None
                    )
                    strategy_filter_expr = getattr(strategy, "filter_expression", None) or (
                        strategy.get("filter_expression") if isinstance(strategy, dict) else None
                    )

                    strategy_filters = dict(basic_filters)
                    # Keep coarse tolerance generous unless Strategy 7 explicitly tightened it
                    if strategy_name == "title+strict-duration":
                        strategy_filters["duration_tolerance_ms"] = strategy_tolerance
                    else:
                        strategy_filters["duration_tolerance_ms"] = max(int(strategy_tolerance) * 2, 12000)
                    if strategy_filter_expr:
                        strategy_filters["filter_expression"] = strategy_filter_expr

                    logger.info(
                        f"  Strategy {strategy_idx}/{len(provider_strategies)} [{strategy_name}] "
                        f"via {provider.name}: query='{query}'"
                    )

                    # Call provider search (with live in-poll early stop + dual-profile support)
                    search_results: list[EchosyncTrack] = []
                    sniper_hit = False
                    strat_t0 = time.monotonic()
                    try:
                        logger.debug(f"    Invoking search on {provider.name} with quality profile")
                        invoke_kwargs: dict[str, Any] = {
                            "target_track": target_track,
                            "strategy_name": strategy_name,
                            "perfect_match_threshold": perfect_match_threshold,
                            "includes": strategy_includes,
                            "excludes": strategy_excludes,
                        }
                        try:
                            inv_sig = inspect.signature(self._invoke_provider_search)
                            if "blacklisted_candidates" in inv_sig.parameters:
                                invoke_kwargs["blacklisted_candidates"] = blacklisted_candidates
                            if "fallback_quality_profile" in inv_sig.parameters:
                                invoke_kwargs["fallback_quality_profile"] = fallback_profile
                            if "early_stop_evaluator" in inv_sig.parameters:
                                invoke_kwargs["early_stop_evaluator"] = _make_live_early_stop()
                        except (TypeError, ValueError):
                            pass

                        search_results, sniper_hit = await self._invoke_provider_search(
                            provider,
                            query,
                            strategy_filters,
                            quality_profile,
                            **invoke_kwargs,
                        )
                    except Exception as e:
                        diag_strategy_funnel.append(
                            {
                                "strategy": strategy_name,
                                "query": query,
                                "raw": 0,
                                "eligible": 0,
                                "preferred": 0,
                                "elapsed_s": round(time.monotonic() - strat_t0, 2),
                                "outcome": "error",
                            }
                        )
                        logger.warning(
                            f"    Strategy {strategy_idx} [{strategy_name}] failed on {provider.name}: {e}. "
                            f"Advancing to Strategy {strategy_idx + 1}"
                        )
                        continue

                    if not search_results:
                        diag_strategy_funnel.append(
                            {
                                "strategy": strategy_name,
                                "query": query,
                                "raw": 0,
                                "eligible": 0,
                                "preferred": 0,
                                "elapsed_s": round(time.monotonic() - strat_t0, 2),
                                "outcome": "0_results",
                            }
                        )
                        logger.info(
                            f"    Strategy {strategy_idx} returned 0 candidates, advancing to Strategy {strategy_idx + 1}"
                        )
                        continue

                    logger.info(f"    Strategy {strategy_idx} returned {len(search_results)} candidates")

                    if search_results:
                        valid_results = []
                        for c in search_results:
                            if self._is_candidate_blacklisted(c, blacklisted_candidates):
                                diag_rejections["blacklisted"] += 1
                                pid = c.identifiers.get("plugin_item_id") or c.identifiers.get("provider_item_id")
                                username = c.identifiers.get("username")
                                logger.info(f"    Skipping blacklisted candidate '{pid}' from user '{username}'")
                                continue
                            c.identifiers["discovery_strategy"] = (
                                getattr(strategy, "strategy_type", None)
                                or (strategy.get("strategy_type") if isinstance(strategy, dict) else None)
                                or strategy_name
                            )
                            c.identifiers["strategy_name"] = strategy_name
                            valid_results.append(c)
                        enriched_results = [self._enrich_candidate_metadata(c) for c in valid_results]
                        provider_candidates.extend(enriched_results)

                        # Short-circuit ONLY on Preferred Profile candidates (never Fallback Profile
                        # and never Remaster substitutes when an Original was requested).
                        viable_preferred = 0
                        has_preferred_snipe = False
                        for cand in enriched_results:
                            try:
                                viable_cand = self._filter_by_formats([cand], preferred_formats, quality_profile)
                            except TypeError:
                                viable_cand = self._filter_by_formats([cand], preferred_formats)
                            if not viable_cand:
                                diag_rejections["format_or_size"] += 1
                                continue

                            match_obj = matcher.calculate_match(target_track, cand, context="download")
                            raw_score = match_obj.confidence_score
                            if raw_score < 70.0 and cand.identifiers.get("discovery_strategy") == "loose_title_duration" and hasattr(matcher, "calculate_title_duration_match"):
                                td_res = matcher.calculate_title_duration_match(target_track, cand)
                                if td_res.confidence_score > raw_score:
                                    raw_score = td_res.confidence_score
                                    match_obj = td_res
                            if raw_score < 70.0:
                                _record_rejection(match_obj)
                            if raw_score >= perfect_match_threshold:
                                has_preferred_snipe = True
                            if raw_score >= 75.0:
                                viable_preferred += 1

                        did_short_circuit = viable_preferred >= 3 or (
                            has_preferred_snipe and (viable_preferred >= 3 or sniper_hit)
                        )
                        diag_strategy_funnel.append(
                            {
                                "strategy": strategy_name,
                                "query": query,
                                "raw": len(search_results),
                                "eligible": len(enriched_results),
                                "preferred": viable_preferred,
                                "elapsed_s": round(time.monotonic() - strat_t0, 2),
                                "outcome": "short_circuited" if did_short_circuit else "advanced",
                            }
                        )
                        if did_short_circuit:
                            logger.info(
                                f"  ⚡ Strategy {strategy_idx} [{strategy_name}] populated Preferred pool "
                                f"(snipe={has_preferred_snipe}, viable_preferred={viable_preferred}) "
                                f"— holding at strategy {strategy_idx}/{len(provider_strategies)}."
                            )
                            break

                matcher = self._get_matching_engine(quality_profile)

                # ── Deduplicate + Preferred Profile / Remaster Fallback / Fallback Profile scoring ──
                provider_candidates = self._deduplicate_candidates(provider_candidates)
                logger.info(f"  Total candidates from {provider.name}: {len(provider_candidates)}")

                if not provider_candidates:
                    logger.info(f"  No candidates found on {provider.name}, trying next provider...")
                    continue

                def _evaluate_profile_into_pool(
                    prof: dict[str, Any] | None,
                    prof_formats: list[str],
                    target_pool: list[tuple[EchosyncTrack, float, PluginBase]],
                    *,
                    match_context: str = "download",
                    _candidates=provider_candidates,
                    _provider=provider,
                ) -> None:
                    tiers = self._get_priority_tiers(prof)
                    if not tiers:
                        tiers = [(0, prof_formats)]
                    prof_matcher = self._get_matching_engine(prof)
                    for priority_num, priority_formats in tiers:
                        try:
                            tier_candidates = self._filter_by_formats(
                                _candidates,
                                priority_formats,
                                prof,
                                priority=priority_num,
                            )
                        except TypeError:
                            try:
                                tier_candidates = self._filter_by_formats(
                                    _candidates, priority_formats, prof
                                )
                            except TypeError:
                                tier_candidates = self._filter_by_formats(_candidates, priority_formats)
                        if not tier_candidates:
                            continue

                        tier_hits: list[tuple[EchosyncTrack, float, PluginBase]] = []
                        for candidate in tier_candidates:
                            raw_score = _score_candidate(prof_matcher, candidate, context=match_context)
                            if raw_score >= 70.0:
                                tier_hits.append((candidate, raw_score, _provider))

                        if tier_hits:
                            tier_hits.sort(key=_peer_sort_key, reverse=True)
                            target_pool.extend(tier_hits[:3])
                            # Preserve profile format priority ordering: stop advancing lower format tiers
                            # once we have 3 qualifying candidates in higher-priority format rules.
                            if len(target_pool) >= 3:
                                break

                    if target_pool:
                        target_pool.sort(key=_peer_sort_key, reverse=True)
                        del target_pool[3:]

                # 1. Preferred Profile (strict Original if Original requested)
                _evaluate_profile_into_pool(
                    quality_profile, preferred_formats, scored_candidates, match_context="download"
                )

                # 2. Remaster fallback pool (ONLY if Original was requested and Preferred pool has < 3)
                if source_requests_original and len(scored_candidates) < 3:
                    _evaluate_profile_into_pool(
                        quality_profile,
                        preferred_formats,
                        remaster_fallback_candidates,
                        match_context="download_remaster_fallback",
                    )

                # 3. Fallback ("Good Enough") Profile evaluated IN-MEMORY (0 extra Soulseek searches!)
                if fallback_profile and len(scored_candidates) == 0:
                    _evaluate_profile_into_pool(
                        fallback_profile,
                        fallback_formats,
                        fallback_profile_candidates,
                        match_context="download",
                    )

                # Release raw provider candidate payloads immediately
                provider_candidates.clear()

                if scored_candidates:
                    best_provider_score = scored_candidates[0][1]
                    logger.info(f"  Current best Preferred match: score={best_provider_score:.1f}")
                    if best_provider_score >= perfect_match_threshold and len(scored_candidates) >= 3:
                        logger.info(
                            f"  ✓ PERFECT PREFERRED POOL from {provider.name} "
                            f"(score {best_provider_score:.1f} >= {perfect_match_threshold}, count={len(scored_candidates)})"
                        )
                        break
                else:
                    logger.info(f"  No acceptable Preferred match from {provider.name}")
                    continue

            # Assemble final Top-3:
            # - Preferred Originals ALWAYS occupy Pick #1 (Remasters can NEVER displace an Original).
            # - If Preferred Originals has 1-2 items, backfill remaining backup slots from remaster_fallback_candidates.
            # - If Preferred Originals is empty, try remaster_fallback_candidates (marking in-memory remaster flag).
            # - If still empty after all strategies, promote Fallback ("Good Enough") Profile pool.
            final_pool: list[tuple[EchosyncTrack, float, PluginBase]] = list(scored_candidates)
            if remaster_fallback_candidates:
                existing_keys = {
                    (prov.name, c.identifiers.get("provider_item_id") or c.identifiers.get("plugin_item_id"))
                    for c, _, prov in final_pool
                }
                for cand, sc, prov in remaster_fallback_candidates:
                    ckey = (prov.name, cand.identifiers.get("provider_item_id") or cand.identifiers.get("plugin_item_id"))
                    if ckey not in existing_keys and len(final_pool) < 3:
                        if not final_pool:
                            used_remaster_fallback = True
                        final_pool.append((cand, sc, prov))
                        existing_keys.add(ckey)

            if not final_pool and fallback_profile_candidates:
                logger.info(
                    f"Preferred profile yielded 0 candidates across all strategies; "
                    f"promoting {len(fallback_profile_candidates)} candidate(s) from fallback profile."
                )
                final_pool = list(fallback_profile_candidates)

            if not hasattr(self, "_remaster_fallback_ids"):
                self._remaster_fallback_ids = set()
            if used_remaster_fallback:
                self._remaster_fallback_ids.add(download_id)
            else:
                self._remaster_fallback_ids.discard(download_id)

            # ============================================================================
            # DOWNLOAD CANDIDATE (WITH PEER ENQUEUE FALLBACK RESILIENCE)
            # ============================================================================
            # Deduplicate final_pool by (provider.name, filename) and retain Top-3 (preserving priority order)
            unique_candidates: list[tuple[EchosyncTrack, float, PluginBase]] = []
            seen_cand_keys = set()
            for cand, score, prov in final_pool:
                fname = cand.identifiers.get("provider_item_id") or cand.identifiers.get("plugin_item_id")
                ckey = (prov.name, fname)
                if ckey not in seen_cand_keys:
                    seen_cand_keys.add(ckey)
                    unique_candidates.append((cand, score, prov))

            unique_candidates = unique_candidates[:3]

            def _build_diagnostics_payload(finalists: list[dict[str, Any]], outcome_event: str) -> dict[str, Any]:
                return {
                    "strategy_funnel": diag_strategy_funnel[:12],
                    "rejection_histogram": {k: v for k, v in diag_rejections.items() if v > 0},
                    "pool_counts": {
                        "preferred": len(scored_candidates),
                        "remaster_fallback": len(remaster_fallback_candidates),
                        "fallback_profile": len(fallback_profile_candidates),
                    },
                    "top_candidates": [
                        {
                            "peer": d["username"],
                            "filename": d["filename"],
                            "score": round(float(d["score"]), 1),
                            "pool": (
                                "remaster_fallback"
                                if used_remaster_fallback
                                else ("fallback_profile" if not scored_candidates and fallback_profile_candidates else "preferred")
                            ),
                        }
                        for d in finalists[:3]
                    ],
                    "timeline": [
                        {
                            "ts": utc_now().isoformat(),
                            "event": outcome_event,
                            "candidate_id": finalists[0]["id"] if finalists else None,
                            "detail": (
                                f"Selected {len(finalists)} finalist(s) after {len(diag_strategy_funnel)} strategy step(s)"
                                if finalists
                                else f"No match >= 70% across {len(diag_strategy_funnel)} strategy step(s)"
                            ),
                        }
                    ],
                }

            if not unique_candidates:
                logger.warning(f"No suitable candidate matched across all {len(providers)} providers (min score: 70%)")
                try:
                    with self.work_db.session_scope() as session:
                        item = session.query(DownloadQueue).get(download_id)
                        if item and isinstance(item.echo_sync_track, dict):
                            updated_payload = dict(item.echo_sync_track)
                            updated_payload["_diagnostics"] = _build_diagnostics_payload([], "SEARCH_EXHAUSTED")
                            item.echo_sync_track = updated_payload
                            item.error_reason = "NO_MATCHING_CANDIDATES"
                except Exception:
                    pass
                self._update_status(download_id, DownloadStatus.FAILED)
                return

            candidate_descriptors = []
            for cand, score, prov in unique_candidates:
                uname = cand.identifiers.get("username") or "unknown"
                fname = cand.identifiers.get("plugin_item_id") or cand.identifiers.get("provider_item_id") or ""
                cid = f"{uname}|{fname}" if uname and fname else (fname or cand.sync_id or "")
                candidate_descriptors.append(
                    {
                        "id": cid,
                        "username": uname,
                        "filename": fname,
                        "size": cand.identifiers.get("size") or 0,
                        "score": float(score),
                        "plugin_id": getattr(prov, "plugin_id", None) or getattr(prov, "name", None),
                        "provider_name": prov.name,
                    }
                )

            active_candidate = candidate_descriptors[0]
            remaining_stack = candidate_descriptors[1:]

            with self.work_db.session_scope() as session:
                item = session.query(DownloadQueue).get(download_id)
                if item:
                    item.active_candidate_id = active_candidate["id"]
                    item.candidate_stack = remaining_stack
                    item.plugin_id = str(active_candidate.get("plugin_id") or "")
                    if isinstance(item.echo_sync_track, dict):
                        updated_payload = dict(item.echo_sync_track)
                        updated_payload["_acquisition_state"] = {
                            "last_strategy_idx": checkpoint_strategy_idx,
                            "total_strategies": checkpoint_total_strategies,
                            "last_search_ts": time.time(),
                        }
                        updated_payload["_diagnostics"] = _build_diagnostics_payload(
                            candidate_descriptors, "CANDIDATES_SELECTED"
                        )
                        item.echo_sync_track = updated_payload
                    if hasattr(session, "commit"):
                        with db_write_lease(task_name="update_candidate_stack"):
                            session.commit()

            logger.info(
                f"**PROCEEDING WITH DOWNLOAD EVALUATION** ({len(unique_candidates)} qualifying Top candidate(s) >= 70%)"
            )

            download_started = False
            for cand_idx, (candidate, score, download_provider) in enumerate(unique_candidates):
                username = candidate.identifiers.get("username") or "unknown"
                filename = candidate.identifiers.get("provider_item_id") or candidate.identifiers.get("plugin_item_id")
                size = candidate.identifiers.get("size") or 0
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
                        "BEFORE_DOWNLOAD_START",
                        None,
                        target_track=target_track.to_dict(),
                        candidate=candidate.to_dict(),
                        provider=download_provider.name,
                    )
                    if plugin_decision == "ABORT":
                        logger.warning(
                            f"Plugin aborted download for: {candidate.title} on {download_provider.name}. "
                            f"Falling back to next best candidate."
                        )
                        continue

                    if hasattr(download_provider, "_async_download"):
                        provider_id = await download_provider._async_download(username, filename, size)
                    else:
                        loop = asyncio.get_running_loop()
                        provider_id = await loop.run_in_executor(
                            None, download_provider.download, username, filename, size
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to enqueue candidate from user '{username}': {e}. Falling back to next best candidate."
                    )
                    continue

                if provider_id:
                    logger.info(f"DownloadQueue started: {provider_id}")
                    self._update_status(download_id, DownloadStatus.DOWNLOADING, provider_id)
                    download_started = True
                    break
                else:
                    logger.warning(
                        f"Failed to enqueue candidate from user '{username}'. Falling back to next best candidate."
                    )

            if not download_started:
                logger.error(f"All candidate download attempts failed for download {download_id}")
                self._update_status(download_id, DownloadStatus.FAILED)

        except asyncio.CancelledError:
            logger.warning(
                f"Search task for download {download_id} was cancelled; resetting from SEARCHING to QUEUED."
            )
            try:
                with self.work_db.session_scope() as session:
                    item = session.get(DownloadQueue, download_id)
                    if item and str(item.status).upper() == DownloadStatus.SEARCHING.value:
                        item.status = DownloadStatus.QUEUED.value
                        item.updated_at = utc_now()
            except Exception:
                pass
            raise
        except Exception as e:
            logger.error(
                f"Error executing waterfall search and download {download_id}: {e}",
                exc_info=True,
            )
            self._update_status(download_id, DownloadStatus.FAILED)
        finally:
            if hasattr(self, "_active_search_ids"):
                self._active_search_ids.discard(download_id)

    def _can_resume_next_strategy(self, download_id: int) -> bool:
        """Return True if download has unsearched strategies remaining within the 10-minute checkpoint window."""
        import time

        with self.work_db.session_scope() as session:
            item = session.get(DownloadQueue, download_id)
            if not item or not isinstance(item.echo_sync_track, dict):
                return False
            acq = item.echo_sync_track.get("_acquisition_state") or {}
            last_idx = acq.get("last_strategy_idx")
            total = acq.get("total_strategies")
            last_ts = acq.get("last_search_ts")
            return bool(
                isinstance(last_idx, int)
                and isinstance(total, int)
                and isinstance(last_ts, (int, float))
                and (time.time() - last_ts) < 600.0
                and (last_idx + 1) < total
            )

    def _append_diagnostic_event(
        self,
        download_id: int,
        event: str,
        candidate_id: str | None = None,
        detail: str | None = None,
    ) -> None:
        """Append a bounded timeline event to echo_sync_track['_diagnostics']['timeline']."""
        try:
            with self.work_db.session_scope() as session:
                item = session.get(DownloadQueue, download_id)
                if not item or not isinstance(item.echo_sync_track, dict):
                    return
                payload = dict(item.echo_sync_track)
                diag = dict(payload.get("_diagnostics") or {})
                timeline = list(diag.get("timeline") or [])
                timeline.append(
                    {
                        "ts": utc_now().isoformat(),
                        "event": str(event),
                        "candidate_id": candidate_id,
                        "detail": detail,
                    }
                )
                diag["timeline"] = timeline[-15:]
                payload["_diagnostics"] = diag
                item.echo_sync_track = payload
        except Exception:
            pass

    async def _handle_active_download_failure(
        self,
        db_id: int,
        failed_candidate_id: str,
        all_providers: list[PluginBase],
        cancel_providers: list[PluginBase],
        reason: str,
    ) -> None:
        """Cancel remote transfer, rotate candidate via DownloadRepository, and dispatch backup or resume strategies."""
        if hasattr(self, "_transfer_progress_tracker"):
            self._transfer_progress_tracker.pop(db_id, None)
        self._append_diagnostic_event(db_id, reason, candidate_id=failed_candidate_id)
        await self._cancel_transfer_async(cancel_providers, failed_candidate_id)

        rotated = self.repo.transition_to_retrying_or_failed(
            db_id,
            reason=reason,
            failed_candidate_id=failed_candidate_id,
        )
        has_next_backup = False
        if rotated:
            with self.work_db.session_scope() as session:
                refreshed = session.get(DownloadQueue, db_id)
                has_next_backup = bool(refreshed and refreshed.active_candidate_id)

        if rotated and has_next_backup:
            # Await directly so short-lived asyncio.run() poller loops do not cancel the dispatch
            await self._dispatch_candidate(db_id, providers=all_providers)
        elif self._can_resume_next_strategy(db_id):
            logger.info(
                f"Download {db_id} exhausted Top-3 backups ({reason}); resuming next search strategy within 10m window."
            )
            self._update_status(db_id, DownloadStatus.RETRYING.value)
            # Delegate to JobQueue-backed single-download runner so the search survives poller loop exit
            self.process_single_download(db_id)
        elif rotated:
            self._update_status(db_id, DownloadStatus.RETRYING.value)
            self.process_single_download(db_id)

    async def _check_active_downloads(self):
        """Poll providers for status of active downloads using waterfall strategy"""
        providers = self._get_active_download_providers()
        if not providers:
            return

        active_downloads = []
        with self.work_db.session_scope() as session:
            # Find items marked 'downloading'
            items = session.query(DownloadQueue).filter(DownloadQueue.status == DownloadStatus.DOWNLOADING.value).all()
            for item in items:
                transfer_id = (
                    item.provider_id
                    if (item.provider_id and "|" in item.provider_id)
                    else (item.active_candidate_id or item.provider_id)
                )
                active_downloads.append((item.id, transfer_id))

        if not active_downloads:
            return

        logger.debug(
            f"Checking status for {len(active_downloads)} active downloads across {len(providers)} providers..."
        )

        for db_id, provider_id in active_downloads:
            if not provider_id:
                continue

            try:
                # Try to find which provider has this download
                status = None
                found_provider = None

                for provider in providers:
                    if not hasattr(provider, "_async_get_download_status") and not hasattr(
                        provider, "get_download_status"
                    ):
                        continue

                    try:
                        if hasattr(provider, "_async_get_download_status"):
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
                    remote_state = status.get("status", "").lower()
                    progress_pct = status.get("progress", 0)

                    try:
                        from core.hook_manager import hook_manager

                        # Use a persistent dict on the class to track last announced progress
                        if not hasattr(self, "_last_progress_event"):
                            self._last_progress_event = {}

                        last_pct = self._last_progress_event.get(db_id, -100)
                        if abs(progress_pct - last_pct) >= 5 or progress_pct >= 100:
                            hook_manager.apply_filters(
                                "ON_DOWNLOAD_PROGRESS",
                                None,
                                download_id=db_id,
                                provider_id=provider_id,
                                progress=progress_pct,
                                state=remote_state,
                            )
                            self._last_progress_event[db_id] = progress_pct
                    except Exception as e:
                        logger.error(f"Error in ON_DOWNLOAD_PROGRESS hook: {e}")

                    new_status = DownloadStatus.DOWNLOADING.value
                    if remote_state == "complete":
                        new_status = DownloadStatus.VERIFYING.value
                    elif remote_state == "failed":
                        new_status = DownloadStatus.FAILED.value
                    elif remote_state == "queued":
                        new_status = DownloadStatus.DOWNLOADING.value

                    # Extract speed and progress (0-100)
                    speed = status.get("speed", 0.0)  # bytes/s
                    progress = status.get("progress", 0.0)  # 0.0 to 100.0

                    if new_status == DownloadStatus.VERIFYING.value:
                        self._transfer_progress_tracker.pop(db_id, None)
                        file_path = status.get("file_path") or status.get("local_path") or status.get("path")
                        self.transition_to_verifying(db_id, file_path=file_path)
                    elif new_status == DownloadStatus.FAILED.value:
                        logger.warning(
                            f"Download {db_id} transfer errored/rejected on {found_provider or 'provider'} "
                            f"(ID: {provider_id}). Cancelling remote transfer and rotating candidate."
                        )
                        active_prov = next(
                            (p for p in providers if p.name == found_provider),
                            providers[0],
                        )
                        await self._handle_active_download_failure(
                            db_id,
                            provider_id,
                            providers,
                            [active_prov],
                            reason="TRANSFER_FAILED",
                        )
                    else:
                        # Enforce 5-minute queued/0% stall timeout and 2-minute mid-transfer freeze timeout
                        import time as _time

                        now_mono = _time.monotonic()
                        tracker = self._transfer_progress_tracker.get(db_id)
                        if tracker is None or tracker.get("transfer_id") != provider_id:
                            tracker = {
                                "transfer_id": provider_id,
                                "first_seen_ts": now_mono,
                                "last_progress_ts": now_mono,
                                "last_progress_pct": float(progress or 0.0),
                            }
                            self._transfer_progress_tracker[db_id] = tracker
                        else:
                            cur_pct = float(progress or 0.0)
                            if cur_pct > tracker["last_progress_pct"] + 0.01 or float(speed or 0.0) > 1024.0:
                                tracker["last_progress_pct"] = cur_pct
                                tracker["last_progress_ts"] = now_mono

                        stalled_seconds = now_mono - tracker["last_progress_ts"]
                        is_queued_stall = tracker["last_progress_pct"] <= 0.01 and stalled_seconds >= 300.0
                        is_mid_transfer_freeze = tracker["last_progress_pct"] > 0.01 and stalled_seconds >= 120.0

                        if is_queued_stall or is_mid_transfer_freeze:
                            stall_reason = "PEER_QUEUED_TIMEOUT" if is_queued_stall else "PEER_TRANSFER_FROZEN"
                            logger.warning(
                                f"Download {db_id} stalled ({stall_reason}, {stalled_seconds:.0f}s at {tracker['last_progress_pct']:.1f}%) "
                                f"on {found_provider} (ID: {provider_id}). Rotating to next candidate."
                            )
                            active_prov = next(
                                (p for p in providers if p.name == found_provider),
                                providers[0],
                            )
                            await self._handle_active_download_failure(
                                db_id,
                                provider_id,
                                providers,
                                [active_prov],
                                reason=stall_reason,
                            )
                            continue

                        self._update_status(db_id, new_status, provider_id, speed, progress)
                        if new_status != DownloadStatus.DOWNLOADING.value:
                            logger.info(
                                f"DownloadQueue {db_id} (Provider {found_provider}, ID {provider_id}) finished with status: {new_status}"
                            )
                else:
                    logger.warning(
                        f"DownloadQueue {db_id} not found in active transfers (disappeared) - "
                        f"treating as failed, cleaning remote state, and rotating candidate."
                    )
                    await self._handle_active_download_failure(
                        db_id,
                        provider_id,
                        providers,
                        providers,
                        reason="TRANSFER_DISAPPEARED",
                    )

            except Exception as e:
                logger.error(f"Error checking status for {db_id}: {e}")

    def _generate_search_strategies(
        self, track: EchosyncTrack, base_duration_tolerance_ms: int
    ) -> list[SearchStrategyIntent]:
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
        strategies: list[SearchStrategyIntent] = []

        # Build a core title for provider search by stripping bracketed/parenthetical
        # qualifiers, then applying standard normalization.
        base_track_title = track.title or getattr(track, "raw_title", "") or ""
        search_title = self._build_core_search_title(base_track_title)
        if search_title != base_track_title:
            logger.info(f"Normalized title for search: '{base_track_title}' -> '{search_title}'")

        from core.matching_engine.text_utils import (
            fold_diacritics_for_wire,
            sanitize_query_preserve_keyboard,
        )

        primary_artist, collaborators = split_artist_collaborators(track.artist_name)
        raw_artist_str = track.artist_name or ""
        # Preserve pure duo/group names joined only by '&' or 'and' (e.g. "Pat & Sean", "Hall & Oates")
        # instead of splitting into single-word noise queries like "Pat" and "Sean".
        _explicit_collab_marker = re.search(
            r"(?:[,/+]|\bfeat\.?\b|\bft\.?\b|\bfeaturing\b|\bwith\b|\bx\b|[\u00d7\u0445\u2715\u2716×✕✖])",
            raw_artist_str,
            flags=re.IGNORECASE,
        )
        is_pure_ampersand_duo = bool(
            collaborators
            and not _explicit_collab_marker
            and re.search(r"\s+(?:&|and)\s+", raw_artist_str, flags=re.IGNORECASE)
            and len(collaborators) == 1
        )
        effective_primary_artist = raw_artist_str if is_pure_ampersand_duo else (primary_artist or raw_artist_str)
        effective_collaborators = [] if is_pure_ampersand_duo else collaborators

        wire_primary_artist = sanitize_query_preserve_keyboard(effective_primary_artist)
        wire_search_title = sanitize_query_preserve_keyboard(search_title)
        folded_artist = fold_diacritics_for_wire(effective_primary_artist)
        folded_title = fold_diacritics_for_wire(search_title)
        target_dur = getattr(track, "duration_ms", None) or getattr(track, "duration", None) or None

        # Determine non-original edition / remixer cue if explicitly set on the track
        raw_edition = (getattr(track, "edition", None) or getattr(track, "version", None) or "").strip()
        raw_remixers = [str(r).strip() for r in (getattr(track, "remixers", None) or []) if str(r).strip()]
        _ignorable_editions = {"", "original", "album version", "standard", "deluxe", "deluxe edition", "explicit", "clean"}
        edition_cue = ""
        if raw_edition and raw_edition.lower() not in _ignorable_editions:
            edition_cue = sanitize_query_preserve_keyboard(raw_edition)
        elif raw_remixers:
            edition_cue = sanitize_query_preserve_keyboard(raw_remixers[0])

        # Strategy 1 (ISRC / Strict GUID if available - requires Capability.FETCH_BY_ISRC)
        if getattr(track, "isrc", None):
            strategies.append(
                SearchStrategyIntent(
                    id="isrc",
                    name="isrc",
                    strategy_type="isrc",
                    wire_query=str(track.isrc).strip().upper(),
                    required_capability=Capability.FETCH_BY_ISRC,
                    target_duration_ms=target_dur,
                    duration_tolerance_ms=int(base_duration_tolerance_ms),
                )
            )

        # Strategy 2a: Edition / Remixer-qualified Artist + Title (when track explicitly requests a remix/live/acoustic/etc.)
        if wire_primary_artist and wire_search_title and edition_cue:
            strategies.append(
                SearchStrategyIntent(
                    id="artist+title+edition",
                    name="artist+title+edition",
                    strategy_type="strict_metadata",
                    wire_query=f"{wire_primary_artist} {wire_search_title} {edition_cue}".strip(),
                    required_capability=None,
                    target_duration_ms=target_dur,
                    duration_tolerance_ms=int(base_duration_tolerance_ms),
                )
            )

        # Strategy 2: Artist + Title (Strict Metadata - Universal Baseline, preserving keyboard symbols like !, $)
        if wire_primary_artist and wire_search_title:
            strategies.append(
                SearchStrategyIntent(
                    id="artist+title",
                    name="artist+title",
                    strategy_type="strict_metadata",
                    wire_query=f"{wire_primary_artist} {wire_search_title}".strip(),
                    required_capability=None,
                    target_duration_ms=target_dur,
                    duration_tolerance_ms=int(base_duration_tolerance_ms),
                )
            )

        # Strategy 2b: Diacritic-folded fallback (e.g., Beyoncé -> Beyonce, Tiësto -> Tiesto) while keeping !, $
        if folded_artist and folded_title and (
            folded_artist.lower() != wire_primary_artist.lower()
            or folded_title.lower() != wire_search_title.lower()
        ):
            strategies.append(
                SearchStrategyIntent(
                    id="artist+title+diacritics_folded",
                    name="artist+title+diacritics_folded",
                    strategy_type="strict_metadata",
                    wire_query=f"{folded_artist} {folded_title}".strip(),
                    required_capability=None,
                    target_duration_ms=target_dur,
                    duration_tolerance_ms=int(base_duration_tolerance_ms),
                )
            )

        # Strategy 3: Artist broad + client-side title filter (Requires Capability.CLIENT_PREFILTER)
        if wire_primary_artist and search_title:
            strategies.append(
                SearchStrategyIntent(
                    id="artist+broad+filter",
                    name="artist+broad+filter",
                    strategy_type="fuzzy_artist_title",
                    wire_query=wire_primary_artist,
                    filter_expression=search_title,
                    includes=[search_title],
                    required_capability=Capability.CLIENT_PREFILTER,
                    target_duration_ms=target_dur,
                    duration_tolerance_ms=int(base_duration_tolerance_ms),
                )
            )

        # Strategy 4: Title + client-side artist filter (Requires Capability.CLIENT_PREFILTER)
        if wire_search_title and wire_primary_artist:
            strategies.append(
                SearchStrategyIntent(
                    id="title+filter_artist",
                    name="title+filter_artist",
                    strategy_type="fuzzy_artist_title",
                    wire_query=wire_search_title,
                    filter_expression=wire_primary_artist,
                    includes=[wire_primary_artist],
                    required_capability=Capability.CLIENT_PREFILTER,
                    target_duration_ms=target_dur,
                    duration_tolerance_ms=int(base_duration_tolerance_ms),
                )
            )

        # Strategy 5: Collaborator + client-side title filter (Requires Capability.CLIENT_PREFILTER)
        for idx, collab in enumerate(effective_collaborators, 1):
            wire_collab = sanitize_query_for_wire(collab)
            if wire_collab and search_title:
                strategies.append(
                    SearchStrategyIntent(
                        id=f"collab+filter_title_{idx}",
                        name="collab+filter_title",
                        strategy_type="fuzzy_artist_title",
                        wire_query=wire_collab,
                        filter_expression=search_title,
                        includes=[search_title],
                        required_capability=Capability.CLIENT_PREFILTER,
                        target_duration_ms=target_dur,
                        duration_tolerance_ms=int(base_duration_tolerance_ms),
                    )
                )

        # Strategy 6: Album + Title (Strict Metadata - Universal Baseline)
        if track.album_title and wire_search_title:
            from core.matching_engine.text_utils import normalize_album

            normalized_album = normalize_album(track.album_title)
            wire_album = sanitize_query_for_wire(normalized_album)
            if wire_album and wire_album.lower() != wire_search_title.lower():
                strategies.append(
                    SearchStrategyIntent(
                        id="album+title",
                        name="album+title",
                        strategy_type="strict_metadata",
                        wire_query=f"{wire_album} {wire_search_title}".strip(),
                        required_capability=None,
                        target_duration_ms=target_dur,
                        duration_tolerance_ms=int(base_duration_tolerance_ms),
                    )
                )

        # Strategy 7: Title only + stricter duration window (Loose Title + Duration - Universal Baseline)
        if wire_search_title:
            stricter_tolerance = max(1000, int(base_duration_tolerance_ms * 0.5))
            strategies.append(
                SearchStrategyIntent(
                    id="title+strict-duration",
                    name="title+strict-duration",
                    strategy_type="loose_title_duration",
                    wire_query=wire_search_title,
                    required_capability=None,
                    target_duration_ms=target_dur,
                    duration_tolerance_ms=stricter_tolerance,
                )
            )

        # De-duplicate by (normalized query, required_capability, strategy_name) while preserving order
        unique: list[SearchStrategyIntent] = []
        seen_keys = set()
        for strategy in strategies:
            query_str = getattr(strategy, "wire_query", None) or (
                strategy.get("query") if isinstance(strategy, dict) else ""
            )
            req_cap = (
                getattr(strategy, "required_capability", None)
                if not isinstance(strategy, dict)
                else strategy.get("required_capability")
            )
            strat_name = getattr(strategy, "name", None) if not isinstance(strategy, dict) else strategy.get("name")
            key = ((query_str or "").strip().lower(), req_cap, strat_name)
            if key and key not in seen_keys:
                unique.append(strategy)
                seen_keys.add(key)

        return unique

    def _build_core_search_title(self, title: str | None) -> str:
        """Build core query title by stripping bracketed/version qualifiers while preserving
        native Unicode diacritics (e.g. 'Déjà Vu') and 104-key symbols ('!', '$') so
        Strategy 2 queries native characters and Strategy 2b queries diacritic-folded ASCII.
        """
        if not title:
            return ""

        from core.matching_engine.text_utils import _NORM_PROMO_EVENT_RE, _NORM_VERSION_DASH_RE, normalize_chars

        core_title = normalize_chars(str(title))
        # Strip anything in parentheses/brackets before constructing provider query.
        core_title = re.sub(r"\s*[\(\[][^(\)\]]*[\)\]]", "", core_title)
        # Strip trailing hyphenated version/remaster/promo qualifiers (e.g. " - 2011 Remaster")
        core_title = _NORM_PROMO_EVENT_RE.sub("", core_title)
        core_title = _NORM_VERSION_DASH_RE.sub("", core_title)
        core_title = re.sub(r"\s+", " ", core_title).strip()

        if not core_title:
            core_title = str(title).strip()

        return core_title.lower()

    def _deduplicate_candidates(self, candidates: list[EchosyncTrack]) -> list[EchosyncTrack]:
        """Deduplicate candidates collected from multiple fallback strategies.

        Only removes true duplicates (same peer, same file path, and same core
        technical metadata). This preserves meaningful variants of the same track
        that may differ by bitrate/size/sample-rate/bit-depth.
        """
        unique: list[EchosyncTrack] = []
        seen = set()

        for candidate in candidates:
            identifiers = getattr(candidate, "identifiers", None) or {}
            username = identifiers.get("username") if isinstance(identifiers, dict) else None
            plugin_item_id = identifiers.get("plugin_item_id") if isinstance(identifiers, dict) else None

            # Include quality-relevant fields from media[0] so we only collapse exact duplicate
            # observations of the same file result across fallback strategies.
            size = identifiers.get("size") if isinstance(identifiers, dict) else None
            bitrate = identifiers.get("bitrate") if isinstance(identifiers, dict) else None
            duration = getattr(candidate, "duration", None)

            first_media = candidate.media[0] if getattr(candidate, "media", None) else None
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

    def _get_quality_profile(self, profile_id: str | None = None) -> dict[str, Any] | None:
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

    def _get_fallback_quality_profile(self, primary_profile: dict[str, Any] | None) -> dict[str, Any] | None:
        """Resolve optional 1-hop fallback ('Good Enough') quality profile if configured."""
        if not primary_profile or not isinstance(primary_profile, dict):
            return None
        fb_id = primary_profile.get("fallback_profile_id")
        if not fb_id or str(fb_id).strip() == "":
            return None
        fb_id_str = str(fb_id).strip()
        if fb_id_str == str(primary_profile.get("id") or ""):
            return None
        try:
            profiles = config_manager.get_quality_profiles() or []
            for p in profiles:
                if str(p.get("id")) == fb_id_str:
                    return p
        except Exception as e:
            logger.debug(f"Failed to resolve fallback quality profile '{fb_id_str}': {e}")
        return None

    def _get_matching_engine(self, quality_profile: dict[str, Any] | None = None) -> WeightedMatchingEngine:
        """
        Get or create the matching engine with settings from quality profile.
        Resolves via ServiceRegistry so optional language/plugin overrides apply automatically.
        """
        if quality_profile is None:
            quality_profile = self._get_quality_profile()
        if not quality_profile:
            return self._instantiate_matching_engine(PROFILE_DOWNLOAD_SEARCH)

        # Check for custom matching settings in quality profile
        has_custom_settings = False
        custom_weights = dict(vars(PROFILE_DOWNLOAD_SEARCH.get_weights()))

        # Read custom duration tolerance if specified
        if "advanced_filters" in quality_profile:
            filters = quality_profile["advanced_filters"]
            if "enforce_duration_match" in filters:
                custom_weights["enforce_duration_match"] = filters["enforce_duration_match"]
                has_custom_settings = True
            if "duration_tolerance_seconds" in filters:
                tolerance_s = filters["duration_tolerance_seconds"]
                custom_weights["duration_tolerance_ms"] = int(tolerance_s * 1000)
                has_custom_settings = True

        # Read prefer larger files if specified
        if "prefer_larger_files" in quality_profile:
            custom_weights["tie_breaker"] = quality_profile.get("tie_breaker", "MAX_QUALITY")
            has_custom_settings = True

        if has_custom_settings:
            # Create custom profile with updated weights
            from core.matching_engine.scoring_profile import (
                ConfigurableProfile,
                ScoringWeights,
            )

            custom_profile = ConfigurableProfile(
                name=str(quality_profile.get("name") or "download_custom"),
                weights=ScoringWeights(**custom_weights),
            )
            logger.info(
                f"Using custom matching profile: duration_tolerance={custom_weights.get('duration_tolerance_ms')}ms, tie_breaker={custom_weights.get('tie_breaker')}"
            )
            return self._instantiate_matching_engine(custom_profile)

        return self._instantiate_matching_engine(PROFILE_DOWNLOAD_SEARCH)

    def _extract_allowed_formats(self, quality_profile: dict[str, Any] | None) -> list[str]:
        """Extract allowed file formats from quality profile."""
        if not quality_profile:
            # Default fallback if no profile configured
            return ["mp3", "flac", "ogg", "wav", "m4a", "aac"]

        formats = quality_profile.get("formats", [])
        allowed = []

        for fmt in formats:
            format_type = fmt.get("type", "").lower()
            if format_type:
                allowed.append(format_type)

        if not allowed:
            # Fallback if profile exists but has no formats
            logger.warning("Quality profile has no formats defined, using defaults")
            return ["flac", "wav", "dsd"]  # Conservative default

        return allowed

    def _get_min_bitrate(self, quality_profile: dict[str, Any] | None) -> int:
        """Get minimum bitrate from quality profile."""
        if not quality_profile:
            return 128

        # Find the minimum bitrate across all format rules
        formats = quality_profile.get("formats", [])
        min_bitrate = 9999

        for fmt in formats:
            fmt_min = fmt.get("min_bitrate", 0)
            if fmt_min > 0 and fmt_min < min_bitrate:
                min_bitrate = fmt_min

        return min_bitrate if min_bitrate < 9999 else 128

    def _get_priority_tiers(self, quality_profile: dict[str, Any] | None) -> list[tuple[int, list[str]]]:
        """
        Extract priority tiers from quality profile while preserving exact rule ordering.
        Returns list of (priority_number, [format_list]) sorted by priority.
        """
        if not quality_profile or not isinstance(quality_profile, dict):
            return []
        formats = quality_profile.get("formats", [])
        if not formats:
            return []

        # Group formats by priority (defaulting to index when priority omitted so rule order is preserved)
        priority_map: dict[int, list[str]] = {}
        for idx, fmt in enumerate(formats):
            if not isinstance(fmt, dict):
                continue
            priority = fmt.get("priority")
            priority_num = int(priority) if priority is not None else idx
            format_type = (fmt.get("type") or fmt.get("format") or "").lower()
            if not format_type:
                continue

            if priority_num not in priority_map:
                priority_map[priority_num] = []
            if format_type not in priority_map[priority_num]:
                priority_map[priority_num].append(format_type)

        # Sort by priority (lower number = higher priority)
        sorted_tiers = sorted(priority_map.items(), key=lambda x: x[0])
        return sorted_tiers

    def _filter_by_formats(
        self,
        candidates: list[EchosyncTrack],
        formats: list[str],
        quality_profile: dict[str, Any] | None = None,
        priority: int | None = None,
    ) -> list[EchosyncTrack]:
        """Filter candidates by format and apply quality profile constraints."""
        if quality_profile is None:
            quality_profile = self._get_quality_profile()
        if not quality_profile:
            # Fallback: just filter by format
            filtered = []
            for track in candidates:
                if not getattr(track, "media", None):
                    continue
                media = track.media[0]
                if media.file_format and media.file_format.lower() in formats:
                    filtered.append(track)
            return filtered

        # Get format configs for the requested formats (optionally filtered by priority)
        profile_formats = quality_profile.get("formats", [])
        if priority is not None:
            matching_configs = [
                fmt
                for fmt in profile_formats
                if fmt.get("priority") == priority and fmt.get("type", "").lower() in formats
            ]
        else:
            matching_configs = [fmt for fmt in profile_formats if fmt.get("type", "").lower() in formats]

        filtered = []
        for track in candidates:
            if not getattr(track, "media", None):
                continue
            media = track.media[0]
            if not media.file_format:
                continue

            format_type = media.file_format.lower()
            if format_type not in formats:
                continue

            if not matching_configs:
                filtered.append(track)
                continue

            # Candidate must satisfy at least one matching tier config
            passed_tier = False
            for fmt_config in matching_configs:
                if fmt_config.get("type", "").lower() != format_type:
                    continue

                # Apply size constraints
                min_size_mb = fmt_config.get("min_size_mb", 0)
                max_size_mb = fmt_config.get("max_size_mb", 0)

                if media.file_size_bytes:
                    size_mb = media.file_size_bytes / (1024 * 1024)
                    if min_size_mb > 0 and size_mb < min_size_mb:
                        continue
                    if max_size_mb > 0 and size_mb > max_size_mb:
                        continue

                # For lossless formats (FLAC, WAV, DSD), check bit depth and sample rate
                if format_type in ["flac", "wav", "dsd"]:
                    bit_depths = fmt_config.get("bit_depths", [])
                    sample_rates = fmt_config.get("sample_rates", [])

                    # Only enforce bit depth if profile has it configured and media has it
                    if bit_depths and media.bit_depth is not None:
                        allowed_bd = [str(b).strip() for b in bit_depths]
                        if str(media.bit_depth) not in allowed_bd:
                            continue

                    # Only enforce sample rate if profile has it configured and media has it
                    if sample_rates and media.sample_rate is not None:
                        sr_val = media.sample_rate
                        sr_khz = f"{sr_val / 1000:.1f}".rstrip("0").rstrip(".")
                        sr_hz = str(int(sr_val))
                        allowed_sr = [str(s).strip().lower() for s in sample_rates]
                        if sr_khz not in allowed_sr and sr_hz not in allowed_sr and str(sr_val) not in allowed_sr:
                            continue

                # For lossy formats (MP3, AAC, OGG, etc.), check bitrate
                elif format_type in ["mp3", "aac", "ogg", "m4a", "opus", "vorbis"]:
                    min_bitrate_kbps = fmt_config.get("min_bitrate", 0)
                    max_bitrate_kbps = fmt_config.get("max_bitrate", 999999)

                    # Extract bitrate from media or identifiers
                    bitrate_kbps = media.bitrate or 0
                    if not bitrate_kbps and track.identifiers and "bitrate" in track.identifiers:
                        bitrate_kbps = track.identifiers.get("bitrate", 0) or 0

                    # Convert to kbps if in bps
                    if bitrate_kbps > 10000:
                        bitrate_kbps = bitrate_kbps // 1000

                    if min_bitrate_kbps > 0 and bitrate_kbps > 0 and bitrate_kbps < min_bitrate_kbps:
                        continue

                    if max_bitrate_kbps > 0 and bitrate_kbps > 0 and bitrate_kbps > max_bitrate_kbps:
                        continue

                passed_tier = True
                break

            if passed_tier:
                filtered.append(track)

        # Sort by size (prefer larger files for better quality)
        filtered.sort(
            key=lambda t: (
                t.media[0].file_size_bytes
                if (getattr(t, "media", None) and t.media and t.media[0].file_size_bytes)
                else 0
            ),
            reverse=True,
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

    def _update_status(
        self,
        download_id: int,
        status: Any,
        provider_id: str | None = None,
        speed: float = 0.0,
        progress: float = 0.0,
    ):
        """Helper to update DB status, speed, and progress"""
        status_val = (
            status.value
            if isinstance(status, DownloadStatus)
            else (str(status).upper() if status else DownloadStatus.QUEUED.value)
        )
        with self.work_db.session_scope() as session:
            download = session.query(DownloadQueue).get(download_id)
            if download:
                download.status = status_val

                # Store progress/speed in the JSON blob instead of invented columns
                track_json = dict(download.echo_sync_track or {})
                track_json["current_speed"] = speed
                track_json["progress_percent"] = progress
                download.echo_sync_track = track_json

                download.updated_at = utc_now()
                if provider_id:
                    # Keep download.plugin_id as the provider identifier; store transfer IDs
                    # ("username|filename") in active_candidate_id instead of clobbering plugin_id.
                    if "|" in str(provider_id):
                        download.active_candidate_id = str(provider_id)
                    else:
                        download.plugin_id = str(provider_id)
                        if not download.active_candidate_id:
                            download.active_candidate_id = str(provider_id)

    def transition_to_searching(self, download_id: int) -> bool:
        """Transition item to SEARCHING state."""
        return self.repo.transition_to_searching(download_id)

    def transition_to_downloading(
        self,
        download_id: int,
        active_candidate_id: str,
        candidate_stack: list[dict[str, Any]] | None = None,
        plugin_id: str | None = None,
    ) -> bool:
        """Transition item to DOWNLOADING state."""
        return self.repo.transition_to_downloading(
            download_id,
            active_candidate_id=active_candidate_id,
            candidate_stack=candidate_stack,
            plugin_id=plugin_id,
        )

    def transition_to_verifying(self, download_id: int, file_path: str | None = None) -> bool:
        """Transition item from DOWNLOADING to VERIFYING state, locking file from cleanup sweepers."""
        with self.work_db.session_scope() as session:
            item = session.get(DownloadQueue, download_id)
            if not item:
                return False
            item.status = DownloadStatus.VERIFYING.value
            if file_path and item.echo_sync_track is not None:
                track_dict = dict(item.echo_sync_track)
                track_dict["downloaded_file_path"] = file_path
                item.echo_sync_track = track_dict
            item.updated_at = utc_now()
            with db_write_lease(task_name="transition_to_verifying"):
                session.commit()
            logger.info(f"DownloadQueue {download_id} transitioned to VERIFYING (file: {file_path})")
            return True

    def handle_verification_success(self, download_id: int, file_path: str | None = None) -> bool:
        """Transition item from VERIFYING to COMPLETED and emit DOWNLOAD_COMPLETED."""
        self._remaster_fallback_ids.discard(download_id)
        self._transfer_progress_tracker.pop(download_id, None)
        with self.work_db.session_scope() as session:
            item = session.get(DownloadQueue, download_id)
            if not item:
                return False
            item.status = DownloadStatus.COMPLETED.value
            item.updated_at = utc_now()
            with db_write_lease(task_name="handle_verification_success"):
                session.commit()

        # Emit DOWNLOAD_COMPLETED event
        from core.event_bus import event_bus

        event_bus.publish(
            {
                "event": "DOWNLOAD_COMPLETED",
                "channel": "downloads",
                "download_id": download_id,
                "file_path": file_path,
                "data": {
                    "download_id": download_id,
                    "file_path": file_path,
                },
            }
        )
        try:
            from core.hook_manager import hook_manager

            hook_manager.apply_filters(
                "ON_DOWNLOAD_COMPLETED",
                None,
                download_id=download_id,
                file_path=file_path,
            )
        except Exception as e:
            logger.error(f"Error in ON_DOWNLOAD_COMPLETED hook: {e}")

        logger.info(f"DownloadQueue {download_id} verification succeeded -> COMPLETED")
        return True

    def handle_verification_failure(
        self,
        download_id: int,
        reason: str = "MISMATCH_EDITION",
        file_path: str | None = None,
        *,
        delete_file: bool = False,
    ) -> bool:
        """On verification failure, delete or quarantine rejected file, blacklist candidate, and rotate."""
        self._transfer_progress_tracker.pop(download_id, None)
        if file_path:
            if delete_file:
                self._delete_rejected_file(file_path, reason)
            else:
                self._quarantine_file(file_path, reason)

        rotated = False
        has_next_backup = False
        with self.work_db.session_scope() as session:
            item = session.get(DownloadQueue, download_id)
            if item:
                rotated = item.rotate_candidate(reason=reason)
                has_next_backup = bool(item.active_candidate_id)
                item.updated_at = utc_now()
                with db_write_lease(task_name="handle_verification_failure"):
                    session.commit()

        def _schedule_retry_coro(coro_factory):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro_factory())
                return
            except RuntimeError:
                pass
            if getattr(self, "_loop", None) and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(coro_factory(), self._loop)
                return
            # Non-async worker/watchdog thread: dispatch asynchronously via JobQueue when running
            if getattr(job_queue, "_running", False):
                self.process_single_download(download_id)

        if rotated and has_next_backup:
            logger.info(
                f"DownloadQueue {download_id} rotated candidate ({reason}) -> RETRYING. Dispatching next backup candidate."
            )
            _schedule_retry_coro(lambda: self._dispatch_candidate(download_id))
            return True
        elif self._can_resume_next_strategy(download_id):
            logger.info(
                f"DownloadQueue {download_id} exhausted Top-3 backups ({reason}); resuming next search strategy within 10m window."
            )
            self._update_status(download_id, DownloadStatus.RETRYING.value)
            providers = self._get_active_download_providers()
            if providers:
                _schedule_retry_coro(lambda: self._execute_waterfall_search_and_download(download_id, providers))
            return True
        else:
            self._remaster_fallback_ids.discard(download_id)
            logger.warning(f"DownloadQueue {download_id} exhausted candidates -> FAILED ({reason})")
            return False

    def _delete_rejected_file(self, file_path: str, reason: str = "FAKE_LOSSLESS") -> bool:
        """Delete a confirmed-fake/corrupt/mismatched download file via Gatekeeper."""
        from pathlib import Path

        from core.io_gatekeeper import Gatekeeper

        try:
            src = Path(file_path)
            if not src.exists():
                return False
            Gatekeeper.authorize_and_execute({"operation": "delete", "src": str(src)})
            logger.info(f"Deleted rejected download {src.name} via Gatekeeper ({reason})")
            return True
        except Exception as e:
            logger.error(f"Failed to delete rejected file {file_path} via Gatekeeper: {e}")
            return False

    def _quarantine_file(self, file_path: str, reason: str = "MISMATCH_EDITION") -> str | None:
        """Move rejected file to data/quarantine via Gatekeeper using Windows-safe filenames."""
        from pathlib import Path

        from core.io_gatekeeper import Gatekeeper

        try:
            src = Path(file_path)
            if not src.exists():
                return None
            quarantine_dir = Path("data/quarantine")
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            safe_reason = re.sub(r'[<>:"/\\|?*\s]+', "_", str(reason or "REJECTED")).strip("_")[:60] or "REJECTED"
            dest = quarantine_dir / f"{src.stem}_{safe_reason}{src.suffix}"
            Gatekeeper.authorize_and_execute(
                {
                    "operation": "safe_move",
                    "src": str(src),
                    "dst": str(dest),
                }
            )
            logger.info(f"Moved invalid file {src} to quarantine via Gatekeeper: {dest}")
            return str(dest)
        except Exception as e:
            logger.error(f"Failed to quarantine file {file_path}: {e}")
            return None

    async def _dispatch_candidate(self, download_id: int, providers: list[Any] | None = None):
        """Immediately dispatch the popped active backup candidate on a RETRYING download without re-searching."""
        if not providers:
            providers = self._get_active_download_providers()
        if not providers:
            return

        active_id = None
        target_plugin_id = None
        active_file_size = 0
        with self.work_db.session_scope() as session:
            item = session.get(DownloadQueue, download_id)
            if not item:
                return
            active_id = item.active_candidate_id
            target_plugin_id = item.plugin_id
            if isinstance(item.echo_sync_track, dict):
                meta = item.echo_sync_track.get("_active_candidate_meta") or {}
                if isinstance(meta, dict):
                    active_file_size = int(meta.get("size") or 0)
                    if not target_plugin_id and meta.get("plugin_id"):
                        target_plugin_id = str(meta["plugin_id"])

        if active_id and "|" in active_id:
            username, filename = active_id.split("|", 1)
            provider = next(
                (
                    p
                    for p in providers
                    if str(getattr(p, "plugin_id", "")) == str(target_plugin_id)
                    or getattr(p, "name", "") == str(target_plugin_id)
                ),
                providers[0],
            )
            try:
                logger.info(
                    f"Direct backup dispatch for download {download_id}: user='{username}', file='{filename}' "
                    f"(size={active_file_size}) via {provider.name}"
                )
                if hasattr(provider, "_async_download"):
                    provider_id = await provider._async_download(
                        username=username, filename=filename, file_size=active_file_size
                    )
                elif hasattr(provider, "download"):
                    loop = asyncio.get_running_loop()
                    try:
                        provider_id = await loop.run_in_executor(
                            None, lambda: provider.download(username, filename, active_file_size)
                        )
                    except TypeError:
                        provider_id = await loop.run_in_executor(
                            None, lambda: provider.download(username, filename)
                        )
                else:
                    provider_id = None

                if provider_id:
                    self._update_status(download_id, DownloadStatus.DOWNLOADING.value, str(provider_id))
                    return
                logger.warning(f"Direct backup dispatch failed for download {download_id}; rotating next candidate.")
            except Exception as exc:
                logger.warning(f"Direct backup dispatch error for download {download_id}: {exc}")

            # Direct dispatch failed — rotate to next backup or resume search
            await self._handle_active_download_failure(
                download_id,
                active_id,
                providers,
                [provider],
                reason="BACKUP_DISPATCH_FAILED",
            )
            return

        await self._execute_waterfall_search_and_download(download_id, providers)

    def _is_signature_match(
        self,
        sig1: tuple[str, str, str, int | None],
        sig2: tuple[str, str, str, int | None],
    ) -> bool:
        """Check if two track signatures match with duration tolerance."""
        artist1, title1, album1, dur1 = sig1
        artist2, title2, album2, dur2 = sig2

        if not artist1 or not artist2 or not title1 or not title2:
            return False

        if artist1.lower() != artist2.lower() or title1.lower() != title2.lower():
            return False

        if dur1 is not None and dur2 is not None:
            if abs(dur1 - dur2) > 5000:
                return False

        return True

    def _find_existing_download(
        self, track_json: dict[str, Any], include_failed: bool = False
    ) -> tuple[int, str] | None:
        """Return an existing active or failed download (id, status) matching the normalized track signature."""
        signature = self._normalize_track_signature(track_json)
        if not signature[0] or not signature[1]:
            return None

        active_states = {
            DownloadStatus.QUEUED.value,
            DownloadStatus.SEARCHING.value,
            DownloadStatus.DOWNLOADING.value,
            DownloadStatus.VERIFYING.value,
            DownloadStatus.RETRYING.value,
        }
        with self.work_db.session_scope() as session:
            query = session.query(DownloadQueue)
            if not include_failed:
                query = query.filter(DownloadQueue.status.in_(active_states))

            # Query newest first so we match the most recent record
            items = query.order_by(DownloadQueue.id.desc()).all()
            for item in items:
                other_sig = self._normalize_track_signature(item.echo_sync_track or {})
                if self._is_signature_match(signature, other_sig):
                    return item.id, item.status
        return None

    def _normalize_track_signature(self, track_json: dict[str, Any]) -> tuple[str, str, str, int | None]:
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

    def get_status(self, download_id: int) -> dict | None:
        """Get status for UI"""
        with self.work_db.session_scope() as session:
            download = session.query(DownloadQueue).get(download_id)
            if download:
                return {
                    "id": download.id,
                    "status": download.status,
                    "track": download.echo_sync_track,
                    "provider_id": download.provider_id,
                    "updated_at": download.updated_at.isoformat(),
                }
        return None

    def _track_exists_in_library(
        self,
        artist_name: str,
        title: str,
        album: str | None = None,
        duration: int | None = None,
    ) -> bool:
        """
        Check if a track already exists in the library (database).
        """
        if not artist_name or not title:
            return False

        try:
            with self.db.session_scope() as session:
                # Base filters: artist + title
                filters = [
                    Artist.name.ilike(artist_name.strip()),
                    Track.title.ilike(title.strip()),
                ]

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

                exists = session.query(session.query(Track).join(Artist).filter(*filters).exists()).scalar()
                return bool(exists)
        except Exception as e:
            logger.error(f"Error checking library for {artist_name} - {title}: {e}")
            return False

    def _deduplicate_queue(self):
        """
        Deduplicate existing rows in DownloadQueue.

        Scans all records, keeps the most recent record per track signature,
        and deletes redundant duplicate rows.
        """
        try:
            with self.work_db.session_scope() as session:
                items = session.query(DownloadQueue).order_by(DownloadQueue.id.desc()).all()
                seen_signatures = {}
                to_delete = []

                for item in items:
                    sig = self._normalize_track_signature(item.echo_sync_track or {})
                    if not sig[0] or not sig[1]:
                        continue

                    matched_key = None
                    for existing_sig, _existing_item_id in seen_signatures.items():
                        if self._is_signature_match(sig, existing_sig):
                            matched_key = existing_sig
                            break

                    if matched_key:
                        # Found duplicate item with same signature — delete older duplicate
                        to_delete.append(item.id)
                    else:
                        seen_signatures[sig] = item.id

                if to_delete:
                    session.query(DownloadQueue).filter(DownloadQueue.id.in_(to_delete)).delete(
                        synchronize_session=False
                    )
                    logger.info(f"Queue deduplication removed {len(to_delete)} duplicate records from download queue.")
        except Exception as e:
            logger.warning(f"Error during queue deduplication: {e}")

    def _purge_existing_tracks_from_queue(self):
        """
        Startup Check: Remove items from the download queue that are already in the library.
        Prevents re-downloading tracks that were imported while the queue was active/stalled.
        """
        try:
            with self.work_db.session_scope() as session:
                last_id = 0
                batch_size = 25
                removed_count = 0
                while True:
                    queued_items = (
                        session.query(DownloadQueue)
                        .filter(
                            DownloadQueue.status.in_(
                                [
                                    DownloadStatus.QUEUED.value,
                                    DownloadStatus.SEARCHING.value,
                                    DownloadStatus.RETRYING.value,
                                    DownloadStatus.FAILED.value,
                                    "queued",
                                    "searching",
                                    "retrying",
                                    "failed",
                                    "failed_no_match",
                                ]
                            ),
                            DownloadQueue.id > last_id,
                        )
                        .order_by(DownloadQueue.id.asc())
                        .limit(batch_size)
                        .all()
                    )
                    if not queued_items:
                        break
                    last_id = queued_items[-1].id

                    for item in queued_items:
                        try:
                            track_data = item.echo_sync_track
                            if not track_data:
                                continue

                            artist = track_data.get("artist_name") or track_data.get("artist")
                            title = track_data.get("title")
                            album = track_data.get("album_title") or track_data.get("album")
                            duration = track_data.get("duration") or track_data.get("duration_ms")

                            if not artist or not title:
                                continue

                            filters = [
                                Artist.name.ilike(artist.strip()),
                                Track.title.ilike(title.strip()),
                            ]
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
                                logger.info(
                                    f"Removing redundant download {item.id}: '{title}' by '{artist}' is already in library"
                                )
                                session.delete(item)
                                removed_count += 1
                        except Exception as e:
                            logger.warning(f"Error checking queued item {item.id}: {e}")

                if removed_count > 0:
                    logger.info(f"Startup purge removed {removed_count} redundant items from download queue")

        except Exception as e:
            logger.error(f"Error purging existing tracks from queue: {e}")

    def _reclaim_orphaned_searching_items(self) -> int:
        """Reset rows stuck in SEARCHING with no live in-process search coroutine back to QUEUED.

        Unlike _recover_stuck_items(), this NEVER touches active DOWNLOADING or VERIFYING rows,
        so it is safe to invoke on every live manual or scheduled processing cycle.
        """
        active_ids = set(getattr(self, "_active_search_ids", set()) or set())
        reclaimed = 0
        now = utc_now()
        try:
            with self.work_db.session_scope() as session:
                stuck_rows = (
                    session.query(DownloadQueue)
                    .filter(DownloadQueue.status.in_([DownloadStatus.SEARCHING.value, "searching"]))
                    .all()
                )
                for row in stuck_rows:
                    if row.id in active_ids:
                        continue
                    row.status = DownloadStatus.QUEUED.value
                    row.provider_id = None
                    row.updated_at = now
                    reclaimed += 1
            if reclaimed > 0:
                logger.info(f"Reclaimed {reclaimed} orphaned SEARCHING download(s) back to QUEUED.")
        except Exception as e:
            logger.warning(f"Failed to reclaim orphaned SEARCHING items: {e}")
        return reclaimed

    def process_downloads_now(self):
        """Run one processing cycle. Safe to call from any sync or async context.

        When the background worker loop is actively running (self._loop_task),
        scheduled job triggers delegate to it to prevent concurrent queue consumption races.
        """
        # If the background processing loop is already running, delegate directly to the existing worker loop
        if self._loop_task and not self._loop_task.done() and self._loop and self._loop.is_running():
            logger.info(
                "DownloadManager: background processing loop is active; delegating queue consumption to existing worker loop."
            )
            return

        async def _cycle():
            requeued = self._requeue_retryable_failed_items(limit=50)
            if requeued > 0:
                logger.info(f"Manual run: re-queued {requeued} retryable failed items")
            # Do NOT call _recover_stuck_items() during live manual cycles — it resets active
            # in-flight DOWNLOADING transfers back to queued. Startup recovery runs in _process_loop.
            self._deduplicate_queue()
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
        """Run acquisition strictly for a single download ID via JobQueue (TaskCategory.GENERAL).

        Deduplicated by download item ID to prevent redundant acquisition jobs.
        """
        job_name = f"download:{download_id}"

        def _run_job(**kwargs):
            async def _run_single():
                providers = self._get_active_download_providers()
                if not providers:
                    logger.warning("No active download providers available for single-item retry.")
                    return
                await self._execute_waterfall_search_and_download(download_id, providers)

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(_run_single(), loop)
                    return future.result()
                else:
                    return loop.run_until_complete(_run_single())
            except RuntimeError:
                return asyncio.run(_run_single())

        job_queue.register_job(
            name=job_name,
            func=_run_job,
            enabled=True,
            category=TaskCategory.GENERAL,
            priority=TaskPriority.HIGH,
            tags=["echosync", "downloads", f"download:{download_id}"],
            max_retries=1,
        )
        res = job_queue.trigger_job_by_name(job_name)
        if not job_queue._running:
            _run_job()
            return True
        return res

    def _requeue_retryable_failed_items(self, limit: int = 50) -> int:
        """Move retryable failed items back to queued so manual runs can re-attempt them.

        Prioritizes NEWEST tracks first (DESC by created_at) so most recent failures are retried first.
        Caps automatic re-queuing at retry_count < 5. Tracks with >= 5 retries require manual user intervention.
        Enforces exponential backoff: delay >= (2 ** retry_count) * 60s.
        """
        retryable_statuses = {
            DownloadStatus.FAILED.value,
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
                    (DownloadQueue.retry_count < 5) | (DownloadQueue.retry_count.is_(None)),
                )
                .order_by(DownloadQueue.created_at.desc())  # Newest first
                .limit(limit)
                .all()
            )

            for item in items:
                retry_c = item.retry_count or 0
                required_delay = (2**retry_c) * 60
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


    def poll_active_downloads_if_needed(self) -> None:
        """Lightweight active-transfer poll for JobQueue when background _process_loop is inactive."""
        if self._loop_task and not self._loop_task.done():
            return
        try:
            with self.work_db.session_scope() as session:
                has_active = (
                    session.query(DownloadQueue.id)
                    .filter(DownloadQueue.status == DownloadStatus.DOWNLOADING.value)
                    .first()
                    is not None
                )
            if not has_active:
                return
            asyncio.run(self._check_active_downloads())
        except Exception as e:
            logger.debug(f"Active download poll cycle failed: {e}")


# Global Accessor
def get_download_manager():
    return DownloadManager.get_instance()


def register_download_manager_job(interval_seconds: int = 21600):
    """
    Register download manager processing + lightweight 30s active-transfer polling
    with the global job_queue.
    """
    from core.task_manager.task_queue import job_queue, unregister_job

    def process_downloads(force_run: bool = False, **kwargs):
        """Run one full download processing cycle driven by the job queue."""
        dm = get_download_manager()
        dm.process_downloads_now()

    def poll_active_downloads(**kwargs):
        """Poll active DOWNLOADING transfers every 30s even when auto_start is False."""
        dm = get_download_manager()
        dm.poll_active_downloads_if_needed()

    unregister_job("download_manager_status")

    job_queue.register_job(
        name="download_manager",
        func=process_downloads,
        interval_seconds=interval_seconds,
        start_after=interval_seconds,
        enabled=True,
        category=TaskCategory.GENERAL,
        tags=["echosync", "downloads"],
        max_retries=3,
    )
    job_queue.register_job(
        name="download_status_poller",
        func=poll_active_downloads,
        interval_seconds=30,
        start_after=30,
        enabled=True,
        category=TaskCategory.GENERAL,
        tags=["echosync", "downloads"],
        max_retries=1,
    )

    logger.info(
        f"DownloadQueue manager job registered (name: download_manager, interval: {interval_seconds}s, first run after startup: {interval_seconds}s)"
    )
