#!/usr/bin/env python3
"""
Unified Playlist Sync Service.

Provides decoupled candidate matching (matching ANY local format in library,
selecting highest quality media file, without gating by target_quality),
persistent match trace caching for 100% diagnostic parity, and unified
playlist synchronization and missing-track download dispatch.
"""

import asyncio
from collections import OrderedDict
from collections.abc import Callable, Iterator, MutableMapping
from dataclasses import dataclass, field, replace
from datetime import datetime
import inspect
import re
import threading
import time
from typing import Any, Generic, TypeVar
from urllib.parse import quote
import zlib

from sqlalchemy import text
from sqlalchemy.orm import joinedload

from core.db.echo_sync_track import EchosyncTrack
from core.event_bus import event_bus
from core.hook_manager import hook_manager
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import ExactSyncProfile
from core.matching_engine.text_utils import (
    _cmp_artists,
    _cmp_titles,
    normalize_title as _normalize_candidate_title,
    parse_duration_to_ms,
)
from core.nexus_framework.plugin_loader import PluginRegistry
from core.sync_history import sync_history
from core.task_manager.task_queue import job_queue
from core.tiered_logger import get_logger
import database.music_database as db_mod
from database.music_database import Track
import services.download_manager as dm_mod
from services.playlists_api import (
    resolve_duplicate_matches,
)
from time_utils import utc_isoformat, utc_now

logger = get_logger("playlist_sync")

LOSSLESS_FORMATS = {"flac", "wav", "alac", "aiff", "dsd", "dff", "dsf", "ape"}

_K = TypeVar("_K")
_V = TypeVar("_V")

DEFAULT_MATCH_TRACE_MAX_SIZE = 1024
DEFAULT_MATCH_TRACE_TTL_SECONDS = 1800.0
DEFAULT_ANALYSIS_JOBS_MAX_SIZE = 256
DEFAULT_ANALYSIS_JOBS_TTL_SECONDS = 3600.0


class BoundedTTLCache(MutableMapping[_K, _V], Generic[_K, _V]):
    """Thread-safe bounded LRU + TTL cache protected by a threading.Lock."""

    def __init__(
        self,
        max_size: int = 1024,
        ttl_seconds: float = 1800.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if max_size < 1:
            raise ValueError("max_size must be at least 1")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.max_size = int(max_size)
        self.ttl_seconds = float(ttl_seconds)
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: OrderedDict[_K, tuple[float, _V]] = OrderedDict()

    def _now(self) -> float:
        return self._clock() if self._clock is not None else time.monotonic()

    def _evict_expired_locked(self, now: float) -> None:
        expired_keys = [k for k, (expires_at, _) in self._entries.items() if expires_at <= now]
        for k in expired_keys:
            del self._entries[k]

    def __getitem__(self, key: _K) -> _V:
        with self._lock:
            now = self._now()
            entry = self._entries.get(key)
            if entry is None:
                raise KeyError(key)
            expires_at, value = entry
            if expires_at <= now:
                del self._entries[key]
                raise KeyError(key)
            self._entries.move_to_end(key)
            return value

    def __setitem__(self, key: _K, value: _V) -> None:
        with self._lock:
            now = self._now()
            self._evict_expired_locked(now)
            if key in self._entries:
                self._entries.move_to_end(key)
            self._entries[key] = (now + self.ttl_seconds, value)
            while len(self._entries) > self.max_size:
                self._entries.popitem(last=False)

    def __delitem__(self, key: _K) -> None:
        with self._lock:
            if key not in self._entries:
                raise KeyError(key)
            del self._entries[key]

    def __contains__(self, key: object) -> bool:
        with self._lock:
            now = self._now()
            entry = self._entries.get(key)  # type: ignore[arg-type]
            if entry is None:
                return False
            expires_at, _ = entry
            if expires_at <= now:
                del self._entries[key]  # type: ignore[arg-type]
                return False
            return True

    def __iter__(self) -> Iterator[_K]:
        with self._lock:
            self._evict_expired_locked(self._now())
            return iter(list(self._entries.keys()))

    def __len__(self) -> int:
        with self._lock:
            self._evict_expired_locked(self._now())
            return len(self._entries)

    def get(self, key: _K, default: Any = None) -> Any:
        with self._lock:
            now = self._now()
            entry = self._entries.get(key)
            if entry is None:
                return default
            expires_at, value = entry
            if expires_at <= now:
                del self._entries[key]
                return default
            self._entries.move_to_end(key)
            return value

    def items(self):  # type: ignore[override]
        with self._lock:
            self._evict_expired_locked(self._now())
            return [(k, v) for k, (_, v) in self._entries.items()]

    def keys(self):  # type: ignore[override]
        with self._lock:
            self._evict_expired_locked(self._now())
            return list(self._entries.keys())

    def values(self):  # type: ignore[override]
        with self._lock:
            self._evict_expired_locked(self._now())
            return [v for _, v in self._entries.values()]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def update_item(self, key: _K, updates: dict[str, Any]) -> bool:
        """Atomically update a cached mapping entry and refresh its TTL/recency."""
        with self._lock:
            now = self._now()
            entry = self._entries.get(key)
            if entry is None:
                return False
            expires_at, value = entry
            if expires_at <= now:
                del self._entries[key]
                return False
            new_value: Any = {**value, **updates} if isinstance(value, dict) else updates
            self._entries[key] = (now + self.ttl_seconds, new_value)
            self._entries.move_to_end(key)
            return True


# Thread-safe bounded TTL + LRU caches
MATCH_TRACE_CACHE: BoundedTTLCache[tuple, dict] = BoundedTTLCache(
    max_size=DEFAULT_MATCH_TRACE_MAX_SIZE,
    ttl_seconds=DEFAULT_MATCH_TRACE_TTL_SECONDS,
)
ANALYSIS_JOBS: BoundedTTLCache[str, dict[str, Any]] = BoundedTTLCache(
    max_size=DEFAULT_ANALYSIS_JOBS_MAX_SIZE,
    ttl_seconds=DEFAULT_ANALYSIS_JOBS_TTL_SECONDS,
)


@dataclass
class TrackMatchResult:
    """Result object for track matching in playlist sync."""

    source_track: EchosyncTrack | None = None
    provider_track_id: str | None = None
    confidence: float = 0.0

    @property
    def is_match(self) -> bool:
        """True if a track was found in the provider."""
        return self.provider_track_id is not None


@dataclass
class SourcePlaylist:
    id: str
    name: str
    tracks: list[EchosyncTrack] = field(default_factory=list)
    account_id: int | None = None
    account_name: str | None = None


@dataclass
class SyncResult:
    playlist_name: str
    total_tracks: int
    matched_tracks: int
    synced_tracks: int
    downloaded_tracks: int
    failed_tracks: int
    sync_time: datetime
    errors: list[str]
    wishlist_added_count: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_tracks == 0:
            return 0.0
        return (self.synced_tracks / self.total_tracks) * 100


@dataclass
class SyncProgress:
    current_step: str
    current_track: str
    progress: float
    total_steps: int
    current_step_number: int
    total_tracks: int = 0
    matched_tracks: int = 0
    failed_tracks: int = 0


def get_cache_key(
    title: str, artist: str, duration_ms: int = 0, album: str | None = None
) -> tuple[str, str, int]:
    """Derive deterministic cache key for a track query."""
    return (
        (title or "").strip().lower(),
        (artist or "").strip().lower(),
        int(duration_ms or 0),
    )


def cache_match_trace(query_dict: dict, trace: dict) -> None:
    """Store match evaluation trace in in-memory cache."""
    key = get_cache_key(
        query_dict.get("title", ""),
        query_dict.get("artist", ""),
        query_dict.get("duration_ms", 0),
        query_dict.get("album"),
    )
    MATCH_TRACE_CACHE[key] = trace


def get_cached_match_trace(
    title: str, artist: str, duration_ms: int = 0, album: str | None = None
) -> dict | None:
    """Retrieve cached match trace if available."""
    key = get_cache_key(title, artist, duration_ms, album)
    cached = MATCH_TRACE_CACHE.get(key)
    if cached is not None:
        return cached

    # Flexible fallback: match title + artist with duration tolerance ±5000ms
    t_clean = key[0]
    a_clean = key[1]
    dur = key[2]
    for (ct, ca, cd), trace in MATCH_TRACE_CACHE.items():
        if ct == t_clean and ca == a_clean:
            if dur == 0 or cd == 0 or abs(dur - cd) <= 5000:
                return trace
    return None


def clear_match_trace_cache() -> None:
    """Clear all cached match traces."""
    MATCH_TRACE_CACHE.clear()


def select_highest_quality_media(media_files: list[Any]) -> Any | None:
    """
    Select the edition with the highest bitrate/sample rate as the primary playback reference.

    Preference hierarchy:
    1. Lossless format (flac, wav, alac, aiff, dsd)
    2. Bitrate (bps / kbps)
    3. Sample rate (Hz)
    4. Bit depth (bits)
    """
    if not media_files:
        return None

    def _sort_key(m: Any) -> tuple[int, int, int, int]:
        fmt = getattr(m, "file_format", None) or (
            m.get("file_format") if isinstance(m, dict) else ""
        )
        fmt = str(fmt or "").lower().strip()
        is_lossless = 1 if fmt in LOSSLESS_FORMATS else 0

        bitrate = getattr(m, "bitrate", None) or (
            m.get("bitrate") if isinstance(m, dict) else 0
        )
        sample_rate = getattr(m, "sample_rate", None) or (
            m.get("sample_rate") if isinstance(m, dict) else 0
        )
        bit_depth = getattr(m, "bit_depth", None) or (
            m.get("bit_depth") if isinstance(m, dict) else 0
        )

        return (
            is_lossless,
            int(bitrate or 0),
            int(sample_rate or 0),
            int(bit_depth or 0),
        )

    return max(media_files, key=_sort_key)


def _strip_feat(title: str) -> str:
    """Strip featured artist annotations from title."""
    if not title:
        return ""
    cleaned = re.sub(
        r"\s*[\(\[\{]\s*(feat\.?|featuring|with)\b[^\)\]\}]*[\)\]\}]",
        "",
        title,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s+(feat\.?|featuring|with)\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip() or title


def _fetch_candidates_tier1(
    conn, search_title: str, base_search_title: str, track_artist: str, track_duration: int
):
    """Retrieve Tier 1 candidates using SQL connection."""
    expanded_terms = hook_manager.apply_filters(
        "search_expansion",
        [],
        title=search_title,
        artist=track_artist,
    )
    if not isinstance(expanded_terms, list):
        expanded_terms = []

    seen_terms = {search_title.lower(), base_search_title.lower()}
    clean_expanded = []
    for t in expanded_terms:
        if isinstance(t, str) and t.strip() and t.strip().lower() not in seen_terms:
            seen_terms.add(t.strip().lower())
            clean_expanded.append(t.strip())

    title_norm = search_title.replace("\u2019", "'").replace("\u2018", "'")
    norm_search = _normalize_candidate_title(search_title) or search_title

    params: dict[str, Any] = {
        "artist_exact": track_artist,
        "artist_pattern": f"%{track_artist}%",
        "title_exact": search_title,
        "title_pattern": f"%{search_title}%",
        "base_title_pattern": f"%{base_search_title}%",
        "title_norm_pattern": f"%{title_norm}%",
        "norm_search_pattern": f"%{norm_search}%",
        "duration": track_duration or 0,
    }

    def _am(param: str) -> str:
        return (
            f"(LOWER(t.title) LIKE LOWER(:{param})"
            f" OR (t.sort_title IS NOT NULL AND LOWER(t.sort_title) LIKE LOWER(:{param}))"
            f" OR (t.normalized_title IS NOT NULL AND LOWER(t.normalized_title) LIKE LOWER(:{param}))"
            f" OR EXISTS (SELECT 1 FROM track_aliases ta_x"
            f" WHERE ta_x.track_id = t.id AND LOWER(ta_x.name) LIKE LOWER(:{param})))"
        )

    base_where = (
        f"{_am('title_pattern')}\n"
        f"        OR {_am('base_title_pattern')}\n"
        f"        OR {_am('norm_search_pattern')}\n"
        f"        OR (LOWER(REPLACE(REPLACE(t.title, char(8217), char(39)), char(8216), char(39)))"
        f" LIKE LOWER(:title_norm_pattern))"
    )

    exp_parts = []
    for i, term in enumerate(clean_expanded):
        pkey = f"exp_{i}"
        params[pkey] = f"%{term}%"
        exp_parts.append(_am(pkey))
    exp_where = ("\n        OR " + "\n        OR ".join(exp_parts)) if exp_parts else ""

    from core.matching_engine.text_utils import split_artist_collaborators

    primary_art, collabs = split_artist_collaborators(track_artist or "")
    all_artists = ([primary_art] + collabs) if primary_art else ([track_artist] if track_artist else [])

    artist_order_parts = [
        "(LOWER(a.name) = LOWER(:artist_exact) OR (a.sort_name IS NOT NULL AND LOWER(a.sort_name) = LOWER(:artist_exact)) OR (ta_a.name IS NOT NULL AND LOWER(ta_a.name) = LOWER(:artist_exact)) OR (alb_a.name IS NOT NULL AND LOWER(alb_a.name) = LOWER(:artist_exact)))"
    ]
    for i, art in enumerate(all_artists):
        k = f"art_token_{i}"
        params[k] = art
        artist_order_parts.append(
            f"(LOWER(a.name) = LOWER(:{k}) OR (a.sort_name IS NOT NULL AND LOWER(a.sort_name) = LOWER(:{k})) OR (ta_a.name IS NOT NULL AND LOWER(ta_a.name) = LOWER(:{k})) OR (alb_a.name IS NOT NULL AND LOWER(alb_a.name) = LOWER(:{k})))"
        )
    artist_order_sql = " OR ".join(artist_order_parts)

    sql = text(f"""
        SELECT DISTINCT t.id, t.title, t.duration, t.edition,
               a.name AS artist_name, a.id AS artist_id,
               t.sort_title, al.title AS album_title, lm.file_path, t.sync_id
        FROM tracks t
        JOIN artists a ON t.artist_id = a.id
        LEFT JOIN track_artists ta ON t.id = ta.track_id
        LEFT JOIN artists ta_a ON ta.artist_id = ta_a.id
        LEFT JOIN albums al ON t.album_id = al.id
        LEFT JOIN artists alb_a ON al.artist_id = alb_a.id
        JOIN local_media lm ON t.id = lm.track_id
        WHERE ({base_where}{exp_where})
        ORDER BY
            ({artist_order_sql}) DESC,
            (LOWER(t.title) = LOWER(:title_exact)) DESC,
            ABS(t.duration - :duration) ASC
        LIMIT 50
    """)

    return conn.execute(sql, params).fetchall()


def _fetch_candidates_tier2(
    conn, search_title: str, track_duration: int, duration_window_ms: int = 10000
):
    """Retrieve Tier 2 candidates using SQL connection."""
    expanded_terms = hook_manager.apply_filters(
        "search_expansion",
        [],
        title=search_title,
        artist="",
    )
    if not isinstance(expanded_terms, list):
        expanded_terms = []

    seen_terms = {search_title.lower()}
    clean_expanded = []
    for t in expanded_terms:
        if isinstance(t, str) and t.strip() and t.strip().lower() not in seen_terms:
            seen_terms.add(t.strip().lower())
            clean_expanded.append(t.strip())

    norm_search = _normalize_candidate_title(search_title) or search_title
    params: dict[str, Any] = {
        "title_exact": search_title,
        "title_pattern": f"%{search_title}%",
        "norm_search_pattern": f"%{norm_search}%",
        "duration": track_duration,
    }

    base_where = (
        "LOWER(t.title) LIKE LOWER(:title_pattern)\n"
        "        OR (t.sort_title IS NOT NULL AND LOWER(t.sort_title) LIKE LOWER(:title_pattern))\n"
        "        OR (t.normalized_title IS NOT NULL AND LOWER(t.normalized_title) LIKE LOWER(:norm_search_pattern))\n"
        "        OR EXISTS (SELECT 1 FROM track_aliases ta_x\n"
        "                   WHERE ta_x.track_id = t.id AND (LOWER(ta_x.name) LIKE LOWER(:title_pattern) OR LOWER(ta_x.name) LIKE LOWER(:norm_search_pattern)))"
    )

    exp_parts = []
    for i, term in enumerate(clean_expanded):
        pkey = f"exp_{i}"
        params[pkey] = f"%{term}%"
        exp_parts.append(
            f"(LOWER(t.title) LIKE LOWER(:{pkey})"
            f" OR (t.sort_title IS NOT NULL AND LOWER(t.sort_title) LIKE LOWER(:{pkey}))"
            f" OR (t.normalized_title IS NOT NULL AND LOWER(t.normalized_title) LIKE LOWER(:{pkey}))"
            f" OR EXISTS (SELECT 1 FROM track_aliases ta_x"
            f" WHERE ta_x.track_id = t.id AND LOWER(ta_x.name) LIKE LOWER(:{pkey})))"
        )
    exp_where = ("\n        OR " + "\n        OR ".join(exp_parts)) if exp_parts else ""

    sql = text(f"""
        SELECT DISTINCT t.id, t.title, t.duration, t.edition,
               a.name AS artist_name, a.id AS artist_id,
               t.sort_title, al.title AS album_title, lm.file_path, t.sync_id
        FROM tracks t
        JOIN artists a ON t.artist_id = a.id
        LEFT JOIN albums al ON t.album_id = al.id
        JOIN local_media lm ON t.id = lm.track_id
        WHERE ({base_where}{exp_where})
        ORDER BY
            (LOWER(t.title) = LOWER(:title_exact)) DESC,
            ABS(t.duration - :duration) ASC
        LIMIT 50
    """)

    return conn.execute(sql, params).fetchall()


# Canonical aliases for candidate retrieval
_fetch_tier1_candidates = _fetch_candidates_tier1
_fetch_tier2_candidates = _fetch_candidates_tier2


def evaluate_single_track_diagnostics(
    title: str,
    artist: str,
    duration_ms: int = 0,
    album: str | None = None,
    db: Any | None = None,
    matching_engine: WeightedMatchingEngine | None = None,
) -> dict:
    """
    Run the canonical matching pipeline for a single track and return structured match trace.
    Provides 100% parity with batch playlist sync evaluation.
    """
    if db is None:
        db = db_mod.MusicDatabase()
    profile = ExactSyncProfile()
    if matching_engine is None:
        matching_engine = WeightedMatchingEngine(profile)

    clean_search_title = _strip_feat(title or "")
    base_search_title = re.sub(r"\s*[\(\[].*?[\)\]]", "", clean_search_title).strip()
    base_search_title = re.sub(r"\s+-.*$", "", base_search_title).strip() or clean_search_title

    from core.matching_engine.track_parser import extract_version_descriptors

    _src_clean_t, _src_version, _src_edition = extract_version_descriptors(title or "")
    source_track = EchosyncTrack(
        raw_title=title,
        artist_name=artist,
        album_title=album or "",
        duration_ms=duration_ms,
        edition=_src_edition,
        version=_src_version,
    )
    hook_manager.apply_filters(
        "pre_normalize_title",
        source_track.raw_title,
        plugin_context=source_track.plugin_context,
    )
    clean_src = _normalize_candidate_title(
        source_track.raw_title,
        plugin_context=source_track.plugin_context,
    )
    if clean_src:
        source_track = replace(source_track, title=clean_src)

    candidate_rows = []
    seen_ids = set()

    with db.engine.connect() as conn:
        t1_rows = _fetch_candidates_tier1(conn, clean_search_title, base_search_title, artist, duration_ms)
        for r in t1_rows:
            if r[0] not in seen_ids:
                seen_ids.add(r[0])
                candidate_rows.append(r)

        if duration_ms and len(candidate_rows) < 10:
            t2_rows = _fetch_candidates_tier2(conn, clean_search_title, duration_ms, 10000)
            for r in t2_rows:
                if r[0] not in seen_ids:
                    seen_ids.add(r[0])
                    candidate_rows.append(r)

    # If no SQL rows found, query candidate tracks via ORM session fallback
    if not candidate_rows:
        with db.session_scope() as session:
            from services.playlists_api import get_library_candidates

            orm_candidates = get_library_candidates(session, clean_search_title, artist)
            for cand in orm_candidates:
                if cand.id not in seen_ids:
                    seen_ids.add(cand.id)
                    highest_media = select_highest_quality_media(cand.media_files)
                    media_path = highest_media.file_path if highest_media else None
                    candidate_rows.append(
                        (
                            cand.id,
                            cand.title,
                            cand.duration,
                            cand.edition,
                            cand.artist.name if cand.artist else "",
                            cand.artist_id,
                            cand.sort_title,
                            cand.album.title if cand.album else "",
                            media_path,
                            cand.sync_id or str(cand.id),
                        )
                    )

    candidate_evaluations: list[dict] = []
    candidate_tracks_by_id: dict[int, EchosyncTrack] = {}
    best_candidate_eval = None
    best_score = 0.0

    # Fetch track and artist aliases
    alias_map: dict[int, list[str]] = {}
    artist_alias_map: dict[int, list[str]] = {}
    if candidate_rows:
        try:
            cids = [int(r[0]) for r in candidate_rows]
            with db.engine.connect() as ac:
                for ar in ac.execute(
                    text(
                        "SELECT track_id, name FROM track_aliases WHERE track_id IN ("
                        + ",".join(str(c) for c in cids)
                        + ")"
                    )
                ).fetchall():
                    alias_map.setdefault(ar[0], []).append(ar[1])

                a_ids = list({int(r[5]) for r in candidate_rows if r[5] is not None})
                if a_ids:
                    for aar in ac.execute(
                        text(
                            "SELECT artist_id, name FROM artist_aliases WHERE artist_id IN ("
                            + ",".join(str(a) for a in a_ids)
                            + ")"
                        )
                    ).fetchall():
                        artist_alias_map.setdefault(aar[0], []).append(aar[1])
        except Exception as ex:
            logger.debug(f"Alias query error: {ex}")

    active_dur_map: dict[int, int] = {}
    primary_artist_map: dict[int, list[str]] = {}
    featured_artist_map: dict[int, list[str]] = {}
    remixer_map: dict[int, list[str]] = {}
    if candidate_rows:
        try:
            cids = [int(r[0]) for r in candidate_rows]
            with db.engine.connect() as ac:
                for adr in ac.execute(
                    text(
                        "SELECT track_id, MAX(active_duration_ms) FROM local_media "
                        "WHERE track_id IN ("
                        + ",".join(str(cid) for cid in cids)
                        + ") AND active_duration_ms IS NOT NULL GROUP BY track_id"
                    )
                ).fetchall():
                    if adr[1]:
                        active_dur_map[int(adr[0])] = int(adr[1])
                for rar in ac.execute(
                    text(
                        "SELECT ta.track_id, a.name, lower(ta.role) FROM track_artists ta "
                        "JOIN artists a ON ta.artist_id = a.id "
                        "WHERE ta.track_id IN ("
                        + ",".join(str(cid) for cid in cids)
                        + ") AND lower(ta.role) IN ('remixer', 'featured', 'primary')"
                    )
                ).fetchall():
                    if rar[1]:
                        tid = int(rar[0])
                        aname = str(rar[1])
                        role = str(rar[2] or "").strip().lower()
                        if role == "primary":
                            primary_artist_map.setdefault(tid, []).append(aname)
                        elif role == "featured":
                            featured_artist_map.setdefault(tid, []).append(aname)
                        elif role == "remixer":
                            remixer_map.setdefault(tid, []).append(aname)
        except Exception as ex:
            logger.debug(f"Active duration / remixer query error: {ex}")

    for row in candidate_rows:
        cand_id = row[0]
        raw_t = row[1]
        cand_dur = parse_duration_to_ms(row[2]) if row[2] else 0
        cand_ed = row[3]
        cand_artist = row[4] or ""
        cand_artist_id = row[5]
        cand_album = row[7] if len(row) > 7 else ""
        cand_media_path = row[8] if len(row) > 8 else None
        sync_id = row[9] if len(row) > 9 and row[9] else str(cand_id)
        cand_active_dur = active_dur_map.get(cand_id)
        cand_primary_artists = primary_artist_map.get(cand_id, [])
        cand_featured_artists = featured_artist_map.get(cand_id, [])
        cand_remixers = remixer_map.get(cand_id, [])

        cand_extra: dict[str, Any] = {}
        if cand_active_dur:
            cand_extra["active_duration_ms"] = cand_active_dur
        if cand_media_path:
            cand_extra["file_path"] = cand_media_path

        cand_track = EchosyncTrack(
            raw_title=raw_t,
            artist_name=cand_artist,
            album_title=cand_album or "",
            duration_ms=cand_dur,
            edition=cand_ed,
            primary_artists=cand_primary_artists,
            featured_artists=cand_featured_artists,
            remixers=cand_remixers,
            sync_id=sync_id,
            extra_metadata=cand_extra,
        )
        hook_manager.apply_filters(
            "pre_normalize_title",
            cand_track.raw_title,
            plugin_context=cand_track.plugin_context,
        )

        clean_cand_t = _normalize_candidate_title(
            raw_t,
            plugin_context=cand_track.plugin_context,
        )
        best_cand_t = clean_cand_t or cand_track.title
        for al in alias_map.get(cand_id, []):
            if al and _cmp_titles(source_track.title, al) > _cmp_titles(source_track.title, best_cand_t):
                best_cand_t = al
        if best_cand_t:
            cand_track = replace(cand_track, title=best_cand_t)

        best_art = cand_track.artist_name or ""
        for art_al in artist_alias_map.get(cand_artist_id, []):
            if art_al and _cmp_artists(source_track.artist_name, art_al) > _cmp_artists(
                source_track.artist_name, best_art
            ):
                best_art = art_al
        if best_art:
            cand_track = replace(cand_track, artist_name=best_art)

        candidate_tracks_by_id[cand_id] = cand_track
        match_res = matching_engine.calculate_match(source_track, cand_track)
        confidence = min(100.0, max(0.0, match_res.confidence_score))

        delta_sec = round(abs(cand_dur - duration_ms) / 1000.0, 2) if (cand_dur and duration_ms) else 0.0
        accepted = confidence >= profile.weights.min_confidence_to_accept

        rejection_reason = None
        if not accepted:
            if not match_res.passed_version_check:
                rejection_reason = f"Version mismatch: {match_res.reasoning}"
            elif delta_sec > 6.0 and match_res.duration_match_score == 0.0:
                rejection_reason = f"Duration Delta > 6.0s ({delta_sec}s)"
            else:
                rejection_reason = (
                    f"Confidence {confidence:.1f}% below threshold {profile.weights.min_confidence_to_accept:.1f}%"
                )

        penalties = dict(match_res.penalties or {})
        if match_res.version_penalty_applied > 0:
            penalties["version_penalty"] = match_res.version_penalty_applied
        if match_res.edition_penalty_applied > 0:
            penalties["edition_penalty"] = match_res.edition_penalty_applied

        eval_item = {
            "track_sync_id": sync_id,
            "track_id": cand_id,
            "title": raw_t or cand_track.title,
            "artist": cand_artist or cand_track.artist_name,
            "album": cand_album,
            "duration_ms": cand_dur,
            "duration_delta_sec": delta_sec,
            "title_score": round(match_res.title_score, 2),
            "artist_score": round(match_res.artist_score, 2),
            "duration_score": round(match_res.duration_match_score, 2),
            "album_score": round(match_res.album_score, 2),
            "penalties": penalties,
            "composite_score": round(confidence, 2),
            "accepted": accepted,
            "rejection_reason": rejection_reason,
        }
        candidate_evaluations.append(eval_item)

        if confidence > best_score:
            best_score = confidence
            best_candidate_eval = eval_item

    # Tier 3 Deluxe & Remaster fallback when no primary candidate was accepted.
    # Ensures Sync matches an existing local Remaster (within 5s duration tolerance)
    # when the Original is absent, preventing duplicate download re-requests while
    # always preferring the Original whenever one exists in the library.
    if candidate_evaluations and not any(c["accepted"] for c in candidate_evaluations):
        from core.matching_engine.matching_engine import get_version_family

        t3_best_score = -1.0
        for eval_item in candidate_evaluations:
            cand_track = candidate_tracks_by_id.get(eval_item["track_id"])
            if cand_track is None:
                continue
            t3_res = matching_engine.calculate_match(
                source_track, cand_track, context="tier3_fallback"
            )
            t3_conf = min(100.0, max(0.0, t3_res.confidence_score))
            if t3_res.passed_version_check and t3_conf >= profile.weights.min_confidence_to_accept:
                penalties = dict(t3_res.penalties or {})
                if t3_res.version_penalty_applied > 0:
                    penalties["version_penalty"] = t3_res.version_penalty_applied
                if t3_res.edition_penalty_applied > 0:
                    penalties["edition_penalty"] = t3_res.edition_penalty_applied
                eval_item["title_score"] = round(t3_res.title_score, 2)
                eval_item["artist_score"] = round(t3_res.artist_score, 2)
                eval_item["duration_score"] = round(t3_res.duration_match_score, 2)
                eval_item["album_score"] = round(t3_res.album_score, 2)
                eval_item["penalties"] = penalties
                eval_item["composite_score"] = round(t3_conf, 2)
                eval_item["accepted"] = True
                eval_item["rejection_reason"] = None
                eval_item["fallback_tier"] = "tier3_fallback"
                if (
                    get_version_family(getattr(cand_track, "edition", None)) == "remaster"
                    or get_version_family(getattr(source_track, "edition", None)) == "remaster"
                ):
                    eval_item["matched_via_remaster_fallback"] = True
                if t3_conf > t3_best_score:
                    t3_best_score = t3_conf
                    best_score = t3_conf
                    best_candidate_eval = eval_item

    candidate_evaluations.sort(key=lambda c: c["composite_score"], reverse=True)
    best_match = (
        best_candidate_eval
        if (best_candidate_eval and best_candidate_eval["accepted"])
        else (
            candidate_evaluations[0]
            if candidate_evaluations and candidate_evaluations[0]["accepted"]
            else None
        )
    )

    trace = {
        "query": {
            "title": title,
            "artist": artist,
            "duration_ms": duration_ms,
            "album": album,
        },
        "candidates_located_count": len(candidate_evaluations),
        "candidates_retrieved_count": len(candidate_evaluations),
        "evaluated_candidates": candidate_evaluations,
        "candidates": candidate_evaluations,
        "best_match": best_match,
        "winning_threshold": profile.weights.min_confidence_to_accept,
    }

    cache_match_trace(trace["query"], trace)
    return trace


def analyze_playlist(
    source_provider: Any = None,
    playlist_id: str | None = None,
    playlist_name: str = "Unknown Playlist",
    tracks: list[Any] | None = None,
    target_source: str | None = None,
    target_quality: str | None = None,
    db: Any | None = None,
    matching_engine: WeightedMatchingEngine | None = None,
) -> dict[str, Any]:
    """
    Analyze a playlist's tracks against the local library without gating candidates by target_quality.

    Selects the highest quality available media file for each candidate, but marks tracks as 'Found'
    regardless of whether they meet target_quality. Restricts target_quality exclusively for download queue.
    """
    if db is None:
        db = db_mod.MusicDatabase()
    profile = ExactSyncProfile()
    if matching_engine is None:
        matching_engine = WeightedMatchingEngine(profile)

    source_tracks = []
    if tracks:
        source_tracks = tracks
    elif source_provider and playlist_id:
        sig = inspect.signature(source_provider.get_playlist_tracks)
        if "force_refresh" in sig.parameters:
            source_tracks = source_provider.get_playlist_tracks(playlist_id, force_refresh=True)
        else:
            source_tracks = source_provider.get_playlist_tracks(playlist_id)

    all_tracks = []
    found_count = 0
    missing_count = 0

    for item in source_tracks:
        if isinstance(item, dict):
            track_title = item.get("title") or item.get("raw_title") or ""
            track_artist = item.get("artist") or item.get("artist_name") or ""
            track_album = item.get("album") or item.get("album_title") or ""
            track_duration = item.get("duration_ms") or item.get("duration") or 0
            if isinstance(track_duration, str):
                track_duration = parse_duration_to_ms(track_duration)
            item_id = item.get("id") or item.get("playlist_track_id")
            item_isrc = item.get("isrc")
            source_track_dict = item
        else:
            track_title = getattr(item, "title", "")
            track_artist = getattr(item, "artist_name", "") or getattr(item, "artist", "")
            track_album = getattr(item, "album_title", "") or getattr(item, "album", "")
            track_duration = getattr(item, "duration", 0) or getattr(item, "duration_ms", 0)
            item_id = getattr(item, "id", None)
            item_isrc = getattr(item, "isrc", None)
            source_track_dict = item.to_dict() if hasattr(item, "to_dict") else None

        # Execute single track diagnostics matching pipeline
        trace = evaluate_single_track_diagnostics(
            title=track_title,
            artist=track_artist,
            duration_ms=track_duration,
            album=track_album,
            db=db,
            matching_engine=matching_engine,
        )

        candidates = trace.get("candidates", [])
        best_match = trace.get("best_match")
        best_score = (
            best_match.get("composite_score", 0.0)
            if best_match
            else (candidates[0]["composite_score"] if candidates else 0.0)
        )
        matched_track_id = best_match.get("track_id") if best_match else None

        if matched_track_id is None and candidates and candidates[0]["accepted"]:
            best_match = candidates[0]
            matched_track_id = best_match["track_id"]
            best_score = best_match["composite_score"]

        # Selection of highest quality media file for the matched track
        primary_media_path = None
        target_identifier = None
        if matched_track_id is not None:
            try:
                with db.session_scope() as session:
                    t_rec = (
                        session.query(Track)
                        .filter_by(id=matched_track_id)
                        .options(joinedload(Track.media_files))
                        .first()
                    )
                    if t_rec and t_rec.media_files:
                        highest_media = select_highest_quality_media(t_rec.media_files)
                        if highest_media:
                            primary_media_path = highest_media.file_path
            except Exception as e:
                logger.debug(f"Media file lookup error for track {matched_track_id}: {e}")

            if target_source:
                try:
                    if hasattr(db, "get_external_identifier_map"):
                        id_map = db.get_external_identifier_map(str(target_source), [matched_track_id])
                        target_identifier = id_map.get(matched_track_id) if isinstance(id_map, dict) else None
                    elif hasattr(db, "get_external_identifier"):
                        target_identifier = db.get_external_identifier(
                            str(target_source), matched_track_id
                        )
                except Exception:
                    target_identifier = None

        matched = bool(matched_track_id and best_score >= 70.0)
        if matched:
            if best_score >= 85:
                library_match = "Found"
            else:
                library_match = f"Found (score: {int(best_score)}%)"
            found_count += 1
            status = "found"
        else:
            library_match = "Not Found"
            missing_count += 1
            status = "not_found"

        duration_str = "–"
        if track_duration:
            mins = track_duration // 60000
            secs = (track_duration % 60000) // 1000
            duration_str = f"{mins}:{secs:02d}"

        valid_candidates = [
            {
                "id": c["track_id"],
                "score": c["composite_score"],
                "title": c["title"],
                "artist": c["artist"],
            }
            for c in candidates
            if c["composite_score"] >= 70
        ]

        track_summary = {
            "playlist": playlist_name,
            "playlist_track_id": item_id,
            "title": track_title,
            "artist": track_artist,
            "album": track_album,
            "duration": duration_str,
            "duration_ms": track_duration,
            "isrc": item_isrc,
            "status": status,
            "library_match": library_match,
            "download_status": "-",
            "matched_track_id": matched_track_id if matched else None,
            "primary_media_path": primary_media_path,
            "match_score": best_score,
            "rejection_reason": candidates[0].get("rejection_reason")
            if (candidates and not matched)
            else None,
            "candidate_matches": valid_candidates,
            "target_source": target_source,
            "target_identifier": target_identifier if matched else None,
            "target_exists": bool(target_identifier) if matched else False,
            "source_track": source_track_dict,
            "match_diagnostics": trace,
        }
        all_tracks.append(track_summary)

    all_tracks = resolve_duplicate_matches(all_tracks)
    total_tracks = len(all_tracks)
    found_count = sum(1 for t in all_tracks if t.get("matched_track_id"))
    missing_count = total_tracks - found_count

    matched_pairs = []
    missing_tracks = []
    for t in all_tracks:
        if t.get("matched_track_id"):
            matched_pairs.append(
                {
                    "track_id": t["matched_track_id"],
                    "matched_track_id": t["matched_track_id"],
                    "target_identifier": t.get("target_identifier"),
                    "title": t.get("title"),
                    "artist": t.get("artist"),
                    "album": t.get("album"),
                    "duration_ms": t.get("duration_ms"),
                    "source_title": t.get("title"),
                    "source_artist": t.get("artist"),
                    "source_track": t.get("source_track"),
                    "primary_media_path": t.get("primary_media_path"),
                }
            )
        else:
            missing_tracks.append(
                {
                    "title": t["title"],
                    "artist": t["artist"],
                    "album": t["album"],
                    "duration": t.get("duration_ms"),
                    "duration_ms": t.get("duration_ms"),
                    "isrc": t.get("isrc"),
                    "source_track": t.get("source_track"),
                    "rejection_reason": t.get("rejection_reason"),
                }
            )

    return {
        "summary": {
            "total_tracks": total_tracks,
            "found_in_library": found_count,
            "missing_tracks": missing_count,
            "downloaded": 0,
            "quality_profile": target_quality or "Auto",
            "target_quality": target_quality or "Auto",
            "source": getattr(source_provider, "name", "unknown") if source_provider else "unknown",
            "target": target_source,
            "matched_pairs": matched_pairs,
            "can_sync": len(matched_pairs) > 0,
        },
        "tracks": all_tracks,
        "missing": missing_tracks,
    }


def analyze_playlists(
    source: Any,
    target_source: str | None,
    playlists: list[dict] | dict,
    target_quality: str | None = "Auto",
    db: Any | None = None,
) -> dict[str, Any]:
    """Analyze multiple playlists or a single playlist dict."""
    if isinstance(playlists, dict):
        playlists = [playlists]

    if db is None:
        db = db_mod.MusicDatabase()

    matching_engine = WeightedMatchingEngine(ExactSyncProfile())

    from web.routes.playlists import _get_provider_for_account, _normalize_provider_short_name

    target_source_canonical = (
        _normalize_provider_short_name(target_source) if target_source else target_source
    )

    needs_provider = any(not p.get("tracks") for p in playlists if isinstance(p, dict))
    source_provider = None
    caps = None
    if isinstance(source, str) and needs_provider:
        source_provider, _ = _get_provider_for_account(source, None)
        if source_provider:
            caps = getattr(source_provider, "capabilities", None)
    elif not isinstance(source, str):
        source_provider = source
        caps = getattr(source_provider, "capabilities", None)

    all_tracks = []
    found_count = 0
    missing_count = 0

    for playlist_info in playlists:
        playlist_id = playlist_info.get("id")
        playlist_name = playlist_info.get("name", "Unknown Playlist")
        provided_tracks = playlist_info.get("tracks")

        provider_to_use = source_provider
        acc_id = playlist_info.get("account_id")
        if acc_id and caps and getattr(caps, "supports_user_auth", False):
            inst, _ = _get_provider_for_account(source, acc_id)
            if inst:
                provider_to_use = inst

        res = analyze_playlist(
            source_provider=provider_to_use,
            playlist_id=playlist_id,
            playlist_name=playlist_name,
            tracks=provided_tracks,
            target_source=target_source_canonical,
            target_quality=target_quality,
            db=db,
            matching_engine=matching_engine,
        )
        all_tracks.extend(res.get("tracks", []))

    all_tracks = resolve_duplicate_matches(all_tracks)
    total_tracks = len(all_tracks)
    found_count = sum(1 for t in all_tracks if t.get("matched_track_id"))
    missing_count = total_tracks - found_count

    matched_pairs = []
    missing_tracks = []
    for track in all_tracks:
        if track.get("matched_track_id"):
            matched_pairs.append(
                {
                    "track_id": track["matched_track_id"],
                    "matched_track_id": track["matched_track_id"],
                    "target_identifier": track.get("target_identifier"),
                    "title": track.get("title"),
                    "artist": track.get("artist"),
                    "album": track.get("album"),
                    "duration_ms": track.get("duration_ms"),
                    "source_title": track.get("title"),
                    "source_artist": track.get("artist"),
                    "source_track": track.get("source_track"),
                    "primary_media_path": track.get("primary_media_path"),
                }
            )
        else:
            missing_tracks.append(
                {
                    "title": track["title"],
                    "artist": track["artist"],
                    "album": track["album"],
                    "duration": track.get("duration_ms"),
                    "duration_ms": track.get("duration_ms"),
                    "isrc": track.get("isrc"),
                    "source_track": track.get("source_track"),
                    "rejection_reason": track.get("rejection_reason"),
                }
            )

    return {
        "summary": {
            "total_tracks": total_tracks,
            "found_in_library": found_count,
            "missing_tracks": missing_count,
            "downloaded": 0,
            "quality_profile": target_quality,
            "target_quality": target_quality,
            "source": source if isinstance(source, str) else getattr(source, "name", "unknown"),
            "target": target_source_canonical or target_source,
            "matched_pairs": matched_pairs,
            "can_sync": len(matched_pairs) > 0,
        },
        "tracks": all_tracks,
        "missing": missing_tracks,
    }


def queue_missing_downloads(
    missing: list[dict[str, Any]],
    target_quality: str | None = None,
    download_manager: Any | None = None,
) -> dict[str, Any]:
    """
    Queue missing tracks for download, applying target_quality strictly to the download queue.
    """
    if not missing:
        return {"accepted": False, "error": "missing tracks list required"}

    dm = download_manager or dm_mod.get_download_manager()
    success_count = 0
    failed_count = 0

    for track_info in missing:
        try:
            source_track_payload = track_info.get("source_track")
            if isinstance(source_track_payload, dict):
                track = EchosyncTrack.from_dict(source_track_payload)
            else:
                duration_ms = track_info.get("duration_ms")
                if duration_ms is None:
                    duration_ms = track_info.get("duration")

                identifiers = dict(track_info.get("identifiers") or {})
                source_identifier = track_info.get("source_identifier")
                source_key = track_info.get("source")
                if not source_key and isinstance(source_identifier, str) and "-" in source_identifier:
                    source_key = source_identifier.split("-", 1)[0]
                if source_identifier:
                    if source_key:
                        identifiers[str(source_key)] = str(source_identifier)
                    identifiers.setdefault("provider_id", str(source_identifier))

                track = EchosyncTrack(
                    raw_title=track_info.get("title") or "",
                    artist_name=track_info.get("artist") or "",
                    album_title=track_info.get("album") or "",
                    duration_ms=duration_ms,
                    isrc=track_info.get("isrc"),
                    identifiers=identifiers,
                )

            if target_quality is not None:
                try:
                    download_id = dm.queue_download(track, quality_profile_id=target_quality)
                except TypeError:
                    download_id = dm.queue_download(track)
            else:
                download_id = dm.queue_download(track)

            if download_id:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Error queuing track: {e}")

    if success_count > 0:
        if hasattr(dm, "process_downloads_now"):
            try:
                dm.process_downloads_now()
            except Exception as proc_err:
                logger.warning(f"Error calling process_downloads_now: {proc_err}")
        try:
            from core.task_manager.task_queue import job_queue

            job_queue.trigger_job_by_name("download_manager")
        except Exception as e:
            logger.warning(f"Queued downloads but background trigger failed: {e}")

    return {
        "accepted": True,
        "track_count": len(missing),
        "queued": success_count,
        "failed": failed_count,
        "message": f"Queued {success_count} tracks to download_manager (failed: {failed_count})",
    }


class PlaylistSyncService:
    """Unified service for playlist analysis, matching diagnostics, and sync execution."""

    def __init__(
        self,
        db: Any | None = None,
        source_client: Any = None,
        media_client: Any = None,
        default_source_provider: str | None = None,
        **legacy_clients: Any,
    ):
        self._db = db
        self.matching_engine = WeightedMatchingEngine(ExactSyncProfile())
        self._client_cache: dict[str, Any] = {}
        self._default_source_provider = default_source_provider

        if source_client is not None:
            self._client_cache["source"] = source_client
            self._client_cache["source_list"] = [source_client]
        if media_client is not None:
            self._client_cache["media_server"] = media_client

        for key, client_val in legacy_clients.items():
            if client_val is None:
                continue
            if key.endswith("_client"):
                p_key = key[:-7]
                self._client_cache[p_key] = client_val
                self._client_cache[f"{p_key}_list"] = [client_val]
            else:
                self._client_cache[key] = client_val

        self._download_manager: Any | None = None
        self.progress_callbacks: dict[str, Callable[[SyncProgress], None]] = {}
        self.syncing_playlists: set[str] = set()
        self._cancelled = False

    @property
    def download_manager(self) -> Any:
        if self._download_manager is not None:
            return self._download_manager
        return dm_mod.get_download_manager()

    @download_manager.setter
    def download_manager(self, value: Any) -> None:
        self._download_manager = value

    @property
    def db(self) -> Any:
        if self._db is None:
            self._db = db_mod.MusicDatabase()
        return self._db

    @db.setter
    def db(self, value: Any) -> None:
        self._db = value

    def _resolve_default_source_provider_name(self) -> str:
        if self._default_source_provider:
            return self._default_source_provider
        for k in self._client_cache:
            if k.endswith("_list") and k != "source_list":
                return k[:-5]
        try:
            from core.nexus_framework.plugin_SDK import PlaylistSupport
            from core.nexus_framework.plugin_loader import get_plugin_capabilities

            for p_name in PluginRegistry.list_plugins():
                if PluginRegistry.is_plugin_disabled(p_name):
                    continue
                try:
                    caps = get_plugin_capabilities(p_name)
                    if caps and caps.supports_playlists in (
                        PlaylistSupport.READ,
                        PlaylistSupport.READ_WRITE,
                    ):
                        if not getattr(caps, "supports_library_scan", False):
                            return str(getattr(caps, "name", p_name)).split(".")[-1].lower()
                except Exception:
                    continue
        except Exception:
            pass
        try:
            from core.settings import config_manager

            configured = config_manager.get("active_playlist_source")
            if configured:
                return str(configured)
        except Exception:
            pass
        return "default_source"

    def _get_cached_client(self, name: str) -> Any:
        if name in self._client_cache:
            return self._client_cache[name]
        try:
            client = PluginRegistry.create_instance(name)
            self._client_cache[name] = client
            return client
        except Exception as e:
            logger.warning(f"{str(name).capitalize()} client unavailable: {e}")
            return None

    def get_provider_client(self, provider_key: str | None = None) -> Any:
        key = provider_key or self._resolve_default_source_provider_name()
        if key in self._client_cache:
            return self._client_cache[key]
        clients = self.get_provider_clients(key)
        if clients:
            self._client_cache[key] = clients[0]
            return clients[0]
        return None

    def get_provider_clients(self, provider_key: str | None = None) -> list[Any]:
        key = provider_key or self._resolve_default_source_provider_name()
        list_key = f"{key}_list"
        if list_key in self._client_cache:
            return self._client_cache[list_key]

        clients = []
        try:
            from services.storage_service import get_storage_service

            storage = get_storage_service()
            accounts = storage.list_accounts(key) or []

            for acc in accounts:
                try:
                    if acc.get("is_active") is False:
                        continue
                    client = PluginRegistry.create_instance(key, account_id=acc.get("id"))
                    if client and (not hasattr(client, "is_configured") or client.is_configured()):
                        clients.append(client)
                except Exception as e:
                    logger.warning(f"Failed to load {key} client for account {acc.get('id')}: {e}")
                    continue

            if not clients:
                try:
                    client = PluginRegistry.create_instance(key)
                    if client:
                        clients = [client]
                except Exception as e:
                    logger.error(f"Failed to create default {key} client: {e}")
        except Exception:
            try:
                client = PluginRegistry.create_instance(key)
                if client:
                    clients = [client]
            except Exception as create_err:
                logger.error(f"Critical failure creating {key} client: {create_err}")

        self._client_cache[list_key] = clients
        return clients

    @property
    def source_client(self) -> Any:
        if "source" in self._client_cache:
            return self._client_cache["source"]
        return self.get_provider_client()

    @source_client.setter
    def source_client(self, value: Any) -> None:
        self._client_cache["source"] = value
        if value:
            self._client_cache["source_list"] = [value]

    @property
    def source_clients(self) -> list[Any]:
        if "source_list" in self._client_cache:
            return self._client_cache["source_list"]
        return self.get_provider_clients()

    @source_clients.setter
    def source_clients(self, value: list[Any]) -> None:
        self._client_cache["source_list"] = value
        if value:
            self._client_cache["source"] = value[0]

    def __getattr__(self, name: str) -> Any:
        if name.endswith("_clients") and not name.startswith("_"):
            provider_key = name[:-8]
            self._default_source_provider = provider_key
            return self.get_provider_clients(provider_key)
        if name.endswith("_client") and not name.startswith("_"):
            provider_key = name[:-7]
            return self.get_provider_client(provider_key)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def _get_active_media_client(self, target_server: str | None = None) -> tuple[Any, str]:
        """Get the active media client based on config settings."""
        if "media_server" in self._client_cache:
            client = self._client_cache["media_server"]
            server_name = getattr(client, "name", None) or target_server or "media_server"
            return client, str(server_name)
        try:
            from core.settings import config_manager

            active_server = target_server or config_manager.get("active_media_server")
            if not active_server:
                active_ids = PluginRegistry.get_active_services_by_type("media_server")
                active_server = str(active_ids[0]) if active_ids else "media_server"

            client = self._get_cached_client(str(active_server))
            if not client:
                logger.error(f"{str(active_server).capitalize()} client not available to sync service")
                return None, str(active_server)
            return client, str(active_server)
        except Exception as e:
            logger.error(f"Error determining active media server: {e}")
            return None, target_server or "media_server"

    @property
    def is_syncing(self) -> bool:
        """Check if any playlist is currently syncing."""
        return len(self.syncing_playlists) > 0

    @is_syncing.setter
    def is_syncing(self, value: bool) -> None:
        if not value:
            self.syncing_playlists.clear()

    def set_progress_callback(
        self, callback: Callable[[SyncProgress], None], playlist_name: str | None = None
    ) -> None:
        if playlist_name:
            self.progress_callbacks[playlist_name] = callback
        else:
            for playlist in self.syncing_playlists:
                self.progress_callbacks[playlist] = callback

    def clear_progress_callback(self, playlist_name: str) -> None:
        if playlist_name in self.progress_callbacks:
            del self.progress_callbacks[playlist_name]

    def cancel_sync(self) -> None:
        logger.info("PlaylistSyncService.cancel_sync() called - setting cancellation flag")
        self._cancelled = True
        self.is_syncing = False

    def _update_progress(
        self,
        playlist_name: str,
        step: str,
        track: str,
        progress: float,
        total_steps: int,
        current_step: int,
        total_tracks: int = 0,
        matched_tracks: int = 0,
        failed_tracks: int = 0,
    ) -> None:
        callback = self.progress_callbacks.get(playlist_name)
        if callback:
            callback(
                SyncProgress(
                    current_step=step,
                    current_track=track,
                    progress=progress,
                    total_steps=total_steps,
                    current_step_number=current_step,
                    total_tracks=total_tracks,
                    matched_tracks=matched_tracks,
                    failed_tracks=failed_tracks,
                )
            )

    def analyze_playlist(self, *args, **kwargs) -> dict[str, Any]:
        if "db" not in kwargs:
            kwargs["db"] = self.db
        if "matching_engine" not in kwargs:
            kwargs["matching_engine"] = self.matching_engine
        return analyze_playlist(*args, **kwargs)

    def analyze_playlists(self, *args, **kwargs) -> dict[str, Any]:
        if "db" not in kwargs:
            kwargs["db"] = self.db
        return analyze_playlists(*args, **kwargs)

    def evaluate_single_track_diagnostics(self, *args, **kwargs) -> dict[str, Any]:
        if "db" not in kwargs:
            kwargs["db"] = self.db
        if "matching_engine" not in kwargs:
            kwargs["matching_engine"] = self.matching_engine
        return evaluate_single_track_diagnostics(*args, **kwargs)

    def select_highest_quality_media(self, media_files: list[Any]) -> Any | None:
        return select_highest_quality_media(media_files)

    def queue_missing_downloads(
        self, missing: list[dict[str, Any]], target_quality: str | None = None
    ) -> dict[str, Any]:
        return queue_missing_downloads(
            missing=missing,
            target_quality=target_quality,
            download_manager=self.download_manager,
        )

    def execute_sync(
        self,
        payload: dict[str, Any],
        source: Any = "unknown",
        target: Any = None,
        playlist_name: str | None = None,
        matches: list[dict[str, Any]] | None = None,
        download_missing: bool = False,
        sync_mode: str = "local-server",
        source_account_name: str | None = None,
        target_user_id: str | int | None = None,
    ) -> dict[str, Any]:
        """
        Execute a playlist sync job against a target media server or streaming provider,
        selecting the highest-fidelity edition when multiple local media files exist,
        decoupling target_quality strictly to missing-track download queueing,
        and recording results in sync_history.
        """
        target_name = str(target or payload.get("target_source") or payload.get("target") or "")
        pl_name = str(playlist_name or payload.get("playlist_name") or "")
        match_items = list(matches if matches is not None else (payload.get("matches") or []))
        dl_missing = bool(download_missing or payload.get("download_missing", False))
        src_name = str(source or payload.get("source") or "unknown")
        target_quality = payload.get("target_quality") or payload.get("quality_profile")

        if not target_name:
            return {"accepted": False, "error": "target_source required"}
        if not pl_name:
            return {"accepted": False, "error": "playlist_name required"}

        valid_matches = [
            m
            for m in match_items
            if isinstance(m, dict)
            and (m.get("target_identifier") or m.get("matched_track_id") or m.get("track_id"))
        ]
        if not valid_matches:
            return {"accepted": False, "error": f"No {target_name} track IDs provided in matches"}

        job_name = f"sync:{target_name}:{pl_name}:{int(time.time())}"

        def _run_sync_job() -> None:
            total = len(valid_matches)
            event_bus.publish(
                job_name,
                "sync_started",
                {
                    "playlist": pl_name,
                    "target": target_name,
                    "total": total,
                    "download_missing": dl_missing,
                    "sync_mode": sync_mode,
                },
            )
            client = self._get_cached_client(target_name) or PluginRegistry.get_plugin(target_name)
            synced_keys: list[str] = []
            failed_tracks: list[dict[str, Any]] = []

            for idx, m in enumerate(valid_matches):
                tid = m.get("target_identifier") or m.get("matched_track_id") or m.get("track_id")
                track_title = m.get("source_title") or m.get("title") or "Unknown Track"
                track_artist = m.get("source_artist") or m.get("artist") or "Unknown Artist"
                event_bus.publish(
                    job_name,
                    "track_started",
                    {
                        "index": idx,
                        "track_id": str(tid),
                        "title": track_title,
                        "artist": track_artist,
                        "total": total,
                    },
                )
                try:
                    if client and hasattr(client, "add_to_playlist") and sync_mode == "tier-to-tier":
                        client.add_to_playlist(pl_name, str(tid))
                    synced_keys.append(str(tid))
                    event_bus.publish(
                        job_name,
                        "track_synced",
                        {
                            "index": idx,
                            "track_id": str(tid),
                            "title": track_title,
                            "artist": track_artist,
                        },
                    )
                except Exception as exc:
                    failed_tracks.append(
                        {
                            "index": idx + 1,
                            "track_id": str(tid),
                            "title": track_title,
                            "artist": track_artist,
                            "error": str(exc),
                        }
                    )
                    event_bus.publish(
                        job_name,
                        "track_failed",
                        {
                            "index": idx,
                            "track_id": str(tid),
                            "title": track_title,
                            "artist": track_artist,
                            "error": str(exc),
                        },
                    )

            if client and synced_keys and sync_mode != "tier-to-tier":
                if hasattr(client, "add_tracks_to_managed_playlist"):
                    client.add_tracks_to_managed_playlist(
                        pl_name,
                        synced_keys,
                        marker="⇄",
                        overwrite=True,
                        source_account_name=source_account_name,
                        target_user_id=target_user_id,
                    )
                elif hasattr(client, "add_tracks_to_playlist"):
                    client.add_tracks_to_playlist(pl_name, synced_keys)

            if dl_missing and payload.get("missing"):
                self.queue_missing_downloads(
                    payload["missing"],
                    target_quality=str(target_quality) if target_quality else None,
                )

            event_bus.publish(
                job_name,
                "sync_complete",
                {
                    "playlist": pl_name,
                    "synced": len(synced_keys),
                    "failed": len(failed_tracks),
                    "failed_tracks": failed_tracks,
                    "target": target_name,
                    "sync_mode": sync_mode,
                },
            )
            sync_history.record_sync(
                source=src_name,
                target=target_name,
                playlist=pl_name,
                total=total,
                synced=len(synced_keys),
                failed=len(failed_tracks),
                download_missing=dl_missing,
                job_name=job_name,
            )

        try:
            job_queue.register_job(
                name=job_name,
                func=_run_sync_job,
                interval_seconds=None,
                enabled=True,
                max_retries=3,
                backoff_base=5.0,
                backoff_factor=2.0,
            )
            job_queue.execute_job_now(job_name)
        except Exception as e:
            logger.error(f"Failed to schedule sync job '{job_name}': {e}")
            return {"accepted": False, "error": "Failed to schedule sync job"}

        return {
            "accepted": True,
            "job": job_name,
            "target": target_name,
            "playlist": pl_name,
            "match_count": len(valid_matches),
            "track_count": len(valid_matches),
            "sync_mode": sync_mode,
            "events_path": f"/api/v1/core/playlists/sync/events?job={quote(job_name, safe='')}",
        }

    async def sync_playlist(
        self,
        playlist: SourcePlaylist | str,
        download_missing: bool = False,
        target_quality: str | None = None,
        account_id: int | None = None,
    ) -> SyncResult:
        if isinstance(playlist, str):
            resolved = self._get_source_playlist(playlist, account_id=account_id)
            if resolved is None:
                return self._create_error_result(playlist, [f"Playlist '{playlist}' not found"])
            playlist = resolved

        if playlist.name in self.syncing_playlists:
            logger.warning(f"Sync already in progress for playlist: {playlist.name}")
            return SyncResult(
                playlist_name=playlist.name,
                total_tracks=0,
                matched_tracks=0,
                synced_tracks=0,
                downloaded_tracks=0,
                failed_tracks=0,
                sync_time=utc_now(),
                errors=[f"Sync already in progress for playlist: {playlist.name}"],
            )

        self.syncing_playlists.add(playlist.name)
        self._cancelled = False
        errors: list[str] = []

        try:
            logger.info(f"Starting sync for playlist: {playlist.name}")

            if self._cancelled:
                return self._create_error_result(playlist.name, ["Sync cancelled"])

            self._update_progress(playlist.name, "Preparing playlist sync", "", 10, 5, 1)

            if not playlist.tracks:
                errors.append(f"Playlist '{playlist.name}' has no tracks")
                return self._create_error_result(playlist.name, errors)

            if self._cancelled:
                return self._create_error_result(playlist.name, ["Sync cancelled"])

            total_tracks = len(playlist.tracks)
            media_client, server_type = self._get_active_media_client()
            self._update_progress(
                playlist.name,
                f"Matching tracks against {server_type.title()} library",
                "",
                20,
                5,
                2,
                total_tracks=total_tracks,
            )

            match_results: list[TrackMatchResult] = []
            for i, track in enumerate(playlist.tracks):
                if self._cancelled:
                    return self._create_error_result(playlist.name, ["Sync cancelled"])

                progress_percent = 20 + (40 * (i + 1) / total_tracks)
                current_track_name = (
                    f"{track.artist_name} - {track.title}" if track.artist_name else track.title
                )

                self._update_progress(
                    playlist.name,
                    "Matching tracks",
                    current_track_name,
                    progress_percent,
                    5,
                    2,
                    total_tracks=total_tracks,
                    matched_tracks=len([r for r in match_results if r.is_match]),
                    failed_tracks=len([r for r in match_results if not r.is_match]),
                )

                target_match, confidence = await self._find_track_in_media_server(track)
                match_results.append(
                    TrackMatchResult(
                        source_track=track,
                        provider_track_id=target_match,
                        confidence=confidence,
                    )
                )

            matched_tracks = [r for r in match_results if r.is_match]
            unmatched_tracks = [r for r in match_results if not r.is_match]

            if self._cancelled:
                return self._create_error_result(playlist.name, ["Sync cancelled"])

            self._update_progress(
                playlist.name,
                "Matching completed",
                "",
                60,
                5,
                3,
                total_tracks=total_tracks,
                matched_tracks=len(matched_tracks),
                failed_tracks=len(unmatched_tracks),
            )

            downloaded_tracks = 0
            if download_missing and unmatched_tracks:
                if self._cancelled:
                    return self._create_error_result(playlist.name, ["Sync cancelled"])
                self._update_progress(
                    playlist.name,
                    "Publishing download intents",
                    "",
                    70,
                    5,
                    4,
                    total_tracks=total_tracks,
                    matched_tracks=len(matched_tracks),
                    failed_tracks=len(unmatched_tracks),
                )
                downloaded_tracks = await self._publish_download_intents(
                    unmatched_tracks, target_quality=target_quality
                )

            if self._cancelled:
                return self._create_error_result(playlist.name, ["Sync cancelled"])

            media_client, server_type = self._get_active_media_client()
            self._update_progress(
                playlist.name,
                f"Creating/updating {server_type.title()} playlist",
                "",
                80,
                5,
                4,
                total_tracks=total_tracks,
                matched_tracks=len(matched_tracks),
                failed_tracks=len(unmatched_tracks),
            )

            provider_track_ids = [
                str(r.provider_track_id) for r in matched_tracks if r.provider_track_id
            ]

            if not media_client:
                logger.error("No active media client available for playlist sync")
                sync_success = False
            else:
                sync_success = bool(
                    media_client.add_tracks_to_playlist(playlist.name, provider_track_ids)
                )

            synced_tracks = len(provider_track_ids) if sync_success else 0
            failed_tracks = len(playlist.tracks) - synced_tracks - downloaded_tracks

            self._update_progress(
                playlist.name,
                "Sync completed",
                "",
                100,
                5,
                5,
                total_tracks=total_tracks,
                matched_tracks=len(matched_tracks),
                failed_tracks=failed_tracks,
            )

            try:
                sync_history.record_sync(
                    source=self._resolve_default_source_provider_name(),
                    target=server_type,
                    playlist=playlist.name,
                    total=total_tracks,
                    synced=synced_tracks,
                    failed=failed_tracks,
                    download_missing=download_missing,
                    job_name=f"sync:{server_type}:{playlist.name}",
                )
            except Exception as hist_err:
                logger.debug(f"Failed to record sync history: {hist_err}")

            return SyncResult(
                playlist_name=playlist.name,
                total_tracks=total_tracks,
                matched_tracks=len(matched_tracks),
                synced_tracks=synced_tracks,
                downloaded_tracks=downloaded_tracks,
                failed_tracks=failed_tracks,
                sync_time=utc_now(),
                errors=errors,
                wishlist_added_count=0,
            )

        except Exception as e:
            logger.error(f"Error during sync: {e}")
            errors.append(str(e))
            return self._create_error_result(playlist.name, errors)

        finally:
            self.syncing_playlists.discard(playlist.name)
            self.clear_progress_callback(playlist.name)
            self._cancelled = False

    async def _find_track_in_media_server(
        self, source_track: EchosyncTrack
    ) -> tuple[str | None, float]:
        """Find a track in the active media server using database matching."""
        try:
            media_client, server_type = self._get_active_media_client()
            if not media_client or (
                hasattr(media_client, "is_connected") and not media_client.is_connected()
            ):
                return None, 0.0

            if self._cancelled:
                return None, 0.0

            trace = self.evaluate_single_track_diagnostics(
                title=source_track.title or source_track.raw_title,
                artist=source_track.artist_name,
                duration_ms=int(source_track.duration_ms or 0),
                album=source_track.album_title,
            )
            best_match = trace.get("best_match")
            if best_match and best_match.get("accepted"):
                db_track_id = best_match.get("track_id")
                confidence = float(best_match.get("composite_score", 0.0)) / 100.0
                plugin_item_id = None
                if hasattr(self.db, "get_external_identifier_map"):
                    id_map = self.db.get_external_identifier_map(server_type, [db_track_id])
                    plugin_item_id = id_map.get(db_track_id) if isinstance(id_map, dict) else None
                elif hasattr(self.db, "get_external_identifier"):
                    plugin_item_id = self.db.get_external_identifier(server_type, db_track_id)
                else:
                    plugin_item_id = str(db_track_id)
                if not plugin_item_id:
                    return None, 0.0
                if hasattr(media_client, "get_track"):
                    validated = media_client.get_track(plugin_item_id)
                    if not validated:
                        return None, 0.0
                return str(plugin_item_id), confidence

            if hasattr(self.db, "check_track_exists"):
                db_track, confidence = self.db.check_track_exists(
                    source_track.title or source_track.raw_title,
                    source_track.artist_name,
                    confidence_threshold=0.7,
                    server_source=server_type,
                )
                if db_track and confidence >= 0.7:
                    plugin_item_id = self.db.get_external_identifier(server_type, db_track.id)
                    if not plugin_item_id:
                        return None, 0.0
                    if hasattr(media_client, "get_track") and not media_client.get_track(plugin_item_id):
                        return None, 0.0
                    return str(plugin_item_id), float(confidence)

            return None, 0.0
        except Exception as e:
            logger.error(f"Error searching for track '{source_track.title}': {e}")
            return None, 0.0

    async def sync_multiple_playlists(
        self, playlist_names: list[str], download_missing: bool = False
    ) -> list[SyncResult]:
        results = []
        for i, playlist_name in enumerate(playlist_names):
            result = await self.sync_playlist(playlist_name, download_missing)
            results.append(result)
            if i < len(playlist_names) - 1:
                await asyncio.sleep(0.01)
        return results

    def _get_source_playlist(
        self,
        playlist_name: str,
        account_id: int | None = None,
        provider_key: str | None = None,
    ) -> SourcePlaylist | None:
        """Locate a playlist by name across one or all configured provider accounts."""
        try:
            all_clients = self.get_provider_clients(provider_key)
            clients = []
            if account_id is not None:
                for c in all_clients:
                    if getattr(c, "account_id", None) == account_id:
                        clients = [c]
                        break
            if not clients:
                clients = all_clients

            for client in clients:
                try:
                    playlists = client.get_user_playlists() or []
                except Exception:
                    playlists = []
                for p in playlists:
                    if p.get("name", "").lower() == playlist_name.lower():
                        tracks = client.get_playlist_tracks(p["id"])
                        return SourcePlaylist(
                            id=p["id"],
                            name=p["name"],
                            tracks=tracks,
                            account_id=getattr(client, "account_id", account_id),
                        )
            return None
        except Exception as e:
            logger.error(f"Error fetching source playlist: {e}")
            return None

    async def _get_media_tracks(self) -> list:
        """Get tracks from the active media server."""
        server_type = "media_server"
        try:
            media_client, server_type = self._get_active_media_client()
            if not media_client:
                return []
            if hasattr(media_client, "search_tracks"):
                return media_client.search_tracks("", limit=10000)
            return []
        except Exception as e:
            logger.error(f"Error fetching {server_type} tracks: {e}")
            return []

    async def _publish_download_intents(
        self,
        unmatched_tracks: list[TrackMatchResult],
        target_quality: str | None = None,
    ) -> int:
        """Publish DOWNLOAD_INTENT events via event bus for missing tracks."""
        intent_count = 0
        for match_result in unmatched_tracks:
            try:
                source_track = match_result.source_track
                if source_track is None:
                    continue
                full_track = source_track.to_dict()
                identifiers = (
                    full_track.get("identifiers") if isinstance(full_track, dict) else {}
                )
                provider_id = None
                if isinstance(identifiers, dict) and identifiers:
                    provider_id = identifiers.get("provider_id") or next(
                        (v for v in identifiers.values() if v), None
                    )

                event_bus.publish(
                    {
                        "event": "DOWNLOAD_INTENT",
                        "sync_id": provider_id or getattr(source_track, "sync_id", None),
                        "track": full_track,
                        "fallback_metadata": full_track,
                        "duration_ms": full_track.get("duration_ms"),
                        "isrc": full_track.get("isrc"),
                        "target_quality": target_quality,
                        "timestamp": utc_isoformat(utc_now()),
                        "source": "playlist_sync",
                    }
                )
                intent_count += 1
            except Exception as e:
                logger.error(f"Error publishing DOWNLOAD_INTENT: {e}")

        return intent_count

    def _create_error_result(self, playlist_name: str, errors: list[str]) -> SyncResult:
        return SyncResult(
            playlist_name=playlist_name,
            total_tracks=0,
            matched_tracks=0,
            synced_tracks=0,
            downloaded_tracks=0,
            failed_tracks=0,
            sync_time=utc_now(),
            errors=errors,
            wishlist_added_count=0,
        )

    def get_sync_preview(
        self, playlist_name: str, account_id: int | None = None
    ) -> dict[str, Any]:
        try:
            source_playlist = self._get_source_playlist(playlist_name, account_id=account_id)
            if not source_playlist:
                return {"error": f"Playlist '{playlist_name}' not found"}

            media_client, server_type = self._get_active_media_client()
            analysis = self.analyze_playlist(
                playlist_name=source_playlist.name,
                tracks=source_playlist.tracks,
                target_source=server_type,
            )
            summary = analysis.get("summary", {})
            total = summary.get("total_tracks", 0)
            matched = summary.get("found_in_library", 0)
            pct = (matched / total * 100.0) if total > 0 else 0.0

            preview = {
                "playlist_name": playlist_name,
                "total_tracks": total,
                f"available_in_{server_type}": matched,
                "needs_download": total - matched,
                "match_percentage": round(pct, 1),
                "tracks_preview": [
                    {
                        "source_track": f"{t.get('title')} - {t.get('artist')}",
                        f"{server_type}_match": f"ID: {t.get('matched_track_id')}"
                        if t.get("matched_track_id")
                        else None,
                        "confidence": t.get("match_score", 0.0),
                        "status": "available" if t.get("matched_track_id") else "needs_download",
                    }
                    for t in analysis.get("tracks", [])[:10]
                ],
            }
            return preview
        except Exception as e:
            logger.error(f"Error generating sync preview: {e}")
            return {"error": str(e)}

    async def _get_all_source_playlists(
        self, provider_key: str | None = None
    ) -> list[SourcePlaylist]:
        """Fetch playlists from all configured and active source accounts."""
        all_playlists: list[SourcePlaylist] = []
        key = provider_key or self._resolve_default_source_provider_name()
        plugin_id = zlib.crc32(f"echosync.{key}".encode("utf-8")) & 0xFFFFFFFF
        try:
            from database.config_database import get_config_database

            config_db = get_config_database()
            service_id = config_db.get_or_create_service_id(key)
            accounts = config_db.get_accounts(service_id=service_id, is_active=True)

            if not accounts:
                client = self.get_provider_client(key)
                if client:
                    for p in client.get_user_playlists() or []:
                        all_playlists.append(
                            SourcePlaylist(
                                id=p["id"],
                                name=p["name"],
                                tracks=[],
                                account_name="Primary",
                            )
                        )
                return all_playlists

            for account in accounts:
                try:
                    account_id = account.get("id")
                    account_name = account.get("name", f"Account {account_id}")
                    client = PluginRegistry.create_instance(plugin_id, account_id=account_id)
                    if not client or (hasattr(client, "is_configured") and not client.is_configured()):
                        continue
                    for p in client.get_user_playlists() or []:
                        all_playlists.append(
                            SourcePlaylist(
                                id=p["id"],
                                name=p["name"],
                                tracks=[],
                                account_id=account_id,
                                account_name=account_name,
                            )
                        )
                except Exception as e:
                    logger.error(f"Error fetching playlists for account {account.get('id')}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error in _get_all_source_playlists: {e}")

        return all_playlists

    def refresh_playlist_cache_throttled(
        self, max_per_run: int = 5, provider_key: str | None = None
    ) -> dict[str, Any]:
        """Incrementally refresh the source playlist track cache."""
        from database.config_database import get_config_database

        summary = {
            "total": 0,
            "up_to_date": 0,
            "stale_or_missing": 0,
            "refreshed": 0,
            "remaining_for_next_run": 0,
            "errors": 0,
        }

        key = provider_key or self._resolve_default_source_provider_name()
        try:
            config_db = get_config_database()
            service_id = config_db.get_or_create_service_id(key)
            accounts = config_db.get_accounts(service_id=service_id, is_active=True) or []
        except Exception as e:
            logger.error(f"refresh_playlist_cache_throttled: failed to load accounts: {e}")
            return summary

        plugin_id = zlib.crc32(f"echosync.{key}".encode("utf-8")) & 0xFFFFFFFF
        for account in accounts:
            account_id = account.get("id")
            account_name = account.get("name", f"Account {account_id}")

            try:
                client = PluginRegistry.create_instance(plugin_id, account_id=account_id)
                if not client or (hasattr(client, "is_configured") and not client.is_configured()):
                    continue

                remote_playlists = list(client.get_user_playlists() or [])
                if not remote_playlists:
                    continue

                playlist_ids = [p["id"] for p in remote_playlists]
                cache_manager = getattr(client, "cache_manager", None)
                if cache_manager is None:
                    continue

                cached_snapshots: dict[str, str | None] = (
                    cache_manager.get_snapshot_ids_bulk(playlist_ids)
                )

                up_to_date = []
                stale_or_missing = []
                for p in remote_playlists:
                    pid = p["id"]
                    remote_snap = p.get("snapshot_id")
                    if remote_snap and cached_snapshots.get(pid) == remote_snap:
                        up_to_date.append(p)
                    else:
                        stale_or_missing.append(p)

                summary["total"] += len(remote_playlists)
                summary["up_to_date"] += len(up_to_date)
                summary["stale_or_missing"] += len(stale_or_missing)

                to_refresh = stale_or_missing[:max_per_run]
                remaining = len(stale_or_missing) - len(to_refresh)

                for p in to_refresh:
                    try:
                        client.get_playlist_tracks(p["id"], force_refresh=True)
                        summary["refreshed"] += 1
                    except Exception:
                        summary["errors"] += 1

                summary["remaining_for_next_run"] += remaining
            except Exception as account_err:
                logger.error(
                    f"refresh_playlist_cache_throttled: error for account '{account_name}': {account_err}"
                )
                summary["errors"] += 1

        return summary

    def get_library_comparison(self, provider_key: str | None = None) -> dict[str, Any]:
        try:
            from database.config_database import get_config_database

            key = provider_key or self._resolve_default_source_provider_name()
            config_db = get_config_database()
            service_id = config_db.get_or_create_service_id(key)
            accounts = config_db.get_accounts(service_id=service_id, is_active=True)

            source_playlists = []
            plugin_id = zlib.crc32(f"echosync.{key}".encode("utf-8")) & 0xFFFFFFFF

            if not accounts:
                client = self.get_provider_client(key)
                if client and (not hasattr(client, "is_configured") or client.is_configured()):
                    for p in client.get_user_playlists() or []:
                        source_playlists.append(p)
            else:
                for account in accounts:
                    try:
                        client = PluginRegistry.create_instance(
                            plugin_id, account_id=account.get("id")
                        )
                        if client and (not hasattr(client, "is_configured") or client.is_configured()):
                            for p in client.get_user_playlists() or []:
                                source_playlists.append(p)
                    except Exception:
                        continue

            source_track_count = sum(p.get("track_count", 0) for p in source_playlists)
            media_client, server_type = self._get_active_media_client()
            if not media_client:
                return {"error": "No active media client available"}

            media_playlists = (
                media_client.get_all_playlists()
                if hasattr(media_client, "get_all_playlists")
                else []
            )
            media_stats = (
                media_client.get_library_stats()
                if hasattr(media_client, "get_library_stats")
                else {}
            )

            return {
                key: {
                    "playlists": len(source_playlists),
                    "total_tracks": source_track_count,
                },
                server_type: {
                    "playlists": len(media_playlists),
                    "artists": media_stats.get("artists", 0),
                    "albums": media_stats.get("albums", 0),
                    "tracks": media_stats.get("tracks", 0),
                },
                "sync_potential": {
                    "estimated_matches": min(source_track_count, media_stats.get("tracks", 0)),
                    "potential_downloads": max(
                        0, source_track_count - media_stats.get("tracks", 0)
                    ),
                },
            }
        except Exception as e:
            logger.error(f"Error generating library comparison: {e}")
            return {"error": str(e)}

    async def sync_lightweight_batch(self, sync_ids: list[str]) -> dict[str, Any]:
        """
        Phase 2 Lightweight Syncing: Accepts an array of SyncID strings, performs a fast
        bulk diff against the database to find missing tracks, and queues missing tracks.
        """
        from database.music_database import get_database
        from database.working_database import DownloadQueue, get_working_database

        provider_name = (
            getattr(self.provider, "name", "unknown")
            if hasattr(self, "provider")
            else "unknown"
        )
        account_id = None

        if not sync_ids:
            return {"total": 0, "existing": 0, "missing": 0, "queued": 0}

        db = (
            getattr(self, "music_db", None)
            or getattr(self, "library_db", None)
            or getattr(self, "_db", None)
            or getattr(self, "music_database", None)
            or get_database()
        )

        existing_sync_ids = set()
        if hasattr(db, "get_existing_sync_ids"):
            existing_sync_ids = db.get_existing_sync_ids(sync_ids)
        elif hasattr(db, "bulk_existing_sync_ids"):
            existing_sync_ids = db.bulk_existing_sync_ids(sync_ids)
        elif hasattr(db, "fetch_existing_sync_ids"):
            existing_sync_ids = db.fetch_existing_sync_ids(sync_ids)
        else:
            with db.session_scope() as session:
                chunk_size = 500
                for i in range(0, len(sync_ids), chunk_size):
                    chunk = sync_ids[i : i + chunk_size]
                    found_tracks = (
                        session.query(Track.sync_id).filter(Track.sync_id.in_(chunk)).all()
                    )
                    for t in found_tracks:
                        if t.sync_id:
                            existing_sync_ids.add(t.sync_id)

            work_db = get_working_database()
            with work_db.session_scope() as session:
                chunk_size = 500
                for i in range(0, len(sync_ids), chunk_size):
                    chunk = sync_ids[i : i + chunk_size]
                    queued_downloads = (
                        session.query(DownloadQueue.sync_id)
                        .filter(
                            DownloadQueue.sync_id.in_(list(chunk)),
                            DownloadQueue.status.in_(["queued", "searching", "downloading"]),
                        )
                        .all()
                    )
                    for d in queued_downloads:
                        existing_sync_ids.add(d.sync_id)

        missing_sync_ids = [sid for sid in sync_ids if sid not in existing_sync_ids]
        if not missing_sync_ids:
            return {
                "total": len(sync_ids),
                "existing": len(existing_sync_ids),
                "missing": 0,
                "queued": 0,
            }

        client = (
            getattr(self, "provider", None)
            or getattr(self, "provider_client", None)
            or getattr(self, "active_provider", None)
            or getattr(self, "source_provider", None)
        )

        if not client:
            from core.nexus_framework.plugin_loader import generate_plugin_id

            p_id: Any = provider_name
            if isinstance(provider_name, str):
                if provider_name.isdigit():
                    p_id = int(provider_name)
                elif "." not in provider_name:
                    p_id = generate_plugin_id(f"echosync.{provider_name.lower()}")
                else:
                    p_id = generate_plugin_id(provider_name.lower())

            client = PluginRegistry.create_instance(p_id, account_id=account_id)

        if not client:
            return {
                "total": len(sync_ids),
                "existing": len(existing_sync_ids),
                "missing": len(missing_sync_ids),
                "queued": 0,
                "error": "Provider not configured",
            }

        queued_count = 0
        full_tracks = []
        if hasattr(client, "fetch_tracks_by_sync_ids"):
            full_tracks = client.fetch_tracks_by_sync_ids(missing_sync_ids)
        elif hasattr(client, "fetch_by_sync_ids"):
            full_tracks = client.fetch_by_sync_ids(missing_sync_ids)
        elif hasattr(client, "fetch_tracks"):
            full_tracks = client.fetch_tracks(missing_sync_ids)
        elif hasattr(client, "get_tracks_by_sync_ids"):
            full_tracks = client.get_tracks_by_sync_ids(missing_sync_ids)

        if full_tracks:
            for track in full_tracks:
                if hasattr(self, "download_manager") and self.download_manager:
                    self.download_manager.queue_download(track)
                queued_count += 1

        return {
            "total": len(sync_ids),
            "existing": len(existing_sync_ids),
            "missing": len(missing_sync_ids),
            "queued": queued_count,
        }
