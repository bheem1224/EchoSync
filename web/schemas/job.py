from typing import Any

from pydantic import BaseModel, Field


class JobSchema(BaseModel):
    id: str | None = None
    type: str | None = None
    state: str | None = None  # queued, running, failed, completed
    created_at: str | None = None
    updated_at: str | None = None
    meta: dict = Field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)


class JobRunRequest(BaseModel):
    job_name: str | None = None
    name: str | None = None
    scan_mode: str | None = None
    params: dict[str, Any] | None = Field(default_factory=dict)


class JobIntervalRequest(BaseModel):
    interval_seconds: float


class UpcomingJob(BaseModel):
    job_name: str
    interval_seconds: int
    last_run: str | None = None
    next_run: str | None = None
