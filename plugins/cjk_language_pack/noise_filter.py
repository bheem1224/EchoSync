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

# ---------------------------------------------------------------------------
# OST Block "Black Hole" — strips the entire descriptive metadata block
# ---------------------------------------------------------------------------
#
# Problem: individual term stripping (e.g. removing only 主题曲) leaves behind
# dirty fragments like "电视剧温情" from an original "电视剧《苍兰诀》温情主题曲".
#
# Solution: match the COMPLETE block from a *media-type indicator* all the way
# through to a *song-role indicator*, consuming everything in between (random
# adjectives, character names, decorated brackets, etc.).
#
# Pattern anatomy (each group is non-capturing):
#
#   LEAD_SEP   — optional leading separator: space / hyphen / ～ / · / （ / (
#   MEDIA      — media-type word:  电视剧 | 网剧 | 影视剧 | 影視劇 | 剧集 |
#                                  电影 | 动画片 | 动画 | 手游 | 游戏
#   MID        — anything between: brackets, adjectives, character names, spaces
#                (non-greedy; won't swallow an unrelated separator like " - ")
#   SONG       — song-role word:   主题曲 | 插曲 | 片尾曲 | 片头曲 | 人物曲 |
#                                  推广曲 | 同行曲 | 时光曲 | 原声带 | 大碟 |
#                                  片頭曲 | 片尾曲 (trad.) | 主題曲 (trad.)
#   TRAIL_SEP  — optional trailing separator / closing bracket: 】 ） ) etc.
#
# The regex is applied in a loop (re.sub with count=0) because a title may
# contain multiple consecutive OST blocks.

_OST_BLOCK_MEDIA = (
    r"(?:"
    r"电视剧|网剧|影视剧|影視劇|剧集"
    r"|电影|动画片|动画|手游|游戏"
    r")"
)

_OST_BLOCK_SONG = (
    r"(?:"
    r"[\u4e00-\u9fff]{1,5}曲"   # any 1–5 CJK chars ending in 曲 —
                                 # catches 主题曲, 插曲, 片头曲, 片尾曲, 人物曲,
                                 #         推广曲, 同行曲, 时光曲, 勇气曲, etc.
    r"|原声带|原聲帶"             # Soundtrack (no 曲 ending)
    r"|大碟"                     # Album marker (no 曲 ending)
    r")"
)

# Full "Black Hole" pattern — optional lead separator, media word, freeform
# middle (lazy), song-role word, optional trailing bracket/separator.
_OST_BLOCK_RE = re.compile(
    r"(?:"
    r"[\s\-–—～·]"             # optional lead separator (space, dash, middle dot)
    r"|[（(【「]"               # …or an opening bracket
    r")*"
    + _OST_BLOCK_MEDIA
    + r"(?:[^。！？\n]*?)"      # freeform middle — lazy, won't cross sentence boundary
    + _OST_BLOCK_SONG
    + r"(?:"
    r"[）)】」]"                # optional closing bracket
    r"|[\s\-–—～·]"             # …or a trailing separator
    r")*",
    re.UNICODE,
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
# Leading character / actor tag injected by streaming services (e.g. Spotify).
#
# Some platforms prefix a track title with the character or actor name in
# brackets when a song is associated with a specific role in a drama/anime:
#
#   [Jiang Cheng] Hen Bie      →  Hen Bie
#   【薛洋】荒城渡              →  荒城渡
#   （宸玖）同行               →  同行
#   （林深）见鹿                →  见鹿
#
# The local database holds the bare title without the actor prefix, so the
# prefix must be stripped before fuzzy scoring takes place.
#
# Match criteria:
#   • The bracket pair must start at the very beginning of the string (^).
#   • Content inside the brackets is non-greedy and may contain any
#     character EXCEPT a newline.
#   • One or more trailing whitespace characters are consumed so the
#     remaining title does not start with a stray space.
#   • Three bracket flavours are matched:
#       [ ... ]   ASCII square brackets  (used by Spotify for Latin names)
#       【 ... 】  CJK square brackets    (used in Chinese streaming metadata)
#       （ ... ）  Full-width parentheses  (used in Japanese/Chinese metadata)
#
# IMPORTANT: this pattern is intentionally NOT guarded by the CJK tripwire
# because `[Jiang Cheng] Hen Bie` is pure ASCII yet still needs stripping.
_LEADING_BRACKET_RE = re.compile(
    r"^(?:"
    r"\[.*?\]"          # ASCII square brackets  [ ... ]
    r"|【.*?】"           # CJK corner brackets   【 ... 】
    r"|（.*?）"           # Full-width parens      （ ... ）
    r")\s*"              # consume any trailing whitespace (including zero for CJK)
    r"(?=\S)",           # lookahead: something must follow — prevents stripping lone [Tag]
    re.UNICODE,
)

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

    def strip_leading_character_tag(self, text: str) -> str:
        """Remove a leading bracketed character/actor tag from the start of *text*.

        Targets patterns injected by streaming services (e.g. Spotify) that
        prefix a track title with the associated drama character or actor name::

            [Jiang Cheng] Hen Bie   →  Hen Bie
            【薛洋】荒城渡           →  荒城渡
            （宸玖）同行            →  同行

        The bracket pair must be at position 0 and must be followed by at
        least one whitespace character — this prevents accidental stripping of
        titles that are legitimately wrapped in brackets (e.g. ``[Single]``).

        Unlike most NoiseFilter passes this method is NOT guarded by the CJK
        tripwire: ASCII square brackets (``[Name]``) occur on purely Latin
        titles and must be handled even when ``has_cjk_or_fullwidth`` returns
        False.
        """
        if not isinstance(text, str):
            return text
        return _LEADING_BRACKET_RE.sub("", text)

    def strip_ost_block(self, text: str) -> str:
        """Strip the entire media+song-role descriptive OST block in one pass.

        Replaces patterns like:
          - 《苍兰诀》温情主题曲      (adjective 温情 is consumed, not left behind)
          - （影视劇宸玖·同行曲）  (full decorated block)
          - (剧集自爱勇气曲)           (ASCII-paren variant)
          - 动画片头曲               (no separator, plain inline block)

        Runs re.sub with no count limit so multiple consecutive blocks are all
        removed in a single call.
        """
        return _OST_BLOCK_RE.sub("", text)

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
            0. Leading character/actor tag  (bracket at string start, pre-CJK check)
            1. OST Block "Black Hole"       (media+freeform+song-role in one sweep)
            2. Full-width bracket removal   (structural wrappers)
            3. Full-width Latin noise       (ｆｅａｔ, ＯＳＴ, ＆)
            4. Japanese noise terms
            5. Chinese noise terms
            6. Korean noise terms
            7. Japanese 'と' separator
            8. Whitespace collapse
        """
        # Pass 0 runs BEFORE the CJK tripwire — it handles pure-ASCII titles
        # like "[Jiang Cheng] Hen Bie" that contain no CJK/full-width chars.
        text = self.strip_leading_character_tag(text)

        if not isinstance(text, str) or not self.has_cjk_or_fullwidth(text):
            return text

        text = self.strip_ost_block(text)        # ← NEW: black-hole pass first
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
