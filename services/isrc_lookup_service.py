"""ISRC metadata lookup service.

Dispatches ISRC lookups through the PluginRegistry rather than hardcoding
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
from typing import Any

from core.caching.plugin_cache import plugin_cache
from core.db.echo_sync_track import EchosyncTrack
from core.tiered_logger import get_logger

logger = get_logger("isrc_lookup")

# ─── ISRC validation ─────────────────────────────────────────────────────────
# ISRC format: CC-XXX-YY-NNNNN (hyphens optional)
# CC  = 2 uppercase letters (country)
# XXX = 3 uppercase alphanumeric (registrant)
# YY  = 2 digits (year)
# NNNNN = 5 digits (designation)
_ISRC_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}[0-9]{7}$")


def _normalise_isrc(raw: str) -> str | None:
    """Return the canonical 12-character ISRC (no hyphens) or None if invalid."""
    code = raw.strip().upper().replace("-", "")
    if _ISRC_RE.match(code):
        return code
    return None


# ─── Result normalisation ────────────────────────────────────────────────────


def _track_to_dict(track: Any, source: str) -> dict[str, Any]:
    """Convert an EchosyncTrack or dict to a serialisable result dict."""
    title = (
        getattr(track, "raw_title", None)
        or getattr(track, "title", None)
        or (track.get("raw_title") if isinstance(track, dict) else None)
        or (track.get("title") if isinstance(track, dict) else None)
    )
    artist = (
        getattr(track, "artist_name", None)
        or getattr(track, "artist", None)
        or (track.get("artist_name") if isinstance(track, dict) else None)
        or (track.get("artist") if isinstance(track, dict) else None)
    )
    album = (
        getattr(track, "album_title", None)
        or getattr(track, "album", None)
        or (track.get("album_title") if isinstance(track, dict) else None)
        or (track.get("album") if isinstance(track, dict) else None)
    )
    isrc_val = getattr(track, "isrc", None) or (
        track.get("isrc") if isinstance(track, dict) else None
    )
    mbid = getattr(track, "musicbrainz_id", None) or (
        track.get("musicbrainz_recording_id")
        or track.get("musicbrainz_id")
        or track.get("mbid")
        if isinstance(track, dict)
        else None
    )
    duration = getattr(track, "duration", None) or (
        track.get("duration_ms") or track.get("duration")
        if isinstance(track, dict)
        else None
    )
    year = getattr(track, "release_year", None) or (
        track.get("release_year") or track.get("year")
        if isinstance(track, dict)
        else None
    )

    return {
        "source": source,
        "isrc": isrc_val,
        "title": title,
        "raw_title": title,
        "artist": artist,
        "album": album,
        "musicbrainz_recording_id": mbid,
        "duration_ms": duration,
        "release_year": year,
    }


# ─── Provider-agnostic ISRC dispatcher ───────────────────────────────────────


def dispatch_isrc_lookup(isrc: str) -> EchosyncTrack | None:
    """Dispatch ISRC lookup across all capable providers (MusicBrainz -> Spotify -> etc.)
    returning an EchosyncTrack if found, or None.
    """
    canonical = _normalise_isrc(isrc)
    if not canonical:
        return None

    from core.enums import Capability
    from core.nexus_framework.plugin_loader import PluginRegistry

    candidates = PluginRegistry.get_plugins_with_capability(Capability.FETCH_METADATA)
    isrc_providers = [
        p for p in candidates if getattr(p, "supports_isrc_lookup", False)
    ]
    for p in PluginRegistry.get_plugins_with_capability(Capability.FETCH_BY_ISRC):
        if p not in isrc_providers:
            isrc_providers.append(p)

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
        try:
            track = provider.search_by_isrc(canonical)
        except Exception as exc:
            logger.warning("ISRC provider %s raised: %s", provider_name, exc)
            track = None

        if track is not None:
            if isinstance(track, EchosyncTrack):
                if not isinstance(track.identifiers, dict):
                    track.identifiers = {}
                if not track.identifiers.get("source"):
                    track.identifiers["source"] = provider_name
                return track
            elif isinstance(track, dict):
                track_obj = EchosyncTrack(
                    raw_title=track.get("title") or track.get("raw_title") or "",
                    artist_name=track.get("artist") or track.get("artist_name") or "",
                    album_title=track.get("album") or track.get("album_title") or "",
                    release_year=track.get("release_year") or track.get("year"),
                    duration=track.get("duration_ms") or track.get("duration"),
                    isrc=canonical,
                    musicbrainz_id=track.get("musicbrainz_recording_id")
                    or track.get("musicbrainz_id")
                    or track.get("mbid"),
                    identifiers={"source": provider_name},
                )
                return track_obj

    return None


def _dispatch_isrc_via_providers(
    isrc: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Iterate registered providers that support ISRC lookup, return first hit.

    Providers are sorted by their declared MetadataRichness (highest first) so
    the best-quality source wins.  The ``tried`` list records every provider
    that was attempted regardless of outcome.
    """
    from core.enums import Capability
    from core.nexus_framework.plugin_loader import PluginRegistry

    tried: list[str] = []

    candidates = PluginRegistry.get_plugins_with_capability(Capability.FETCH_METADATA)
    isrc_providers = [
        p for p in candidates if getattr(p, "supports_isrc_lookup", False)
    ]
    for p in PluginRegistry.get_plugins_with_capability(Capability.FETCH_BY_ISRC):
        if p not in isrc_providers:
            isrc_providers.append(p)

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
            if not isinstance(track, EchosyncTrack):
                if isinstance(track, dict):
                    track = EchosyncTrack(
                        raw_title=track.get("raw_title") or track.get("title") or "",
                        artist_name=track.get("artist")
                        or track.get("artist_name")
                        or "",
                        album_title=track.get("album")
                        or track.get("album_title")
                        or "",
                        release_year=track.get("release_year") or track.get("year"),
                        duration=track.get("duration_ms") or track.get("duration"),
                        isrc=isrc,
                        musicbrainz_id=track.get("musicbrainz_recording_id")
                        or track.get("musicbrainz_id")
                        or track.get("mbid"),
                        identifiers={"source": provider_name},
                    )
                else:
                    logger.warning(
                        "ISRC provider %s returned unexpected type %s (expected EchosyncTrack) "
                        "— skipping to next provider.",
                        provider_name,
                        type(track).__name__,
                    )
                    continue
            return _track_to_dict(track, provider_name), tried

    return None, tried


# ─── Public entrypoint ────────────────────────────────────────────────────────


@plugin_cache(ttl_seconds=2592000)
def fetch_metadata_by_isrc(isrc_code: str) -> dict[str, Any]:
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
