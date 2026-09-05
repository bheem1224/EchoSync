from datetime import datetime
from enum import Enum
from typing import Any

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


class ProcessCategory(str, Enum):
    CORE_SYSTEM = "Core System"
    OS_SUBPROCESS = "OS Subprocess"
    WASM_SANDBOX = "WebAssembly Sandbox"
    WORKER_THREAD = "Worker Thread"


class ProcessOwner(BaseModel):
    owner_id: str
    owner_type: OwnerType
    pid: int | None = None
    thread_id: int | None = None
    task_name: str
    started_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)
    parent_id: str | None = None
    category: ProcessCategory = ProcessCategory.WORKER_THREAD
    is_killable: bool = True
    cpu_percent: float = 0.0
    memory_bytes: int = 0
    wasm_instance_id: str | None = None


class PluginStatus(BaseModel):
    state: PluginLifecycleState
    message: str | None = None
    last_health_check: datetime | None = None
