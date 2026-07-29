"""
System tasks router alias exposing the blueprint and models for API imports.
"""

from web.routes.system_tasks import bp as router
from api.schemas.system_tasks import (
    TaskQueueSummaryResponse,
    ProcessListResponse,
    ProcessTerminateResponse,
    SystemHealthResponse,
)

__all__ = [
    "router",
    "TaskQueueSummaryResponse",
    "ProcessListResponse",
    "ProcessTerminateResponse",
    "SystemHealthResponse",
]
