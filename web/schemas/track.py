from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class TrackSchema:
    id: Optional[str] = None
    title: Optional[str] = None
    artists: List[str] = field(default_factory=list)
    album: Optional[str] = None
    album_artist: Optional[str] = None
    duration_ms: Optional[int] = None
    isrc: Optional[str] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    provider_refs: Dict[str, str] = field(default_factory=dict)
    source_provider: Optional[str] = None
    metadata_richness: Optional[str] = None
    metadata_completeness: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "artists": self.artists,
            "album": self.album,
            "album_artist": self.album_artist,
            "duration_ms": self.duration_ms,
            "isrc": self.isrc,
            "track_number": self.track_number,
            "disc_number": self.disc_number,
            "provider_refs": self.provider_refs,
            "source_provider": self.source_provider,
            "metadata_richness": self.metadata_richness,
            "metadata_completeness": self.metadata_completeness,
        }
