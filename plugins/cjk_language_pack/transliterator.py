"""
CJK Transliteration Engine
===========================
Offline wrapper around opencc (Trad↔Simp), pypinyin (Chinese→Pinyin),
pykakasi (Japanese→Hepburn Romaji), and hangul_romanize (Korean→Revised
Romanization).

All four library imports are **deferred** to first use inside method bodies so
startup cost is zero when the library contains no CJK metadata.  On the first
CJK string each import is resolved and cached by Python's module machinery;
subsequent calls pay only function-call overhead.

Each language block is wrapped in its own ``try/except``.  A missing or broken
dependency causes that block to be skipped silently and the partially-processed
(or original) string is returned — a bad dependency never crashes the pipeline.
"""

from __future__ import annotations

import re
from typing import Optional

from core.tiered_logger import get_logger

logger = get_logger("cjk_language_pack.transliterator")

# ── Unicode block patterns ─────────────────────────────────────────────────────

_CJK_RE = re.compile(
    r"[\u4e00-\u9fff"       # CJK Unified Ideographs
    r"\u3400-\u4dbf"        # CJK Extension A
    r"\uf900-\ufaff"        # CJK Compatibility Ideographs
    r"\u3040-\u309f"        # Hiragana
    r"\u30a0-\u30ff"        # Katakana
    r"\uac00-\ud7af"        # Hangul Syllables
    r"\u1100-\u11ff]"       # Hangul Jamo
)

# Chinese ideographs only (no kana/hangul)
_CHINESE_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")

# Japanese: kana + common-use kanji block (mix triggers pykakasi)
_JAPANESE_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")

# Pure kana (hiragana or katakana) — confirms Japanese, not just Chinese kanji
_KANA_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")

# Korean Hangul
_KOREAN_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff]")


class CJKTransliterator:
    """
    Offline CJK → Latin transliteration with lazy-loaded library imports.

    Supports:
    - Traditional ↔ Simplified Chinese conversion  (opencc)
    - Chinese → tone-stripped Pinyin              (pypinyin)
    - Japanese kana / kanji → Hepburn Romaji      (pykakasi)
    - Korean Hangul → Revised Romanization        (hangul_romanize)

    Usage::

        t = CJKTransliterator()
        t.flatten_to_romaji("約束のネバーランド")   # → "yakusoku no neverrando"
        t.flatten_to_romaji("晴天")               # → "qing tian"
        t.flatten_to_romaji("봄날")               # → "bom nal"
        t.script_variants("晴天")                 # → ["晴天", "qing tian"]
    """

    def __init__(self) -> None:
        self._t2s: object | None = None   # opencc: Traditional → Simplified
        self._s2t: object | None = None   # opencc: Simplified  → Traditional

    # ── Public helpers ─────────────────────────────────────────────────────────

    def has_cjk(self, text: str) -> bool:
        """Return True if *text* contains at least one CJK / Hangul codepoint."""
        if not isinstance(text, str):
            return False
        return bool(_CJK_RE.search(text))

    def to_simplified(self, text: str) -> str:
        """Convert Traditional Chinese → Simplified using opencc (best-effort)."""
        if not _CHINESE_RE.search(text):
            return text
        try:
            import opencc  # type: ignore
            if self._t2s is None:
                self._t2s = opencc.OpenCC("t2s")
            return self._t2s.convert(text)
        except Exception as exc:
            logger.debug("opencc t2s conversion failed: %s", exc)
            return text

    def to_traditional(self, text: str) -> str:
        """Convert Simplified Chinese → Traditional using opencc (best-effort)."""
        if not _CHINESE_RE.search(text):
            return text
        try:
            import opencc  # type: ignore
            if self._s2t is None:
                self._s2t = opencc.OpenCC("s2t")
            return self._s2t.convert(text)
        except Exception as exc:
            logger.debug("opencc s2t conversion failed: %s", exc)
            return text

    def to_pinyin(self, text: str) -> str:
        """Convert Chinese ideographs → space-separated tone-stripped Pinyin."""
        if not _CHINESE_RE.search(text):
            return text
        try:
            from pypinyin import lazy_pinyin, Style  # type: ignore
            syllables = lazy_pinyin(text, style=Style.NORMAL)
            return " ".join(syllables)
        except Exception as exc:
            logger.debug("pypinyin conversion failed: %s", exc)
            return text

    def to_romaji(self, text: str) -> str:
        """Convert Japanese kana / kanji → Hepburn Romaji using pykakasi."""
        if not _JAPANESE_RE.search(text):
            return text
        try:
            import pykakasi  # type: ignore
            kks = pykakasi.kakasi()
            items = kks.convert(text)
            return " ".join(i["hepburn"] for i in items if i.get("hepburn"))
        except Exception as exc:
            logger.debug("pykakasi conversion failed: %s", exc)
            return text

    def to_hangul_latin(self, text: str) -> str:
        """Convert Korean Hangul → Revised Romanization using hangul_romanize."""
        if not _KOREAN_RE.search(text):
            return text
        try:
            from hangul_romanize import Transliter      # type: ignore
            from hangul_romanize.rule import academic   # type: ignore
            transliter = Transliter(academic)

            parts: list[str] = []
            buf: list[str] = []

            def _flush() -> None:
                if buf:
                    parts.append(str(transliter.translit("".join(buf))))
                    buf.clear()

            for ch in text:
                cp = ord(ch)
                if 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
                    buf.append(ch)
                else:
                    _flush()
                    parts.append(ch)
            _flush()
            return "".join(parts)
        except Exception as exc:
            logger.debug("hangul_romanize conversion failed: %s", exc)
            return text

    def flatten_to_romaji(self, text: str) -> str:
        """
        Return a pure-Latin phonetic representation of *text*.

        Detection order (dominant script wins first):

        1. Korean Hangul  → Revised Romanization
        2. Japanese kana  → Hepburn Romaji  (pykakasi handles mixed kanji+kana)
        3. Chinese CJK    → Pinyin          (opencc Simplified first, then pypinyin)
        4. Non-CJK text   → returned unchanged

        Each step is fault-isolated; a broken library degrades silently.
        """
        if not isinstance(text, str) or not self.has_cjk(text):
            return text

        result = text

        # Korean pass — Hangul is unambiguous
        if _KOREAN_RE.search(result):
            result = self.to_hangul_latin(result)

        # Japanese pass — kana presence confirms Japanese; pykakasi handles
        # mixed kanji+kana spans in a single conversion.
        if _KANA_RE.search(result):
            result = self.to_romaji(result)

        # Chinese pass — any remaining CJK ideographs after the Japanese pass
        if _CHINESE_RE.search(result):
            simplified = self.to_simplified(result)
            result = self.to_pinyin(simplified)

        return result

    def script_variants(self, text: str) -> list[str]:
        """
        Return all meaningful script variants of *text*, deduplicated,
        with the original form first.

        Chinese  → [original, simplified?, traditional?, pinyin]
        Japanese → [original, romaji]
        Korean   → [original, revised_romanization]
        Latin    → [original]
        """
        if not self.has_cjk(text):
            return [text]

        seen: list[str] = [text]

        def _add(variant: str) -> None:
            if variant and variant not in seen:
                seen.append(variant)

        # Korean (only Hangul, no ideographs)
        if _KOREAN_RE.search(text) and not _CHINESE_RE.search(text) and not _KANA_RE.search(text):
            _add(self.to_hangul_latin(text))
            return seen

        # Japanese (kana present)
        if _KANA_RE.search(text):
            _add(self.to_romaji(text))
            return seen

        # Chinese
        simplified  = self.to_simplified(text)
        traditional = self.to_traditional(text)
        pinyin      = self.to_pinyin(simplified)
        _add(simplified)
        _add(traditional)
        _add(pinyin)
        return seen


# ── Module-level singleton ──────────────────────────────────────────────────────

_transliterator: CJKTransliterator | None = None


def get_transliterator() -> CJKTransliterator:
    """Return (or lazily create) the module-level :class:`CJKTransliterator`."""
    global _transliterator
    if _transliterator is None:
        _transliterator = CJKTransliterator()
    return _transliterator
