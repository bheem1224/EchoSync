from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class OwnerType(str, Enum):
    CORE = "core"
    PLUGIN = "plugin"
    SYSTEM_JOB = "system_job"


class PluginLifecycleState(str, Enum):
    UNCONFIGURED = "unconfigured"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    ERROR = "error"


class ProcessOwner(BaseModel):
    owner_id: str
    owner_type: OwnerType
    pid: Optional[int] = None
    thread_id: Optional[int] = None
    task_name: str
    started_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PluginStatus(BaseModel):
    state: PluginLifecycleState
    message: Optional[str] = None
    last_health_check: Optional[datetime] = None
