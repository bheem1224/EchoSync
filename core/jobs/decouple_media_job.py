import logging
from typing import Optional

from core.tiered_logger import get_logger
from services.maintenance_service import run_media_decoupling_job
from core.event_bus import event_bus
from core.task_manager.task_queue import register_job, TaskCategory

logger = get_logger("jobs.decouple_media")


class BaseJob:
    def update_progress(self, current: int, total: int, status: str = ""):
        event_bus.publish("job_progress", {
            "job_name": self.__class__.__name__,
            "current": current,
            "total": total,
            "status": status,
            "percentage": round((current / total) * 100, 1) if total > 0 else 0
        })


class DecoupleMediaJob(BaseJob):
    def execute(self, *args, **kwargs):
        logger.info("Executing DecoupleMediaJob")
        return run_media_decoupling_job(progress_callback=self.update_progress)


def register_decouple_media_job(interval_seconds: Optional[int] = 86400 * 1000, enabled: bool = True):
    """
    Registration snippet for the global JobQueue.
    Registers with a dormant 1000-day interval and start_after so it never runs automatically on startup.
    """
    job_instance = DecoupleMediaJob()
    
    # 1000-day interval and start_after (86,400,000 seconds) prevents automatic startup execution
    dormant_delay = interval_seconds if interval_seconds is not None else 86400 * 1000
    register_job(
        name="system.decouple_collapsed_media",
        func=job_instance.execute,
        interval_seconds=interval_seconds,
        start_after=dormant_delay,
        enabled=enabled,
        category=TaskCategory.DATABASE_WRITE_HEAVY,
        tags=["system", "maintenance", "database"]
    )
