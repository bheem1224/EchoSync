"""ISRC metadata lookup service.

Dispatches ISRC lookups through the ProviderRegistry rather than hardcoding
provider-specific HTTP calls.  Any provider that sets ``supports_isrc_lookup =
True`` and implements ``search_by_isrc(isrc)`` participates automatically —
no changes to this module are required when new providers are added.

Waterfall order is determined by the provider's declared ``MetadataRichness``
so that the highest-quality source is tried first.

Security note: ``isrc_code`` is validated against the strict ISRC regex before
being used in any lookup, preventing injection into query strings.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from core.caching.provider_cache import provider_cache
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.tiered_logger import get_logger

logger = get_logger("isrc_lookup")

# ─── ISRC validation ─────────────────────────────────────────────────────────
# ISRC format: CC-XXX-YY-NNNNN (hyphens optional)
# CC  = 2 uppercase letters (country)
# XXX = 3 uppercase alphanumeric (registrant)
# YY  = 2 digits (year)
# NNNNN = 5 digits (designation)
_ISRC_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}[0-9]{7}$")


def _normalise_isrc(raw: str) -> Optional[str]:
    """Return the canonical 12-character ISRC (no hyphens) or None if invalid."""
    code = raw.strip().upper().replace("-", "")
    if _ISRC_RE.match(code):
        return code
    return None


# ─── Result normalisation ────────────────────────────────────────────────────

def _track_to_dict(track: SoulSyncTrack, source: str) -> Dict[str, Any]:
    """Convert a SoulSyncTrack to a serialisable result dict."""
    return {
        "source": source,
        "isrc": track.isrc,
        "title": track.raw_title,
        "artist": track.artist_name,
        "album": track.album_title,
        "musicbrainz_recording_id": track.musicbrainz_id,
        "duration_ms": track.duration,
        "release_year": track.release_year,
    }


# ─── Provider-agnostic ISRC dispatcher ───────────────────────────────────────

def _dispatch_isrc_via_providers(
    isrc: str,
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Iterate registered providers that support ISRC lookup, return first hit.

    Providers are sorted by their declared MetadataRichness (highest first) so
    the best-quality source wins.  The ``tried`` list records every provider
    that was attempted regardless of outcome.
    """
    from core.provider import ProviderRegistry
    from core.enums import Capability

    tried: List[str] = []

    candidates = ProviderRegistry.get_providers_with_capability(Capability.FETCH_METADATA)
    isrc_providers = [p for p in candidates if getattr(p, "supports_isrc_lookup", False)]

    # Sort descending by metadata richness so the richest source goes first.
    # MetadataRichness values are comparable integers (HIGH > MEDIUM > LOW).
    def _richness(provider: Any) -> int:
        caps = getattr(provider, "capabilities", None)
        if caps is None:
            return 0
        meta = getattr(caps, "metadata", None)
        try:
            return int(meta) if meta is not None else 0
        except (TypeError, ValueError):
            return 0

    isrc_providers.sort(key=_richness, reverse=True)

    for provider in isrc_providers:
        provider_name = getattr(provider, "name", repr(provider))
        tried.append(provider_name)
        try:
            track = provider.search_by_isrc(isrc)
        except Exception as exc:
            logger.warning("ISRC provider %s raised: %s", provider_name, exc)
            track = None
        if track is not None:
            if not isinstance(track, SoulSyncTrack):
                logger.warning(
                    "ISRC provider %s returned unexpected type %s (expected SoulSyncTrack) "
                    "— skipping to next provider.",
                    provider_name,
                    type(track).__name__,
                )
                continue
            return _track_to_dict(track, provider_name), tried

    return None, tried


# ─── Public entrypoint ────────────────────────────────────────────────────────

@provider_cache(ttl_seconds=2592000)
def fetch_metadata_by_isrc(isrc_code: str) -> Dict[str, Any]:
    """
    Resolve track metadata for *isrc_code* via the provider-agnostic waterfall.

    Returns a dict with a ``result`` key containing the first successful hit,
    or ``None`` if all providers fail.  The ``tried`` key lists every provider
    that was attempted.

    Raises ``ValueError`` for a malformed ISRC so callers can return HTTP 400.
    """
    canonical = _normalise_isrc(isrc_code)
    if canonical is None:
        raise ValueError(
            f"Invalid ISRC format: {isrc_code!r}. "
            "Expected CC-XXX-YY-NNNNN (12 alphanumeric chars, hyphens optional)."
        )

    result, tried = _dispatch_isrc_via_providers(canonical)

    if result:
        logger.info("ISRC %s resolved via %s", canonical, result.get("source"))
    else:
        logger.info("ISRC %s: no result from any provider (%s)", canonical, tried)

    return {"isrc": canonical, "result": result, "tried": tried}
