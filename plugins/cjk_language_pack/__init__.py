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


# ── HOOK 4: Restore + Persist Aliases (post_metadata_enrichment) ─────────────

def _build_alias_entries(track_obj: Any) -> list:
    """
    Derive localised alias entries from a track's metadata_status payload.

    Expects metadata_status to optionally contain a 'cjk_aliases' list of dicts:
      [{"name": "...", "locale": "zh", "script": "Hant", "is_primary_for_locale": True}, ...]

    When the key is absent we synthesise a minimal Romaji/Pinyin placeholder so
    the alias table is never left empty for a CJK track.
    """
    status = track_obj.metadata_status or {}
    declared = status.get("cjk_aliases")
    if declared and isinstance(declared, list):
        return declared

    # Synthesise Pinyin/Romaji placeholder from the existing title.
    title = getattr(track_obj, "title", "") or ""
    if not contains_cjk(title):
        return []

    return [
        {
            "name": title + " [Romaji/Pinyin]",
            "locale": "en",
            "script": "Latn",
            "is_primary_for_locale": True,
        }
    ]


def _persist_track_aliases(track_obj: Any, alias_entries: list) -> None:
    """Write alias rows to the database, ignoring duplicates (upsert-safe)."""
    if not alias_entries:
        return
    try:
        from database.music_database import TrackAlias, get_database
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        db = get_database()
        with db.session_scope() as session:
            for entry in alias_entries:
                name = entry.get("name") or ""
                if not name:
                    continue
                existing = (
                    session.query(TrackAlias)
                    .filter_by(
                        track_id=track_obj.id,
                        locale=entry.get("locale"),
                        script=entry.get("script"),
                        name=name,
                    )
                    .first()
                )
                if existing is None:
                    session.add(
                        TrackAlias(
                            track_id=track_obj.id,
                            name=name,
                            locale=entry.get("locale"),
                            script=entry.get("script"),
                            is_primary_for_locale=bool(entry.get("is_primary_for_locale", False)),
                        )
                    )
        logger.debug(
            "Persisted %d alias row(s) for Track ID %s", len(alias_entries), track_obj.id
        )
    except Exception as exc:
        # Never crash the enrichment pipeline — alias persistence is best-effort.
        logger.warning("Failed to persist CJK aliases for Track ID %s: %s", track_obj.id, exc)


def _on_post_metadata_enrichment(track_obj: Any) -> Any:
    """
    1. Marks cjk_restored on metadata_status so downstream code knows the
       script was inspected.
    2. Derives alias rows (Romaji, Pinyin, Traditional, etc.) and writes them
       to the track_aliases table via the MusicDatabase session.
    """
    if not hasattr(track_obj, 'metadata_status') or not hasattr(track_obj, 'id'):
        return track_obj

    title = getattr(track_obj, "title", "") or ""
    if not contains_cjk(title):
        return track_obj

    status = dict(track_obj.metadata_status or {})
    if "cjk_restored" not in status:
        status["cjk_restored"] = True
        status["cjk_script_applied"] = status.get("release_script", "Latn")
        track_obj.metadata_status = status
        logger.debug("Restored CJK character set for Track ID: %s", track_obj.id)

    alias_entries = _build_alias_entries(track_obj)
    _persist_track_aliases(track_obj, alias_entries)

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


# ── HOOK 5: Registry Override ───────────────────────────────────────────────
from core.provider import ServiceRegistry
from core.matching_engine.matching_engine import WeightedMatchingEngine

class CJKMatchingEngine(WeightedMatchingEngine):
    pass

ServiceRegistry.register_override('com.soulsync.cjk-pack', CJKMatchingEngine)
