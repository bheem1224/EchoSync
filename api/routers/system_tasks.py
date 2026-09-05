"""
System tasks router alias exposing the blueprint and models for API imports.
"""

from api.schemas.system_tasks import (
    ProcessListResponse,
    ProcessTerminateResponse,
    SystemHealthResponse,
    TaskQueueSummaryResponse,
)
from web.routes.system_tasks import bp as router

__all__ = [
    "ProcessListResponse",
    "ProcessTerminateResponse",
    "SystemHealthResponse",
    "TaskQueueSummaryResponse",
    "router",
]
