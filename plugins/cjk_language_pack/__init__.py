"""
CJK Language Pack Plugin
========================

This is the first sandbox-compliant plugin built on the "Expand -> Reduce -> Restore" architecture.
It intercepts metadata queries to handle Chinese, Japanese, and Korean characters.

1.  Fast Tripwire: Checks for CJK Unicode blocks.
2.  Expand: Multiplies a search query into original, Pinyin, Traditional, Simplified.
3.  Reduce: Normalizes chaotic incoming text into Pinyin/Romaji for the MatchingEngine.
4.  Restore: Resets the original character script on the track ORM object before saving.
"""

from typing import List, Any
import re
from core.hook_manager import hook_manager
from core.tiered_logger import get_logger

logger = get_logger("plugin.cjk")

# Fast CJK Unicode Block Regex Tripwire
# Covers basic CJK Unified Ideographs, Hiragana, Katakana, Hangul.
CJK_PATTERN = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]')

def contains_cjk(text: str) -> bool:
    if not isinstance(text, str):
        return False
    return bool(CJK_PATTERN.search(text))


# ── HOOK 1: Register Requirements ─────────────────────────────────────────────

def _on_register_metadata_requirements(requirements: List[str]) -> List[str]:
    """Adds the necessary fields to the MusicBrainz metadata fetch payload."""
    logger.debug("Registering CJK metadata requirements.")
    # In a real environment, we ensure these aren't duplicated, but we just append here.
    return requirements + ["musicbrainz_aliases", "release_script", "release_locale"]


# ── HOOK 2: Expand (pre_provider_search) ──────────────────────────────────────

def _on_pre_provider_search(query: str) -> Any:
    """
    Expands the search query if CJK characters are detected.
    Returns a list of search permutations (Original, Pinyin, Traditional, Simplified).
    """
    if not contains_cjk(query):
        return query

    logger.info(f"CJK characters detected in search query: '{query}'. Expanding permutations...")

    # MOCK IMPLEMENTATION:
    # In a real production plugin, we would use OpenCC to convert between Simplified/Traditional
    # and pypinyin for romanization. To respect the strict lightweight requirement, we mock it.
    permutations = [
        query,                      # Original
        query + " (Pinyin)",        # Mock Pinyin
        query + " (Traditional)",   # Mock Traditional
        query + " (Simplified)",    # Mock Simplified
    ]

    return permutations


# ── HOOK 3: Reduce (pre_normalize_text) ───────────────────────────────────────

def _on_pre_normalize_text(raw_text: str) -> str:
    """
    Reduces chaotic CJK text into standardized Pinyin/Romaji so the core
    WeightedMatchingEngine can score it accurately using the Latin alphabet.
    """
    if not contains_cjk(raw_text):
        return raw_text

    logger.debug(f"Reducing CJK string for MatchingEngine: '{raw_text}'")

    # MOCK IMPLEMENTATION:
    # Convert everything to standard Pinyin. For now, we append a mock tag.
    return raw_text + " [Romaji/Pinyin Normalized]"


# ── HOOK 4: Restore (post_metadata_enrichment) ────────────────────────────────

def _on_post_metadata_enrichment(track_obj: Any) -> Any:
    """
    Restores the original intent by looking at the fetched 'release_script'.
    Overwrites the display title and ID3 tags with the accurate character set.
    """
    # Assuming track_obj is a SQLAlchemy Track instance
    if not hasattr(track_obj, 'metadata_status'):
        return track_obj

    # In a real plugin, we would check track_obj.metadata_status.get('release_script') == 'Hant'
    # and then apply OpenCC translation.

    # MOCK IMPLEMENTATION:
    # Since we don't have the actual DB fields easily populated in the mock, we simulate it
    # by writing a flag into the JSON metadata_status block.

    status = track_obj.metadata_status or {}
    if "cjk_restored" not in status:
        status["cjk_restored"] = True
        status["cjk_script_applied"] = "Mock_Traditional"
        track_obj.metadata_status = status
        logger.debug(f"Restored CJK character set for Track ID: {track_obj.id}")

    return track_obj


# ── Plugin Initialization ─────────────────────────────────────────────────────

def initialize_plugin():
    """Wire all hooks into the system."""
    logger.info("Initializing CJK Language Pack Plugin...")

    hook_manager.add_filter('register_metadata_requirements', _on_register_metadata_requirements)
    hook_manager.add_filter('pre_provider_search', _on_pre_provider_search)
    hook_manager.add_filter('pre_normalize_text', _on_pre_normalize_text)
    hook_manager.add_filter('post_metadata_enrichment', _on_post_metadata_enrichment)

    logger.info("CJK Language Pack hooks registered successfully.")

# Auto-initialize when the PluginLoader imports this module
initialize_plugin()
