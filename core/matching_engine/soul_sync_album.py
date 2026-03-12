from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date

from core.matching_engine.soul_sync_track import SoulSyncTrack

@dataclass
class SoulSyncAlbum:
    """
    Foundational album representation in the matching engine.
    Allows for album-level suggestions and library ingestion tracking.
    """
    id: Optional[int] = None
    title: str = ""
    artist_id: Optional[int] = None
    musicbrainz_id: Optional[str] = None
    release_date: Optional[date] = None
    tracks: List[SoulSyncTrack] = field(default_factory=list)

    @property
    def display_title(self) -> str:
        return self.title or "Unknown Album"
