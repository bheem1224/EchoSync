"""Retroactive metadata enhancement worker service.

Executes a two-phase workflow:
  Phase 1: Native Rust audio fingerprinting pre-pass (Chromaprint / AcoustID backfill).
  Phase 2: Authoritative metadata enhancement with signature-aware candidate selection
           and content-addressed acoustic proof (ECHOSYNC_SIGNATURE) generation.
"""

from __future__ import annotations

from collections.abc import Callable

from core.tiered_logger import get_logger
from services.metadata_enhancer import RetroactiveEnhancer

logger = get_logger("retroactive_metadata_worker")


def run_retroactive_metadata_worker(
    batch_size: int = 50,
    check_all_files: bool = False,
    limit: int | None = None,
    force_refresh: bool = False,
    require_signature: bool = True,
    target_plugin: str | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> None:
    """Execute scheduled or manual retroactive metadata enhancement across library tracks.

    Args:
        batch_size: Number of tracks processed per database commit chunk.
        check_all_files: If True, evaluates all tracks rather than only tracks requiring identification.
        limit: Optional maximum number of tracks to enhance before halting.
        force_refresh: If True, re-evaluates even tracks already stamped as enhanced.
        require_signature: If True, considers tracks missing v2.5 echosync_signature as needing enhancement.
        target_plugin: If provided, runs a lightweight plugin-only enrichment pass without DSP audio decoding.
        progress_callback: Optional callback(current, total, status) reporting progress.
    """
    logger.info(
        "Starting retroactive metadata enhancement worker (batch_size=%d, check_all_files=%s, "
        "limit=%s, force_refresh=%s, require_signature=%s, target_plugin=%s)",
        batch_size,
        check_all_files,
        limit,
        force_refresh,
        require_signature,
        target_plugin,
    )

    try:
        from core.event_bus import event_bus

        def _default_progress(current: int, total: int, status: str = "") -> None:
            try:
                event_bus.publish(
                    "job_progress",
                    {
                        "job_name": "retroactive_metadata_enhancement",
                        "phase": "fingerprinting",
                        "current": current,
                        "total": total,
                        "status": status,
                        "percentage": (round((current / total) * 100, 1) if total > 0 else 0),
                    },
                )
            except Exception:
                pass

        cb = progress_callback or _default_progress

        enhancer = RetroactiveEnhancer()

        if target_plugin:
            logger.info("Executing targeted plugin enrichment pass for plugin: %s...", target_plugin)
            processed_count = enhancer.enrich_plugin_metadata(
                target_plugin=target_plugin,
                batch_size=batch_size,
                limit=limit,
                progress_callback=cb,
            )
            logger.info(
                "Targeted plugin enrichment complete: %d tracks processed for %s",
                processed_count,
                target_plugin,
            )
            return

        # Phase 1: Native Rust audio fingerprinting pre-pass
        logger.info("Executing Phase 1: Native Rust fingerprinting pre-pass...")
        enhancer.backfill_missing_fingerprints(
            batch_size=min(batch_size, 50),
            progress_callback=cb,
        )

        # Phase 2: Metadata enhancement with signature verification and local cache resolution
        logger.info("Executing Phase 2: Metadata enhancement...")
        enhancer.enhance_library_metadata(
            batch_size=batch_size,
            check_all_files=check_all_files,
            limit=limit,
            force_refresh=force_refresh,
            require_signature=require_signature,
        )

        logger.info("Retroactive metadata enhancement worker complete")
    except Exception:
        logger.exception("Retroactive metadata enhancement worker failed")
        raise
