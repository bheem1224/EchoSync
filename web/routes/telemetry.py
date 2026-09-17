import asyncio
import json
import os

import psutil
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from core.task_manager.health_service import get_system_health
from core.tiered_logger import get_logger

logger = get_logger("telemetry_route")

router = APIRouter(prefix="/api/v1/system/telemetry", tags=["Telemetry"])


@router.get("/stream")
async def telemetry_stream(request: Request):
    """
    Unified SSE telemetry endpoint streaming:
    - system_stats: CPU, Memory, Disk
    - system_health: Health service summary and status
    - queue_summary: Download queue active vs queued counts
    """

    async def event_generator():
        process = psutil.Process(os.getpid())
        while True:
            if await request.is_disconnected():
                break

            try:
                # 1. System Stats (non-blocking)
                sys_mem = psutil.virtual_memory()
                sys_cpu = psutil.cpu_percent(interval=None)
                app_cpu = process.cpu_percent(interval=None)
                app_mem = process.memory_info().rss
                disk_stats = psutil.disk_usage(os.getcwd())._asdict()

                stats_payload = {
                    "memory": {
                        "total": sys_mem.total,
                        "available": sys_mem.available,
                        "percent": sys_mem.percent,
                        "app_rss": app_mem,
                    },
                    "cpu": {
                        "system": sys_cpu,
                        "app": app_cpu,
                    },
                    "disk": disk_stats,
                }
                yield {
                    "event": "system_stats",
                    "data": json.dumps(stats_payload),
                }

                # 2. System Health
                try:
                    health_payload = get_system_health()
                except Exception as he:
                    logger.debug(f"Failed to gather health for telemetry stream: {he}")
                    health_payload = {"status": "unknown", "error": str(he)}

                yield {
                    "event": "system_health",
                    "data": json.dumps(health_payload),
                }

                # 3. Queue Summary
                queue_summary = {"active": 0, "queued": 0}
                try:
                    from core.database.models.working import DownloadQueue, DownloadStatus
                    from database.working_database import get_working_database

                    w_db = get_working_database()
                    with w_db.session_scope() as session:
                        active_count = (
                            session.query(DownloadQueue)
                            .filter(
                                DownloadQueue.status.in_(
                                    [
                                        DownloadStatus.DOWNLOADING.value,
                                        DownloadStatus.SEARCHING.value,
                                        DownloadStatus.VERIFYING.value,
                                        DownloadStatus.RETRYING.value,
                                    ]
                                )
                            )
                            .count()
                        )
                        queued_count = (
                            session.query(DownloadQueue)
                            .filter(DownloadQueue.status == DownloadStatus.QUEUED.value)
                            .count()
                        )
                        queue_summary = {"active": active_count, "queued": queued_count}
                except Exception as qe:
                    logger.debug(f"Failed to fetch queue summary for telemetry stream: {qe}")

                yield {
                    "event": "queue_summary",
                    "data": json.dumps(queue_summary),
                }

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in telemetry event generator: {e}")

            await asyncio.sleep(2.0)

    return EventSourceResponse(event_generator(), ping=15)
