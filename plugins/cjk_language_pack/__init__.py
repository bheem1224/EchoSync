"""
CJK Language Pack Plugin — v2.4.0
===================================
Solves the "Anime/Drama OST Problem" via a three-stage Expand → Score → Restore
pipeline that works entirely offline (no cloud ASR, no paid APIs).

Expand  (pre_provider_search)
    Detects CJK characters in a search query and generates a targeted set of
    search strings:
      • Original CJK query
      • Simplified / Traditional Chinese script variants   (opencc)
      • Tone-stripped Pinyin / Hepburn Romaji / Revised Romanization  (pypinyin / pykakasi / hangul_romanize)
      • Anime or drama series names discovered from VGMdb.info
        → e.g. "YOASOBI Idol" becomes ["YOASOBI Idol", "晴天", "yoasobi idol", "Oshi no Ko Idol"]

Score   (pre_normalize_text)
    Intercepts every string that flows through the WeightedMatchingEngine:
      • CJK strings are flattened to pure-Latin phonetics so edit-distance
        scoring works across scripts ("アイドル" → "aidoru" vs "idol").
      • Strings matching a known anime / drama series name (populated by the
        VGMdb lookup above) are remapped to the canonical artist name so
        "Oshi no Ko" scores as "yoasobi" — a near-perfect artist match.

Restore (post_metadata_enrichment)
    After the MetadataEnhancerService pipeline completes:
      • Writes TrackAlias rows for Simplified, Traditional, and Latin
        (Pinyin / Romaji) forms of the track title.
      • Writes ArtistAlias rows for the same variants of the artist name.
    Both use the SQLAlchemy ORM session already attached to the track object —
    no new session or raw database connection is ever created (Zero-Trust).

Zero-Trust sandbox compliance
    • No direct file I/O.
    • No os / sys / subprocess / importlib imports at module level.
    • Database access exclusively via object_session() on the passed ORM object.
    • VGMdb HTTP calls use only stdlib urllib with a hard timeout and hardcoded
      base URL — user input is URL-encoded and never used to construct the host.
"""

from __future__ import annotations

import re
from typing import Any, List

from core.hook_manager import hook_manager
from core.tiered_logger import get_logger
from plugins.cjk_language_pack.transliterator import get_transliterator
from plugins.cjk_language_pack.vgmdb_proxy import get_proxy
from plugins.cjk_language_pack.noise_filter import get_noise_filter
from plugins.cjk_language_pack.noise_filter import get_noise_filter

logger = get_logger("plugin.cjk")

# Fast CJK tripwire — same ranges covered by transliterator._CJK_RE
_CJK_RE = re.compile(
    r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af\u1100-\u11ff]"
)


def _has_cjk(text: str) -> bool:
    return isinstance(text, str) and bool(_CJK_RE.search(text))


# kept for callers that still use the old name
def contains_cjk(text: str) -> bool:
    return _has_cjk(text)


# ── Hook 0: register_metadata_requirements ────────────────────────────────────

def _on_register_metadata_requirements(requirements: List[str]) -> List[str]:
    """Register the metadata_status key that this plugin writes to metadata_status upon enrichment.

    ``cjk_restored`` is set to True on CJK tracks and False on non-CJK tracks so the
    retroactive enhancer knows a track has already been processed and won't requeue it.
    """
    extra = ["cjk_restored"]
    existing = set(requirements)
    return requirements + [f for f in extra if f not in existing]


# ── Hook 1: pre_provider_search (Expand) ──────────────────────────────────────

def _expand_query(query: str, artist_name: str = "", title: str = "") -> list[str]:
    """
    Return a priority-ordered list of search strings for a CJK-containing query.

    Sniper priority matrix (highest → lowest hit-rate on slskd):
        1. ``<VGMdb series name> <CJK title>``       — files tagged by show name
        2. ``<original combined query>``              — pass-through / exact tags
        3. ``<romaji/pinyin artist> <romaji/pinyin title>``  — Latin-phonetic files
        4. Simplified Chinese variant
        5. Traditional Chinese variant
    """
    tr = get_transliterator()

    # Prefer explicit per-field kwargs over parsing the combined query string.
    if artist_name and title:
        cjk_artist    = artist_name
        cjk_title     = title
        latin_artist  = tr.flatten_to_romaji(artist_name)
        latin_title   = tr.flatten_to_romaji(title)
    elif " - " in query:
        raw_artist, raw_title = query.split(" - ", 1)
        cjk_artist    = raw_artist.strip()
        cjk_title     = raw_title.strip()
        latin_artist  = tr.flatten_to_romaji(cjk_artist)
        latin_title   = tr.flatten_to_romaji(cjk_title)
    else:
        cjk_artist    = ""
        cjk_title     = query
        latin_artist  = ""
        latin_title   = tr.flatten_to_romaji(query)

    # ------------------------------------------------------------------
    # 1. VGMdb series look-up — use Latin forms for better API match quality
    # ------------------------------------------------------------------
    proxy        = get_proxy()
    series_hits  = proxy.lookup_series(
        (latin_artist or cjk_artist).strip(),
        (latin_title  or cjk_title).strip(),
    )

    result: list[str] = []
    seen:   set[str]  = set()

    def _add(candidate: str) -> None:
        s = candidate.strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)

    # Priority 1 (a/b/c): VGMdb series queries — highest hit-rate on slskd P2P.
    # Covers files tagged by show/game name rather than by artist name.
    for hit in series_hits:
        native  = hit.get("native", "")
        english = hit.get("english", "")
        # (a) "<native series> OST" — e.g. "葬送のフリーレン OST"
        if native:
            _add(f"{native} OST")
        # (b) "<english series> Soundtrack" — e.g. "Frieren Soundtrack"
        if english:
            _add(f"{english} Soundtrack")
        # (c) "<english series> <original CJK title>" — e.g. "Frieren Frieren"
        #     (catches releases labelled by series name with the track title)
        if english and cjk_title:
            _add(f"{english} {cjk_title}")

    # Priority 2: original combined query (pass-through / exact tags)
    _add(query)

    # Priority 3: fully Latin — covers files tagged in Romaji / Pinyin
    if cjk_artist:
        _add(f"{latin_artist} {latin_title}".strip())
    else:
        _add(latin_title)

    # Priority 4 & 5: Simplified / Traditional Chinese script variants
    # (only emitted for Chinese; detect_language guards are inside script_variants)
    from plugins.cjk_language_pack.transliterator import detect_language
    lang = detect_language(cjk_title or query)
    if lang == "zh":
        if cjk_artist:
            _add(f"{tr.to_simplified(cjk_artist)} {tr.to_simplified(cjk_title)}".strip())
            _add(f"{tr.to_traditional(cjk_artist)} {tr.to_traditional(cjk_title)}".strip())
        else:
            _add(tr.to_simplified(cjk_title))
            _add(tr.to_traditional(cjk_title))

    return result


def _on_pre_provider_search(
    query: Any,
    strategy_name: str = "",
    artist_name: str = "",
    title: str = "",
    **kwargs: Any,
) -> Any:
    """
    Expand a CJK query into a prioritised list of search strings.

    * Returns ``[]`` immediately for the ``album+title`` strategy — CJK tracks
      on slskd are almost never tagged by CJK album name, so this strategy
      produces only noise while burning an extra HTTP round-trip.
    * Passes ``artist_name`` / ``title`` down to ``_expand_query`` so the
      sniper priority matrix can use precise per-field metadata rather than
      parsing the combined query string.
    """
    # ── Album+title pruning for CJK queries ──────────────────────────────
    _probe = query if isinstance(query, str) else " ".join(str(q) for q in (query or []))
    if strategy_name == "album+title" and _has_cjk(_probe):
        logger.debug(
            "Pruning album+title strategy for CJK query %r "
            "(slskd files are not tagged by CJK album name).",
            query,
        )
        return []

    if isinstance(query, list):
        out: list[str] = []
        seen: set[str] = set()
        for q in query:
            for v in (
                _expand_query(q, artist_name=artist_name, title=title)
                if _has_cjk(q)
                else [q]
            ):
                if v not in seen:
                    seen.add(v)
                    out.append(v)
        return out

    if not _has_cjk(query):
        return query

    logger.info("CJK detected in search query %r — expanding sniper variants", query)
    expanded = _expand_query(query, artist_name=artist_name, title=title)
    logger.debug("Expanded to %d variants: %s", len(expanded), expanded)
    return expanded


# ── Hook 2: pre_normalize_text (Score / Reduce) ────────────────────────────────

def _on_pre_normalize_text(text: str) -> str:
    """
    Transform *text* before the WeightedMatchingEngine's ASCII-folding pass.

    **Fast gatekeeper** (first line):
        If *text* contains no CJK or full-width characters, return it unchanged
        immediately.  This guarantees zero overhead for English / Latin tracks
        — the core normalizer handles those natively.

    When CJK is detected, three steps run in strict order:

    1. **Series → artist remapping**
           If *text* matches a VGMdb-resolved series name, return the
           canonical artist name (e.g. "Oshi no Ko" → "yoasobi").

    2. **CJK noise stripping** (NoiseFilter.strip_cjk_noise)
           Remove OST markers, theme-song labels, full-width brackets, and
           full-width Latin tokens (ｆｅａｔ, ＯＳＴ) that are exclusive to
           CJK text.  Standard English noise (feat., OST, …) is left in place
           so the core normalizer can strip it during its own downstream pass.

    3. **Transliteration** (CJKTransliterator.flatten_to_romaji)
           Convert ideographs / kana / hangul to pure-Latin phonetics.
           The resulting Romaji/Pinyin string re-enters the core pipeline,
           which then runs its own feat.-stripping and Unicode canonicalization
           — cleanly splitting the workload between plugin and core.
    """
    # ── Gatekeeper: bypass entirely for non-CJK strings ──────────────────
    if not isinstance(text, str) or not _has_cjk(text):
        return text

    # ── Step 1: series → canonical artist remap ───────────────────────────
    proxy = get_proxy()
    canonical_artist = proxy.resolve_artist_for_series(text)
    if canonical_artist:
        logger.debug("Series alias remap: %r → %r", text, canonical_artist)
        return canonical_artist

    # ── Step 2: strip CJK-exclusive structural noise ──────────────────────
    cleaned = get_noise_filter().strip_cjk_noise(text)
    if cleaned != text:
        logger.debug("CJK noise strip: %r → %r", text, cleaned)

    # ── Step 3: transliterate to Latin phonetics ──────────────────────────
    # Returns the cleaned string unchanged if no CJK remains after noise strip.
    result = get_transliterator().flatten_to_romaji(cleaned)
    logger.debug("CJK transliterate: %r → %r", cleaned, result)
    return result


# ── Hook 3: post_metadata_enrichment (Restore) ────────────────────────────────

def _build_track_alias_entries(track_obj: Any) -> list[dict]:
    """
    Return a list of alias dicts for every script variant of the track title.

    Priority order:
      1. Explicit ``cjk_aliases`` list in ``track_obj.metadata_status``
         (set by a provider that fetched MusicBrainz aliases directly).
      2. Synthesised from the title using CJKTransliterator:
         • Simplified Chinese  (locale="zh", script="Hans")
         • Traditional Chinese (locale="zh", script="Hant")
         • Latin phonetics     (locale="en", script="Latn") ← primary
    """
    status = track_obj.metadata_status or {}
    declared = status.get("cjk_aliases")
    if declared and isinstance(declared, list):
        return declared

    title = getattr(track_obj, "title", "") or ""
    if not _has_cjk(title):
        return []

    tr = get_transliterator()
    entries: list[dict] = []
    seen: set[str] = set()

    def _add(name: str, locale: str, script: str, primary: bool) -> None:
        if name and name not in seen and name != title:
            seen.add(name)
            entries.append({
                "name": name,
                "locale": locale,
                "script": script,
                "is_primary_for_locale": primary,
            })

    _add(tr.to_simplified(title),  "zh", "Hans", False)
    _add(tr.to_traditional(title), "zh", "Hant", False)
    _add(tr.flatten_to_romaji(title), "en", "Latn", True)   # Pinyin/Romaji
    return entries


def _build_artist_alias_entries(artist_name: str) -> list[dict]:
    """Return alias dicts for every script variant of *artist_name*."""
    if not _has_cjk(artist_name):
        return []

    tr = get_transliterator()
    entries: list[dict] = []
    seen: set[str] = set()

    def _add(name: str, locale: str, script: str, primary: bool) -> None:
        if name and name not in seen and name != artist_name:
            seen.add(name)
            entries.append({
                "name": name,
                "locale": locale,
                "script": script,
                "is_primary_for_locale": primary,
            })

    _add(tr.to_simplified(artist_name),  "zh", "Hans", False)
    _add(tr.to_traditional(artist_name), "zh", "Hant", False)
    _add(tr.flatten_to_romaji(artist_name), "en", "Latn", True)
    return entries


def _persist_track_aliases(track_obj: Any, alias_entries: list[dict]) -> None:
    """
    Append TrackAlias rows via the ORM session that already owns *track_obj*.

    Zero-Trust: uses ``object_session(track_obj)`` — no new session opened.
    The MetadataEnhancerService owns the surrounding ``session_scope`` and
    commits all pending changes (including these rows) when its block exits.
    """
    if not alias_entries:
        return
    try:
        from sqlalchemy.orm import object_session
        from sqlalchemy import inspect as sa_inspect

        session = object_session(track_obj)
        if session is None:
            logger.warning(
                "No ORM session on track_obj (ID %s) — TrackAlias write skipped.",
                getattr(track_obj, "id", "?"),
            )
            return

        rel = sa_inspect(type(track_obj)).relationships.get("aliases")
        if rel is None:
            logger.warning("Track ORM has no 'aliases' relationship — skipping.")
            return
        TrackAlias = rel.mapper.class_

        added = 0
        for entry in alias_entries:
            name = entry.get("name") or ""
            if not name:
                continue
            if any(
                a.name == name
                and a.locale == entry.get("locale")
                and a.script == entry.get("script")
                for a in track_obj.aliases
            ):
                continue
            track_obj.aliases.append(
                TrackAlias(
                    track_id=track_obj.id,
                    name=name,
                    locale=entry.get("locale"),
                    script=entry.get("script"),
                    is_primary_for_locale=bool(entry.get("is_primary_for_locale", False)),
                )
            )
            added += 1

        if added:
            logger.debug(
                "Queued %d TrackAlias row(s) for Track ID %s (commit deferred to caller).",
                added, track_obj.id,
            )
    except Exception as exc:
        logger.warning(
            "TrackAlias persistence failed for Track ID %s: %s",
            getattr(track_obj, "id", "?"), exc,
        )


def _persist_artist_aliases(track_obj: Any, alias_entries: list[dict]) -> None:
    """
    Append ArtistAlias rows for the artist attached to *track_obj*.

    Accesses ``track_obj.artist`` via the SQLAlchemy lazy-load mechanism —
    safe because we're always called from inside a ``session_scope`` context.
    Zero-Trust: no new session opened.
    """
    if not alias_entries:
        return
    try:
        from sqlalchemy.orm import object_session
        from sqlalchemy import inspect as sa_inspect

        if object_session(track_obj) is None:
            return

        artist_obj = getattr(track_obj, "artist", None)
        if artist_obj is None:
            return

        rel = sa_inspect(type(artist_obj)).relationships.get("aliases")
        if rel is None:
            return
        ArtistAlias = rel.mapper.class_

        added = 0
        for entry in alias_entries:
            name = entry.get("name") or ""
            if not name:
                continue
            if any(
                a.name == name
                and a.locale == entry.get("locale")
                and a.script == entry.get("script")
                for a in artist_obj.aliases
            ):
                continue
            artist_obj.aliases.append(
                ArtistAlias(
                    artist_id=artist_obj.id,
                    name=name,
                    locale=entry.get("locale"),
                    script=entry.get("script"),
                    is_primary_for_locale=bool(entry.get("is_primary_for_locale", False)),
                )
            )
            added += 1

        if added:
            logger.debug(
                "Queued %d ArtistAlias row(s) for Artist ID %s (commit deferred to caller).",
                added, artist_obj.id,
            )
    except Exception as exc:
        logger.warning(
            "ArtistAlias persistence failed for Track ID %s: %s",
            getattr(track_obj, "id", "?"), exc,
        )


def _on_post_metadata_enrichment(track_obj: Any) -> Any:
    """
    After the MetadataEnhancerService pipeline:

    1. Stamp ``cjk_restored`` on ``track_obj.metadata_status`` (True for CJK tracks,
       False for non-CJK tracks so the enhancer won't requeue them on the next pass).
    2. Persist all script-variant TrackAlias rows for the track title (CJK only).
    3. Persist all script-variant ArtistAlias rows for the artist name (CJK only).

    Design invariant: ``track_obj.metadata_status`` is always written BEFORE any
    relationship lazy-load or alias-persistence work.  This prevents a silent
    ``DetachedInstanceError`` (or any other ORM error thrown while accessing
    ``track_obj.artist``) from propagating up to ``apply_filters`` and aborting
    the hook before the stamp is persisted.
    """
    if not hasattr(track_obj, "metadata_status") or not hasattr(track_obj, "id"):
        return track_obj

    title = getattr(track_obj, "title", "") or ""

    # Guard the artist relationship lazy-load with an explicit try/except so that a
    # DetachedInstanceError or any other SQLAlchemy session error can never prevent
    # the metadata_status stamp from being written below.
    # (Python's built-in getattr(obj, attr, default) only catches AttributeError —
    # it does NOT suppress DetachedInstanceError or other SQLAlchemy exceptions.)
    artist_name = ""
    try:
        artist_obj = getattr(track_obj, "artist", None)
        artist_name = (getattr(artist_obj, "name", "") or "") if artist_obj else ""
    except Exception as _exc:
        logger.debug(
            "CJK plugin: could not load artist for Track ID %s (%s) — "
            "CJK detection falls back to title-only.",
            getattr(track_obj, "id", "?"), _exc,
        )

    status = dict(track_obj.metadata_status or {})
    is_cjk = _has_cjk(title) or _has_cjk(artist_name)

    # ── STAMP FIRST, before any further lazy-loads or alias persistence ───────
    # Writing cjk_restored here guarantees the value reaches the DB even if the
    # alias work below raises — the enhancer's flag_modified + session.commit()
    # will capture whatever is currently assigned to track_obj.metadata_status.
    if "cjk_restored" not in status:
        status["cjk_restored"] = is_cjk
        if is_cjk:
            status["cjk_script_applied"] = status.get("release_script", "Latn")
            logger.debug("Stamped cjk_restored for Track ID %s", track_obj.id)
        track_obj.metadata_status = status

    if not is_cjk:
        return track_obj

    # ── CJK-only: persist script-variant aliases ──────────────────────────────
    if _has_cjk(title):
        _persist_track_aliases(track_obj, _build_track_alias_entries(track_obj))

    if _has_cjk(artist_name):
        _persist_artist_aliases(track_obj, _build_artist_alias_entries(artist_name))

    return track_obj


# ── Plugin Initialization ──────────────────────────────────────────────────────

def initialize_plugin() -> None:
    """Wire all hooks into the system. Called automatically on first import."""
    logger.info("CJK Language Pack: initializing hooks...")
    hook_manager.add_filter("register_metadata_requirements", _on_register_metadata_requirements)
    hook_manager.add_filter("pre_provider_search",            _on_pre_provider_search)
    hook_manager.add_filter("pre_normalize_text",             _on_pre_normalize_text)
    hook_manager.add_filter("post_metadata_enrichment",       _on_post_metadata_enrichment)
    logger.info(
        "CJK Language Pack: registered hooks "
        "(register_metadata_requirements / pre_provider_search / "
        "pre_normalize_text / post_metadata_enrichment)"
    )


initialize_plugin()


# ── Registry Override (WeightedMatchingEngine subclass) ───────────────────────
from core.provider import ServiceRegistry
from core.matching_engine.matching_engine import WeightedMatchingEngine


class CJKMatchingEngine(WeightedMatchingEngine):
    """
    Subclass reserved for future CJK-specific scoring overrides.
    Currently delegates all scoring to WeightedMatchingEngine unchanged;
    the pre_normalize_text hook above is sufficient for correct CJK matching.
    """


ServiceRegistry.register_override("com.soulsync.cjk-pack", CJKMatchingEngine)
