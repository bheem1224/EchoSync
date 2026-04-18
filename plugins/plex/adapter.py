"""
Plex Provider Adapter - DEPRECATED

This adapter is no longer needed. The Plex client.py now returns EchosyncTrack directly.

For backward compatibility, this module remains but should not be used in new code.
Direct usage of PlexClient is recommended instead.
"""

from core.tiered_logger import get_logger

logger = get_logger("plex_adapter")

