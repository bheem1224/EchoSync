"""
Data models for media server content synchronization.
Provides standardized data structures for content changes across providers.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Any, Optional, Dict, Union  # For more specific type annotations
from core.tiered_logger import tiered_logger
import logging  # Add this import for logging levels

# Define placeholder types for Artist, Album, and Track
class Artist:
    pass

class Album:
    parent_id: Optional[str] = None  # Provider-agnostic parent (artist) ID

class Track:
    parent_id: Optional[str] = None          # Provider-agnostic parent (album) ID
    grandparent_id: Optional[str] = None     # Provider-agnostic grandparent (artist) ID

@dataclass
class ContentChanges:
    """
    Standardized container for content changes from media servers.
    Used by MediaServerProvider.get_content_changes_since() to return
    changed content in a provider-agnostic format.
    """
    artists: List[Artist] = field(default_factory=list)
    albums: List[Album] = field(default_factory=list)
    tracks: List[Track] = field(default_factory=list)
    last_checked: Optional[datetime] = None
    full_refresh: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)  # Provider-specific metadata

    def albums_for_artist(self, artist_id: str) -> List[Album]:
        """Get all albums belonging to a specific artist"""
        tiered_logger.log("debug", logging.INFO, f"Filtering albums for artist_id: {artist_id}")
        return [a for a in self.albums if str(getattr(a, 'parent_id', None)) == artist_id]

    def tracks_for_album(self, album_id: str) -> List[Track]:
        """Get all tracks belonging to a specific album"""
        tiered_logger.log("debug", logging.INFO, f"Filtering tracks for album_id: {album_id}")
        return [t for t in self.tracks if str(getattr(t, 'parent_id', None)) == album_id]

    def tracks_for_artist(self, artist_id: str) -> List[Track]:
        """Get all tracks belonging to a specific artist"""
        tiered_logger.log("debug", logging.INFO, f"Filtering tracks for artist_id: {artist_id}")
        return [t for t in self.tracks if str(getattr(t, 'grandparent_id', None)) == artist_id]

    @property
    def total_items(self) -> int:
        """Total number of items across all categories"""
        total = len(self.artists) + len(self.albums) + len(self.tracks)
        tiered_logger.log("debug", logging.INFO, f"Total items calculated: {total}")
        return total

    @property
    def is_empty(self) -> bool:
        """Check if no content changes detected"""
        empty = self.total_items == 0
        tiered_logger.log("debug", logging.INFO, f"ContentChanges is_empty: {empty}")
        return empty

    def __str__(self) -> str:
        return (f"ContentChanges(artists={len(self.artists)}, "
                f"albums={len(self.albums)}, tracks={len(self.tracks)}, "
                f"full_refresh={self.full_refresh})")
