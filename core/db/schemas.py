from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class EchosyncMediaSchema(BaseModel):
    media_id: Optional[str] = None
    file_path: Optional[str] = None
    file_format: Optional[str] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    bit_depth: Optional[int] = None
    channels: Optional[int] = None
    file_size_bytes: Optional[int] = None
    inode: Optional[int] = None
    mtime: Optional[float] = None
    added_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class TrackSummarySchema(BaseModel):
    sync_id: Optional[str] = None
    title: Optional[str] = None
    artist_name: Optional[str] = None
    album_title: Optional[str] = None
    artist_id: Optional[int] = None
    album_id: Optional[int] = None
    duration: Optional[int] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    media_ids: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class TrackResponseSchema(TrackSummarySchema):
    media: List[EchosyncMediaSchema] = []
