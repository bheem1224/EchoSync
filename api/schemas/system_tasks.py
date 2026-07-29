from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from core.task_manager.models import ProcessOwner, PluginStatus, PluginLifecycleState, OwnerType


class TaskQueueSummaryResponse(BaseModel):
    stats: Dict[str, int] = Field(
        default_factory=dict,
        description="Summary statistics (total, running, pending, blocked)"
    )
    running_jobs: List[Dict[str, Any]] = Field(default_factory=list)
    pending_jobs: List[Dict[str, Any]] = Field(default_factory=list)
    blocked_jobs: List[Dict[str, Any]] = Field(default_factory=list)


class ProcessListResponse(BaseModel):
    total: int
    processes: List[ProcessOwner]


class ProcessTerminateResponse(BaseModel):
    status: str
    registration_id: str
    message: str


class SystemHealthResponse(BaseModel):
    status: str
    timestamp: str
    health_checks: Dict[str, Any] = Field(default_factory=dict)
    plugin_states: Dict[str, Any] = Field(default_factory=dict)
