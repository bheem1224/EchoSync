from typing import Any

from pydantic import BaseModel, Field

from core.task_manager.models import ProcessOwner


class TaskQueueSummaryResponse(BaseModel):
    stats: dict[str, int] = Field(
        default_factory=dict,
        description="Summary statistics (total, running, pending, blocked)",
    )
    running_jobs: list[dict[str, Any]] = Field(default_factory=list)
    pending_jobs: list[dict[str, Any]] = Field(default_factory=list)
    blocked_jobs: list[dict[str, Any]] = Field(default_factory=list)


class ProcessListResponse(BaseModel):
    total: int
    processes: list[ProcessOwner]


class ProcessTerminateResponse(BaseModel):
    status: str
    registration_id: str
    message: str


class SystemHealthResponse(BaseModel):
    status: str
    timestamp: str
    health_checks: dict[str, Any] = Field(default_factory=dict)
    plugin_states: dict[str, Any] = Field(default_factory=dict)
