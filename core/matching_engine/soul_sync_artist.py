from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class SoulSyncArtist:
    """
    Foundational artist representation in the matching engine.
    Allows for Lidarr-style artist tracking and discovery suggestions.
    """
    id: Optional[int] = None
    name: str = ""
    musicbrainz_id: Optional[str] = None
    tracking_enabled: bool = True
    albums: List['SoulSyncAlbum'] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.name or "Unknown Artist"
