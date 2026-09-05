from pydantic import BaseModel, Field, ConfigDict


class TrackSchema(BaseModel):
    id: str | None = None
    title: str | None = None
    artists: list[str] = Field(default_factory=list)
    album: str | None = None
    album_artist: str | None = None
    duration_ms: int | None = None
    isrc: str | None = None
    track_number: int | None = None
    disc_number: int | None = None
    plugin_refs: dict[str, str] = Field(default_factory=dict)
    source_plugin: str | None = None
    metadata_richness: str | None = None
    metadata_completeness: str | None = None
    bitrate: int | None = None
    sample_rate: int | None = None
    file_size_bytes: int | None = None
    added_at: str | None = None
    file_format: str | None = None
    musicbrainz_id: str | None = None
    acoustid_id: str | None = None

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)


class TrackPatchRequest(BaseModel):
    title: str | None = None
    track_number: int | None = None
    disc_number: int | None = None
    musicbrainz_id: str | None = None
    isrc: str | None = None
    global_rating: float | None = None

    model_config = ConfigDict(extra="allow")
