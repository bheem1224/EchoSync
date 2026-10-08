"""ISRC Registry & Validation module.

Classifies ISRCs into Major Label vs. Digital Aggregator registries
and calculates penalty/bonus adjustments for AcoustID and metadata candidate arbitration.
"""

from __future__ import annotations

import re
from typing import Any

# Standard ISRC pattern: 2 alpha country code, 3 alphanumeric registrant code,
# 2 digit year code, 5 digit designation code (12 characters total).
_ISRC_REGEX = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$")

# Known Major Label Registrant Prefixes (Country Code + Registrant Code = chars 0:5)
# Encompasses Universal Music Group (UMG), Sony Music Entertainment (SME),
# Warner Music Group (WMG), and legacy EMI / Virgin.
MAJOR_LABEL_PREFIXES: frozenset[str] = frozenset({
    # Universal Music Group (UMG)
    "USUM7",
    "DEUM7",
    "GBUM7",
    "USUG1",
    "CAUM7",
    "FRUM7",
    "NLUM7",
    "JPUM7",
    "AUUM7",
    "DKUM7",
    "SEUM7",
    "NOUM7",
    "FIUM7",
    # Sony Music Entertainment (SME) / Columbia / RCA / Epic
    "USSM1",
    "DESN1",
    "GBSMU",
    "GBARL",
    "USRC1",
    "JPSME",
    "CASM1",
    "FRSM1",
    "NLSM1",
    "AUSM1",
    # Warner Music Group (WMG) / Atlantic / Elektra / Parlophone
    "USAT2",
    "USWB1",
    "GBAHT",
    "USAT1",
    "DEE86",
    "CAWB1",
    "FRWB1",
    "NLWB1",
    "AUWB1",
    # EMI / Virgin
    "GBAYE",
    "GBVIR",
})

# Digital aggregator country codes (e.g. QZ is specifically designated for digital aggregators like DistroKid)
DIGITAL_AGGREGATOR_COUNTRY_CODES: frozenset[str] = frozenset({
    "QZ",  # DistroKid, Too Lost, etc.
    "TC",  # TuneCore
})

# Specific known digital aggregator registrant prefixes (chars 0:5)
DIGITAL_AGGREGATOR_PREFIXES: frozenset[str] = frozenset({
    # CD Baby
    "USCG1",
    "USCG2",
    "USHM8",
    "USHM9",
    # Symphonic / Amuse / Ditto / AWAL indie tiers
    "GBK3W",
    "SE6AA",
    "GBBKS",
})


def classify_isrc(isrc: str | None) -> dict[str, Any]:
    """Classify an ISRC into Major Label vs. Digital Aggregator registrant.

    Extracts:
      - Country Code: characters 0:2
      - Registrant Code: characters 2:5
      - Prefix: characters 0:5 (Country + Registrant)

    Returns:
      dict with keys:
        - is_valid (bool)
        - is_major_label (bool)
        - is_aggregator (bool)
        - country_code (str)
        - registrant_code (str)
        - prefix (str)
        - cleaned_isrc (str)
    """
    if not isrc:
        return {
            "is_valid": False,
            "is_major_label": False,
            "is_aggregator": False,
            "country_code": "",
            "registrant_code": "",
            "prefix": "",
            "cleaned_isrc": "",
        }

    cleaned = str(isrc).replace("-", "").strip().upper()
    is_valid = bool(_ISRC_REGEX.match(cleaned))

    if len(cleaned) < 5:
        return {
            "is_valid": False,
            "is_major_label": False,
            "is_aggregator": False,
            "country_code": "",
            "registrant_code": "",
            "prefix": "",
            "cleaned_isrc": cleaned,
        }

    country_code = cleaned[:2]
    registrant_code = cleaned[2:5]
    prefix = cleaned[:5]

    is_major = prefix in MAJOR_LABEL_PREFIXES

    is_agg = (
        country_code in DIGITAL_AGGREGATOR_COUNTRY_CODES
        or prefix in DIGITAL_AGGREGATOR_PREFIXES
        or cleaned.startswith("QZ")
        or cleaned.startswith("TC")
    )

    return {
        "is_valid": is_valid,
        "is_major_label": is_major,
        "is_aggregator": is_agg,
        "country_code": country_code,
        "registrant_code": registrant_code,
        "prefix": prefix,
        "cleaned_isrc": cleaned,
    }


def calculate_isrc_penalty_or_bonus(
    file_isrc: str | None,
    cand_isrcs: list[str] | str | None,
) -> float:
    """Calculate arbitration score penalty or bonus based on ISRC registrant validation.

    Arbitration Rules:
      1. Exact ISRC match: +25.0 bonus.
      2. File is major label but candidate is digital aggregator: -50.0 penalty (disqualification).
      3. Matching label prefix (same country & registrant code): +10.0 bonus.
      4. Default: 0.0 adjustment.

    Args:
      file_isrc: The ISRC embedded in or associated with the physical audio file.
      cand_isrcs: List of ISRCs (or single ISRC string) associated with the candidate recording.

    Returns:
      float adjustment value in [-50.0, 25.0].
    """
    if not file_isrc:
        return 0.0

    if not cand_isrcs:
        return 0.0

    if isinstance(cand_isrcs, str):
        raw_list = [cand_isrcs]
    else:
        raw_list = list(cand_isrcs)

    file_class = classify_isrc(file_isrc)
    if not file_class["is_valid"]:
        return 0.0

    clean_file_isrc = file_class["cleaned_isrc"]

    cand_classes = [classify_isrc(c) for c in raw_list if c]
    # Filter to those that at least have a 5-char prefix or are valid
    cand_classes = [c for c in cand_classes if len(c["cleaned_isrc"]) >= 5]
    if not cand_classes:
        return 0.0

    # Rule 1: Exact match with any candidate ISRC -> +25.0
    for cand_c in cand_classes:
        if cand_c["cleaned_isrc"] == clean_file_isrc:
            return 25.0

    # Rule 2: File is major label but candidate is digital aggregator -> -50.0 (disqualification)
    if file_class["is_major_label"]:
        has_matching_prefix = any(c["prefix"] == file_class["prefix"] for c in cand_classes)
        is_candidate_aggregator = any(c["is_aggregator"] for c in cand_classes)
        if is_candidate_aggregator and not has_matching_prefix:
            return -50.0

    # Rule 3: Matching label prefix -> +10.0
    for cand_c in cand_classes:
        if cand_c["prefix"] == file_class["prefix"]:
            return 10.0

    return 0.0

