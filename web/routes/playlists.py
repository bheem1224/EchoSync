import logging
import re
import time
import uuid
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from core.db.echo_sync_track import EchosyncTrack
from core.event_bus import event_bus
from core.hook_manager import hook_manager
from core.job_queue import job_queue
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.text_utils import (
    normalize_title as _normalize_candidate_title,
)
from core.personalized_playlists import get_personalized_playlists_service
from core.sync_history import sync_history
from core.tiered_logger import get_logger
from database.music_database import MusicDatabase


class PlaylistAnalyzeSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str | int | None = None
    target: str | int | None = None
    target_source: str | int | None = None
    playlists: list[Any] | None = None
    quality_profile: str | dict[str, Any] | None = "Auto"
    source_account_name: str | None = None
    target_user_id: str | int | None = None
    target_account_id: str | int | None = None


class PlaylistSyncSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    target: str | int | None = None
    target_source: str | int | None = None
    playlist_name: str | None = None
    matches: list[Any] | None = None
    download_missing: bool | None = False
    source: str | int | None = "unknown"
    source_account_name: str | None = None
    target_user_id: str | int | None = None
    target_account_id: str | int | None = None


class PlaylistDownloadMissingSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    missing: list[Any] | None = None


class PlaylistSyncScheduleSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str | int | None = None
    target: str | int | None = None
    target_source: str | int | None = None
    playlists: list[Any] | None = None
    interval: int | None = 3600
    download_missing: bool | None = False
    enabled: bool | None = True
    source_account_name: str | None = None
    target_user_id: str | int | None = None
    target_account_id: str | int | None = None


class MatchDiagnosticRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    artist: str
    duration_ms: int = 0
    album: str | None = None


# In-memory store for ad-hoc analysis jobs started via API
ANALYSIS_JOBS = {}

logger = get_logger("playlists_api")
router = APIRouter(prefix="/api/v1/core/playlists", tags=["Playlists"])
api_v1_router = APIRouter(prefix="/api/v1/playlists", tags=["Playlists"])
legacy_router = APIRouter(prefix="/api/playlists", tags=["Playlists"])
double_v1_router = APIRouter(prefix="/api/v1/v1/core/playlists", tags=["Playlists"])

# ── Semantic Substring Failsafe — safe OST filler dictionary ──────────────────
# Words that commonly appear in longer CJK/English OST title variants but do NOT
# change the track's identity.  If a title delta (the extra part of the longer
# string after the shared shorter title is removed) is composed *entirely* of
# these words the two strings refer to the same track and a 0.95 title score is
# awarded.  Any unrecognised token (e.g. 'Part 2', 'Remix', 'Live') causes the
# substring boost to be withheld, preventing false-positive Swap Cases.
_OST_SAFE_WORDS = {
    "电视剧",
    "网剧",
    "影视剧",
    "影視劇",
    "电影",
    "片头曲",
    "片尾曲",
    "主题曲",
    "插曲",
    "推广曲",
    "原声带",
    "原声",
    "配乐",
    "ost",
    "theme",
    "opening",
    "ending",
    "soundtrack",
    "original",
    "remastered",
    "remaster",
    "acoustic",
    "live",
    "radio",
    "single",
    "extended",
    "club",
    "version",
    "edit",
    "mix",
    "remix",
    "bootleg",
    "official",
    "song",
    "shanty",
    "sea",
    "uefa",
    "euro",
    "anthem",
    "from",
    "la",
    "deluxe",
    "pt",
    "part",
    "vol",
    "volume",
    "viii",
    "vii",
    "iii",
    "iv",
    "vi",
    "ix",
    "ii",
    "i",
    "x",
    "v",
    "gabry",
    "ponte",
    "ice",
    "pop",
}


class _OstSafeMatcher:
    def match(self, text: str):
        if not text:
            return None
        s = re.sub(r"[\s\-_]+", "", str(text).lower())
        if not s:
            return True
        n = len(s)
        dp = [False] * (n + 1)
        dp[0] = True
        for i in range(n):
            if not dp[i]:
                continue
            if s[i].isdigit():
                dp[i + 1] = True
            for w in _OST_SAFE_WORDS:
                if s.startswith(w, i):
                    dp[i + len(w)] = True
        return True if dp[n] else None


_OST_SAFE_RE = _OstSafeMatcher()
# ──────────────────────────────────────────────────────────────────────────────

# ── Pinyin artist-matching constants ─────────────────────────────────────────
# When the best artist score after primary-name + alias checks is still below
# _PINYIN_ARTIST_THRESHOLD, a Hanzi → Pinyin transliteration fallback is tried.
# _PINYIN_ARTIST_PASS is the minimum token_sort_ratio (0–100) required for that
# fallback to override the alias-based score and accept the match.
_PINYIN_ARTIST_THRESHOLD = 0.85  # only enter Pinyin path when score is below this
_PINYIN_ARTIST_PASS = 90  # token_sort_ratio needed to accept the match
# ──────────────────────────────────────────────────────────────────────────────


def _get_provider_for_account(provider_id, acc_id=None):
    from core.nexus_framework.plugin_loader import (
        PluginRegistry,
        generate_plugin_id,
        get_plugin_capabilities,
    )

    # Handle if a string was passed for backward compatibility, though it should be an int
    if isinstance(provider_id, str):
        if provider_id.isdigit():
            provider_id = int(provider_id)
        else:
            # Try to match a registered plugin name ending with the string
            found = False
            for p_id, p_cls in PluginRegistry._plugins.items():
                if hasattr(p_cls, "name") and p_cls.name and p_cls.name.lower().endswith(provider_id.lower()):
                    provider_id = p_id
                    found = True
                    break
            if not found:
                provider_id = generate_plugin_id(provider_id.lower())

    try:
        plugin_class = PluginRegistry.get_plugin_class(provider_id)
        if not plugin_class:
            return None, None

        caps = get_plugin_capabilities(provider_id)

        if getattr(caps, "supports_user_auth", False):
            if acc_id is None:
                from services.storage_service import get_storage_service

                storage = get_storage_service()

                # We need to find an account for this plugin. Use the stringified provider_id
                accounts = storage.list_accounts(str(provider_id))
                if not accounts:
                    return None, None
                acc_id_local = accounts[0]["id"]
            else:
                acc_id_local = acc_id

            return plugin_class(account_id=acc_id_local), acc_id_local

        return PluginRegistry.create_instance(provider_id), None
    except Exception:
        import traceback

        traceback.print_exc()
        return None, None


def _normalize_provider_short_name(provider_id: Any) -> str:
    """Normalize provider identifier (numeric string/int, full plugin name) to canonical short name (e.g. 'plex', 'spotify')."""
    if not provider_id:
        return ""
    from core.nexus_framework.plugin_loader import PluginRegistry

    try:
        p_cls = PluginRegistry.get_plugin_class(provider_id)
        if p_cls and hasattr(p_cls, "name") and p_cls.name:
            return p_cls.name.lower().split(".")[-1]
    except Exception:
        pass

    p_str = str(provider_id).strip()
    if p_str.isdigit():
        try:
            from database.config_database import get_config_database

            cfg_db = get_config_database()
            with cfg_db._get_connection() as conn:
                row = conn.execute(
                    "SELECT s.name FROM accounts a JOIN services s ON a.service_id = s.id WHERE a.id = ?",
                    (int(p_str),),
                ).fetchone()
                if row and row[0]:
                    return str(row[0]).lower().split(".")[-1]
        except Exception:
            pass

    if p_str.lower().startswith("echosync."):
        return p_str.lower().split(".")[-1]
    return p_str.lower()


def _extract_track_field(track, key):
    if isinstance(track, dict):
        return track.get(key)
    return getattr(track, key, None)


def _extract_target_identifier(candidate):
    if isinstance(candidate, dict):
        return candidate.get("id") or candidate.get("target_identifier")

    identifiers = getattr(candidate, "identifiers", {}) or {}
    for key in ("plex", "spotify_id", "tidal_id", "id"):
        if key in identifiers:
            return identifiers.get(key)

    return getattr(candidate, "id", None)


def _cmp_titles(
    a: str,
    b: str,
    context_score: float = 0.0,
    drama_ctx: bool = False,
) -> float:
    """Lightweight title similarity score (0–1), matching the engine's _fuzzy_match logic.

    Lowercases, strips non-word/non-space characters, collapses whitespace, then runs
    SequenceMatcher.  Used to pick the best candidate title or alias before scoring.

    Semantic Substring Failsafe (Step 4 of the matching pipeline):
      When the plain fuzzy ratio falls below 0.90 *and* we have a confident artist
      or drama-context match (`context_score >= 0.80` or `drama_ctx=True`), the
      function checks whether the shorter normalised title is a whole-word substring
      of the longer one.  If yes, the "delta" (the extra characters in the longer
      string) is extracted and validated against `_OST_SAFE_RE`:
        • Delta is entirely safe OST filler ⇒ title_score forced to 0.95.
        • Delta contains ANY unrecognised token (e.g. 'Part 2', 'Remix', 'Live')
          ⇒ substring boost is withheld; the plain ratio is returned, preventing a
          false-positive Swap Case (e.g. matching Part 1 instead of Part 2).
    """

    def _n(s: str) -> str:
        s = s.lower()
        s = re.sub(r"[^\w\s]", "", s)
        return " ".join(s.split())

    a_n, b_n = _n(a), _n(b)
    if not a_n or not b_n:
        return 0.0
    ratio = SequenceMatcher(None, a_n, b_n).ratio()

    # ── Semantic Substring Failsafe ───────────────────────────────────────────
    # Only activate when the plain ratio hasn't already passed AND we have a
    # confident external signal (artist similarity ≥ 80% OR drama context hit)
    # to guard against unrelated short-title collisions.
    if ratio < 0.90 and (context_score >= 0.80 or drama_ctx):
        shorter, longer = (a_n, b_n) if len(a_n) <= len(b_n) else (b_n, a_n)
        if len(shorter) >= 3 and re.search(r"(?<![\w])" + re.escape(shorter) + r"(?![\w])", longer):
            # Extract delta: strip the shared prefix and collapse leftover whitespace.
            delta_raw = re.sub(r"(?<![\w])" + re.escape(shorter) + r"(?![\w])", "", longer, count=1)
            # Strip ALL punctuation and separators; keep only word characters.
            delta_words = re.sub(r"[^\w]", "", delta_raw, flags=re.UNICODE)
            if not delta_words:
                # Delta is purely separators / punctuation — same track.
                logger.debug(
                    "Substring failsafe: '%s' ⊂ '%s' — delta is empty after strip → score=0.95",
                    shorter,
                    longer,
                )
                ratio = 0.95
            elif _OST_SAFE_RE.match(delta_words):
                # Delta is composed entirely of safe OST filler tokens.
                logger.debug(
                    "Substring failsafe: '%s' ⊂ '%s' — delta '%s' is safe filler → score=0.95",
                    shorter,
                    longer,
                    delta_words,
                )
                ratio = 0.95
            else:
                # Delta contains unrecognised text — do NOT boost; prevents Swap Cases.
                logger.debug(
                    "Substring failsafe: '%s' ⊂ '%s' — delta '%s' contains unrecognised token "
                    "→ rejecting substring match",
                    shorter,
                    longer,
                    delta_words,
                )
    # ── End Semantic Substring Failsafe ──────────────────────────────────────

    return ratio


_TRIBUTE_DELTA_TOKENS = {
    "tribute",
    "tribute band",
    "cover band",
    "karaoke",
    "sound-alike",
    "soundalike",
    "parody",
    "style of",
    "in the style of",
    "celebration",
    "orchestra",
    "instrumental version",
    "piano tribute",
}


def _cmp_artists(a: str, b: str) -> float:
    """Artist similarity score (0–1) with hardened substring-containment boost.

    Normalises both strings identically to _cmp_titles, then returns the
    SequenceMatcher ratio OR 0.95 (whichever is higher) when one normalised
    form is fully contained in the other, UNLESS the delta difference contains
    tribute/cover/karaoke qualifiers (e.g. 'The Maroon 5 Tribute Band' vs 'Maroon 5').
    """

    def _n(s: str) -> str:
        s = s.lower()
        s = re.sub(r"[^\w\s]", "", s)
        return " ".join(s.split())

    a_n, b_n = _n(a), _n(b)
    if not a_n or not b_n:
        return 0.0
    if a_n == b_n:
        return 1.0

    from core.matching_engine.text_utils import is_franchise_entity

    if is_franchise_entity(a) or is_franchise_entity(b):
        return 0.90

    ratio = SequenceMatcher(None, a_n, b_n).ratio()
    if a_n in b_n or b_n in a_n:
        shorter, longer = (a_n, b_n) if len(a_n) < len(b_n) else (b_n, a_n)
        delta = re.sub(r"(?<![\w])" + re.escape(shorter) + r"(?![\w])", "", longer).strip()
        delta_lower = delta.lower()
        delta_tokens = set(re.findall(r"\b\w+\b", delta_lower))

        has_tribute = any(t in delta_lower or t in delta_tokens for t in _TRIBUTE_DELTA_TOKENS)
        if not has_tribute:
            return max(ratio, 0.95)

    return ratio


def _fetch_tier1_candidates(conn, search_title, base_search_title, track_artist, track_duration):
    """Execute the Tier 1 artist+title candidate query with search-expansion hook support.

    Fires the ``search_expansion`` hook to collect plugin-provided alternative
    search strings (e.g. Pinyin / Romaji transliterations from the CJK plugin),
    then runs a single SQL query that matches against Track.title,
    Track.sort_title, and track_aliases.name.  The artist-anchored conditions
    are preserved for the default terms; expanded terms are searched without an
    artist anchor to handle 'Various Artists' and similar mis-tagged libraries.

    Returns a list of unique row tuples: (id, title, duration, edition,
    artist_name, artist_id, sort_title, album_title).
    """
    from sqlalchemy import text as _sql

    # Request plugin-provided alternative search strings.
    expanded_terms = hook_manager.apply_filters(
        "search_expansion",
        [],
        title=search_title,
        artist=track_artist,
    )
    if not isinstance(expanded_terms, list):
        expanded_terms = []

    # Deduplicate expanded terms; skip strings already covered by the base search.
    seen_terms = {search_title.lower(), base_search_title.lower()}
    clean_expanded = []
    for t in expanded_terms:
        if isinstance(t, str) and t.strip() and t.strip().lower() not in seen_terms:
            seen_terms.add(t.strip().lower())
            clean_expanded.append(t.strip())

    title_norm = search_title.replace("\u2019", "'").replace("\u2018", "'")

    from core.matching_engine.text_utils import normalize_title

    norm_search = normalize_title(search_title)
    params = {
        "artist_exact": track_artist,
        "artist_pattern": f"%{track_artist}%",
        "title_exact": search_title,
        "title_pattern": f"%{search_title}%",
        "base_title_pattern": f"%{base_search_title}%",
        "title_norm_pattern": f"%{title_norm}%",
        "norm_search_pattern": f"%{norm_search}%",
        "duration": track_duration or 0,
    }

    # Returns an alias-aware LIKE fragment for a named SQL parameter.
    # Matches Track.title, Track.sort_title, Track.normalized_title, or any track_aliases.name row.
    def _am(param):
        return (
            f"(LOWER(t.title) LIKE LOWER(:{param})"
            f" OR (t.sort_title IS NOT NULL AND LOWER(t.sort_title) LIKE LOWER(:{param}))"
            f" OR (t.normalized_title IS NOT NULL AND LOWER(t.normalized_title) LIKE LOWER(:{param}))"
            f" OR EXISTS (SELECT 1 FROM track_aliases ta_x"
            f" WHERE ta_x.track_id = t.id AND LOWER(ta_x.name) LIKE LOWER(:{param})))"
        )

    # Broad Funnel: match title/aliases loosely, completely ignoring artist and duration filters in WHERE.
    base_where = (
        f"{_am('title_pattern')}\n"
        f"        OR {_am('base_title_pattern')}\n"
        f"        OR {_am('norm_search_pattern')}\n"
        f"        OR (LOWER(REPLACE(REPLACE(t.title, char(8217), char(39)), char(8216), char(39)))"
        f" LIKE LOWER(:title_norm_pattern))"
    )

    # Plugin-expanded terms: no artist anchor — covers 'Various Artists' mis-tags.
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

    sql = _sql(f"""
        SELECT DISTINCT t.id, t.title, t.duration, t.edition,
               a.name AS artist_name, a.id AS artist_id,
               t.sort_title, al.title AS album_title, lm.file_path
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


def _fetch_tier2_candidates(conn, search_title, track_duration, duration_window_ms):
    """Execute the Tier 2 title-exact + duration-window query with alias support.

    Fires the ``search_expansion`` hook so that transliterated strings returned
    by plugins are also matched against Track.title, Track.sort_title, and
    track_aliases.name with LIKE (transliterations are rarely exact-match).
    The base title-exact conditions retain the original strict equality so non-CJK
    tracks are unaffected.

    Returns a list of unique row tuples compatible with the existing candidate loop.
    """
    from sqlalchemy import text as _sql

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

    duration_min = track_duration - duration_window_ms
    duration_max = track_duration + duration_window_ms

    from core.matching_engine.text_utils import normalize_title

    norm_search = normalize_title(search_title)
    params = {
        "title_exact": search_title,
        "title_pattern": f"%{search_title}%",
        "norm_search_pattern": f"%{norm_search}%",
        "duration": track_duration,
    }

    # Base title-exact conditions (original Tier 2) replaced with broad funnel LIKE/alias checks.
    base_where = (
        "LOWER(t.title) LIKE LOWER(:title_pattern)\n"
        "        OR (t.sort_title IS NOT NULL AND LOWER(t.sort_title) LIKE LOWER(:title_pattern))\n"
        "        OR (t.normalized_title IS NOT NULL AND LOWER(t.normalized_title) LIKE LOWER(:norm_search_pattern))\n"
        "        OR EXISTS (SELECT 1 FROM track_aliases ta_x\n"
        "                   WHERE ta_x.track_id = t.id AND (LOWER(ta_x.name) LIKE LOWER(:title_pattern) OR LOWER(ta_x.name) LIKE LOWER(:norm_search_pattern)))"
    )

    # Expanded terms use LIKE — transliterations need fuzzy title matching.
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

    sql = _sql(f"""
        SELECT DISTINCT t.id, t.title, t.duration, t.edition,
               a.name AS artist_name, a.id AS artist_id,
               t.sort_title, al.title AS album_title, lm.file_path
        FROM tracks t
        JOIN artists a ON t.artist_id = a.id
        LEFT JOIN albums al ON t.album_id = al.id
        JOIN local_media lm ON t.id = lm.track_id
        WHERE ({base_where}{exp_where})
        ORDER BY ABS(t.duration - :duration) ASC
        LIMIT 30
    """)

    return conn.execute(sql, params).fetchall()


def _analyze_playlists_internal(source, target_source, playlists, quality_profile="Auto"):
    """Run the canonical playlist matching flow used by both manual and scheduled syncs."""
    from services.playlist_sync import analyze_playlists

    return analyze_playlists(source, target_source, playlists, target_quality=quality_profile)


@router.get("/")
def list_playlists(request: Request):
    # Placeholder: surface playlists via provider adapters (future)
    return {"items": [], "total": 0}


@router.post("/analyze")
def analyze_playlists(payload_obj: PlaylistAnalyzeSchema | None = None):
    """Analyze playlists: fetch real tracks from source provider and check against database using WeightedMatchingEngine."""
    payload = payload_obj.model_dump(exclude_unset=True) if payload_obj else {}
    source = str(payload.get("source")) if payload.get("source") is not None else None
    target = str(payload.get("target")) if payload.get("target") is not None else None
    target_source = str(payload.get("target_source")) if payload.get("target_source") is not None else target
    playlists = payload.get("playlists") or []
    quality_profile = payload.get("quality_profile", "Auto")

    if not source:
        return {"error": "source provider required"}

    if not playlists:
        return {"error": "playlists list required"}

    try:
        result = _analyze_playlists_internal(source, target_source, playlists, quality_profile)
        return result
    except Exception as e:
        logger.error(f"Error analyzing playlists: {e}", exc_info=True)
        return {"error": "Playlist analysis failed"}


@router.post("/match-diagnostics")
@api_v1_router.post("/match-diagnostics")
@legacy_router.post("/match-diagnostics")
@double_v1_router.post("/match-diagnostics")
def match_diagnostics(payload: MatchDiagnosticRequest):
    """Evaluate candidate tracks against ExactSyncProfile and return structured match trace."""
    from services.playlist_sync import evaluate_single_track_diagnostics, get_cached_match_trace

    query_title = (payload.title or "").strip()
    query_artist = (payload.artist or "").strip()
    query_duration = int(payload.duration_ms or 0)
    query_album = (payload.album or "").strip()

    cached = get_cached_match_trace(query_title, query_artist, query_duration, query_album)
    if cached is not None:
        return cached

    return evaluate_single_track_diagnostics(
        title=query_title,
        artist=query_artist,
        duration_ms=query_duration,
        album=query_album,
    )


@router.post("/analyze/start")
def start_analyze_job(payload_obj: PlaylistAnalyzeSchema | None = None):
    """Start playlist analysis as a background job and return a job_id to poll."""
    payload = payload_obj.model_dump(exclude_unset=True) if payload_obj else {}
    source = str(payload.get("source")) if payload.get("source") is not None else None
    target = str(payload.get("target")) if payload.get("target") is not None else None
    target_source = str(payload.get("target_source")) if payload.get("target_source") is not None else target
    playlists = payload.get("playlists") or []
    quality_profile = payload.get("quality_profile", "Auto")

    if not source:
        return {"error": "source provider required"}
    if not playlists:
        return {"error": "playlists list required"}

    job_id = str(uuid.uuid4())
    job_name = f"playlist_analyze:{job_id}"

    # Initialize job record
    ANALYSIS_JOBS[job_id] = {
        "status": "queued",
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
    }

    def _job_func():
        ANALYSIS_JOBS[job_id]["status"] = "running"
        ANALYSIS_JOBS[job_id]["started_at"] = time.time()
        try:
            res = _analyze_playlists_internal(source, target_source, playlists, quality_profile)
            ANALYSIS_JOBS[job_id]["result"] = res
            ANALYSIS_JOBS[job_id]["status"] = "finished"
        except Exception as e:
            logger.error(f"Background analysis job {job_id} failed: {e}", exc_info=True)
            ANALYSIS_JOBS[job_id]["error"] = "Playlist analysis failed"
            ANALYSIS_JOBS[job_id]["status"] = "failed"
        finally:
            ANALYSIS_JOBS[job_id]["finished_at"] = time.time()

    # Register a one-off job and execute it immediately
    from core.nexus_framework.plugin_loader import get_plugin_capabilities

    source_caps = get_plugin_capabilities(source)
    if not source_caps:
        return {"error": f"Source plugin {source} not found"}

    target_caps = get_plugin_capabilities(target)

    try:
        job_queue.register_job(job_name, _job_func, interval_seconds=None, start_after=0, enabled=True)
        job_queue.execute_job_now(job_name)
    except Exception as e:
        logger.error(f"Failed to start background analysis job: {e}")
        return {"error": "failed to start background job"}

    return {"accepted": True, "job_id": job_id, "job_name": job_name}


@router.get("/analyze/{job_id}")
def get_analyze_job(job_id, request: Request):
    rec = ANALYSIS_JOBS.get(job_id)
    if not rec:
        return {"error": "job not found"}
    # Do not leak large results unnecessarily; include result when finished
    payload = {
        "status": rec.get("status"),
        "started_at": rec.get("started_at"),
        "finished_at": rec.get("finished_at"),
        "error": rec.get("error"),
    }
    if rec.get("status") == "finished":
        payload["result"] = rec.get("result")
    return payload


@router.post("/sync")
def trigger_sync(payload_obj: PlaylistSyncSchema):
    payload = payload_obj.model_dump(exclude_unset=True) if hasattr(payload_obj, "model_dump") else (payload_obj or {})
    target = payload.get("target_source") or payload.get("target")
    playlist_name = payload.get("playlist_name")
    matches = payload.get("matches") or []
    download_missing = payload.get("download_missing", False)
    source = payload.get("source", "unknown")

    if not target:
        return {"accepted": False, "error": "target_source required"}

    if not playlist_name:
        return {"accepted": False, "error": "playlist_name required"}

    from core.nexus_framework.plugin_loader import get_plugin_capabilities
    from core.nexus_framework.plugin_SDK import PlaylistSupport

    try:
        source_caps = get_plugin_capabilities(source)
        if source_caps.supports_playlists not in (
            PlaylistSupport.READ,
            PlaylistSupport.READ_WRITE,
        ):
            return {
                "accepted": False,
                "error": f"Source provider {source} does not support reading playlists",
            }
    except KeyError:
        return {"accepted": False, "error": f"Source provider {source} not found"}

    try:
        target_caps = get_plugin_capabilities(target)
        if target_caps.supports_playlists != PlaylistSupport.READ_WRITE:
            return {
                "accepted": False,
                "error": f"Target provider {target} does not support writing playlists",
            }
    except KeyError:
        return {"accepted": False, "error": f"Target provider {target} not found"}

    # Detect sync mode: tier-to-tier (streaming↔streaming) vs local-server (streaming→server)
    is_source_tier = getattr(source_caps, "supports_streaming", False)
    is_target_tier = getattr(target_caps, "supports_streaming", False)
    is_source_server = getattr(source_caps, "supports_library_scan", False)
    is_target_server = getattr(target_caps, "supports_library_scan", False)

    sync_mode = None
    if is_source_tier and is_target_tier:
        sync_mode = "tier-to-tier"
    elif is_source_tier and is_target_server:
        sync_mode = "local-server"
    elif is_source_server and is_target_tier:
        sync_mode = "server-to-tier"
    else:
        sync_mode = "unknown"

    tier_to_tier_providers = {"spotify", "tidal", "apple_music", "deezer", "qobuz"}

    # For non-Plex targets, return not implemented
    canonical_target = _normalize_provider_short_name(target)
    if canonical_target == "plex" or target == "plex":
        # Local-server sync: add tracks to managed playlist with overwrite
        source_account_name = payload.get("source_account_name")
        target_user_id = payload.get("target_user_id")
        return _sync_to_plex(
            payload,
            source,
            target,
            playlist_name,
            matches,
            download_missing,
            sync_mode,
            source_account_name,
            target_user_id,
        )
    elif target in tier_to_tier_providers or canonical_target in tier_to_tier_providers:
        # Tier-to-tier sync: add tracks to target provider's playlist
        return _sync_to_tier(
            payload,
            source,
            canonical_target,
            playlist_name,
            matches,
            download_missing,
            sync_mode,
        )
    else:
        return {"accepted": False, "error": f"Sync to {target} not implemented"}


def _sync_to_plex(
    payload,
    source,
    target,
    playlist_name,
    matches,
    download_missing,
    sync_mode,
    source_account_name=None,
    target_user_id=None,
):
    """Sync matched tracks to a Plex managed playlist."""
    # Collect ratingKeys from matches (target_identifier)
    rating_keys = [m.get("target_identifier") for m in matches if m.get("target_identifier")]
    if not rating_keys:
        return {"accepted": False, "error": "No Plex ratingKeys provided in matches"}

    # Schedule a one-off sync job with retry/backoff
    job_name = f"sync:plex:{playlist_name}:{int(time.time())}"

    def _run_sync():
        marker = "⇄"
        total = len(rating_keys)
        logger.info(
            f"[{job_name}] Starting Plex sync for playlist '{playlist_name}' with {total} tracks "
            f"(target_user_id='{target_user_id}', source_account_name='{source_account_name}')"
        )
        event_bus.publish(
            job_name,
            "sync_started",
            {
                "playlist": playlist_name,
                "target": target,
                "total": total,
                "download_missing": download_missing,
                "sync_mode": sync_mode,
            },
        )

        target_account_id = None
        if payload.get("target_account_id"):
            try:
                target_account_id = int(payload.get("target_account_id"))
            except Exception:
                pass
        elif str(target).isdigit() and int(target) < 2000000000:
            target_account_id = int(target)

        client = None
        try:
            from plugins.EchoSync.plex.client import PlexClient

            client = PlexClient(account_id=target_account_id)
        except ImportError:
            try:
                from core.nexus_framework.plugin_loader import PluginRegistry

                PlexCls = PluginRegistry.get_plugin_class("EchoSync.plex") or PluginRegistry.get_plugin_class("plex")
                if PlexCls:
                    client = PlexCls(account_id=target_account_id)
                else:
                    client = PluginRegistry.get_plugin_instance("EchoSync.plex") or PluginRegistry.get_plugin_instance(
                        "plex"
                    )
            except Exception as reg_err:
                logger.warning(f"PluginRegistry resolution of Plex failed: {reg_err}")

        if not client:
            err_msg = "Plex plugin is disabled, unconfigured, or could not be loaded"
            logger.error(f"[{job_name}] {err_msg}")
            event_bus.publish(
                job_name,
                "sync_failed",
                {
                    "playlist": playlist_name,
                    "error": err_msg,
                },
            )
            return

        try:
            if not client.ensure_connection():
                raise RuntimeError("Plex connection failed")

            valid_match_items = [
                m for m in matches if m.get("target_identifier") or m.get("matched_track_id") or m.get("track_id")
            ]
            valid_keys = []
            failed_tracks = []
            recovered_keys = []

            # Pre-fetch local track, artist, and media data to guarantee telemetry for live recovery
            matched_track_ids = []
            for m in valid_match_items:
                tid = m.get("matched_track_id") if m.get("matched_track_id") is not None else m.get("track_id")
                if tid is not None and str(tid).isdigit():
                    matched_track_ids.append(int(tid))

            track_info_map = {}
            if matched_track_ids:
                try:
                    from database.music_database import (
                        Artist,
                        LocalMedia,
                        Track,
                        get_database,
                    )

                    db = get_database()
                    with db.session_scope() as session:
                        rows = (
                            session.query(Track, Artist, LocalMedia)
                            .outerjoin(Artist, Track.artist_id == Artist.id)
                            .outerjoin(LocalMedia, Track.id == LocalMedia.track_id)
                            .filter(Track.id.in_(matched_track_ids))
                            .all()
                        )
                        for t, a, lm in rows:
                            track_info_map[t.id] = {
                                "title": t.title,
                                "artist": a.name if a else "Unknown Artist",
                                "album": t.album.title if getattr(t, "album", None) else "",
                                "duration": t.duration or 0,
                                "file_path": lm.file_path if lm else None,
                                "media_id": lm.media_id if lm else None,
                            }
                except Exception as pre_err:
                    logger.debug(f"Failed to prefetch Track/LocalMedia for sync recovery: {pre_err}")

            from core.db.echo_sync_track import EchosyncMedia, EchosyncTrack

            for idx, m in enumerate(valid_match_items):
                rk = m.get("target_identifier")
                matched_t_id = m.get("matched_track_id") if m.get("matched_track_id") is not None else m.get("track_id")
                if matched_t_id is not None and str(matched_t_id).isdigit():
                    matched_t_id = int(matched_t_id)

                db_info = track_info_map.get(matched_t_id) if matched_t_id else {}

                track_title = (
                    m.get("source_title")
                    or m.get("title")
                    or (m.get("source_track") or {}).get("title")
                    or (m.get("source_track") or {}).get("name")
                    or db_info.get("title")
                    or "Unknown Track"
                )
                track_artist = (
                    m.get("source_artist")
                    or m.get("artist")
                    or (m.get("source_track") or {}).get("artist")
                    or db_info.get("artist")
                    or "Unknown Artist"
                )
                track_album = m.get("album") or (m.get("source_track") or {}).get("album") or db_info.get("album") or ""
                track_duration = (
                    m.get("duration_ms")
                    or (m.get("source_track") or {}).get("duration_ms")
                    or db_info.get("duration")
                    or 0
                )

                local_file_path = db_info.get("file_path")
                local_media_id = db_info.get("media_id")

                local_media_list = (
                    [EchosyncMedia(file_path=local_file_path, media_id=local_media_id)] if local_file_path else []
                )
                local_track_meta = EchosyncTrack(
                    raw_title=track_title,
                    artist_name=track_artist,
                    album_title=track_album or "",
                    duration=track_duration,
                    media=local_media_list,
                )

                logger.debug(
                    f"[{job_name}] Processing track {idx + 1}/{total} (ratingKey: {rk}, title: '{track_title}', artist: '{track_artist}')"
                )
                event_bus.publish(
                    job_name,
                    "track_started",
                    {
                        "index": idx,
                        "rating_key": rk,
                        "title": track_title,
                        "artist": track_artist,
                        "total": total,
                    },
                )
                try:
                    # Attempt fetch with live recovery fallback on 404/NotFound
                    item = None
                    is_recovered = False
                    if hasattr(client, "fetch_or_recover_track"):
                        item, is_recovered = client.fetch_or_recover_track(rk, local_track_meta)
                    elif client.server:
                        try:
                            rk_int = int(rk) if rk else None
                            item = client.server.fetchItem(rk_int) if rk_int else None
                        except Exception:
                            item = None

                    if not item:
                        raise RuntimeError(
                            f"Track '{track_title}' with ratingKey {rk} not found on Plex (404/unrecoverable)"
                        )

                    resolved_rk = str(getattr(item, "ratingKey", rk))
                    valid_keys.append(resolved_rk)

                    if is_recovered:
                        recovered_keys.append(
                            (
                                local_media_id or matched_t_id or local_file_path,
                                resolved_rk,
                            )
                        )

                    logger.debug(
                        f"[{job_name}] Track {idx + 1} synced successfully (key: {resolved_rk}, recovered: {is_recovered})"
                    )
                    event_bus.publish(
                        job_name,
                        "track_synced",
                        {
                            "index": idx,
                            "rating_key": resolved_rk,
                            "title": track_title,
                            "artist": track_artist,
                            "recovered": is_recovered,
                        },
                    )
                except Exception as fe:
                    err_msg = str(fe)
                    logger.warning(
                        f"[{job_name}] Track {idx + 1} failed: '{track_title}' by '{track_artist}' (ratingKey: {rk}) -> {err_msg}"
                    )
                    failed_tracks.append(
                        {
                            "index": idx + 1,
                            "rating_key": rk,
                            "title": track_title,
                            "artist": track_artist,
                            "error": err_msg,
                        }
                    )
                    event_bus.publish(
                        job_name,
                        "track_failed",
                        {
                            "index": idx,
                            "rating_key": rk,
                            "title": track_title,
                            "artist": track_artist,
                            "error": err_msg,
                        },
                    )

            if not valid_keys:
                raise RuntimeError("No valid Plex items resolved for playlist sync")

            # Local-server sync: overwrite managed playlist
            logger.info(f"[{job_name}] Creating/updating managed playlist with {len(valid_keys)} tracks")
            updated = client.add_tracks_to_managed_playlist(
                playlist_name,
                valid_keys,
                marker=marker,
                overwrite=True,
                source_account_name=source_account_name,
                target_user_id=target_user_id,
            )
            event_bus.publish(
                job_name,
                "playlist_updated",
                {
                    "playlist": playlist_name,
                    "synced": len(valid_keys),
                    "failed": len(failed_tracks),
                    "updated": bool(updated),
                },
            )

            # Batch persist recovered rating keys to database
            if recovered_keys:
                try:
                    from core.database.repositories.track_repo import TrackRepository
                    from database.music_database import get_database

                    db = get_database()
                    with db.session_scope() as session:
                        persisted = TrackRepository.update_external_identifiers(
                            session,
                            recovered_keys,
                            provider="plex",
                        )
                        logger.info(
                            f"[{job_name}] Batch persisted {persisted} recovered Plex ratingKey external identifiers to database."
                        )
                except Exception as persist_err:
                    logger.warning(f"[{job_name}] Failed to persist recovered ratingKeys to database: {persist_err}")

            try:
                from core.hook_manager import hook_manager

                hook_manager.apply_filters(
                    "ON_PLAYLIST_SAVED",
                    None,
                    playlist_name=playlist_name,
                    target=target,
                    synced_count=len(valid_keys),
                )
            except Exception as e:
                logger.error(f"Error in ON_PLAYLIST_SAVED hook: {e}")

            if failed_tracks:
                summary_lines = [
                    f"[{job_name}] Sync completed with {len(failed_tracks)} failed tracks (out of {total} requested):"
                ]
                for f in failed_tracks:
                    summary_lines.append(
                        f"  • [Track #{f['index']}] '{f['title']}' by '{f['artist']}' (ratingKey: {f['rating_key']}) -> Error: {f['error']}"
                    )
                logger.warning("\n".join(summary_lines))
            else:
                logger.info(f"[{job_name}] All {len(valid_keys)}/{total} tracks synced successfully to Plex!")

            logger.info(f"[{job_name}] Sync complete: {len(valid_keys)} synced, {len(failed_tracks)} failed")
            event_bus.publish(
                job_name,
                "sync_complete",
                {
                    "playlist": playlist_name,
                    "synced": len(valid_keys),
                    "failed": len(failed_tracks),
                    "failed_tracks": failed_tracks,
                    "target": target,
                    "sync_mode": sync_mode,
                },
            )

            # Record in history
            sync_history.record_sync(
                source=source,
                target=target,
                playlist=playlist_name,
                total=total,
                synced=len(valid_keys),
                failed=len(failed_tracks),
                download_missing=download_missing,
                job_name=job_name,
            )
        except Exception as e:
            logger.error(f"[{job_name}] Sync error: {e!s}")
            event_bus.publish(job_name, "sync_error", {"message": str(e)})
            raise

    try:
        job_queue.register_job(
            name=job_name,
            func=_run_sync,
            interval_seconds=None,
            enabled=True,
            max_retries=3,
            backoff_base=5.0,
            backoff_factor=2.0,
        )
        if not job_queue.execute_job_now(job_name):
            raise RuntimeError(f"Job '{job_name}' is already running or unavailable")
    except Exception as e:
        logger.error(f"Failed to schedule Plex sync job '{job_name}': {e}", exc_info=True)
        return {"accepted": False, "error": "Failed to schedule sync job"}

    return {
        "accepted": True,
        "job": job_name,
        "target": target,
        "playlist": playlist_name,
        "match_count": len(rating_keys),
        "sync_mode": sync_mode,
        "events_path": f"/api/v1/core/playlists/sync/events?job={quote(job_name, safe='')}",
    }


def _sync_to_tier(payload, source, target, playlist_name, matches, download_missing, sync_mode):
    """Sync matched tracks to a tier provider (Spotify, Tidal, etc.)."""
    valid_match_items = [m for m in matches if m.get("target_identifier")]
    track_ids = [m.get("target_identifier") for m in valid_match_items]
    if not track_ids:
        return {
            "accepted": False,
            "error": f"No {target} track IDs provided in matches",
        }

    # Schedule a one-off sync job
    job_name = f"sync:{target}:{playlist_name}:{int(time.time())}"

    def _run_sync():
        logger.info(f"[{job_name}] Starting {target} sync for playlist '{playlist_name}' with {len(track_ids)} tracks")
        event_bus.publish(
            job_name,
            "sync_started",
            {
                "playlist": playlist_name,
                "target": target,
                "total": len(track_ids),
                "download_missing": download_missing,
                "sync_mode": sync_mode,
            },
        )

        try:
            from core.nexus_framework.plugin_loader import (
                PluginRegistry,
            )

            target_provider = PluginRegistry.get_plugin(target)

            if not target_provider:
                raise RuntimeError(f"Plugin {target} not found")

            # Add tracks to target provider's playlist
            synced = 0
            failed_tracks = []

            for idx, m in enumerate(valid_match_items):
                track_id = m.get("target_identifier")
                track_title = (
                    m.get("source_title")
                    or m.get("title")
                    or (m.get("source_track") or {}).get("title")
                    or (m.get("source_track") or {}).get("name")
                    or "Unknown Track"
                )
                track_artist = (
                    m.get("source_artist")
                    or m.get("artist")
                    or (m.get("source_track") or {}).get("artist")
                    or "Unknown Artist"
                )

                logger.debug(
                    f"[{job_name}] Processing track {idx + 1}/{len(track_ids)} (ID: {track_id}, title: '{track_title}', artist: '{track_artist}')"
                )
                event_bus.publish(
                    job_name,
                    "track_started",
                    {
                        "index": idx,
                        "track_id": track_id,
                        "title": track_title,
                        "artist": track_artist,
                        "total": len(track_ids),
                    },
                )
                try:
                    # Provider-specific add-to-playlist logic
                    target_provider.add_to_playlist(playlist_name, track_id)
                    synced += 1
                    logger.debug(f"[{job_name}] Track {idx + 1} synced successfully")
                    event_bus.publish(
                        job_name,
                        "track_synced",
                        {
                            "index": idx,
                            "track_id": track_id,
                            "title": track_title,
                            "artist": track_artist,
                        },
                    )
                except Exception as fe:
                    err_msg = str(fe)
                    logger.warning(
                        f"[{job_name}] Track {idx + 1} failed: '{track_title}' by '{track_artist}' (ID: {track_id}) -> {err_msg}"
                    )
                    failed_tracks.append(
                        {
                            "index": idx + 1,
                            "track_id": track_id,
                            "title": track_title,
                            "artist": track_artist,
                            "error": err_msg,
                        }
                    )
                    event_bus.publish(
                        job_name,
                        "track_failed",
                        {
                            "index": idx,
                            "track_id": track_id,
                            "title": track_title,
                            "artist": track_artist,
                            "error": err_msg,
                        },
                    )

            if failed_tracks:
                summary_lines = [
                    f"[{job_name}] Sync completed with {len(failed_tracks)} failed tracks (out of {len(track_ids)} requested):"
                ]
                for f in failed_tracks:
                    summary_lines.append(
                        f"  • [Track #{f['index']}] '{f['title']}' by '{f['artist']}' (ID: {f['track_id']}) -> Error: {f['error']}"
                    )
                logger.warning("\n".join(summary_lines))
            else:
                logger.info(f"[{job_name}] All {synced}/{len(track_ids)} tracks synced successfully to {target}!")

            logger.info(f"[{job_name}] Sync complete: {synced} synced, {len(failed_tracks)} failed")
            event_bus.publish(
                job_name,
                "sync_complete",
                {
                    "playlist": playlist_name,
                    "synced": synced,
                    "failed": len(failed_tracks),
                    "failed_tracks": failed_tracks,
                    "target": target,
                    "sync_mode": sync_mode,
                },
            )

            # Record in history
            sync_history.record_sync(
                source=source,
                target=target,
                playlist=playlist_name,
                total=len(track_ids),
                synced=synced,
                failed=len(failed_tracks),
                download_missing=download_missing,
                job_name=job_name,
            )
        except Exception as e:
            event_bus.publish(job_name, "sync_error", {"message": str(e)})
            raise

    try:
        job_queue.register_job(
            name=job_name,
            func=_run_sync,
            interval_seconds=None,
            enabled=True,
            max_retries=3,
            backoff_base=5.0,
            backoff_factor=2.0,
        )
        if not job_queue.execute_job_now(job_name):
            raise RuntimeError(f"Job '{job_name}' is already running or unavailable")
    except Exception as e:
        logger.error(f"Failed to schedule {target} sync job '{job_name}': {e}", exc_info=True)
        return {"accepted": False, "error": "Failed to schedule sync job"}

    return {
        "accepted": True,
        "job": job_name,
        "target": target,
        "playlist": playlist_name,
        "track_count": len(track_ids),
        "sync_mode": sync_mode,
        "events_path": f"/api/v1/core/playlists/sync/events?job={quote(job_name, safe='')}",
    }


@router.get("/sync/events")
def sync_events(request: Request, job: str | None = None, since: int | str | None = None):
    job_name = job or request.query_params.get("job")
    since_val = since if since is not None else request.query_params.get("since")
    since_int = None
    if since_val is not None:
        try:
            since_int = int(since_val)
        except (ValueError, TypeError):
            since_int = None

    if not job_name:
        return {"error": "job query parameter required"}

    events = event_bus.get_events(job_name, since_id=since_int)
    return {
        "job": job_name,
        "events": events,
        "count": len(events),
    }


for extra_r in (api_v1_router, legacy_router, double_v1_router):
    extra_r.add_api_route("/sync/events", sync_events, methods=["GET"])


@router.get("/sync/history")
def sync_history_endpoint(request: Request):
    """Get recent sync records for observability."""
    source = request.query_params.get("source")
    target = request.query_params.get("target")
    limit = int(request.query_params.get("limit", 20))

    records = sync_history.get_records(source=source, target=target)
    recent = records[-limit:] if records else []

    return {
        "records": [r.to_dict() for r in recent],
        "total": len(recent),
    }


@router.post("/download-missing")
async def download_missing_tracks(request: Request):
    """Trigger downloads for missing tracks identified during analysis.

    Directly queues tracks to the download_manager's queue.
    No separate job is created - the main download_manager job handles processing.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    missing = payload.get("missing") or []
    target_quality = payload.get("target_quality") or payload.get("quality_profile")

    if not missing:
        return {"accepted": False, "error": "missing tracks list required"}

    try:
        from core.db.echo_sync_track import EchosyncTrack
        from services.download_manager import get_download_manager

        download_manager = get_download_manager()
        success_count = 0
        failed_count = 0

        # Queue all tracks directly to the download manager
        # The existing download_manager job will process them
        for track_info in missing:
            try:
                # Prefer full serialized source track when present so metadata survives queueing.
                source_track_payload = track_info.get("source_track")
                if isinstance(source_track_payload, dict):
                    track = EchosyncTrack.from_dict(source_track_payload)
                else:
                    duration_ms = track_info.get("duration_ms")
                    if duration_ms is None:
                        duration_ms = track_info.get("duration")

                    identifiers = {}
                    source_identifier = track_info.get("source_identifier")
                    if source_identifier:
                        identifiers["spotify"] = str(source_identifier)

                    # Create EchosyncTrack from fallback metadata, preserving ISRC when provided.
                    track = EchosyncTrack(
                        raw_title=track_info.get("title"),
                        artist_name=track_info.get("artist"),
                        album_title=track_info.get("album") or "",
                        duration=duration_ms,
                        isrc=track_info.get("isrc"),
                        identifiers=identifiers,
                    )

                # Queue the download (no separate job needed)
                download_id = download_manager.queue_download(track, quality_profile_id=target_quality)

                if download_id:
                    success_count += 1
                    logger.info(f"Queued for download: {track.title} by {track.artist_name} (ID: {download_id})")
                else:
                    failed_count += 1
                    logger.warning(f"Failed to queue: {track.title} by {track.artist_name}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Error queuing track: {e}")

        if success_count > 0:
            if hasattr(download_manager, "process_downloads_now"):
                try:
                    download_manager.process_downloads_now()
                except Exception as proc_err:
                    logger.warning(f"Error calling process_downloads_now: {proc_err}")
            try:
                from core.task_manager.task_queue import task_queue

                # Enqueue/trigger the asynchronous background download runner
                task_queue.trigger_job_by_name("download_queue_runner")
            except Exception as e:
                logger.warning(f"Queued downloads but background trigger failed: {e}")

        return {
            "accepted": True,
            "track_count": len(missing),
            "queued": success_count,
            "failed": failed_count,
            "message": f"Queued {success_count} tracks to download_manager (failed: {failed_count})",
        }

    except Exception as e:
        logger.error(f"Failed to queue downloads: {e}", exc_info=True)
        return {"accepted": False, "error": "Failed to queue downloads"}


# ========================================
# PERSONALIZED PLAYLISTS ENDPOINTS
# ========================================


@router.get("/genres")
def get_available_genres(request: Request):
    """Get list of available genres from discovery pool"""
    try:
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        genres = service.get_available_genres()
        return {"genres": genres, "total": len(genres)}
    except Exception as e:
        logger.error(f"Error fetching genres: {e}")
        return {"error": "Failed to fetch genres"}


@router.get("/genre/{genre_name}")
def get_genre_playlist(genre_name, request: Request):
    """Get playlist for a specific genre"""
    try:
        limit = int(request.query_params.get("limit", 50))
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_genre_playlist(genre_name, limit=limit)
        return {"genre": genre_name, "tracks": tracks, "total": len(tracks)}
    except Exception as e:
        logger.error(f"Error fetching genre playlist for {genre_name}: {e}")
        return {"error": "Failed to fetch genre playlist"}


@router.get("/decade/{decade}")
def get_decade_playlist(decade, request: Request):
    """Get playlist for a specific decade"""
    try:
        limit = int(request.query_params.get("limit", 100))
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_decade_playlist(decade, limit=limit)
        return {"decade": decade, "tracks": tracks, "total": len(tracks)}
    except Exception as e:
        logger.error(f"Error fetching decade playlist for {decade}s: {e}")
        return {"error": "Failed to fetch decade playlist"}


@router.get("/popular-picks")
def get_popular_picks(request: Request):
    """Get high-popularity tracks from discovery pool"""
    try:
        limit = int(request.query_params.get("limit", 50))
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_popular_picks(limit=limit)
        return {"name": "Popular Picks", "tracks": tracks, "total": len(tracks)}
    except Exception as e:
        logger.error(f"Error fetching popular picks: {e}")
        return {"error": "Failed to fetch popular picks"}


@router.get("/hidden-gems")
def get_hidden_gems(request: Request):
    """Get low-popularity underground tracks from discovery pool"""
    try:
        limit = int(request.query_params.get("limit", 50))
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_hidden_gems(limit=limit)
        return {"name": "Hidden Gems", "tracks": tracks, "total": len(tracks)}
    except Exception as e:
        logger.error(f"Error fetching hidden gems: {e}")
        return {"error": "Failed to fetch hidden gems"}


@router.get("/discovery-shuffle")
def get_discovery_shuffle(request: Request):
    """Get random tracks from discovery pool"""
    try:
        limit = int(request.query_params.get("limit", 50))
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_discovery_shuffle(limit=limit)
        return {"name": "Discovery Shuffle", "tracks": tracks, "total": len(tracks)}
    except Exception as e:
        logger.error(f"Error fetching discovery shuffle: {e}")
        return {"error": "Failed to fetch discovery shuffle"}


@router.get("/daily-mixes")
def get_all_daily_mixes(request: Request):
    """Get all daily mixes"""
    try:
        max_mixes = int(request.query_params.get("max_mixes", 4))
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        mixes = service.get_all_daily_mixes(max_mixes=max_mixes)
        return {"mixes": mixes, "total": len(mixes)}
    except Exception as e:
        logger.error(f"Error fetching daily mixes: {e}")
        return {"error": "Failed to fetch daily mixes"}


@router.post("/sync/schedule")
def schedule_recurring_sync(payload_obj: PlaylistSyncScheduleSchema):
    """Schedule a recurring playlist sync job (e.g., every 6 hours)."""
    payload = payload_obj.model_dump(exclude_unset=True) if payload_obj else {}
    source = payload.get("source")
    target = payload.get("target_source") or payload.get("target")
    playlists = payload.get("playlists", [])
    interval = payload.get("interval", 3600)  # Default: 1 hour in seconds
    download_missing = payload.get("download_missing", False)
    enabled = payload.get("enabled", True)

    if not source or not target or not playlists:
        return {"error": "source, target, and playlists required"}

    if interval < 300:
        return {"error": "interval must be at least 300 seconds (5 minutes)"}

    # Create scheduled sync config
    from core.settings import config_manager

    scheduled_syncs = config_manager.get("scheduled_syncs", [])

    sync_config = {
        "id": f"sync:{source}:{target}:{int(time.time())}",
        "source": source,
        "target": target,
        "playlists": playlists,
        "interval": interval,
        "download_missing": download_missing,
        "enabled": enabled,
        "created_at": time.time(),
    }

    scheduled_syncs.append(sync_config)
    config_manager.set("scheduled_syncs", scheduled_syncs)
    config_manager.save_config()

    # Register the job immediately if enabled
    if enabled:
        _register_scheduled_sync_job(sync_config)

    logger.info(f"Scheduled sync created: {sync_config['id']} (interval: {interval}s)")
    return {
        "accepted": True,
        "sync_id": sync_config["id"],
        "interval": interval,
    }


@router.get("/sync/scheduled")
def list_scheduled_syncs(request: Request):
    """List all scheduled playlist sync jobs."""
    from core.settings import config_manager

    scheduled_syncs = config_manager.get("scheduled_syncs", [])

    # Enrich with job status from job_queue
    for sync in scheduled_syncs:
        job_name = f"scheduled:{sync['id']}"
        if job_name in job_queue.jobs:
            job_info = job_queue.jobs[job_name]
            sync["running"] = job_queue.running.get(job_name, False)
            sync["last_run"] = job_info.get("last_run")
            sync["last_error"] = job_info.get("last_error")
        else:
            sync["running"] = False

    return {
        "scheduled_syncs": scheduled_syncs,
        "count": len(scheduled_syncs),
    }


@router.delete("/sync/scheduled/{sync_id}")
def delete_scheduled_sync(sync_id, request: Request):
    """Delete a scheduled sync job."""
    from core.settings import config_manager

    scheduled_syncs = config_manager.get("scheduled_syncs", [])

    # Find and remove sync
    updated_syncs = [s for s in scheduled_syncs if s.get("id") != sync_id]
    if len(updated_syncs) == len(scheduled_syncs):
        return {"error": "Sync not found"}

    config_manager.set("scheduled_syncs", updated_syncs)
    config_manager.save_config()

    # Unregister from job queue
    job_name = f"scheduled:{sync_id}"
    if job_name in job_queue.jobs:
        job_queue.unregister_job(job_name)

    logger.info(f"Scheduled sync deleted: {sync_id}")
    return {"accepted": True}


def _register_scheduled_sync_job(sync_config):
    """Register a scheduled sync config as a recurring job in the job queue."""
    job_name = f"scheduled:{sync_config['id']}"
    source = sync_config["source"]
    target = sync_config["target"]
    playlists = sync_config["playlists"]
    download_missing = sync_config.get("download_missing", False)
    interval = sync_config["interval"]

    def _run_scheduled_sync():
        try:
            playlist_entries = [playlist if isinstance(playlist, dict) else {"id": playlist} for playlist in playlists]
            analysis = _analyze_playlists_internal(source, target, playlist_entries, quality_profile="Auto")
            matches = analysis.get("summary", {}).get("matched_pairs", []) or []

            if matches:
                playlist_name = f"Synced Playlist ({sync_config['id']})"
                primary_playlist = playlist_entries[0] if len(playlist_entries) == 1 else {}
                if target == "plex":
                    _sync_to_plex(
                        {
                            "source": source,
                            "target": target,
                            "target_user_id": primary_playlist.get("target_user_id"),
                            "source_account_name": primary_playlist.get("source_account_name"),
                        },
                        source,
                        target,
                        playlist_name,
                        matches,
                        download_missing,
                        "scheduled",
                    )
                elif target in {"spotify", "tidal", "apple_music"}:
                    _sync_to_tier(
                        {
                            "source": source,
                            "target": target,
                        },
                        source,
                        target,
                        playlist_name,
                        matches,
                        download_missing,
                        "scheduled",
                    )
        except Exception as e:
            logger.error(f"Scheduled sync {sync_config['id']} failed: {e}")
            raise

    try:
        job_queue.register_job(
            name=job_name,
            func=_run_scheduled_sync,
            interval_seconds=interval,
            enabled=True,
            max_retries=3,
            backoff_base=5.0,
            backoff_factor=2.0,
        )
        logger.info(f"Registered scheduled sync job: {job_name} (interval: {interval}s)")
    except Exception as e:
        logger.error(f"Failed to register scheduled sync job '{job_name}': {e}")


def load_scheduled_syncs_on_startup():
    """Load all enabled scheduled syncs from config at startup."""
    from core.settings import config_manager

    scheduled_syncs = config_manager.get("scheduled_syncs", [])

    for sync_config in scheduled_syncs:
        if sync_config.get("enabled", True):
            _register_scheduled_sync_job(sync_config)

    logger.info(f"Loaded {len([s for s in scheduled_syncs if s.get('enabled')])} scheduled syncs")
