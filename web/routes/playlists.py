import logging
import re
from difflib import SequenceMatcher
from urllib.parse import quote
from flask import Blueprint, jsonify, request
from web.services.sync_service import SyncAdapter
from core.personalized_playlists import get_personalized_playlists_service
from database.music_database import MusicDatabase
from core.tiered_logger import get_logger
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import ScoringProfile
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.matching_engine.text_utils import normalize_title as _normalize_candidate_title
from core.job_queue import job_queue
from core.event_bus import event_bus
from core.sync_history import sync_history
from core.hook_manager import hook_manager
import time

logger = get_logger("playlists_api")
bp = Blueprint("playlists", __name__, url_prefix="/api/playlists")

# ── Semantic Substring Failsafe — safe OST filler dictionary ──────────────────
# Words that commonly appear in longer CJK/English OST title variants but do NOT
# change the track's identity.  If a title delta (the extra part of the longer
# string after the shared shorter title is removed) is composed *entirely* of
# these words the two strings refer to the same track and a 0.95 title score is
# awarded.  Any unrecognised token (e.g. 'Part 2', 'Remix', 'Live') causes the
# substring boost to be withheld, preventing false-positive Swap Cases.
_OST_SAFE_RE = re.compile(
    r'^(?:'
    r'\s*'                                           # whitespace between tokens
    r'|电视剧|网剧|影视剧|影視劇|电影'              # drama-type classifiers
    r'|片头曲|片尾曲|主题曲|插曲|推广曲'             # song-role labels
    r'|原声带|原声|配乐'                              # soundtrack labels
    r'|ost|theme|opening|ending|soundtrack|original'  # English equivalents
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


def _get_provider_for_account(provider_name, acc_id=None):
    from core.provider import ProviderRegistry

    if provider_name in ['spotify', 'tidal']:
        if acc_id is None:
            from core.file_handling.storage import get_storage_service

            storage = get_storage_service()
            accounts = storage.list_accounts(provider_name)
            if not accounts:
                return None, None
            acc_id_local = accounts[0]['id']
        else:
            acc_id_local = acc_id

        if provider_name == 'spotify':
            from providers.spotify.client import SpotifyClient

            return SpotifyClient(account_id=acc_id_local), acc_id_local
        if provider_name == 'tidal':
            from providers.tidal.client import TidalClient

            return TidalClient(account_id=str(acc_id_local)), acc_id_local

    try:
        return ProviderRegistry.create_instance(provider_name), None
    except ValueError:
        return None, None


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


def _cmp_artists(a: str, b: str) -> float:
    """Artist similarity score (0–1) with substring-containment boost.

    Normalises both strings identically to _cmp_titles, then returns the
    SequenceMatcher ratio OR 0.95 (whichever is higher) when one normalised
    form is fully contained in the other.  The 0.95 floor handles credit-group
    names like '摩登兄弟刘宇宁' vs '刘宇宁' and romanisation variants like
    'Zhou Shen' (alias) vs '周深' (primary), without conflating unrelated artists.
    """
    def _n(s: str) -> str:
        s = s.lower()
        s = re.sub(r'[^\w\s]', '', s)
        return ' '.join(s.split())

    a_n, b_n = _n(a), _n(b)
    if not a_n or not b_n:
        return 0.0
    ratio = SequenceMatcher(None, a_n, b_n).ratio()
    # Substring containment: one name is fully inside the other — very likely the same artist.
    if a_n in b_n or b_n in a_n:
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

    # Artist-anchored conditions — identical semantics to the original Tier 1 SQL
    # but the title side now also searches sort_title and aliases.
    base_where = (
        f"(LOWER(a.name) = LOWER(:artist_exact) AND {_am('title_pattern')})\n"
        f"        OR (LOWER(a.name) LIKE LOWER(:artist_pattern) AND LOWER(t.title) = LOWER(:title_exact))\n"
        f"        OR (LOWER(a.name) LIKE LOWER(:artist_pattern) AND {_am('title_pattern')})\n"
        f"        OR (LOWER(a.name) LIKE LOWER(:artist_pattern) AND {_am('base_title_pattern')})\n"
        f"        OR (LOWER(a.name) = LOWER(:artist_exact) AND {_am('base_title_pattern')})\n"
        f"        OR (LOWER(a.name) = LOWER(:artist_exact)\n"
        f"            AND LOWER(REPLACE(REPLACE(t.title, char(8217), char(39)), char(8216), char(39)))"
        f" LIKE LOWER(:title_norm_pattern))\n"
        f"        OR (LOWER(a.name) LIKE LOWER(:artist_pattern)\n"
        f"            AND LOWER(REPLACE(REPLACE(t.title, char(8217), char(39)), char(8216), char(39)))"
        f" LIKE LOWER(:title_norm_pattern))"
    )

    # Plugin-expanded terms: no artist anchor — covers 'Various Artists' mis-tags.
    exp_parts = []
    for i, term in enumerate(clean_expanded):
        pkey = f"exp_{i}"
        params[pkey] = f"%{term}%"
        exp_parts.append(_am(pkey))
    exp_where = ("\n        OR " + "\n        OR ".join(exp_parts)) if exp_parts else ""

    sql = _sql(f"""
        SELECT DISTINCT t.id, t.title, t.duration, t.edition,
               a.name AS artist_name, a.id AS artist_id,
               t.sort_title, al.title AS album_title
        FROM tracks t
        JOIN artists a ON t.artist_id = a.id
        LEFT JOIN albums al ON t.album_id = al.id
        WHERE ({base_where}{exp_where})
        ORDER BY
            (LOWER(a.name) = LOWER(:artist_exact)) DESC,
            (LOWER(t.title) = LOWER(:title_exact)) DESC,
            ABS(t.duration - :duration) ASC
        LIMIT 20
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
        "duration":     track_duration,
        "duration_min": duration_min,
        "duration_max": duration_max,
    }

    # Base title-exact conditions (original Tier 2) plus alias equality match.
    base_where = (
        "LOWER(t.title) = LOWER(:title_exact)\n"
        "        OR LOWER(REPLACE(REPLACE(t.title, char(8217), char(39)), char(8216), char(39)))"
        " = LOWER(:title_exact)\n"
        "        OR LOWER(t.title)"
        " = LOWER(REPLACE(REPLACE(:title_exact, char(8217), char(39)), char(8216), char(39)))\n"
        "        OR EXISTS (SELECT 1 FROM track_aliases ta_x\n"
        "                   WHERE ta_x.track_id = t.id AND LOWER(ta_x.name) = LOWER(:title_exact))"
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
        WHERE ({base_where}{exp_where})
          AND t.duration IS NOT NULL
          AND t.duration BETWEEN :duration_min AND :duration_max
        ORDER BY ABS(t.duration - :duration) ASC
        LIMIT 10
    """)

    return conn.execute(sql, params).fetchall()


def _analyze_playlists_internal(source, target_source, playlists, quality_profile="Auto"):
    """Run the canonical playlist matching flow used by both manual and scheduled syncs."""
    from database.music_database import MusicDatabase
    from core.provider import PlaylistSupport
    from core.matching_engine.scoring_profile import ExactSyncProfile
    from sqlalchemy import text

    source_provider, default_acc = _get_provider_for_account(source, None)
    if source_provider is None:
        raise RuntimeError(f"No {source.title()} accounts configured. Please add an account in Settings.")

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
        if acc_id and source in ['spotify', 'tidal']:
            provider_instance, _ = _get_provider_for_account(source, acc_id)
            if provider_instance:
                source_provider = provider_instance

        if not playlist_id:
            logger.warning(f"Skipping playlist without id: {playlist_name}")
            continue

        try:
            logger.info(f"Fetching tracks for playlist: {playlist_name} (id: {playlist_id})")
            # force_refresh=True: the UI is explicitly requesting this playlist, so we
            # bypass the background-job cache limit and always serve current data.
            source_tracks = source_provider.get_playlist_tracks(playlist_id, force_refresh=True)

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
                            candidates = _fetch_tier2_candidates(
                                conn, search_title, track_duration,
                                sql_duration_tolerance_ms,
                            )
                            tier2_mode = True

                    external_ids_map = {}
                    if target_source and candidates:
                        candidate_ids = [row[0] for row in candidates]
                        try:
                            external_ids_map = db.get_external_identifier_map(target_source, candidate_ids)
                        except Exception as ext_err:
                            logger.debug(f"External identifier lookup failed for target '{target_source}': {ext_err}")

                    best_match = None
                    best_match_track_id = None
                    best_match_target_id = None
                    candidate_diagnostics = []
                    near_miss_candidate_id = None

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

                        candidate_track = SoulSyncTrack(
                            raw_title=raw_title_candidate,
                            artist_name=candidate_row[4],
                            album_title=candidate_row[7] or "",
                            duration=candidate_row[2] if candidate_row[2] else 0,
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

                            # ── Bilingual Double-Lock ──────────────────────────────────────────
                            # Handles Spotify combined bilingual tags like 'Faye 詹雯婷' or
                            # 'Lu Han 鹿晗' where neither pure fuzzy score nor substring
                            # containment alone is safe enough.
                            #
                            # Check 1 — Space-Agnostic Exact Match:
                            #   Strip ALL spaces from both normalised names; if they are
                            #   identical ('Lu Han' → 'luhan' == 'luhan') score = 1.0.
                            #   Handles split-romanisation variants without false positives.
                            #
                            # Check 2 — Double-Lock Containment Failsafe:
                            #   Requires BOTH the candidate's primary name AND at least one
                            #   stored artist alias to appear inside the Spotify artist string.
                            #   One alone is too weak (e.g. a common given-name substring
                            #   like 'Faye' could match unrelated artists); two independent
                            #   anchors from different scripts make a false positive virtually
                            #   impossible.
                            if _best_artist_score < 1.0:
                                def _dl_norm(s: str) -> str:
                                    """Lowercase + strip punctuation; keep spaces for containment."""
                                    return re.sub(r'[^\w\s]', '', s, flags=re.UNICODE).strip().lower()

                                _dl_src  = _dl_norm(source_track.artist_name)
                                _dl_cand = _dl_norm(_best_artist_name)

                                # Check 1: space-agnostic exact match.
                                if _dl_src and _dl_cand and _dl_src.replace(' ', '') == _dl_cand.replace(' ', ''):
                                    _best_artist_score = 1.0
                                    _best_artist_name  = source_track.artist_name
                                    logger.debug(
                                        "Double-Lock (space-agnostic): '%s' ≡ '%s' "
                                        "(stripped) → artist_score=1.0",
                                        source_track.artist_name, _best_artist_name,
                                    )
                                else:
                                    # Check 2: primary name + ≥1 alias both present in Spotify string.
                                    _dl_primary = _dl_norm(candidate_track.artist_name or '')
                                    _dl_aliases  = [
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
                            # ── End Bilingual Double-Lock ──────────────────────────────────────

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
                                    from plugins.cjk_language_pack.transliterator import CJKTransliterator
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

                        if tier2_mode:
                            result = matching_engine.calculate_title_duration_match(
                                source_track,
                                candidate_track,
                                target_source=target_source,
                                target_identifier=candidate_target_id,
                            )
                        else:
                            result = matching_engine.calculate_match(
                                source_track,
                                candidate_track,
                                target_source=target_source,
                                target_identifier=candidate_target_id,
                            )

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

                        if result.confidence_score > best_score:
                            best_score = result.confidence_score
                            best_match = (candidate_row[0], result)
                            best_match_track_id = candidate_row[0]
                            best_match_target_id = candidate_target_id

                        if result.is_near_miss and near_miss_candidate_id is None:
                            near_miss_candidate_id = candidate_row[0]

                    tier2_needed_due_to_version = (
                        not tier2_mode and len(candidates) > 0 and best_score == 0.0 and
                        all(not d["result"]["passed_version"] for d in candidate_diagnostics)
                    )
                    tier2_needed_due_to_failure = (
                        not tier2_mode and len(candidates) > 0 and best_score < 70 and track_duration
                    )
                    if tier2_needed_due_to_version or tier2_needed_due_to_failure:
                        logger.debug(
                            (
                                f"Tier 2 escalation triggered for '{track_title}' by '{track_artist}'. "
                                + ("Reason: version mismatch." if tier2_needed_due_to_version else "Reason: no acceptable Tier 1 match.")
                            )
                        )

                        candidates = []
                        candidate_diagnostics = []
                        best_score = 0
                        best_match = None
                        near_miss_candidate_id = None

                        if track_duration:
                            # Escalation Tier 2: widen to ±10000ms — wider than the engine's
                            # 8500ms Artist Match Duration Escalation ceiling so a confident
                            # artist match is never blocked at the SQL layer. Python scoring
                            # discriminates; the SQL window is just a coarse pre-filter.
                            # (Previously 5000ms — raised to 10000ms.)
                            sql_duration_tolerance_ms = 10000
                            duration_min = track_duration - sql_duration_tolerance_ms
                            duration_max = track_duration + sql_duration_tolerance_ms

                            with db.engine.connect() as tier2_conn:
                                candidates = _fetch_tier2_candidates(
                                    tier2_conn, search_title, track_duration,
                                    sql_duration_tolerance_ms,
                                )

                            if candidates:
                                logger.debug(
                                    f"Tier 2 escalation found {len(candidates)} title+duration matches for '{track_title}'. "
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

                                    candidate_track = SoulSyncTrack(
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

                                    result = matching_engine.calculate_title_duration_match(
                                        source_track,
                                        candidate_track,
                                        target_source=target_source,
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

                                    if result.confidence_score > best_score:
                                        best_score = result.confidence_score
                                        best_match = (candidate_row[0], result)
                                        best_match_track_id = candidate_row[0]
                                        best_match_target_id = candidate_target_id

                                    if result.is_near_miss and near_miss_candidate_id is None:
                                        near_miss_candidate_id = candidate_row[0]

                                tier2_mode = True

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
                    "target_source": target_source,
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

    total_tracks = len(all_tracks)
    try:
        matched_map = {}
        for t in all_tracks:
            mid = t.get("matched_track_id")
            if not mid:
                continue
            matched_map.setdefault(mid, []).append(t)

        duplicate_matches = {k: v for k, v in matched_map.items() if len(v) > 1}
        if duplicate_matches and logger.isEnabledFor(logging.DEBUG):
            logger.debug("[system] - Duplicate match analysis: found %d SoulSync tracks matched by multiple source tracks", len(duplicate_matches))
            for soul_id, entries in duplicate_matches.items():
                try:
                    lines = []
                    for e in entries:
                        src_id = e.get("source_identifier") or "<unknown_source_id>"
                        lines.append(f"{src_id} ('{e.get('title')}' by '{e.get('artist')}')")
                    logger.debug(f"[system] - Duplicate match: {', '.join([f'{l} matched SoulSyncTrack {soul_id}' for l in lines])}")
                except Exception as dup_err:
                    logger.debug(f"[system] - Duplicate match formatting failed for SoulSyncTrack {soul_id}: {dup_err}")
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
            })

    return {
        "summary": {
            "total_tracks": total_tracks,
            "found_in_library": found_count,
            "missing_tracks": missing_count,
            "downloaded": 0,
            "quality_profile": quality_profile,
            "source": source,
            "target": target_source,
            "matched_pairs": matched_pairs,
            "can_sync": len(matched_pairs) > 0,
        },
        "tracks": all_tracks,
        "missing": missing_tracks,
    }

@bp.get("/")
def list_playlists():
    # Placeholder: surface playlists via provider adapters (future)
    return jsonify({"items": [], "total": 0}), 200

@bp.post("/analyze")
def analyze_playlists():
    """Analyze playlists: fetch real tracks from source provider and check against database using WeightedMatchingEngine."""
    payload = request.get_json(silent=True) or {}
    source = payload.get("source")
    target = payload.get("target")
    target_source = payload.get("target_source") or target
    playlists = payload.get("playlists") or []
    quality_profile = payload.get("quality_profile", "Auto")

    if not source:
        return jsonify({"error": "source provider required"}), 400
    
    if not playlists:
        return jsonify({"error": "playlists list required"}), 400

    try:
        result = _analyze_playlists_internal(source, target_source, playlists, quality_profile)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error analyzing playlists: {e}", exc_info=True)
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@bp.post("/sync")
def trigger_sync():
    payload = request.get_json(silent=True) or {}
    target = payload.get("target_source") or payload.get("target")
    playlist_name = payload.get("playlist_name")
    matches = payload.get("matches") or []
    download_missing = payload.get("download_missing", False)
    source = payload.get("source", "unknown")

    if not target:
        return jsonify({"accepted": False, "error": "target_source required"}), 400

    if not playlist_name:
        return jsonify({"accepted": False, "error": "playlist_name required"}), 400

    from core.provider import ProviderRegistry, PlaylistSupport, get_provider_capabilities
    try:
        source_caps = get_provider_capabilities(source)
        if source_caps.supports_playlists not in (PlaylistSupport.READ, PlaylistSupport.READ_WRITE):
            return jsonify({"accepted": False, "error": f"Source provider {source} does not support reading playlists"}), 400
    except KeyError:
        return jsonify({"accepted": False, "error": f"Source provider {source} not found"}), 400

    try:
        target_caps = get_provider_capabilities(target)
        if target_caps.supports_playlists != PlaylistSupport.READ_WRITE:
            return jsonify({"accepted": False, "error": f"Target provider {target} does not support writing playlists"}), 400
    except KeyError:
        return jsonify({"accepted": False, "error": f"Target provider {target} not found"}), 400

    # Detect sync mode: tier-to-tier (streaming↔streaming) vs local-server (streaming→plex)
    tier_to_tier_providers = {"spotify", "tidal", "apple_music"}
    local_server_providers = {"plex", "jellyfin", "navidrome"}
    
    is_source_tier = source in tier_to_tier_providers
    is_target_tier = target in tier_to_tier_providers
    is_source_server = source in local_server_providers
    is_target_server = target in local_server_providers
    
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
    if target == "plex":
        # Local-server sync: add tracks to managed playlist with overwrite
        source_account_name = payload.get("source_account_name")
        target_user_id = payload.get("target_user_id")
        return _sync_to_plex(payload, source, target, playlist_name, matches, download_missing, sync_mode, source_account_name, target_user_id)
    elif target in tier_to_tier_providers:
        # Tier-to-tier sync: add tracks to target provider's playlist
        return _sync_to_tier(payload, source, target, playlist_name, matches, download_missing, sync_mode)
    else:
        return jsonify({"accepted": False, "error": f"Sync to {target} not implemented"}), 400


def _sync_to_plex(payload, source, target, playlist_name, matches, download_missing, sync_mode, source_account_name=None, target_user_id=None):
    """Sync matched tracks to a Plex managed playlist."""
    # Collect ratingKeys from matches (target_identifier)
    rating_keys = [m.get("target_identifier") for m in matches if m.get("target_identifier")]
    if not rating_keys:
        return jsonify({"accepted": False, "error": "No Plex ratingKeys provided in matches"}), 400

    # Schedule a one-off sync job with retry/backoff
    job_name = f"sync:plex:{playlist_name}:{int(time.time())}"

    def _run_sync():
        from providers.plex.client import PlexClient

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

        try:
            client = PlexClient()
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
        logger.error(f"Failed to schedule Plex sync job '{job_name}': {e}")
        return jsonify({"accepted": False, "error": f"Failed to schedule sync: {e}"}), 500

    return jsonify({
        "accepted": True,
        "job": job_name,
        "target": target,
        "playlist": playlist_name,
        "match_count": len(rating_keys),
        "sync_mode": sync_mode,
        "events_path": f"/api/playlists/sync/events?job={quote(job_name, safe='')}",
    }), 202


def _sync_to_tier(payload, source, target, playlist_name, matches, download_missing, sync_mode):
    """Sync matched tracks to a tier provider (Spotify, Tidal, etc.)."""
    # Collect provider-specific IDs from matches (target_identifier for tier target)
    track_ids = [m.get("target_identifier") for m in matches if m.get("target_identifier")]
    if not track_ids:
        return jsonify({"accepted": False, "error": f"No {target} track IDs provided in matches"}), 400

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
            from core.provider import ProviderRegistry
            target_provider = ProviderRegistry.get_provider(target)
            
            if not target_provider:
                raise RuntimeError(f"Provider {target} not found")

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
        logger.error(f"Failed to schedule {target} sync job '{job_name}': {e}")
        return jsonify({"accepted": False, "error": f"Failed to schedule sync: {e}"}), 500

    return jsonify({
        "accepted": True,
        "job": job_name,
        "target": target,
        "playlist": playlist_name,
        "track_count": len(track_ids),
        "sync_mode": sync_mode,
        "events_path": f"/api/playlists/sync/events?job={quote(job_name, safe='')}",
    }), 202


@bp.get("/sync/events")
def sync_events():
    job_name = request.args.get("job")
    since = request.args.get("since", type=int)

    if not job_name:
        return jsonify({"error": "job query parameter required"}), 400

    events = event_bus.get_events(job_name, since_id=since)
    return jsonify({
        "job": job_name,
        "events": events,
        "count": len(events),
    }), 200


@bp.get("/sync/history")
def sync_history_endpoint():
    """Get recent sync records for observability."""
    source = request.args.get("source")
    target = request.args.get("target")
    limit = request.args.get("limit", 20, type=int)
    
    records = sync_history.get_records(source=source, target=target)
    recent = records[-limit:] if records else []
    
    return jsonify({
        "records": [r.to_dict() for r in recent],
        "total": len(recent),
    }), 200


@bp.post("/download-missing")
def download_missing_tracks():
    """Trigger downloads for missing tracks identified during analysis.
    
    Directly queues tracks to the download_manager's queue.
    No separate job is created - the main download_manager job handles processing.
    """
    payload = request.get_json(silent=True) or {}
    missing = payload.get("missing") or []
    
    if not missing:
        return jsonify({"accepted": False, "error": "missing tracks list required"}), 400
    
    try:
        from services.download_manager import get_download_manager
        from core.matching_engine.soul_sync_track import SoulSyncTrack
        
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
                    track = SoulSyncTrack.from_dict(source_track_payload)
                else:
                    duration_ms = track_info.get("duration_ms")
                    if duration_ms is None:
                        duration_ms = track_info.get("duration")

                    identifiers = {}
                    source_identifier = track_info.get("source_identifier")
                    if source_identifier:
                        identifiers["spotify"] = str(source_identifier)

                    # Create SoulSyncTrack from fallback metadata, preserving ISRC when provided.
                    track = SoulSyncTrack(
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
                download_manager.process_downloads_now()
            except Exception as e:
                logger.warning(f"Queued downloads but immediate processing trigger failed: {e}")
        
        return jsonify({
            "accepted": True,
            "track_count": len(missing),
            "queued": success_count,
            "failed": failed_count,
            "message": f"Queued {success_count} tracks to download_manager (failed: {failed_count})",
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to queue downloads: {e}")
        return jsonify({"accepted": False, "error": f"Failed to queue downloads: {e}"}), 500


# ========================================
# PERSONALIZED PLAYLISTS ENDPOINTS
# ========================================

@bp.get("/genres")
def get_available_genres():
    """Get list of available genres from discovery pool"""
    try:
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        genres = service.get_available_genres()
        return jsonify({
            "genres": genres,
            "total": len(genres)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching genres: {e}")
        return jsonify({"error": "Failed to fetch genres"}), 500


@bp.get("/genre/<genre_name>")
def get_genre_playlist(genre_name):
    """Get playlist for a specific genre"""
    try:
        limit = request.args.get("limit", 50, type=int)
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_genre_playlist(genre_name, limit=limit)
        return jsonify({
            "genre": genre_name,
            "tracks": tracks,
            "total": len(tracks)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching genre playlist for {genre_name}: {e}")
        return jsonify({"error": "Failed to fetch genre playlist"}), 500


@bp.get("/decade/<int:decade>")
def get_decade_playlist(decade):
    """Get playlist for a specific decade"""
    try:
        limit = request.args.get("limit", 100, type=int)
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_decade_playlist(decade, limit=limit)
        return jsonify({
            "decade": decade,
            "tracks": tracks,
            "total": len(tracks)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching decade playlist for {decade}s: {e}")
        return jsonify({"error": "Failed to fetch decade playlist"}), 500


@bp.get("/popular-picks")
def get_popular_picks():
    """Get high-popularity tracks from discovery pool"""
    try:
        limit = request.args.get("limit", 50, type=int)
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_popular_picks(limit=limit)
        return jsonify({
            "name": "Popular Picks",
            "tracks": tracks,
            "total": len(tracks)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching popular picks: {e}")
        return jsonify({"error": "Failed to fetch popular picks"}), 500


@bp.get("/hidden-gems")
def get_hidden_gems():
    """Get low-popularity underground tracks from discovery pool"""
    try:
        limit = request.args.get("limit", 50, type=int)
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_hidden_gems(limit=limit)
        return jsonify({
            "name": "Hidden Gems",
            "tracks": tracks,
            "total": len(tracks)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching hidden gems: {e}")
        return jsonify({"error": "Failed to fetch hidden gems"}), 500


@bp.get("/discovery-shuffle")
def get_discovery_shuffle():
    """Get random tracks from discovery pool"""
    try:
        limit = request.args.get("limit", 50, type=int)
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        tracks = service.get_discovery_shuffle(limit=limit)
        return jsonify({
            "name": "Discovery Shuffle",
            "tracks": tracks,
            "total": len(tracks)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching discovery shuffle: {e}")
        return jsonify({"error": "Failed to fetch discovery shuffle"}), 500


@bp.get("/daily-mixes")
def get_all_daily_mixes():
    """Get all daily mixes"""
    try:
        max_mixes = request.args.get("max_mixes", 4, type=int)
        db = MusicDatabase()
        service = get_personalized_playlists_service(db)
        mixes = service.get_all_daily_mixes(max_mixes=max_mixes)
        return jsonify({
            "mixes": mixes,
            "total": len(mixes)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching daily mixes: {e}")
        return jsonify({"error": "Failed to fetch daily mixes"}), 500


@bp.post("/sync/schedule")
def schedule_recurring_sync():
    """Schedule a recurring playlist sync job (e.g., every 6 hours)."""
    payload = request.get_json(silent=True) or {}
    source = payload.get("source")
    target = payload.get("target_source") or payload.get("target")
    playlists = payload.get("playlists", [])
    interval = payload.get("interval", 3600)  # Default: 1 hour in seconds
    download_missing = payload.get("download_missing", False)
    enabled = payload.get("enabled", True)

    if not source or not target or not playlists:
        return jsonify({"error": "source, target, and playlists required"}), 400

    if interval < 300:
        return jsonify({"error": "interval must be at least 300 seconds (5 minutes)"}), 400

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
    return jsonify({
        "accepted": True,
        "sync_id": sync_config["id"],
        "interval": interval,
    }), 201


@bp.get("/sync/scheduled")
def list_scheduled_syncs():
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
    
    return jsonify({
        "scheduled_syncs": scheduled_syncs,
        "count": len(scheduled_syncs),
    }), 200


@bp.delete("/sync/scheduled/<sync_id>")
def delete_scheduled_sync(sync_id):
    """Delete a scheduled sync job."""
    from core.settings import config_manager
    scheduled_syncs = config_manager.get("scheduled_syncs", [])
    
    # Find and remove sync
    updated_syncs = [s for s in scheduled_syncs if s.get("id") != sync_id]
    if len(updated_syncs) == len(scheduled_syncs):
        return jsonify({"error": "Sync not found"}), 404
    
    config_manager.set("scheduled_syncs", updated_syncs)
    config_manager.save_config()
    
    # Unregister from job queue
    job_name = f"scheduled:{sync_id}"
    if job_name in job_queue.jobs:
        job_queue.unregister_job(job_name)
    
    logger.info(f"Scheduled sync deleted: {sync_id}")
    return jsonify({"accepted": True}), 200


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
