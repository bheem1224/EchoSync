from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class TrackSchema(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    artists: List[str] = Field(default_factory=list)
    album: Optional[str] = None
    album_artist: Optional[str] = None
    duration_ms: Optional[int] = None
    isrc: Optional[str] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    plugin_refs: Dict[str, str] = Field(default_factory=dict)
    source_plugin: Optional[str] = None
    metadata_richness: Optional[str] = None
    metadata_completeness: Optional[str] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    file_size_bytes: Optional[int] = None
    added_at: Optional[str] = None
    file_format: Optional[str] = None
    musicbrainz_id: Optional[str] = None
    acoustid_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return self.model_dump(exclude_none=True)

class TrackPatchRequest(BaseModel):
    title: Optional[str] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    musicbrainz_id: Optional[str] = None
    isrc: Optional[str] = None
    global_rating: Optional[float] = None
    
    class Config:
        extra = "allow"
