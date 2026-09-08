"""Title similarity trust gate to prevent false candidate metadata adoptions."""

import difflib
import re
from pathlib import Path

from core.matching_engine.text_utils import normalize_title


def sanitize_title_from_filename(filename: str | Path) -> str:
    """Extract clean title from filename by stripping track numbers and delimiters."""
    base = Path(filename).stem
    # Strip leading track numbers e.g. "00 - ", "01. ", "01 - ", "12 ", etc.
    cleaned = re.sub(r"^\d+[\s\-_.]+", "", base)
    return cleaned.strip()


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
    """
    if not candidate_title or not str(candidate_title).strip():
        return False

    clean_candidate = str(candidate_title).lower().strip()
    norm_candidate = normalize_title(clean_candidate)

    ratios = []

    if baseline_title and str(baseline_title).strip():
        clean_baseline = str(baseline_title).lower().strip()
        norm_baseline = normalize_title(clean_baseline)
        ratios.append(difflib.SequenceMatcher(None, clean_candidate, clean_baseline).ratio())
        ratios.append(difflib.SequenceMatcher(None, norm_candidate, norm_baseline).ratio())

    if filename and str(filename).strip():
        clean_file = sanitize_title_from_filename(filename).lower().strip()
        if clean_file:
            norm_file = normalize_title(clean_file)
            ratios.append(difflib.SequenceMatcher(None, clean_candidate, clean_file).ratio())
            ratios.append(difflib.SequenceMatcher(None, norm_candidate, norm_file).ratio())

    if tag_title and str(tag_title).strip():
        clean_tag = str(tag_title).lower().strip()
        norm_tag = normalize_title(clean_tag)
        ratios.append(difflib.SequenceMatcher(None, clean_candidate, clean_tag).ratio())
        ratios.append(difflib.SequenceMatcher(None, norm_candidate, norm_tag).ratio())

    if not ratios:
        # If no baseline information exists whatsoever, allow update
        return True

    return max(ratios) >= min_similarity
