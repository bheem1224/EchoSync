"""
Data models for media server content synchronization.
Provides standardized data structures for content changes across providers.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Any, Optional, Dict


@dataclass
class ContentChanges:
    """
    Standardized container for content changes from media servers.
    Used by MediaServerProvider.get_content_changes_since() to return
    changed content in a provider-agnostic format.
    """
    artists: List[Any] = field(default_factory=list)
    albums: List[Any] = field(default_factory=list)
    tracks: List[Any] = field(default_factory=list)
    last_checked: Optional[datetime] = None
    full_refresh: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)  # Provider-specific metadata
    
    def albums_for_artist(self, artist_id: str) -> List[Any]:
        """Get all albums belonging to a specific artist"""
        return [a for a in self.albums if str(getattr(a, 'parentRatingKey', None)) == artist_id]
    
    def tracks_for_album(self, album_id: str) -> List[Any]:
        """Get all tracks belonging to a specific album"""
        return [t for t in self.tracks if str(getattr(t, 'parentRatingKey', None)) == album_id]
    
    def tracks_for_artist(self, artist_id: str) -> List[Any]:
        """Get all tracks belonging to a specific artist"""
        return [t for t in self.tracks if str(getattr(t, 'grandparentRatingKey', None)) == artist_id]
    
    @property
    def total_items(self) -> int:
        """Total number of items across all categories"""
        return len(self.artists) + len(self.albums) + len(self.tracks)
    
    @property
    def is_empty(self) -> bool:
        """Check if no content changes detected"""
        return self.total_items == 0
    
    def __str__(self) -> str:
        return (f"ContentChanges(artists={len(self.artists)}, "
                f"albums={len(self.albums)}, tracks={len(self.tracks)}, "
                f"full_refresh={self.full_refresh})")
