from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EchosyncMediaSchema(BaseModel):
    media_id: str | None = None
    file_path: str | None = None
    file_format: str | None = None
    bitrate: int | None = None
    sample_rate: int | None = None
    bit_depth: int | None = None
    channels: int | None = None
    file_size_bytes: int | None = None
    inode: int | None = None
    mtime: float | None = None
    added_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TrackSummarySchema(BaseModel):
    sync_id: str | None = None
    title: str | None = None
    artist_name: str | None = None
    album_title: str | None = None
    artist_id: int | None = None
    album_id: int | None = None
    duration: int | None = None
    track_number: int | None = None
    disc_number: int | None = None
    media_ids: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class TrackResponseSchema(TrackSummarySchema):
    media: list[EchosyncMediaSchema] = []


class SuccessResponse(BaseModel):
    success: bool


class QueueItemSchema(BaseModel):
    id: int
    file_path: str | None = None
    filename: str | None = None
    detected_metadata: dict | None = None
    confidence_score: float | None = None
    created_at: str | None = None


class QueueItemDetailSchema(QueueItemSchema):
    source_metadata: dict | None = None
    file_exists: bool = False


class QueueListResponse(BaseModel):
    queue: list[QueueItemSchema]


class QueueDetailResponse(BaseModel):
    item: QueueItemDetailSchema


class ApproveMatchRequest(BaseModel):
    id: int
    metadata: dict


class ManualSearchRequest(BaseModel):
    query: str


class IgnoreTaskRequest(BaseModel):
    id: int
