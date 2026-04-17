# 🧠 The Matching Engine

The Matching Engine (`core/matching_engine/`) is the heart of EchoSync. It compares metadata from streaming providers against your local media server or external APIs to determine if a track is a match.

## Core Mechanisms

### 1. Text Parsing & Normalization
Commercial streaming tags are messy. The engine aggressively normalizes strings:
*   Converts all smart quotes and dashes to standard straight characters (`text_utils.py`).
*   Uses `NFKD` Unicode normalization to strip accents and diacritics.
*   **Token-Sort Logic:** Splits strings into words, sorts them alphabetically, and joins them back together. This ensures that "Faye Wong" and "Wong Faye" generate the exact same match score.
*   **CJK/OST Scrubbing:** Strips out parentheticals like `(Original Television Soundtrack)` or lore/character injections before scoring.

### 2. Duration Amnesty
Exact duration matching is impossible due to variable silence padding across different CD/digital releases. EchoSync uses a floating tolerance window:
*   Standard tolerance is ±2 seconds.
*   **Amnesty Logic:** If the engine achieves a perfect 100% semantic text match on both the artist and track title, the duration tolerance is automatically widened to ±15 seconds to catch unlabelled "Extended Mixes" or "Album Versions".

### 3. The "Double-Lock" Logic
Bilingual artists often have shifting metadata across platforms (e.g., Spotify: `Faye 詹雯婷`, Plex: `Faye`). The Double-Lock ensures that if the system maps these two strings together successfully once, it locks the association to prevent false-negative misses in the future without corrupting the database with false-positives.

---

## 🪝 Plugin Hooks (v2.5.0)

*   `pre_normalize_title`: Mutate the raw string before the engine scrubs it.
*   `skip_native_normalization`: Bypass the `NFKD` and Token-Sort logic entirely, returning a custom normalized string.
*   `skip_matching`: Completely replace the fuzzy scoring engine. The plugin receives the `EchosyncTrack` candidate and target, and returns a strict 0-100 float score, bypassing the native WeightedMatchingEngine matrix.

---

## 🪝 Plugin Hooks (v2.5.0)

*   `pre_normalize_title`: Mutate the raw string before the engine scrubs it.
*   `skip_native_normalization`: Bypass the `NFKD` and Token-Sort logic entirely, returning a custom normalized string.
*   `skip_matching`: Completely replace the fuzzy scoring engine. The plugin receives the `EchosyncTrack` candidate and target, and returns a strict 0-100 float score, bypassing the native WeightedMatchingEngine matrix.
