"""
CJK Language Pack — Echosync community plugin.

Registers a ``pre_normalize_text`` filter that transliterates Chinese
(Simplified and Traditional), Japanese (Kanji/Kana), and Korean (Hangul)
text into its Latin-script equivalent (Pinyin / Romaji / Revised Romanization)
before the core matching engine runs its NFKD ascii-folding pass.

This allows the matching engine to successfully pair, for example:

    "約束のネバーランド"   ↔   "Yakusoku no Neverland"
    "晴天"                ↔   "Qing Tian"
    "봄날"                ↔   "Bom Nal"

Setup
-----
Called automatically by :class:`core.plugin_loader.PluginLoader` once the
security scan and manifest validation have passed::

    module.setup(hook_manager)

The plugin registers a single filter at priority 10, which runs *before* any
user-supplied filters at priority > 10 but *after* lower-priority ones (p < 10)
that might, for example, collapse custom ligatures.

Lazy loading
------------
All four transliteration libraries are imported **inside** the filter function
so they do not consume memory or slow down startup when the filter is never
invoked (e.g. a library with no CJK metadata).  On the first CJK string each
import is resolved and cached by Python's module machinery; subsequent calls
pay only the function-call overhead.

Error isolation
---------------
Each transliteration block (Chinese, Japanese, Korean) is wrapped in its own
``try/except``.  A broken or missing library causes that block to be skipped
silently — the partially-transliterated string (or the original, if the very
first block failed) is returned, so a bad dependency never crashes the matching
pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from core.tiered_logger import get_logger

if TYPE_CHECKING:
    from core.plugins.hook_manager import HookManager

logger = get_logger("cjk_language_pack")


# ---------------------------------------------------------------------------
# Unicode range helpers
# ---------------------------------------------------------------------------

def _contains_cjk(text: str) -> bool:
    """Return True if *text* contains at least one CJK / Kana / Hangul codepoint."""
    for ch in text:
        cp = ord(ch)
        if (
            # CJK Unified Ideographs (core block + extensions A/B)
            0x4E00 <= cp <= 0x9FFF
            or 0x3400 <= cp <= 0x4DBF
            or 0x20000 <= cp <= 0x2A6DF
            # CJK Compatibility Ideographs
            or 0xF900 <= cp <= 0xFAFF
            # Hiragana + Katakana
            or 0x3040 <= cp <= 0x30FF
            # Katakana Phonetic Extensions
            or 0x31F0 <= cp <= 0x31FF
            # Hangul Syllables + Jamo
            or 0xAC00 <= cp <= 0xD7AF
            or 0x1100 <= cp <= 0x11FF
            or 0xA960 <= cp <= 0xA97F
            or 0xD7B0 <= cp <= 0xD7FF
        ):
            return True
    return False


def _contains_hangul(text: str) -> bool:
    """Return True if *text* contains at least one Hangul syllable or jamo."""
    for ch in text:
        cp = ord(ch)
        if (
            0xAC00 <= cp <= 0xD7AF   # Hangul Syllables
            or 0x1100 <= cp <= 0x11FF   # Hangul Jamo
        ):
            return True
    return False


def _contains_kana_or_kanji(text: str) -> bool:
    """Return True if *text* contains Hiragana, Katakana, or CJK Ideographs."""
    for ch in text:
        cp = ord(ch)
        if (
            0x3040 <= cp <= 0x30FF   # Hiragana + Katakana
            or 0x31F0 <= cp <= 0x31FF  # Katakana Phonetic Extensions
            or 0x4E00 <= cp <= 0x9FFF   # CJK Unified Ideographs
            or 0x3400 <= cp <= 0x4DBF
        ):
            return True
    return False


def _contains_hanzi(text: str) -> bool:
    """Return True if *text* contains CJK Unified Ideographs (Chinese characters)."""
    for ch in text:
        cp = ord(ch)
        if (
            0x4E00 <= cp <= 0x9FFF
            or 0x3400 <= cp <= 0x4DBF
            or 0x20000 <= cp <= 0x2A6DF
            or 0xF900 <= cp <= 0xFAFF
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# Transliteration filter
# ---------------------------------------------------------------------------

def transliterate_cjk(text: str, **kwargs: Any) -> str:
    """
    Filter function registered on the ``pre_normalize_text`` hook.

    Converts CJK scripts found in *text* to their Latin-script equivalents.
    Returns *text* unchanged if it is purely ASCII or contains no CJK codepoints.

    Args:
        text:      The input string, as passed by the hook pipeline.
        **kwargs:  Extra context forwarded by ``apply_filters`` (ignored here).

    Returns:
        Transliterated string, or the original *text* on any failure.
    """
    if not text:
        return text

    # ── Fast-path: purely ASCII ────────────────────────────────────────────
    if text.isascii():
        return text

    # ── Fast-path: no CJK at all ───────────────────────────────────────────
    if not _contains_cjk(text):
        return text

    result = text

    # ── 1. Chinese: Traditional → Simplified → Pinyin ─────────────────────
    # Run this first so that Traditional characters are converted to Simplified
    # before pypinyin processes them (pypinyin handles Simplified much better).
    if _contains_hanzi(result):
        try:
            import opencc as _opencc_raw  # type: ignore[import-untyped]
            from pypinyin import lazy_pinyin as _pinyin_raw, Style as _Style_raw  # type: ignore[import-untyped]

            # Re-bind to Any so Pylance does not cascade Unknown through downstream calls.
            opencc_mod: Any = cast(Any, _opencc_raw)
            lazy_pinyin: Any = cast(Any, _pinyin_raw)
            Style: Any = cast(Any, _Style_raw)

            # opencc converter: Traditional → Simplified
            converter = opencc_mod.OpenCC("t2s")
            simplified: str = str(converter.convert(result))

            # Convert Simplified Hanzi to Pinyin, tones stripped (NORMAL style)
            parts: list[str] = []
            for ch in simplified:
                cp = ord(ch)
                if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
                    # CJK character → convert to tone-stripped pinyin syllable
                    pinyin_syllables: list[str] = list(lazy_pinyin(ch, style=Style.NORMAL))
                    parts.extend(pinyin_syllables)
                else:
                    parts.append(ch)

            result = " ".join(parts)
        except Exception as exc:
            logger.warning(
                "CJK Language Pack: Chinese transliteration failed: %s", exc
            )
            # Proceed with the previous value of `result`

    # ── 2. Japanese: Kanji / Kana → Romaji ────────────────────────────────
    # pykakasi handles mixed Kanji/Kana/Latin strings naturally.
    if _contains_kana_or_kanji(result):
        try:
            import pykakasi as _pykakasi_raw  # type: ignore[import-untyped]

            pykakasi: Any = cast(Any, _pykakasi_raw)

            kks = pykakasi.kakasi()
            items: list[dict[str, str]] = list(kks.convert(result))

            # Each item dict has keys: orig, hira, kana, hepburn, passport, kunrei
            # We use 'hepburn' for standard Romaji; fall back to 'orig' when empty.
            romaji_parts: list[str] = []
            for item in items:
                hepburn: str = str(item.get("hepburn", "")).strip()
                orig: str = str(item.get("orig", ""))
                romaji_parts.append(hepburn if hepburn else orig)

            result = " ".join(p for p in romaji_parts if p)
        except Exception as exc:
            logger.warning(
                "CJK Language Pack: Japanese transliteration failed: %s", exc
            )

    # ── 3. Korean: Hangul → Revised Romanization ──────────────────────────
    if _contains_hangul(result):
        try:
            from hangul_romanize import Transliter as _Transliter_raw  # type: ignore[import-untyped]
            from hangul_romanize.rule import academic as _academic_raw  # type: ignore[import-untyped]

            Transliter: Any = cast(Any, _Transliter_raw)
            academic: Any = cast(Any, _academic_raw)

            transliter = Transliter(academic)

            # Transliterate syllable-by-syllable; leave non-Hangul spans as-is.
            parts_ko: list[str] = []
            current_hangul: list[str] = []

            def _flush_hangul() -> None:
                if current_hangul:
                    parts_ko.append(str(transliter.translit("".join(current_hangul))))
                    current_hangul.clear()

            for ch in result:
                cp = ord(ch)
                if 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
                    current_hangul.append(ch)
                else:
                    _flush_hangul()
                    parts_ko.append(ch)

            _flush_hangul()
            result = "".join(parts_ko)
        except Exception as exc:
            logger.warning(
                "CJK Language Pack: Korean transliteration failed: %s", exc
            )

    return result


# ---------------------------------------------------------------------------
# MusicBrainz alias extractor
# ---------------------------------------------------------------------------

# Locale prefixes that indicate CJK content in MusicBrainz alias records.
_CJK_LOCALES: tuple[str, ...] = ("zh", "ja", "ko")


def extract_mb_aliases(db_track: Any, **kwargs: Any) -> Any:
    """
    Filter registered on the ``post_musicbrainz_fetch`` hook.

    Parses the raw MusicBrainz recording response for CJK-locale aliases and
    persists them to the ``track_aliases`` and ``artist_aliases`` tables.

    Args:
        db_track:       The SQLAlchemy ``Track`` ORM instance just updated.
        **kwargs:       Expected key: ``mb_data`` — the raw dict returned by
                        ``metadata_provider.get_metadata()``.

    Returns:
        *db_track* unchanged (filter pipeline requirement).
    """
    _raw_mb: Any = kwargs.get("mb_data")
    mb_data: Any = cast(Any, _raw_mb if _raw_mb is not None else {})
    if not mb_data or not db_track:
        return db_track

    # ── Collect track-level aliases from the recording response ───────────
    raw_track_aliases: list[Any] = []
    _ta: Any = mb_data.get("aliases")
    if isinstance(_ta, list):
        for _a in cast(list[Any], _ta):
            if not isinstance(_a, dict):
                continue
            a: Any = cast(Any, _a)
            if str(a.get("locale", "")).startswith(_CJK_LOCALES):
                raw_track_aliases.append(a)

    # ── Collect artist-level aliases from the artist-credit list ──────────
    raw_artist_aliases: list[Any] = []
    _credits: Any = mb_data.get("artist-credit")
    if isinstance(_credits, list):
        for _credit in cast(list[Any], _credits):
            if not isinstance(_credit, dict) or "artist" not in _credit:
                continue
            credit: Any = cast(Any, _credit)
            _artist_node: Any = cast(dict[Any, Any], credit)["artist"]
            if not isinstance(_artist_node, dict):
                continue
            _aa: Any = cast(dict[Any, Any], _artist_node).get("aliases")
            if not isinstance(_aa, list):
                continue
            for _a2 in cast(list[Any], _aa):
                if not isinstance(_a2, dict):
                    continue
                a2: Any = cast(Any, _a2)
                if str(a2.get("locale", "")).startswith(_CJK_LOCALES):
                    raw_artist_aliases.append(a2)

    if not raw_track_aliases and not raw_artist_aliases:
        return db_track

    try:
        from database.music_database import get_database, TrackAlias, ArtistAlias

        db = get_database()
        with db.session_scope() as session:
            # ── Track aliases ─────────────────────────────────────────────
            for a in raw_track_aliases:
                alias_str = str(a.get("name") or a.get("sort-name") or "").strip()
                locale_str = str(a.get("locale") or "").strip()
                if not alias_str:
                    continue
                exists = (
                    session.query(TrackAlias)
                    .filter_by(track_id=db_track.id, alias=alias_str)
                    .first()
                )
                if not exists:
                    session.add(TrackAlias(
                        track_id=db_track.id,
                        alias=alias_str,
                        locale=locale_str or None,
                    ))

            # ── Artist aliases ────────────────────────────────────────────
            for a in raw_artist_aliases:
                alias_str = str(a.get("name") or a.get("sort-name") or "").strip()
                locale_str = str(a.get("locale") or "").strip()
                if not alias_str:
                    continue
                exists = (
                    session.query(ArtistAlias)
                    .filter_by(artist_id=db_track.artist_id, alias=alias_str)
                    .first()
                )
                if not exists:
                    session.add(ArtistAlias(
                        artist_id=db_track.artist_id,
                        alias=alias_str,
                        locale=locale_str or None,
                    ))

        logger.debug(
            "CJK Language Pack: stored %d track alias(es) and %d artist alias(es) for track %d",
            len(raw_track_aliases),
            len(raw_artist_aliases),
            db_track.id,
        )
    except Exception as exc:
        logger.warning("CJK Language Pack: extract_mb_aliases failed: %s", exc)

    return db_track


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def setup(hm: "HookManager") -> None:
    """
    Legacy entry point — kept for compatibility with any caller that invokes
    ``module.setup(hook_manager)`` directly.

    All hook registrations now live in :mod:`plugins.cjk_language_pack`
    (``__init__.py``) and are performed automatically when the package is
    imported by the PluginLoader.  This function is intentionally a no-op so
    that a second call never produces duplicate filter registrations.
    """
    logger.debug(
        "CJK Language Pack plugin.setup() called — hooks already registered "
        "by __init__.py; no action taken."
    )
