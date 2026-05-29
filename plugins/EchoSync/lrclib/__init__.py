"""
LRClib Lyrics Provider
Fetches synchronized lyrics and creates .lrc sidecar files
"""

from .provider import LRCLibProvider

ProviderClass = LRCLibProvider

__all__ = ['LRCLibProvider', 'ProviderClass']
