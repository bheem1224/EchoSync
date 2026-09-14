"""
Legacy compatibility shim.

This module re-exports PathMapper from its new canonical location in `core.utils`
to prevent ModuleNotFoundError exceptions during legacy plugin initialization
(e.g., EchoSync.plex v2.4.2).
"""

from core.utils import PathMapper

__all__ = ["PathMapper"]
