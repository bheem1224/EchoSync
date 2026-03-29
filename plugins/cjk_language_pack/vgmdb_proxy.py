"""
VGMdb Proxy
===========
Lightweight, offline-first utility that queries the VGMdb.info community
JSON API to resolve anime / drama series names associated with a given
artist + title pair.

Primary use-cases inside the CJK Language Pack
------------------------------------------------
1. **pre_provider_search** — enrich slskd query strings so tracks tagged with
   the series name instead of the artist name can still be found.
   e.g. "Oshi no Ko Idol" in addition to "YOASOBI Idol".

2. **pre_normalize_text** — remap a series name to its canonical artist name
   so the WeightedMatchingEngine accepts "Oshi no Ko" as a high-confidence
   match for "YOASOBI".

Network contract
----------------
All outbound calls go to the single hardcoded base URL ``https://vgmdb.info``.
User-supplied artist / title are always URL-encoded before being appended to
the query path so they can never redirect the request to another host.
A ``_TIMEOUT``-second cap and silent error handling ensure the pipeline never
blocks on a flaky or unreachable API.

Cache
-----
Results are scoped to the lifetime of the server process (module-level
:data:`_proxy` singleton).  A simple dict capped at :data:`_MAX_CACHE`
entries prevents unbounded memory growth; the oldest entry is evicted when
the cap is reached.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from core.tiered_logger import get_logger

logger = get_logger("cjk_language_pack.vgmdb_proxy")

_BASE_URL  = "https://vgmdb.info"
_TIMEOUT   = 5        # seconds per HTTP request
_MAX_CACHE = 512      # maximum cached query results


class VGMdbProxy:
    """
    Resolve anime / drama series names from the VGMdb.info JSON API.

    Typical usage::

        proxy = VGMdbProxy()
        series = proxy.lookup_series("YOASOBI", "Idol")
        # → [{"native": "\u63a8\u3057\u306e\u5b50", "english": "Oshi no Ko"}]

        canonical = proxy.resolve_artist_for_series("Oshi no Ko")
        # → "yoasobi"  (populated after the lookup above)
    """

    def __init__(self, timeout: int = _TIMEOUT) -> None:
        self._timeout = timeout
        # {cache_key: (monotonic_timestamp, [{"native": ..., "english": ...}, ...])}
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        # Reverse map populated by lookup_series:
        # both native_name.lower() and english_name.lower() → artist_name_lower
        self._series_to_artist: dict[str, str] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def lookup_series(self, artist: str, title: str) -> list[dict]:
        """
        Return a (possibly empty) list of series info dicts for *artist* + *title*.

        Each dict has the shape::

            {"native": str, "english": str}

        where ``native`` is the original-language title (Japanese/Chinese/Korean)
        and ``english`` is the localised English title.  Both keys are always
        present; when a locale is unavailable both fields hold the same value.

        Results are cached in-process; returns ``[]`` on any network / parse
        failure.
        """
        key = self._make_key(artist, title)
        cached = self._cache.get(key)
        if cached is not None:
            return list(cached[1])

        series = self._fetch_series(artist, title)

        # Populate the reverse map so pre_normalize_text can remap later.
        # Both the native and English name are registered as aliases.
        artist_norm = artist.strip().lower()
        for hit in series:
            for name in (hit.get("native", ""), hit.get("english", "")):
                if name:
                    self._series_to_artist.setdefault(name.lower(), artist_norm)

        self._store(key, series)
        return series

    def resolve_artist_for_series(self, series_name: str) -> Optional[str]:
        """
        Return the canonical (lowercased) artist name associated with
        *series_name* if a prior :meth:`lookup_series` call populated the
        reverse map; otherwise ``None``.
        """
        if not isinstance(series_name, str):
            return None
        return self._series_to_artist.get(series_name.strip().lower())

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _make_key(artist: str, title: str) -> str:
        return f"{artist.strip().lower()}::{title.strip().lower()}"

    def _store(self, key: str, series: list[dict]) -> None:
        if len(self._cache) >= _MAX_CACHE:
            oldest = min(self._cache, key=lambda k: self._cache[k][0])
            del self._cache[oldest]
        self._cache[key] = (time.monotonic(), series)

    def _fetch_series(self, artist: str, title: str) -> list[dict]:
        """Search VGMdb.info and extract product/series names from the results."""
        query = f"{artist} {title}".strip()
        try:
            albums = self._search_albums(query)
        except Exception as exc:
            logger.debug("VGMdb search request failed for %r: %s", query, exc)
            return []

        series: list[dict] = []
        seen_pairs: set[tuple[str, str]] = set()

        for album in albums[:5]:   # inspect only the top 5 results
            for product in album.get("products", []):
                names = product.get("names", {})

                # English / localised name
                english: str = (
                    names.get("en")
                    or names.get("en-US")
                    or ""
                )

                # Native / original-language name (prefer non-English locales)
                native: str = (
                    names.get("ja")
                    or names.get("zh")
                    or names.get("ko")
                    or next(
                        (v for k, v in names.items() if k not in ("en", "en-US")),
                        None,
                    )
                    or ""
                )

                # Cross-fill when one locale is missing
                if not native:
                    native = english
                if not english:
                    english = native

                if not english and not native:
                    continue

                pair = (native.strip(), english.strip())
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    series.append({"native": pair[0], "english": pair[1]})

        logger.debug("VGMdb %r → series: %s", query, series)
        return series

    def _search_albums(self, query: str) -> list[dict]:
        """
        Call ``GET /search/albums/<query>?format=json`` and return the
        ``results.albums`` list.  Raises on network or HTTP errors.
        """
        encoded = urllib.parse.quote_plus(query)
        url = f"{_BASE_URL}/search/albums/{encoded}?format=json"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SoulSync/2.4.0"},
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            if resp.status != 200:
                return []
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("results", {}).get("albums", [])


# ── Module-level singleton ─────────────────────────────────────────────────────

_proxy: VGMdbProxy | None = None


def get_proxy() -> VGMdbProxy:
    """Return (or lazily create) the module-level :class:`VGMdbProxy`."""
    global _proxy
    if _proxy is None:
        _proxy = VGMdbProxy()
    return _proxy
