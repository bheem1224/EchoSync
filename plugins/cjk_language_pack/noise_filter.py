"""
CJK Noise Filter
================
Strips CJK-specific structural noise tokens from track / artist strings
**before** the transliterator converts them to Latin phonetics.

Design contract
---------------
This filter handles **only** tokens that are exclusive to CJK text or are the
full-width Unicode equivalents of ASCII terms.  Standard English noise (feat.,
ft., OST, Soundtrack, …) is intentionally left untouched — the core
``text_utils.normalize_text()`` pipeline already removes those after the
``pre_normalize_text`` hook returns.

That clean split prevents double-processing: the CJK plugin owns the ideograph
space; the core normalizer owns the Latin space.

Token inventory
---------------

Japanese
    サントラ                    Abbreviation of "サウンドトラック" (Soundtrack)
    オリジナルサウンドトラック    "Original Soundtrack"
    主題歌                      Theme song (OP/ED marker in OST listings)
    挿入歌                      Insert song (variant of 插曲 in Japanese)
    と                          "and" when used as an artist separator (e.g. "A と B")
    【…】                       Full-width/CJK corner brackets (structural noise)
    「…」                       Japanese corner quotation marks

Chinese
    原声带                       Original soundtrack (Mandarin)
    原声                        Abbreviated form of 原声带
    主题曲                       Theme song
    片头曲                       Opening theme
    片尾曲                       Ending theme
    插曲                        Insert song

Korean
    오에스티                     OST (phonetic)
    사운드트랙                    Soundtrack

Full-width Latin noise (Unicode half→full rotations of ASCII terms)
    ｆｅａｔ                     Full-width "feat"
    Ｆｅａｔ / ＦＥＡＴ variants
    ＯＳＴ                       Full-width "OST"
    ＆                          Full-width ampersand — normalised to ASCII '&'

These full-width Latin tokens are normalised by ``normalize_chars()`` in the
core pipeline, but stripping them here first avoids them being carried into the
Romaji/Pinyin output where they would look like garbled Latin noise.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# Parenthetical / bracketed wrappers — any balanced pair of:
#   (…)  （…）  [...]  【…】  「…」  『…』  〈…〉  《…》
# Matches only if the inner content contains CJK noise or is purely Latin noise.
# Approach: strip the specific token inside known structural chars rather than
# removing all bracketed content (which would destroy legitimate album info).

# Full-width bracket strip — 【...】 and 「...」 and 『...』
_FW_BRACKET_RE = re.compile(
    r"[【「『〈《]([^】」』〉》]*?)[】」』〉》]"
)

# Japanese structural noise — standalone terms (word-boundary aware for mixed strings)
_JAPANESE_NOISE_RE = re.compile(
    r"(?:"
    r"オリジナルサウンドトラック"   # "Original Soundtrack"
    r"|サントラ"                   # "Santora" (abbrev.)
    r"|主題歌"                     # Theme song
    r"|挿入歌"                     # Insert song
    r"|エンディングテーマ"           # Ending theme
    r"|オープニングテーマ"           # Opening theme
    r")"
)

# Chinese structural noise
_CHINESE_NOISE_RE = re.compile(
    r"(?:"
    r"原声带"                      # Original Soundtrack (Mandarin)
    r"|原声"                       # Abbreviated form
    r"|主题曲"                     # Theme song
    r"|片头曲"                     # Opening theme
    r"|片尾曲"                     # Ending theme
    r"|插曲"                       # Insert song
    r")"
)

# Korean structural noise
_KOREAN_NOISE_RE = re.compile(
    r"(?:"
    r"오에스티"                    # OST (phonetic)
    r"|사운드트랙"                  # Soundtrack
    r")"
)

# Full-width Latin noise — feat / OST variants plus full-width ampersand
_FW_LATIN_NOISE_RE = re.compile(
    r"(?:"
    r"[ｆＦ][ｅＥ][ａＡ][ｔＴ]\.?"  # ｆｅａｔ / Ｆｅａｔ / ＦＥＡＴ (optional full-width period)
    r"|[ＯｏＯ][ＳｓＳ][ＴｔＴ]"      # ＯＳＴ etc.
    r")"
)

# Japanese の / と used as structural separators:
#   "AとB" → artist separator; strip " と " with surrounding spaces.
#   "の" as possessive is meaningful and must NOT be stripped.
_JA_AND_RE = re.compile(r"(?<!\S)\s*と\s*(?=\S)")

# Normalise full-width ampersand → ASCII '&'
_FW_AMP_RE = re.compile(r"＆")

# Collapse multiple spaces left by stripping
_SPACE_RE = re.compile(r"\s{2,}")

# Empty / whitespace-only bracket pairs left after noise stripping
# Covers ASCII (), full-width （）, and square []
_EMPTY_PARENS_RE = re.compile(r"[(\[（]\s*[)\]）]")


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class NoiseFilter:
    """
    Stateless CJK noise stripper.

    All methods operate on a single string and return a cleaned string.
    ``strip_cjk_noise(text)`` is the primary entry point; it runs all passes
    in order and is safe to call on any string — non-CJK text is returned
    unchanged after a fast tripwire check.

    Example::

        nf = NoiseFilter()
        nf.strip_cjk_noise("ドラゴン桜 主題歌")     # → "ドラゴン桜"
        nf.strip_cjk_noise("晴天 (原声带)")          # → "晴天"
        nf.strip_cjk_noise("YOASOBI feat. Artist")  # → "YOASOBI feat. Artist"  (untouched)
    """

    # Fast CJK / full-width Latin tripwire
    _TRIPWIRE = re.compile(
        r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af"  # CJK/kana/hangul
        r"\uff01-\uff60\uffe0-\uffe6]"               # Full-width forms
    )

    def has_cjk_or_fullwidth(self, text: str) -> bool:
        """Return True if *text* contains CJK or full-width characters."""
        return bool(self._TRIPWIRE.search(text))

    # ── Individual passes (public for testing) ────────────────────────────

    def strip_fullwidth_brackets(self, text: str) -> str:
        """Remove full-width bracket pairs 【…】「…」『…』〈…〉《…》."""
        return _FW_BRACKET_RE.sub("", text)

    def strip_japanese_noise(self, text: str) -> str:
        """Remove Japanese OST/theme structural terms."""
        return _JAPANESE_NOISE_RE.sub("", text)

    def strip_chinese_noise(self, text: str) -> str:
        """Remove Chinese OST/theme structural terms."""
        return _CHINESE_NOISE_RE.sub("", text)

    def strip_korean_noise(self, text: str) -> str:
        """Remove Korean OST structural terms."""
        return _KOREAN_NOISE_RE.sub("", text)

    def strip_fullwidth_latin_noise(self, text: str) -> str:
        """Remove / normalise full-width Latin noise tokens."""
        text = _FW_LATIN_NOISE_RE.sub("", text)
        text = _FW_AMP_RE.sub("&", text)
        return text

    def strip_japanese_and_separator(self, text: str) -> str:
        """Replace a leading 'と' artist separator with ' & '."""
        return _JA_AND_RE.sub(" & ", text)

    # ── Primary entry point ───────────────────────────────────────────────

    def strip_cjk_noise(self, text: str) -> str:
        """
        Run all CJK noise passes and return a cleaned string.

        Non-CJK / non-full-width strings are returned immediately via the
        fast tripwire — zero regex work for pure ASCII / Latin input.

        Pass order:
            1. Full-width bracket removal   (structural wrappers first)
            2. Full-width Latin noise       (ｆｅａｔ, ＯＳＴ, ＆)
            3. Japanese noise terms
            4. Chinese noise terms
            5. Korean noise terms
            6. Japanese 'と' separator
            7. Whitespace collapse
        """
        if not isinstance(text, str) or not self.has_cjk_or_fullwidth(text):
            return text

        text = self.strip_fullwidth_brackets(text)
        text = self.strip_fullwidth_latin_noise(text)
        text = self.strip_japanese_noise(text)
        text = self.strip_chinese_noise(text)
        text = self.strip_korean_noise(text)
        text = self.strip_japanese_and_separator(text)
        text = _EMPTY_PARENS_RE.sub("", text)   # remove empty () left after noise strip
        text = _SPACE_RE.sub(" ", text).strip()

        return text


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_noise_filter: NoiseFilter | None = None


def get_noise_filter() -> NoiseFilter:
    """Return (or lazily create) the module-level :class:`NoiseFilter`."""
    global _noise_filter
    if _noise_filter is None:
        _noise_filter = NoiseFilter()
    return _noise_filter
