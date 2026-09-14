"""Title similarity trust gate to prevent false candidate metadata adoptions."""

import difflib
import re
from pathlib import Path

from core.matching_engine.text_utils import normalize_title


def is_generic_title(title: str | Path | None) -> bool:
    """Check if a title extracted from filename is generic (e.g. 'track 01', 'audio', '01', 'cached_song')."""
    if not title or not str(title).strip():
        return True
    t = str(title).strip().lower()
    t_clean = re.sub(r"[\s\-_.]+", " ", t).strip()
    if not t_clean:
        return True
    if re.fullmatch(r"^(?:track|audio|title|disc|side|cd|song|file)(?:\s*\d+)*$", t_clean) or re.fullmatch(
        r"^\d+$", t_clean
    ):
        return True
    generic_words = {
        "unknown",
        "unknown track",
        "unknown title",
        "unknown artist",
        "untitled",
        "audio",
        "track",
        "input",
        "output",
        "sound",
        "song",
        "cached song",
        "song cached",
        "song with tag",
        "test song",
        "dummy",
        "temp",
        "music",
        "corrupted",
        "corrupted track",
        "corrupted song",
    }
    if t_clean in generic_words:
        return True
    tokens = set(t_clean.split())
    return tokens.issubset(
        {
            "cached",
            "song",
            "with",
            "tag",
            "test",
            "audio",
            "track",
            "file",
            "dummy",
            "temp",
            "surround",
            "sound",
            "corrupted",
            "isrc",
        }
    )


def is_cross_script(s1: str, s2: str) -> bool:
    """Returns True if one string has CJK/Cyrillic characters and the other is purely Latin/ASCII."""

    def has_non_latin(s: str) -> bool:
        return any(
            "\u4e00" <= ch <= "\u9fff"  # CJK Unified
            or "\u3040" <= ch <= "\u309f"  # Hiragana
            or "\u30a0" <= ch <= "\u30ff"  # Katakana
            or "\uac00" <= ch <= "\ud7af"  # Hangul
            or "\u0400" <= ch <= "\u04ff"  # Cyrillic
            for ch in s
        )

    return has_non_latin(s1) != has_non_latin(s2)


def sanitize_title_from_filename(filename: str | Path) -> str:
    """Extract clean title from filename by stripping track numbers and delimiters."""
    base = Path(filename).stem
    # Strip leading track numbers e.g. "00 - ", "01. ", "01 - ", "12 ", etc.
    cleaned = re.sub(r"^\d+[\s\-_.]+", "", base)
    return cleaned.strip()


# Alias for compatibility with clean_title_from_filename convention
clean_title_from_filename = sanitize_title_from_filename


def verify_title_trust_gate(
    candidate_title: str,
    baseline_title: str | None = None,
    filename: str | None = None,
    tag_title: str | None = None,
    min_similarity: float = 0.60,
) -> bool:
    """Verify that a proposed candidate title is sufficiently similar to the baseline title.

    Compares candidate title against:
    1. Existing track baseline title
    2. Clean filename (with track number stripped)
    3. Embedded ID3/flac tag title

    Returns True if similarity >= min_similarity (default 0.60), False otherwise.
    If baseline_title contradicts an identifiable physical filename, the candidate MUST
    confirm against the physical filename to prevent circular cache poisoning.
    """
    if not candidate_title or not str(candidate_title).strip():
        return False

    clean_candidate = str(candidate_title).lower().strip()
    norm_candidate = normalize_title(clean_candidate)

    clean_file = None
    file_sim = 0.0
    file_is_identifiable = False

    if filename and str(filename).strip():
        raw_file_title = sanitize_title_from_filename(filename)
        if raw_file_title and not is_generic_title(raw_file_title):
            clean_file = raw_file_title.lower().strip()
            norm_file = normalize_title(clean_file)
            file_sim = max(
                difflib.SequenceMatcher(None, clean_candidate, clean_file).ratio(),
                difflib.SequenceMatcher(None, norm_candidate, norm_file).ratio(),
            )
            file_is_identifiable = True

    clean_tag = str(tag_title).lower().strip() if tag_title and str(tag_title).strip() else None
    tag_cand_sim = 0.0
    if clean_tag:
        norm_tag = normalize_title(clean_tag)
        tag_cand_sim = max(
            difflib.SequenceMatcher(None, clean_candidate, clean_tag).ratio(),
            difflib.SequenceMatcher(None, norm_candidate, norm_tag).ratio(),
        )

    # Check for contradiction between dirty baseline_title and identifiable physical filename
    if (
        file_is_identifiable
        and clean_file
        and baseline_title
        and str(baseline_title).strip()
        and not is_cross_script(str(baseline_title), clean_file)
    ):
        clean_baseline = str(baseline_title).lower().strip()
        norm_baseline = normalize_title(clean_baseline)
        base_file_sim = max(
            difflib.SequenceMatcher(None, clean_baseline, clean_file).ratio(),
            difflib.SequenceMatcher(None, norm_baseline, norm_file).ratio(),
        )
        # If DB baseline contradicts physical filename stem and candidate also contradicts filename stem:
        if base_file_sim < min_similarity and file_sim < min_similarity and tag_cand_sim < min_similarity:
            return False

    ratios = []

    if baseline_title and str(baseline_title).strip() and not is_generic_title(baseline_title):
        clean_baseline = str(baseline_title).lower().strip()
        norm_baseline = normalize_title(clean_baseline)
        ratios.append(difflib.SequenceMatcher(None, clean_candidate, clean_baseline).ratio())
        ratios.append(difflib.SequenceMatcher(None, norm_candidate, norm_baseline).ratio())

    if file_is_identifiable and clean_file:
        ratios.append(file_sim)

    if tag_title and str(tag_title).strip():
        clean_tag = str(tag_title).lower().strip()
        norm_tag = normalize_title(clean_tag)
        ratios.append(difflib.SequenceMatcher(None, clean_candidate, clean_tag).ratio())
        ratios.append(difflib.SequenceMatcher(None, norm_candidate, norm_tag).ratio())

    if not ratios:
        # If no baseline information exists whatsoever, allow update
        return True

    return max(ratios) >= min_similarity
