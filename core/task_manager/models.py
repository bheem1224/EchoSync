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


class ProcessCategory(str, Enum):
    CORE_SYSTEM = "Core System"
    OS_SUBPROCESS = "OS Subprocess"
    WASM_SANDBOX = "WebAssembly Sandbox"
    WORKER_THREAD = "Worker Thread"


class ProcessOwner(BaseModel):
    owner_id: str
    owner_type: OwnerType
    pid: Optional[int] = None
    thread_id: Optional[int] = None
    task_name: str
    started_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    parent_id: Optional[str] = None
    category: ProcessCategory = ProcessCategory.WORKER_THREAD
    is_killable: bool = True
    cpu_percent: float = 0.0
    memory_bytes: int = 0
    wasm_instance_id: Optional[str] = None


class PluginStatus(BaseModel):
    state: PluginLifecycleState
    message: Optional[str] = None
    last_health_check: Optional[datetime] = None
