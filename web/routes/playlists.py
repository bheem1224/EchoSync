import logging
import re
from difflib import SequenceMatcher
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, Request
from web.services.sync_service import SyncAdapter
from core.personalized_playlists import get_personalized_playlists_service
from database.music_database import MusicDatabase
from core.tiered_logger import get_logger
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import ScoringProfile
from core.db.echo_sync_track import EchosyncTrack
from core.matching_engine.text_utils import normalize_title as _normalize_candidate_title
from core.job_queue import job_queue
from core.event_bus import event_bus
from core.sync_history import sync_history
from core.hook_manager import hook_manager
import time
import uuid

from pydantic import BaseModel
from typing import List, Optional, Any, Dict, Union

class PlaylistAnalyzeSchema(BaseModel):
    source: Optional[Union[str, int]] = None
    target: Optional[Union[str, int]] = None
    target_source: Optional[Union[str, int]] = None
    playlists: Optional[List[Any]] = None
    quality_profile: Optional[Union[str, Dict[str, Any]]] = "Auto"

class PlaylistSyncSchema(BaseModel):
    target: Optional[Union[str, int]] = None
    target_source: Optional[Union[str, int]] = None
    playlist_name: Optional[str] = None
    matches: Optional[List[Any]] = None
    download_missing: Optional[bool] = False
    source: Optional[Union[str, int]] = "unknown"

class PlaylistDownloadMissingSchema(BaseModel):
    missing: Optional[List[Any]] = None

class PlaylistSyncScheduleSchema(BaseModel):
    source: Optional[Union[str, int]] = None
    target: Optional[Union[str, int]] = None
    target_source: Optional[Union[str, int]] = None
    playlists: Optional[List[Any]] = None
    interval: Optional[int] = 3600
    download_missing: Optional[bool] = False
    enabled: Optional[bool] = True

# In-memory store for ad-hoc analysis jobs started via API
ANALYSIS_JOBS = {}

logger = get_logger("playlists_api")
router = APIRouter(prefix="/api/v1/core/playlists", tags=["Playlists"])
api_v1_router = APIRouter(prefix="/api/v1/playlists", tags=["Playlists"])
legacy_router = APIRouter(prefix="/api/playlists", tags=["Playlists"])

# ── Semantic Substring Failsafe — safe OST filler dictionary ──────────────────
# Words that commonly appear in longer CJK/English OST title variants but do NOT
# change the track's identity.  If a title delta (the extra part of the longer
# string after the shared shorter title is removed) is composed *entirely* of
# these words the two strings refer to the same track and a 0.95 title score is
# awarded.  Any unrecognised token (e.g. 'Part 2', 'Remix', 'Live') causes the
# substring boost to be withheld, preventing false-positive Swap Cases.
_OST_SAFE_RE = re.compile(
    r'^(?:'
    r'\s'                                            # whitespace between tokens
    r'|电视剧|网剧|影视剧|影視劇|电影'              # drama-type classifiers
    r'|片头曲|片尾曲|主题曲|插曲|推广曲'             # song-role labels
    r'|原声带|原声|配乐'                              # soundtrack labels
    r'|ost|theme|opening|ending|soundtrack|original'  # English equivalents (original set)
    # ── Extended English metadata terms ──────────────────────────────────
    # These words appear in longer title variants (remaster editions, release
    # format suffixes, event-specific tags) but do NOT change track identity.
    # Longer forms are listed before shorter prefixes so the regex engine
    # consumes them greedily before attempting a shorter alternative
    # (e.g. 'remastered' is tried before 'remaster').
    # \d covers year tokens (2013, 2024) and track numbers.
    r'|remastered|remaster'                          # remaster suffix variants
    r'|acoustic|live'                                # performance/recording type
    r'|radio|single|extended|club'                   # release format descriptors
    r'|version|edit|mix|remix|bootleg'               # common music metadata
    r'|official|song|shanty'                         # descriptor words
    r'|sea|uefa|euro|anthem|from|la'                 # expanded descriptor words: sea shanty, euro 2024, from "...", la la la, anthem
    r'|deluxe'                                       # edition descriptor
    r'|pt|part|vol|volume'                           # part indicators
    r'|viii|vii|iii|iv|vi|ix|ii|i|x'                 # Roman numerals (longest first)
    r'|gabry|ponte|ice|pop'                          # common edit descriptors
    r'|\d'                                           # digits for years / track numbers (2013, 2024, 1, 2)
    r')+$',
    re.IGNORECASE | re.UNICODE,
)
# ──────────────────────────────────────────────────────────────────────────────

# ── Pinyin artist-matching constants ─────────────────────────────────────────
# When the best artist score after primary-name + alias checks is still below
# _PINYIN_ARTIST_THRESHOLD, a Hanzi → Pinyin transliteration fallback is tried.
# _PINYIN_ARTIST_PASS is the minimum token_sort_ratio (0–100) required for that
# fallback to override the alias-based score and accept the match.
_PINYIN_ARTIST_THRESHOLD = 0.85  # only enter Pinyin path when score is below this
_PINYIN_ARTIST_PASS      = 90    # token_sort_ratio needed to accept the match
# ──────────────────────────────────────────────────────────────────────────────


def _get_provider_for_account(provider_id, acc_id=None):
    from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry, generate_plugin_id, get_plugin_capabilities

    # Handle if a string was passed for backward compatibility, though it should be an int
    if isinstance(provider_id, str):
        if provider_id.isdigit():
            provider_id = int(provider_id)
        else:
            # Try to match a registered plugin name ending with the string
            found = False
            for p_id, p_cls in PluginRegistry._plugins.items():
                if hasattr(p_cls, 'name') and p_cls.name and p_cls.name.lower().endswith(provider_id.lower()):
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
        
        if getattr(caps, 'supports_user_auth', False):
            if acc_id is None:
                from services.storage_service import get_storage_service
                storage = get_storage_service()
                
                # We need to find an account for this plugin. Use the stringified provider_id
                accounts = storage.list_accounts(str(provider_id))
                if not accounts:
                    return None, None
                acc_id_local = accounts[0]['id']
            else:
                acc_id_local = acc_id
                
            return plugin_class(account_id=acc_id_local), acc_id_local
            
        return PluginRegistry.create_instance(provider_id), None
    except Exception as e:
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

    p_str = str(provider_id).lower()
    if p_str.startswith("echosync."):
        return p_str.split(".")[-1]
    return p_str


def _extract_track_field(track, key):
    if isinstance(track, dict):
        return track.get(key)
    return getattr(track, key, None)


def _extract_target_identifier(candidate):
    if isinstance(candidate, dict):
        return candidate.get('id') or candidate.get('target_identifier')

    identifiers = getattr(candidate, 'identifiers', {}) or {}
    for key in ('plex', 'spotify_id', 'tidal_id', 'id'):
        if key in identifiers:
            return identifiers.get(key)

    return getattr(candidate, 'id', None)


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
        s = re.sub(r'[^\w\s]', '', s)
        return ' '.join(s.split())

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
        if len(shorter) >= 3 and re.search(
            r'(?<![\w])' + re.escape(shorter) + r'(?![\w])', longer
        ):
            # Extract delta: strip the shared prefix and collapse leftover whitespace.
            delta_raw = re.sub(r'(?<![\w])' + re.escape(shorter) + r'(?![\w])', '', longer, count=1)
            # Strip ALL punctuation and separators; keep only word characters.
            delta_words = re.sub(r'[^\w]', '', delta_raw, flags=re.UNICODE)
            if not delta_words:
                # Delta is purely separators / punctuation — same track.
                logger.debug(
                    "Substring failsafe: '%s' ⊂ '%s' — delta is empty after strip → score=0.95",
                    shorter, longer,
                )
                ratio = 0.95
            elif _OST_SAFE_RE.match(delta_words):
                # Delta is composed entirely of safe OST filler tokens.
                logger.debug(
                    "Substring failsafe: '%s' ⊂ '%s' — delta '%s' is safe filler → score=0.95",
                    shorter, longer, delta_words,
                )
                ratio = 0.95
            else:
                # Delta contains unrecognised text — do NOT boost; prevents Swap Cases.
                logger.debug(
                    "Substring failsafe: '%s' ⊂ '%s' — delta '%s' contains unrecognised token "
                    "→ rejecting substring match",
                    shorter, longer, delta_words,
                )
    # ── End Semantic Substring Failsafe ──────────────────────────────────────

    return ratio


_TRIBUTE_DELTA_TOKENS = {
    "tribute", "tribute band", "cover band", "karaoke", 
    "sound-alike", "soundalike", "parody", "style of", "in the style of",
    "celebration", "orchestra", "instrumental version", "piano tribute"
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
        s = re.sub(r'[^\w\s]', '', s)
        return ' '.join(s.split())

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
        delta = re.sub(r'(?<![\w])' + re.escape(shorter) + r'(?![\w])', '', longer).strip()
        delta_lower = delta.lower()
        delta_tokens = set(re.findall(r'\b\w+\b', delta_lower))

        has_tribute = any(
            t in delta_lower or t in delta_tokens
            for t in _TRIBUTE_DELTA_TOKENS
        )
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
        'search_expansion', [],
        title=search_title, artist=track_artist,
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

    title_norm = search_title.replace('\u2019', "'").replace('\u2018', "'")

    params = {
        "artist_exact":       track_artist,
        "artist_pattern":     f"%{track_artist}%",
        "title_exact":        search_title,
        "title_pattern":      f"%{search_title}%",
        "base_title_pattern": f"%{base_search_title}%",
        "title_norm_pattern": f"%{title_norm}%",
        "duration":           track_duration or 0,
    }

    # Returns an alias-aware LIKE fragment for a named SQL parameter.
    # Matches Track.title, Track.sort_title, or any track_aliases.name row.
    def _am(param):
        return (
            f"(LOWER(t.title) LIKE LOWER(:{param})"
            f" OR (t.sort_title IS NOT NULL AND LOWER(t.sort_title) LIKE LOWER(:{param}))"
            f" OR EXISTS (SELECT 1 FROM track_aliases ta_x"
            f" WHERE ta_x.track_id = t.id AND LOWER(ta_x.name) LIKE LOWER(:{param})))"
        )

    # Broad Funnel: match title/aliases loosely, completely ignoring artist and duration filters in WHERE.
    base_where = (
        f"{_am('title_pattern')}\n"
        f"        OR {_am('base_title_pattern')}\n"
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
               t.sort_title, al.title AS album_title
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
        'search_expansion', [],
        title=search_title, artist='',
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

    params = {
        "title_exact":  search_title,
        "title_pattern": f"%{search_title}%",
        "duration":     track_duration,
    }

    # Base title-exact conditions (original Tier 2) replaced with broad funnel LIKE/alias checks.
    base_where = (
        "LOWER(t.title) LIKE LOWER(:title_pattern)\n"
        "        OR (t.sort_title IS NOT NULL AND LOWER(t.sort_title) LIKE LOWER(:title_pattern))\n"
        "        OR EXISTS (SELECT 1 FROM track_aliases ta_x\n"
        "                   WHERE ta_x.track_id = t.id AND LOWER(ta_x.name) LIKE LOWER(:title_pattern))"
    )

    # Expanded terms use LIKE — transliterations need fuzzy title matching.
    exp_parts = []
    for i, term in enumerate(clean_expanded):
        pkey = f"exp_{i}"
        params[pkey] = f"%{term}%"
        exp_parts.append(
            f"(LOWER(t.title) LIKE LOWER(:{pkey})"
            f" OR (t.sort_title IS NOT NULL AND LOWER(t.sort_title) LIKE LOWER(:{pkey}))"
            f" OR EXISTS (SELECT 1 FROM track_aliases ta_x"
            f" WHERE ta_x.track_id = t.id AND LOWER(ta_x.name) LIKE LOWER(:{pkey})))"
        )
    exp_where = ("\n        OR " + "\n        OR ".join(exp_parts)) if exp_parts else ""

    sql = _sql(f"""
        SELECT DISTINCT t.id, t.title, t.duration, t.edition,
               a.name AS artist_name, a.id AS artist_id,
               t.sort_title, al.title AS album_title
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
    from database.music_database import MusicDatabase
    from core.nexus_framework.plugin_SDK import PlaylistSupport
    from core.matching_engine.scoring_profile import ExactSyncProfile
    from sqlalchemy import text

    target_source_canonical = _normalize_provider_short_name(target_source) if target_source else target_source

    source_provider, default_acc = _get_provider_for_account(source, None)
    if source_provider is None:
        source_name = str(source).title()
        raise RuntimeError(f"No {source_name} accounts configured. Please add an account in Settings.")

    caps = getattr(source_provider, 'capabilities', None)
    if not caps or caps.supports_playlists not in (PlaylistSupport.READ, PlaylistSupport.READ_WRITE):
        raise RuntimeError(f"Provider {source} does not support reading playlists")

    db = MusicDatabase()
    matching_engine = WeightedMatchingEngine(ExactSyncProfile())

    all_tracks = []
    found_count = 0
    missing_count = 0

    for playlist_info in playlists:
        playlist_id = playlist_info.get("id")
        playlist_name = playlist_info.get("name", "Unknown Playlist")

        acc_id = playlist_info.get('account_id')
        if acc_id and getattr(caps, 'supports_user_auth', False):
            provider_instance, _ = _get_provider_for_account(source, acc_id)
            if provider_instance:
                source_provider = provider_instance

        if not playlist_id:
            logger.warning(f"Skipping playlist without id: {playlist_name}")
            continue

        try:
            logger.info(f"Fetching tracks for playlist: {playlist_name} (id: {playlist_id})")
            import inspect
            sig = inspect.signature(source_provider.get_playlist_tracks)
            if 'force_refresh' in sig.parameters:
                source_tracks = source_provider.get_playlist_tracks(playlist_id, force_refresh=True)
            else:
                source_tracks = source_provider.get_playlist_tracks(playlist_id)

            for source_track in source_tracks:
                track_title = source_track.title
                track_artist = source_track.artist_name
                track_album = source_track.album_title or ''
                track_duration = source_track.duration

                def _strip_feat(title: str) -> str:
                    if not title:
                        return ""
                    cleaned = re.sub(r"\s*[\(\[\{]\s*(feat\.?|featuring|with)\b[^\)\]\}]*[\)\]\}]", "", title, flags=re.IGNORECASE)
                    cleaned = re.sub(r"\s+(feat\.?|featuring|with)\b.*$", "", cleaned, flags=re.IGNORECASE)
                    return cleaned.strip() or title

                search_title = _strip_feat(track_title)
                # Base title: strip parentheticals, brackets, and post-hyphen suffixes so that
                # e.g. "Wellerman - Sea Shanty" also queries for "Wellerman" and finds the DB
                # row stored as "Wellerman (Sea Shanty)".
                base_search_title = re.sub(r'\s*[\(\[].*?[\)\]]', '', search_title).strip()
                base_search_title = re.sub(r'\s+-.*$', '', base_search_title).strip()
                if not base_search_title:
                    base_search_title = search_title

                # ── Populate source-track plugin context (drama name extraction) ─────
                # Fire the pre_normalize_title hook on the raw source title while CJK
                # brackets are still intact so the CJK plugin can write cjk_drama into
                # source_track.plugin_context.  The scoring_modifier hook later compares
                # this value against the candidate's drama context.
                hook_manager.apply_filters(
                    'pre_normalize_title',
                    source_track.raw_title,
                    plugin_context=source_track.plugin_context,
                )

                # ── Normalize source title for scoring ───────────────────────────────
                # Pass through the same normalize_title() pipeline used on candidate
                # titles so the fuzzy matcher always compares clean text on both sides.
                # e.g. "逆刃（电视剧《山河令》片头曲）" → "逆刃"
                # plugin_context is passed so normalize_title re-fires pre_normalize_title
                # on the same title — harmless since cjk_drama is just overwritten with
                # the same value that was already extracted above.
                _clean_source_title = _normalize_candidate_title(
                    source_track.raw_title,
                    plugin_context=source_track.plugin_context,
                )
                if _clean_source_title:
                    source_track.title = _clean_source_title

                library_match = "Not Found"
                best_score = 0
                had_cover_rejection = False
                evaluated_candidate_ids: set[int] = set()

                try:
                    with db.engine.connect() as conn:
                        candidates = _fetch_tier1_candidates(
                            conn, search_title, base_search_title,
                            track_artist, track_duration,
                        )
                        tier2_mode = False

                        if not candidates and track_duration:
                            # Wide net: ±10000ms. The SQL window is intentionally wider
                            # than the engine’s hard rejection threshold so that the
                            # Artist Match Duration Escalation (up to 8500ms) always has
                            # candidates to work with. Python scoring enforces the strict
                            # gate; false positives are rejected there, not at the SQL layer.
                            # (Previously 5000ms — raised to 10000ms.)
                            sql_duration_tolerance_ms = 10000
                            logger.debug(
                                f"Tier 1 found 0 candidates for '{track_title}' by '{track_artist}'. "
                                f"Attempting Tier 2 with title='{search_title}', duration={track_duration}ms ±{sql_duration_tolerance_ms}ms"
                            )
                            tier2_raw_candidates = _fetch_tier2_candidates(
                                conn, search_title, track_duration,
                                sql_duration_tolerance_ms,
                            )
                            candidates = [c for c in tier2_raw_candidates if c[0] not in evaluated_candidate_ids]
                            tier2_mode = True

                    external_ids_map = {}
                    if target_source_canonical and candidates:
                        candidate_ids = [row[0] for row in candidates]
                        try:
                            external_ids_map = db.get_external_identifier_map(target_source_canonical, candidate_ids)
                        except Exception as ext_err:
                            logger.debug(f"External identifier lookup failed for target '{target_source_canonical}': {ext_err}")

                    best_match = None
                    best_match_track_id = None
                    best_match_target_id = None
                    valid_candidates = []
                    candidate_diagnostics = []
                    near_miss_candidate_id = None
                    initial_candidates = list(candidates) if candidates else []

                    # Batch-fetch all track aliases for the candidate set so that
                    # per-candidate alias scoring below needs no extra DB round-trips.
                    _alias_map: dict = {}
                    if candidates:
                        try:
                            _cids = [int(r[0]) for r in candidates]
                            with db.engine.connect() as _ac:
                                for _ar in _ac.execute(
                                    text(
                                        "SELECT track_id, name FROM track_aliases"
                                        " WHERE track_id IN ("
                                        + ",".join(str(c) for c in _cids)
                                        + ")"
                                    )
                                ).fetchall():
                                    _alias_map.setdefault(_ar[0], []).append(_ar[1])
                        except Exception:
                            _alias_map = {}

                    # Batch-fetch artist aliases keyed by artist_id (column 5) so that
                    # romanised forms ('Zhou Shen') and alternate scripts ('\u5468\u6df1') stored in the
                    # artist_aliases table are considered when scoring the artist dimension.
                    _artist_alias_map: dict = {}
                    if candidates:
                        try:
                            _artist_ids = list({int(r[5]) for r in candidates if r[5] is not None})
                            if _artist_ids:
                                with db.engine.connect() as _aac:
                                    for _aar in _aac.execute(
                                        text(
                                            "SELECT artist_id, name FROM artist_aliases"
                                            " WHERE artist_id IN ("
                                            + ",".join(str(a) for a in _artist_ids)
                                            + ")"
                                        )
                                    ).fetchall():
                                        _artist_alias_map.setdefault(_aar[0], []).append(_aar[1])
                        except Exception:
                            _artist_alias_map = {}

                    for candidate_row in candidates:
                        evaluated_candidate_ids.add(candidate_row[0])
                        candidate_target_id = external_ids_map.get(candidate_row[0]) if target_source_canonical else None
                        raw_title_candidate = candidate_row[1]
                        edition_candidate = candidate_row[3]
                        sort_title_candidate = None
                        try:
                            sort_title_candidate = candidate_row[6]
                        except Exception:
                            sort_title_candidate = None

                        if edition_candidate is None and sort_title_candidate and sort_title_candidate != raw_title_candidate:
                            version_pattern = r'\b(Remix|Mix|Live|Demo|Remaster|Deluxe|Edit|Version|Acoustic|Instrumental|Bonus|Extended|Original)\b'
                            version_match = re.search(version_pattern, sort_title_candidate, re.IGNORECASE)
                            if version_match:
                                edition_candidate = version_match.group(0)

                        from core.matching_engine.text_utils import parse_duration_to_ms
                        candidate_track = EchosyncTrack(
                            raw_title=raw_title_candidate,
                            artist_name=candidate_row[4],
                            album_title=candidate_row[7] or "",
                            duration=parse_duration_to_ms(candidate_row[2]) if candidate_row[2] else 0,
                            edition=edition_candidate,
                        )
                        # Populate candidate plugin_context so scoring_modifier can
                        # compare drama names extracted from both sides.
                        hook_manager.apply_filters(
                            'pre_normalize_title',
                            candidate_track.raw_title,
                            plugin_context=candidate_track.plugin_context,
                        )

                        # ── Normalize candidate title & promote best alias ─────────────
                        # Pass the raw DB title through normalize_title() to strip CJK
                        # promo suffixes (e.g. "望天涯 - 网剧《山河令》推广" → "望天涯") and
                        # CJK bracket annotations.  Then score each stored alias so that
                        # script-variant or Pinyin/Romaji forms can achieve a 100% match.
                        _clean_cand_title = _normalize_candidate_title(
                            raw_title_candidate,
                            plugin_context=candidate_track.plugin_context,
                        )
                        _best_cand_title = _clean_cand_title or candidate_track.title
                        # Context guard for the Semantic Substring Failsafe: compute raw
                        # artist similarity from the primary name pair (before alias
                        # resolution) and check whether the CJK plugin found a drama
                        # context in the candidate title (set by pre_normalize_title).
                        _t1_artist_ctx = (
                            _cmp_artists(source_track.artist_name, candidate_row[4])
                            if source_track.artist_name and candidate_row[4]
                            else 0.0
                        )
                        _t1_drama_ctx = bool(
                            (candidate_track.plugin_context or {}).get('remote_drama')
                        )
                        _best_cand_score = _cmp_titles(
                            source_track.title, _best_cand_title,
                            context_score=_t1_artist_ctx, drama_ctx=_t1_drama_ctx,
                        )
                        for _alias_name in _alias_map.get(candidate_row[0], []):
                            if not _alias_name:
                                continue
                            _alias_clean = _normalize_candidate_title(_alias_name)
                            _alias_score = _cmp_titles(
                                source_track.title, _alias_clean,
                                context_score=_t1_artist_ctx, drama_ctx=_t1_drama_ctx,
                            )
                            if _alias_score > _best_cand_score:
                                _best_cand_score = _alias_score
                                _best_cand_title = _alias_clean
                        if _best_cand_title and _best_cand_title != candidate_track.title:
                            candidate_track.title = _best_cand_title

                        # ── Promote best artist alias (Tier 1) ────────────────────────────
                        # Score the primary artist name and every stored artist alias against
                        # the source artist; hand the best-matching form to the engine so
                        # that fuzzy matching sees 'Zhou Shen' vs 'Zhou Shen' (alias) rather
                        # than 'Zhou Shen' vs '\u5468\u6df1' (primary).  _cmp_artists assigns a 0.95
                        # floor when one normalised name contains the other as a substring,
                        # handling credit-group tags like '\u6469\u767b\u5144\u5f1f\u5218\u5b87\u5b81' vs '\u5218\u5b87\u5b81'.
                        # Initialised to 0.0 so the Dynamic Duration Expansion below can
                        # read this value even when source_track.artist_name is empty.
                        _best_artist_score = 0.0
                        if source_track.artist_name:
                            _best_artist_name = candidate_track.artist_name or ''
                            _best_artist_score = _cmp_artists(source_track.artist_name, _best_artist_name)
                            for _artist_alias in _artist_alias_map.get(candidate_row[5], []):
                                if not _artist_alias:
                                    continue
                                _a_score = _cmp_artists(source_track.artist_name, _artist_alias)
                                if _a_score > _best_artist_score:
                                    _best_artist_score = _a_score
                                    _best_artist_name = _artist_alias

                            # ── Multi-Artist Substring + Bilingual Double-Lock ─────────────────
                            # Three-way spaceless check:
                            #
                            # Check 1 — Equal (space-agnostic exact match):
                            #   'Axwell /\ Ingrosso' → 'axwellingrosso' == 'axwellingrosso'
                            #
                            # Check 2 — Safe direction (Spotify primary ⊆ local candidate):
                            #   Local DB tracks tagged with ALL credited artists contain the
                            #   Spotify primary as a substring.  Score=1.0 with no further
                            #   verification required because the extra artists come from the
                            #   local file tags, not from an untrusted Spotify string.
                            #   e.g. candidate 'Axwell /\ Ingrosso, Axwell, Sebastian Ingrosso'
                            #        contains Spotify 'Axwell /\ Ingrosso'.
                            #
                            # Check 3 — Risky direction (local candidate ⊆ Spotify string):
                            #   The Spotify artist string is longer — it might be a combined
                            #   bilingual tag ('Faye 詹雯婷') or a feat. credit.  Apply the
                            #   Double-Lock Containment Failsafe: require BOTH the candidate's
                            #   primary name AND at least one stored alias to appear inside the
                            #   Spotify string.  Two independent anchors make a false positive
                            #   virtually impossible.
                            if _best_artist_score < 1.0:
                                def _ss_norm(s: str) -> str:
                                    """Strip ALL whitespace and non-word chars, lowercase."""
                                    return re.sub(r'[\s\W_]+', '', s, flags=re.UNICODE).lower()

                                _ss_src  = _ss_norm(source_track.artist_name)
                                _ss_cand = _ss_norm(_best_artist_name)

                                if _ss_src and _ss_cand and _ss_src == _ss_cand:
                                    # Check 1: exact spaceless match.
                                    _best_artist_score = 1.0
                                    _best_artist_name  = source_track.artist_name
                                    logger.debug(
                                        "Multi-Artist (exact spaceless): '%s' ≡ '%s' → artist_score=1.0",
                                        source_track.artist_name, _best_artist_name,
                                    )
                                elif _ss_src and _ss_cand and _ss_src in _ss_cand:
                                    # Check 2: safe direction — local candidate contains the Spotify primary.
                                    _best_artist_score = 1.0
                                    _best_artist_name  = source_track.artist_name
                                    logger.debug(
                                        "Multi-Artist (safe containment): Spotify '%s' found inside "
                                        "local '%s' → artist_score=1.0",
                                        source_track.artist_name, _best_artist_name,
                                    )
                                elif _ss_src and _ss_cand and _ss_cand in _ss_src:
                                    # Check 3: risky direction — apply Double-Lock.
                                    def _dl_norm(s: str) -> str:
                                        """Lowercase + strip punctuation; keep spaces for containment."""
                                        return re.sub(r'[^\w\s]', '', s, flags=re.UNICODE).strip().lower()

                                    _dl_src     = _dl_norm(source_track.artist_name)
                                    _dl_primary = _dl_norm(candidate_track.artist_name or '')
                                    _dl_aliases = [
                                        _dl_norm(a)
                                        for a in _artist_alias_map.get(candidate_row[5], [])
                                        if a
                                    ]
                                    if (
                                        _dl_primary
                                        and _dl_primary in _dl_src
                                        and any(a and a in _dl_src for a in _dl_aliases)
                                    ):
                                        _best_artist_score = 1.0
                                        _best_artist_name  = source_track.artist_name
                                        logger.debug(
                                            "Double-Lock (bilingual containment): primary '%s' "
                                            "and an alias both found in Spotify artist '%s' "
                                            "→ artist_score=1.0",
                                            _dl_primary, _dl_src,
                                        )
                            # ── End Multi-Artist Substring + Bilingual Double-Lock ─────────────

                            # ── Pinyin transliteration fallback ────────────────────────────────
                            # If the best score after primary name + aliases is still below the
                            # threshold, convert both sides through the CJK transliterator so
                            # Hanzi characters become space-separated Pinyin syllables:
                            #   Spotify source: '陳雪燃'  → 'chen xue ran'
                            #   Local DB:       'Xueran Chen' → 'xueran chen' (Latin, no-op)
                            # token_sort_ratio handles Eastern vs Western name-token ordering
                            # ('chen xue ran' vs 'xueran chen').  Primary name AND all stored
                            # aliases are checked; the highest Pinyin score wins.
                            if _best_artist_score < _PINYIN_ARTIST_THRESHOLD:
                                try:
                                    from plugins.EchoSync.cjk_language_pack.transliterator import CJKTransliterator
                                    from rapidfuzz import fuzz as _rfuzz

                                    def _py_strip(s: str) -> str:
                                        return re.sub(r'[^\w\s]', '', s, flags=re.UNICODE).strip().lower()

                                    _xlate = CJKTransliterator()
                                    _src_py = _py_strip(_xlate.to_pinyin(source_track.artist_name))

                                    _py_best_score = 0
                                    _py_best_name  = _best_artist_name or ''
                                    # Check primary candidate name + every alias in Pinyin space.
                                    _py_candidates = [_best_artist_name or ''] + list(
                                        _artist_alias_map.get(candidate_row[5], [])
                                    )
                                    for _py_cand in _py_candidates:
                                        if not _py_cand:
                                            continue
                                        _cand_py = _py_strip(_xlate.to_pinyin(_py_cand))
                                        if _src_py and _cand_py:
                                            _ts = _rfuzz.token_sort_ratio(_src_py, _cand_py)
                                            if _ts > _py_best_score:
                                                _py_best_score = _ts
                                                _py_best_name  = _py_cand

                                    if _py_best_score >= _PINYIN_ARTIST_PASS:
                                        _best_artist_score = _py_best_score / 100.0
                                        # Substitute the source's artist name so the downstream
                                        # matching engine sees identical strings on both sides
                                        # and awards the maximum artist component score.
                                        _best_artist_name = source_track.artist_name
                                        logger.debug(
                                            "Pinyin fallback: '%s' ↔ '%s' → py_src='%s' "
                                            "token_sort=%d — artist accepted.",
                                            source_track.artist_name, _py_best_name,
                                            _src_py, _py_best_score,
                                        )
                                except ImportError:
                                    logger.debug("CJK language pack not installed; skipping Pinyin fallback for artist name.")
                                except Exception as _py_exc:
                                    logger.debug("Pinyin artist fallback error: %s", _py_exc)
                            # ── End Pinyin fallback ────────────────────────────────────────────

                            if _best_artist_name and _best_artist_name != candidate_track.artist_name:
                                candidate_track.artist_name = _best_artist_name

                        if source_track.edition or candidate_track.edition:
                            logger.debug(
                                f"Version comparison: source='{source_track.edition}' vs candidate='{candidate_track.edition}' "
                                f"(source_title='{source_track.title}', candidate_title='{candidate_track.title}')"
                            )

                        # ── Dynamic Duration Expansion ─────────────────────────────────────
                        # Tiered tolerance based on how strongly artist + title are confirmed:
                        #
                        # Tier A — Perfect semantic match (artist ≥ 95 % AND titles identical):
                        #   90 000 ms (90 s) — absorbs unlabelled Extended / Album versions
                        #   whose only difference from the Spotify track is extra runtime.
                        #   Title identity guarantees no Remix/Acoustic confusion.
                        #
                        # Tier B — Strong artist match only (artist ≥ 95 %, title differs):
                        #   15 000 ms (15 s) — allows reasonable edit-length variation while
                        #   staying tight enough to reject unrelated versions.
                        #
                        # The original tolerance is restored immediately after the call so
                        # all other candidates in the same batch remain unaffected.
                        _ss_src_title  = re.sub(r'[\s\W_]+', '', (source_track.title or ''), flags=re.UNICODE).lower()
                        _ss_cand_title = re.sub(r'[\s\W_]+', '', (candidate_track.title or ''), flags=re.UNICODE).lower()
                        _title_exact   = bool(_ss_src_title and _ss_cand_title and _ss_src_title == _ss_cand_title)

                        _orig_dur_tol = None
                        if _best_artist_score >= 0.95 and _title_exact:
                            _orig_dur_tol = matching_engine.weights.duration_tolerance_ms
                            matching_engine.weights.duration_tolerance_ms = 90000
                            logger.debug(
                                "Duration expansion (Tier A): artist_score=%.2f + exact title '%s' — "
                                "duration_tolerance raised from %d ms to 90000 ms.",
                                _best_artist_score, candidate_track.title, _orig_dur_tol,
                            )
                        elif _best_artist_score >= 0.95:
                            _orig_dur_tol = matching_engine.weights.duration_tolerance_ms
                            matching_engine.weights.duration_tolerance_ms = 15000
                            logger.debug(
                                "Duration expansion (Tier B): artist_score=%.2f for '%s' — "
                                "duration_tolerance raised from %d ms to 15000 ms.",
                                _best_artist_score, candidate_track.title, _orig_dur_tol,
                            )
                        # ── End Dynamic Duration Expansion ────────────────────────────────

                        if tier2_mode:
                            result = matching_engine.calculate_title_duration_match(
                                source_track,
                                candidate_track,
                                target_source=target_source_canonical,
                                target_identifier=candidate_target_id,
                            )
                        else:
                            result = matching_engine.calculate_match(
                                source_track,
                                candidate_track,
                                target_source=target_source_canonical,
                                target_identifier=candidate_target_id,
                            )

                        if _orig_dur_tol is not None:
                            matching_engine.weights.duration_tolerance_ms = _orig_dur_tol

                        logger.debug(f"Match score for '{track_title}' vs '{candidate_track.title}': {result.confidence_score}")

                        candidate_diagnostics.append({
                            "candidate": {
                                "title": candidate_track.title,
                                "artist": candidate_track.artist_name,
                                "duration": candidate_track.duration or 0,
                            },
                            "result": {
                                "score": result.confidence_score,
                                "passed_version": result.passed_version_check,
                                "passed_edition": result.passed_edition_check,
                                "fuzzy_text": result.fuzzy_text_score,
                                "duration_score": result.duration_match_score,
                                "quality_bonus": result.quality_bonus_applied,
                                "version_penalty": result.version_penalty_applied,
                                "edition_penalty": result.edition_penalty_applied,
                            },
                            "reasoning": result.reasoning,
                        })

                        if result.confidence_score >= 70:
                            valid_candidates.append({
                                "id": candidate_row[0],
                                "score": result.confidence_score,
                                "target_identifier": candidate_target_id,
                                "title": candidate_track.title,
                                "artist": candidate_track.artist_name,
                            })

                        if result.confidence_score > best_score:
                            best_score = result.confidence_score
                            best_match = (candidate_row[0], result)
                            best_match_track_id = candidate_row[0]
                            best_match_target_id = candidate_target_id

                        if result.is_near_miss and near_miss_candidate_id is None:
                            near_miss_candidate_id = candidate_row[0]

                    from services.playlists_api import check_cover_rejection
                    had_cover_rejection = check_cover_rejection(
                        source_track.title or track_title,
                        source_track.artist_name or track_artist,
                        candidate_diagnostics,
                    )

                    tier2_needed_due_to_version = (
                        not tier2_mode and len(candidates) > 0 and best_score == 0.0 and
                        all(not d["result"]["passed_version"] for d in candidate_diagnostics)
                    )
                    tier2_needed_due_to_failure = (
                        not tier2_mode and len(candidates) > 0 and best_score < 70 and track_duration
                    )

                    if had_cover_rejection:
                        logger.debug(
                            f"[system] Tier 2 escalation skipped for '{track_title}' by '{track_artist}': "
                            f"detected cover version by distinct artist."
                        )
                        tier2_needed_due_to_version = False
                        tier2_needed_due_to_failure = False

                    if tier2_needed_due_to_version or tier2_needed_due_to_failure:
                        logger.debug(
                            (
                                f"Tier 2 escalation triggered for '{track_title}' by '{track_artist}'. "
                                + ("Reason: version mismatch." if tier2_needed_due_to_version else "Reason: no acceptable Tier 1 match.")
                            )
                        )

                        candidates = []
                        valid_candidates = []
                        candidate_diagnostics = []
                        best_score = 0
                        best_match = None
                        near_miss_candidate_id = None

                        if track_duration:
                            # Sanitize source title for Tier 2 rescoring (strip remix/version/descriptor noise)
                            from core.matching_engine.text_utils import normalize_title
                            clean_t2_source_title = normalize_title(source_track.raw_title or source_track.title or "")
                            if clean_t2_source_title:
                                source_track.title = clean_t2_source_title
                            t2_search_title = clean_t2_source_title or search_title

                            # Escalation Tier 2: widen to ±10000ms — wider than the engine's
                            # 8500ms Artist Match Duration Escalation ceiling so a confident
                            # artist match is never blocked at the SQL layer. Python scoring
                            # discriminates; the SQL window is just a coarse pre-filter.
                            # (Previously 5000ms — raised to 10000ms.)
                            sql_duration_tolerance_ms = 10000
                            duration_min = track_duration - sql_duration_tolerance_ms
                            duration_max = track_duration + sql_duration_tolerance_ms

                            with db.engine.connect() as tier2_conn:
                                tier2_raw_candidates = _fetch_tier2_candidates(
                                    tier2_conn, t2_search_title, track_duration,
                                    sql_duration_tolerance_ms,
                                )
                                candidates = [c for c in tier2_raw_candidates if c[0] not in evaluated_candidate_ids]

                            if candidates:
                                logger.debug(
                                    f"Tier 2 escalation found {len(candidates)} new title+duration matches for '{track_title}'. "
                                    f"Re-scoring with Tier 2 profile..."
                                )

                                external_ids_map = {}
                                if target_source:
                                    candidate_ids = [row[0] for row in candidates]
                                    try:
                                        external_ids_map = db.get_external_identifier_map(target_source, candidate_ids)
                                    except Exception as ext_err:
                                        logger.debug(f"External identifier lookup failed for Tier 2: {ext_err}")

                                # Batch-fetch aliases for all Tier 2 escalation candidates.
                                _t2_alias_map: dict = {}
                                try:
                                    _t2_cids = [int(r[0]) for r in candidates]
                                    with db.engine.connect() as _t2_ac:
                                        for _t2_ar in _t2_ac.execute(
                                            text(
                                                "SELECT track_id, name FROM track_aliases"
                                                " WHERE track_id IN ("
                                                + ",".join(str(c) for c in _t2_cids)
                                                + ")"
                                            )
                                        ).fetchall():
                                            _t2_alias_map.setdefault(_t2_ar[0], []).append(_t2_ar[1])
                                except Exception:
                                    _t2_alias_map = {}

                                # Batch-fetch artist aliases for Tier 2 escalation candidates.
                                _t2_artist_alias_map: dict = {}
                                try:
                                    _t2_artist_ids = list({int(r[5]) for r in candidates if r[5] is not None})
                                    if _t2_artist_ids:
                                        with db.engine.connect() as _t2_aac:
                                            for _t2_aar in _t2_aac.execute(
                                                text(
                                                    "SELECT artist_id, name FROM artist_aliases"
                                                    " WHERE artist_id IN ("
                                                    + ",".join(str(a) for a in _t2_artist_ids)
                                                    + ")"
                                                )
                                            ).fetchall():
                                                _t2_artist_alias_map.setdefault(_t2_aar[0], []).append(_t2_aar[1])
                                except Exception:
                                    _t2_artist_alias_map = {}

                                for candidate_row in candidates:
                                    evaluated_candidate_ids.add(candidate_row[0])
                                    candidate_target_id = external_ids_map.get(candidate_row[0]) if target_source else None
                                    raw_title_candidate = candidate_row[1]
                                    edition_candidate = candidate_row[3]
                                    sort_title_candidate = None
                                    try:
                                        sort_title_candidate = candidate_row[6]
                                    except Exception:
                                        sort_title_candidate = None

                                    if edition_candidate is None and sort_title_candidate and sort_title_candidate != raw_title_candidate:
                                        version_pattern = r'\b(Remix|Mix|Live|Demo|Remaster|Deluxe|Edit|Version|Acoustic|Instrumental|Bonus|Extended|Original)\b'
                                        version_match = re.search(version_pattern, sort_title_candidate, re.IGNORECASE)
                                        if version_match:
                                            edition_candidate = version_match.group(0)

                                    candidate_track = EchosyncTrack(
                                        raw_title=raw_title_candidate,
                                        artist_name=candidate_row[4],
                                        album_title=candidate_row[7] or "",
                                        duration=candidate_row[2] if candidate_row[2] else 0,
                                        edition=edition_candidate,
                                    )
                                    # Populate candidate plugin_context for the Tier 2
                                    # escalation path as well.
                                    hook_manager.apply_filters(
                                        'pre_normalize_title',
                                        candidate_track.raw_title,
                                        plugin_context=candidate_track.plugin_context,
                                    )

                                    # ── Normalize candidate title & promote best alias ─────
                                    _t2_clean = _normalize_candidate_title(
                                        raw_title_candidate,
                                        plugin_context=candidate_track.plugin_context,
                                    )
                                    _t2_best_title = _t2_clean or candidate_track.title
                                    # Context guard for Tier 2 Semantic Substring Failsafe.
                                    _t2_artist_ctx = (
                                        _cmp_artists(source_track.artist_name, candidate_row[4])
                                        if source_track.artist_name and candidate_row[4]
                                        else 0.0
                                    )
                                    _t2_drama_ctx = bool(
                                        (candidate_track.plugin_context or {}).get('remote_drama')
                                    )
                                    _t2_best_score = _cmp_titles(
                                        source_track.title, _t2_best_title,
                                        context_score=_t2_artist_ctx, drama_ctx=_t2_drama_ctx,
                                    )
                                    for _t2_alias in _t2_alias_map.get(candidate_row[0], []):
                                        if not _t2_alias:
                                            continue
                                        _t2_alias_clean = _normalize_candidate_title(_t2_alias)
                                        _t2_alias_score = _cmp_titles(
                                            source_track.title, _t2_alias_clean,
                                            context_score=_t2_artist_ctx, drama_ctx=_t2_drama_ctx,
                                        )
                                        if _t2_alias_score > _t2_best_score:
                                            _t2_best_score = _t2_alias_score
                                            _t2_best_title = _t2_alias_clean
                                    if _t2_best_title and _t2_best_title != candidate_track.title:
                                        candidate_track.title = _t2_best_title

                                    # ── Promote best artist alias (Tier 2) ────────────────────────
                                    _t2_best_artist_score = 0.0
                                    if source_track.artist_name:
                                        _t2_best_artist = candidate_track.artist_name or ''
                                        _t2_best_artist_score = _cmp_artists(source_track.artist_name, _t2_best_artist)
                                        for _t2_artist_alias in _t2_artist_alias_map.get(candidate_row[5], []):
                                            if not _t2_artist_alias:
                                                continue
                                            _t2_a_score = _cmp_artists(source_track.artist_name, _t2_artist_alias)
                                            if _t2_a_score > _t2_best_artist_score:
                                                _t2_best_artist_score = _t2_a_score
                                                _t2_best_artist = _t2_artist_alias
                                        if _t2_best_artist and _t2_best_artist != candidate_track.artist_name:
                                            candidate_track.artist_name = _t2_best_artist

                                    # If a new Tier 2 candidate matches the requested artist (artist_score >= 0.90),
                                    # evaluate with full artist score confidence and allow standard acceptance.
                                    if _t2_best_artist_score >= 0.90:
                                        result = matching_engine.calculate_match(
                                            source_track,
                                            candidate_track,
                                            target_source=target_source_canonical,
                                            target_identifier=candidate_target_id,
                                        )
                                        if result.confidence_score < 70.0:
                                            t2_res = matching_engine.calculate_title_duration_match(
                                                source_track,
                                                candidate_track,
                                                target_source=target_source_canonical,
                                                target_identifier=candidate_target_id,
                                            )
                                            if t2_res.confidence_score > result.confidence_score:
                                                result = t2_res
                                    else:
                                        result = matching_engine.calculate_title_duration_match(
                                            source_track,
                                            candidate_track,
                                            target_source=target_source_canonical,
                                            target_identifier=candidate_target_id,
                                        )

                                    logger.debug(f"Tier 2 re-score: '{track_title}' vs '{candidate_track.title}': {result.confidence_score}")

                                    candidate_diagnostics.append({
                                        "candidate": {
                                            "title": candidate_track.title,
                                            "artist": candidate_track.artist_name,
                                            "duration": candidate_track.duration or 0,
                                        },
                                        "result": {
                                            "score": result.confidence_score,
                                            "passed_version": result.passed_version_check,
                                            "passed_edition": result.passed_edition_check,
                                            "fuzzy_text": result.fuzzy_text_score,
                                            "duration_score": result.duration_match_score,
                                            "quality_bonus": result.quality_bonus_applied,
                                            "version_penalty": result.version_penalty_applied,
                                            "edition_penalty": result.edition_penalty_applied,
                                        },
                                        "reasoning": result.reasoning,
                                    })

                                    if result.confidence_score >= 70:
                                        valid_candidates.append({
                                            "id": candidate_row[0],
                                            "score": result.confidence_score,
                                            "target_identifier": candidate_target_id,
                                            "title": candidate_track.title,
                                            "artist": candidate_track.artist_name,
                                        })

                                    if result.confidence_score > best_score:
                                        best_score = result.confidence_score
                                        best_match = (candidate_row[0], result)
                                        best_match_track_id = candidate_row[0]
                                        best_match_target_id = candidate_target_id

                                    if result.is_near_miss and near_miss_candidate_id is None:
                                        near_miss_candidate_id = candidate_row[0]

                                tier2_mode = True

                    # Tier 3 Deluxe Fallback:
                    # Only considered when both Tier 1 and Tier 2 fail to find an acceptable match (best_score < 70).
                    # Re-evaluates candidates with context="tier3_fallback" where deluxe editions are permitted (delta <= 10000ms).
                    if best_score < 70 and initial_candidates:
                        for candidate_row in initial_candidates:
                            candidate_target_id = external_ids_map.get(candidate_row[0]) if target_source_canonical else None
                            raw_title_candidate = candidate_row[1]
                            edition_candidate = candidate_row[3]
                            sort_title_candidate = None
                            try:
                                sort_title_candidate = candidate_row[6]
                            except Exception:
                                sort_title_candidate = None

                            if edition_candidate is None and sort_title_candidate and sort_title_candidate != raw_title_candidate:
                                version_pattern = r'\b(Remix|Mix|Live|Demo|Remaster|Deluxe|Edit|Version|Acoustic|Instrumental|Bonus|Extended|Original)\b'
                                version_match = re.search(version_pattern, sort_title_candidate, re.IGNORECASE)
                                if version_match:
                                    edition_candidate = version_match.group(0)

                            from core.matching_engine.text_utils import parse_duration_to_ms
                            candidate_track = EchosyncTrack(
                                raw_title=raw_title_candidate,
                                artist_name=candidate_row[4],
                                album_title=candidate_row[7] or "",
                                duration=parse_duration_to_ms(candidate_row[2]) if candidate_row[2] else 0,
                                edition=edition_candidate,
                            )
                            hook_manager.apply_filters(
                                'pre_normalize_title',
                                candidate_track.raw_title,
                                plugin_context=candidate_track.plugin_context,
                            )

                            result = matching_engine.calculate_match(
                                source_track, candidate_track,
                                target_source=target_source_canonical or target_source,
                                target_identifier=candidate_target_id,
                                context="tier3_fallback",
                            )

                            if result.confidence_score >= 70:
                                valid_candidates.append({
                                    "id": candidate_row[0],
                                    "score": result.confidence_score,
                                    "target_identifier": candidate_target_id,
                                    "title": candidate_track.title,
                                    "artist": candidate_track.artist_name,
                                })

                            if result.confidence_score > best_score:
                                best_score = result.confidence_score
                                best_match = (candidate_row[0], result)
                                best_match_track_id = candidate_row[0]
                                best_match_target_id = candidate_target_id

                    if best_score >= 85:
                        library_match = "Found"
                        found_count += 1
                    elif best_score >= 70:
                        library_match = f"Found (score: {int(best_score)}%)"
                        found_count += 1
                    else:
                        library_match = "Not Found"
                        missing_count += 1
                        if near_miss_candidate_id is not None:
                            try:
                                from core.suggestion_engine.discovery import recommend_near_miss
                                recommend_near_miss(
                                    user_id=acc_id if acc_id else source,
                                    music_db_track_id=near_miss_candidate_id,
                                    context={
                                        "source_title": track_title,
                                        "source_artist": track_artist,
                                        "source_duration_ms": track_duration,
                                        "target_context": f"{target_source or source} sync",
                                    },
                                )
                                logger.debug(
                                    f"Near-miss suggestion queued for '{track_title}' "
                                    f"-> track_id={near_miss_candidate_id}"
                                )
                            except Exception as nm_err:
                                logger.warning(f"Failed to queue near-miss suggestion: {nm_err}")
                        if logger.isEnabledFor(logging.DEBUG):
                            try:
                                src_dur = source_track.duration or 0
                                logger.debug(
                                    f"Unmatched: '{track_title}' by '{track_artist}' (duration: {src_dur} ms). "
                                    f"Considered {len(candidate_diagnostics)} candidates."
                                )
                                top_candidates = sorted(candidate_diagnostics, key=lambda c: c["result"]["score"], reverse=True)[:5]
                                for idx, diag in enumerate(top_candidates, start=1):
                                    cand = diag["candidate"]
                                    res = diag["result"]
                                    logger.debug(
                                        (
                                            f"  Candidate {idx}: '{cand['title']}' by '{cand['artist']}' "
                                            f"(duration: {cand['duration']} ms) → score {res['score']:.1f} | "
                                            f"version_pass={res['passed_version']}, edition_pass={res['passed_edition']}, "
                                            f"fuzzy={res['fuzzy_text']:.2f}, duration={res['duration_score']:.2f}, "
                                            f"penalties=V-{res['version_penalty']:.1f} E-{res['edition_penalty']:.1f}, "
                                            f"quality=+{res['quality_bonus']:.1f}"
                                        )
                                    )
                                    logger.debug(f"    Reasoning: {diag['reasoning']}")
                            except Exception as log_err:
                                logger.debug(f"Verbose unmatched diagnostics failed: {log_err}")

                    if best_match:
                        logger.info(f"Matched '{track_title}' with database track (score: {best_score:.0f}%)")

                except Exception as e:
                    logger.error(f"Error searching for track '{track_title}' by '{track_artist}': {e}", exc_info=True)
                    missing_count += 1
                    best_match_track_id = None
                    best_match_target_id = None

                duration_str = "–"
                if track_duration:
                    mins = track_duration // 60000
                    secs = (track_duration % 60000) // 1000
                    duration_str = f"{mins}:{secs:02d}"

                all_tracks.append({
                    "playlist": playlist_name,
                    "title": track_title,
                    "artist": track_artist,
                    "album": track_album,
                    "duration": duration_str,
                    "duration_ms": track_duration,
                    "isrc": getattr(source_track, "isrc", None),
                    "library_match": library_match,
                    "download_status": "-",
                    "matched_track_id": best_match_track_id,
                    "match_score": best_score,
                    "rejection_reason": "Cover version detected: local tracks with title exist under distinct artist(s)" if (had_cover_rejection and best_score < 70) else None,
                    "candidate_matches": valid_candidates,
                    "target_source": target_source_canonical or target_source,
                    "target_identifier": best_match_target_id,
                    "target_exists": bool(best_match_target_id),
                    "source_track": source_track.to_dict() if hasattr(source_track, "to_dict") else None,
                    "source_identifier": (
                        None if not getattr(source_track, 'identifiers', None) else (
                            source_track.identifiers.get(source)
                            if isinstance(source_track.identifiers, dict) and source in source_track.identifiers
                            else next(iter(source_track.identifiers.values()), None)
                            if isinstance(source_track.identifiers, dict) and source_track.identifiers
                            else None
                        )
                    ),
                })

        except Exception as e:
            logger.error(f"Error fetching tracks for playlist {playlist_name}: {e}", exc_info=True)
            all_tracks.append({
                "playlist": playlist_name,
                "title": f"Error: {str(e)}",
                "artist": "–",
                "album": "–",
                "duration": "–",
                "library_match": "Error",
                "download_status": "-",
            })

    from services.playlists_api import resolve_duplicate_matches
    all_tracks = resolve_duplicate_matches(all_tracks)

    total_tracks = len(all_tracks)
    found_count = sum(1 for t in all_tracks if t.get("matched_track_id"))
    missing_count = total_tracks - found_count

    try:
        matched_map = {}
        for t in all_tracks:
            mid = t.get("matched_track_id")
            if not mid:
                continue
            matched_map.setdefault(mid, []).append(t)

        duplicate_matches = {k: v for k, v in matched_map.items() if len(v) > 1}
        if duplicate_matches and logger.isEnabledFor(logging.DEBUG):
            logger.debug("[system] - Duplicate match analysis: found %d Echosync tracks matched by multiple source tracks", len(duplicate_matches))
            for echo_id, entries in duplicate_matches.items():
                try:
                    lines = []
                    for e in entries:
                        src_id = e.get("source_identifier") or "<unknown_source_id>"
                        lines.append(f"{src_id} ('{e.get('title')}' by '{e.get('artist')}')")
                    logger.debug(f"[system] - Duplicate match: {', '.join([f'{l} matched EchosyncTrack {echo_id}' for l in lines])}")
                except Exception as dup_err:
                    logger.debug(f"[system] - Duplicate match formatting failed for EchosyncTrack {echo_id}: {dup_err}")
    except Exception as dup_all_err:
        logger.debug(f"[system] - Duplicate match analysis failed: {dup_all_err}")

    matched_pairs = []
    missing_tracks = []
    for track in all_tracks:
        if track.get("matched_track_id") and track.get("target_identifier"):
            matched_pairs.append({
                "track_id": track["matched_track_id"],
                "target_identifier": track["target_identifier"],
            })
        elif not track.get("matched_track_id"):
            missing_tracks.append({
                "title": track["title"],
                "artist": track["artist"],
                "album": track["album"],
                "duration": track.get("duration_ms"),
                "duration_ms": track.get("duration_ms"),
                "isrc": track.get("isrc"),
                "source_identifier": track.get("source_identifier"),
                "source_track": track.get("source_track"),
                "rejection_reason": track.get("rejection_reason"),
            })

    return {
        "summary": {
            "total_tracks": total_tracks,
            "found_in_library": found_count,
            "missing_tracks": missing_count,
            "downloaded": 0,
            "quality_profile": quality_profile,
            "source": source,
            "target": target_source_canonical or target_source,
            "matched_pairs": matched_pairs,
            "can_sync": len(matched_pairs) > 0,
        },
        "tracks": all_tracks,
        "missing": missing_tracks,
    }

@router.get("/")
def list_playlists(request: Request):
    # Placeholder: surface playlists via provider adapters (future)
    return {"items": [], "total": 0}

@router.post("/analyze")
def analyze_playlists(payload_obj: Optional[PlaylistAnalyzeSchema] = None):
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


@router.post("/analyze/start")
def start_analyze_job(payload_obj: Optional[PlaylistAnalyzeSchema] = None):
    """Start playlist analysis as a background job and return a job_id to poll."""
    payload = payload_obj.model_dump(exclude_unset=True) if payload_obj else {}
    source = str(payload.get('source')) if payload.get('source') is not None else None
    target = str(payload.get('target')) if payload.get('target') is not None else None
    target_source = str(payload.get('target_source')) if payload.get('target_source') is not None else target
    playlists = payload.get('playlists') or []
    quality_profile = payload.get('quality_profile', 'Auto')

    if not source:
        return {"error": "source provider required"}
    if not playlists:
        return {"error": "playlists list required"}

    job_id = str(uuid.uuid4())
    job_name = f"playlist_analyze:{job_id}"

    # Initialize job record
    ANALYSIS_JOBS[job_id] = {
        'status': 'queued',
        'started_at': None,
        'finished_at': None,
        'result': None,
        'error': None,
    }

    def _job_func():
        ANALYSIS_JOBS[job_id]['status'] = 'running'
        ANALYSIS_JOBS[job_id]['started_at'] = time.time()
        try:
            res = _analyze_playlists_internal(source, target_source, playlists, quality_profile)
            ANALYSIS_JOBS[job_id]['result'] = res
            ANALYSIS_JOBS[job_id]['status'] = 'finished'
        except Exception as e:
            logger.error(f"Background analysis job {job_id} failed: {e}", exc_info=True)
            ANALYSIS_JOBS[job_id]['error'] = str(e)
            ANALYSIS_JOBS[job_id]['status'] = 'failed'
        finally:
            ANALYSIS_JOBS[job_id]['finished_at'] = time.time()

    # Register a one-off job and execute it immediately
    from core.nexus_framework.plugin_SDK import PlaylistSupport
    from core.nexus_framework.plugin_loader import get_plugin_capabilities

    source_caps = get_plugin_capabilities(source)
    if not source_caps:
        return {'error': f'Source plugin {source} not found'}
        
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
        'status': rec.get('status'),
        'started_at': rec.get('started_at'),
        'finished_at': rec.get('finished_at'),
        'error': rec.get('error'),
    }
    if rec.get('status') == 'finished':
        payload['result'] = rec.get('result')
    return payload


@router.post("/sync")
def trigger_sync(payload_obj: PlaylistSyncSchema):
    payload = payload_obj.model_dump(exclude_unset=True) if payload_obj else {}
    target = payload.get("target_source") or payload.get("target")
    playlist_name = payload.get("playlist_name")
    matches = payload.get("matches") or []
    download_missing = payload.get("download_missing", False)
    source = payload.get("source", "unknown")

    if not target:
        return {"accepted": False, "error": "target_source required"}

    if not playlist_name:
        return {"accepted": False, "error": "playlist_name required"}

    from core.nexus_framework.plugin_SDK import PlaylistSupport
    from core.nexus_framework.plugin_loader import get_plugin_capabilities

    try:
        source_caps = get_plugin_capabilities(source)
        if source_caps.supports_playlists not in (PlaylistSupport.READ, PlaylistSupport.READ_WRITE):
            return {"accepted": False, "error": f"Source provider {source} does not support reading playlists"}
    except KeyError:
        return {"accepted": False, "error": f"Source provider {source} not found"}

    try:
        target_caps = get_plugin_capabilities(target)
        if target_caps.supports_playlists != PlaylistSupport.READ_WRITE:
            return {"accepted": False, "error": f"Target provider {target} does not support writing playlists"}
    except KeyError:
        return {"accepted": False, "error": f"Target provider {target} not found"}

    # Detect sync mode: tier-to-tier (streaming↔streaming) vs local-server (streaming→server)
    is_source_tier = getattr(source_caps, 'supports_streaming', False)
    is_target_tier = getattr(target_caps, 'supports_streaming', False)
    is_source_server = getattr(source_caps, 'supports_library_scan', False)
    is_target_server = getattr(target_caps, 'supports_library_scan', False)
    
    sync_mode = None
    if is_source_tier and is_target_tier:
        sync_mode = "tier-to-tier"
    elif is_source_tier and is_target_server:
        sync_mode = "local-server"
    elif is_source_server and is_target_tier:
        sync_mode = "server-to-tier"
    else:
        sync_mode = "unknown"
    
    logger.info(f"Sync mode detected: {sync_mode} ({source} → {target})")

    # For non-Plex targets, return not implemented
    canonical_target = _normalize_provider_short_name(target)
    if canonical_target == "plex" or target == "plex":
        # Local-server sync: add tracks to managed playlist with overwrite
        source_account_name = payload.get("source_account_name")
        target_user_id = payload.get("target_user_id")
        return _sync_to_plex(payload, source, canonical_target, playlist_name, matches, download_missing, sync_mode, source_account_name, target_user_id)
    elif target in tier_to_tier_providers or canonical_target in tier_to_tier_providers:
        # Tier-to-tier sync: add tracks to target provider's playlist
        return _sync_to_tier(payload, source, canonical_target, playlist_name, matches, download_missing, sync_mode)
    else:
        return {"accepted": False, "error": f"Sync to {target} not implemented"}


def _sync_to_plex(payload, source, target, playlist_name, matches, download_missing, sync_mode, source_account_name=None, target_user_id=None):
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
        logger.info(f"[{job_name}] Starting Plex sync for playlist '{playlist_name}' with {total} tracks")
        event_bus.publish(job_name, "sync_started", {
            "playlist": playlist_name,
            "target": target,
            "total": total,
            "download_missing": download_missing,
            "sync_mode": sync_mode,
        })

        client = None
        try:
            from plugins.EchoSync.plex.client import PlexClient
            client = PlexClient()
        except ImportError:
            try:
                from core.nexus_framework.plugin_loader import PluginRegistry
                PlexCls = PluginRegistry.get_plugin_class('EchoSync.plex') or PluginRegistry.get_plugin_class('plex')
                if PlexCls:
                    client = PlexCls()
                else:
                    client = PluginRegistry.get_plugin_instance('EchoSync.plex') or PluginRegistry.get_plugin_instance('plex')
            except Exception as reg_err:
                logger.warning(f"PluginRegistry resolution of Plex failed: {reg_err}")

        if not client:
            err_msg = "Plex plugin is disabled, unconfigured, or could not be loaded"
            logger.error(f"[{job_name}] {err_msg}")
            event_bus.publish(job_name, "sync_failed", {
                "playlist": playlist_name,
                "error": err_msg,
            })
            return

        try:
            if not client.ensure_connection():
                raise RuntimeError("Plex connection failed")

            valid_keys = []
            for idx, rk in enumerate(rating_keys):
                logger.debug(f"[{job_name}] Processing track {idx + 1}/{total} (ratingKey: {rk}, type: {type(rk).__name__})")
                event_bus.publish(job_name, "track_started", {
                    "index": idx,
                    "rating_key": rk,
                    "total": total,
                })
                try:
                    # Ensure ratingKey is an integer
                    try:
                        rk_int = int(rk) if rk else None
                    except (ValueError, TypeError):
                        raise RuntimeError(f"Invalid ratingKey format: {rk}")
                    
                    if not rk_int:
                        raise RuntimeError("Empty or invalid ratingKey")
                    
                    item = client.server.fetchItem(rk_int) if client.server else None
                    if not item:
                        raise RuntimeError("Track not found on Plex")
                    valid_keys.append(rk)
                    logger.debug(f"[{job_name}] Track {idx + 1} synced successfully")
                    event_bus.publish(job_name, "track_synced", {
                        "index": idx,
                        "rating_key": rk,
                    })
                except Exception as fe:
                    logger.warning(f"[{job_name}] Track {idx + 1} failed: {str(fe)}")
                    event_bus.publish(job_name, "track_failed", {
                        "index": idx,
                        "rating_key": rk,
                        "error": str(fe),
                    })

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
            event_bus.publish(job_name, "playlist_updated", {
                "playlist": playlist_name,
                "synced": len(valid_keys),
                "failed": total - len(valid_keys),
                "updated": bool(updated),
            })

            try:
                from core.hook_manager import hook_manager
                hook_manager.apply_filters('ON_PLAYLIST_SAVED', None, playlist_name=playlist_name, target=target, synced_count=len(valid_keys))
            except Exception as e:
                logger.error(f"Error in ON_PLAYLIST_SAVED hook: {e}")

            logger.info(f"[{job_name}] Sync complete: {len(valid_keys)} synced, {total - len(valid_keys)} failed")
            event_bus.publish(job_name, "sync_complete", {
                "playlist": playlist_name,
                "synced": len(valid_keys),
                "failed": total - len(valid_keys),
                "target": target,
                "sync_mode": sync_mode,
            })
            
            # Record in history
            sync_history.record_sync(
                source=source,
                target=target,
                playlist=playlist_name,
                total=total,
                synced=len(valid_keys),
                failed=total - len(valid_keys),
                download_missing=download_missing,
                job_name=job_name,
            )
        except Exception as e:
            logger.error(f"[{job_name}] Sync error: {str(e)}")
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
    # Collect provider-specific IDs from matches (target_identifier for tier target)
    track_ids = [m.get("target_identifier") for m in matches if m.get("target_identifier")]
    if not track_ids:
        return {"accepted": False, "error": f"No {target} track IDs provided in matches"}

    # Schedule a one-off sync job
    job_name = f"sync:{target}:{playlist_name}:{int(time.time())}"

    def _run_sync():
        logger.info(f"[{job_name}] Starting {target} sync for playlist '{playlist_name}' with {len(track_ids)} tracks")
        event_bus.publish(job_name, "sync_started", {
            "playlist": playlist_name,
            "target": target,
            "total": len(track_ids),
            "download_missing": download_missing,
            "sync_mode": sync_mode,
        })

        try:
            from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
            target_provider = PluginRegistry.get_plugin(target)
            
            if not target_provider:
                raise RuntimeError(f"Plugin {target} not found")

            # Add tracks to target provider's playlist
            synced = 0
            failed = 0
            
            for idx, track_id in enumerate(track_ids):
                logger.debug(f"[{job_name}] Processing track {idx + 1}/{len(track_ids)} (ID: {track_id})")
                event_bus.publish(job_name, "track_started", {
                    "index": idx,
                    "track_id": track_id,
                    "total": len(track_ids),
                })
                try:
                    # Provider-specific add-to-playlist logic
                    target_provider.add_to_playlist(playlist_name, track_id)
                    synced += 1
                    logger.debug(f"[{job_name}] Track {idx + 1} synced successfully")
                    event_bus.publish(job_name, "track_synced", {
                        "index": idx,
                        "track_id": track_id,
                    })
                except Exception as fe:
                    failed += 1
                    logger.warning(f"[{job_name}] Track {idx + 1} failed: {str(fe)}")
                    event_bus.publish(job_name, "track_failed", {
                        "index": idx,
                        "track_id": track_id,
                        "error": str(fe),
                    })

            logger.info(f"[{job_name}] Sync complete: {synced} synced, {failed} failed")
            event_bus.publish(job_name, "sync_complete", {
                "playlist": playlist_name,
                "synced": synced,
                "failed": failed,
                "target": target,
                "sync_mode": sync_mode,
            })
            
            # Record in history
            sync_history.record_sync(
                source=source,
                target=target,
                playlist=playlist_name,
                total=len(track_ids),
                synced=synced,
                failed=failed,
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
def sync_events(request: Request, job: Optional[str] = None, since: Optional[Union[int, str]] = None):
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


for extra_r in (api_v1_router, legacy_router):
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
    
    if not missing:
        return {"accepted": False, "error": "missing tracks list required"}
    
    try:
        from services.download_manager import get_download_manager
        from core.db.echo_sync_track import EchosyncTrack
        
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
                download_id = download_manager.queue_download(track)

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
        return {
            "genres": genres,
            "total": len(genres)
        }
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
        return {
            "genre": genre_name,
            "tracks": tracks,
            "total": len(tracks)
        }
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
        return {
            "decade": decade,
            "tracks": tracks,
            "total": len(tracks)
        }
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
        return {
            "name": "Popular Picks",
            "tracks": tracks,
            "total": len(tracks)
        }
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
        return {
            "name": "Hidden Gems",
            "tracks": tracks,
            "total": len(tracks)
        }
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
        return {
            "name": "Discovery Shuffle",
            "tracks": tracks,
            "total": len(tracks)
        }
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
        return {
            "mixes": mixes,
            "total": len(mixes)
        }
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
                    _sync_to_plex({
                        "source": source,
                        "target": target,
                        "target_user_id": primary_playlist.get('target_user_id'),
                        "source_account_name": primary_playlist.get('source_account_name'),
                    }, source, target, playlist_name, matches, download_missing, "scheduled")
                elif target in {"spotify", "tidal", "apple_music"}:
                    _sync_to_tier({
                        "source": source,
                        "target": target,
                    }, source, target, playlist_name, matches, download_missing, "scheduled")
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

